import { Component, Input, OnInit, OnDestroy, signal, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Subscription, firstValueFrom } from 'rxjs';
import { ApiService } from '../../../../core/services/api.service';
import { MercUiService } from '../../services/merc-ui.service';
import { OfflineQueueService } from '../../services/offline-queue.service';
import { ConfirmService } from '../../../../shared/components/confirm-dialog/confirm.service';
import { ConfirmDialogComponent } from '../../../../shared/components/confirm-dialog/confirm-dialog.component';
import { SkeletonLoaderComponent } from '../../../../shared/components/skeleton-loader/skeleton-loader.component';
import { PuntosInteresModalComponent } from './puntos-interes-modal.component';
import { SeleccionarClienteModalComponent } from './seleccionar-cliente-modal.component';

interface RutaDelDia {
  id_ruta: number;
  nombre: string;
  tipo: string;
  pdvs: any[];
  // Estado derivado
  status: 'inactiva' | 'en_progreso' | 'finalizada';
  puntos_count: number;
  finalizada?: boolean;
}

interface PdvForModal {
  id_punto: string;
  nombre: string;
  cadena: string;
  direccion: string;
  latitud?: number;
  longitud?: number;
  prioridad?: string;
  hasVisited: boolean;
  clients: { id_cliente: number; nombre: string; visitado: boolean; visita_id: number | null }[];
}

const PRIORITY_COLORS: Record<string, { bg: string; text: string; border: string; dot: string }> = {
  Alta: { bg: 'bg-red-500/10', text: 'text-red-600', border: 'border-red-500/20', dot: 'bg-red-500' },
  Media: { bg: 'bg-amber-500/10', text: 'text-amber-600', border: 'border-amber-500/20', dot: 'bg-amber-500' },
  Baja: { bg: 'bg-slate-200 dark:bg-slate-800', text: 'text-slate-500 dark:text-slate-400', border: 'border-slate-200 dark:border-slate-700', dot: 'bg-slate-400' },
};

const PRIORITY_LABELS: Record<string, string> = {
  Alta: 'Alta', Media: 'Media', Baja: 'Baja',
};

