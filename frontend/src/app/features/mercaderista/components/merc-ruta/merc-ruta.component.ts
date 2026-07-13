import { Component, OnInit, OnDestroy, signal, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import maplibregl from 'maplibre-gl';
import { ApiService } from '../../../../core/services/api.service';
import { MercUiService } from '../../services/merc-ui.service';

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
  hasVisited: boolean;
  clients: PdvClient[];
}

@Component({
  selector: 'app-merc-ruta',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatButtonModule, MatProgressSpinnerModule, MatSnackBarModule],
  template: `
    <div class="flex flex-col h-full bg-slate-50 dark:bg-slate-950">
      
      <!-- TABS (Fixed at top) -->
      <div class="bg-white dark:bg-slate-900 px-6 pt-6 border-b border-slate-200 dark:border-white/5 shrink-0">
        <h2 class="text-2xl font-black text-slate-800 dark:text-white tracking-tight italic uppercase mb-4">Mi Ruta</h2>
        <div class="flex gap-8">
          <button (click)="changeTab('fija')" 
                  [class]="activeTab() === 'fija' ? 'text-primary-500 border-b-4 border-primary-500' : 'text-slate-400 border-b-4 border-transparent'"
                  class="pb-3 text-xs font-black uppercase tracking-widest transition-all">
            Rutas Fijas
          </button>
          <button (click)="changeTab('variable')" 
                  [class]="activeTab() === 'variable' ? 'text-primary-500 border-b-4 border-primary-500' : 'text-slate-400 border-b-4 border-transparent'"
                  class="pb-3 text-xs font-black uppercase tracking-widest transition-all">
            Rutas Variables
          </button>
        </div>
      </div>

      <!-- LIST AREA -->
      <div class="flex-grow overflow-y-auto p-6 space-y-6">
        
        @if (loading()) {
          <div class="py-20 flex flex-col items-center gap-3">
            <mat-spinner diameter="32"></mat-spinner>
            <span class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Sincronizando ruta...</span>
          </div>
        } @else if (!selectedRouteId()) {
          <!-- 1. Route Selection -->
          <div class="space-y-3">
            <p class="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] mb-4">Selecciona una ruta para hoy</p>
            @for (ruta of filteredRutas(); track ruta.id_ruta) {
              <div (click)="selectRoute(ruta)" 
                   class="bg-white dark:bg-slate-900 p-5 rounded-[1.5rem] border border-slate-100 dark:border-white/5 shadow-sm active:scale-[0.98] transition-all cursor-pointer">
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-4">
                    <div class="w-10 h-10 rounded-2xl bg-primary-500/10 text-primary-500 flex items-center justify-center">
                      <mat-icon>route</mat-icon>
                    </div>
                    <div>
                      <h4 class="font-bold text-slate-800 dark:text-white tracking-tight">{{ ruta.nombre }}</h4>
                      <span class="text-[9px] font-black text-slate-400 uppercase tracking-widest">ID: {{ ruta.id_ruta }}</span>
                    </div>
                  </div>
                  <mat-icon class="text-slate-200">chevron_right</mat-icon>
                </div>
              </div>
            } @empty {
              <div class="py-12 text-center opacity-40 grayscale italic">
                <p class="text-xs text-slate-400 uppercase font-black tracking-widest">No hay rutas {{ activeTab() }}s hoy</p>
              </div>
            }
          </div>
        } @else if (!routeExecuted()) {
          <!-- 2. Execute Route Overview -->
          <div class="space-y-6">
            <button (click)="selectedRouteId.set(null)" class="flex items-center gap-2 text-slate-400 active:scale-95 transition-all">
              <mat-icon class="!text-sm">arrow_back</mat-icon>
              <span class="text-[10px] font-black uppercase tracking-widest">Volver</span>
            </button>

            <div class="bg-gradient-to-br from-primary-600 to-indigo-700 p-8 rounded-[2.5rem] text-white shadow-xl shadow-primary-500/20 relative overflow-hidden">
              <div class="relative z-10 space-y-4">
                <div>
                  <span class="text-[10px] font-black uppercase tracking-[0.3em] opacity-70">Ruta Seleccionada</span>
                  <h3 class="text-2xl font-black italic uppercase tracking-tighter">{{ selectedRoute()?.nombre }}</h3>
                </div>
                <div class="flex gap-4">
                  <div class="flex flex-col">
                    <span class="text-[9px] font-black uppercase opacity-60">PDVs de la ruta</span>
                    <span class="text-lg font-black">{{ groupedPdvs().length }}</span>
                  </div>
                  <div class="w-px h-8 bg-white/20 mt-2"></div>
                  <div class="flex flex-col">
                    <span class="text-[9px] font-black uppercase opacity-60">Tipo</span>
                    <span class="text-lg font-black capitalize">{{ activeTab() }}</span>
                  </div>
                </div>
                <button (click)="ejecutarRuta()" class="w-full py-4 bg-white text-primary-600 rounded-2xl font-black uppercase tracking-widest text-xs active:scale-95 transition-all shadow-lg">
                  Ejecutar Ruta
                </button>
              </div>
              <div class="absolute -top-20 -right-20 w-64 h-64 bg-white/10 rounded-full blur-3xl"></div>
            </div>
          </div>
        } @else {
          <!-- 3. PDV List / Execution -->
          <div class="space-y-4 pb-20">
            <div class="flex items-center justify-between mb-2">
              <button (click)="routeExecuted.set(false)" class="flex items-center gap-2 text-slate-400">
                <mat-icon class="!text-sm">arrow_back</mat-icon>
                <span class="text-[10px] font-black uppercase tracking-widest">Resumen</span>
              </button>
              <span class="text-[10px] font-black text-primary-500 uppercase tracking-widest bg-primary-500/10 px-3 py-1 rounded-full">En Ejecución</span>
            </div>

            @for (group of groupedPdvs(); track group.id_punto) {
              <div class="bg-white dark:bg-slate-900 rounded-[1.5rem] border border-slate-100 dark:border-white/5 p-5 shadow-sm space-y-4">
                <div class="flex items-start gap-4">
                  <div [class]="group.hasVisited ? 'bg-emerald-500/10 text-emerald-500' : 'bg-slate-100 dark:bg-white/5 text-slate-400'" 
                       class="w-12 h-12 rounded-2xl flex items-center justify-center shrink-0 transition-colors">
                    <mat-icon>{{ group.hasVisited ? 'check_circle' : 'storefront' }}</mat-icon>
                  </div>
                  <div class="flex-grow min-w-0">
                    <div class="flex items-center gap-2 mb-0.5">
                       <span class="text-[10px] font-black text-primary-500 uppercase tracking-widest truncate">{{ group.cadena }}</span>
                       @if (group.latitud && group.longitud) {
                         <mat-icon class="!text-[10px] text-slate-300">location_on</mat-icon>
                       }
                    </div>
                    <h4 class="font-bold text-slate-800 dark:text-white truncate tracking-tight">{{ group.nombre }}</h4>
                    <p class="text-[10px] text-slate-500 dark:text-slate-400 line-clamp-1 italic">{{ group.direccion }}</p>
                  </div>
                </div>

                <!-- Action Button: Activation or Enter -->
                <div class="pt-2">
                  @if (activatingPdvId() === group.id_punto) {
                    <!-- Client Selection After Activation -->
                    <div class="bg-slate-50 dark:bg-slate-950 rounded-2xl p-4 space-y-3 animate-in fade-in zoom-in duration-200">
                      <p class="text-[9px] font-black text-slate-400 uppercase tracking-widest">Selecciona el Cliente</p>
                      <div class="grid grid-cols-1 gap-2">
                        @for (c of group.clients; track c.id_cliente) {
                          <button (click)="iniciar(group, c)" 
                                  class="w-full p-3 rounded-xl border border-slate-200 dark:border-white/5 bg-white dark:bg-slate-900 text-left hover:border-primary-500 transition-all flex items-center justify-between group/btn">
                            <span class="text-xs font-bold text-slate-700 dark:text-slate-200">{{ c.nombre }}</span>
                            <mat-icon class="text-slate-300 group-hover/btn:text-primary-500 transition-colors">arrow_forward</mat-icon>
                          </button>
                        }
                      </div>
                      <button (click)="activatingPdvId.set(null)" class="w-full py-2 text-[9px] font-black text-slate-400 uppercase tracking-widest">Cancelar</button>
                    </div>
                  } @else {
                    <button (click)="triggerActivation(group)" 
                            [class]="group.hasVisited ? 'bg-slate-100 dark:bg-white/5 text-slate-600 dark:text-slate-300' : 'bg-primary-600 text-white shadow-lg shadow-primary-600/20'"
                            class="w-full py-3 rounded-xl text-xs font-black uppercase tracking-widest active:scale-95 transition-all flex items-center justify-center gap-2">
                      <mat-icon class="!text-sm">{{ group.hasVisited ? 'visibility' : 'camera_alt' }}</mat-icon>
                      {{ group.hasVisited ? 'Ver Visitas' : 'Activar PDV' }}
                    </button>
                  }
                </div>
              </div>
            } @empty {
              <div class="py-16 text-center opacity-50">
                <mat-icon class="!text-5xl text-slate-300">wrong_location</mat-icon>
                <p class="text-xs font-black text-slate-400 uppercase tracking-widest mt-2">Esta ruta no tiene PDV activos</p>
              </div>
            }
          </div>
        }

      </div>

      <!-- Hidden Camera Input -->
      <input type="file" #cameraInput accept="image/*" capture="camera" class="hidden" (change)="onActivationPhoto($event)">
    </div>
  `,
  styles: [`:host { display: block; height: 100%; }`]
})
export class MercRutaComponent implements OnInit, OnDestroy {
  private api = inject(ApiService);
  private snack = inject(MatSnackBar);
  private ui = inject(MercUiService);

