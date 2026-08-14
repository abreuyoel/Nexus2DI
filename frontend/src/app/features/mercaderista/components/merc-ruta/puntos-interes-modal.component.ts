import { Component, Input, Output, EventEmitter, inject, signal, computed, ElementRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ConfirmService } from '../../../../shared/components/confirm-dialog/confirm.service';

interface PdvClient {
  id_cliente: number;
  nombre: string;
  visitado: boolean;
  visita_id: number | null;
}

interface PdvGroup {
  id_punto: string;
  nombre: string;
  cadena: string;
  direccion: string;
  latitud?: number;
  longitud?: number;
  prioridad?: string;
  hasVisited: boolean;
  clients: PdvClient[];
}

const PRIORITY_COLORS: Record<string, { bg: string; text: string; border: string; dot: string }> = {
  Alta: { bg: 'bg-red-500/10', text: 'text-red-600', border: 'border-red-500/20', dot: 'bg-red-500' },
  Media: { bg: 'bg-amber-500/10', text: 'text-amber-600', border: 'border-amber-500/20', dot: 'bg-amber-500' },
  Baja: { bg: 'bg-slate-200 dark:bg-slate-800', text: 'text-slate-500 dark:text-slate-400', border: 'border-slate-200 dark:border-slate-700', dot: 'bg-slate-400' },
};

