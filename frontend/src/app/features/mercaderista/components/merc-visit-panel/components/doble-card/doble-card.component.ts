import { Component, Input, Output, EventEmitter, signal, inject, ElementRef, ViewChild, SimpleChanges, OnChanges } from '@angular/core';
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

export interface FotoPair {
  pairId: string;
  antes: FotoItem | null;
  despues: FotoItem | null;
}

@Component({
  selector: 'app-doble-card',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatProgressSpinnerModule, FormsModule, ConfirmDialogComponent],
  template: `
    <div class="bg-white dark:bg-slate-900 border rounded-3xl p-4 shadow-sm flex flex-col gap-3 transition-all border-slate-100 dark:border-white/5">

      <!-- Header -->
      <div class="flex items-start gap-3">
        <div class="shrink-0 w-9 h-9 rounded-lg flex items-center justify-center"
          [style.background-color]="color + '1A'">
          <mat-icon [style.color]="color" class="!text-lg">{{ icono }}</mat-icon>
        </div>
        <div class="flex-1 min-w-0">
          <span class="text-[13px] font-bold text-slate-700 dark:text-slate-100">{{ titulo }}</span>
          <p class="text-[11px] text-slate-400 dark:text-slate-500 mt-0.5">
            {{ countAntes() }} antes · {{ countDespues() }} después
          </p>
        </div>
        <span class="text-[10px] text-slate-300 dark:text-slate-600">{{ pairs.length }} anaqueles</span>
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

      <!-- Category Selector (if categories provided) -->
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

      <!-- Tab Selectors: Antes / Después / Mixto -->
      <div class="flex gap-2">
        @for (tab of tabs; track tab.index; let i = $index) {
          <button (click)="activeTab.set(i)"
            class="flex-1 py-1.5 rounded-xl text-[11px] font-bold flex items-center justify-center gap-1 transition-all"
            [ngClass]="activeTab() === i ? 'text-white' : 'bg-slate-100 dark:bg-white/5 text-slate-500'"
            [style.background-color]="activeTab() === i ? color : ''">
            {{ tab.label }}
            @if (tab.count > 0) {
              <span class="px-1.5 py-0.5 rounded-lg text-[9px] font-black"
                [ngClass]="activeTab() === i ? 'bg-white/20' : ''"
                [style.background-color]="activeTab() !== i ? color + '1A' : ''"
                [style.color]="activeTab() !== i ? color : ''">
                {{ tab.count }}
              </span>
            }
          </button>
        }
      </div>

      <!-- TAB: Antes -->
      @if (activeTab() === 0) {
        <div class="space-y-3">
          <p class="text-[11px] text-slate-400 dark:text-slate-500">
            Captura fotos del ANTES de la gestión para {{ titulo }}.
          </p>
          <div class="flex gap-2">
            <button (click)="openCameraBurst('antes')"
              class="flex-1 py-2 rounded-xl text-white text-[11px] font-bold flex items-center justify-center gap-1.5 active:scale-95 transition-all"
              [style.background-color]="color">
              <mat-icon class="!text-sm">camera_alt</mat-icon>
              Cámara Ráfaga
            </button>
            <button (click)="openGalleryMultiple('antes')"
              class="flex-1 py-2 rounded-xl border-1.5 text-[11px] font-bold flex items-center justify-center gap-1.5 active:scale-95 transition-all"
              [style.border-color]="color"
              [style.color]="color"
              style="border-width: 1.5px;">
              <mat-icon class="!text-sm">photo_library</mat-icon>
              Galería
            </button>
          </div>
          @if (blockAntes.length > 0) {
            <div class="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1">
              @for (f of blockAntes; track f.id_foto) {
                <div class="relative shrink-0 w-[70px] h-[70px] rounded-xl overflow-hidden bg-slate-100 dark:bg-slate-950 group cursor-pointer"
                  (click)="onViewPhoto.emit(f)">
                  <img [src]="f.url" class="w-full h-full object-cover" loading="lazy" decoding="async" onerror="this.style.opacity=0.2">
                  <button (click)="$event.stopPropagation(); onDelete.emit(f)"
                    class="absolute top-1 right-1 w-5 h-5 rounded-full bg-red-500 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                    <mat-icon class="!text-[11px] !w-[11px] !h-[11px] text-white">close</mat-icon>
                  </button>
                  <div class="absolute bottom-1 right-1 w-5 h-5 rounded-md bg-black/50 flex items-center justify-center">
                    <mat-icon class="!text-[10px] !w-[10px] !h-[10px]"
                      [class.text-amber-400]="f.estado === 'Pendiente'"
                      [class.text-emerald-400]="f.estado !== 'Pendiente'">
                      {{ f.estado === 'Pendiente' ? 'cloud_queue' : 'cloud_done' }}
                    </mat-icon>
                  </div>
                </div>
              }
            </div>
          }
        </div>
      }

      <!-- TAB: Después -->
      @if (activeTab() === 1) {
        <div class="space-y-3">
          <div class="flex items-center gap-1">
            <p class="text-[11px] text-slate-400 dark:text-slate-500">
              Captura fotos del DESPUÉS de la gestión.
            </p>
            @if (despuesObligatorio) {
              <span class="text-[10px] font-bold text-red-500">(obligatorio)</span>
            }
          </div>
          <div class="flex gap-2">
            <button (click)="openCameraBurst('despues')"
              class="flex-1 py-2 rounded-xl text-white text-[11px] font-bold flex items-center justify-center gap-1.5 active:scale-95 transition-all"
              [style.background-color]="color">
              <mat-icon class="!text-sm">camera_alt</mat-icon>
              Cámara Ráfaga
            </button>
            <button (click)="openGalleryMultiple('despues')"
              class="flex-1 py-2 rounded-xl border-1.5 text-[11px] font-bold flex items-center justify-center gap-1.5 active:scale-95 transition-all"
              [style.border-color]="color"
              [style.color]="color"
              style="border-width: 1.5px;">
              <mat-icon class="!text-sm">photo_library</mat-icon>
              Galería
            </button>
          </div>
          @if (blockDespues.length > 0) {
            <div class="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1">
              @for (f of blockDespues; track f.id_foto) {
                <div class="relative shrink-0 w-[70px] h-[70px] rounded-xl overflow-hidden bg-slate-100 dark:bg-slate-950 group cursor-pointer"
                  (click)="onViewPhoto.emit(f)">
                  <img [src]="f.url" class="w-full h-full object-cover" loading="lazy" decoding="async" onerror="this.style.opacity=0.2">
                  <button (click)="$event.stopPropagation(); onDelete.emit(f)"
                    class="absolute top-1 right-1 w-5 h-5 rounded-full bg-red-500 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                    <mat-icon class="!text-[11px] !w-[11px] !h-[11px] text-white">close</mat-icon>
                  </button>
                  <div class="absolute bottom-1 right-1 w-5 h-5 rounded-md bg-black/50 flex items-center justify-center">
                    <mat-icon class="!text-[10px] !w-[10px] !h-[10px]"
                      [class.text-amber-400]="f.estado === 'Pendiente'"
                      [class.text-emerald-400]="f.estado !== 'Pendiente'">
                      {{ f.estado === 'Pendiente' ? 'cloud_queue' : 'cloud_done' }}
                    </mat-icon>
                  </div>
                </div>
              }
            </div>
          }
        </div>
      }

      <!-- TAB: Mixto -->
      @if (activeTab() === 2) {
        <div class="space-y-3">
          <p class="text-[11px] text-slate-400 dark:text-slate-500">
            Asociación directa de fotos de Antes y Después por anaquel.
          </p>

          @for (pair of pairs; track pair.pairId; let idx = $index) {
            <div class="flex items-center gap-2 py-1">
              <span class="text-[11px] font-bold text-slate-600 dark:text-slate-300 shrink-0">Anaquel {{ idx + 1 }}</span>
              <div class="flex-1"></div>

              <!-- ANTES thumbnail -->
              <div class="w-[80px] h-[48px] shrink-0">
                @if (pair.antes) {
                  <div class="relative w-full h-full rounded-md overflow-hidden bg-slate-100 cursor-pointer" (click)="onViewPhoto.emit(pair.antes)">
                    <img [src]="pair.antes.url" class="w-full h-full object-cover" loading="lazy" decoding="async">
                    <div class="absolute bottom-0.5 right-0.5 w-4 h-4 rounded bg-black/50 flex items-center justify-center">
                      <mat-icon class="!text-[8px] !w-[8px] !h-[8px] text-emerald-400">cloud_done</mat-icon>
                    </div>
                  </div>
                } @else {
                  <button (click)="captureMixed(pair.pairId, 'antes')"
                    class="w-full h-full rounded-md border flex flex-col items-center justify-center gap-0.5 transition-colors hover:bg-slate-50 dark:hover:bg-white/5"
                    [style.border-color]="color + '80'"
                    [style.color]="color"
                    style="border-width: 1px; border-style: dashed;">
                    <mat-icon class="!text-[14px] !w-[14px] !h-[14px]">camera_alt</mat-icon>
                    <span class="text-[8px] font-bold">Foto</span>
                  </button>
                }
              </div>

              <mat-icon class="!text-sm text-slate-300 shrink-0">arrow_forward</mat-icon>

              <!-- DESPUÉS thumbnail -->
              <div class="w-[80px] h-[48px] shrink-0">
                @if (pair.despues) {
                  <div class="relative w-full h-full rounded-md overflow-hidden bg-slate-100 cursor-pointer" (click)="onViewPhoto.emit(pair.despues)">
                    <img [src]="pair.despues.url" class="w-full h-full object-cover" loading="lazy" decoding="async">
                    <div class="absolute bottom-0.5 right-0.5 w-4 h-4 rounded bg-black/50 flex items-center justify-center">
                      <mat-icon class="!text-[8px] !w-[8px] !h-[8px] text-emerald-400">cloud_done</mat-icon>
                    </div>
                  </div>
                } @else {
                  <button (click)="captureMixed(pair.pairId, 'despues')"
                    [disabled]="!pair.antes"
                    class="w-full h-full rounded-md border flex flex-col items-center justify-center gap-0.5 transition-colors hover:bg-slate-50 dark:hover:bg-white/5 disabled:opacity-30"
                    [style.border-color]="color + '80'"
                    [style.color]="color"
                    style="border-width: 1px; border-style: dashed;">
                    <mat-icon class="!text-[14px] !w-[14px] !h-[14px]">camera_alt</mat-icon>
                    <span class="text-[8px] font-bold">Foto</span>
                  </button>
                }
              </div>
            </div>
          }

          <!-- Add new pair button -->
          <button (click)="addNewPair()"
            class="w-full py-2 rounded-xl text-white text-[11px] font-bold flex items-center justify-center gap-1.5 active:scale-95 transition-all"
            [style.background-color]="color">
            <mat-icon class="!text-sm">add_a_photo</mat-icon>
            Agregar Nuevo Anaquel (Mixto)
          </button>
        </div>
      }

      <!-- Comment field -->
      @if (showComment()) {
        <textarea [(ngModel)]="commentText" (ngModelChange)="onCommentChange()"
          placeholder="Observaciones de esta sección..."
          rows="2"
          class="w-full text-xs bg-slate-50 dark:bg-white/5 border rounded-xl px-3 py-2 outline-none resize-none"
          [style.border-color]="color + '66'"></textarea>
      }

      <!-- Hidden file inputs -->
      <input type="file" #fileInputBurst accept="image/*" capture="environment" class="hidden" multiple (change)="onBurstFilesSelected($event)">
      <input type="file" #fileInputGallery accept="image/*" class="hidden" multiple (change)="onGalleryFilesSelected($event)">
      <input type="file" #fileInputMixed accept="image/*" capture="environment" class="hidden" (change)="onMixedFileSelected($event)">

      <!-- Processing spinner -->
      @if (processing()) {
        <div class="flex items-center justify-center gap-2 py-3 text-slate-500">
          <mat-spinner diameter="20"></mat-spinner>
          <span class="text-xs font-medium">Procesando...</span>
        </div>
      }
    </div>
  `,
  styles: [`:host { display: block; }`]
})
export class DobleCardComponent {
  @Input() titulo: string = '';
  @Input() icono: string = 'photo_camera';
  @Input() color: string = '#3b82f6';
  @Input() tipo: string = '';
  @Input() fotos: FotoItem[] = [];
  @Input() categorias: string[] = [];
  /** Indica si las categorías aún se están cargando del backend. Muestra spinner y bloquea upload. */
  @Input() loadingCategorias: boolean = false;
  @Input() visitaId!: number | string;
  @Input() chainId: string | null = null;
  @Input() despuesObligatorio: boolean = false;
  @Input() seccionComentario: string = '';

