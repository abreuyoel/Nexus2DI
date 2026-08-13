import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MercaderistaComponent } from '../mercaderista/mercaderista.component';
import { DataComponent } from '../data/data.component';
import { AuthService } from '../../core/services/auth.service';

/**
 * Portal de Auditoría de Data:
 * - Para el rol Admin/Analista, muestra el panel de control y revisión de data (DataComponent).
 * - Para el rol Auditor (de campo), muestra el flujo móvil de carga de mercaderista (MercaderistaComponent).
 */
@Component({
  selector: 'app-auditoria-data',
  standalone: true,
  imports: [CommonModule, MercaderistaComponent, DataComponent],
  template: `
    <app-data *ngIf="isAdmin"></app-data>
    <app-mercaderista *ngIf="!isAdmin" titulo="Portal Auditoría de Data"></app-mercaderista>
  `,
})
export class AuditoriaDataComponent {
  get isAdmin(): boolean {
    const user = this.auth.currentUser();
    return user ? (user.is_admin || user.rol === 'admin' || user.rol === 'analyst') : false;
  }

  constructor(private auth: AuthService) {}
}
