import { Component, OnInit, signal, inject, computed, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ApiService } from '../../../../core/services/api.service';
import { MercUiService } from '../../services/merc-ui.service';
import { OfflineQueueService } from '../../services/offline-queue.service';
import { ConfirmService } from '../../../../shared/components/confirm-dialog/confirm.service';

@Component({
  selector: 'app-merc-visitas',
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule, MatButtonModule, MatProgressSpinnerModule],
  template: `
    <div class="flex flex-col h-full bg-slate-50 dark:bg-slate-950">

      <!-- FILTROS -->
      <div class="bg-white dark:bg-slate-900 border-b border-slate-100 dark:border-white/5 p-4 space-y-3">
        <!-- Fechas -->
        <div class="flex gap-2 items-end">
          <div class="flex-1">
            <label class="block text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">Desde</label>
            <input type="date" [(ngModel)]="fechaDesde" (change)="cargar()"
                   class="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-white/10 rounded-xl text-xs font-bold text-slate-700 dark:text-white outline-none focus:ring-2 focus:ring-primary-500 transition-all">
          </div>
          <div class="flex-1">
            <label class="block text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">Hasta</label>
            <input type="date" [(ngModel)]="fechaHasta" (change)="cargar()"
                   class="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-white/10 rounded-xl text-xs font-bold text-slate-700 dark:text-white outline-none focus:ring-2 focus:ring-primary-500 transition-all">
          </div>
          @if (fechaDesde || fechaHasta) {
            <button (click)="limpiarFechas()" class="mb-0.5 p-2 text-slate-400 hover:text-rose-500 transition-colors rounded-xl hover:bg-rose-50 dark:hover:bg-rose-500/10">
              <mat-icon class="!text-lg">clear</mat-icon>
            </button>
          }
        </div>

        <!-- PDV Search -->
        <div class="relative">
          <mat-icon class="absolute left-3 top-1/2 -translate-y-1/2 !text-slate-400 !text-sm">search</mat-icon>
          <input type="text" [(ngModel)]="pdvQuery"
                 placeholder="Nombre del PDV (ej. Central Madeirense)..."
                 class="w-full pl-9 pr-4 py-2.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-white/10 rounded-xl text-xs font-bold outline-none focus:ring-2 focus:ring-primary-500 transition-all">
        </div>

        <!-- Cliente Filter -->
        <select [(ngModel)]="filtroCliente"
                class="w-full px-3 py-2.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-white/10 rounded-xl text-xs font-bold text-slate-700 dark:text-white outline-none focus:ring-2 focus:ring-primary-500">
          <option value="">Todos los clientes</option>
          @for (c of clientesUnicos(); track c.id) {
            <option [value]="c.id">{{ c.nombre }}</option>
          }
        </select>
      </div>

      <!-- CONTENIDO -->
      <div class="flex-grow overflow-y-auto">
        @if (loading()) {
          <div class="py-20 flex flex-col items-center gap-3">
            <mat-spinner diameter="32"></mat-spinner>
            <span class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Cargando visitas...</span>
          </div>
        } @else {
          <div class="p-4 space-y-4">

            <!-- BANNER SIN CONEXIÓN -->
            @if (sinConexion()) {
              <div class="bg-orange-500/10 border border-orange-500/20 rounded-2xl p-3 flex items-center gap-3">
                <mat-icon class="text-orange-500 !text-lg">wifi_off</mat-icon>
                <p class="text-xs text-orange-600 dark:text-orange-400 font-bold leading-relaxed">Sin conexión: solo se muestran las visitas locales guardadas en el dispositivo.</p>
              </div>
            }

            <!-- SECCIÓN: PENDIENTES DE ENVIAR (chains offline) -->
            @if (visitasLocales().length > 0) {
              <div>
                <h4 class="text-xs font-black text-slate-500 uppercase tracking-widest mb-2 px-1">Pendientes de enviar</h4>
                <div class="space-y-2">
                  @for (v of visitasLocales(); track v.chainId) {
                    <div class="bg-amber-50 dark:bg-amber-500/5 border border-amber-200 dark:border-amber-500/20 rounded-2xl p-4 flex items-start gap-3">
                      <div class="w-10 h-10 rounded-xl bg-amber-500/10 flex items-center justify-center shrink-0">
                        <mat-icon class="text-amber-500 !text-xl">cloud_upload</mat-icon>
                      </div>
                      <div class="flex-1 min-w-0">
                        <p class="font-bold text-sm text-slate-800 dark:text-white leading-snug">{{ v.pdv_nombre || 'Visita local' }}</p>
                        <p class="text-[10px] text-slate-500 font-bold uppercase tracking-widest mt-0.5">{{ v.cliente }}</p>
                        <p class="text-[10px] text-amber-600 dark:text-amber-400 font-bold mt-1">
                          {{ v.stepCount }} elemento(s) por enviar
                        </p>
                      </div>
                      <span class="bg-amber-500/15 text-amber-600 text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full whitespace-nowrap">Pendiente</span>
                    </div>
                  }
                </div>
              </div>
            }

            <!-- SECCIÓN: HISTORIAL DEL SERVIDOR -->
            <div>
              <h4 class="text-xs font-black text-slate-500 uppercase tracking-widest mb-2 px-1">Historial</h4>

              @if (visitasFiltradas().length === 0 && !sinConexion()) {
                <div class="py-12 text-center opacity-40 space-y-2">
                  <mat-icon class="!text-5xl text-slate-400">assignment</mat-icon>
                  <p class="text-xs font-bold text-slate-500">No hay visitas para estos filtros</p>
                </div>
              }

              <div class="space-y-2">
                @for (v of visitasFiltradas(); track v.id_visita) {
                  <div class="bg-white dark:bg-slate-900 border border-slate-100 dark:border-white/5 rounded-2xl overflow-hidden shadow-sm">

                    <!-- Cuerpo clickable -->
                    <div (click)="verDetalle(v)"
                         class="p-4 flex items-start gap-3 cursor-pointer active:bg-slate-50 dark:active:bg-white/5 transition-colors">

                      <!-- Ícono estado data -->
                      <div class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 mt-0.5"
                           [class]="tieneData(v) ? 'bg-emerald-500/10' : 'bg-slate-100 dark:bg-white/5'">
                        <mat-icon [class]="tieneData(v) ? 'text-emerald-500' : 'text-slate-400'" class="!text-xl">
                          {{ tieneData(v) ? 'assignment_turned_in' : 'assignment_late' }}
                        </mat-icon>
                      </div>

                      <!-- Info principal -->
                      <div class="flex-1 min-w-0">
                        <p class="font-bold text-sm text-slate-800 dark:text-white leading-snug truncate">
                          {{ v.cliente_nombre || 'Sin cliente' }}
                        </p>
                        <p class="text-[10px] text-slate-500 truncate mt-0.5">
                          {{ v.pdv_nombre || v.identificador_punto_interes }}
                        </p>
                        <p class="text-[10px] text-slate-400 mt-0.5">{{ formatFecha(v.fecha_visita) }}</p>

                        <!-- Stats fotos / balances -->
                        @if (tieneData(v)) {
                          <p class="text-[10px] text-slate-500 mt-1.5 leading-relaxed">
                            <span class="font-bold">{{ v.total_fotos ?? 0 }}</span> foto(s)
                            @if ((v.fotos_rechazadas ?? 0) > 0) {
                              · <span class="text-rose-500 font-bold">{{ v.fotos_rechazadas }} rechazada(s)</span>
                            }
                            @if ((v.fotos_aprobadas ?? 0) > 0) {
                              · <span class="text-emerald-500 font-bold">{{ v.fotos_aprobadas }} aprobada(s)</span>
                            }
                            · <span class="font-bold">{{ v.total_balances ?? 0 }}</span> SKU
                          </p>
                        } @else {
                          <p class="text-[10px] text-slate-400 italic mt-1">Sin data enviada todavía</p>
                        }
                      </div>

                      <!-- Badge estado + flecha -->
                      <div class="flex flex-col items-end gap-2 shrink-0">
                        <span [class]="estadoClass(v.estado)"
                              class="text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full border whitespace-nowrap">
                          {{ estadoLabel(v.estado) }}
                        </span>
                        <mat-icon class="!text-slate-300 !text-sm">chevron_right</mat-icon>
                      </div>
                    </div>

                    <!-- Botón Reabrir (completada, no revisada) -->
                    @if ((v.estado === 'completada' || v.estado === 'Finalizada') && v.estado !== 'Revisado' && v.estado !== 'Revisada') {
                      <div class="px-4 pb-3 pt-0">
                        <button (click)="reabrirVisita(v)"
                                class="w-full py-2.5 border border-amber-400 dark:border-amber-500/50 text-amber-600 dark:text-amber-400 rounded-xl text-[10px] font-black uppercase tracking-widest flex items-center justify-center gap-2 hover:bg-amber-500/10 transition-all active:scale-95">
                          <mat-icon class="!text-sm">replay</mat-icon>
                          Reabrir visita (olvidé una foto)
                        </button>
                      </div>
                    }

                  </div>
                }
              </div>
            </div>

            <div class="h-16"></div>
          </div>
        }
      </div>
    </div>
  `,
  styles: [`:host { display: block; height: 100%; }`]
})
export class MercVisitasComponent implements OnInit {
  private api = inject(ApiService);
  private ui = inject(MercUiService);
  private offline = inject(OfflineQueueService);
  private confirm = inject(ConfirmService);