@Component({
  selector: 'app-puntos-interes-modal',
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule, MatButtonModule, MatProgressSpinnerModule, MatSnackBarModule],
  template: `
    <!-- Overlay backdrop -->
    <div class="fixed inset-0 z-[120] bg-black/60 backdrop-blur-sm animate-in fade-in duration-200"
         (click)="close.emit()">
    </div>

    <!-- Bottom Sheet -->
    <div class="fixed inset-x-0 bottom-0 z-[121] bg-white dark:bg-slate-900 rounded-t-[2rem] shadow-2xl max-h-[85vh] flex flex-col animate-in slide-in-from-bottom duration-300">
      <!-- Handle -->
      <div class="flex justify-center pt-3 pb-1">
        <div class="w-10 h-1 rounded-full bg-slate-300 dark:bg-slate-600"></div>
      </div>

      <!-- Header -->
      <div class="px-6 py-3 flex items-center justify-between border-b border-slate-100 dark:border-white/5">
        <div class="flex items-center gap-3 min-w-0">
          <div class="w-10 h-10 rounded-2xl bg-primary-500/10 text-primary-500 flex items-center justify-center shrink-0">
            <mat-icon>location_on</mat-icon>
          </div>
          <div class="min-w-0">
            <h3 class="font-black text-sm text-slate-800 dark:text-white truncate">📍 {{ rutaNombre }}</h3>
            <p class="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
              {{ pdvs.length }} punto(s) de interés
            </p>
          </div>
        </div>
        <button (click)="close.emit()"
                class="w-9 h-9 rounded-xl bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400 active:scale-95 transition-all">
          <mat-icon class="!text-lg">close</mat-icon>
        </button>
      </div>

      <!-- Search Bar -->
      <div class="px-4 pt-3 pb-1 shrink-0">
        <div class="relative">
          <mat-icon class="absolute left-3 top-1/2 -translate-y-1/2 !text-slate-400 !text-sm">search</mat-icon>
          <input type="text" [ngModel]="busqueda()" (ngModelChange)="busqueda.set($event)"
                 placeholder="Buscar PDV, cadena, dirección o cliente..."
                 class="w-full pl-9 pr-8 py-2.5 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-white/10 rounded-xl text-xs font-bold outline-none focus:ring-2 focus:ring-primary-500 transition-all text-slate-800 dark:text-white">
          @if (busqueda()) {
            <button (click)="busqueda.set('')" class="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-white">
              <mat-icon class="!text-sm">close</mat-icon>
            </button>
          }
        </div>
        @if (busqueda()) {
          <p class="text-[10px] text-slate-400 font-bold px-1 mt-1">
            Mostrando {{ pdvsFiltrados().length }} de {{ pdvs.length }} puntos
          </p>
        }
      </div>

      <!-- PDV List -->
      <div class="flex-grow overflow-y-auto px-4 py-3 space-y-3 custom-scrollbar">

        <!-- Aclaración: ruta activa — solo se pueden visitar PDVs de esta ruta -->
        <div class="bg-primary-500/10 border border-primary-500/20 rounded-xl p-3 flex items-start gap-2">
          <mat-icon class="!text-base text-primary-500 mt-0.5 shrink-0">info</mat-icon>
          <p class="text-[11px] font-medium text-primary-600 dark:text-primary-400 leading-relaxed">
            La ruta <strong>{{ rutaNombre }}</strong> está activa. Solo podés visitar PDVs de esta ruta hasta que la finalices.
          </p>
        </div>
        @if (pdvsFiltrados().length === 0) {
          <div class="py-16 text-center opacity-50">
            <mat-icon class="!text-5xl text-slate-300">{{ busqueda() ? 'search_off' : 'wrong_location' }}</mat-icon>
            <p class="text-xs font-black text-slate-400 uppercase tracking-widest mt-2">
              {{ busqueda() ? 'No se encontraron PDVs para esta búsqueda' : 'No hay PDVs en esta ruta' }}
            </p>
          </div>
        }

        @for (group of pdvsFiltrados(); track group.id_punto) {
          <div class="bg-slate-50 dark:bg-slate-800/50 rounded-2xl p-4 border border-slate-100 dark:border-white/5 space-y-3">

            <!-- Priority Badge -->
            @if (group.prioridad) {
              <div [class]="priorityColors(group.prioridad).bg + ' ' + priorityColors(group.prioridad).border + ' border rounded-full px-2.5 py-0.5 inline-flex items-center gap-1.5 self-start'">
                <span [class]="priorityColors(group.prioridad).dot + ' w-1.5 h-1.5 rounded-full'"></span>
                <span [class]="priorityColors(group.prioridad).text + ' text-[9px] font-black uppercase tracking-widest'">{{ group.prioridad }}</span>
              </div>
            }

            <!-- PDV Info Row -->
            <div class="flex items-start gap-3">
              <div [class]="statusColor(group).iconBg"
                   class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0">
                <mat-icon [class]="statusColor(group).iconColor + ' !text-lg'">{{ statusIcon(group) }}</mat-icon>
              </div>
              <div class="flex-grow min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                  <h4 class="font-bold text-sm text-slate-800 dark:text-white truncate">{{ group.nombre }}</h4>
                  <span [class]="statusColor(group).badgeBg + ' ' + statusColor(group).badgeText + ' text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full'">
                    {{ statusLabel(group) }}
                  </span>
                </div>
                @if (group.cadena) {
                  <p class="text-[10px] font-bold text-primary-500 dark:text-primary-400 uppercase tracking-wider mt-0.5">{{ group.cadena }}</p>
                }
                @if (group.direccion) {
                  <p class="text-[11px] text-slate-500 dark:text-slate-400 mt-1 line-clamp-1">{{ group.direccion }}</p>
                }
              </div>
            </div>

            <!-- Clients List -->
            @if (group.clients.length > 0) {
              <div class="pl-13 space-y-1.5">
                <p class="text-[9px] font-black text-slate-400 uppercase tracking-widest">Clientes</p>
                @for (c of group.clients; track c.id_cliente) {
                  <div class="flex items-center justify-between py-1.5 px-3 bg-white dark:bg-slate-900 rounded-xl border border-slate-100 dark:border-white/5">
                    <span class="text-xs font-bold text-slate-700 dark:text-slate-300">{{ c.nombre }}</span>
                    @if (c.visitado) {
                      <span class="text-[9px] font-black text-emerald-500 uppercase tracking-widest flex items-center gap-1">
                        <mat-icon class="!text-[10px]">check_circle</mat-icon> Visitado
                      </span>
                    } @else if (c.visita_id) {
                      <span class="text-[9px] font-black text-blue-500 uppercase tracking-widest flex items-center gap-1">
                        <mat-icon class="!text-[10px]">play_circle</mat-icon> En Progreso
                      </span>
                    } @else {
                      <span class="text-[9px] font-black text-amber-500 uppercase tracking-widest flex items-center gap-1">
                        <mat-icon class="!text-[10px]">pending</mat-icon> Pendiente
                      </span>
                    }
                  </div>
                }
              </div>
            }

            <!-- Action Button (IDÉNTICO al APK) -->
            <div class="pt-1">
              @if (allClientsVisited(group)) {
                <!-- All completed -->
                <div class="w-full py-2.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 rounded-xl text-[10px] font-black uppercase tracking-widest flex items-center justify-center gap-1.5">
                  <mat-icon class="!text-sm">check_circle</mat-icon>
                  Visita Completada
                </div>
              } @else if (hasActiveVisit(group)) {
                <!-- Resume active visit -->
                <button (click)="resumeVisit(group)"
                        class="w-full py-2.5 bg-primary-600 text-white rounded-xl text-[10px] font-black uppercase tracking-widest flex items-center justify-center gap-2 active:scale-95 transition-all shadow-sm">
                  <mat-icon class="!text-sm">play_arrow</mat-icon>
                  Continuar Gestión
                </button>
              } @else if (showPhotoChoice() === group.id_punto) {
                <!-- Camera / Gallery choice (IDÉNTICO al APK: dos botones separados) -->
                <div class="space-y-2">
                  <div class="flex gap-2">
                    <button (click)="openCamera()"
                            class="flex-1 py-2.5 bg-primary-600 text-white rounded-xl text-[10px] font-black uppercase tracking-widest flex items-center justify-center gap-1.5 active:scale-95 transition-all shadow-sm">
                      <mat-icon class="!text-sm">camera_alt</mat-icon>
                      Cámara
                    </button>
                    <button (click)="openGallery()"
                            class="flex-1 py-2.5 bg-slate-600 text-white rounded-xl text-[10px] font-black uppercase tracking-widest flex items-center justify-center gap-1.5 active:scale-95 transition-all shadow-sm">
                      <mat-icon class="!text-sm">photo_library</mat-icon>
                      Galería
                    </button>
                  </div>
                  <button (click)="cancelPhotoChoice()"
                          class="w-full py-2 text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest active:scale-95 transition-all">
                    Cancelar
                  </button>
                </div>
              } @else {
                <!-- Pendiente: Activar (IDÉNTICO al APK: botón con icono de cámara) -->
                <button (click)="activarPunto(group)"
                        [disabled]="activatingPdv() === group.id_punto"
                        class="w-full py-2.5 bg-amber-500 hover:bg-amber-400 disabled:opacity-60 text-white rounded-xl text-[10px] font-black uppercase tracking-widest flex items-center justify-center gap-2 active:scale-95 transition-all shadow-sm">
                  @if (activatingPdv() === group.id_punto) {
                    <mat-spinner diameter="16" color="accent"></mat-spinner>
                  } @else {
                    <mat-icon class="!text-sm">camera_alt</mat-icon>
                  }
                  Activar
                </button>
              }
            </div>

          </div>
        }
      </div>

      <!-- Footer: safe area padding -->
      <div class="h-5"></div>
    </div>

    <!-- Hidden file input: Camera (capture="environment" → abre cámara nativa) -->
    <input #cameraInput type="file" accept="image/*" capture="environment"
           class="hidden" (change)="onFileSelected($event)" />

    <!-- Hidden file input: Gallery (sin capture → abre galería) -->
    <input #galleryInput type="file" accept="image/*"
           class="hidden" (change)="onFileSelected($event)" />

    <!-- Spinner overlay: "Subiendo foto..." (IDÉNTICO al APK) -->
    @if (showUploadSpinner()) {
      <div class="fixed inset-0 z-[200] bg-black/50 flex items-center justify-center">
        <div class="bg-white dark:bg-slate-900 rounded-3xl p-8 shadow-2xl flex items-center gap-4">
          <mat-spinner diameter="36" color="primary"></mat-spinner>
          <span class="text-sm font-bold text-slate-700 dark:text-slate-200">Subiendo foto...</span>
        </div>
      </div>
    }

    <!-- Success modal: "¡Foto subida!" (IDÉNTICO al APK) -->
    @if (showSuccessModal()) {
      <div class="fixed inset-0 z-[200] bg-black/50 flex items-center justify-center">
        <div class="bg-white dark:bg-slate-900 rounded-3xl p-8 shadow-2xl flex flex-col items-center gap-3 max-w-[280px] text-center">
          <mat-icon class="!text-[54px] text-green-500">cloud_done</mat-icon>
          <h4 class="text-base font-black text-slate-800 dark:text-white">¡Foto subida!</h4>
          <p class="text-xs text-slate-500 dark:text-slate-400">Ahora selecciona el cliente para esta visita</p>
        </div>
      </div>
    }
  `,
  styles: [`:host { display: block; }`]
})
export class PuntosInteresModalComponent {
  private confirm = inject(ConfirmService);
  private snack = inject(MatSnackBar);

