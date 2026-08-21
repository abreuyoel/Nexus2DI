import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { ApiService } from '../../../core/services/api.service';
import { SearchableSelectComponent, SelectOption } from '../../client-visits/searchable-select.component';
import { ConfirmService } from '../../../shared/components/confirm-dialog/confirm.service';

type CatalogKey = 'tipo-negocio' | 'subtipo-negocio' | 'alcance' | 'canal-venta' | 'departamentos' | 'ciudades';

interface CatalogItem {
  id: number;
  nombre: string;
  activo: boolean;
}

interface CiudadItem extends CatalogItem {
  departamento_id: number;
  departamento_nombre: string | null;
}

interface TabDef {
  key: CatalogKey;
  label: string;
  icon: string;
  hint: string;
}

@Component({
  selector: 'app-catalogos',
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule, MatSnackBarModule, MatProgressSpinnerModule, MatTooltipModule, SearchableSelectComponent],
  template: `
<div class="space-y-5">

  <!-- Sub-tabs -->
  <div class="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-white/5 shadow-sm p-2 overflow-x-auto">
    <div class="flex gap-1 min-w-max">
      @for (t of tabs; track t.key) {
        <button (click)="switchTab(t.key)"
          [ngClass]="activeTab() === t.key
            ? 'bg-primary-600 text-white shadow-md'
            : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-white/5'"
          class="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold whitespace-nowrap transition-all">
          <mat-icon class="!text-base">{{ t.icon }}</mat-icon>
          {{ t.label }}
        </button>
      }
    </div>
  </div>

  <!-- Header / Add -->
  <div class="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-white/5 shadow-sm p-5">
    <div class="flex flex-col md:flex-row md:items-end gap-4 md:gap-6">
      <div class="flex-1">
        <h2 class="text-xl font-black text-slate-900 dark:text-white">{{ currentTab().label }}</h2>
        <p class="text-xs text-slate-500 mt-1">{{ currentTab().hint }}</p>
      </div>

      <div class="flex flex-col md:flex-row gap-3 items-stretch md:items-end">
        @if (activeTab() === 'ciudades') {
          <div class="space-y-1 w-full md:w-64">
            <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Departamento</label>
            <app-searchable-select [options]="departamentoOpts()" [value]="newCiudadDepStr()" (valueChange)="newCiudadDepStr.set($event || '')"
              placeholder="— Selecciona —" searchPlaceholder="Buscar departamento..." allLabel="Sin asignar" icon="map"></app-searchable-select>
          </div>
        }
        <div class="space-y-1 flex-1">
          <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Nuevo</label>
          <input [ngModel]="newName()" (ngModelChange)="newName.set($event)" (keyup.enter)="add()" [placeholder]="'Nombre de ' + currentTab().label.toLowerCase()"
            class="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-primary-500 rounded-xl px-3 py-2 text-sm font-semibold text-slate-900 dark:text-white placeholder-slate-400 outline-none w-full">
        </div>
        <button (click)="add()" [disabled]="!canAdd() || saving()"
          class="flex items-center gap-2 px-5 py-2 bg-primary-600 hover:bg-primary-500 disabled:opacity-40 text-white font-black rounded-xl text-sm shadow-lg transition-all active:scale-95">
          @if (saving()) { <mat-spinner diameter="14"></mat-spinner> } @else { <mat-icon class="!text-base">add</mat-icon> }
          Agregar
        </button>
      </div>
    </div>
  </div>

  <!-- Búsqueda + filtros + paginación -->
  <div class="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-white/5 shadow-sm p-4 flex flex-col md:flex-row items-stretch md:items-center gap-3">
    <div class="relative flex-1 min-w-52">
      <mat-icon class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 !text-base">search</mat-icon>
      <input [ngModel]="searchText()" (ngModelChange)="onSearchChange($event)" placeholder="Buscar por nombre..."
        class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-primary-500 rounded-xl pl-9 pr-3 py-2 text-sm font-semibold text-slate-900 dark:text-white placeholder-slate-400 outline-none">
    </div>
    @if (activeTab() === 'ciudades') {
      <div class="w-full md:w-64">
        <app-searchable-select [options]="departamentoOpts()" [value]="filterDepStr()" (valueChange)="onFilterDepChange($event)"
          placeholder="Todos los departamentos" searchPlaceholder="Buscar departamento..." allLabel="Todos" icon="filter_list"></app-searchable-select>
      </div>
    }
    <div class="flex items-center gap-2 shrink-0">
      <span class="text-xs font-black text-slate-500 uppercase tracking-widest">Pág.</span>
      <select [ngModel]="pageSize()" (ngModelChange)="onPageSizeChange($event)"
        class="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-primary-500 rounded-xl px-2 py-2 text-sm font-semibold text-slate-900 dark:text-white outline-none">
        <option [ngValue]="20">20</option>
        <option [ngValue]="50">50</option>
        <option [ngValue]="100">100</option>
      </select>
    </div>
  </div>

  <!-- Lista -->
  @if (loading()) {
    <div class="flex flex-col items-center py-20 gap-3">
      <mat-spinner diameter="40"></mat-spinner>
      <p class="text-slate-400 font-medium text-sm">Cargando…</p>
    </div>
  } @else {
    <div class="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-white/5 shadow-sm overflow-hidden">
      <table class="w-full text-left">
        <thead class="bg-slate-50 dark:bg-slate-950/50 border-b border-slate-100 dark:border-white/5">
          <tr>
            <th class="px-4 py-3 text-[10px] font-black text-slate-400 uppercase tracking-widest">Nombre</th>
            @if (activeTab() === 'ciudades') {
              <th class="px-4 py-3 text-[10px] font-black text-slate-400 uppercase tracking-widest">Departamento</th>
            }
            <th class="px-4 py-3 text-[10px] font-black text-slate-400 uppercase tracking-widest">Estado</th>
            <th class="px-4 py-3 text-[10px] font-black text-slate-400 uppercase tracking-widest text-right">Acciones</th>
          </tr>
        </thead>
        <tbody>
          @for (item of paginatedItems(); track item.id) {
            <tr class="border-b border-slate-100 dark:border-white/5 hover:bg-slate-50 dark:hover:bg-white/5">
              <td class="px-4 py-3">
                @if (editingId() === item.id) {
                  <input [(ngModel)]="editName"
                    class="bg-slate-50 dark:bg-slate-800 border border-primary-500 rounded-lg px-2 py-1 text-sm font-semibold text-slate-900 dark:text-white outline-none w-full">
                } @else {
                  <span class="font-semibold text-slate-800 dark:text-white text-sm">{{ item.nombre }}</span>
                }
              </td>
              @if (activeTab() === 'ciudades') {
                <td class="px-4 py-3">
                  @if (editingId() === item.id) {
                    <app-searchable-select [options]="departamentoOpts()" [(value)]="editDepStr"
                      placeholder="Departamento" searchPlaceholder="Buscar departamento..." allLabel="Sin asignar" icon="map"></app-searchable-select>
                  } @else {
                    <span class="text-xs text-slate-500">{{ asCiudad(item).departamento_nombre || '—' }}</span>
                  }
                </td>
              }
              <td class="px-4 py-3">
                <button (click)="toggleActive(item)"
                  [class.bg-emerald-100]="item.activo" [class.text-emerald-700]="item.activo"
                  [class.bg-slate-100]="!item.activo" [class.text-slate-500]="!item.activo"
                  class="text-[10px] font-black px-2 py-1 rounded-full uppercase tracking-wider">
                  {{ item.activo ? 'Activo' : 'Inactivo' }}
                </button>
              </td>
              <td class="px-4 py-3 text-right">
                <div class="inline-flex items-center gap-1">
                  @if (editingId() === item.id) {
                    <button (click)="saveEdit(item)" matTooltip="Guardar"
                      class="w-8 h-8 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white inline-flex items-center justify-center">
                      <mat-icon class="!text-sm">check</mat-icon>
                    </button>
                    <button (click)="cancelEdit()" matTooltip="Cancelar"
                      class="w-8 h-8 rounded-lg bg-slate-200 dark:bg-white/5 hover:bg-slate-300 text-slate-600 inline-flex items-center justify-center">
                      <mat-icon class="!text-sm">close</mat-icon>
                    </button>
                  } @else {
                    <button (click)="startEdit(item)" matTooltip="Editar"
                      class="w-8 h-8 rounded-lg bg-slate-100 dark:bg-white/5 hover:bg-primary-500 text-slate-500 hover:text-white inline-flex items-center justify-center">
                      <mat-icon class="!text-sm">edit</mat-icon>
                    </button>
                    <button (click)="remove(item)" matTooltip="Eliminar"
                      class="w-8 h-8 rounded-lg bg-slate-100 dark:bg-white/5 hover:bg-rose-500 text-slate-500 hover:text-white inline-flex items-center justify-center">
                      <mat-icon class="!text-sm">delete</mat-icon>
                    </button>
                  }
                </div>
              </td>
            </tr>
          }
          @if (paginatedItems().length === 0) {
            <tr>
              <td [attr.colspan]="activeTab() === 'ciudades' ? 4 : 3" class="py-16 text-center">
                <div class="flex flex-col items-center gap-2 opacity-40">
                  <mat-icon class="!text-4xl">inbox</mat-icon>
                  <p class="font-bold text-sm">Sin elementos</p>
                  <p class="text-xs">Agrega el primero arriba</p>
                </div>
              </td>
            </tr>
          }
        </tbody>
      </table>
      @if (totalPages() > 1) {
        <div class="flex items-center justify-between gap-3 px-4 py-3 border-t border-slate-100 dark:border-white/5 bg-slate-50/50 dark:bg-slate-950/30">
          <span class="text-xs font-semibold text-slate-500">
            {{ filteredItems().length }} registros · pág. {{ page() + 1 }} de {{ totalPages() }}
          </span>
          <div class="flex items-center gap-2">
            <button (click)="goPage(page() - 1)" [disabled]="page() <= 0"
              class="w-8 h-8 inline-flex items-center justify-center rounded-lg border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 disabled:opacity-40 hover:bg-slate-100 dark:hover:bg-white/5">
              <mat-icon class="!text-sm">chevron_left</mat-icon>
            </button>
            <span class="text-sm font-black text-slate-700 dark:text-white">{{ page() + 1 }} / {{ totalPages() }}</span>
            <button (click)="goPage(page() + 1)" [disabled]="page() >= totalPages() - 1"
              class="w-8 h-8 inline-flex items-center justify-center rounded-lg border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 disabled:opacity-40 hover:bg-slate-100 dark:hover:bg-white/5">
              <mat-icon class="!text-sm">chevron_right</mat-icon>
            </button>
          </div>
        </div>
      }
    </div>
  }
</div>
  `
})
export class CatalogosComponent implements OnInit {
  private api = inject(ApiService);
  private snack = inject(MatSnackBar);
  private confirmSvc = inject(ConfirmService);

