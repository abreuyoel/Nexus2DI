import { Component, Input, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';
import { ApiService } from '../../../../../../core/services/api.service';
import { OfflineQueueService } from '../../../../services/offline-queue.service';

@Component({
  selector: 'app-photo-grid',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatProgressSpinnerModule],
  template: `
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      @for (tipo of tipos(); track tipo.codigo) {
        <div class="bg-white dark:bg-slate-900 border rounded-3xl p-4 shadow-sm flex flex-col gap-3 transition-all"
          [ngClass]="tipo.fotos.length > 0 ? 'border-emerald-400 dark:border-emerald-500/40' : 'border-slate-100 dark:border-white/5'">

          <!-- Header -->
          <div class="flex items-start justify-between gap-2">
            <div class="flex flex-col">
              <span class="text-[8px] font-black text-slate-400 uppercase tracking-widest mb-0.5">Tipo de Foto</span>
              <h4 class="text-[12px] font-black text-slate-700 dark:text-slate-100 leading-tight">{{ tipo.label }}</h4>
            </div>
            <span class="shrink-0 text-[10px] font-black px-2 py-0.5 rounded-full"
              [class]="tipo.fotos.length > 0 ? 'bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-400' : 'bg-slate-100 dark:bg-white/5 text-slate-400'">
              {{ tipo.fotos.length }}
            </span>
          </div>

          <!-- Miniaturas -->
          @if (tipo.fotos.length > 0) {
            <div class="grid grid-cols-3 gap-2">
              @for (f of tipo.fotos; track f.id_foto) {
                <div class="relative aspect-square rounded-xl overflow-hidden bg-slate-100 dark:bg-slate-950 group">
                  <img [src]="f.url" class="w-full h-full object-cover" loading="lazy" decoding="async" onerror="this.style.opacity=0.2">
                  <button (click)="deleteFoto(tipo, f)"
                    class="absolute top-1 right-1 w-6 h-6 rounded-lg bg-rose-600/90 hover:bg-rose-600 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                    <mat-icon class="!text-[14px] !w-[14px] !h-[14px]">close</mat-icon>
                  </button>
                  @if (f.estado === 'Rechazada') {
                    <span class="absolute bottom-0 inset-x-0 bg-rose-600 text-white text-[7px] font-black text-center py-0.5">RECHAZADA</span>
                  } @else if (f.estado === 'Aprobada') {
                    <span class="absolute bottom-0 inset-x-0 bg-emerald-600 text-white text-[7px] font-black text-center py-0.5">APROBADA</span>
                  }
                </div>
              }
            </div>
          }

          <!-- Botones Cámara / Galería -->
          <div class="flex gap-2 mt-auto">
            <button (click)="pick(tipo, 'cam')" [disabled]="isUploading(tipo.codigo)"
              class="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white text-[10px] font-black uppercase tracking-widest active:scale-95 transition-all">
              <mat-icon class="!text-sm">photo_camera</mat-icon> Cámara
            </button>
            @if (!tipo.solo_camara) {
              <button (click)="pick(tipo, 'gal')" [disabled]="isUploading(tipo.codigo)"
                class="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl bg-slate-100 dark:bg-white/5 hover:bg-slate-200 dark:hover:bg-white/10 disabled:opacity-50 text-slate-600 dark:text-slate-300 text-[10px] font-black uppercase tracking-widest active:scale-95 transition-all">
                <mat-icon class="!text-sm">photo_library</mat-icon> Galería
              </button>
            }
          </div>

          @if (isUploading(tipo.codigo)) {
            <div class="flex items-center justify-center gap-2 text-primary-500">
              <mat-spinner diameter="16"></mat-spinner>
              <span class="text-[9px] font-black uppercase tracking-widest">Subiendo...</span>
            </div>
          }

          <!-- Inputs ocultos: cámara (capture) y galería (múltiple) -->
          <input type="file" [id]="'cam-'+tipo.codigo" accept="image/*" capture="environment" class="hidden" (change)="onFiles($event, tipo)">
          <input type="file" [id]="'gal-'+tipo.codigo" accept="image/*" multiple class="hidden" (change)="onFiles($event, tipo)">
        </div>
      }
    </div>
  `,
  styles: [`:host { display: block; }`]
})
export class PhotoGridComponent implements OnInit {
  @Input() visitaId!: number;

  private api = inject(ApiService);
  private offline = inject(OfflineQueueService);
  private snack = inject(MatSnackBar);

  tipos = signal<any[]>([]);
  uploading = signal<Set<string>>(new Set());

  ngOnInit() { this.loadFotos(); }

  loadFotos() {
    this.api.getFotosVisita(this.visitaId).subscribe(res => {
      this.tipos.set((res.tipos || []).map((t: any) => ({ ...t, fotos: t.fotos || [] })));
    });
  }

  pick(tipo: any, source: 'cam' | 'gal') {
    const input = document.getElementById((source === 'cam' ? 'cam-' : 'gal-') + tipo.codigo) as HTMLInputElement;
    input?.click();
  }

  isUploading(codigo: string): boolean { return this.uploading().has(codigo); }

  async onFiles(event: Event, tipo: any) {
    const input = event.target as HTMLInputElement;
    const files = Array.from(input.files || []);
    input.value = '';
    if (!files.length) return;

    this.uploading.update(s => { s.add(tipo.codigo); return new Set(s); });
    try {
      for (const file of files) {
        await this.offline.enqueuePhoto(this.visitaId, tipo.codigo, file);
      }
    } finally {
      setTimeout(() => {
        this.uploading.update(s => { s.delete(tipo.codigo); return new Set(s); });
        this.loadFotos();
      }, 900);
    }
  }

  deleteFoto(tipo: any, foto: any) {
    if (!confirm('¿Eliminar esta foto?')) return;
    this.tipos.update(list => list.map(t => t.codigo === tipo.codigo
      ? { ...t, fotos: t.fotos.filter((f: any) => f.id_foto !== foto.id_foto) } : t));
    this.api.deleteMercFoto(foto.id_foto).subscribe({
      next: () => this.snack.open('Foto eliminada', 'OK', { duration: 1500 }),
      error: () => { this.snack.open('No se pudo eliminar', 'OK', { duration: 2500 }); this.loadFotos(); },
    });
  }
}
