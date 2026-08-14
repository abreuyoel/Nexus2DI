import { Component, Input, OnInit, signal, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ApiService } from '../../../../core/services/api.service';
import { MercUiService } from '../../services/merc-ui.service';

interface FotoDetalle {
    id_foto: number;
    estado?: string;
    fecha?: string;
    url?: string;
    tipo_foto?: string;
    categoria?: string;
    motivo_rechazo?: string;
    latitud?: number;
    longitud?: number;
}

interface BalanceDetalle {
    id_balance: number;
    producto?: string;
    categoria?: string;
    fabricante?: string;
    inv_inicial?: number;
    inv_final?: number;
    inv_deposito?: number;
    caras?: number;
    precio_bs?: number;
    precio_ds?: number;
    fefo?: string;
    estado_producto?: string;
    no_existe?: boolean;
}

interface VisitaDetalle {
    id_visita: number;
    fecha?: string;
    estado?: string;
    estado_data?: string;
    punto_nombre?: string;
    cadena?: string;
    direccion?: string;
    cliente_nombre?: string;
    revisada_por?: string;
    fecha_revision?: string;
    fotos: FotoDetalle[];
    balances: BalanceDetalle[];
    punto?: any;
    punto_activado?: boolean;
    es_ultimo_cliente?: boolean;
}

const TIPO_FOTO_LABELS: Record<string, string> = {
    activacion: 'Activación',
    desactivacion: 'Desactivación',
    nevera: 'Nevera',
    gondola: 'Góndola',
    exhibicion: 'Exhibición',
    adicional1: 'Adicional 1',
    adicional2: 'Adicional 2',
    adicional3: 'Adicional 3',
    adicional4: 'Adicional 4',
};

const TIPO_FOTO_COLORS: Record<string, string> = {
    activacion: 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20',
    desactivacion: 'bg-rose-500/10 text-rose-600 border-rose-500/20',
    nevera: 'bg-sky-500/10 text-sky-600 border-sky-500/20',
    gondola: 'bg-amber-500/10 text-amber-600 border-amber-500/20',
    exhibicion: 'bg-purple-500/10 text-purple-600 border-purple-500/20',
    adicional1: 'bg-slate-500/10 text-slate-600 border-slate-500/20',
    adicional2: 'bg-slate-500/10 text-slate-600 border-slate-500/20',
    adicional3: 'bg-slate-500/10 text-slate-600 border-slate-500/20',
    adicional4: 'bg-slate-500/10 text-slate-600 border-slate-500/20',
};

