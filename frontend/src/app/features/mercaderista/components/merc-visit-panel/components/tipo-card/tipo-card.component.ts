import { Component, Input, Output, EventEmitter, signal, inject, ElementRef, ViewChild, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../../../../core/services/api.service';
import { OfflineQueueService } from '../../../../services/offline-queue.service';
import { ConfirmService } from '../../../../../../shared/components/confirm-dialog/confirm.service';
import { ConfirmDialogComponent } from '../../../../../../shared/components/confirm-dialog/confirm-dialog.component';

export interface FotoItem {
  id_foto: number | string;
  url: string;
  estado?: string;
  tipo_foto: string;
  comentario?: string;
  pair_id?: string;
  sub?: string;
}

@Component({
  selector: 'app-tipo-card',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatProgressSpinnerModule, FormsModule, ConfirmDialogComponent],
  template: `
    <div class="bg-white dark:bg-slate-900 border rounded-3xl p-4 shadow-sm flex flex-col gap-3 transition-all"
      [ngClass]="{
        'border-emerald-400': fotos.length > 0,
        'border-slate-100 dark:border-white/5': fotos.length === 0
      }">

      <!-- Header -->
      <div class="flex items-start gap-3">
        <div class="shrink-0 w-9 h-9 rounded-lg flex items-center justify-center"
          [style.background-color]="color + '1A'">
          <mat-icon [style.color]="color" class="!text-lg">{{ icono }}</mat-icon>
        </div>
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <span class="text-[13px] font-bold text-slate-700 dark:text-slate-100">{{ titulo }}</span>
            @if (fotos.length > 0) {
              <span class="text-[10px] font-black px-2 py-0.5 rounded-full"
                [style.background-color]="color + '1A'"
                [style.color]="color">
                {{ fotos.length }}
              </span>
            }
          </div>
          <p class="text-[11px] text-slate-400 dark:text-slate-500 mt-0.5">{{ desc }}</p>
        </div>
        <!-- Comment toggle -->
        <button (click)="showComment.set(!showComment())"
          class="shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-colors"
          [ngClass]="!showComment() ? 'bg-slate-100 dark:bg-white/5' : ''"
          [style.background-color]="showComment() ? color + '1A' : ''">
          <mat-icon class="!text-base"
            [style.color]="showComment() ? color : ''">
            {{ comentario() ? 'comment' : 'comment_outlined' }}
          </mat-icon>
        </button>
      </div>

      <!-- Loading Spinner for Categories -->
      @if (loadingCategorias) {
        <div class="flex items-center justify-center py-2">
          <mat-spinner diameter="20"></mat-spinner>
          <span class="text-[10px] text-slate-400 ml-2">Cargando categorías...</span>
        </div>
      }

      <!-- Category Selector (APK: dropdown de categorías antes de tomar fotos) -->
      @if (categorias.length > 0) {
        <div class="flex items-center gap-2 px-3 py-2 border rounded-lg text-xs"
          [style.border-color]="color + '66'">
          <mat-icon class="!text-sm" [style.color]="color">category</mat-icon>
          <span class="font-semibold text-slate-600 dark:text-slate-300">Categoría:</span>
          <select [(ngModel)]="selectedCategory" (ngModelChange)="onCategoryChange($event)"
            class="flex-1 bg-transparent outline-none text-xs font-bold text-slate-800 dark:text-slate-100 cursor-pointer">
            @for (cat of categorias; track cat) {
              <option [value]="cat">{{ cat }}</option>
            }
          </select>
        </div>
      }

      <!-- Thumbnail Grid -->
      @if (fotos.length > 0) {
        <div class="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1">
          @for (f of fotos; track f.id_foto) {
            <div class="relative shrink-0 w-[70px] h-[70px] rounded-xl overflow-hidden bg-slate-100 dark:bg-slate-950 group cursor-pointer"
              (click)="onViewPhoto.emit(f)">
              <img [src]="f.url" class="w-full h-full object-cover" loading="lazy" decoding="async" onerror="this.style.opacity=0.2">
              <!-- Sync status -->
              <div class="absolute bottom-1 right-1 w-5 h-5 rounded-md bg-black/50 flex items-center justify-center">
                <mat-icon class="!text-[10px] !w-[10px] !h-[10px]"
                  [class.text-amber-400]="f.estado === 'Pendiente'"
                  [class.text-emerald-400]="f.estado !== 'Pendiente'">
                  {{ f.estado === 'Pendiente' ? 'cloud_queue' : 'cloud_done' }}
                </mat-icon>
              </div>
              <!-- Delete button -->
              <button (click)="$event.stopPropagation(); onDelete.emit(f)"
                class="absolute top-1 right-1 w-5 h-5 rounded-full bg-red-500 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                <mat-icon class="!text-[11px] !w-[11px] !h-[11px] text-white">close</mat-icon>
              </button>
              <!-- Comment indicator -->
              @if (f.comentario) {
                <div class="absolute bottom-1 left-1 w-5 h-5 rounded-md flex items-center justify-center"
                  [style.background-color]="color">
                  <mat-icon class="!text-[10px] !w-[10px] !h-[10px] text-white">chat_bubble_outline</mat-icon>
                </div>
              }
              <!-- Rejected overlay -->
              @if (f.estado === 'Rechazada') {
                <div class="absolute inset-0 bg-orange-500/40 border-2 border-orange-500 rounded-xl flex items-center justify-center">
                  <mat-icon class="text-white !text-xl">warning_amber</mat-icon>
                </div>
              }
            </div>
          }
        </div>
      }

      <!-- Upload Button -->
      <button (click)="triggerUpload()" [disabled]="uploading()"
        class="w-full flex items-center justify-center gap-1.5 py-2.5 rounded-xl text-white text-[11px] font-bold active:scale-95 transition-all disabled:opacity-50"
        [style.background-color]="color">
        @if (uploading()) {
          <mat-spinner diameter="14" color="accent"></mat-spinner>
          <span>Subiendo...</span>
        } @else {
          <mat-icon class="!text-sm">add_a_photo</mat-icon>
          <span>Subir Foto</span>
        }
      </button>

      <!-- Comment field -->
      @if (showComment()) {
        <textarea [(ngModel)]="commentText" (ngModelChange)="onCommentChange()"
          placeholder="Observaciones de esta sección..."
          rows="2"
          class="w-full text-xs bg-slate-50 dark:bg-white/5 border rounded-xl px-3 py-2 outline-none resize-none"
          [style.border-color]="color + '66'"></textarea>
      }

      <!-- Pending sync indicator -->
      @if (pendingCount() > 0) {
        <div class="flex items-center gap-1.5 text-amber-500">
          <mat-icon class="!text-[12px] !w-[12px] !h-[12px]">cloud_queue</mat-icon>
          <span class="text-[10px] font-medium">{{ pendingCount() }} pendiente(s) de sync</span>
        </div>
      }

      <!-- Preview modal -->
      @if (previewSrc()) {
        <div class="relative rounded-2xl overflow-hidden bg-slate-100 dark:bg-slate-800 border-2" [style.border-color]="color">
          <img [src]="previewSrc()" class="w-full h-32 object-contain" alt="Preview">
          <div class="absolute bottom-2 inset-x-2 flex gap-2">
            <button (click)="confirmUpload()"
              class="flex-1 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-[10px] font-black uppercase tracking-widest">Confirmar</button>
            <button (click)="cancelPreview()"
              class="flex-1 py-2 rounded-xl bg-slate-200 dark:bg-white/10 text-slate-500 text-[10px] font-black uppercase tracking-widest">Cancelar</button>
          </div>
        </div>
      }

      <input type="file" #fileInput accept="image/*" capture="environment" class="hidden" (change)="onFileSelected($event)">
    </div>
  `,
  styles: [`:host { display: block; }`]
})
export class TipoCardComponent implements OnChanges {
  @Input() titulo: string = '';
  @Input() icono: string = 'photo_camera';
  @Input() desc: string = '';
  @Input() color: string = '#3b82f6';
  @Input() fotos: FotoItem[] = [];
  @Input() tipoFoto: string = '';
  @Input() visitaId!: number | string;
  @Input() chainId: string | null = null;
  @Input() seccionComentario: string = '';
  /** Categorías disponibles para el selector (cargadas dinámicamente desde productos del cliente) */
  @Input() categorias: string[] = [];
  /** Indica si las categorías aún se están cargando del backend. Muestra spinner y bloquea upload. */
  @Input() loadingCategorias: boolean = false;
  @Output() fotoSubida = new EventEmitter<void>();
  @Output() onDelete = new EventEmitter<FotoItem>();
  @Output() onViewPhoto = new EventEmitter<FotoItem>();
  @Output() onCommentChangeEmit = new EventEmitter<string>();