  loading = signal(true);
  sinConexion = signal(false);
  visitasServidor = signal<any[]>([]);
  visitasLocales = signal<any[]>([]);

  fechaDesde = this.getDefaultDesde();
  fechaHasta = '';
  pdvQuery = '';
  filtroCliente = '';

  constructor() {
    effect(() => {
      const active = this.ui.activeVisit();
      if (!active) {
        this.cargar();
      }
    }, { allowSignalWrites: true });
  }

  clientesUnicos = computed(() => {
    const map = new Map<number, string>();
    for (const v of this.visitasServidor()) {
      if (v.id_cliente) map.set(v.id_cliente, v.cliente_nombre || `Cliente ${v.id_cliente}`);
    }
    return Array.from(map.entries()).map(([id, nombre]) => ({ id, nombre }));
  });

  visitasFiltradas = computed(() => {
    const q = this.pdvQuery.toLowerCase();
    const fc = String(this.filtroCliente);
    return this.visitasServidor().filter(v => {
      // Excluir visitas en estado 'Pendiente' del historial
      if (v.estado === 'Pendiente') return false;

      const matchPdv = !q ||
        (v.pdv_nombre || '').toLowerCase().includes(q) ||
        (v.identificador_punto_interes || '').toLowerCase().includes(q);
      const matchCliente = !fc || String(v.id_cliente) === fc;
      return matchPdv && matchCliente;
    });
  });