@Component({
  selector: 'app-merc-ruta',
  standalone: true,
  imports: [
    CommonModule, MatIconModule, MatButtonModule, MatProgressSpinnerModule, MatSnackBarModule,
    PuntosInteresModalComponent, SeleccionarClienteModalComponent,
    SkeletonLoaderComponent, ConfirmDialogComponent
  ],
  template: `
    <div class="flex flex-col h-full bg-slate-50 dark:bg-slate-950">

      <!-- LISTA DE RUTAS (IDÉNTICO al APK MisRutasScreen) -->
      <div class="flex-grow overflow-y-auto p-4 space-y-4">

        @if (loading()) {
          <app-skeleton-loader [count]="3"></app-skeleton-loader>
        } @else if (rutas().length === 0) {
          <div class="py-20 text-center opacity-50">
            <mat-icon class="!text-6xl text-slate-300">route</mat-icon>
            <p class="text-xs font-black text-slate-400 uppercase tracking-widest mt-3">
              No hay rutas {{ tipoRuta === 'variable' ? 'variables' : 'fijas' }} asignadas.
            </p>
          </div>
        } @else {
          @for (ruta of rutas(); track ruta.id_ruta) {
            <div class="bg-white dark:bg-slate-900 border border-slate-100 dark:border-white/5 rounded-[1.5rem] p-5 shadow-sm space-y-4">

              <!-- Header: Nombre + Estado -->
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2 min-w-0">
                  <div class="w-9 h-9 rounded-xl bg-primary-500/10 text-primary-500 flex items-center justify-center shrink-0">
                    <mat-icon class="!text-lg">label</mat-icon>
                  </div>
                  <h4 class="font-bold text-sm text-slate-800 dark:text-white truncate">Ruta {{ ruta.nombre }}</h4>
                </div>
                <span [class]="statusBadgeClass(ruta.status)"
                      class="text-[10px] font-black uppercase tracking-widest px-3 py-1 rounded-full shrink-0">
                  {{ statusLabel(ruta.status) }}
                </span>
              </div>

              <!-- Aclaración: ruta activa — solo se pueden visitar PDVs de esta ruta -->
              @if (ruta.status === 'en_progreso' && ui.activeRouteId() === ruta.id_ruta) {
                <div class="bg-primary-500/10 border border-primary-500/20 rounded-xl p-3 flex items-start gap-2">
                  <mat-icon class="!text-base text-primary-500 mt-0.5 shrink-0">info</mat-icon>
                  <p class="text-[11px] font-medium text-primary-600 dark:text-primary-400 leading-relaxed">
                    Esta ruta está activa. Solo podés seleccionar PDVs de <strong>Ruta {{ ruta.nombre }}</strong> hasta que la finalices. Las demás rutas permanecen bloqueadas.
                  </p>
                </div>
              }

              <!-- Info: ID + Puntos -->
              <div class="flex items-center gap-6 text-xs text-slate-500 dark:text-slate-400">
                <span><strong class="font-bold text-slate-700 dark:text-slate-300">ID Ruta:</strong> {{ ruta.id_ruta }}</span>
                <span><strong class="font-bold text-slate-700 dark:text-slate-300">Puntos:</strong> {{ ruta.puntos_count }}</span>
              </div>

              <!-- Acciones según estado -->
              <div class="pt-2">
                @if (ruta.status === 'finalizada') {
                  <!-- Finalizada: botón deshabilitado -->
                  <div class="w-full py-3 bg-slate-100 dark:bg-white/5 rounded-xl text-center">
                    <span class="text-[11px] font-bold text-slate-400 dark:text-slate-500">Gestión del PDV Completada</span>
                  </div>
                } @else if (ruta.status === 'en_progreso') {
                  <!-- En Progreso: "Ver Puntos" + "Finalizar PDV" -->
                  <div class="grid grid-cols-2 gap-3">
                    <button (click)="verPuntos(ruta)"
                            class="py-3 rounded-xl border border-slate-200 dark:border-white/10 text-slate-700 dark:text-slate-200 text-[10px] font-black uppercase tracking-widest flex items-center justify-center gap-1.5 active:scale-95 transition-all hover:bg-slate-50 dark:hover:bg-white/5">
                      <mat-icon class="!text-sm">search</mat-icon>
                      Ver Puntos
                    </button>
                    <button (click)="finalizarRuta(ruta)"
                            class="py-3 rounded-xl border-2 border-red-400 dark:border-red-600 text-red-500 dark:text-red-400 text-[10px] font-black uppercase tracking-widest flex items-center justify-center gap-1.5 active:scale-95 transition-all hover:bg-red-50 dark:hover:bg-red-950/20">
                      <mat-icon class="!text-sm">cancel</mat-icon>
                      Finalizar PDV
                    </button>
                  </div>
                } @else {
                  <!-- Inactiva: "Iniciar PDV Nuevo" (verde, IDÉNTICO al APK) -->
                  <button (click)="iniciarRuta(ruta)" [disabled]="activandoRutaId() === ruta.id_ruta"
                          class="w-full py-3.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-60 text-white rounded-xl text-xs font-black uppercase tracking-widest flex items-center justify-center gap-2 active:scale-95 transition-all shadow-md shadow-emerald-500/20">
                    @if (activandoRutaId() === ruta.id_ruta) {
                      <mat-spinner diameter="18" color="accent"></mat-spinner>
                    } @else {
                      <mat-icon class="!text-base">play_circle</mat-icon>
                    }
                    Iniciar PDV Nuevo
                  </button>
                }
              </div>

            </div>
          }
        }

      </div>

      <!-- Puntos de Interés Modal (se abre al hacer clic en "Ver Puntos") -->
      @if (showPuntosInteres()) {
        <app-puntos-interes-modal
          [rutaNombre]="selectedRutaForPuntos()?.nombre || ''"
          [rutaId]="selectedRutaForPuntos()?.id_ruta?.toString() || ''"
          [pdvs]="pdvsForModal()"
          (close)="showPuntosInteres.set(false)"
          (activarPdv)="onActivarPdvDesdeModal($event)"
          (resumeVisita)="onResumeVisitaDesdeModal($event)">
        </app-puntos-interes-modal>
      }

      <!-- Seleccionar Cliente Modal (se abre después de capturar foto desde PuntosInteresModal) -->
      @if (showSeleccionarCliente()) {
        <app-seleccionar-cliente-modal
          [punto]="puntoParaSeleccionar()!"
          [rutaId]="selectedRutaForPuntos()?.id_ruta?.toString() || ''"
          [rutaNombre]="selectedRutaForPuntos()?.nombre || ''"
          [activationPhoto]="activationPhotoFromModal()!"
          (close)="showSeleccionarCliente.set(false); activationPhotoFromModal.set(null)"
          (visitaCreada)="onVisitaCreada($event)">
        </app-seleccionar-cliente-modal>
      }

      <!-- Spinner overlay: "Iniciando PDV nuevo..." -->
      @if (showActivationSpinner()) {
        <div class="fixed inset-0 z-[200] bg-black/50 flex items-center justify-center">
          <div class="bg-white dark:bg-slate-900 rounded-3xl p-8 shadow-2xl flex flex-col items-center gap-4">
            <mat-spinner diameter="40" [color]="spinnerType()"></mat-spinner>
            <p class="text-sm font-bold text-slate-700 dark:text-slate-200">{{ spinnerMessage() }}</p>
          </div>
        </div>
      }

    </div>
  `,
  styles: [`:host { display: block; height: 100%; }`]
})
export class MercRutaComponent implements OnInit, OnDestroy {
  @Input() tipoRuta: 'fija' | 'variable' = 'fija';

