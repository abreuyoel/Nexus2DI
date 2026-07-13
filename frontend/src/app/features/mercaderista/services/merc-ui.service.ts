import { Injectable, signal } from '@angular/core';

export interface ActiveVisit {
  id_visita: number;
  pdv_nombre: string;
  id_cliente: number;
  cliente?: string;
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
}