  @Input() rutaNombre: string = '';
  @Input() rutaId: string = '';
  @Input() pdvs: PdvGroup[] = [];

  @Output() close = new EventEmitter<void>();
  /** Emite cuando el usuario captura foto y confirma activar un PDV (IDÉNTICO al APK) */
  @Output() activarPdv = new EventEmitter<{ pdv: PdvGroup; photo: File }>();
  /** Emite cuando el usuario quiere continuar una visita activa */
  @Output() resumeVisita = new EventEmitter<{ pdv: PdvGroup; clienteId: number; visitaId: number }>();

  @ViewChild('cameraInput') cameraInput!: ElementRef<HTMLInputElement>;
  @ViewChild('galleryInput') galleryInput!: ElementRef<HTMLInputElement>;

  activatingPdv = signal<string | null>(null);
  showPhotoChoice = signal<string | null>(null);
  showUploadSpinner = signal(false);
  showSuccessModal = signal(false);
  private pendingPdv: PdvGroup | null = null;
  private _fileCancelCheck = false;
  private _cancelFocusHandler: (() => void) | null = null;

  busqueda = signal<string>('');

  pdvsFiltrados = computed<PdvGroup[]>(() => {
    const q = this.busqueda().trim().toLowerCase();
    if (!q) return this.pdvs;
    return this.pdvs.filter(p => {
      const matchNombre = (p.nombre || '').toLowerCase().includes(q);
      const matchCadena = (p.cadena || '').toLowerCase().includes(q);
      const matchDireccion = (p.direccion || '').toLowerCase().includes(q);
      const matchCliente = (p.clients || []).some(c => (c.nombre || '').toLowerCase().includes(q));
      return matchNombre || matchCadena || matchDireccion || matchCliente;
    });
  });