  private api = inject(ApiService);
  private snack = inject(MatSnackBar);
  ui = inject(MercUiService);
  private offline = inject(OfflineQueueService);
  private confirmSvc = inject(ConfirmService);

  loading = signal(true);
  rutas = signal<RutaDelDia[]>([]);
  activandoRutaId = signal<number | null>(null);

  // Puntos de Interés Modal
  showPuntosInteres = signal(false);
  selectedRutaForPuntos = signal<RutaDelDia | null>(null);

  // Seleccionar Cliente Modal
  showSeleccionarCliente = signal(false);
  puntoParaSeleccionar = signal<PdvForModal | null>(null);
  activationPhotoFromModal = signal<File | null>(null);

  // Spinner overlay global
  showActivationSpinner = signal(false);
  spinnerMessage = signal('');
  spinnerType = signal<'primary' | 'warn'>('primary');

  private chainResolvedSub?: Subscription;

  priorityColors(prioridad: string) {
    return PRIORITY_COLORS[prioridad] ?? PRIORITY_COLORS['Baja'];
  }

  priorityLabel(prioridad: string) {
    return PRIORITY_LABELS[prioridad] ?? prioridad;
  }

  statusLabel(status: string): string {
    switch (status) {
      case 'en_progreso': return 'En Progreso';
      case 'finalizada': return 'Finalizada';
      default: return 'Inactiva';
    }
  }

  statusBadgeClass(status: string): string {
    switch (status) {
      case 'en_progreso': return 'bg-emerald-500/10 text-emerald-600 border border-emerald-500/20';
      case 'finalizada': return 'bg-slate-300/30 dark:bg-white/5 text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-white/5';
      default: return 'bg-slate-200 dark:bg-slate-800 text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-slate-700';
    }
  }

  /** PDVs aplanados para el modal de puntos de interés */
  pdvsForModal = computed<PdvForModal[]>(() => {
    const ruta = this.selectedRutaForPuntos();
    if (!ruta) return [];
    return (ruta.pdvs || []).map((pdv: any) => {
      const clients = (pdv.clientes || []).map((c: any) => ({
        id_cliente: c.id_cliente,
        nombre: c.nombre,
        visitado: c.visitado,
        visita_id: c.id_visita,
      }));
      return {
        id_punto: pdv.id_punto,
        nombre: pdv.nombre,
        cadena: pdv.cadena,
        direccion: pdv.direccion,
        latitud: pdv.latitud ? Number(pdv.latitud) : undefined,
        longitud: pdv.longitud ? Number(pdv.longitud) : undefined,
        prioridad: pdv.prioridad,
        hasVisited: clients.some((c: any) => c.visitado),
        clients,
      };
    });
  });

