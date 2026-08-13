import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { BehaviorSubject, fromEvent, merge, of, firstValueFrom } from 'rxjs';
import { map, timeout } from 'rxjs/operators';

/**
 * A diferencia de auditor-campo (sesiones independientes por cliente), el flujo del
 * encuestador es una jornada estrictamente lineal: activar jornada -> abrir encuesta de
 * centro -> N médicos -> cerrar encuesta -> (repetir con otro centro) -> finalizar jornada.
 * El backend exige ese orden (una encuesta abierta a la vez, jornada "En Progreso" para
 * poder abrir una, etc.), así que en vez de colas independientes se usa UNA cola ordenada
 * (por `seq`) que se reproduce estrictamente en orden y se detiene en el primer error.
 */
export interface QueueEntry {
  id: string;
  seq: number;
  url: string;
  jsonBody?: any;
  label: string;
  /** Si esta llamada genera un id que acciones posteriores necesitan (ej. id_encuesta). */
  producesLocalId?: string;
  /** Campo de la respuesta del servidor que contiene el id real a asociar con `producesLocalId`. */
  idField?: string;
  resolvedValue?: any;
  status: 'pending' | 'done' | 'error';
  error?: string;
  timestamp: number;
}

const DB_NAME = 'encuestador_offline_db';
const DB_VERSION = 1;
const STORE_CACHE = 'reference_cache';
const STORE_QUEUE = 'queue';

/** Con señal mala un request puede quedarse colgado un minuto o más antes de
 *  fallar. Se corta antes y se encola, en vez de dejar al encuestador
 *  esperando frente al médico. */
const REQUEST_TIMEOUT_MS = 12_000;

/** Clave del listado completo de centros, precargado estando online para
 *  poder buscar localmente sin señal (el caché por query -- `centros:${q}` --
 *  solo sirve si se buscó ese texto exacto estando conectado). */
const KEY_CENTROS_ALL = 'centros_all';

/**
 * Umbrales de espacio del dispositivo (fracción de la cuota ya usada por la
 * app). NO son un límite de la cola: un médico encolado pesa ~2 KB, así que
 * 1000 médicos son ~2 MB -- irrelevante hasta para un celular viejo. Miden el
 * espacio REAL que le queda al teléfono (que puede estar lleno de fotos), y
 * sirven para avisar con tiempo, nunca para impedir seguir cargando: el
 * encuestador está sin señal justamente porque está adentro del centro de
 * salud, y bloquearlo perdería más data de la que se evita.
 */
const STORAGE_WARN_PCT = 0.80;
const STORAGE_CRITICAL_PCT = 0.95;

export interface StorageHealth {
  /** true si el navegador se comprometió a NO borrar los datos solo. */
  persisted: boolean;
  usage: number;
  quota: number;
  /** Fracción usada (0-1). 0 si el navegador no reporta cuota. */
  pct: number;
  nivel: 'ok' | 'warn' | 'critical';
  /** Soporte real de la API en este navegador (Safari viejo no la tiene). */
  soportado: boolean;
}

@Injectable({ providedIn: 'root' })
export class EncuestadorOfflineQueueService {
  private db: IDBDatabase | null = null;
  private dbReady: Promise<void>;
  private syncing = false;
  private seqCounter = 0;

  private _pendingCount = new BehaviorSubject<number>(0);
  pendingCount$ = this._pendingCount.asObservable();

  private _syncError = new BehaviorSubject<QueueEntry | null>(null);
  syncError$ = this._syncError.asObservable();

  isOnline$ = merge(
    of(navigator.onLine),
    fromEvent(window, 'online').pipe(map(() => true)),
    fromEvent(window, 'offline').pipe(map(() => false)),
  );

  constructor(private http: HttpClient) {
    this.dbReady = this.initDB();
    fromEvent(window, 'online').subscribe(() => this.syncAll());
  }