@Component({
    selector: 'app-merc-visita-detalle',
    standalone: true,
    imports: [CommonModule, MatIconModule, MatButtonModule, MatProgressSpinnerModule],
    template: `
    <div class="fixed inset-0 z-[100] flex flex-col overflow-hidden bg-slate-100 dark:bg-slate-950 animate-in slide-in-from-right-full duration-300">

      <!-- Header -->
      <div class="shrink-0 px-4 py-3 flex items-center gap-3 bg-slate-900 text-white border-b border-white/5">
        <button (click)="close()"
                class="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center text-slate-300 active:scale-95 transition-all">
          <mat-icon>arrow_back</mat-icon>
        </button>
        <div class="flex-1 min-w-0">
          <h3 class="font-bold text-sm leading-tight text-white truncate">
            {{ detalle()?.punto_nombre || detalle()?.cliente_nombre || 'Visita' }}
          </h3>
          <span class="text-[9px] font-black text-slate-400 uppercase tracking-widest">
            {{ detalle()?.cliente_nombre || '' }}
            @if (detalle()?.cadena) { · {{ detalle()?.cadena }} }
          </span>
        </div>
      </div>

      <!-- Tabs -->
      <div class="shrink-0 flex border-b border-slate-200 dark:border-white/5 bg-white dark:bg-slate-900 overflow-x-auto">
        @for (tab of tabs; track tab.key) {
          <button (click)="activeTab.set(tab.key)"
                  [class]="activeTab() === tab.key
                    ? 'border-b-2 border-primary-500 text-primary-600 dark:text-primary-400'
                    : 'text-slate-500 border-b-2 border-transparent'"
                  class="flex items-center gap-1.5 px-4 py-3 text-[10px] font-black uppercase tracking-widest whitespace-nowrap transition-colors">
            <mat-icon class="!text-sm">{{ tab.icon }}</mat-icon>
            {{ tab.label }}
          </button>
        }
      </div>

      <!-- Content -->
      <div class="flex-grow overflow-y-auto">
        @if (loading()) {
          <div class="py-20 flex flex-col items-center gap-3">
            <mat-spinner diameter="32"></mat-spinner>
            <span class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Cargando detalle...</span>
          </div>
        } @else if (!detalle()) {
          <div class="py-20 text-center opacity-40 space-y-3">
            <mat-icon class="!text-5xl text-slate-400">error_outline</mat-icon>
            <p class="text-sm font-bold">No se pudo cargar el detalle de esta visita.</p>
          </div>
        } @else {

          <!-- TAB: INFO -->
          @if (activeTab() === 'info') {
            <div class="p-4 space-y-4">
              <!-- Status Card -->
              <div class="bg-white dark:bg-slate-900 border border-slate-100 dark:border-white/5 rounded-2xl p-4 shadow-sm space-y-3">
                <h4 class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Estado</h4>
                <div class="flex items-center gap-3">
                  <span [class]="estadoBadgeClass()"
                        class="text-[9px] font-black uppercase tracking-widest px-3 py-1 rounded-full border">
                    {{ detalle()?.estado || 'Desconocido' }}
                  </span>
                  @if (detalle()?.estado_data) {
                    <span class="text-[10px] text-slate-500 font-bold">
                      Data: {{ detalle()?.estado_data }}
                    </span>
                  }
                </div>
                @if (detalle()?.revisada_por) {
                  <div class="flex items-center gap-2 text-[10px] text-slate-500">
                    <mat-icon class="!text-sm text-slate-400">check_circle</mat-icon>
                    <span>Revisada por <strong class="font-bold text-slate-700 dark:text-slate-300">{{ detalle()?.revisada_por }}</strong>
                    @if (detalle()?.fecha_revision) { — {{ formatFecha(detalle()?.fecha_revision) }} }</span>
                  </div>
                }
              </div>

              <!-- Info Card -->
              <div class="bg-white dark:bg-slate-900 border border-slate-100 dark:border-white/5 rounded-2xl p-4 shadow-sm space-y-3">
                <h4 class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Información</h4>
                <div class="space-y-2 text-xs">
                  @if (detalle()?.punto_nombre) {
                    <div class="flex justify-between">
                      <span class="text-slate-500">PDV</span>
                      <span class="font-bold text-slate-800 dark:text-white text-right max-w-[60%]">{{ detalle()?.punto_nombre }}</span>
                    </div>
                  }
                  @if (detalle()?.cadena) {
                    <div class="flex justify-between">
                      <span class="text-slate-500">Cadena</span>
                      <span class="font-bold text-slate-800 dark:text-white">{{ detalle()?.cadena }}</span>
                    </div>
                  }
                  @if (detalle()?.direccion) {
                    <div class="flex justify-between">
                      <span class="text-slate-500">Dirección</span>
                      <span class="font-bold text-slate-800 dark:text-white text-right max-w-[60%]">{{ detalle()?.direccion }}</span>
                    </div>
                  }
                  @if (detalle()?.cliente_nombre) {
                    <div class="flex justify-between">
                      <span class="text-slate-500">Cliente</span>
                      <span class="font-bold text-slate-800 dark:text-white">{{ detalle()?.cliente_nombre }}</span>
                    </div>
                  }
                  @if (detalle()?.fecha) {
                    <div class="flex justify-between">
                      <span class="text-slate-500">Fecha</span>
                      <span class="font-bold text-slate-800 dark:text-white">{{ formatFecha(detalle()?.fecha) }}</span>
                    </div>
                  }
                  <div class="flex justify-between">
                    <span class="text-slate-500">PDV Activado</span>
                    <span [class]="detalle()?.punto_activado ? 'text-emerald-500 font-bold' : 'text-slate-400'">
                      {{ detalle()?.punto_activado ? 'Sí' : 'No' }}
                    </span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-slate-500">Último Cliente</span>
                    <span [class]="detalle()?.es_ultimo_cliente ? 'text-amber-500 font-bold' : 'text-slate-400'">
                      {{ detalle()?.es_ultimo_cliente ? 'Sí' : 'No' }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          }

          <!-- TAB: FOTOS -->
          @if (activeTab() === 'fotos') {
            <div class="p-4">
              @if (fotosPorTipo().length === 0) {
                <div class="py-16 text-center opacity-40 space-y-3">
                  <mat-icon class="!text-5xl text-slate-400">photo_library</mat-icon>
                  <p class="text-xs font-bold text-slate-500">Sin fotos en esta visita</p>
                </div>
              } @else {
                <div class="space-y-4">
                  @for (grupo of fotosPorTipo(); track grupo.tipo) {
                    <div class="bg-white dark:bg-slate-900 border border-slate-100 dark:border-white/5 rounded-2xl p-4 shadow-sm">
                      <div class="flex items-center justify-between mb-3">
                        <div class="flex items-center gap-2">
                          <span [class]="(tipoFotoColor(grupo.tipo)) + ' text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full border'">
                            {{ tipoFotoLabel(grupo.tipo) }}
                          </span>
                          <span class="text-[10px] text-slate-400 font-bold">{{ grupo.fotos.length }} foto(s)</span>
                        </div>
                      </div>
                      <div class="space-y-3">
                        @for (f of grupo.fotos; track f.id_foto) {
                          <div class="flex items-start gap-3 bg-slate-50 dark:bg-slate-800/50 rounded-xl p-3">
                            <!-- Thumbnail -->
                            @if (f.url) {
                              <div class="w-16 h-16 rounded-lg overflow-hidden shrink-0 bg-slate-200 dark:bg-slate-700">
                                <img [src]="f.url" alt="Foto" class="w-full h-full object-cover" loading="lazy" />
                              </div>
                            } @else {
                              <div class="w-16 h-16 rounded-lg shrink-0 bg-slate-200 dark:bg-slate-700 flex items-center justify-center">
                                <mat-icon class="text-slate-400 !text-lg">image</mat-icon>
                              </div>
                            }
                            <!-- Info -->
                            <div class="flex-1 min-w-0">
                              <div class="flex items-center gap-2 flex-wrap">
                                <span [class]="estadoFotoClass(f.estado)"
                                      class="text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full border">
                                  {{ f.estado || 'pendiente' }}
                                </span>
                                @if (f.categoria) {
                                  <span class="text-[9px] text-slate-500 font-bold">{{ f.categoria }}</span>
                                }
                              </div>
                              @if (f.motivo_rechazo) {
                                <p class="text-[10px] text-rose-500 italic mt-1 leading-relaxed">
                                  Motivo: {{ f.motivo_rechazo }}
                                </p>
                              }
                              <p class="text-[9px] text-slate-400 mt-1">{{ formatFecha(f.fecha) }}</p>
                              @if (f.latitud && f.longitud) {
                                <p class="text-[8px] text-slate-400 mt-0.5">
                                  📍 {{ f.latitud.toFixed(6) }}, {{ f.longitud.toFixed(6) }}
                                </p>
                              }
                            </div>
                          </div>
                        }
                      </div>
                    </div>
                  }
                </div>
              }
            </div>
          }

          <!-- TAB: BALANCE -->
          @if (activeTab() === 'balance') {
            <div class="p-4">
              @if (balances().length === 0) {
                <div class="py-16 text-center opacity-40 space-y-3">
                  <mat-icon class="!text-5xl text-slate-400">inventory_2</mat-icon>
                  <p class="text-xs font-bold text-slate-500">Sin balances en esta visita</p>
                </div>
              } @else {
                <!-- Summary -->
                <div class="bg-white dark:bg-slate-900 border border-slate-100 dark:border-white/5 rounded-2xl p-4 shadow-sm mb-4">
                  <h4 class="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2">Resumen</h4>
                  <div class="flex gap-4 text-xs">
                    <span class="font-bold text-slate-800 dark:text-white">{{ balances().length }} SKU(s)</span>
                    <span class="text-slate-500">{{ categoriasBalance().length }} categoría(s)</span>
                  </div>
                </div>

                <!-- Balances por categoría -->
                @for (cat of categoriasBalance(); track cat) {
                  <div class="bg-white dark:bg-slate-900 border border-slate-100 dark:border-white/5 rounded-2xl p-4 shadow-sm mb-3">
                    <h5 class="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-3">{{ cat || 'Sin categoría' }}</h5>
                    <div class="space-y-2">
                      @for (b of balancesPorCategoria(cat); track b.id_balance) {
                        <div class="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-3">
                          <div class="flex items-start justify-between gap-2">
                            <div class="min-w-0 flex-1">
                              <p class="text-xs font-bold text-slate-800 dark:text-white leading-snug truncate">
                                {{ b.producto || 'Producto #' + b.id_balance }}
                              </p>
                              @if (b.fabricante) {
                                <p class="text-[9px] text-slate-400 mt-0.5">{{ b.fabricante }}</p>
                              }
                              @if (b.no_existe) {
                                <span class="inline-block mt-1 text-[9px] font-bold text-rose-500 bg-rose-500/10 px-2 py-0.5 rounded-full">
                                  No existe en PDV
                                </span>
                              }
                            </div>
                          </div>
                          <div class="grid grid-cols-2 gap-x-4 gap-y-1 mt-2 text-[10px]">
                            @if (b.inv_inicial != null) {
                              <div class="flex justify-between">
                                <span class="text-slate-400">Inv. Inicial</span>
                                <span class="font-bold text-slate-700 dark:text-slate-300">{{ b.inv_inicial }}</span>
                              </div>
                            }
                            @if (b.inv_final != null) {
                              <div class="flex justify-between">
                                <span class="text-slate-400">Inv. Final</span>
                                <span class="font-bold text-slate-700 dark:text-slate-300">{{ b.inv_final }}</span>
                              </div>
                            }
                            @if (b.inv_deposito != null) {
                              <div class="flex justify-between">
                                <span class="text-slate-400">Depósito</span>
                                <span class="font-bold text-slate-700 dark:text-slate-300">{{ b.inv_deposito }}</span>
                              </div>
                            }
                            @if (b.caras != null) {
                              <div class="flex justify-between">
                                <span class="text-slate-400">Caras</span>
                                <span class="font-bold text-slate-700 dark:text-slate-300">{{ b.caras }}</span>
                              </div>
                            }
                            @if (b.precio_bs != null) {
                              <div class="flex justify-between">
                                <span class="text-slate-400">Precio Bs</span>
                                <span class="font-bold text-slate-700 dark:text-slate-300">{{ b.precio_bs }}</span>
                              </div>
                            }
                            @if (b.precio_ds != null) {
                              <div class="flex justify-between">
                                <span class="text-slate-400">Precio $</span>
                                <span class="font-bold text-slate-700 dark:text-slate-300">{{ b.precio_ds }}</span>
                              </div>
                            }
                            @if (b.fefo) {
                              <div class="flex justify-between">
                                <span class="text-slate-400">FEFO</span>
                                <span class="font-bold text-slate-700 dark:text-slate-300">{{ b.fefo }}</span>
                              </div>
                            }
                            @if (b.estado_producto) {
                              <div class="flex justify-between">
                                <span class="text-slate-400">Estado</span>
                                <span class="font-bold text-slate-700 dark:text-slate-300">{{ b.estado_producto }}</span>
                              </div>
                            }
                          </div>
                        </div>
                      }
                    </div>
                  </div>
                }
              }
            </div>
          }

          <!-- TAB: CHAT (histórico de mensajes 1-a-1 de esta visita) -->
          @if (activeTab() === 'chat') {
            <div class="p-4">
              @if (chatMessages().length === 0) {
                <div class="py-16 text-center opacity-40 space-y-3">
                  <mat-icon class="!text-5xl text-slate-400">chat_bubble_outline</mat-icon>
                  <p class="text-xs font-bold text-slate-500">Sin mensajes en esta visita</p>
                </div>
              } @else {
                <div class="space-y-2">
                  @for (m of chatMessages(); track $index) {
                    <div [class]="m.es_mio ? 'flex justify-end' : 'flex justify-start'">
                      <div [class]="m.es_mio
                          ? 'bg-primary-600 text-white rounded-2xl rounded-br-md max-w-[80%]'
                          : 'bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 border border-slate-100 dark:border-white/5 rounded-2xl rounded-bl-md max-w-[80%]'"
                           class="px-3.5 py-2 shadow-sm">
                        @if (!m.es_mio && m.username) {
                          <p class="text-[9px] font-black text-primary-500 uppercase tracking-wider mb-0.5">{{ m.username }}</p>
                        }
                        <p class="text-xs leading-relaxed whitespace-pre-wrap break-words">{{ m.mensaje }}</p>
                        <p [class]="m.es_mio ? 'text-white/60' : 'text-slate-400'"
                           class="text-[8px] font-medium text-right mt-1">
                          {{ formatFecha(m.fecha_envio) }}
                        </p>
                      </div>
                    </div>
                  }
                </div>
              }
            </div>
          }

        }
      </div>
    </div>
  `,
    styles: [`:host { display: block; height: 100%; }`]
})
export class MercVisitaDetalleComponent implements OnInit {
    @Input() visitaId!: number;

