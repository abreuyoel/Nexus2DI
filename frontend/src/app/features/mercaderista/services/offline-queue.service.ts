import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, fromEvent, merge, of } from 'rxjs';
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

const DB_NAME = 'mercaderista_offline_db';
const DB_VERSION = 1;
const STORE_FOTOS = 'pending_photos';

@Injectable({ providedIn: 'root' })
export class OfflineQueueService {
  private db: IDBDatabase | null = null;
  private _pendingCount = new BehaviorSubject<number>(0);
  pendingCount$ = this._pendingCount.asObservable();

  // Observable del estado de la red
  isOnline$ = merge(
    of(navigator.onLine),
    fromEvent(window, 'online').pipe(map(() => true)),
    fromEvent(window, 'offline').pipe(map(() => false)),
  );

  constructor(private http: HttpClient) {
    this.initDB();
    // Auto-sync cuando se recupera la conexión
    fromEvent(window, 'online').subscribe(() => this.syncQueue());
  }

  private async initDB(): Promise<void> {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = (e) => {
        const db = (e.target as IDBOpenDBRequest).result;
        if (!db.objectStoreNames.contains(STORE_FOTOS)) {
          db.createObjectStore(STORE_FOTOS, { keyPath: 'id' });
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

    await this.dbPut(photo);
    this.refreshCount();

    // Si hay conexión, subir inmediatamente
    if (navigator.onLine) {
      this.uploadPhoto(photo);
    }
    return photo.id;
  }

  /** Sube todos los pendientes */
  async syncQueue(): Promise<void> {
    if (!navigator.onLine) return;
    const photos = await this.getPendingPhotos();
    for (const photo of photos) {
      if (photo.status === 'pending' || photo.status === 'error') {
        await this.uploadPhoto(photo);
      }
    }
  }

  private async uploadPhoto(photo: OfflinePhoto): Promise<void> {
    await this.dbUpdateStatus(photo.id, 'uploading');

    const fd = new FormData();
    fd.append('visita_id', String(photo.visitaId));
    fd.append('tipo_foto', photo.tipoFoto);
    fd.append('file', photo.file, photo.fileName);

    try {
      await this.http.post('/api/merc/fotos/upload', fd).toPromise();
      await this.dbDelete(photo.id);
      this.refreshCount();
    } catch (err) {
      await this.dbUpdateStatus(photo.id, 'error');
    }
  }

  async getPendingPhotos(): Promise<OfflinePhoto[]> {
    return new Promise((resolve) => {
      if (!this.db) return resolve([]);
      const tx = this.db.transaction(STORE_FOTOS, 'readonly');
      const req = tx.objectStore(STORE_FOTOS).getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => resolve([]);
    });
  }

  private async refreshCount(): Promise<void> {
    const photos = await this.getPendingPhotos();
    this._pendingCount.next(photos.filter(p => p.status !== 'done').length);
  }

  private dbPut(photo: OfflinePhoto): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.db) return resolve();
      const tx = this.db.transaction(STORE_FOTOS, 'readwrite');
      const req = tx.objectStore(STORE_FOTOS).put(photo);
      req.onsuccess = () => resolve();
      req.onerror = () => reject(req.error);
    });
  }

  private dbDelete(id: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.db) return resolve();
      const tx = this.db.transaction(STORE_FOTOS, 'readwrite');
      const req = tx.objectStore(STORE_FOTOS).delete(id);
      req.onsuccess = () => resolve();
      req.onerror = () => reject(req.error);
    });
  }

  private dbUpdateStatus(id: string, status: OfflinePhoto['status']): Promise<void> {
    return new Promise(async (resolve) => {
      const all = await this.getPendingPhotos();
      const photo = all.find(p => p.id === id);
      if (photo) {
        photo.status = status;
        await this.dbPut(photo);
      }
      resolve();
    });
  }
}