  ngOnInit(): void {
    this.cargar();
  }

  private getDefaultDesde(): string {
    const d = new Date();
    d.setDate(d.getDate() - 30);
    return d.toISOString().split('T')[0];
  }

  async cargar(): Promise<void> {
    this.loading.set(true);

    // Cargar cadenas offline locales pendientes
    try {
      const chains = await this.offline.getChains();
      this.visitasLocales.set(
        chains
          .filter((c: any) => c.status !== 'done')
          .map((c: any) => ({
            chainId: c.chainId,
            pdv_nombre: c.iniciarBody?.id_punto || 'Visita offline',
            cliente: `Cliente #${c.iniciarBody?.id_cliente ?? '?'}`,
            stepCount: c.steps?.length ?? 0,
          }))
      );
    } catch {
      this.visitasLocales.set([]);
    }

    // Cargar historial del servidor
    const params: any = {};
    if (this.fechaDesde) params.fecha_inicio = this.fechaDesde;
    if (this.fechaHasta) params.fecha_fin = this.fechaHasta;

    this.api.getMercMisVisitas(params).subscribe({
      next: (res: any[]) => {
        this.visitasServidor.set(res || []);
        this.sinConexion.set(false);
        this.loading.set(false);
      },
      error: () => {
        this.sinConexion.set(true);
        this.loading.set(false);
      }
    });
  }

  limpiarFechas(): void {
    this.fechaDesde = '';
    this.fechaHasta = '';
    this.cargar();
  }

  tieneData(v: any): boolean {
    return (v.total_fotos ?? 0) > 0 || (v.total_balances ?? 0) > 0 || (v.fotos_count ?? 0) > 0;
  }

  formatFecha(raw: string): string {
    if (!raw) return '';
    try {
      return new Date(raw).toLocaleString('es-VE', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit'
      });
    } catch { return raw; }
  }

  estadoClass(estado: string): string {
    if (estado === 'Revisado' || estado === 'Revisada') return 'bg-emerald-500/10 text-emerald-600 border-emerald-500/30';
    if (estado === 'completada' || estado === 'Finalizada') return 'bg-sky-500/10 text-sky-600 border-sky-500/30';
    return 'bg-amber-500/10 text-amber-600 border-amber-500/30';
  }

  estadoLabel(estado: string): string {
    if (estado === 'Revisado' || estado === 'Revisada') return 'Revisada';
    if (estado === 'completada' || estado === 'Finalizada') return 'Completada';
    return 'Pend. revisión';
  }

  verDetalle(v: any): void {
    this.ui.openDetailVisit(v.id_visita);
  }

  async reabrirVisita(v: any): Promise<void> {
    // 1. Pedir el motivo de reapertura
    const motivo = await this.confirm.promptText(
      'Escribe una razón de por qué necesitas reabrir esta visita para completar datos.',
      {
        title: '📝 Motivo de reapertura',
        placeholder: 'Ej: Faltaron fotos del exhibidor, datos de balance incompletos…',
        required: true,
        confirmText: 'Reabrir',
        cancelText: 'Cancelar'
      }
    );
    if (!motivo) return;

    // 2. Confirmar reglas del temporizador
    const confirmed = await this.confirm.confirm(
      '⏱️ Al reabrir esta visita se reactivará el temporizador de 40 minutos.\n\nSolo se abrirá el PDV, no la ruta.\n\nDeberás guardar tus datos o fotos dentro de ese límite para evitar que expire.\n\n¿Estás seguro de que deseas reabrir la visita?',
      { title: '⏰ Reglas del Temporizador', confirmText: 'Reabrir', cancelText: 'Cancelar' }
    );
    if (!confirmed) return;

    try {
      await this.api.post<any>(`/api/merc/visitas/${v.id_visita}/reabrir`, { motivo }).toPromise();
      this.ui.openVisit({
        id_visita: v.id_visita,
        pdv_nombre: v.pdv_nombre,
        id_punto: v.identificador_punto,
        id_cliente: v.id_cliente,
        cliente: v.cliente_nombre
      });
    } catch {
      alert('No se pudo reabrir la visita. Verifica tu conexión.');
    }
  }
}
