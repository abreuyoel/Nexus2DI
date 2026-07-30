import { Injectable, signal } from '@angular/core';

export interface ActiveVisit {
  // number cuando la visita ya tiene id real del servidor; string ("local_<uuid>")
  // mientras la activación quedó encolada offline y todavía no sincronizó.
  id_visita: number | string;
  pdv_nombre: string;
  id_cliente: number;
  cliente?: string;
  // Si la visita se abrió offline, el id de la cadena en OfflineQueueService
  // (ver offline-queue.service.ts) -- fotos/balance/finalizar deben encolarse
  // como pasos de esta cadena mientras no se resuelva a un id_visita real.
  chainId?: string | null;
}

@Injectable({ providedIn: 'root' })
export class MercUiService {
  activeVisit = signal<ActiveVisit | null>(null);

  openVisit(visit: ActiveVisit) {
    this.activeVisit.set(visit);
  }

  closeVisit() {
    this.activeVisit.set(null);
  }

  /** Reemplaza el id_visita placeholder por el real cuando la cadena sincroniza. */
  resolveVisita(chainId: string, realVisitaId: number) {
    const v = this.activeVisit();
    if (v && v.chainId === chainId) {
      this.activeVisit.set({ ...v, id_visita: realVisitaId, chainId: null });
    }
  }
}