  tabs: TabDef[] = [
    { key: 'tipo-negocio', label: 'Tipo de Negocio', icon: 'category', hint: 'Categorización principal del establecimiento (antes Jerarquía Nivel 2)' },
    { key: 'subtipo-negocio', label: 'Subtipo de Negocio', icon: 'sell', hint: 'Subcategoría del tipo de negocio (antes Jerarquía Nivel 2_2)' },
    { key: 'alcance', label: 'Alcance', icon: 'public', hint: 'Alcance geográfico/comercial del PDV' },
    { key: 'canal-venta', label: 'Canal de Venta', icon: 'storefront', hint: 'Clasificación del canal comercial' },
    { key: 'departamentos', label: 'Departamentos', icon: 'map', hint: 'Departamentos / regiones donde operan los PDV' },
    { key: 'ciudades', label: 'Ciudades', icon: 'location_city', hint: 'Ciudades asociadas a cada departamento' },
  ];

  activeTab = signal<CatalogKey>('tipo-negocio');
  loading = signal(false);
  saving = signal(false);

  items = signal<(CatalogItem | CiudadItem)[]>([]);
  departamentos = signal<CatalogItem[]>([]);

  editingId = signal<number | null>(null);
  editName = '';
  editDepStr = '';

  newName = signal('');
  newCiudadDepStr = signal('');
  filterDepStr = signal('');
  searchText = signal('');
  pageSize = signal(20);
  page = signal(0);

