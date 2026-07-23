import { Directive, ElementRef, Input, OnChanges, OnDestroy, inject } from '@angular/core';
import { Subscription } from 'rxjs';
import { AuthImageCacheService } from '../../core/services/auth-image-cache.service';

/**
 * Reemplazo de [src] para imágenes que vienen del proxy autenticado
 * /api/media/foto. Un <img src="..."> nativo no lleva el header
 * Authorization, así que el backend (que exige JWT) responde 403 y la
 * foto nunca aparece.
 *
 * Esta directiva descarga la imagen vía HttpClient (que sí adjunta el
 * token, ver auth.interceptor.ts) y la asigna como Object URL. Las URLs
 * que no apuntan al proxy (data:, blob:, http(s) externas ya firmadas)
 * se asignan directo, sin pasar por HttpClient.
 *
 * Uso: <img [appAuthSrc]="foto.url"> en vez de <img [src]="foto.url">.
 */
@Directive({
  selector: 'img[appAuthSrc]',
  standalone: true,
})
export class AuthImgDirective implements OnChanges, OnDestroy {
  @Input('appAuthSrc') appAuthSrc: string | null | undefined;

  private cacheSvc = inject(AuthImageCacheService);
  private el = inject(ElementRef<HTMLImageElement>);
  private sub?: Subscription;

  ngOnChanges(): void {
    this.sub?.unsubscribe();
    const url = this.appAuthSrc;

    if (!url) {
      this.el.nativeElement.removeAttribute('src');
      return;
    }
    if (!url.startsWith('/api/media/')) {
      this.el.nativeElement.src = url;
      return;
    }
    this.sub = this.cacheSvc.get(url).subscribe({
      next: (objectUrl) => { this.el.nativeElement.src = objectUrl; },
      error: () => { this.el.nativeElement.dispatchEvent(new Event('error')); },
    });
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
  }
}