  private initDB(): Promise<void> {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = (e) => {
        const db = (e.target as IDBOpenDBRequest).result;
        if (!db.objectStoreNames.contains(STORE_CACHE)) db.createObjectStore(STORE_CACHE, { keyPath: 'key' });
        if (!db.objectStoreNames.contains(STORE_QUEUE)) db.createObjectStore(STORE_QUEUE, { keyPath: 'id' });
      };
      req.onsuccess = (e) => {
        this.db = (e.target as IDBOpenDBRequest).result;
        // No await aquí: this.dbReady (esta misma promesa) todavía no se resolvió, y getAll()/
        // refreshCount() dependen de él vía withStore() -> esperarlos antes de resolve() sería un deadlock.
        resolve();
        this.getAll().then(all => {
          this.seqCounter = all.reduce((m, x) => Math.max(m, x.seq), 0);
        });
        this.refreshCount();
      };
      req.onerror = () => reject(req.error);
    });
  }

  private async withStore<T>(store: string, mode: IDBTransactionMode, fn: (s: IDBObjectStore) => IDBRequest): Promise<T> {
    await this.dbReady;
    return new Promise((resolve, reject) => {
      if (!this.db) return resolve(undefined as any);
      const tx = this.db.transaction(store, mode);
      const req = fn(tx.objectStore(store));
      req.onsuccess = () => resolve(req.result as T);
      req.onerror = () => reject(req.error);
    });
  }

  // ── Caché de lectura (jornada-activa, encuesta-abierta, búsquedas de centros/médicos) ──

  async cacheRead(key: string): Promise<any | null> {
    const row = await this.withStore<any>(STORE_CACHE, 'readonly', s => s.get(key));
    return row ? row.data : null;
  }

  async cacheWrite(key: string, data: any): Promise<void> {
    await this.withStore(STORE_CACHE, 'readwrite', s => s.put({ key, data, cachedAt: Date.now() }));
  }

  // ── Salud del almacenamiento del dispositivo ────────────────────────────

  /**
   * Pide almacenamiento "persistente". Sin esto los datos del sitio son
   * "best-effort": Android/Chrome los puede desalojar SOLO y SIN AVISAR
   * cuando al teléfono le falta espacio -- y ahí se perdería la jornada
   * entera encolada. Es el riesgo real de un dispositivo de gama baja, y
   * mucho más grave que el tamaño de la cola (que es de KBs).
   *
   * El navegador puede conceder o no según heurísticas (PWA instalada, uso
   * frecuente, permisos). Si lo niega, no rompe nada: se sigue trabajando,
   * pero conviene sincronizar más seguido -- por eso se refleja en la UI.
   */
  async requestPersistence(): Promise<boolean> {
    try {
      if (!navigator.storage?.persist) return false;
      if (await navigator.storage.persisted()) return true;
      return await navigator.storage.persist();
    } catch {
      return false;
    }
  }

  /** Espacio real disponible para la app en ESTE dispositivo. */
  async getStorageHealth(): Promise<StorageHealth> {
    const vacio: StorageHealth = { persisted: false, usage: 0, quota: 0, pct: 0, nivel: 'ok', soportado: false };
    try {
      if (!navigator.storage?.estimate) return vacio;
      const est = await navigator.storage.estimate();
      const usage = est.usage ?? 0;
      const quota = est.quota ?? 0;
      const pct = quota > 0 ? usage / quota : 0;
      const persisted = navigator.storage.persisted ? await navigator.storage.persisted() : false;
      const nivel: StorageHealth['nivel'] =
        pct >= STORAGE_CRITICAL_PCT ? 'critical' : pct >= STORAGE_WARN_PCT ? 'warn' : 'ok';
      return { persisted, usage, quota, pct, nivel, soportado: true };
    } catch {
      return vacio;
    }
  }

  // ── Identificadores locales (placeholder mientras no hay id real del servidor) ──

  newLocalId(): string {
    return `local_${crypto.randomUUID()}`;
  }

  isLocalId(v: any): boolean {
    return typeof v === 'string' && v.startsWith('local_');
  }

  // ── Cola ordenada ──────────────────────────────────────────────────────

  private async getAll(): Promise<QueueEntry[]> {
    return (await this.withStore<QueueEntry[]>(STORE_QUEUE, 'readonly', s => s.getAll())) || [];
  }

  async enqueue(entry: { url: string; jsonBody?: any; label: string; producesLocalId?: string; idField?: string; }): Promise<string> {
    const rec: QueueEntry = { id: crypto.randomUUID(), seq: ++this.seqCounter, status: 'pending', timestamp: Date.now(), ...entry };
    try {
      await this.withStore(STORE_QUEUE, 'readwrite', s => s.put(rec));
    } catch (err: any) {
      // Único caso donde el dispositivo REALMENTE no puede guardar más. Se
      // marca para que la UI lo distinga de un error del servidor y le diga
      // al encuestador qué hacer (liberar espacio / buscar señal y subir),
      // en vez de un "error al guardar" genérico.
      if (err?.name === 'QuotaExceededError' || err?.code === 22) {
        this.seqCounter--; // no se llegó a guardar: no consumir el número de orden
        const e: any = new Error('SIN_ESPACIO');
        e.sinEspacio = true;
        throw e;
      }
      throw err;
    }
    this.refreshCount();
    if (navigator.onLine) this.syncAll();
    return rec.id;
  }

  /**
   * ¿Este fallo es "no llegué al servidor" (encolar y seguir) o "el servidor
   * rechazó el dato" (mostrar el error de verdad)?
   *
   * La distinción importa: encolar un 400/422/500 de validación haría que se
   * reintente para siempre y, como la cola se detiene en el primer error,
   * trabaría TODO lo que venga detrás. Solo se encola lo que puede andar bien
   * más tarde: sin red (status 0), timeout propio, o el gateway caído/saturado.
   */
  private esFalloDeRed(err: any): boolean {
    if (err?.name === 'TimeoutError') return true;
    if (err instanceof HttpErrorResponse) {
      return err.status === 0 || err.status === 408 || err.status === 429
        || err.status === 502 || err.status === 503 || err.status === 504;
    }
    return false;
  }

  /**
   * Única vía de escritura del módulo. Si no hay red -- o si el request falla
   * por red/timeout, que es lo que realmente pasa con señal débil, donde
   * `navigator.onLine` sigue diciendo `true` -- guarda en la cola en vez de
   * perder lo que el encuestador acaba de cargar.
   *
   * Devuelve `queued: true` si quedó pendiente de sincronizar; lanza solo si
   * el servidor rechazó el dato de verdad (ahí sí hay que mostrarle el error).
   */
  async postOrQueue<T = any>(
    url: string,
    jsonBody: any,
    opts: { label: string; producesLocalId?: string; idField?: string },
  ): Promise<{ queued: boolean; response?: T }> {
    if (!navigator.onLine) {
      await this.enqueue({ url, jsonBody, ...opts });
      return { queued: true };
    }
    try {
      const resp = await firstValueFrom(
        this.http.post<T>(url, jsonBody ?? {}).pipe(timeout(REQUEST_TIMEOUT_MS)),
      );
      return { queued: false, response: resp };
    } catch (err: any) {
      if (this.esFalloDeRed(err)) {
        await this.enqueue({ url, jsonBody, ...opts });
        return { queued: true };
      }
      throw err;
    }
  }

  /** Cola visible para la UI (lo que todavía no subió, en orden). */
  async getPendientes(): Promise<QueueEntry[]> {
    return (await this.getAll()).filter(e => e.status !== 'done').sort((a, b) => a.seq - b.seq);
  }

  // ── Precarga de datos de referencia (para poder trabajar sin señal) ─────

  /** Se llama estando online al entrar al módulo: deja en IndexedDB el listado
   *  completo de centros y los catálogos, que es lo que hace falta para
   *  completar una jornada entera sin conexión. */
  async prefetchReference(apiBase: string): Promise<void> {
    if (!navigator.onLine) return;
    try {
      const centros = await firstValueFrom(
        this.http.get<any>(`${apiBase}/centros?q=`).pipe(timeout(REQUEST_TIMEOUT_MS)),
      );
      if (centros?.centros) await this.cacheWrite(KEY_CENTROS_ALL, centros.centros);
    } catch { /* sin señal: se usa lo que ya haya cacheado de antes */ }
    try {
      const cat = await firstValueFrom(
        this.http.get<any>(`${apiBase}/catalogos`).pipe(timeout(REQUEST_TIMEOUT_MS)),
      );
      if (cat) await this.cacheWrite('catalogos', cat);
    } catch { /* idem */ }
  }

  /** Búsqueda local sobre el listado precargado -- reemplaza al servidor
   *  cuando no hay señal, por nombre o ciudad, igual que el endpoint. */
  async buscarCentrosLocal(q: string): Promise<any[]> {
    const all: any[] = (await this.cacheRead(KEY_CENTROS_ALL)) || [];
    const term = (q || '').trim().toLowerCase();
    if (!term) return all;
    return all.filter(c =>
      (c.nombre_centro || '').toLowerCase().includes(term) ||
      (c.ciudad || '').toLowerCase().includes(term),
    );
  }

  async cacheCentrosAll(centros: any[]): Promise<void> {
    await this.cacheWrite(KEY_CENTROS_ALL, centros);
  }

  /** Sustituye ocurrencias de placeholders locales por sus valores reales ya resueltos. */
  private substitute(entry: QueueEntry, idMap: Map<string, any>): { url: string; jsonBody?: any } {
    let url = entry.url;
    for (const [k, v] of idMap) url = url.split(k).join(String(v));
    let jsonBody = entry.jsonBody;
    if (jsonBody) {
      jsonBody = JSON.parse(JSON.stringify(jsonBody));
      for (const k of Object.keys(jsonBody)) {
        if (typeof jsonBody[k] === 'string') {
          for (const [ph, v] of idMap) {
            if (jsonBody[k] === ph) jsonBody[k] = v;
          }
        }
      }
    }
    return { url, jsonBody };
  }

  async syncAll(): Promise<void> {
    if (this.syncing || !navigator.onLine) return;
    this.syncing = true;
    try {
      const entries = (await this.getAll()).sort((a, b) => a.seq - b.seq);
      const idMap = new Map<string, any>();
      for (const e of entries) {
        if (e.status === 'done') {
          if (e.producesLocalId && e.resolvedValue != null) idMap.set(e.producesLocalId, e.resolvedValue);
          continue;
        }
        const { url, jsonBody } = this.substitute(e, idMap);
        try {
          const resp: any = await firstValueFrom(
            this.http.post(url, jsonBody ?? {}).pipe(timeout(REQUEST_TIMEOUT_MS)),
          );
          e.status = 'done'; e.error = undefined;
          if (e.producesLocalId && e.idField) {
            e.resolvedValue = resp?.[e.idField];
            idMap.set(e.producesLocalId, e.resolvedValue);
          }
          await this.withStore(STORE_QUEUE, 'readwrite', s => s.put(e));
        } catch (err: any) {
          e.status = 'error';
          e.error = err?.error?.detail || err?.message || 'Error de sincronización';
          await this.withStore(STORE_QUEUE, 'readwrite', s => s.put(e));
          this._syncError.next(e);
          return; // se detiene en el primer fallo: preserva el orden/las dependencias
        }
      }
      this._syncError.next(null);
      // Cola totalmente drenada: limpiar entradas ya sincronizadas.
      const remaining = await this.getAll();
      if (remaining.every(x => x.status === 'done')) {
        for (const e of remaining) await this.withStore(STORE_QUEUE, 'readwrite', s => s.delete(e.id));
      }
    } finally {
      this.syncing = false;
      this.refreshCount();
    }
  }

  /**
   * Descarta una entrada de la cola. Necesario porque la cola se detiene en el
   * primer error: si una entrada quedó envenenada (el servidor la rechaza
   * siempre, ej. un dato inválido), sin esto bloquearía para siempre todo lo
   * que venga detrás. Es destructivo -- la UI debe confirmarlo y mostrar qué
   * se está por perder.
   */
  async descartar(id: string): Promise<void> {
    await this.withStore(STORE_QUEUE, 'readwrite', s => s.delete(id));
    this._syncError.next(null);
    await this.refreshCount();
    if (navigator.onLine) this.syncAll();
  }

  private async refreshCount(): Promise<void> {
    const entries = await this.getAll();
    this._pendingCount.next(entries.filter(e => e.status !== 'done').length);
  }

  // ── Respaldos (Backup Manual) ──────────────────────────────────────────

  /**
   * Exporta toda la cola (pendientes y completados recientes) a un string JSON.
   */
  async exportQueue(): Promise<string> {
    const entries = await this.getAll();
    return JSON.stringify(entries, null, 2);
  }

  /**
   * Importa entradas desde un JSON de respaldo.
   * Evita duplicados basándose en el ID único (UUID) de cada entrada.
   * Actualiza el contador de secuencia para que los próximos envíos sigan el orden.
   */
  async importQueue(jsonString: string): Promise<{ success: boolean; count: number; error?: string }> {
    try {
      const entries: QueueEntry[] = JSON.parse(jsonString);
      if (!Array.isArray(entries)) {
        return { success: false, count: 0, error: 'Formato de respaldo inválido' };
      }

      let importCount = 0;
      for (const entry of entries) {
        if (!entry.id || !entry.url) continue; // Validación básica

        // put() sobreescribe si el ID ya existe, lo cual es seguro porque el ID es un UUID único de esta entrada
        await this.withStore(STORE_QUEUE, 'readwrite', s => s.put(entry));

        // Actualizamos el contador de secuencia para evitar choques futuros
        if (entry.seq > this.seqCounter) {
          this.seqCounter = entry.seq;
        }
        importCount++;
      }

      await this.refreshCount();
      return { success: true, count: importCount };
    } catch (err: any) {
      return { success: false, count: 0, error: 'No se pudo leer el archivo de respaldo' };
    }
  }
}
