import { Component, Input, Output, EventEmitter, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { firstValueFrom } from 'rxjs';
import { ApiService } from '../../../../core/services/api.service';

interface ClienteParaSeleccionar {
    id_cliente: number;
    cliente_nombre: string;
    prioridad: string;
}

const PRIORITY_COLORS: Record<string, { bg: string; text: string; border: string; dot: string }> = {
    Alta: { bg: 'bg-red-500/10', text: 'text-red-600', border: 'border-red-500/20', dot: 'bg-red-500' },
    Media: { bg: 'bg-amber-500/10', text: 'text-amber-600', border: 'border-amber-500/20', dot: 'bg-amber-500' },
    Baja: { bg: 'bg-slate-200 dark:bg-slate-700', text: 'text-slate-500 dark:text-slate-400', border: 'border-slate-200 dark:border-slate-700', dot: 'bg-slate-400' },
};

@Component({
    selector: 'app-seleccionar-cliente-modal',
    standalone: true,
    imports: [CommonModule, MatIconModule, MatProgressSpinnerModule, MatSnackBarModule],
    template: `
    <!-- Overlay backdrop -->
    <div class="fixed inset-0 z-[130] bg-black/60 backdrop-blur-sm animate-in fade-in duration-200"
         (click)="close.emit()">
    </div>

    <!-- Bottom Sheet -->
    <div class="fixed inset-x-0 bottom-0 z-[131] bg-white dark:bg-slate-900 rounded-t-[2rem] shadow-2xl max-h-[85vh] flex flex-col animate-in slide-in-from-bottom duration-300">
      <!-- Handle -->
      <div class="flex justify-center pt-3 pb-1">
        <div class="w-10 h-1 rounded-full bg-slate-300 dark:bg-slate-600"></div>
      </div>

      <!-- Header -->
      <div class="px-6 py-3 flex items-center justify-between border-b border-slate-100 dark:border-white/5">
        <div class="flex items-center gap-3 min-w-0">
          <mat-icon class="text-primary-500">people_alt</mat-icon>
          <div class="min-w-0">
            <h3 class="font-black text-sm text-slate-800 dark:text-white truncate">Seleccionar Cliente</h3>
            <p class="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
              {{ punto?.nombre || 'PDV' }}
            </p>
          </div>
        </div>
        <button (click)="close.emit()"
                class="w-9 h-9 rounded-xl bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400 active:scale-95 transition-all">
          <mat-icon class="!text-lg">close</mat-icon>
        </button>
      </div>

      <!-- Description -->
      <div class="px-6 py-2">
        <p class="text-xs text-slate-500 dark:text-slate-400">Selecciona el cliente para el cual deseas tomar fotos adicionales</p>
      </div>

      <div class="border-b border-slate-100 dark:border-white/5"></div>

      <!-- Client List -->
      <div class="flex-grow overflow-y-auto px-4 py-4 space-y-3 custom-scrollbar">
        @if (loading()) {
          <div class="py-20 flex flex-col items-center gap-3">
            <mat-spinner diameter="36" color="primary"></mat-spinner>
            <p class="text-xs text-slate-400 font-bold">Cargando clientes...</p>
          </div>
        } @else if (clientes().length === 0) {
          <div class="py-16 text-center opacity-50">
            <mat-icon class="!text-5xl text-slate-300">people_outline</mat-icon>
            <p class="text-xs font-black text-slate-400 uppercase tracking-widest mt-2">No hay clientes configurados para este punto</p>
          </div>
        } @else {
          @for (c of clientes(); track c.id_cliente) {
            <div class="bg-slate-50 dark:bg-slate-800/50 rounded-2xl p-4 border border-slate-100 dark:border-white/5">
              <div class="flex items-center justify-between">
                <div class="flex-1 min-w-0">
                  <h4 class="font-bold text-sm text-slate-800 dark:text-white truncate">{{ c.cliente_nombre }}</h4>
                  <div class="mt-1.5">
                    <span [class]="priorityColors(c.prioridad).bg + ' ' + priorityColors(c.prioridad).border + ' border rounded-full px-2.5 py-0.5 inline-flex items-center gap-1.5'">
                      <span [class]="priorityColors(c.prioridad).dot + ' w-1.5 h-1.5 rounded-full'"></span>
                      <span [class]="priorityColors(c.prioridad).text + ' text-[9px] font-black uppercase tracking-widest'">Prioridad: {{ c.prioridad }}</span>
                    </span>
                  </div>
                </div>
                <button (click)="seleccionarCliente(c)"
                        [disabled]="creatingVisit() === c.id_cliente"
                        class="ml-3 py-2 px-4 border-2 border-primary-500 text-primary-600 dark:text-primary-400 rounded-xl text-xs font-bold active:scale-95 transition-all hover:bg-primary-50 dark:hover:bg-primary-500/10 disabled:opacity-50 shrink-0">
                  @if (creatingVisit() === c.id_cliente) {
                    <mat-spinner diameter="14" color="primary"></mat-spinner>
                  } @else {
                    Seleccionar
                  }
                </button>
              </div>
            </div>
          }
        }
      </div>

      <!-- Footer: safe area padding -->
      <div class="h-5"></div>
    </div>

    <!-- Spinner overlay: "Creando visita..." (IDÉNTICO al APK) -->
    @if (showCreatingSpinner()) {
      <div class="fixed inset-0 z-[200] bg-black/50 flex items-center justify-center">
        <div class="bg-white dark:bg-slate-900 rounded-3xl p-8 shadow-2xl flex items-center gap-4">
          <mat-spinner diameter="36" color="primary"></mat-spinner>
          <span class="text-sm font-bold text-slate-700 dark:text-slate-200">Creando visita...</span>
        </div>
      </div>
    }

    <!-- Success modal: "¡Visita creada!" (IDÉNTICO al APK) -->
    @if (showSuccessModal()) {
      <div class="fixed inset-0 z-[200] bg-black/50 flex items-center justify-center">
        <div class="bg-white dark:bg-slate-900 rounded-3xl p-8 shadow-2xl flex flex-col items-center gap-3 max-w-[280px] text-center">
          <mat-icon class="!text-[54px] text-green-500">check_circle</mat-icon>
          <h4 class="text-base font-black text-slate-800 dark:text-white">¡Visita creada!</h4>
          <p class="text-xs text-slate-500 dark:text-slate-400">Se ha creado la visita para {{ successCliente() }}</p>
        </div>
      </div>
    }

    <!-- Error view -->
    @if (error()) {
      <div class="fixed inset-0 z-[200] bg-black/50 flex items-center justify-center">
        <div class="bg-white dark:bg-slate-900 rounded-3xl p-8 shadow-2xl flex flex-col items-center gap-4 max-w-[280px] text-center">
          <mat-icon class="!text-[48px] text-red-500">error_outline</mat-icon>
          <p class="text-xs text-slate-600 dark:text-slate-300 font-bold">{{ error() }}</p>
          <button (click)="error.set(null)"
                  class="py-2 px-6 bg-primary-600 text-white rounded-xl text-xs font-bold active:scale-95 transition-all">
            Aceptar
          </button>
        </div>
      </div>
    }
  `,
    styles: [`:host { display: block; }`]
})
export class SeleccionarClienteModalComponent implements OnInit {
    private api = inject(ApiService);
    private snack = inject(MatSnackBar);

    @Input() punto: any = null;
    @Input() rutaId: string = '';
    @Input() rutaNombre: string = '';
    @Input() activationPhoto!: File;

    @Output() close = new EventEmitter<void>();
    @Output() visitaCreada = new EventEmitter<{ id_visita: number; id_cliente: number; cliente: string }>();

    clientes = signal<ClienteParaSeleccionar[]>([]);
    loading = signal(true);
    creatingVisit = signal<number | null>(null);
    showCreatingSpinner = signal(false);
    showSuccessModal = signal(false);
    successCliente = signal('');
    error = signal<string | null>(null);

    ngOnInit(): void {
        this.loadClientes();
    }

    priorityColors(prioridad: string) {
        return PRIORITY_COLORS[prioridad] ?? PRIORITY_COLORS['Baja'];
    }

    private priorityValue(prioridad: string): number {
        const p = prioridad.toLowerCase();
        if (p.includes('alta')) return 3;
        if (p.includes('media')) return 2;
        return 1;
    }

    /** Carga clientes del PDV y los ordena por prioridad (IDÉNTICO al APK) */
    private loadClientes(): void {
        this.loading.set(true);

        // Usar método público getMercRutaPdvs
        const idRuta = Number(this.rutaId);
        if (!idRuta) {
            // Fallback: usar clients del punto recibido
            this.buildFromPuntoClients();
            return;
        }

        this.api.getMercRutaPdvs(idRuta).subscribe({
            next: (res: any) => {
                const pdvs = res.pdvs || res.data || [];
                const targetPdv = pdvs.find((p: any) =>
                    String(p.id_punto) === String(this.punto?.id_punto || this.punto?.id)
                );

                if (targetPdv && targetPdv.clientes) {
                    this.buildClientList(targetPdv.clientes);
                } else {
                    this.buildFromPuntoClients();
                }
                this.loading.set(false);
            },
            error: () => {
                this.buildFromPuntoClients();
                this.loading.set(false);
            }
        });
    }

    private buildFromPuntoClients(): void {
        if (this.punto?.clients) {
            this.buildClientList(this.punto.clients);
        }
    }

    private buildClientList(sourceList: any[]): void {
        const unique = new Map<number, ClienteParaSeleccionar>();
        for (const c of sourceList) {
            const id = c.id_cliente || c.id;
            if (id && !unique.has(id)) {
                unique.set(id, {
                    id_cliente: id,
                    cliente_nombre: c.nombre || c.cliente_nombre || c.cliente || 'Sin nombre',
                    prioridad: c.prioridad || 'Media',
                });
            }
        }
        const list = Array.from(unique.values());
        // Ordenar por prioridad: Alta > Media > Baja (IDÉNTICO al APK)
        list.sort((a, b) => this.priorityValue(b.prioridad) - this.priorityValue(a.prioridad));
        this.clientes.set(list);
    }

    /** FLUJO IDÉNTICO al APK: "Creando visita..." → GPS → iniciar API → "¡Visita creada!" → emitir */
    async seleccionarCliente(cliente: ClienteParaSeleccionar): Promise<void> {
        this.creatingVisit.set(cliente.id_cliente);

        // 1. Spinner "Creando visita..." (IDÉNTICO al APK)
        this.showCreatingSpinner.set(true);

        try {
            // 2. Obtener GPS
            let lat: number | undefined;
            let lon: number | undefined;
            try {
                const pos = await this.getPosition();
                lat = pos.lat;
                lon = pos.lon;
            } catch (e) {
                console.warn('GPS no disponible para crear visita:', e);
            }

            // 3. Iniciar visita usando el método público del ApiService
            const payload = {
                id_punto: String(this.punto?.id_punto || this.punto?.id || ''),
                id_cliente: cliente.id_cliente,
            };

            const res: any = await firstValueFrom(this.api.iniciarVisita(payload));
            const visitaId = res?.id_visita || res?.id;

            // 4. Subir foto de activación si existe
            if (this.activationPhoto && visitaId) {
                try {
                    await firstValueFrom(this.api.uploadMercFoto(visitaId, 'activacion', this.activationPhoto, lat, lon));
                } catch (e) {
                    console.warn('Error subiendo foto de activación:', e);
                }
            }

            // 5. Cerrar spinner
            this.showCreatingSpinner.set(false);
            this.creatingVisit.set(null);

            // 6. Mostrar "¡Visita creada!" y auto-cerrar después de 1.5s (IDÉNTICO al APK)
            this.successCliente.set(cliente.cliente_nombre);
            this.showSuccessModal.set(true);

            setTimeout(() => {
                this.showSuccessModal.set(false);
                this.visitaCreada.emit({
                    id_visita: visitaId,
                    id_cliente: cliente.id_cliente,
                    cliente: cliente.cliente_nombre,
                });
            }, 1500);

        } catch (e: any) {
            this.showCreatingSpinner.set(false);
            this.creatingVisit.set(null);
            const msg = e?.error?.detail || e?.message || 'Error al crear la visita';
            this.error.set(msg);
        }
    }

    private getPosition(): Promise<{ lat?: number; lon?: number }> {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error('Geolocalización no soportada'));
                return;
            }
            navigator.geolocation.getCurrentPosition(
                (pos) => resolve({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
                (err) => reject(err),
                { timeout: 10000, enableHighAccuracy: true }
            );
        });
    }
}
