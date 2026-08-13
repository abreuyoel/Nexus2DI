import { Component, Input, OnInit, signal, inject, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';
import { ApiService } from '../../../../../../core/services/api.service';
import { OfflineQueueService } from '../../../../services/offline-queue.service';
import { ConfirmService } from '../../../../../../shared/components/confirm-dialog/confirm.service';
import { ConfirmDialogComponent } from '../../../../../../shared/components/confirm-dialog/confirm-dialog.component';

// Colores por tipo de foto (igual que la APK)
const COLOR_MAP: Record<string, string> = {
  gestion_antes: 'border-blue-400 dark:border-blue-500/40',
  gestion_despues: 'border-green-400 dark:border-green-500/40',
  precios: 'border-orange-400 dark:border-orange-500/40',
  exhibicion_antes: 'border-purple-400 dark:border-purple-500/40',
  activacion: 'border-red-400 dark:border-red-500/40',
  desactivacion: 'border-red-400 dark:border-red-500/40',
  exhibicion_despues: 'border-purple-400 dark:border-purple-500/40',
  pop_antes: 'border-yellow-400 dark:border-yellow-500/40',
  pop_despues: 'border-yellow-400 dark:border-yellow-500/40',
};

// Tipos obligatorios
const OBLIGATORIOS = new Set(['activacion', 'desactivacion']);

@Component({
  selector: 'app-photo-grid',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatProgressSpinnerModule, ConfirmDialogComponent],
  template: `
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      @for (tipo of tipos(); track tipo.codigo) {
        <div class="bg-white dark:bg-slate-900 border rounded-3xl p-4 shadow-sm flex flex-col gap-3 transition-all"
          [class]="tipo.fotos.length > 0 ? 'border-emerald-400 dark:border-emerald-500/40' : borderColor(tipo.codigo)">

          <!-- Header -->
          <div class="flex items-start justify-between gap-2">
            <div class="flex flex-col min-w-0">
              <div class="flex items-center gap-1.5">
                <h4 class="text-[12px] font-black text-slate-700 dark:text-slate-100 leading-tight">{{ tipo.label }}</h4>
                @if (isObligatorio(tipo.codigo)) {
                  <span class="shrink-0 text-[9px] font-black text-red-500 bg-red-50 dark:bg-red-950 px-1.5 py-0.5 rounded-md uppercase">Obligatorio</span>
                }
              </div>
              @if (isObligatorio(tipo.codigo) && tipo.fotos.length === 0) {
                <span class="text-[9px] text-red-500 font-medium mt-0.5">⚠ Falta foto obligatoria</span>
              }
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

          <!-- Botón Subir Foto (web: solo file picker) -->
          <div class="mt-auto">
            <button (click)="pick(tipo)" [disabled]="isUploading(tipo.codigo)"
              class="w-full flex items-center justify-center gap-1.5 py-2.5 rounded-xl bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white text-[10px] font-black uppercase tracking-widest active:scale-95 transition-all">
              <mat-icon class="!text-sm">add_a_photo</mat-icon> Subir Foto
            </button>
          </div>

          <!-- Preview antes de confirmar -->
          @if (previewSrc() && previewTipo() === tipo.codigo) {
            <div class="relative rounded-2xl overflow-hidden bg-slate-100 dark:bg-slate-800">
              <img [src]="previewSrc()" class="w-full h-32 object-contain" alt="Preview">
              <div class="absolute bottom-2 inset-x-2 flex gap-2">
                <button (click)="confirmUpload()"
                  class="flex-1 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-[10px] font-black uppercase tracking-widest">Confirmar</button>
                <button (click)="cancelPreview()"
                  class="flex-1 py-2 rounded-xl bg-slate-200 dark:bg-white/10 text-slate-500 text-[10px] font-black uppercase tracking-widest">Cancelar</button>
              </div>
            </div>
          }

          @if (isUploading(tipo.codigo)) {
            <div class="flex items-center justify-center gap-2 text-primary-500">
              <mat-spinner diameter="16"></mat-spinner>
              <span class="text-[9px] font-black uppercase tracking-widest">Subiendo...</span>
            </div>
          }

          <input type="file" [id]="'foto-'+tipo.codigo" accept="image/*" class="hidden" (change)="onFileSelected($event, tipo)">
        </div>
      }
    </div>
  `,
  styles: [`:host { display: block; }`]
})
export class PhotoGridComponent implements OnInit {
  @Input() visitaId!: number | string;
  @Input() chainId: string | null = null;
  @Output() photosLoaded = new EventEmitter<any[]>();

  private api = inject(ApiService);
  private offline = inject(OfflineQueueService);
  private snack = inject(MatSnackBar);
  private confirmSvc = inject(ConfirmService);

  tipos = signal<any[]>([]);
  uploading = signal<Set<string>>(new Set());

  // Preview state
  previewSrc = signal<string | null>(null);
  previewTipo = signal<string | null>(null);
  private pendingFile: File | null = null;
  private pendingTipo: any = null;

  // Constantes
  readonly OBLIGATORIOS = OBLIGATORIOS;

  borderColor(codigo: string): string {
    return COLOR_MAP[codigo] || 'border-slate-100 dark:border-white/5';
  }