  priorityColors(prioridad: string) {
    return PRIORITY_COLORS[prioridad] ?? PRIORITY_COLORS['Baja'];
  }

  statusIcon(group: PdvGroup): string {
    if (this.allClientsVisited(group)) return 'check_circle';
    if (this.hasActiveVisit(group)) return 'play_circle';
    return 'storefront';
  }

  statusLabel(group: PdvGroup): string {
    if (this.allClientsVisited(group)) return 'Completado';
    if (this.hasActiveVisit(group)) return 'Activo';
    return 'Pendiente';
  }

  statusColor(group: PdvGroup): { iconBg: string; iconColor: string; badgeBg: string; badgeText: string } {
    if (this.allClientsVisited(group)) {
      return { iconBg: 'bg-emerald-500/10', iconColor: 'text-emerald-500', badgeBg: 'bg-emerald-500/10', badgeText: 'text-emerald-600' };
    }
    if (this.hasActiveVisit(group)) {
      return { iconBg: 'bg-blue-500/10', iconColor: 'text-blue-500', badgeBg: 'bg-blue-500/10', badgeText: 'text-blue-600' };
    }
    return { iconBg: 'bg-amber-500/10', iconColor: 'text-amber-500', badgeBg: 'bg-amber-500/10', badgeText: 'text-amber-600' };
  }

  allClientsVisited(group: PdvGroup): boolean {
    return group.clients.length > 0 && group.clients.every(c => c.visitado);
  }

  /** Tiene visita activa si algún cliente tiene visita_id (aunque no esté finalizada) pero no todos */
  hasActiveVisit(group: PdvGroup): boolean {
    return group.clients.some(c => c.visita_id !== null) && !this.allClientsVisited(group);
  }