  @Output() fotoSubida = new EventEmitter<void>();
  @Output() onDelete = new EventEmitter<FotoItem>();
  @Output() onViewPhoto = new EventEmitter<FotoItem>();
  @Output() onCommentChangeEmit = new EventEmitter<string>();

  private api = inject(ApiService);
  private offline = inject(OfflineQueueService);
  private snack = inject(MatSnackBar);

  @ViewChild('fileInputBurst') fileInputBurst!: ElementRef<HTMLInputElement>;
  @ViewChild('fileInputGallery') fileInputGallery!: ElementRef<HTMLInputElement>;
  @ViewChild('fileInputMixed') fileInputMixed!: ElementRef<HTMLInputElement>;

  activeTab = signal(0);
  showComment = signal(false);
  commentText = '';
  comentario(): boolean { return this.commentText?.length > 0; }
  selectedCategory: string = '';
  processing = signal(false);

  private _pendingPairId: string | null = null;
  private _pendingSub: string | null = null;

  tabs: { index: number; label: string; count: number }[] = [
    { index: 0, label: 'Antes', count: 0 },
    { index: 1, label: 'Después', count: 0 },
    { index: 2, label: 'Mixto', count: 0 },
  ];

  get blockAntes(): FotoItem[] {
    return this.fotos.filter(f => f.sub === 'antes' && !f.pair_id);
  }