  departamentoOpts = computed<SelectOption[]>(() =>
    this.departamentos().map(d => ({ value: String(d.id), label: d.nombre }))
  );

  currentTab = computed(() => this.tabs.find(t => t.key === this.activeTab())!);
  canAdd = computed(() => {
    if (!this.newName().trim()) return false;
    if (this.activeTab() === 'ciudades' && !this.newCiudadDepStr()) return false;
    return true;
  });

  filteredItems = computed(() => {
    const q = this.searchText().trim().toLowerCase();
    let list = this.items();
    const depStr = this.filterDepStr();
    if (this.activeTab() === 'ciudades' && depStr) {
      const depId = +depStr;
      list = list.filter(it => this.asCiudad(it).departamento_id === depId);
    }
    if (q) {
      list = list.filter(it => (it.nombre || '').toLowerCase().includes(q));
    }
    return list;
  });

  paginatedItems = computed(() => {
    const start = this.page() * this.pageSize();
    return this.filteredItems().slice(start, start + this.pageSize());
  });

  totalPages = computed(() => Math.max(1, Math.ceil(this.filteredItems().length / this.pageSize())));

  onSearchChange(val: string): void {
    this.searchText.set(val || '');
    this.page.set(0);
  }

  onFilterDepChange(val?: string): void {
    if (val !== undefined) this.filterDepStr.set(val);
    this.page.set(0);
    this.loadList();
  }

