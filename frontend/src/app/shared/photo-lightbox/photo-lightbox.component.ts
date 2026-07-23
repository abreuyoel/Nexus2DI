import {
  Component, HostListener, OnChanges, SimpleChanges,
  computed, signal, input, output, inject,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { AuthImgDirective } from '../directives/auth-img.directive';
import { AuthImageCacheService } from '../../core/services/auth-image-cache.service';

/** Forma mínima de foto que el lightbox necesita.
 *  Cualquier objeto con `url` (o `file_path`) sirve. */
export interface LightboxPhoto {
  url?: string | null;
  file_path?: string | null;
  // Cualquier otro campo libre para que el padre lo use en el footer.
  [key: string]: any;
}

@Component({
  selector: 'app-photo-lightbox',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatProgressSpinnerModule, AuthImgDirective],
  template: `
@if (open()) {
  <div class="pl-backdrop" (click)="close()"></div>
  <div class="pl-modal" (click)="$event.stopPropagation()">

    <div class="pl-main-content">
      <div class="pl-header">
        <h3 class="pl-title">{{ title() || ' ' }}</h3>
        <div class="pl-counter">
          @if (photos().length > 1) { {{ currentIndex() + 1 }} / {{ photos().length }} }
        </div>
        <button class="pl-close" (click)="close()" type="button" aria-label="Cerrar">
          <mat-icon>close</mat-icon>
        </button>
      </div>

      <div class="pl-body">
        @if (photos().length > 1) {
          <button class="pl-nav pl-prev" type="button"
                  [disabled]="currentIndex() === 0"
                  (click)="prev()" aria-label="Anterior">
            <mat-icon>chevron_left</mat-icon>
          </button>
        }

        <div class="pl-img-wrap">
          @if (currentUrl()) {
            <img [appAuthSrc]="currentUrl()"
                 alt="Foto"
                 (load)="onImgLoad()"
                 (error)="onImgError()"
                 [style.opacity]="loading() ? 0.25 : 1">
          }
          @if (loading()) {
            <div class="pl-loading">
              <mat-spinner diameter="42" strokeWidth="3"></mat-spinner>
            </div>
          }
        </div>

        @if (photos().length > 1) {
          <button class="pl-nav pl-next" type="button"
                  [disabled]="currentIndex() === photos().length - 1"
                  (click)="next()" aria-label="Siguiente">
            <mat-icon>chevron_right</mat-icon>
          </button>
        }
      </div>

      @if (photos().length > 1) {
        <div class="pl-dots">
          @for (dot of dots(); track dot) {
            <span class="pl-dot" [class.active]="currentIndex() === dot" (click)="goTo(dot)"></span>
          }
        </div>
      }

      <div class="pl-footer">
        <ng-content></ng-content>
      </div>
    </div>
    
    <div class="pl-sidebar-container">
      <ng-content select="[lightbox-sidebar]"></ng-content>
    </div>

  </div>
}
  `,
  styles: [`
    :host { position: fixed; inset: 0; z-index: 10000; pointer-events: none; }
    .pl-backdrop {
      position: fixed; inset: 0; background: rgba(0,0,0,.85);
      backdrop-filter: blur(4px); pointer-events: auto; animation: pl-fade .15s;
    }
    .pl-modal {
      position: fixed; inset: 0; pointer-events: auto;
      display: flex; flex-direction: row;
      max-width: 100vw; max-height: 100vh;
      animation: pl-zoom .18s ease-out;
    }
    .pl-main-content {
      flex: 1; display: flex; flex-direction: column; min-width: 0;
    }
    .pl-sidebar-container {
      display: flex; flex-direction: column;
      box-shadow: -4px 0 15px rgba(0,0,0,0.2);
      z-index: 10;
      animation: slide-in-right 0.2s ease-out;
    }
    .pl-sidebar-container:empty { display: none; }
    @keyframes pl-fade { from { opacity: 0 } to { opacity: 1 } }
    @keyframes pl-zoom { from { opacity: 0; transform: scale(.96) } to { opacity: 1; transform: none } }
    @keyframes slide-in-right {
      from { transform: translateX(100%); opacity: 0; }
      to { transform: translateX(0); opacity: 1; }
    }

    .pl-header {
      display: flex; align-items: center; gap: 1rem;
      padding: .85rem 1.25rem;
      color: #fff; font-weight: 600;
    }
    .pl-title { flex: 1; margin: 0; font-size: 1.05rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .pl-counter { font-size: .85rem; opacity: .7; font-weight: 500; min-width: 60px; text-align: right; }
    .pl-close {
      width: 36px; height: 36px; border-radius: 50%; border: 0;
      background: rgba(255,255,255,.12); color: #fff; cursor: pointer;
      display: inline-flex; align-items: center; justify-content: center;
      transition: background .15s;
    }
    .pl-close:hover { background: rgba(255,255,255,.22); }

    .pl-body {
      flex: 1; display: flex; align-items: center; justify-content: center;
      gap: .5rem; padding: 0 .5rem; min-height: 0;
    }
    .pl-img-wrap {
      flex: 1; display: flex; align-items: center; justify-content: center;
      position: relative; min-height: 0;
    }
    .pl-img-wrap img {
      max-width: 100%; max-height: 70vh; object-fit: contain;
      border-radius: 8px; transition: opacity .15s;
      box-shadow: 0 12px 30px rgba(0,0,0,.4);
    }
    .pl-loading {
      position: absolute; inset: 0;
      display: flex; align-items: center; justify-content: center;
      pointer-events: none;
    }

    .pl-nav {
      width: 44px; height: 44px; border-radius: 50%; border: 0;
      background: rgba(255,255,255,.12); color: #fff; cursor: pointer;
      display: inline-flex; align-items: center; justify-content: center;
      transition: background .15s; flex-shrink: 0;
    }
    .pl-nav:hover:not(:disabled) { background: rgba(255,255,255,.22); }
    .pl-nav:disabled { opacity: .25; cursor: not-allowed; }
    .pl-nav mat-icon { font-size: 28px; width: 28px; height: 28px; }

    .pl-dots {
      display: flex; gap: 6px; justify-content: center;
      padding: .5rem 1rem;
    }
    .pl-dot {
      width: 8px; height: 8px; border-radius: 50%;
      background: rgba(255,255,255,.25); cursor: pointer;
      transition: background .15s, transform .15s;
    }
    .pl-dot:hover { background: rgba(255,255,255,.5); }
    .pl-dot.active { background: #a78bfa; transform: scale(1.3); }

    .pl-footer { padding: .75rem 1.25rem 1.25rem; color: #fff; }
    .pl-footer:empty { display: none; }
  `],
})
export class PhotoLightboxComponent implements OnChanges {
  private cacheSvc = inject(AuthImageCacheService);