  loading = signal(true);
  activeTab = signal<'fija' | 'variable'>('fija');
  rutas = signal<any[]>([]);
  pdvs = signal<any[]>([]);
  selectedRouteId = signal<number | null>(null);
  routeExecuted = signal(false);
  
  private map: maplibregl.Map | null = null;
  private markers: maplibregl.Marker[] = [];

  activatingPdvId = signal<string | null>(null);
  activationGroup = signal<PdvGroup | null>(null);

  filteredRutas = computed(() => {
    return this.rutas().filter(r => r.tipo.toLowerCase() === this.activeTab().toLowerCase());
  });

  selectedRoute = computed(() => {
    return this.rutas().find(r => r.id_ruta === this.selectedRouteId());
  });

  pdvsOfSelectedRoute = computed(() => {
    return this.pdvs().filter(p => p.id_ruta === this.selectedRouteId());
  });

  groupedPdvs = computed<PdvGroup[]>(() => {
    const list = this.pdvsOfSelectedRoute();
    const groups: Record<string, PdvGroup> = {};
    
    list.forEach(p => {
      if (!groups[p.id_punto]) {
        groups[p.id_punto] = { 
          id_punto: p.id_punto,
          nombre: p.nombre,
          cadena: p.cadena,
          direccion: p.direccion,
          latitud: p.latitud,
          longitud: p.longitud,
          clients: [],
          hasVisited: false 
        };
      }
      groups[p.id_punto].clients.push({ 
        id_cliente: p.id_cliente, 
        nombre: p.cliente, 
        visitado: p.visitado, 
        visita_id: p.visita_id 
      });
      if (p.visitado) groups[p.id_punto].hasVisited = true;
    });
    
    return Object.values(groups);
  });