  onPageSizeChange(val: number): void {
    this.pageSize.set(+val);
    this.page.set(0);
  }

  goPage(p: number): void {
    if (p < 0 || p >= this.totalPages()) return;
    this.page.set(p);
  }

  ngOnInit(): void {
    this.loadDepartamentos();
    this.loadList();
  }

  asCiudad(it: CatalogItem | CiudadItem): CiudadItem {
    return it as CiudadItem;
  }

  switchTab(key: CatalogKey): void {
    this.activeTab.set(key);
    this.editingId.set(null);
    this.newName.set('');
    this.newCiudadDepStr.set('');
    this.filterDepStr.set('');
    this.searchText.set('');
    this.page.set(0);
    this.loadList();
  }

  loadDepartamentos(): void {
    this.api.listCatalog('departamentos').subscribe({
      next: d => this.departamentos.set(d),
      error: () => { }
    });
  }

  loadList(): void {
    this.loading.set(true);
    if (this.activeTab() === 'ciudades') {
      const depId = this.filterDepStr() ? +this.filterDepStr() : null;
      const opts: any = { activo: true };
      if (depId) opts.departamento_id = depId;
      this.api.listCiudades(opts).subscribe({
        next: d => { this.items.set(d); this.loading.set(false); },
        error: () => this.loading.set(false)
      });
    } else {
      this.api.listCatalog(this.activeTab(), true).subscribe({
        next: d => { this.items.set(d); this.loading.set(false); },
        error: () => this.loading.set(false)
      });
    }
  }

  add(): void {
    if (!this.canAdd()) return;
    this.saving.set(true);
    const nombre = this.newName().trim();
    const depStr = this.newCiudadDepStr();
    const op = this.activeTab() === 'ciudades'
      ? this.api.createCiudad({ nombre, departamento_id: +depStr })
      : this.api.createCatalogItem(this.activeTab(), { nombre });
    op.subscribe({
      next: () => {
        this.saving.set(false);
        this.newName.set('');
        this.newCiudadDepStr.set('');
        if (this.activeTab() === 'departamentos') this.loadDepartamentos();
        this.loadList();
        this.snack.open('Agregado exitosamente', 'OK', { duration: 2500 });
      },
      error: (err) => {
        this.saving.set(false);
        this.snack.open(err?.error?.detail ?? 'Error al agregar', 'OK', { duration: 4000 });
      }
    });
  }

  startEdit(item: CatalogItem | CiudadItem): void {
    this.editingId.set(item.id);
    this.editName = item.nombre;
    if (this.activeTab() === 'ciudades') this.editDepStr = String((item as CiudadItem).departamento_id ?? '');
  }

  cancelEdit(): void {
    this.editingId.set(null);
    this.editName = '';
    this.editDepStr = '';
  }