  open = input<boolean>(false);
  photos = input<LightboxPhoto[]>([]);
  startIndex = input<number>(0);
  title = input<string>('');

  closed = output<void>();
  indexChange = output<number>();

  currentIndex = signal(0);
  loading = signal(false);

  private preloadCache = new Set<string>();

  currentUrl = computed(() => this.urlOf(this.photos()[this.currentIndex()]));
  dots = computed(() => Array.from({ length: Math.min(this.photos().length, 14) }, (_, i) => i));

  ngOnChanges(ch: SimpleChanges): void {
    if (ch['open'] && this.open()) {
      // Reset al abrir
      const start = Math.max(0, Math.min(this.startIndex(), this.photos().length - 1));
      this.currentIndex.set(start);
      const url = this.urlOf(this.photos()[start]);
      this.loading.set(!!url && !this.preloadCache.has(url));
      this.preloadAround(start);
      document.body.classList.add('modal-open');
    }
    if (ch['open'] && !this.open()) {
      document.body.classList.remove('modal-open');
    }
    if (ch['photos']) {
      this.preloadCache.clear();
    }
  }

  close(): void {
    document.body.classList.remove('modal-open');
    this.closed.emit();
  }

  prev(): void {
    if (this.currentIndex() > 0) this.goTo(this.currentIndex() - 1);
  }
  next(): void {
    if (this.currentIndex() < this.photos().length - 1) this.goTo(this.currentIndex() + 1);
  }
  goTo(i: number): void {
    if (i === this.currentIndex()) return;
    const url = this.urlOf(this.photos()[i]);
    this.loading.set(!!url && !this.preloadCache.has(url));
    this.currentIndex.set(i);
    this.preloadAround(i);
    this.indexChange.emit(i);
  }

  onImgLoad(): void {
    const url = this.currentUrl();
    if (url) this.preloadCache.add(url);
    this.loading.set(false);
  }
  onImgError(): void {
    this.loading.set(false);
  }

  private urlOf(p: LightboxPhoto | undefined | null): string | null {
    if (!p) return null;
    return p.url || p.file_path || null;
  }

  private preloadAround(index: number): void {
    const fotos = this.photos();
    for (const i of [index, index + 1, index - 1, index + 2]) {
      const url = this.urlOf(fotos[i]);
      if (!url || this.preloadCache.has(url)) continue;

      if (url.startsWith('/api/media/')) {
        // Requiere el token de auth: se descarga vía HttpClient (mismo
        // mecanismo que AuthImgDirective), no con un <img> nativo.
        this.cacheSvc.get(url).subscribe(() => this.preloadCache.add(url));
      } else {
        const img = new Image();
        img.onload = () => this.preloadCache.add(url);
        img.src = url;
      }
    }
  }

  @HostListener('document:keydown', ['$event'])
  onKey(e: KeyboardEvent): void {
    if (!this.open()) return;
    if (e.key === 'ArrowLeft') { this.prev(); e.preventDefault(); }
    else if (e.key === 'ArrowRight') { this.next(); e.preventDefault(); }
    else if (e.key === 'Escape') { this.close(); e.preventDefault(); }
  }
}
