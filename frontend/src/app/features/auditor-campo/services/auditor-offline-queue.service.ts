import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Subject, fromEvent, merge, of } from 'rxjs';
import { map } from 'rxjs/operators';

/** Acción simple e independiente (no depende de un id_visita todavía por crear). */
export interface FlatAction {
  id: string;
  url: string;
  isMultipart: boolean;
  jsonBody?: any;
  formFields?: Record<string, string>;
  fileBlob?: Blob;
  fileName?: string;
  label: string;
  status: 'pending' | 'uploading' | 'done' | 'error';
  timestamp: number;
  error?: string;
}

/** Paso de una sesión de auditoría de cliente que depende del id_visita de la cadena. */
export interface ChainStep {
  stepIndex: number;
  kind: 'guardarCategoria' | 'subirFotoCategoria' | 'finalizarCliente';
  url: string;
  isMultipart: boolean;
  jsonBody?: any;
  formFields?: Record<string, string>;
  fileBlob?: Blob;
  fileName?: string;
  status: 'pending' | 'done';
}

/** Sesión completa de auditoría de un cliente, encolada mientras no hay conexión. */
export interface Chain {
  chainId: string;
  clienteId: number;
  pointId: string;
  rutaId: number;
  cedula: string;
  clienteNombre?: string;
  iniciarUrl: string;
  iniciarBody: any;
  placeholderVisitaId: string;
  realVisitaId: number | null;
  status: 'open' | 'syncing' | 'done' | 'error';
  steps: ChainStep[];
  lastError?: string;
  timestamp: number;
}

const DB_NAME = 'auditor_campo_offline_db';
const DB_VERSION = 1;
const STORE_CACHE = 'reference_cache';
const STORE_FLAT = 'flat_actions';
const STORE_CHAINS = 'chains';

@Injectable({ providedIn: 'root' })
export class AuditorOfflineQueueService {
  private db: IDBDatabase | null = null;
  private dbReady: Promise<void>;
  private syncing = false;

  private _pendingCount = new BehaviorSubject<number>(0);
  pendingCount$ = this._pendingCount.asObservable();

  /** Emite cuando una cadena obtiene su id_visita real (sync completo o promoción en caliente). */
  chainResolved$ = new Subject<{ chainId: string; realVisitaId: number }>();

  /** Cadenas que quedaron en error tras un intento de sync (para mostrar banner/retry). */
  failedChains$ = new BehaviorSubject<Chain[]>([]);

  isOnline$ = merge(
    of(navigator.onLine),
    fromEvent(window, 'online').pipe(map(() => true)),
    fromEvent(window, 'offline').pipe(map(() => false)),
  );

  constructor(private http: HttpClient) {
    this.dbReady = this.initDB();
    fromEvent(window, 'online').subscribe(() => this.syncAll());
  }

  // ── IndexedDB bootstrap ────────────────────────────────────────────────

