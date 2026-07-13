import { Component, OnInit, signal, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { ApiService } from '../../../../core/services/api.service';
import { MercUiService } from '../../services/merc-ui.service';

@Component({
  selector: 'app-merc-visitas',
  standalone: true,
  imports: [
    CommonModule, FormsModule, MatIconModule, MatButtonModule, 
    MatProgressSpinnerModule, MatFormFieldModule, MatInputModule, MatSelectModule
  ],
  template: `
    <div class="flex flex-col h-full bg-slate-50 dark:bg-slate-950">
      
      <!-- MODE TOGGLE -->
      <div class="p-6 bg-white dark:bg-slate-900 border-b border-slate-100 dark:border-white/5 space-y-6">
        <div class="flex items-center justify-between">
          <h2 class="text-2xl font-black text-slate-800 dark:text-white uppercase tracking-tight italic">Mi Actividad</h2>
          <div class="flex bg-slate-100 dark:bg-slate-800 p-1 rounded-xl">
            <button (click)="mode.set('visitas')" 
                    [class]="mode() === 'visitas' ? 'bg-white dark:bg-slate-700 text-primary-600 shadow-sm' : 'text-slate-400'"
                    class="px-4 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all">
              Visitas
            </button>
            <button (click)="mode.set('data')" 
                    [class]="mode() === 'data' ? 'bg-white dark:bg-slate-700 text-primary-600 shadow-sm' : 'text-slate-400'"
                    class="px-4 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all">
              Data
            </button>
          </div>
        </div>

        <!-- FILTERS -->
        <div class="grid grid-cols-2 gap-3">
          <div class="col-span-2 relative">
            <mat-icon class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 !text-sm">search</mat-icon>
            <input type="text" [(ngModel)]="searchQuery" 
                   placeholder="Buscar PDV o Cliente..." 
                   class="w-full pl-10 pr-4 py-3 bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-white/5 rounded-2xl text-xs focus:ring-2 focus:ring-primary-500 outline-none transition-all">
          </div>
          
          <mat-select [(ngModel)]="selectedChain" placeholder="Cadena" class="bg-slate-50 dark:bg-slate-950 px-4 py-2.5 rounded-xl border border-slate-100 dark:border-white/5 text-[10px] font-bold">
            <mat-option [value]="''">Todas las Cadenas</mat-option>
            @for (c of chains(); track c) {
              <mat-option [value]="c">{{ c }}</mat-option>
            }
          </mat-select>

          <mat-select [(ngModel)]="selectedClient" placeholder="Cliente" class="bg-slate-50 dark:bg-slate-950 px-4 py-2.5 rounded-xl border border-slate-100 dark:border-white/5 text-[10px] font-bold">
            <mat-option [value]="''">Todos los Clientes</mat-option>
            @for (c of clients(); track c) {
              <mat-option [value]="c">{{ c }}</mat-option>
            }
          </mat-select>
        </div>
      </div>

      <!-- CONTENT AREA -->
      <div class="flex-grow overflow-y-auto p-6">
        
        @if (loading()) {
          <div class="py-20 flex flex-col items-center gap-3">
            <mat-spinner diameter="32"></mat-spinner>
            <span class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Cargando historial...</span>
          </div>
        } @else if (filteredVisitas().length === 0) {
          <div class="py-20 text-center flex flex-col items-center gap-4 opacity-30 grayscale italic">
            <mat-icon class="!text-6xl">query_stats</mat-icon>
            <p class="font-black uppercase tracking-widest text-xs">No se encontraron registros</p>
          </div>
        } @else {
          <div class="space-y-4">
            @for (v of filteredVisitas(); track v.id_visita) {
              <div class="bg-white dark:bg-slate-900 rounded-[2rem] border border-slate-100 dark:border-white/5 p-6 shadow-sm">
                
                <div class="flex justify-between items-start mb-6">
                  <div class="flex items-center gap-4">
                    <div class="w-12 h-12 rounded-2xl bg-slate-50 dark:bg-white/5 flex items-center justify-center text-slate-400">
                      <mat-icon>{{ mode() === 'visitas' ? 'store' : 'analytics' }}</mat-icon>
                    </div>
                    <div class="flex flex-col min-w-0">
                      <span class="text-[10px] font-black text-primary-500 uppercase tracking-widest truncate">{{ v.cliente_nombre }}</span>
                      <h4 class="font-bold text-slate-800 dark:text-white truncate tracking-tight">{{ v.pdv_nombre }}</h4>
                      <div class="flex items-center gap-2 mt-0.5">
                        <span class="text-[9px] font-black text-slate-400 uppercase tracking-widest">{{ v.cadena }}</span>
                        <span class="text-slate-200 dark:text-white/10">•</span>
                        <span class="text-[9px] font-black text-slate-400 uppercase tracking-widest">{{ v.fecha | date:'shortDate' }}</span>
                      </div>
                    </div>
                  </div>
                  <div [class]="v.estado === 'Revisada' ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20' : 'bg-amber-500/10 text-amber-500 border-amber-500/20'" 
                       class="px-3 py-1 rounded-full border text-[9px] font-black uppercase tracking-widest">
                    {{ v.estado }}
                  </div>
                </div>

                @if (mode() === 'visitas') {
                  <!-- Summary Stats for Visits -->
                  <div class="grid grid-cols-2 gap-3 mb-6">
                    <div class="bg-slate-50 dark:bg-slate-800/40 p-3 rounded-2xl border border-slate-100 dark:border-white/5">
                      <div class="flex items-center gap-2 text-[9px] font-black text-slate-400 uppercase mb-1">
                        <mat-icon class="!text-xs">photo_library</mat-icon> Fotos Enviadas
                      </div>
                      <span class="text-lg font-black text-slate-800 dark:text-white">{{ v.fotos_count }}</span>
                    </div>
                    <div class="bg-slate-50 dark:bg-slate-800/40 p-3 rounded-2xl border border-slate-100 dark:border-white/5">
                      <div class="flex items-center gap-2 text-[9px] font-black text-slate-400 uppercase mb-1">
                        <mat-icon class="!text-xs">inventory_2</mat-icon> SKU Cargados
                      </div>
                      <span class="text-lg font-black text-slate-800 dark:text-white">{{ v.balances_count }}</span>
                    </div>
                  </div>
                } @else {
                  <!-- Data View (Preview of balances) -->
                  <div class="bg-primary-500/5 dark:bg-primary-500/10 rounded-2xl p-4 mb-6 border border-primary-500/10">
                     <div class="flex items-center justify-between mb-2">
                       <span class="text-[10px] font-black uppercase tracking-widest text-primary-600 dark:text-primary-400">Último Balance</span>
                       <span class="text-[9px] font-bold text-slate-400">{{ v.balances_count }} productos</span>
                     </div>
                     <p class="text-xs text-slate-600 dark:text-slate-400 italic">Haz clic para ver el detalle de inventario, precios y FIFO registrados.</p>
                  </div>
                }

                <button (click)="verDetalle(v)" class="w-full py-3.5 bg-slate-900 dark:bg-white/10 hover:bg-black dark:hover:bg-white/20 text-white rounded-2xl text-xs font-black uppercase tracking-widest shadow-lg active:scale-95 transition-all flex items-center justify-center gap-2">
                  <mat-icon class="!text-sm">visibility</mat-icon>
                  {{ mode() === 'visitas' ? 'Revisar Visita' : 'Ver Inventario' }}
                </button>
              </div>
            }
          </div>
        }

        <div class="h-20"></div>
      </div>
    </div>
  `,
  styles: [`
    :host { display: block; height: 100%; }
    ::ng-deep .mat-mdc-select-value { font-size: 10px !important; font-weight: 800 !important; text-transform: uppercase !important; letter-spacing: 0.1em !important; }
  `]
})
export class MercVisitasComponent implements OnInit {
  private api = inject(ApiService);
  private ui = inject(MercUiService);
  
  loading = signal(true);
  mode = signal<'visitas' | 'data'>('visitas');
  visitas = signal<any[]>([]);

  searchQuery = '';
  selectedChain = '';
  selectedClient = '';

  chains = computed(() => [...new Set(this.visitas().map(v => v.cadena))].filter(Boolean));
  clients = computed(() => [...new Set(this.visitas().map(v => v.cliente_nombre))].filter(Boolean));

  filteredVisitas = computed(() => {
    return this.visitas().filter(v => {
      const matchSearch = !this.searchQuery || 
        v.pdv_nombre.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
        v.cliente_nombre.toLowerCase().includes(this.searchQuery.toLowerCase());
      
      const matchChain = !this.selectedChain || v.cadena === this.selectedChain;
      const matchClient = !this.selectedClient || v.cliente_nombre === this.selectedClient;
      
      // If mode is 'data', maybe we only show visits with balances? 
      const matchMode = this.mode() === 'visitas' ? true : v.balances_count > 0;

      return matchSearch && matchChain && matchClient && matchMode;
    });
  });

  ngOnInit(): void {
    this.loadVisitas();
  }

  loadVisitas(): void {
    this.loading.set(true);
    // Fetch last 30 days for history
    const fi = new Date();
    fi.setDate(fi.getDate() - 30);
    
    this.api.getMercMisVisitas({ fecha_inicio: fi.toISOString().split('T')[0] }).subscribe({
      next: (res) => {
        this.visitas.set(res);
        this.loading.set(false);
      },
      error: () => this.loading.set(false)
    });
  }

  verDetalle(v: any): void {
    this.ui.openVisit({
      id_visita: v.id_visita,
      pdv_nombre: v.pdv_nombre,
      id_cliente: v.id_cliente,
      cliente: v.cliente_nombre
    });
  }
}
