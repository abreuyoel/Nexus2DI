import { Component, Inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ApiService } from '../../core/services/api.service';

export interface VisitThreadDialogData {
  visitaId: number;
  puntoNombre?: string;
}

@Component({
  selector: 'app-visit-thread-dialog',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatIconModule, MatProgressSpinnerModule],
  template: `
<div class="vt-dialog">
  <div class="vt-header">
    <div class="vt-header-icon"><mat-icon>chat_bubble</mat-icon></div>
    <div>
      <h2 class="vt-title">Chat de la visita</h2>
      <p class="vt-subtitle">{{ data.puntoNombre || ('Visita #' + data.visitaId) }}</p>
    </div>
    <button class="vt-close" (click)="cancel()" [disabled]="loading()"><mat-icon>close</mat-icon></button>
  </div>

  <div class="vt-body">
    @if (loading()) {
      <div class="vt-loading">
        <mat-spinner diameter="32"></mat-spinner>
        <p>Abriendo chat...</p>
      </div>
    } @else {
      <button class="vt-option" (click)="open('operativo')">
        <mat-icon>groups</mat-icon>
        <div>
          <span class="vt-option-title">Solo equipo</span>
          <span class="vt-option-desc">Analistas, mercaderistas y coordinadores — sin el cliente</span>
        </div>
      </button>
      <button class="vt-option" (click)="open('operativo_cliente')">
        <mat-icon>diversity_3</mat-icon>
        <div>
          <span class="vt-option-title">Equipo + Cliente</span>
          <span class="vt-option-desc">Incluye a los usuarios del cliente en la conversación</span>
        </div>
      </button>
    }
  </div>
</div>
  `,
  styles: [`
    /* Este diálogo no declaraba NI fondo NI color de texto propios: heredaba
       lo que hubiera, y sobre el backdrop oscuro las opciones quedaban
       ilegibles (reportado en campo: "no se pueden ver las opciones").
       Ahora define ambos explícitamente para tema claro y oscuro, y las
       descripciones usan un color real en vez de opacity, que sobre fondo
       traslúcido las volvía invisibles. */
    .vt-dialog { min-width: 340px; background:#ffffff; color:#0f172a; border-radius:16px; }
    :host-context(html.dark) .vt-dialog { background:#0f172a; color:#e2e8f0; }

    .vt-header { display:flex; align-items:center; gap:12px; padding:20px 20px 12px; }
    .vt-header-icon { width:40px; height:40px; border-radius:12px; background:rgba(31,111,235,0.15); color:#1f6feb; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
    .vt-title { margin:0; font-size:16px; font-weight:800; color:inherit; }
    .vt-subtitle { margin:2px 0 0; font-size:12px; color:#64748b; }
    :host-context(html.dark) .vt-subtitle { color:#94a3b8; }

    .vt-close { margin-left:auto; background:transparent; border:none; cursor:pointer; color:#64748b; }
    .vt-close:hover { color:#0f172a; }
    :host-context(html.dark) .vt-close { color:#94a3b8; }
    :host-context(html.dark) .vt-close:hover { color:#ffffff; }

    .vt-body { padding: 4px 20px 20px; display:flex; flex-direction:column; gap:10px; }
    .vt-loading { display:flex; flex-direction:column; align-items:center; gap:12px; padding:24px 0; color:#64748b; }
    :host-context(html.dark) .vt-loading { color:#94a3b8; }

    .vt-option { display:flex; align-items:center; gap:12px; text-align:left; padding:14px; border-radius:14px;
                 border:1px solid #e2e8f0; background:#f8fafc; color:#0f172a; cursor:pointer; transition:all .15s; }
    .vt-option:hover { background:rgba(31,111,235,0.10); border-color:#1f6feb; }
    :host-context(html.dark) .vt-option { border-color:rgba(255,255,255,0.12); background:#1e293b; color:#e2e8f0; }
    :host-context(html.dark) .vt-option:hover { background:rgba(31,111,235,0.22); border-color:#1f6feb; }

    .vt-option-title { display:block; font-weight:700; font-size:13px; color:inherit; }
    .vt-option-desc { display:block; font-size:11px; margin-top:2px; color:#64748b; }
    :host-context(html.dark) .vt-option-desc { color:#94a3b8; }
  `],
})
export class VisitThreadDialogComponent {
  loading = signal(false);

  constructor(
    private api: ApiService,
    private dialogRef: MatDialogRef<VisitThreadDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: VisitThreadDialogData,
  ) {}

  open(tipoGrupo: 'operativo' | 'operativo_cliente'): void {
    this.loading.set(true);
    this.api.getOrCreateVisitaThread(this.data.visitaId, tipoGrupo).subscribe({
      next: (thread) => { this.loading.set(false); this.dialogRef.close(thread); },
      error: () => { this.loading.set(false); this.dialogRef.close(); },
    });
  }

  cancel(): void {
    this.dialogRef.close();
  }
}