  ngOnInit(): void {
    this.loadData();
    this.chainResolvedSub = this.offline.chainResolved$.subscribe(({ chainId, realVisitaId }) => {
      this.ui.resolveVisita(chainId, realVisitaId);
    });
  }

  ngOnDestroy(): void {
    this.chainResolvedSub?.unsubscribe();
  }

  private _processRutasResponse(res: any) {
    const todasLasRutas = [
      ...(res.rutas_fijas || []),
      ...(res.rutas_variables || []),
    ];

    const filtradas = todasLasRutas.filter((r: any) =>
      r.tipo.toLowerCase() === this.tipoRuta.toLowerCase()
    );

    const rutasConEstado: RutaDelDia[] = filtradas.map((r: any) => {
      const pdvs = r.pdvs || [];
      const puntos_count = pdvs.length;
      const tieneClientesVisitados = pdvs.some((p: any) =>
        (p.clientes || []).some((c: any) => c.visitado || c.id_visita)
      );

      let status: 'inactiva' | 'en_progreso' | 'finalizada' = 'inactiva';

      if (r.finalizada === true) {
        status = 'finalizada';
      } else if (r.activada === true || tieneClientesVisitados) {
        status = 'en_progreso';
      }

      return {
        id_ruta: r.id_ruta,
        nombre: r.nombre,
        tipo: r.tipo,
        pdvs,
        status,
        puntos_count,
        finalizada: r.finalizada,
      };
    });

    this.rutas.set(rutasConEstado);
    this.loading.set(false);
  }

  loadData(): void {
    // ⚡ 0ms INSTANT LOAD: si tenemos cache previo, mostrarlo inmediatamente
    if (this.ui.cachedMisRutas) {
      this._processRutasResponse(this.ui.cachedMisRutas);
    } else {
      this.loading.set(true);
    }

    // Background sync para actualizar estado
    this.api.getMercMiRuta().subscribe({
      next: (res) => {
        this.ui.cachedMisRutas = res;
        this._processRutasResponse(res);
      },
      error: () => {
        this.loading.set(false);
        if (!this.ui.cachedMisRutas) {
          this.snack.open('Error al cargar datos', 'OK', { duration: 3000 });
        }
      },
    });
  }

  /** GPS con timeout */
  private getPosition(): Promise<{ lat?: number; lon?: number }> {
    return new Promise((resolve) => {
      if (!navigator.geolocation) return resolve({});
      navigator.geolocation.getCurrentPosition(
        (p) => resolve({ lat: p.coords.latitude, lon: p.coords.longitude }),
        () => resolve({}),
        { enableHighAccuracy: true, timeout: 8000 },
      );
    });
  }

  /** INICIAR RUTA: confirmación → spinner → GPS → activar → éxito (SIN foto, IDÉNTICO al APK) */
  async iniciarRuta(ruta: RutaDelDia): Promise<void> {
    const confirmado = await this.confirmSvc.confirm(
      `Estás a punto de iniciar el registro de PDV nuevo en: ${ruta.nombre}`,
      { title: '¿Iniciar PDV Nuevo?', confirmText: 'Sí, iniciar', cancelText: 'Cancelar' }
    );
    if (!confirmado) return;

    this.activandoRutaId.set(ruta.id_ruta);
    this.showActivationSpinner.set(true);
    this.spinnerMessage.set('Iniciando PDV nuevo...');
    this.spinnerType.set('primary');

    try {
      const { lat, lon } = await this.getPosition();

      // Persistir la activación en el backend (RUTAS_ACTIVADAS) para que
      // sobreviva refrescos del navegador / cierres de sesión.
      // Equivale a g.activarRuta() de la APK.
      await firstValueFrom(this.api.activarRuta(ruta.id_ruta));

      this.showActivationSpinner.set(false);
      this.activandoRutaId.set(null);

      // Actualizar estado local a "en_progreso" para mostrar "Ver Puntos" y "Finalizar PDV"
      this.rutas.update(list => list.map(r => {
        if (r.id_ruta === ruta.id_ruta) return { ...r, status: 'en_progreso' as const };
        return r;
      }));

      // Marcar la ruta como activa en el servicio global (bloquea otras rutas)
      this.ui.setActiveRoute(ruta.id_ruta);

      // Modal de éxito (IDÉNTICO al APK: "¡PDV Nuevo iniciado!")
      await this.confirmSvc.info(
        'Ahora puedes ver los puntos del PDV nuevo',
        { title: '¡PDV Nuevo iniciado!', confirmText: 'Continuar' }
      );
    } catch (e) {
      this.showActivationSpinner.set(false);
      this.activandoRutaId.set(null);
      this.snack.open('Error al activar PDV: ' + (e as any)?.message || 'Error desconocido', 'OK', { duration: 3000 });
    }
  }

