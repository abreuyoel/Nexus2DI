import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { ApiService } from '../../core/services/api.service';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Observable } from 'rxjs';

@Component({
  selector: 'app-group-members-dialog',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatButtonModule, MatIconModule, MatProgressSpinnerModule],
  template: `
    <h2 mat-dialog-title class="flex items-center gap-2">
      <mat-icon class="text-primary-500">group</mat-icon>
      Miembros del Grupo
    </h2>
    <mat-dialog-content class="custom-scrollbar">
      @if (loading) {
        <div class="flex justify-center items-center py-8">
          <mat-spinner diameter="32"></mat-spinner>
        </div>
      } @else {
        <div class="space-y-3 pt-2">
          @for (m of miembros; track m.id_usuario) {
            <div class="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-100 dark:border-slate-700">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center text-primary-600 dark:text-primary-400 font-bold">
                  {{ (m.username || 'U').charAt(0).toUpperCase() }}
                </div>
                <div>
                  <div class="font-bold text-sm text-slate-800 dark:text-slate-200">{{ m.username }}</div>
                  <div class="text-xs text-slate-500 capitalize">{{ m.rol }}</div>
                </div>
              </div>
            </div>
          }
          @if (miembros.length === 0) {
            <div class="text-center text-slate-500 text-sm py-4">No hay miembros disponibles.</div>
          }
        </div>
      }
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button mat-dialog-close>Cerrar</button>
    </mat-dialog-actions>
  `,
  styles: []
})
export class GroupMembersDialogComponent {
  miembros: any[] = [];
  loading = true;

  constructor(
    private dialogRef: MatDialogRef<GroupMembersDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { idGrupo: number },
    private api: ApiService
  ) {
    this.api.getMiembrosGrupo(this.data.idGrupo).subscribe({
      next: (res) => {
        this.miembros = res;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
      }
    });
  }
}