  private initDB(): Promise<void> {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = (e) => {
        const db = (e.target as IDBOpenDBRequest).result;
        if (!db.objectStoreNames.contains(STORE_CACHE)) db.createObjectStore(STORE_CACHE, { keyPath: 'key' });
        if (!db.objectStoreNames.contains(STORE_FLAT)) db.createObjectStore(STORE_FLAT, { keyPath: 'id' });
        if (!db.objectStoreNames.contains(STORE_CHAINS)) db.createObjectStore(STORE_CHAINS, { keyPath: 'chainId' });
      };
      req.onsuccess = (e) => {
        this.db = (e.target as IDBOpenDBRequest).result;
        this.refreshCount();
        resolve();
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

  // ── Caché de datos de solo lectura (rutas/pdvs/clientes/categorias) ────

  async cacheRead(key: string): Promise<any | null> {
    const row = await this.withStore<any>(STORE_CACHE, 'readonly', s => s.get(key));
    return row ? row.data : null;
  }

  async cacheWrite(key: string, data: any): Promise<void> {
    await this.withStore(STORE_CACHE, 'readwrite', s => s.put({ key, data, cachedAt: Date.now() }));
  }

  // ── Acciones planas (sin dependencia de id_visita) ──────────────────────

  async enqueueFlat(action: { url: string; isMultipart: boolean; jsonBody?: any; formFields?: Record<string, string>; fileBlob?: Blob; fileName?: string; label: string; }): Promise<string> {
    const rec: FlatAction = { id: crypto.randomUUID(), status: 'pending', timestamp: Date.now(), ...action };
    await this.withStore(STORE_FLAT, 'readwrite', s => s.put(rec));
    this.refreshCount();
    if (navigator.onLine) this.sendFlat(rec);
    return rec.id;
  }

  private async getFlatActions(): Promise<FlatAction[]> {
    return (await this.withStore<FlatAction[]>(STORE_FLAT, 'readonly', s => s.getAll())) || [];
  }

  private async sendFlat(action: FlatAction): Promise<void> {
    action.status = 'uploading';
    await this.withStore(STORE_FLAT, 'readwrite', s => s.put(action));
    try {
      await this.send(action.url, action.isMultipart, action.jsonBody, action.formFields, action.fileBlob, action.fileName);
      await this.withStore(STORE_FLAT, 'readwrite', s => s.delete(action.id));
    } catch (err: any) {
      action.status = 'error';
      action.error = err?.error?.detail || err?.message || 'Error de sincronización';
      await this.withStore(STORE_FLAT, 'readwrite', s => s.put(action));
    }
    this.refreshCount();
  }

  // ── Cadenas (sesión completa de auditoría de un cliente) ────────────────

  async openChain(meta: { clienteId: number; pointId: string; rutaId: number; cedula: string; clienteNombre?: string; iniciarUrl: string; iniciarBody: any; }): Promise<{ chainId: string; placeholderVisitaId: string }> {
    const chainId = crypto.randomUUID();
    const placeholderVisitaId = `local_${chainId}`;
    const chain: Chain = {
      chainId, ...meta, placeholderVisitaId, realVisitaId: null,
      status: 'open', steps: [], timestamp: Date.now(),
    };
    await this.withStore(STORE_CHAINS, 'readwrite', s => s.put(chain));
    this.refreshCount();
    return { chainId, placeholderVisitaId };
  }

  async addChainStep(chainId: string, step: { kind: ChainStep['kind']; url: string; isMultipart: boolean; jsonBody?: any; formFields?: Record<string, string>; fileBlob?: Blob; fileName?: string; }): Promise<void> {
    const chain = await this.getChain(chainId);
    if (!chain) return;
    chain.steps.push({ ...step, stepIndex: chain.steps.length, status: 'pending' });
    await this.withStore(STORE_CHAINS, 'readwrite', s => s.put(chain));
    this.refreshCount();
  }

  async getChain(chainId: string): Promise<Chain | null> {
    return (await this.withStore<Chain>(STORE_CHAINS, 'readonly', s => s.get(chainId))) || null;
  }

  private async getChains(): Promise<Chain[]> {
    return (await this.withStore<Chain[]>(STORE_CHAINS, 'readonly', s => s.getAll())) || [];
  }

  /** Sustituye el id_visita placeholder por el real en jsonBody/formFields antes de reproducir un paso. */
  private resolveIds<T extends { jsonBody?: any; formFields?: Record<string, string> }>(payload: T, placeholder: string, real: number): T {
    const clone: T = JSON.parse(JSON.stringify(payload ?? {}));
    if (clone.jsonBody) {
      for (const k of Object.keys(clone.jsonBody)) {
        if (clone.jsonBody[k] === placeholder) clone.jsonBody[k] = real;
      }
    }
    if (clone.formFields) {
      for (const k of Object.keys(clone.formFields)) {
        if (clone.formFields[k] === placeholder) clone.formFields[k] = String(real);
      }
    }
    return clone;
  }

  private async syncChain(chain: Chain): Promise<void> {
    chain.status = 'syncing';
    await this.withStore(STORE_CHAINS, 'readwrite', s => s.put(chain));
    try {
      if (chain.realVisitaId == null) {
        const resp: any = await this.http.post<any>(chain.iniciarUrl, chain.iniciarBody).toPromise();
        chain.realVisitaId = resp.id_visita;
        await this.withStore(STORE_CHAINS, 'readwrite', s => s.put(chain));
        this.chainResolved$.next({ chainId: chain.chainId, realVisitaId: chain.realVisitaId! });
      }
      for (const step of chain.steps) {
        if (step.status === 'done') continue;
        const resolved = this.resolveIds(step, chain.placeholderVisitaId, chain.realVisitaId!);
        await this.send(step.url, step.isMultipart, resolved.jsonBody, resolved.formFields, step.fileBlob, step.fileName);
        step.status = 'done';
        await this.withStore(STORE_CHAINS, 'readwrite', s => s.put(chain));
      }
      chain.status = 'done';
      await this.withStore(STORE_CHAINS, 'readwrite', s => s.delete(chain.chainId));
    } catch (err: any) {
      chain.status = 'error';
      chain.lastError = err?.error?.detail || err?.message || 'Error de sincronización';
      await this.withStore(STORE_CHAINS, 'readwrite', s => s.put(chain));
    }
  }

  async retryChain(chainId: string): Promise<void> {
    const chain = await this.getChain(chainId);
    if (chain) await this.syncChain(chain);
    this.refreshCount();
    this.refreshFailedChains();
  }

  // ── Transporte genérico ──────────────────────────────────────────────

  private async send(url: string, isMultipart: boolean, jsonBody?: any, formFields?: Record<string, string>, fileBlob?: Blob, fileName?: string): Promise<any> {
    if (isMultipart) {
      const fd = new FormData();
      for (const [k, v] of Object.entries(formFields || {})) fd.append(k, v);
      if (fileBlob) fd.append('file', fileBlob, fileName || 'foto.jpg');
      return this.http.post(url, fd).toPromise();
    }
    return this.http.post(url, jsonBody).toPromise();
  }

  // ── Orquestación ──────────────────────────────────────────────────────

  async syncAll(): Promise<void> {
    if (this.syncing || !navigator.onLine) return;
    this.syncing = true;
    try {
      const flats = await this.getFlatActions();
      for (const a of flats) {
        if (a.status === 'pending' || a.status === 'error') await this.sendFlat(a);
      }
      const chains = (await this.getChains()).sort((a, b) => a.timestamp - b.timestamp);
      for (const c of chains) {
        if (c.status === 'open' || c.status === 'error') await this.syncChain(c);
      }
    } finally {
      this.syncing = false;
      this.refreshCount();
      this.refreshFailedChains();
    }
  }

  private async refreshCount(): Promise<void> {
    const flats = await this.getFlatActions();
    const chains = await this.getChains();
    this._pendingCount.next(flats.length + chains.filter(c => c.status !== 'done').length);
  }

  private async refreshFailedChains(): Promise<void> {
    const chains = await this.getChains();
    this.failedChains$.next(chains.filter(c => c.status === 'error'));
  }
}