    private api = inject(ApiService);
    private ui = inject(MercUiService);

    detalle = signal<VisitaDetalle | null>(null);
    loading = signal(true);
    activeTab = signal<'info' | 'fotos' | 'balance' | 'chat'>('info');
    chatMessages = signal<any[]>([]);

    tabs: { key: 'info' | 'fotos' | 'balance' | 'chat'; label: string; icon: string }[] = [
        { key: 'info', label: 'Info', icon: 'info' },
        { key: 'fotos', label: 'Fotos', icon: 'photo_library' },
        { key: 'balance', label: 'Balance', icon: 'inventory_2' },
        { key: 'chat', label: 'Chat', icon: 'chat' },
    ];

    balances = computed<BalanceDetalle[]>(() => this.detalle()?.balances ?? []);

    fotosPorTipo = computed<{ tipo: string; fotos: FotoDetalle[] }[]>(() => {
        const fotos = this.detalle()?.fotos ?? [];
        const map = new Map<string, FotoDetalle[]>();
        fotos.forEach(f => {
            const tipo = f.tipo_foto || 'otro';
            if (!map.has(tipo)) map.set(tipo, []);
            map.get(tipo)!.push(f);
        });
        // Orden: activacion primero, desactivacion último, resto alfabético
        const orden = ['activacion', 'nevera', 'gondola', 'exhibicion', 'adicional1', 'adicional2', 'adicional3', 'adicional4', 'desactivacion'];
        return Array.from(map.entries()).sort((a, b) => {
            const ia = orden.indexOf(a[0]);
            const ib = orden.indexOf(b[0]);
            return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
        }).map(([tipo, fotos]) => ({ tipo, fotos }));
    });

