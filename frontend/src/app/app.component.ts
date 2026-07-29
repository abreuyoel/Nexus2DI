import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { SwUpdate, VersionReadyEvent } from '@angular/service-worker';
import { filter } from 'rxjs/operators';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet],
  template: '<router-outlet />',
})
export class AppComponent {
  private swUpdate = inject(SwUpdate);

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