  get blockDespues(): FotoItem[] {
    return this.fotos.filter(f => f.sub === 'despues' && !f.pair_id);
  }

  get pairs(): FotoPair[] {
    const pairMap = new Map<string, FotoPair>();
    const pairedFotos = this.fotos.filter(f => f.pair_id);

    for (const f of pairedFotos) {
      if (!pairMap.has(f.pair_id!)) {
        pairMap.set(f.pair_id!, { pairId: f.pair_id!, antes: null, despues: null });
      }
      const pair = pairMap.get(f.pair_id!)!;
      if (f.sub === 'antes') pair.antes = f;
      if (f.sub === 'despues') pair.despues = f;
    }

    // Sort pairs to keep order stable
    return Array.from(pairMap.values()).sort((a, b) => a.pairId.localeCompare(b.pairId));
  }

  countAntes(): number {
    return this.fotos.filter(f => f.sub === 'antes').length;
  }

  countDespues(): number {
    return this.fotos.filter(f => f.sub === 'despues').length;
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes['fotos'] || changes['categorias']) {
      this.tabs = [
        { index: 0, label: 'Antes', count: this.blockAntes.length },
        { index: 1, label: 'Después', count: this.blockDespues.length },
        { index: 2, label: 'Mixto', count: this.pairs.length },
      ];

      if (this.categorias.length > 0 && !this.selectedCategory) {
        this.selectedCategory = this.categorias[0];
      } else if (this.categorias.length > 0 && !this.categorias.includes(this.selectedCategory)) {
        this.selectedCategory = this.categorias[0];
      }
    }
    if (changes['seccionComentario'] && this.seccionComentario) {
      this.commentText = this.seccionComentario;
    }
  }

  onCategoryChange(cat: string) {
    this.selectedCategory = cat;
  }

  onCommentChange() {
    this.onCommentChangeEmit.emit(this.commentText);
  }

  // ─── Camera Burst (capture="environment" multiple) ───
  openCameraBurst(sub: string) {
    if (this.loadingCategorias) { this.snack.open('Esperá a que carguen las categorías...', 'OK', { duration: 2000 }); return; }
    this._pendingSub = sub;
    this._pendingPairId = null;
    this.fileInputBurst?.nativeElement?.click();
  }

  onBurstFilesSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    const files = input.files;
    if (!files?.length) return;
    this.processMultipleUpload(Array.from(files), this._pendingSub || 'antes');
    input.value = '';
  }

  // ─── Gallery Multiple ───
  openGalleryMultiple(sub: string) {
    if (this.loadingCategorias) { this.snack.open('Esperá a que carguen las categorías...', 'OK', { duration: 2000 }); return; }
    this._pendingSub = sub;
    this._pendingPairId = null;
    this.fileInputGallery?.nativeElement?.click();
  }

  onGalleryFilesSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    const files = input.files;
    if (!files?.length) return;
    this.processMultipleUpload(Array.from(files), this._pendingSub || 'antes');
    input.value = '';
  }

  // ─── Mixto (paired capture) ───
  captureMixed(pairId: string, sub: string) {
    if (this.loadingCategorias) { this.snack.open('Esperá a que carguen las categorías...', 'OK', { duration: 2000 }); return; }
    this._pendingPairId = pairId;
    this._pendingSub = sub;
    this.fileInputMixed?.nativeElement?.click();
  }

  addNewPair() {
    if (this.loadingCategorias) { this.snack.open('Esperá a que carguen las categorías...', 'OK', { duration: 2000 }); return; }
    const pairId = `pair_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
    // First capture: antes
    this._pendingPairId = pairId;
    this._pendingSub = 'antes';
    this.fileInputMixed?.nativeElement?.click();
  }

  async onMixedFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    this.processing.set(true);
    try {
      await this.doUpload(file, this._pendingSub || 'antes', this._pendingPairId || undefined);
      this.snack.open('Foto subida', 'OK', { duration: 2000 });
    } catch (e) {
      this.snack.open('Error al subir foto', 'OK', { duration: 3000 });
    } finally {
      this.processing.set(false);
      input.value = '';
    }
  }

  // ─── Upload logic ───
  private async processMultipleUpload(files: File[], sub: string) {
    this.processing.set(true);
    try {
      for (const file of files) {
        await this.doUpload(file, sub);
      }
      this.snack.open(`${files.length} foto(s) guardada(s)`, 'OK', { duration: 2000 });
    } catch (e) {
      this.snack.open('Error al procesar fotos', 'OK', { duration: 3000 });
    } finally {
      this.processing.set(false);
    }
  }

  private async doUpload(file: File, sub: string, pairId?: string) {
    const tipoFoto = pairId ? `${this.tipo}_mixto` : `${this.tipo}_${sub}`;
    // Include sub and pair_id in the form fields for the backend to parse
    const formFields: Record<string, string> = {
      tipo_foto: tipoFoto,
      sub: sub,
    };
    if (pairId) {
      formFields['pair_id'] = pairId;
    }
    if (this.selectedCategory) {
      formFields['categoria'] = this.selectedCategory;
    }

    if (this.chainId) {
      await this.offline.addChainStep(this.chainId, {
        kind: 'foto',
        url: `/api/merc/visitas/${this.visitaId}/fotos`,
        isMultipart: true,
        formFields,
        fileBlob: file,
        fileName: file.name
      });
    } else {
      // For online, use the standard upload
      await this.offline.enqueuePhoto(this.visitaId as number, tipoFoto, file);
    }
    this.fotoSubida.emit();
  }
}
