import { Component } from '@angular/core';
import { MercaderistaComponent } from '../mercaderista/mercaderista.component';

/**
 * Portal de Auditoría de Data: mismo flujo del portal Mercaderista
 * (jornada -> rutas asignadas vía MERCADERISTAS_RUTAS -> PDV -> cliente ->
 * carga de data por categoría) reutilizado tal cual, para el rol Auditor.
 * El backend (/api/merc/*) ya resuelve por cedula = username sin filtrar por
 * rol, así que un usuario Auditor cuya USUARIOS.username coincida con una fila
 * MERCADERISTAS.cedula (tipo='Auditor') usa exactamente los mismos endpoints.
 */
@Component({
  selector: 'app-auditoria-data',
  standalone: true,
  imports: [MercaderistaComponent],
  template: `<app-mercaderista titulo="Portal Auditoría de Data"></app-mercaderista>`,
})
export class AuditoriaDataComponent {}