    categoriasBalance = computed<string[]>(() => {
        const cats = new Set<string>();
        this.balances().forEach(b => {
            if (b.categoria) cats.add(b.categoria);
        });
        return Array.from(cats).sort();
    });

    balancesPorCategoria(cat: string): BalanceDetalle[] {
        return this.balances().filter(b => b.categoria === cat);
    }

    ngOnInit(): void {
        this.loadDetalle();
        this.loadChat();
    }

    loadDetalle(): void {
        this.loading.set(true);
        this.api.get<VisitaDetalle>(`/api/merc/visitas/${this.visitaId}/detalle`).subscribe({
            next: (res) => {
                this.detalle.set(res);
                this.loading.set(false);
            },
            error: () => this.loading.set(false),
        });
    }

    loadChat(): void {
        this.api.get<any[]>(`/api/merc/chat/visitas/${this.visitaId}`).subscribe({
            next: (res) => this.chatMessages.set(res || []),
            error: () => { },
        });
    }

    close(): void {
        this.ui.closeDetailVisit();
    }

    // --- Helpers ---

    tipoFotoLabel(tipo: string): string {
        return TIPO_FOTO_LABELS[tipo] ?? tipo;
    }

    tipoFotoColor(tipo: string): string {
        return TIPO_FOTO_COLORS[tipo] ?? 'bg-slate-500/10 text-slate-600 border-slate-500/20';
    }

    estadoFotoClass(estado?: string): string {
        switch (estado) {
            case 'aprobado': return 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20';
            case 'rechazado': return 'bg-rose-500/10 text-rose-600 border-rose-500/20';
            case 'pendiente': return 'bg-amber-500/10 text-amber-600 border-amber-500/20';
            default: return 'bg-slate-500/10 text-slate-600 border-slate-500/20';
        }
    }

    estadoBadgeClass(): string {
        const estado = this.detalle()?.estado || '';
        switch (estado.toLowerCase()) {
            case 'completada':
            case 'finalizada':
                return 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20';
            case 'en progreso':
            case 'activa':
                return 'bg-amber-500/10 text-amber-600 border-amber-500/20';
            case 'revisado':
            case 'revisada':
                return 'bg-indigo-500/10 text-indigo-600 border-indigo-500/20';
            default:
                return 'bg-slate-500/10 text-slate-600 border-slate-500/20';
        }
    }

    formatFecha(raw?: string): string {
        if (!raw) return '';
        try {
            const d = new Date(raw);
            return d.toLocaleDateString('es-VE', {
                day: '2-digit', month: 'short', year: 'numeric',
                hour: '2-digit', minute: '2-digit'
            });
        } catch { return raw; }
    }
}