  ngOnInit(): void {
    this.loadData();
  }

  ngOnDestroy(): void {
    if (this.map) this.map.remove();
  }

  loadData(): void {
    this.loading.set(true);
    this.api.getMercMiRuta().subscribe({
      next: (res) => {
        this.rutas.set(res.rutas || []);
        this.pdvs.set(res.pdvs || []);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.snack.open('Error al cargar datos', 'OK', { duration: 3000 });
      }
    });
  }

  changeTab(tab: 'fija' | 'variable') {
    this.activeTab.set(tab);
    this.selectedRouteId.set(null);
    this.routeExecuted.set(false);
  }

  selectRoute(ruta: any): void {
    this.selectedRouteId.set(ruta.id_ruta);
    this.routeExecuted.set(false);
    this.loadRoutePdvs(ruta.id_ruta);
  }

  /** Carga TODOS los PDV de la ruta (sin filtro de día) para que aparezcan al ejecutar. */
  loadRoutePdvs(idRuta: number): void {
    this.api.getMercRutaPdvs(idRuta).subscribe({
      next: (res) => this.pdvs.set(res.pdvs || []),
      error: () => {},
    });
  }

  ejecutarRuta(): void {
    // Sin mapa: al ejecutar mostramos directamente los PDV de la ruta (flujo v1).
    this.routeExecuted.set(true);
  }