  isObligatorio(codigo: string): boolean {
    return OBLIGATORIOS.has(codigo);
  }

  ngOnInit() {
    this.loadFotos();
  }

  async loadFotos() {
    if (this.chainId) {
      const chain = await this.offline.getChain(this.chainId);
      if (chain) {
        if (this.tipos().length === 0) {
          const labelMap: Record<string, string> = {
            gestion_antes: 'Gestión (Antes)',
            gestion_despues: 'Gestión (Después)',
            precios: 'Precios',
            exhibicion_antes: 'Exhibición Adicional (Antes)',
            exhibicion_despues: 'Exhibición Adicional (Después)',
            pop_antes: 'Material POP (Antes)',
            pop_despues: 'Material POP (Después)',
            activacion: 'Activación',
            desactivacion: 'Desactivación'
          };
          this.tipos.set(Object.keys(COLOR_MAP).map(code => ({
            codigo: code,
            label: labelMap[code] || code,
            fotos: []
          })));
        }

        const offlinePhotos = chain.steps
          .filter(s => s.kind === 'foto' && s.formFields?.['tipo_foto'])
          .map(s => ({
            id_foto: 'offline_' + s.stepIndex,
            estado: 'Pendiente',
            url: s.fileBlob ? URL.createObjectURL(s.fileBlob) : '',
            tipo_foto: s.formFields?.['tipo_foto']
          }));

        this.tipos.update(list => list.map(t => {
          const fotos = offlinePhotos.filter(p => p.tipo_foto === t.codigo);
          return { ...t, fotos };
        }));

        this.photosLoaded.emit(this.tipos());
      }
      return;
    }

    this.api.getFotosVisita(this.visitaId as number).subscribe(res => {
      const list = (res.tipos || []).map((t: any) => ({ ...t, fotos: t.fotos || [] }));
      this.tipos.set(list);
      this.photosLoaded.emit(list);
    });
  }

  pick(tipo: any) {
    const input = document.getElementById('foto-' + tipo.codigo) as HTMLInputElement;
    input?.click();
  }

  isUploading(codigo: string): boolean { return this.uploading().has(codigo); }

  onFileSelected(event: Event, tipo: any) {
    const input = event.target as HTMLInputElement;
    const files = input.files;
    if (!files?.length) return;
    this.pendingFile = files[0];
    this.pendingTipo = tipo;
    // Preview
    const reader = new FileReader();
    reader.onload = () => {
      this.previewSrc.set(reader.result as string);
      this.previewTipo.set(tipo.codigo);
    };
    reader.readAsDataURL(files[0]);
    input.value = '';
  }

  confirmUpload() {
    if (!this.pendingFile || !this.pendingTipo) return;
    this.doUpload(this.pendingFile, this.pendingTipo);
    this.cancelPreview();
  }

  cancelPreview() {
    this.previewSrc.set(null);
    this.previewTipo.set(null);
    this.pendingFile = null;
    this.pendingTipo = null;
  }

  private async doUpload(file: File, tipo: any) {
    this.uploading.update(s => { s.add(tipo.codigo); return new Set(s); });
    try {
      if (this.chainId) {
        await this.offline.addChainStep(this.chainId, {
          kind: 'foto', url: `/api/merc/visitas/${this.visitaId}/fotos`, isMultipart: true,
          formFields: { tipo_foto: tipo.codigo },
          fileBlob: file, fileName: file.name
        });
        this.snack.open('Foto guardada — se sincronizará al reconectar', 'OK', { duration: 2500 });
      } else {
        await this.offline.enqueuePhoto(this.visitaId as number, tipo.codigo, file);
        this.snack.open('Foto subida', 'OK', { duration: 2000 });
      }
    } catch (e) {
      this.snack.open('Error al subir foto', 'OK', { duration: 3000 });
    } finally {
      this.uploading.update(s => { s.delete(tipo.codigo); return new Set(s); });
      this.loadFotos();
    }
  }

  async deleteFoto(tipo: any, foto: any) {
    const confirmed = await this.confirmSvc.confirm('¿Eliminar esta foto permanentemente?', {
      title: 'Eliminar Foto',
      confirmText: 'Eliminar',
      cancelText: 'Cancelar',
      danger: true,
    });
    if (!confirmed) return;

    if (this.chainId && String(foto.id_foto).startsWith('offline_')) {
      const stepIndex = Number(String(foto.id_foto).replace('offline_', ''));
      await this.offline.deleteChainStep(this.chainId, stepIndex);
      this.snack.open('Foto local eliminada', 'OK', { duration: 1500 });
      this.loadFotos();
      return;
    }

    this.tipos.update(list => list.map(t => t.codigo === tipo.codigo
      ? { ...t, fotos: t.fotos.filter((f: any) => f.id_foto !== foto.id_foto) } : t));
    this.api.deleteMercFoto(foto.id_foto).subscribe({
      next: () => {
        this.snack.open('Foto eliminada', 'OK', { duration: 1500 });
        this.loadFotos();
      },
      error: () => { this.snack.open('No se pudo eliminar', 'OK', { duration: 2500 }); this.loadFotos(); },
    });
  }
}
