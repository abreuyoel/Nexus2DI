import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { ApiService } from '../../../core/services/api.service';
import { SearchableSelectComponent } from '../../../shared/components/searchable-select/searchable-select.component';

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
          <div class="space-y-1 min-w-[200px]">
            <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Departamento</label>
            <app-searchable-select
              [options]="departamentoOptions()"
              [(value)]="newCiudadDepId"
              placeholder="— Selecciona —">
            </app-searchable-select>
          </div>
        }
        <div class="space-y-1">
          <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Nuevo</label>
          <input [(ngModel)]="newName" (keyup.enter)="add()" [placeholder]="'Nombre de ' + currentTab().label.toLowerCase()"
            class="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-primary-500 rounded-xl px-3 py-2 text-sm font-semibold text-slate-900 dark:text-white placeholder-slate-400 outline-none w-full md:w-72">
        </div>
        <button (click)="add()" [disabled]="!canAdd() || saving()"
          class="flex items-center gap-2 px-5 py-2 bg-primary-600 hover:bg-primary-500 disabled:opacity-40 text-white font-black rounded-xl text-sm shadow-lg transition-all active:scale-95">
          @if (saving()) { <mat-spinner diameter="14"></mat-spinner> } @else { <mat-icon class="!text-base">add</mat-icon> }
          Agregar
        </button>
      </div>
    </div>
  </div>

  <!-- Filtro de departamento (sólo ciudades) -->
  @if (activeTab() === 'ciudades') {
    <div class="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-white/5 shadow-sm p-4 flex items-center gap-3">
      <mat-icon class="text-primary-500 !text-base">filter_list</mat-icon>
      <span class="text-xs font-black text-slate-500 uppercase tracking-widest">Filtrar por departamento</span>
      <div class="w-64">
        <app-searchable-select
          [options]="departamentoOptions()"
          [value]="filterDepId"
          (valueChange)="filterDepId = $event; loadList()"
          placeholder="Todos"
          [clearable]="true">
        </app-searchable-select>
      </div>
    </div>
  }

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
          @for (item of items(); track item.id) {
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
                    <app-searchable-select
                      [options]="departamentoOptions()"
                      [(value)]="editDepId">
                    </app-searchable-select>
                  } @else {
                    <span class="text-xs text-slate-500">{{ asCiudad(item).departamento_nombre || '—' }}</span>
                  }
                </td>
              }
              <td class="px-4 py-3">
                <button (click)="toggleActive(item)"
                  [ngClass]="{
                    'bg-emerald-100 text-emerald-700': item.activo,
                    'dark:bg-emerald-900/30 dark:text-emerald-400': item.activo,
                    'bg-slate-100 text-slate-500': !item.activo,
                    'dark:bg-slate-800 dark:text-slate-400': !item.activo
                  }"
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
                      class="w-8 h-8 rounded-lg bg-slate-200 dark:bg-white/5 hover:bg-slate-300 dark:hover:bg-white/10 text-slate-600 dark:text-slate-300 inline-flex items-center justify-center">
                      <mat-icon class="!text-sm">close</mat-icon>
                    </button>
                  } @else {
                    <button (click)="startEdit(item)" matTooltip="Editar"
                      class="w-8 h-8 rounded-lg bg-slate-100 dark:bg-white/5 hover:bg-primary-500 text-slate-500 dark:text-slate-400 hover:text-white inline-flex items-center justify-center">
                      <mat-icon class="!text-sm">edit</mat-icon>
                    </button>
                    <button (click)="remove(item)" matTooltip="Eliminar"
                      class="w-8 h-8 rounded-lg bg-slate-100 dark:bg-white/5 hover:bg-rose-500 text-slate-500 dark:text-slate-400 hover:text-white inline-flex items-center justify-center">
                      <mat-icon class="!text-sm">delete</mat-icon>
                    </button>
                  }
                </div>
              </td>
            </tr>
          }
          @if (items().length === 0) {
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
    </div>
  }
</div>
  `
})
export class CatalogosComponent implements OnInit {
  private api = inject(ApiService);
  private snack = inject(MatSnackBar);

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
  departamentoOptions = computed(() => this.departamentos().map(d => ({ value: d.id, label: d.nombre })));

  editingId = signal<number | null>(null);
  editName = '';
  editDepId: number | null = null;

  newName = '';
  newCiudadDepId: number | null = null;
  filterDepId: number | null = null;

  currentTab = computed(() => this.tabs.find(t => t.key === this.activeTab())!);
  canAdd = computed(() => {
    if (!this.newName.trim()) return false;
    if (this.activeTab() === 'ciudades' && !this.newCiudadDepId) return false;
    return true;
  });

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
    this.newName = '';
    this.filterDepId = null;
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
      this.api.listCiudades(this.filterDepId ? { departamento_id: this.filterDepId } : {}).subscribe({
        next: d => { this.items.set(d); this.loading.set(false); },
        error: () => this.loading.set(false)
      });
    } else {
      this.api.listCatalog(this.activeTab()).subscribe({
        next: d => { this.items.set(d); this.loading.set(false); },
        error: () => this.loading.set(false)
      });
    }
  }

  add(): void {
    if (!this.canAdd()) return;
    this.saving.set(true);
    const nombre = this.newName.trim();
    const op = this.activeTab() === 'ciudades'
      ? this.api.createCiudad({ nombre, departamento_id: this.newCiudadDepId! })
      : this.api.createCatalogItem(this.activeTab(), { nombre });
    op.subscribe({
      next: () => {
        this.saving.set(false);
        this.newName = '';
        // refrescar departamentos si se creó uno
        if (this.activeTab() === 'departamentos') this.loadDepartamentos();
        this.loadList();
        this.snack.open('Agregado', 'OK', { duration: 2000 });
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
    if (this.activeTab() === 'ciudades') this.editDepId = (item as CiudadItem).departamento_id;
  }

  cancelEdit(): void {
    this.editingId.set(null);
    this.editName = '';
    this.editDepId = null;
  }

  saveEdit(item: CatalogItem | CiudadItem): void {
    const nombre = this.editName.trim();
    if (!nombre) return;
    const op = this.activeTab() === 'ciudades'
      ? this.api.updateCiudad(item.id, { nombre, departamento_id: this.editDepId ?? undefined })
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

  remove(item: CatalogItem | CiudadItem): void {
    if (!confirm(`¿Eliminar "${item.nombre}"?`)) return;
    const op = this.activeTab() === 'ciudades'
      ? this.api.deleteCiudad(item.id)
      : this.api.deleteCatalogItem(this.activeTab(), item.id);
    op.subscribe({
      next: () => {
        if (this.activeTab() === 'departamentos') this.loadDepartamentos();
        this.loadList();
        this.snack.open('Eliminado', 'OK', { duration: 2000 });
      },
      error: (err) => {
        const detail = err?.error?.detail;
        if (typeof detail === 'object' && detail?.usage_count) {
          // Conflicto por uso: ofrecer forzar
          const msg = `${detail.message}\n\nEjemplos de PDV: ${(detail.sample_pdv_ids || []).join(', ')}\n\n¿Forzar eliminación de todos modos?`;
          if (confirm(msg)) this.forceRemove(item);
        } else {
          this.snack.open(typeof detail === 'string' ? detail : 'Error al eliminar', 'OK', { duration: 5000 });
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