  private api = inject(ApiService);
  private offline = inject(OfflineQueueService);
  private snack = inject(MatSnackBar);
  private confirmSvc = inject(ConfirmService);

  @ViewChild('fileInput') fileInput!: ElementRef<HTMLInputElement>;

  uploading = signal(false);
  showComment = signal(false);
  commentText = '';
  comentario(): boolean { return this.commentText?.length > 0; }
  previewSrc = signal<string | null>(null);
  private pendingFile: File | null = null;
  selectedCategory: string = '';

  pendingCount = signal(0);

  ngOnChanges(changes: SimpleChanges) {
    this.pendingCount.set(this.fotos.filter(f => f.estado === 'Pendiente').length);
    if (this.seccionComentario) {
      this.commentText = this.seccionComentario;
    }
    // Inicializar categoría seleccionada si hay categorías disponibles
    if (changes['categorias'] && this.categorias.length > 0) {
      if (!this.selectedCategory || !this.categorias.includes(this.selectedCategory)) {
        this.selectedCategory = this.categorias[0];
      }
    }
  }

  onCategoryChange(cat: string) {
    this.selectedCategory = cat;
  }

  triggerUpload() {
    // Bloquear si las categorías aún se están cargando
    if (this.loadingCategorias) {
      this.snack.open('Esperá a que carguen las categorías...', 'OK', { duration: 2000 });
      return;
    }
    // Validar que haya categoría seleccionada si hay categorías disponibles
    if (this.categorias.length > 0 && !this.selectedCategory) {
      this.snack.open('Seleccioná una categoría antes de subir la foto.', 'OK', { duration: 3000 });
      return;
    }
    this.fileInput?.nativeElement?.click();
  }

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    this.pendingFile = file;
    const reader = new FileReader();
    reader.onload = () => {
      this.previewSrc.set(reader.result as string);
    };
    reader.readAsDataURL(file);
    input.value = '';
  }

  confirmUpload() {
    if (!this.pendingFile) return;
    this.doUpload(this.pendingFile);
    this.cancelPreview();
  }

  cancelPreview() {
    this.previewSrc.set(null);
    this.pendingFile = null;
  }

  onCommentChange() {
    this.onCommentChangeEmit.emit(this.commentText);
  }

  private async doUpload(file: File) {
    this.uploading.set(true);
    try {
      const formFields: Record<string, string> = { tipo_foto: this.tipoFoto };
      if (this.selectedCategory) {
        formFields['categoria'] = this.selectedCategory;
      }

      if (this.chainId) {
        await this.offline.addChainStep(this.chainId, {
          kind: 'foto',
          url: `/api/merc/visitas/${this.visitaId}/fotos`,
          isMultipart: true,
          formFields: formFields,
          fileBlob: file,
          fileName: file.name
        });
        this.snack.open('Foto guardada — se sincronizará al reconectar', 'OK', { duration: 2500 });
      } else {
        await this.offline.enqueuePhoto(this.visitaId as number, this.tipoFoto, file);
        this.snack.open('Foto subida', 'OK', { duration: 2000 });
      }
      this.fotoSubida.emit();
    } catch (e) {
      this.snack.open('Error al subir foto', 'OK', { duration: 3000 });
    } finally {
      this.uploading.set(false);
    }
  }
}
