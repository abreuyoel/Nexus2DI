import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet } from '@angular/router';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { SwUpdate, VersionReadyEvent } from '@angular/service-worker';
import { filter } from 'rxjs/operators';
import { AuthService } from './core/services/auth.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, MatProgressSpinnerModule],
  template: `
    <router-outlet />
    @if (auth.isLoggingOut()) {
      <div class="fixed inset-0 z-[99999] bg-slate-950/80 backdrop-blur-md flex flex-col items-center justify-center gap-4 text-white animate-in fade-in duration-200">
        <mat-spinner diameter="48"></mat-spinner>
        <p class="font-black text-xs tracking-widest uppercase text-slate-300">Cerrando sesión...</p>
      </div>
    }
  `,
})
export class AppComponent {
  private swUpdate = inject(SwUpdate);
  public auth = inject(AuthService);

  constructor() {
    // El service worker (PWA) cachea el bundle entero -- sin esto, un deploy
    // nuevo queda invisible para cualquier pestaña ya abierta hasta que el
    // usuario cierre TODO el navegador (un simple refresh no alcanza, el SW
    // sigue sirviendo el bundle viejo desde su propio caché). Detecta la
    // nueva versión ya descargada en segundo plano y recarga sola.
    if (this.swUpdate.isEnabled) {
      this.swUpdate.versionUpdates
        .pipe(filter((e): e is VersionReadyEvent => e.type === 'VERSION_READY'))
        .subscribe(() => document.location.reload());

      // registerWhenStable ya chequea al cargar, pero una pestaña dejada
      // abierta muchas horas no vuelve a chequear sola -- se fuerza cada 6h.
      setInterval(() => this.swUpdate.checkForUpdate(), 6 * 60 * 60 * 1000);
    }
  }
}