  /** FLUJO IDÉNTICO al APK: confirmar → elegir cámara/galería → "Subiendo foto..." → "¡Foto subida!" → emitir activarPdv */
  async activarPunto(group: PdvGroup): Promise<void> {
    // 1. Confirmar activación
    const confirmed = await this.confirm.confirm(
      `¿Estás seguro de activar ${group.nombre}?`,
      { title: 'Activar punto', confirmText: 'Sí, activar', cancelText: 'Cancelar', danger: false }
    );
    if (!confirmed) return;

    this.pendingPdv = group;
    this.activatingPdv.set(group.id_punto);

    // 2. Mostrar opciones Cámara / Galería (IDÉNTICO al APK)
    this.showPhotoChoice.set(group.id_punto);
  }

  /** Abre la cámara nativa */
  openCamera(): void {
    this._setupCancelDetection();
    this.cameraInput.nativeElement.value = '';
    this.cameraInput.nativeElement.click();
  }

  /** Abre la galería */
  openGallery(): void {
    this._setupCancelDetection();
    this.galleryInput.nativeElement.value = '';
    this.galleryInput.nativeElement.click();
  }

  /** Cancela la elección de foto y vuelve al estado inicial */
  cancelPhotoChoice(): void {
    this._teardownCancelDetection();
    this.showPhotoChoice.set(null);
    this.activatingPdv.set(null);
    this.pendingPdv = null;
  }

  /** Configura detección de cancelación del file picker (window:focus) */
  private _setupCancelDetection(): void {
    this._fileCancelCheck = true;
    this._cancelFocusHandler = () => {
      // Pequeño delay para que el evento change tenga prioridad
      setTimeout(() => {
        if (this._fileCancelCheck && this.pendingPdv) {
          // Usuario canceló el file picker — volver a mostrar opciones
          this.showPhotoChoice.set(this.pendingPdv.id_punto);
        }
        this._fileCancelCheck = false;
      }, 400);
      window.removeEventListener('focus', this._cancelFocusHandler!);
      this._cancelFocusHandler = null;
    };
    window.addEventListener('focus', this._cancelFocusHandler);
  }

  /** Limpia el listener de cancelación */
  private _teardownCancelDetection(): void {
    this._fileCancelCheck = false;
    if (this._cancelFocusHandler) {
      window.removeEventListener('focus', this._cancelFocusHandler);
      this._cancelFocusHandler = null;
    }
  }

  /** Cuando el usuario selecciona/toma una foto */
  onFileSelected(event: Event): void {
    // Marcar que SÍ se seleccionó archivo (anula la detección de cancelación)
    this._fileCancelCheck = false;
    this._teardownCancelDetection();

    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file || !this.pendingPdv) {
      this.activatingPdv.set(null);
      this.pendingPdv = null;
      this.showPhotoChoice.set(null);
      return;
    }

    const pdv = this.pendingPdv;
    this.showPhotoChoice.set(null);

    // 3. Mostrar spinner "Subiendo foto..." (IDÉNTICO al APK)
    this.showUploadSpinner.set(true);

    // Simular tiempo de subida (1.2s como en el APK); en web la foto se sube realmente
    // cuando se crea la visita en SeleccionarClienteModal
    setTimeout(() => {
      this.showUploadSpinner.set(false);
      this.activatingPdv.set(null);
      this.pendingPdv = null;

      // 4. Mostrar "¡Foto subida!" (IDÉNTICO al APK)
      this.showSuccessModal.set(true);

      // Auto-cierre del modal de éxito después de 1.5s y emitir evento
      setTimeout(() => {
        this.showSuccessModal.set(false);
        // Emitir activarPdv para que el padre abra SeleccionarClienteModal
        this.activarPdv.emit({ pdv, photo: file });
      }, 1500);
    }, 1200);
  }

  /** "Continuar Gestión" — IDÉNTICO al APK. Busca cliente con visita activa (por visita_id, no solo visitado) */
  resumeVisit(group: PdvGroup): void {
    const activeClient = group.clients.find(c => c.visita_id !== null);
    if (activeClient) {
      this.resumeVisita.emit({
        pdv: group,
        clienteId: activeClient.id_cliente,
        visitaId: activeClient.visita_id!,
      });
    }
  }
}
