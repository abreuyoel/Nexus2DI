import { Component, Input, OnInit, Output, EventEmitter, signal, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { ApiService } from '../../../../../../core/services/api.service';
import { OfflineQueueService } from '../../../../services/offline-queue.service';
import { MercUiService } from '../../../../services/merc-ui.service';

/**
 * Producto individual en el formulario de balance expandido.
 * Refleja el modelo del APK: estado (normal/quiebre/no_existe) + campos condicionales.
 */
interface ProductBalanceState {
  /** Campos del backend */
  id: number;
  sku: string;
  nombre: string;
  fabricante: string;
  categoria: string;
  id_categoria: number;
  /** Estado del producto (chips) */
  estado: 'normal' | 'quiebre' | 'no_existe';
  /** Campos de balance */
  inv_inicial: number;
  inv_deposito: number;
  inv_final: number;
  caras: number;
  precio_bs: number;
  precio_ds: number;
  fifo: Date | null;
  /** UI state */
  isExpanded: boolean;
  isSaved: boolean;
  saving: boolean;
}

@Component({
  selector: 'app-balance-form',
  standalone: true,
  imports: [
    CommonModule, FormsModule, MatIconModule, MatButtonModule,
    MatProgressSpinnerModule, MatSnackBarModule, MatDatepickerModule,
    MatNativeDateModule, MatFormFieldModule, MatInputModule
  ],
  template: `
    <!-- BOTÓN: Abrir Auditoría (APK: el botón que abre BalanceScreen) -->
    <div class="p-0">
      <button (click)="open()"
        class="w-full flex items-center justify-between px-5 py-4 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors rounded-b-3xl">
        <div class="flex items-center gap-3">
          <div class="shrink-0 w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center">
            <mat-icon class="!text-xl text-emerald-600">inventory_2</mat-icon>
          </div>
          <div class="text-left">
            <span class="text-xs font-black text-slate-600 dark:text-slate-300 uppercase tracking-widest">Realizar Auditoría</span>
            <p class="text-[10px] text-slate-400 dark:text-slate-500">
              @if (auditedCount() > 0) {
                {{ auditedCount() }} de {{ productCount() }} productos auditados ({{ progressPercent() }}%)
              } @else {
                {{ productCount() }} productos disponibles
              }
            </p>
          </div>
        </div>
        <mat-icon class="text-slate-400">chevron_right</mat-icon>
      </button>
    </div>

    <!-- OVERLAY: Pantalla completa de auditoría (APK: BalanceScreen) -->
    @if (isOpen()) {
      <div class="fixed inset-0 z-[200] bg-white dark:bg-slate-950 flex flex-col animate-in slide-in-from-right-full duration-300">

        <!-- Header -->
        <div class="bg-white dark:bg-slate-900 border-b border-slate-100 dark:border-white/5 px-6 py-4 flex items-center gap-3 shrink-0 shadow-sm">
          <button (click)="close()" class="w-10 h-10 rounded-xl bg-slate-50 dark:bg-white/5 flex items-center justify-center text-slate-500">
            <mat-icon>arrow_back</mat-icon>
          </button>
          <div class="flex-1 min-w-0">
            <h3 class="font-bold text-slate-800 dark:text-white tracking-tight text-sm">Inventario y Balance</h3>
            <p class="text-[10px] text-slate-400 dark:text-slate-500">Auditoría de productos del cliente</p>
          </div>
          <!-- Progress Mini -->
          <div class="text-right shrink-0">
            <span class="text-[10px] font-black text-emerald-500">
              {{ auditedCount() }}/{{ productCount() }}
            </span>
            <p class="text-[8px] text-slate-400">{{ progressPercent() }}% completado</p>
          </div>
        </div>

        <!-- Progress Bar (APK: LinearProgressIndicator) -->
        <div class="h-2 bg-slate-100 dark:bg-white/5 shrink-0">
          <div class="h-full bg-emerald-500 transition-all duration-500 rounded-r-full"
            [style.width]="progressPercent() + '%'"></div>
        </div>

        <!-- Search Bar & Toggles -->
        <div class="px-4 py-3 shrink-0 space-y-3">
          <div class="relative">
            <mat-icon class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">search</mat-icon>
            <input type="text" [ngModel]="searchQuery()" (ngModelChange)="onSearchChange($event)"
                   placeholder="Buscar producto, SKU o fabricante..."
                   class="w-full bg-slate-50 dark:bg-slate-900 border border-slate-100 dark:border-white/5 rounded-2xl pl-10 pr-10 py-3 text-sm font-bold outline-none focus:ring-2 focus:ring-emerald-500 transition-all">
            @if (searchQuery()) {
              <button (click)="onSearchChange('')" class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
                <mat-icon class="!text-sm">close</mat-icon>
              </button>
            }
          </div>
          
          <div class="flex items-center justify-between bg-slate-50 dark:bg-slate-900 p-1.5 rounded-2xl border border-slate-100 dark:border-white/5">
            <span class="text-xs font-black text-slate-500 dark:text-slate-400 uppercase tracking-widest pl-2">Agrupación</span>
            <button (click)="verSinCategorias.set(!verSinCategorias())"
              class="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-black transition-all"
              [ngClass]="verSinCategorias() ? 'bg-emerald-600 text-white shadow-sm' : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-100 dark:border-white/5'">
              <mat-icon class="!text-sm">{{ verSinCategorias() ? 'list' : 'grid_view' }}</mat-icon>
              {{ verSinCategorias() ? 'Ver sin categorías (Plano)' : 'Ver por categorías' }}
            </button>
          </div>
        </div>

        <!-- Product List (grouped by category) -->
        <div class="flex-grow overflow-y-auto custom-scrollbar">
          @if (loading()) {
            <div class="flex justify-center py-16"><mat-spinner diameter="36"></mat-spinner></div>
          } @else if (groupedProducts().length === 0) {
            <div class="flex flex-col items-center justify-center py-16 opacity-40 gap-3">
              <mat-icon class="!text-5xl">inventory_2</mat-icon>
              <p class="text-xs font-bold italic">No se encontraron productos</p>
            </div>
          } @else {
            <div class="px-3 pb-24 space-y-3">
              @for (group of groupedProducts(); track group.categoria) {
                <div class="space-y-2">
                  <!-- Category Header -->
                  <button (click)="toggleCategory(group.categoria)"
                    class="w-full flex items-center justify-between px-3 py-2 bg-slate-100 dark:bg-white/5 rounded-2xl select-none">
                    <div class="flex items-center gap-2">
                      <mat-icon class="!text-sm text-slate-400">category</mat-icon>
                      <span class="text-[11px] font-black uppercase tracking-widest text-slate-500 dark:text-slate-400">{{ group.categoria }}</span>
                      <span class="text-[10px] font-bold text-slate-400">({{ group.products.length }})</span>
                    </div>
                    <mat-icon class="!text-sm text-slate-400 transition-transform duration-200"
                      [class.rotate-180]="!isCategoryExpanded(group.categoria)">expand_more</mat-icon>
                  </button>

                  <!-- Products in Category -->
                  @if (isCategoryExpanded(group.categoria)) {
                    <div class="space-y-2 pl-1">
                      @for (p of group.products; track p.id) {
                        <div class="bg-white dark:bg-slate-900 border rounded-2xl overflow-hidden transition-all"
                          [ngClass]="{
                            'border-emerald-400': p.isSaved,
                            'border-emerald-200/50': p.isExpanded && !p.isSaved,
                            'border-slate-100 dark:border-white/5': !p.isExpanded && !p.isSaved
                          }">

                          <!-- Product Row -->
                          <div (click)="toggleProduct(p)" class="flex items-center gap-3 p-3 cursor-pointer">
                            <!-- Status Icon -->
                            <div class="shrink-0 w-9 h-9 rounded-full flex items-center justify-center"
                              [ngClass]="{
                                'bg-emerald-500/10': p.isSaved,
                                'bg-amber-500/10': !p.isSaved
                              }">
                              <mat-icon class="!text-lg"
                                [ngClass]="{
                                  'text-emerald-600': p.isSaved,
                                  'text-amber-500': !p.isSaved
                                }">
                                {{ p.isSaved ? 'check_circle' : 'inventory_2' }}
                              </mat-icon>
                            </div>

                            <!-- Product Info -->
                            <div class="flex-1 min-w-0">
                              <span class="text-[13px] font-semibold text-slate-800 dark:text-slate-100 truncate block"
                                [ngClass]="{'text-emerald-600': p.isSaved}">{{ p.nombre || p.sku }}</span>
                              <div class="flex items-center gap-2 mt-0.5">
                                <span class="text-[9px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-white/5 text-slate-400 font-medium">{{ p.categoria }}</span>
                                <span class="text-[10px] text-slate-400">{{ p.fabricante }}</span>
                              </div>
                            </div>

                            <!-- Expand Arrow -->
                            <mat-icon class="!text-sm text-slate-400 shrink-0">
                              {{ p.isExpanded ? 'keyboard_arrow_up' : 'keyboard_arrow_down' }}
                            </mat-icon>
                          </div>

                          <!-- Expanded Form -->
                          @if (p.isExpanded) {
                            <div class="px-4 pb-4 border-t border-slate-50 dark:border-white/5">
                              <div class="pt-4 space-y-4">

                                <!-- Estado Chips (APK: _buildEstadoChip) -->
                                <div class="flex justify-center gap-3">
                                  <button (click)="setEstado(p, 'normal')"
                                    class="px-6 py-2 rounded-xl text-[11px] font-black uppercase tracking-widest border-2 transition-all"
                                    [ngClass]="{
                                      'bg-emerald-500/10': p.estado === 'normal',
                                      'border-emerald-500': p.estado === 'normal',
                                      'text-emerald-600': p.estado === 'normal',
                                      'border-slate-200 dark:border-white/10': p.estado !== 'normal',
                                      'text-slate-400': p.estado !== 'normal'
                                    }">
                                    Normal
                                  </button>
                                  <button (click)="setEstado(p, 'quiebre')"
                                    class="px-6 py-2 rounded-xl text-[11px] font-black uppercase tracking-widest border-2 transition-all"
                                    [ngClass]="{
                                      'bg-orange-500/10': p.estado === 'quiebre',
                                      'border-orange-500': p.estado === 'quiebre',
                                      'text-orange-600': p.estado === 'quiebre',
                                      'border-slate-200 dark:border-white/10': p.estado !== 'quiebre',
                                      'text-slate-400': p.estado !== 'quiebre'
                                    }">
                                    Quiebre
                                  </button>
                                  <button (click)="setEstado(p, 'no_existe')"
                                    class="px-6 py-2 rounded-xl text-[11px] font-black uppercase tracking-widest border-2 transition-all"
                                    [ngClass]="{
                                      'bg-slate-500/10': p.estado === 'no_existe',
                                      'border-slate-500': p.estado === 'no_existe',
                                      'text-slate-600': p.estado === 'no_existe',
                                      'border-slate-200 dark:border-white/10': p.estado !== 'no_existe',
                                      'text-slate-400': p.estado !== 'no_existe'
                                    }">
                                    No existe
                                  </button>
                                </div>

                                <!-- Fields for "normal" estado -->
                                @if (p.estado === 'normal') {
                                  <div class="grid grid-cols-3 gap-3">
                                    <div class="space-y-1">
                                      <label class="text-[9px] font-black text-slate-400 uppercase tracking-widest px-1">Inv. Inicial</label>
                                      <input type="number" [(ngModel)]="p.inv_inicial"
                                        class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-white/5 rounded-xl px-3 py-2 text-sm font-black outline-none focus:ring-2 focus:ring-emerald-500">
                                    </div>
                                    <div class="space-y-1">
                                      <label class="text-[9px] font-black text-slate-400 uppercase tracking-widest px-1">Inv. Depósito</label>
                                      <input type="number" [(ngModel)]="p.inv_deposito"
                                        class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-white/5 rounded-xl px-3 py-2 text-sm font-black outline-none focus:ring-2 focus:ring-emerald-500">
                                    </div>
                                    <div class="space-y-1">
                                      <label class="text-[9px] font-black text-slate-400 uppercase tracking-widest px-1">Inv. Final</label>
                                      <input type="number" [(ngModel)]="p.inv_final"
                                        class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-white/5 rounded-xl px-3 py-2 text-sm font-black outline-none focus:ring-2 focus:ring-emerald-500">
                                    </div>
                                  </div>

                                  <div class="grid grid-cols-2 gap-3">
                                    <div class="space-y-1">
                                      <label class="text-[9px] font-black text-slate-400 uppercase tracking-widest px-1">Caras (Frentes)</label>
                                      <input type="number" [(ngModel)]="p.caras"
                                        class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-white/5 rounded-xl px-3 py-2 text-sm font-black outline-none focus:ring-2 focus:ring-emerald-500">
                                    </div>
                                    <div class="space-y-1">
                                      <label class="text-[9px] font-black text-slate-400 uppercase tracking-widest px-1">FEFO (Vence)</label>
                                      <div class="relative merc-datepicker-container">
                                        <input matInput [matDatepicker]="dp"
                                               [(ngModel)]="p.fifo"
                                               placeholder="Seleccionar fecha"
                                               class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-white/5 rounded-xl px-3 py-2 text-sm font-bold outline-none cursor-pointer"
                                               (click)="dp.open()">
                                        <mat-datepicker-toggle matSuffix [for]="dp" class="absolute right-1 top-1/2 -translate-y-1/2 scale-75"></mat-datepicker-toggle>
                                        <mat-datepicker #dp></mat-datepicker>
                                      </div>
                                    </div>
                                  </div>

                                  <!-- Precios (always visible for 'normal' and 'quiebre') -->
                                  <div class="grid grid-cols-2 gap-3">
                                    <div class="space-y-1">
                                      <label class="text-[9px] font-black text-slate-400 uppercase tracking-widest px-1">Precio Bs</label>
                                      <div class="relative">
                                        <span class="absolute left-3 top-1/2 -translate-y-1/2 text-[10px] font-black text-slate-400">Bs</span>
                                        <input type="number" [(ngModel)]="p.precio_bs"
                                          class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-white/5 rounded-xl pl-8 pr-3 py-2 text-sm font-black outline-none focus:ring-2 focus:ring-emerald-500">
                                      </div>
                                    </div>
                                    <div class="space-y-1">
                                      <label class="text-[9px] font-black text-slate-400 uppercase tracking-widest px-1">Precio USD</label>
                                      <div class="relative">
                                        <span class="absolute left-3 top-1/2 -translate-y-1/2 text-[10px] font-black text-slate-400">$</span>
                                        <input type="number" [(ngModel)]="p.precio_ds"
                                          class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-white/5 rounded-xl pl-8 pr-3 py-2 text-sm font-black outline-none focus:ring-2 focus:ring-emerald-500">
                                      </div>
                                    </div>
                                  </div>
                                }

                                <!-- Fields for "quiebre" estado: solo precios -->
                                @if (p.estado === 'quiebre') {
                                  <div class="grid grid-cols-2 gap-3">
                                    <div class="space-y-1">
                                      <label class="text-[9px] font-black text-slate-400 uppercase tracking-widest px-1">Precio Bs</label>
                                      <div class="relative">
                                        <span class="absolute left-3 top-1/2 -translate-y-1/2 text-[10px] font-black text-slate-400">Bs</span>
                                        <input type="number" [(ngModel)]="p.precio_bs"
                                          class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-white/5 rounded-xl pl-8 pr-3 py-2 text-sm font-black outline-none focus:ring-2 focus:ring-emerald-500">
                                      </div>
                                    </div>
                                    <div class="space-y-1">
                                      <label class="text-[9px] font-black text-slate-400 uppercase tracking-widest px-1">Precio USD</label>
                                      <div class="relative">
                                        <span class="absolute left-3 top-1/2 -translate-y-1/2 text-[10px] font-black text-slate-400">$</span>
                                        <input type="number" [(ngModel)]="p.precio_ds"
                                          class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-white/5 rounded-xl pl-8 pr-3 py-2 text-sm font-black outline-none focus:ring-2 focus:ring-emerald-500">
                                      </div>
                                    </div>
                                  </div>
                                }

                                <!-- "No existe": no fields needed, just message -->
                                @if (p.estado === 'no_existe') {
                                  <p class="text-[11px] text-slate-400 dark:text-slate-500 text-center italic py-2">
                                    Producto marcado como "No existe" — sin datos de inventario.
                                  </p>
                                }

                                <!-- Guardar Auditoría Button (per product) -->
                                <button (click)="saveProductBalance(p)" [disabled]="p.saving"
                                  class="w-full py-3 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-2xl font-black uppercase tracking-widest text-xs flex items-center justify-center gap-2 active:scale-95 transition-all">
                                  @if (p.saving) {
                                    <mat-spinner diameter="18" color="accent"></mat-spinner>
                                  } @else {
                                    <mat-icon class="!text-base">save</mat-icon>
                                  }
                                  Guardar Auditoría
                                </button>

                              </div>
                            </div>
                          }
                        </div>
                      }
                    </div>
                  }
                </div>
              }
            </div>
          }
        </div>

      </div>
    }
  `,
  styles: [`
    :host { display: block; }
    .merc-datepicker-container ::ng-deep {
      .mat-mdc-form-field-subscript-wrapper { display: none; }
      .mat-mdc-text-field-wrapper { padding: 0; background: transparent !important; }
      .mat-mdc-form-field-flex { padding: 0 !important; }
      .mdc-line-ripple { display: none; }
    }
  `]
})
export class BalanceFormComponent implements OnInit {
  @Input() visitaId!: number | string;
  @Input() idCliente!: number;
  @Input() chainId: string | null = null;
  @Output() balanceGuardado = new EventEmitter<void>();

  private api = inject(ApiService);
  private offline = inject(OfflineQueueService);
  private snack = inject(MatSnackBar);
  private ui = inject(MercUiService);

  // ─── Modal state ───
  isOpen = signal(false);
  loading = signal(false);

  // ─── Products and balances ───
  allProducts = signal<ProductBalanceState[]>([]);
  searchQuery = signal<string>('');
  verSinCategorias = signal(false);

  // ─── Category expansion ───
  expandedCategories = signal<Record<string, boolean>>({});

  // Datepicker tracking: one per product row
  private datepickers: { [id: number]: any } = {};

  // ─── Computed ───
  productCount = computed(() => this.allProducts().length);
  auditedCount = computed(() => this.allProducts().filter(p => p.isSaved).length);
  progressPercent = computed(() => {
    const total = this.productCount();
    const audited = this.auditedCount();
    return total > 0 ? Math.round((audited / total) * 100) : 0;
  });

  filteredProducts = computed(() => {
    const q = this.searchQuery().trim().toLowerCase();
    if (!q) {
      return this.allProducts();
    }
    return this.allProducts().filter(p =>
      (p.nombre || '').toLowerCase().includes(q) ||
      (p.sku || '').toLowerCase().includes(q) ||
      (p.fabricante || '').toLowerCase().includes(q) ||
      (p.categoria || '').toLowerCase().includes(q)
    );
  });

  groupedProducts = computed(() => {
    const prods = this.filteredProducts();
    if (this.verSinCategorias()) {
      return [{ categoria: 'Todos los Productos', products: prods }];
    }
    const groups: Record<string, ProductBalanceState[]> = {};
    prods.forEach(p => {
      const cat = p.categoria || 'Sin Categoría';
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push(p);
    });
    return Object.entries(groups)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([categoria, products]) => ({ categoria, products }));
  });

  // ─── Category toggle ───
  toggleCategory(cat: string) {
    this.expandedCategories.update(state => ({ ...state, [cat]: !state[cat] }));
  }

  isCategoryExpanded(cat: string): boolean {
    // Si hay una búsqueda activa o la vista plana, auto-expandir todas las categorías
    if (this.searchQuery().trim() !== '' || this.verSinCategorias()) {
      return true;
    }
    return this.expandedCategories()[cat] !== false;
  }

  // ─── Product toggle ───
  toggleProduct(p: ProductBalanceState) {
    p.isExpanded = !p.isExpanded;
  }

  // ─── Estado chip ───
  setEstado(p: ProductBalanceState, estado: 'normal' | 'quiebre' | 'no_existe') {
    p.estado = estado;
    // ⚠️ NO limpiar campos al cambiar estado — los valores se conservan en memoria.
    // Si el usuario vuelve a "Normal" después de pasar por "Quiebre", recupera lo que ya había escrito.
    // Al guardar, el backend solo persiste los campos que corresponden según estado_producto.
  }

  // ─── Search ───
  onSearchChange(val: string) {
    this.searchQuery.set(val || '');
  }

  // ─── Datepicker ───
  pickerFor(p: ProductBalanceState): any {
    if (!this.datepickers[p.id]) {
      this.datepickers[p.id] = {};
    }
    return this.datepickers[p.id];
  }

  openDatepicker(p: ProductBalanceState) {
    // Angular Material datepicker opens via click on the input with [matDatepicker]
    // The template uses mat-datepicker-toggle which handles opening
  }

  // ─── Open / Close Modal ───
  open() {
    this.isOpen.set(true);
    if (this.allProducts().length === 0) {
      this.loadProducts();
    }
  }

  close() {
    this.isOpen.set(false);
  }

  private _processProductsResponse(res: { categorias: any[]; total_productos: number }) {
    const allItems: any[] = [];
    for (const cat of res.categorias || []) {
      if (cat.productos) allItems.push(...cat.productos);
    }
    const products: ProductBalanceState[] = allItems.map((p: any) => ({
      id: p.id_producto || p.id,
      sku: p.sku || '',
      nombre: p.nombre || p.sku || '',
      fabricante: p.fabricante || '',
      categoria: p.categoria || 'Sin Categoría',
      id_categoria: p.id_categoria || 0,
      estado: 'normal' as const,
      inv_inicial: 0,
      inv_deposito: 0,
      inv_final: 0,
      caras: 0,
      precio_bs: 0,
      precio_ds: 0,
      fifo: null,
      isExpanded: false,
      isSaved: false,
      saving: false,
    }));
    this.allProducts.set(products);

    // Expand first category by default
    const nonEmpty = products.filter(p => p.categoria);
    const firstCat = nonEmpty[0]?.categoria;
    if (firstCat) {
      this.expandedCategories.set({ [firstCat]: true });
    }

    this.loading.set(false);
    this.loadExistingBalances();
  }

  // ─── Load Products ───
  private loadProducts() {
    // ⚡ 0ms INSTANT LOAD: si tenemos catalogo en cache, cargarlo de inmediato
    const cached = this.ui.getCachedProductos(this.idCliente);
    if (cached) {
      this._processProductsResponse(cached);
    } else {
      this.loading.set(true);
    }

    this.api.getMercProductosCliente(this.idCliente).subscribe({
      next: (res: { categorias: any[]; total_productos: number }) => {
        this.ui.setCachedProductos(this.idCliente, res);
        this._processProductsResponse(res);
      },
      error: () => {
        this.loading.set(false);
        if (!this.ui.getCachedProductos(this.idCliente)) {
          this.snack.open('Error al cargar productos del cliente', 'OK', { duration: 3000 });
        }
      }
    });
  }

  private loadExistingBalances() {
    if (!this.visitaId) return;

    if (this.chainId) {
      this.offline.getChain(this.chainId).then(chain => {
        if (!chain) return;
        const balancesStep = chain.steps.find(s => s.kind === 'balances' && s.jsonBody?.productos);
        if (balancesStep && balancesStep.jsonBody?.productos) {
          this.applySavedBalances(balancesStep.jsonBody.productos);
        }
      });
      return;
    }

    this.api.get<any>(`/api/merc/visitas/${this.visitaId}/detalle`).subscribe({
      next: (res) => {
        if (res.balances) {
          this.applySavedBalances(res.balances);
        }
      },
    });
  }

  private applySavedBalances(balances: any[]) {
    const savedMap = new Map<number, any>();
    for (const b of balances) {
      // Try to match by id_producto, id_balance, or id
      const key = b.id_producto || b.id_balance || b.id;
      if (key) savedMap.set(key, b);
    }

    this.allProducts.update(prods => prods.map(p => {
      const saved = savedMap.get(p.id);
      if (saved) {
        return {
          ...p,
          estado: (saved.estado || saved.estado_producto || 'normal') as 'normal' | 'quiebre' | 'no_existe',
          inv_inicial: saved.inv_inicial || 0,
          inv_deposito: saved.inv_deposito || 0,
          inv_final: saved.inv_final || 0,
          caras: saved.caras || 0,
          precio_bs: saved.precio_bs || 0,
          precio_ds: saved.precio_ds || 0,
          fifo: saved.fifo || saved.fefo ? new Date(saved.fifo || saved.fefo) : null,
          isSaved: true,
        };
      }
      return p;
    }));
  }

  // ─── Save Single Product Balance (APK: _saveProductBalance) ───
  saveProductBalance(p: ProductBalanceState) {
    p.saving = true;

    const balanceData = {
      id_producto: p.id,
      sku: p.sku,
      nombre: p.nombre,
      fabricante: p.fabricante,
      categoria: p.categoria,
      id_categoria: p.id_categoria,
      estado_producto: p.estado,
      inv_inicial: p.inv_inicial,
      inv_deposito: p.inv_deposito,
      inv_final: p.inv_final,
      caras: p.caras,
      precio_bs: p.precio_bs,
      precio_ds: p.precio_ds,
      fifo: p.fifo ? p.fifo.toISOString().split('T')[0] : null,
    };

    // Build payload: list with just this one product
    const payload = {
      visita_id: this.visitaId,
      id_cliente: this.idCliente,
      productos: [balanceData]
    };

    if (this.chainId) {
      // Offline: merge with existing balances in chain
      this.offline.getChain(this.chainId).then(async chain => {
        if (chain) {
          const existingStep = chain.steps.find(s => s.kind === 'balances');
          let allProductos = [balanceData];
          if (existingStep && existingStep.jsonBody?.productos) {
            // Merge: replace if same ID, otherwise add
            const existing = existingStep.jsonBody.productos.filter((x: any) => x.id_producto !== p.id);
            allProductos = [...existing, balanceData];
          }
          // Remove old step if exists
          const oldIdx = chain.steps.indexOf(existingStep!);
          if (oldIdx >= 0) {
            await this.offline.deleteChainStep(this.chainId!, oldIdx);
          }
          await this.offline.addChainStep(this.chainId!, {
            kind: 'balances',
            url: `/api/merc/visitas/${this.visitaId}/balances`,
            isMultipart: false,
            jsonBody: { visita_id: Number(this.visitaId), id_cliente: this.idCliente, productos: allProductos }
          });
          p.isSaved = true;
          p.saving = false;
          this.balanceGuardado.emit();
          this.snack.open(`${p.nombre} guardado — se sincronizará al reconectar`, 'OK', { duration: 2500 });
        }
      });
    } else {
      this.api.guardarMercBalances({
        visita_id: Number(this.visitaId),
        id_cliente: this.idCliente,
        productos: [balanceData]
      }).subscribe({
        next: () => {
          p.isSaved = true;
          p.saving = false;
          this.balanceGuardado.emit();
          this.snack.open(`${p.nombre} guardado exitosamente`, 'OK', { duration: 2000 });
        },
        error: () => {
          p.saving = false;
          this.snack.open('Error al guardar auditoría', 'OK', { duration: 3000 });
        }
      });
    }
  }

  ngOnInit() {
    // Pre-load in background if visita is active
    if (this.visitaId) {
      this.loadProducts();
    }
  }
}