  initMap(): void {
    const el = document.getElementById('merc-map');
    if (!el) return;
    if (this.map) this.map.remove();

    this.map = new maplibregl.Map({
      container: el,
      style: 'https://tiles.openfreemap.org/styles/liberty',
      center: [-66.90, 10.48],
      zoom: 12
    });

    this.markers = [];
    const bounds = new maplibregl.LngLatBounds();
    let hasPoints = false;

    this.groupedPdvs().forEach(pdv => {
      if (pdv.latitud && pdv.longitud) {
        hasPoints = true;
        const marker = new maplibregl.Marker({ 
          color: pdv.hasVisited ? '#10b981' : '#6366f1',
          scale: 0.8 
        })
        .setLngLat([pdv.longitud, pdv.latitud])
        .setPopup(new maplibregl.Popup({ offset: 25 }).setHTML(`
          <div style="padding:4px">
            <div style="font-weight:900;font-size:11px">${pdv.nombre}</div>
            <div style="font-size:9px;color:#64748b">${pdv.cadena}</div>
          </div>
        `))
        .addTo(this.map!);
        this.markers.push(marker);
        bounds.extend([pdv.longitud, pdv.latitud]);
      }
    });

    if (hasPoints) {
      this.map.fitBounds(bounds, { padding: 40, maxZoom: 15 });
    }
  }

  centerOnUser(): void {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(pos => {
      if (this.map) {
        this.map.flyTo({ center: [pos.coords.longitude, pos.coords.latitude], zoom: 15 });
        new maplibregl.Marker({ color: '#f43f5e', scale: 0.6 })
          .setLngLat([pos.coords.longitude, pos.coords.latitude])
          .addTo(this.map);
      }
    });
  }

  triggerActivation(group: PdvGroup): void {
    if (group.hasVisited) {
      this.activatingPdvId.set(group.id_punto);
      return;
    }
    
    this.activationGroup.set(group);
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    if (input) input.click();
  }

  onActivationPhoto(event: Event): void {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file) return;

    const group = this.activationGroup();
    if (group) {
      this.activatingPdvId.set(group.id_punto);
      this.snack.open('Foto de activación capturada', 'OK', { duration: 2000 });
    }
  }

  iniciar(group: PdvGroup, client: PdvClient): void {
    if (client.visitado && client.visita_id) {
      this.ui.openVisit({
        id_visita: client.visita_id,
        pdv_nombre: group.nombre,
        id_cliente: client.id_cliente,
        cliente: client.nombre
      });
      return;
    }

    this.api.iniciarVisita({ id_punto: group.id_punto, id_cliente: client.id_cliente }).subscribe({
      next: (res) => {
        this.ui.openVisit({
          id_visita: res.id_visita,
          pdv_nombre: group.nombre,
          id_cliente: client.id_cliente,
          cliente: client.nombre
        });
        
        this.activatingPdvId.set(null);
        this.activationGroup.set(null);
        this.loadData();
      },
      error: () => this.snack.open('Error al iniciar visita', 'OK', { duration: 3000 })
    });
  }
}