  saveEdit(item: CatalogItem | CiudadItem): void {
    const nombre = this.editName.trim();
    if (!nombre) return;
    const op = this.activeTab() === 'ciudades'
      ? this.api.updateCiudad(item.id, { nombre, departamento_id: this.editDepStr ? +this.editDepStr : undefined })
      : this.api.updateCatalogItem(this.activeTab(), item.id, { nombre });
    op.subscribe({
      next: () => {
        this.cancelEdit();
        if (this.activeTab() === 'departamentos') this.loadDepartamentos();
        this.loadList();
        this.snack.open('Guardado', 'OK', { duration: 2000 });
      },
      error: (err) => this.snack.open(err?.error?.detail ?? 'Error al guardar', 'OK', { duration: 4000 })
    });
  }

  toggleActive(item: CatalogItem | CiudadItem): void {
    const nuevoEstado = !item.activo;
    const op = this.activeTab() === 'ciudades'
      ? this.api.updateCiudad(item.id, { activo: nuevoEstado })
      : this.api.updateCatalogItem(this.activeTab(), item.id, { activo: nuevoEstado });
    op.subscribe({
      next: () => this.loadList(),
      error: (err) => this.snack.open(err?.error?.detail ?? 'Error al cambiar estado', 'OK', { duration: 4000 })
    });
  }

  async remove(item: CatalogItem | CiudadItem): Promise<void> {
    const ok = await this.confirmSvc.confirm(`¿Estás seguro de eliminar el ítem "${item.nombre}" del catálogo?`, {
      title: 'Eliminar ítem del catálogo',
      confirmText: 'Sí, eliminar',
      cancelText: 'Cancelar',
      danger: true,
    });
    if (!ok) return;

    const op = this.activeTab() === 'ciudades'
      ? this.api.deleteCiudad(item.id)
      : this.api.deleteCatalogItem(this.activeTab(), item.id);
    op.subscribe({
      next: () => {
        if (this.activeTab() === 'departamentos') this.loadDepartamentos();
        this.loadList();
        this.snack.open('Ítem eliminado exitosamente', 'OK', { duration: 2500 });
      },
      error: async (err) => {
        const detail = err?.error?.detail;
        if (typeof detail === 'object' && detail?.usage_count) {
          const count = detail.usage_count;
          const unidad = count === 1 ? 'punto de venta' : 'puntos de venta';
          const sampleList = (detail.sample_pdv_ids || []).slice(0, 5).join('\n• ');
          const sampleMsg = sampleList ? `\n\nPuntos de venta afectados:\n• ${sampleList}` : '';

          const userFriendlyMsg = `El ítem "${item.nombre}" está actualmente asignado a ${count} ${unidad}.${sampleMsg}\n\nSi eliminas este valor, los puntos de venta vinculados quedarán sin esta categoría.\n\nNota: Esta acción quedará registrada en el módulo de Auditoría. Si borras este valor por error, contacta a tu supervisor o administrador para restablecerlo.\n\n¿Deseas proceder con la eliminación de todos modos?`;

          const forceOk = await this.confirmSvc.confirm(userFriendlyMsg, {
            title: 'Categoría en Uso por PDVs',
            confirmText: 'Sí, forzar eliminación',
            cancelText: 'Conservar ítem',
            danger: true
          });
          if (forceOk) this.forceRemove(item);
        } else {
          const errorMsg = typeof detail === 'string' ? detail : 'Ocurrió un error al intentar eliminar el elemento';
          this.snack.open(errorMsg, 'OK', { duration: 4000 });
        }
      }
    });
  }

  private forceRemove(item: CatalogItem | CiudadItem): void {
    const op = this.activeTab() === 'ciudades'
      ? this.api.deleteCiudad(item.id, true)
      : this.api.deleteCatalogItem(this.activeTab(), item.id, true);
    op.subscribe({
      next: () => {
        if (this.activeTab() === 'departamentos') this.loadDepartamentos();
        this.loadList();
        this.snack.open('Eliminado (los PDV referenciados quedaron sin este valor)', 'OK', { duration: 5000 });
      },
      error: (err) => this.snack.open(err?.error?.detail ?? 'Error al forzar eliminación', 'OK', { duration: 4000 })
    });
  }
}