  /** FINALIZAR RUTA: confirmación → spinner → finalizar → éxito (IDÉNTICO al APK) */
  async finalizarRuta(ruta: RutaDelDia): Promise<void> {
    const confirmado = await this.confirmSvc.confirm(
      `¿Estás seguro de finalizar la gestión de PDV para ${ruta.nombre}?`,
      { title: '¿Finalizar PDV?', confirmText: 'Sí, finalizar', cancelText: 'Cancelar', danger: true }
    );
    if (!confirmado) return;

    this.showActivationSpinner.set(true);
    this.spinnerMessage.set('Finalizando PDV...');
    this.spinnerType.set('warn');

    try {
      // Backend persistente: POST /api/merc/ruta/finalizar
      await firstValueFrom(this.api.finalizarRuta(ruta.id_ruta));

      this.showActivationSpinner.set(false);

      await this.confirmSvc.info('', { title: '¡PDV Finalizado!', confirmText: 'OK' });

      // Actualizar estado local
      this.rutas.update(list => list.map(r => {
        if (r.id_ruta === ruta.id_ruta) return { ...r, status: 'finalizada' as const };
        return r;
      }));

      // Limpiar la ruta activa global (desbloquea otras rutas)
      this.ui.clearActiveRoute();
    } catch (e: any) {
      this.showActivationSpinner.set(false);
      // Mostrar mensaje específico del backend si está disponible
      const detail = e?.error?.detail || e?.error?.mensaje || e?.error;
      const mensaje = typeof detail === 'string' ? detail
        : (detail?.mensaje || 'Error al finalizar PDV');
      this.snack.open(mensaje, 'OK', { duration: 5000 });
    }
  }

  /** VER PUNTOS: abre el modal de puntos de interés (IDÉNTICO al APK) */
  verPuntos(ruta: RutaDelDia): void {
    this.selectedRutaForPuntos.set(ruta);
    this.showPuntosInteres.set(true);
  }

  /** Cuando desde el modal de puntos se hace clic en "Activar" (pendiente de foto) */
  onActivarPdvDesdeModal(event: { pdv: PdvForModal; photo: File }): void {
    this.activationPhotoFromModal.set(event.photo);
    this.puntoParaSeleccionar.set(event.pdv);
    this.showPuntosInteres.set(false);
    this.showSeleccionarCliente.set(true);
  }

  /** Cuando desde el modal de puntos se hace clic en "Continuar Gestión" */
  onResumeVisitaDesdeModal(event: { pdv: PdvForModal; clienteId: number; visitaId: number }): void {
    const pdv = event.pdv;
    const client = pdv.clients.find(c => c.id_cliente === event.clienteId);
    this.ui.openVisit({
      id_visita: event.visitaId,
      pdv_nombre: pdv.nombre,
      id_punto: pdv.id_punto,
      id_cliente: event.clienteId,
      cliente: client?.nombre || '',
    });
    this.showPuntosInteres.set(false);
  }

  /** Cuando se creó la visita desde SeleccionarClienteModal */
  onVisitaCreada(event: { id_visita: number; id_cliente: number; cliente: string }): void {
    const pdv = this.puntoParaSeleccionar();
    if (pdv) {
      this.ui.openVisit({
        id_visita: event.id_visita,
        pdv_nombre: pdv.nombre,
        id_punto: pdv.id_punto,
        id_cliente: event.id_cliente,
        cliente: event.cliente,
      });
    }
    this.showSeleccionarCliente.set(false);
    this.activationPhotoFromModal.set(null);
    this.puntoParaSeleccionar.set(null);
    this.loadData();
  }
}
