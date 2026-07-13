import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, fromEvent, merge, of } from 'rxjs';
import { map } from 'rxjs/operators';

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
    await this.withStore(STORE_QUEUE, 'readwrite', s => s.put(rec));
    this.refreshCount();
    if (navigator.onLine) this.syncAll();
    return rec.id;
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
          const resp: any = await this.http.post(url, jsonBody ?? {}).toPromise();
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

  private async refreshCount(): Promise<void> {
    const entries = await this.getAll();
    this._pendingCount.next(entries.filter(e => e.status !== 'done').length);
  }
}
