import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, map, shareReplay } from 'rxjs';

/**
 * Cachea, como Object URLs, las imágenes servidas por el proxy autenticado
 * /api/media/foto (ver backend/app/routes/media.py).
 *
 * Ese endpoint exige JWT vía header Authorization, pero un <img src="..."]>
 * nativo no puede llevar headers custom, así que el navegador nunca envía
 * el token y el backend responde 403. La solución es pedir la imagen con
 * HttpClient (que sí adjunta el token gracias a auth.interceptor.ts) y
 * mostrar el blob resultante como Object URL. Ver AuthImgDirective.
 *
 * Cachear por path evita volver a descargar la misma foto cuando aparece
 * dos veces (miniatura en el chat + vista completa en el lightbox).
 */
@Injectable({ providedIn: 'root' })
export class AuthImageCacheService {
  private http = inject(HttpClient);
  private cache = new Map<string, Observable<string>>();

  private static readonly MAX_ENTRIES = 300;

  get(path: string): Observable<string> {
    let entry = this.cache.get(path);
    if (!entry) {
      entry = this.http.get(path, { responseType: 'blob' }).pipe(
        map(blob => URL.createObjectURL(blob)),
        shareReplay({ bufferSize: 1, refCount: false }),
      );
      this.evictIfNeeded();
      this.cache.set(path, entry);
    }
    return entry;
  }

  private evictIfNeeded(): void {
    if (this.cache.size < AuthImageCacheService.MAX_ENTRIES) return;
    const oldestKey = this.cache.keys().next().value;
    if (oldestKey !== undefined) this.cache.delete(oldestKey);
  }
}
