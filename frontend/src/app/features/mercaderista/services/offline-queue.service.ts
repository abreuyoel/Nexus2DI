import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Subject, fromEvent, merge, of } from 'rxjs';
import { map } from 'rxjs/operators';

export interface OfflinePhoto {
  id: string;           // uuid generado localmente
  visitaId: number;
  tipoFoto: string;
  file: Blob;
  fileName: string;
  timestamp: number;
  status: 'pending' | 'uploading' | 'done' | 'error';
}

/** Paso de una visita que depende del id_visita (real o todavía placeholder) de la cadena. */
export interface ChainStep {
  stepIndex: number;
  kind: 'foto' | 'balances' | 'finalizar';
  url: string;
  isMultipart: boolean;
  jsonBody?: any;
  formFields?: Record<string, string>;
  fileBlob?: Blob;
  fileName?: string;
  status: 'pending' | 'done';
}

/** Sesión de una visita (activar PDV -> fotos/balance/finalizar), encolada mientras no hay conexión. */
export interface Chain {
  chainId: string;
  idPunto: string;
  idCliente: number;
  iniciarUrl: string;
  iniciarBody: any;
  placeholderVisitaId: string;
  realVisitaId: number | null;
  status: 'open' | 'syncing' | 'done' | 'error';
  steps: ChainStep[];
  lastError?: string;
  timestamp: number;
}

const DB_NAME = 'mercaderista_offline_db';
const DB_VERSION = 2;
const STORE_FOTOS = 'pending_photos';
const STORE_CHAINS = 'chains';

@Injectable({ providedIn: 'root' })
export class OfflineQueueService {
  private db: IDBDatabase | null = null;
  private dbReady: Promise<void>;
  private syncing = false;

  private _pendingCount = new BehaviorSubject<number>(0);
  pendingCount$ = this._pendingCount.asObservable();

  /** Emite cuando una cadena obtiene su id_visita real (sync completo). */
  chainResolved$ = new Subject<{ chainId: string; realVisitaId: number }>();

  /** Cadenas que quedaron en error tras un intento de sync (para mostrar banner/retry). */
  failedChains$ = new BehaviorSubject<Chain[]>([]);

  // Observable del estado de la red
  isOnline$ = merge(
    of(navigator.onLine),
    fromEvent(window, 'online').pipe(map(() => true)),
    fromEvent(window, 'offline').pipe(map(() => false)),
  );

  constructor(private http: HttpClient) {
    this.dbReady = this.initDB();
    // Auto-sync cuando se recupera la conexión
    fromEvent(window, 'online').subscribe(() => this.syncAll());
  }

  private initDB(): Promise<void> {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = (e) => {
        const db = (e.target as IDBOpenDBRequest).result;
        if (!db.objectStoreNames.contains(STORE_FOTOS)) {
          db.createObjectStore(STORE_FOTOS, { keyPath: 'id' });
        }
        if (!db.objectStoreNames.contains(STORE_CHAINS)) {
          db.createObjectStore(STORE_CHAINS, { keyPath: 'chainId' });
        }
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

  // ── Fotos sueltas (gestión/exhibición/POP de una visita YA con id real) ──

  /** Encola una foto para subir */
  async enqueuePhoto(visitaId: number, tipoFoto: string, file: File): Promise<string> {
    const photo: OfflinePhoto = {
      id: crypto.randomUUID(),
      visitaId,
      tipoFoto,
      file,
      fileName: file.name,
      timestamp: Date.now(),
      status: 'pending',
    };

    await this.withStore(STORE_FOTOS, 'readwrite', s => s.put(photo));
    this.refreshCount();

    // Si hay conexión, subir inmediatamente
    if (navigator.onLine) {
      this.uploadPhoto(photo);
    }
    return photo.id;
  }

  async getPendingPhotos(): Promise<OfflinePhoto[]> {
    return (await this.withStore<OfflinePhoto[]>(STORE_FOTOS, 'readonly', s => s.getAll())) || [];
  }

  private async uploadPhoto(photo: OfflinePhoto): Promise<void> {
    await this.withStore(STORE_FOTOS, 'readwrite', s => s.put({ ...photo, status: 'uploading' }));

    const fd = new FormData();
    fd.append('visita_id', String(photo.visitaId));
    fd.append('tipo_foto', photo.tipoFoto);
    fd.append('file', photo.file, photo.fileName);

    try {
      await this.http.post('/api/merc/fotos/upload', fd).toPromise();
      await this.withStore(STORE_FOTOS, 'readwrite', s => s.delete(photo.id));
    } catch (err) {
      await this.withStore(STORE_FOTOS, 'readwrite', s => s.put({ ...photo, status: 'error' }));
    }
    this.refreshCount();
  }

  // ── Cadenas (activar PDV -> pasos que dependen del id_visita resultante) ──

  async openChain(meta: { idPunto: string; idCliente: number; iniciarUrl: string; iniciarBody: any }): Promise<{ chainId: string; placeholderVisitaId: string }> {
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

  /** Sube todos los pendientes (fotos sueltas + cadenas) */
  async syncQueue(): Promise<void> { return this.syncAll(); }

  async syncAll(): Promise<void> {
    if (this.syncing || !navigator.onLine) return;
    this.syncing = true;
    try {
      const photos = await this.getPendingPhotos();
      for (const photo of photos) {
        if (photo.status === 'pending' || photo.status === 'error') await this.uploadPhoto(photo);
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
    const photos = await this.getPendingPhotos();
    const chains = await this.getChains();
    this._pendingCount.next(
      photos.filter(p => p.status !== 'done').length + chains.filter(c => c.status !== 'done').length
    );
  }

  private async refreshFailedChains(): Promise<void> {
    const chains = await this.getChains();
    this.failedChains$.next(chains.filter(c => c.status === 'error'));
  }
}
