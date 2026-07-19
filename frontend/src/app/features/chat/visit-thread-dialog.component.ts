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
      <button class="vt-option" (click)="open('visit_team')">
        <mat-icon>groups</mat-icon>
        <div>
          <span class="vt-option-title">Solo equipo</span>
          <span class="vt-option-desc">Analistas, mercaderistas y supervisores — sin el cliente</span>
        </div>
      </button>
      <button class="vt-option" (click)="open('visit_team_client')">
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
    .vt-dialog { min-width: 340px; }
    .vt-header { display:flex; align-items:center; gap:12px; padding:20px 20px 12px; }
    .vt-header-icon { width:40px; height:40px; border-radius:12px; background:rgba(31,111,235,0.15); color:#1f6feb; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
    .vt-title { margin:0; font-size:16px; font-weight:800; }
    .vt-subtitle { margin:2px 0 0; font-size:12px; opacity:0.6; }
    .vt-close { margin-left:auto; background:transparent; border:none; cursor:pointer; opacity:0.6; }
    .vt-close:hover { opacity:1; }
    .vt-body { padding: 4px 20px 20px; display:flex; flex-direction:column; gap:10px; }
    .vt-loading { display:flex; flex-direction:column; align-items:center; gap:12px; padding:24px 0; opacity:0.7; }
    .vt-option { display:flex; align-items:center; gap:12px; text-align:left; padding:14px; border-radius:14px; border:1px solid rgba(128,128,128,0.2); background:transparent; cursor:pointer; transition:all .15s; }
    .vt-option:hover { background:rgba(31,111,235,0.08); border-color:#1f6feb; }
    .vt-option-title { display:block; font-weight:700; font-size:13px; }
    .vt-option-desc { display:block; font-size:11px; opacity:0.6; margin-top:2px; }
  `],
})
export class VisitThreadDialogComponent {
  loading = signal(false);

  constructor(
    private api: ApiService,
    private dialogRef: MatDialogRef<VisitThreadDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: VisitThreadDialogData,
  ) {}

  open(tipo: 'visit_team' | 'visit_team_client'): void {
    this.loading.set(true);
    this.api.getOrCreateVisitThread(this.data.visitaId, tipo).subscribe({
      next: (conv) => { this.loading.set(false); this.dialogRef.close(conv); },
      error: () => { this.loading.set(false); this.dialogRef.close(); },
    });
  }

  cancel(): void {
    this.dialogRef.close();
  }
}
