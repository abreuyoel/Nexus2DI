import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators, FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Subject, debounceTime, distinctUntilChanged } from 'rxjs';
import { ApiService } from '../../core/services/api.service';
import { HasPermDirective } from '../../core/directives/has-perm.directive';
import { SearchableSelectComponent, SelectOption } from '../client-visits/searchable-select.component';
import { ConfirmService } from '../../shared/components/confirm-dialog/confirm.service';

interface Producto {
  id: number;
  producto_gu: string;
  cod_prod?: string;
  descripcion_bi?: string;
  gramos?: number;
  inagotable?: boolean;
  comentario?: string;
  id_subcategoria?: number; subcategoria?: string;
  id_categoria?: number; categoria?: string;
  id_departamento?: number; departamento?: string;
  id_marca?: number; marca?: string; fabricante?: string;
  id_presentacion?: number; presentacion?: string;
  id_clasificacion_tamano?: number; tamano?: string;
}
interface Cat { id_categoria: number; nombre: string; id_departamento?: number; }
interface SubCat { id_subcategoria: number; nombre: string; id_categoria: number; }
interface Simple { id: number; nombre: string; id_productora?: number; }
type CatTab = 'departamentos' | 'categorias' | 'subcategorias' | 'marcas' | 'presentaciones' | 'tamanos';

@Component({
  selector: 'app-products',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, FormsModule, MatIconModule, MatSnackBarModule, MatProgressSpinnerModule, MatTooltipModule, HasPermDirective, SearchableSelectComponent],
  template: `
<div class="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white">

  <!-- HEADER -->
  <div class="bg-gradient-to-r from-slate-100 via-slate-100 to-slate-200 dark:from-slate-900 dark:via-slate-900 dark:to-slate-800 border-b border-slate-200 dark:border-white/8 px-8 py-6">
    <div class="flex items-center justify-between gap-4 flex-wrap">
      <div class="flex items-center gap-4">
        <div class="w-12 h-12 rounded-2xl bg-gradient-to-br from-violet-600 to-purple-700 flex items-center justify-center shadow-lg shrink-0">
          <mat-icon class="text-white !text-2xl">inventory_2</mat-icon>
        </div>
        <div>
          <h1 class="text-2xl font-black tracking-tight text-slate-900 dark:text-white leading-none">Productos</h1>
          <p class="text-slate-500 dark:text-slate-400 text-sm mt-0.5"><span class="font-bold text-violet-500 dark:text-violet-400">{{ total() }}</span> productos en catálogo</p>
        </div>
      </div>
      <div class="flex items-center gap-3">
        <button *hasPerm="'products'; action:'write'" (click)="openCatalogPanel()" class="flex items-center gap-2 px-5 py-2.5 bg-slate-200 hover:bg-slate-300 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 font-bold rounded-xl shadow-sm transition-all active:scale-95 text-sm border border-slate-300 dark:border-slate-700">
          <mat-icon class="!text-base">tune</mat-icon> Catálogos
        </button>
        <button *hasPerm="'products'; action:'write'" (click)="openPanel(null)" class="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-violet-700 to-purple-700 hover:from-violet-600 hover:to-purple-600 text-white font-black rounded-xl shadow-lg transition-all active:scale-95 text-sm">
          <mat-icon class="!text-base">add</mat-icon> Nuevo Producto
        </button>
      </div>
    </div>

    <!-- SEARCH + FILTERS -->
    <div class="flex flex-wrap items-center gap-3 mt-5">
      <div class="relative flex-1 min-w-52">
        <mat-icon class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 dark:text-slate-500 pointer-events-none !text-base">search</mat-icon>
        <input [ngModel]="searchText()" (ngModelChange)="onSearch($event)" placeholder="Buscar por nombre o código..."
          class="w-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-violet-500 text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 rounded-xl pl-9 pr-4 py-2.5 text-sm font-semibold outline-none transition-colors">
      </div>
      <div class="w-44 shrink-0">
        <app-searchable-select [options]="deptoFilterOptions()" [value]="filterDeptoStr"
          (valueChange)="onFilterDeptoChange($event)" placeholder="Todos los departamentos"
          searchPlaceholder="Buscar departamento..." allLabel="Todos los departamentos" icon="category"></app-searchable-select>
      </div>
      <div class="w-44 shrink-0">
        <app-searchable-select [options]="catFilterOptions()" [value]="filterCatStr"
          (valueChange)="onFilterCatChange($event)" placeholder="Todas las categorías"
          searchPlaceholder="Buscar categoría..." allLabel="Todas las categorías" icon="folder"></app-searchable-select>
      </div>
      <div class="w-44 shrink-0">
        <app-searchable-select [options]="subcatFilterOptions()" [value]="filterSubcatStr"
          (valueChange)="onFilterSubcatChange($event)" placeholder="Todas las subcategorías"
          searchPlaceholder="Buscar subcategoría..." allLabel="Todas las subcategorías" icon="folder_open"></app-searchable-select>
      </div>
      <div class="w-44 shrink-0">
        <app-searchable-select [options]="marcaFilterOptions()" [value]="filterMarcaStr"
          (valueChange)="onFilterMarcaChange($event)" placeholder="Todas las marcas"
          searchPlaceholder="Buscar marca..." allLabel="Todas las marcas" icon="local_offer"></app-searchable-select>
      </div>
      <div class="w-44 shrink-0">
        <app-searchable-select [options]="productoraFilterOptions()" [value]="filterProductoraStr"
          (valueChange)="onFilterProductoraChange($event)" placeholder="Todas las productoras"
          searchPlaceholder="Buscar productora..." allLabel="Todas las productoras" icon="factory"></app-searchable-select>
      </div>
      <div class="w-44 shrink-0">
        <app-searchable-select [options]="presentacionFilterOptions()" [value]="filterPresentacionStr"
          (valueChange)="onFilterPresentacionChange($event)" placeholder="Todas las presentaciones"
          searchPlaceholder="Buscar presentación..." allLabel="Todas las presentaciones" icon="view_module"></app-searchable-select>
      </div>
      <div class="w-44 shrink-0">
        <app-searchable-select [options]="tamanoFilterOptions()" [value]="filterTamanoStr"
          (valueChange)="onFilterTamanoChange($event)" placeholder="Todos los tamaños"
          searchPlaceholder="Buscar tamaño..." allLabel="Todos los tamaños" icon="straighten"></app-searchable-select>
      </div>
      <div class="relative">
        <select [ngModel]="filterInagotable()" (ngModelChange)="filterInagotable.set($event); reload()"
          class="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-violet-500 text-slate-900 dark:text-white rounded-xl px-3 py-2.5 pr-8 text-sm font-semibold appearance-none outline-none min-w-32">
          <option value="">Inagotable: todos</option>
          <option value="si">Inagotable: Sí</option>
          <option value="no">Inagotable: No</option>
        </select>
        <mat-icon class="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 dark:text-slate-500 pointer-events-none !text-base">expand_more</mat-icon>
      </div>
      @if (hasFilters) {
        <button (click)="clearFilters()" class="flex items-center gap-1.5 px-4 py-2.5 bg-slate-200 hover:bg-slate-300 dark:bg-slate-800 dark:hover:bg-slate-700 border border-slate-300 dark:border-slate-700 text-slate-500 dark:text-slate-400 dark:hover:text-white rounded-xl text-sm font-bold transition-all">
          <mat-icon class="!text-base">close</mat-icon> Limpiar
        </button>
      }
    </div>
  </div>

  <!-- TABLE -->
  <div class="px-8 py-6">
    @if (loading()) {
      <div class="flex items-center justify-center py-32"><mat-spinner diameter="40"></mat-spinner></div>
    } @else if (productos().length === 0) {
      <div class="flex flex-col items-center justify-center py-32 gap-4 text-slate-400 dark:text-slate-600">
        <div class="w-20 h-20 rounded-3xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center"><mat-icon class="!text-4xl">inventory_2</mat-icon></div>
        <p class="font-bold text-lg tracking-tight">No se encontraron productos</p>
      </div>
    } @else {
      <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/8 rounded-2xl overflow-hidden overflow-x-auto">
        <div class="grid grid-cols-[1.7fr_1fr_1fr_1.1fr_1.1fr_1fr_1fr_1fr_0.9fr_0.7fr_56px] gap-3 px-5 py-3 bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-white/8 text-[10px] font-black text-slate-500 dark:text-slate-400 uppercase tracking-widest min-w-[1520px]">
          <span>Producto</span><span>Cód. Barras</span><span>Departamento</span><span>Categoría</span><span>Subcategoría</span><span>Marca</span><span>Productora</span><span>Presentación</span><span>Tamaño</span><span>Inagotable</span><span></span>
        </div>
        @for (p of productos(); track p.id) {
          <div (click)="openDetails(p)" class="grid grid-cols-[1.7fr_1fr_1fr_1.1fr_1.1fr_1fr_1fr_1fr_0.9fr_0.7fr_56px] gap-3 items-center px-5 py-3.5 border-b border-slate-100 dark:border-white/5 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors group min-w-[1520px] cursor-pointer">
            <div class="flex items-center gap-3 min-w-0">
              <div class="w-9 h-9 rounded-xl bg-violet-100 dark:bg-violet-900 flex items-center justify-center shrink-0"><mat-icon class="!text-base text-violet-500 dark:text-violet-400">inventory_2</mat-icon></div>
              <p class="font-bold text-slate-900 dark:text-white text-sm truncate">{{ p.producto_gu || '—' }}</p>
            </div>
            <span class="text-xs font-mono text-slate-500 dark:text-slate-400 truncate">{{ p.cod_prod || '—' }}</span>
            <span class="text-sm text-slate-500 dark:text-slate-400 truncate">{{ p.departamento || '—' }}</span>
            <span class="text-sm text-slate-500 dark:text-slate-400 truncate">{{ p.categoria || '—' }}</span>
            <span class="text-sm text-slate-500 dark:text-slate-400 truncate">{{ p.subcategoria || '—' }}</span>
            <span class="text-sm text-slate-500 dark:text-slate-400 truncate">{{ p.marca || '—' }}</span>
            <span class="text-sm text-slate-500 dark:text-slate-400 truncate">{{ p.fabricante || '—' }}</span>
            <span class="text-sm text-slate-500 dark:text-slate-400 truncate">{{ p.presentacion || '—' }}</span>
            <span class="text-sm text-slate-500 dark:text-slate-400 truncate">{{ p.tamano || '—' }}</span>
            <span class="flex items-center">
              @if (p.inagotable) {
                <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-900/60 text-emerald-600 dark:text-emerald-400 text-[10px] font-black">
                  <mat-icon class="!text-[11px]">all_inclusive</mat-icon> Sí
                </span>
              } @else {
                <span class="text-slate-400 dark:text-slate-600 text-xs">No</span>
              }
            </span>
            <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button *hasPerm="'products'; action:'write'" (click)="openPanel(p); $event.stopPropagation()" matTooltip="Editar" class="w-8 h-8 rounded-lg bg-violet-100 dark:bg-violet-900 hover:bg-violet-200 dark:hover:bg-violet-800 text-violet-500 dark:text-violet-400 flex items-center justify-center"><mat-icon class="!text-base">edit</mat-icon></button>
              <button *hasPerm="'products'; action:'delete'" (click)="deleteProducto(p); $event.stopPropagation()" matTooltip="Eliminar" class="w-8 h-8 rounded-lg bg-red-100 dark:bg-red-950 hover:bg-red-200 dark:hover:bg-red-900 text-red-500 dark:text-red-400 flex items-center justify-center"><mat-icon class="!text-base">delete</mat-icon></button>
            </div>
          </div>
        }
      </div>

      <div class="flex flex-col sm:flex-row items-center justify-between gap-3 mt-5">
        <p class="text-sm text-slate-500 dark:text-slate-400">Mostrando <span class="text-slate-900 dark:text-white font-bold">{{ skipVal() + 1 }}–{{ skipVal() + productos().length }}</span> de <span class="text-slate-900 dark:text-white font-bold">{{ total() }}</span></p>
        <div class="flex items-center gap-2">
          <select [ngModel]="pageSize()" (ngModelChange)="onPageSize($event)"
            class="bg-slate-200 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-white rounded-xl px-3 py-2 text-sm font-bold outline-none" matTooltip="Registros por página">
            <option [ngValue]="20">20</option>
            <option [ngValue]="50">50</option>
            <option [ngValue]="100">100</option>
          </select>
          <button (click)="prevPage()" [disabled]="skipVal() === 0" class="flex items-center gap-1 px-4 py-2 bg-slate-200 hover:bg-slate-300 dark:bg-slate-800 dark:hover:bg-slate-700 disabled:opacity-40 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-white rounded-xl text-sm font-bold"><mat-icon class="!text-base">chevron_left</mat-icon> Anterior</button>
          <button (click)="nextPage()" [disabled]="skipVal() + pageSize() >= total()" class="flex items-center gap-1 px-4 py-2 bg-slate-200 hover:bg-slate-300 dark:bg-slate-800 dark:hover:bg-slate-700 disabled:opacity-40 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-white rounded-xl text-sm font-bold">Siguiente <mat-icon class="!text-base">chevron_right</mat-icon></button>
        </div>
      </div>
    }
  </div>
</div>

<!-- SLIDE PANEL: PRODUCTO -->
@if (panelOpen()) {
  <div class="fixed inset-0 z-50 flex justify-end">
    <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" (click)="closePanel()"></div>
    <div class="relative w-full max-w-md bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-white/8 h-full flex flex-col shadow-2xl">
      <div class="bg-gradient-to-r from-slate-100 to-slate-200 dark:from-slate-800 dark:to-slate-900 border-b border-slate-200 dark:border-white/8 px-6 py-5 shrink-0 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-violet-100 dark:bg-violet-900 flex items-center justify-center"><mat-icon class="text-violet-500 dark:text-violet-400 !text-xl">{{ editingId() ? 'edit' : 'add_circle' }}</mat-icon></div>
          <div><h3 class="font-black text-slate-900 dark:text-white">{{ editingId() ? 'Editar Producto' : 'Nuevo Producto' }}</h3><p class="text-xs text-slate-500 dark:text-slate-400">{{ editingId() ? 'Modifica los datos' : 'Agrega al catálogo' }}</p></div>
        </div>
        <button (click)="closePanel()" class="w-9 h-9 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-white/5 dark:hover:bg-white/10 flex items-center justify-center text-slate-500 dark:text-slate-400 dark:hover:text-white"><mat-icon class="!text-lg">close</mat-icon></button>
      </div>

      <form [formGroup]="form" class="flex-1 px-6 py-6 space-y-5 overflow-y-auto">
        <div class="space-y-1.5">
          <label class="text-[10px] font-black text-slate-500 dark:text-slate-400 uppercase tracking-widest">Nombre del producto *</label>
          <input formControlName="producto_gu" placeholder="Nombre del producto" class="w-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-violet-500 rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 outline-none" [class.border-red-500]="form.get('producto_gu')?.invalid && form.get('producto_gu')?.touched">
          @if (form.get('producto_gu')?.invalid && form.get('producto_gu')?.touched) { <p class="text-xs text-red-400 dark:text-red-500">El nombre es requerido</p> }
        </div>
        <div class="space-y-1.5">
          <label class="text-[10px] font-black text-slate-500 dark:text-slate-400 uppercase tracking-widest">Código de barras / SKU</label>
          <input formControlName="cod_prod" placeholder="Ej: 7501234567890" class="w-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-violet-500 rounded-xl px-4 py-2.5 text-sm font-semibold font-mono text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 outline-none">
        </div>

        <!-- Departamento -> Categoría -> Subcategoría (cascada) -->
        <div class="space-y-1.5">
          <label class="text-[10px] font-black text-slate-500 dark:text-slate-400 uppercase tracking-widest">Departamento</label>
          <app-searchable-select [options]="deptOptions()" [value]="deptStr"
            (valueChange)="onDeptChange($event)" placeholder="— Selecciona —"
            searchPlaceholder="Buscar departamento..." allLabel="— Selecciona —" icon="category"></app-searchable-select>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-1.5">
            <label class="text-[10px] font-black text-slate-500 dark:text-slate-400 uppercase tracking-widest">Categoría</label>
            <app-searchable-select [options]="catOptions()" [value]="catStr"
              (valueChange)="onCatChange($event)" placeholder="— Selecciona —"
              searchPlaceholder="Buscar categoría..." allLabel="— Selecciona —" icon="folder"></app-searchable-select>
          </div>
          <div class="space-y-1.5">
            <label class="text-[10px] font-black text-slate-500 dark:text-slate-400 uppercase tracking-widest">Subcategoría</label>
            <app-searchable-select [options]="subcatOptions()" [value]="subcatStr"
              (valueChange)="onSubcatChange($event)" placeholder="— Selecciona —"
              searchPlaceholder="Buscar subcategoría..." allLabel="— Selecciona —" icon="folder_open"></app-searchable-select>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-1.5">
            <label class="text-[10px] font-black text-slate-500 dark:text-slate-400 uppercase tracking-widest">Marca / Fabricante</label>
            <app-searchable-select [options]="marcaOptions()" [value]="marcaStr"
              (valueChange)="onMarcaChange($event)" placeholder="— Selecciona —"
              searchPlaceholder="Buscar marca..." allLabel="— Selecciona —" icon="local_offer"></app-searchable-select>
          </div>
          <div class="space-y-1.5">
            <label class="text-[10px] font-black text-slate-500 dark:text-slate-400 uppercase tracking-widest">Presentación</label>
            <app-searchable-select [options]="presentacionOptions()" [value]="presentacionStr"
              (valueChange)="onPresentacionChange($event)" placeholder="— Selecciona —"
              searchPlaceholder="Buscar presentación..." allLabel="— Selecciona —" icon="view_module"></app-searchable-select>
          </div>
        </div>

        <div class="space-y-1.5">
          <label class="text-[10px] font-black text-slate-500 dark:text-slate-400 uppercase tracking-widest">Tamaño</label>
          <app-searchable-select [options]="tamanoOptions()" [value]="tamanoStr"
            (valueChange)="onTamanoChange($event)" placeholder="— Selecciona —"
            searchPlaceholder="Buscar tamaño..." allLabel="— Selecciona —" icon="straighten"></app-searchable-select>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-1.5">
            <label class="text-[10px] font-black text-slate-500 dark:text-slate-400 uppercase tracking-widest">Descripción BI</label>
            <input formControlName="descripcion_bi" placeholder="Descripción" class="w-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-violet-500 rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 outline-none">
          </div>
          <div class="space-y-1.5">
            <label class="text-[10px] font-black text-slate-500 dark:text-slate-400 uppercase tracking-widest">Gramos</label>
            <input formControlName="gramos" type="number" placeholder="0" class="w-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-violet-500 rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 outline-none">
          </div>
        </div>
        <div class="space-y-1.5">
          <label class="text-[10px] font-black text-slate-500 dark:text-slate-400 uppercase tracking-widest">Inagotable</label>
          <label class="flex items-center gap-3 cursor-pointer">
            <input type="checkbox" formControlName="inagotable" class="sr-only peer">
            <div class="relative w-11 h-6 bg-slate-300 dark:bg-slate-700 peer-checked:bg-emerald-600 rounded-full transition-colors">
              <div class="absolute left-1 top-1 w-4 h-4 bg-white rounded-full shadow transition-transform peer-checked:translate-x-5 translate-x-0"></div>
            </div>
            <span class="text-sm text-slate-600 dark:text-slate-300 font-semibold peer-checked:text-emerald-600 dark:peer-checked:text-emerald-400">{{ form.get('inagotable')?.value ? 'Sí — el producto nunca se agota' : 'No — stock normal' }}</span>
          </label>
        </div>
        <div class="space-y-1.5">
          <label class="text-[10px] font-black text-slate-500 dark:text-slate-400 uppercase tracking-widest">Comentario</label>
          <textarea formControlName="comentario" rows="2" placeholder="Notas (opcional)" class="w-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-violet-500 rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 outline-none resize-none"></textarea>
        </div>
      </form>

      <div class="px-6 py-5 border-t border-slate-200 dark:border-white/8 bg-slate-50 dark:bg-slate-900 shrink-0 flex gap-3">
        <button type="button" (click)="closePanel()" class="flex-1 py-2.5 border border-slate-300 dark:border-slate-700 text-slate-500 dark:text-slate-400 dark:hover:text-white rounded-xl font-bold text-sm">Cancelar</button>
        <button type="button" (click)="saveProducto()" [disabled]="form.invalid || saving()" class="flex-1 flex items-center justify-center gap-2 py-2.5 bg-gradient-to-r from-violet-700 to-purple-700 hover:from-violet-600 hover:to-purple-600 disabled:opacity-50 text-white font-black rounded-xl text-sm shadow-lg active:scale-95">
          @if (saving()) { <mat-spinner diameter="16"></mat-spinner> } @else { <mat-icon class="!text-base">{{ editingId() ? 'save' : 'add' }}</mat-icon> }
          {{ editingId() ? 'Guardar Cambios' : 'Crear Producto' }}
        </button>
      </div>
    </div>
  </div>
}

<!-- CATALOG PANEL (multi-pestaña ABM) -->
@if (catalogPanelOpen()) {
  <div class="fixed inset-0 z-[60] flex justify-end">
    <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" (click)="closeCatalogPanel()"></div>
    <div class="relative w-full max-w-lg bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-white/8 h-full flex flex-col shadow-2xl">
      <div class="bg-gradient-to-r from-slate-100 to-slate-200 dark:from-slate-800 dark:to-slate-900 border-b border-slate-200 dark:border-white/8 px-6 py-5 shrink-0 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-violet-100 dark:bg-violet-900 flex items-center justify-center"><mat-icon class="text-violet-500 dark:text-violet-400 !text-xl">tune</mat-icon></div>
          <div><h3 class="font-black text-slate-900 dark:text-white">Catálogos (Snowflake)</h3><p class="text-xs text-slate-500 dark:text-slate-400">Departamentos → Categorías → Subcategorías · Marcas · Presentaciones · Tamaños</p></div>
        </div>
        <button (click)="closeCatalogPanel()" class="w-9 h-9 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-white/5 dark:hover:bg-white/10 flex items-center justify-center text-slate-500 dark:text-slate-400 dark:hover:text-white"><mat-icon class="!text-lg">close</mat-icon></button>
      </div>

      <!-- Tabs -->
      <div class="px-4 pt-4 shrink-0">
        <div class="flex gap-1 bg-slate-100 dark:bg-slate-800 rounded-xl p-1 overflow-x-auto">
          @for (t of tabs; track t.key) {
            <button (click)="setTab(t.key)" [ngClass]="catTab() === t.key ? 'bg-violet-600 text-white' : 'text-slate-500 dark:text-slate-400 dark:hover:text-white'" class="flex-1 px-3 py-1.5 rounded-lg text-xs font-bold whitespace-nowrap transition-all">{{ t.label }}</button>
          }
        </div>
      </div>

      <!-- Add row -->
      <div class="px-4 pt-4 shrink-0">
        <div class="bg-slate-100 dark:bg-slate-800 rounded-2xl p-4 border border-slate-200 dark:border-slate-700 space-y-3">
          <h4 class="text-sm font-bold text-slate-900 dark:text-white">Agregar {{ currentTab().singular }}</h4>
          <div class="flex flex-wrap gap-2">
            <input [(ngModel)]="newName" [placeholder]="'Nombre de ' + currentTab().singular.toLowerCase()" class="flex-1 min-w-40 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-900 dark:text-white outline-none focus:border-violet-500">
            @if (catTab() === 'categorias') {
              <div class="w-56">
                <app-searchable-select [options]="deptParentOptions()" [value]="newParentStr"
                  (valueChange)="onNewParentChange($event)" placeholder="Departamento…"
                  searchPlaceholder="Buscar departamento..." allLabel="Departamento…" icon="category"></app-searchable-select>
              </div>
            }
            @if (catTab() === 'subcategorias') {
              <div class="w-56">
                <app-searchable-select [options]="catParentOptions()" [value]="newParentStr"
                  (valueChange)="onNewParentChange($event)" placeholder="Categoría…"
                  searchPlaceholder="Buscar categoría..." allLabel="Categoría…" icon="folder"></app-searchable-select>
              </div>
            }
            @if (catTab() === 'marcas') {
              <div class="w-56">
                <app-searchable-select [options]="productoraParentOptions()" [value]="newParentStr"
                  (valueChange)="onNewParentChange($event)" placeholder="Productora (opcional)…"
                  searchPlaceholder="Buscar productora..." allLabel="Productora (opcional)…" icon="factory"></app-searchable-select>
              </div>
            }
            <button (click)="addCatItem()" [disabled]="!newName || (needsParent() && !newParent)" class="px-4 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-sm font-bold disabled:opacity-50">Agregar</button>
          </div>
        </div>
      </div>

      <!-- List -->
      <div class="flex-1 overflow-y-auto p-4 space-y-2">
        @for (it of currentCatList(); track it.id) {
          <div class="flex items-center justify-between bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5">
            <div class="min-w-0">
              <span class="font-bold text-sm text-slate-900 dark:text-white">{{ it.nombre }}</span>
              @if (it.extra) { <span class="text-xs text-slate-500 dark:text-slate-400 ml-2">({{ it.extra }})</span> }
            </div>
            <button (click)="delCatItem(it.id)" class="text-red-500 hover:text-red-400 dark:text-red-400 dark:hover:text-red-300"><mat-icon class="!text-lg">delete</mat-icon></button>
          </div>
        }
        @if (currentCatList().length === 0) { <p class="text-center text-slate-400 dark:text-slate-600 text-sm py-8">Sin elementos</p> }
      </div>
    </div>
  </div>
}

<!-- MODAL: DETALLES DEL PRODUCTO -->
@if (detailsModalOpen() && selectedProduct()) {
  <div class="fixed inset-0 z-[150] flex items-center justify-center p-4">
    <!-- Backdrop -->
    <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" (click)="closeDetails()"></div>
    
    <!-- Modal Card -->
    <div class="relative w-full max-w-lg bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-white/8 shadow-2xl overflow-hidden flex flex-col max-h-[90vh] animate-in fade-in zoom-in-95 duration-200">
      <!-- Header -->
      <div class="bg-gradient-to-r from-violet-600 to-indigo-600 px-6 py-5 flex items-center justify-between text-white shrink-0">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center">
            <mat-icon class="!text-xl text-white">inventory_2</mat-icon>
          </div>
          <div>
            <h3 class="font-black text-sm uppercase tracking-wider text-white/90">Detalles del Producto</h3>
            <p class="text-[10px] text-indigo-100 font-semibold">Ficha técnica del catálogo</p>
          </div>
        </div>
        <button (click)="closeDetails()" class="w-9 h-9 rounded-xl bg-white/10 hover:bg-white/20 flex items-center justify-center text-white transition-colors">
          <mat-icon class="!text-lg">close</mat-icon>
        </button>
      </div>

      <!-- Content -->
      <div class="flex-grow p-6 overflow-y-auto space-y-6">
        <!-- Title & Code -->
        <div class="space-y-1">
          <span class="text-[10px] font-black text-violet-500 uppercase tracking-widest block">Nombre</span>
          <h2 class="text-xl font-black text-slate-900 dark:text-white leading-snug">{{ selectedProduct()?.producto_gu }}</h2>
          @if (selectedProduct()?.cod_prod) {
            <div class="flex items-center gap-1.5 mt-1.5">
              <span class="text-[9px] font-black uppercase tracking-wider text-slate-400 bg-slate-100 dark:bg-white/5 px-2 py-0.5 rounded">SKU / Cód. Barras</span>
              <span class="text-xs font-mono font-bold text-slate-600 dark:text-slate-300">{{ selectedProduct()?.cod_prod }}</span>
            </div>
          }
        </div>

        <!-- Details Grid -->
        <div class="grid grid-cols-2 gap-4">
          <!-- Departamento -->
          <div class="p-3 bg-slate-50 dark:bg-white/5 rounded-2xl border border-slate-100 dark:border-white/5">
            <span class="text-[9px] font-black text-slate-400 uppercase tracking-widest block">Departamento</span>
            <span class="text-sm font-bold text-slate-800 dark:text-slate-200 mt-1 block truncate" [title]="selectedProduct()?.departamento">{{ selectedProduct()?.departamento || '—' }}</span>
          </div>

          <!-- Categoría -->
          <div class="p-3 bg-slate-50 dark:bg-white/5 rounded-2xl border border-slate-100 dark:border-white/5">
            <span class="text-[9px] font-black text-slate-400 uppercase tracking-widest block">Categoría</span>
            <span class="text-sm font-bold text-slate-800 dark:text-slate-200 mt-1 block truncate" [title]="selectedProduct()?.categoria">{{ selectedProduct()?.categoria || '—' }}</span>
          </div>

          <!-- Subcategoría -->
          <div class="p-3 bg-slate-50 dark:bg-white/5 rounded-2xl border border-slate-100 dark:border-white/5">
            <span class="text-[9px] font-black text-slate-400 uppercase tracking-widest block">Subcategoría</span>
            <span class="text-sm font-bold text-slate-800 dark:text-slate-200 mt-1 block truncate" [title]="selectedProduct()?.subcategoria">{{ selectedProduct()?.subcategoria || '—' }}</span>
          </div>

          <!-- Marca -->
          <div class="p-3 bg-slate-50 dark:bg-white/5 rounded-2xl border border-slate-100 dark:border-white/5">
            <span class="text-[9px] font-black text-slate-400 uppercase tracking-widest block">Marca</span>
            <span class="text-sm font-bold text-slate-800 dark:text-slate-200 mt-1 block truncate" [title]="selectedProduct()?.marca">{{ selectedProduct()?.marca || '—' }}</span>
          </div>

          <!-- Productora / Fabricante -->
          <div class="p-3 bg-slate-50 dark:bg-white/5 rounded-2xl border border-slate-100 dark:border-white/5">
            <span class="text-[9px] font-black text-slate-400 uppercase tracking-widest block">Productora</span>
            <span class="text-sm font-bold text-slate-800 dark:text-slate-200 mt-1 block truncate" [title]="selectedProduct()?.fabricante">{{ selectedProduct()?.fabricante || '—' }}</span>
          </div>

          <!-- Presentación -->
          <div class="p-3 bg-slate-50 dark:bg-white/5 rounded-2xl border border-slate-100 dark:border-white/5">
            <span class="text-[9px] font-black text-slate-400 uppercase tracking-widest block">Presentación</span>
            <span class="text-sm font-bold text-slate-800 dark:text-slate-200 mt-1 block truncate" [title]="selectedProduct()?.presentacion">{{ selectedProduct()?.presentacion || '—' }}</span>
          </div>

          <!-- Tamaño -->
          <div class="p-3 bg-slate-50 dark:bg-white/5 rounded-2xl border border-slate-100 dark:border-white/5">
            <span class="text-[9px] font-black text-slate-400 uppercase tracking-widest block">Tamaño</span>
            <span class="text-sm font-bold text-slate-800 dark:text-slate-200 mt-1 block truncate" [title]="selectedProduct()?.tamano">{{ selectedProduct()?.tamano || '—' }}</span>
          </div>

          <!-- Gramos -->
          <div class="p-3 bg-slate-50 dark:bg-white/5 rounded-2xl border border-slate-100 dark:border-white/5">
            <span class="text-[9px] font-black text-slate-400 uppercase tracking-widest block">Peso (Gramos)</span>
            <span class="text-sm font-bold text-slate-800 dark:text-slate-200 mt-1 block">{{ selectedProduct()?.gramos != null ? selectedProduct()?.gramos + ' g' : '—' }}</span>
          </div>
        </div>

        <!-- Descripción BI & Inagotable -->
        <div class="space-y-4">
          @if (selectedProduct()?.descripcion_bi) {
            <div class="p-4 bg-slate-50 dark:bg-white/5 rounded-2xl border border-slate-100 dark:border-white/5">
              <span class="text-[9px] font-black text-slate-400 uppercase tracking-widest block mb-1">Descripción BI</span>
              <p class="text-sm text-slate-700 dark:text-slate-300 font-semibold">{{ selectedProduct()?.descripcion_bi }}</p>
            </div>
          }

          <!-- Inagotable Status -->
          <div class="flex items-center justify-between p-4 bg-slate-50 dark:bg-white/5 rounded-2xl border border-slate-100 dark:border-white/5">
            <div>
              <span class="text-[9px] font-black text-slate-400 uppercase tracking-widest block">Estado de Stock</span>
              <span class="text-xs text-slate-500 dark:text-slate-400 font-medium">Define si el producto puede agotarse</span>
            </div>
            @if (selectedProduct()?.inagotable) {
              <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-100 dark:bg-emerald-900/60 text-emerald-600 dark:text-emerald-400 text-xs font-black shadow-sm">
                <mat-icon class="!text-xs">all_inclusive</mat-icon> Inagotable
              </span>
            } @else {
              <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-200 dark:bg-white/10 text-slate-600 dark:text-slate-300 text-xs font-black">
                <mat-icon class="!text-xs">inventory</mat-icon> Stock Limitado
              </span>
            }
          </div>

          @if (selectedProduct()?.comentario) {
            <div class="p-4 bg-slate-50 dark:bg-white/5 rounded-2xl border border-slate-100 dark:border-white/5">
              <span class="text-[9px] font-black text-slate-400 uppercase tracking-widest block mb-1">Comentario</span>
              <p class="text-xs text-slate-500 dark:text-slate-400 leading-relaxed italic">"{{ selectedProduct()?.comentario }}"</p>
            </div>
          }
        </div>
      </div>

      <!-- Footer -->
      <div class="px-6 py-5 border-t border-slate-200 dark:border-white/8 bg-slate-50 dark:bg-slate-900 shrink-0">
        <button type="button" (click)="closeDetails()" class="w-full py-3 bg-violet-600 hover:bg-violet-500 text-white font-black rounded-2xl text-sm transition-all active:scale-[0.98] shadow-lg shadow-violet-500/10">
          Cerrar
        </button>
      </div>
    </div>
  </div>
}
  `
})
export class ProductsComponent implements OnInit {
  productos = signal<Producto[]>([]);
  total = signal(0);
  loading = signal(false);
  saving = signal(false);
  panelOpen = signal(false);
  editingId = signal<number | null>(null);
  detailsModalOpen = signal(false);
  selectedProduct = signal<Producto | null>(null);

  catList = signal<Cat[]>([]);
  subcatList = signal<SubCat[]>([]);
  marcasList = signal<Simple[]>([]);
  presentacionesList = signal<Simple[]>([]);
  departamentosList = signal<Simple[]>([]);
  productorasList = signal<Simple[]>([]);
  tamanosList = signal<Simple[]>([]);

  // catálogo (panel)
  catalogPanelOpen = signal(false);
  catTab = signal<CatTab>('departamentos');
  newName = '';
  newParent: number | null = null;
  tabs: { key: CatTab; label: string; singular: string }[] = [
    { key: 'departamentos', label: 'Departamentos', singular: 'Departamento' },
    { key: 'categorias', label: 'Categorías', singular: 'Categoría' },
    { key: 'subcategorias', label: 'Subcategorías', singular: 'Subcategoría' },
    { key: 'marcas', label: 'Marcas', singular: 'Marca' },
    { key: 'presentaciones', label: 'Presentaciones', singular: 'Presentación' },
    { key: 'tamanos', label: 'Tamaños', singular: 'Tamaño' },
  ];

  searchText = signal('');
  filterDepartamento = signal<number | null>(null);
  filterCategoria = signal<number | null>(null);
  filterSubcategoria = signal<number | null>(null);
  filterMarca = signal<number | null>(null);
  filterProductora = signal<number | null>(null);
  filterPresentacion = signal<number | null>(null);
  filterTamano = signal<number | null>(null);
  filterInagotable = signal<'' | 'si' | 'no'>('');
  // Opciones de los selects de filtro, cascadeadas según lo que ya está
  // elegido (ej. si filtrás por productora, categoría/marca/etc. solo
  // muestran lo que esa productora realmente tiene) -- ver loadFacetOpts().
  facetOpts = signal<{ departamentos: Simple[]; categorias: Simple[]; subcategorias: Simple[]; marcas: Simple[]; productoras: Simple[]; presentaciones: Simple[]; tamanos: Simple[] }>({
    departamentos: [], categorias: [], subcategorias: [], marcas: [], productoras: [], presentaciones: [], tamanos: [],
  });
  skipVal = signal(0);
  pageSize = signal(20);
  private search$ = new Subject<string>();

  // ── Filtros: opciones searchable ──
  deptoFilterOptions = computed<SelectOption[]>(() => this.facetOpts().departamentos.map(d => ({ value: String(d.id), label: d.nombre })));
  catFilterOptions = computed<SelectOption[]>(() => {
    const list = this.facetOpts().categorias.map(c => ({ value: String(c.id), label: c.nombre }));
    return [{ value: '-1', label: '❌ Sin Categoría' }, ...list];
  });
  subcatFilterOptions = computed<SelectOption[]>(() => this.facetOpts().subcategorias.map(s => ({ value: String(s.id), label: s.nombre })));
  marcaFilterOptions = computed<SelectOption[]>(() => this.facetOpts().marcas.map(m => ({ value: String(m.id), label: m.nombre })));
  productoraFilterOptions = computed<SelectOption[]>(() => this.facetOpts().productoras.map(p => ({ value: String(p.id), label: p.nombre })));
  presentacionFilterOptions = computed<SelectOption[]>(() => this.facetOpts().presentaciones.map(p => ({ value: String(p.id), label: p.nombre })));
  tamanoFilterOptions = computed<SelectOption[]>(() => this.facetOpts().tamanos.map(t => ({ value: String(t.id), label: t.nombre })));

  // ── Panel de edición: opciones y cascada ──
  formDept = signal<number | null>(null);
  formCat = signal<number | null>(null);
  formSubcat = signal<number | null>(null);
  formMarca = signal<number | null>(null);
  formPresentacion = signal<number | null>(null);
  formTamano = signal<number | null>(null);

  // ── Modal de catálogos: opciones de padre ──
  deptParentOptions = computed<SelectOption[]>(() => this.departamentosList().map(d => ({ value: String(d.id), label: d.nombre })));
  catParentOptions = computed<SelectOption[]>(() => this.catList().map(c => ({ value: String(c.id_categoria), label: c.nombre })));
  productoraParentOptions = computed<SelectOption[]>(() => this.productorasList().map(p => ({ value: String(p.id), label: p.nombre })));
  get newParentStr(): string { return this.newParent != null ? String(this.newParent) : ''; }

  deptOptions = computed<SelectOption[]>(() => this.departamentosList().map(d => ({ value: String(d.id), label: d.nombre })));
  catOptions = computed<SelectOption[]>(() => {
    const id = this.formDept();
    const list = id ? this.catList().filter(c => c.id_departamento === id) : this.catList();
    return list.map(c => ({ value: String(c.id_categoria), label: c.nombre }));
  });
  subcatOptions = computed<SelectOption[]>(() => {
    const id = this.formCat();
    const list = id ? this.subcatList().filter(s => s.id_categoria === id) : this.subcatList();
    return list.map(s => ({ value: String(s.id_subcategoria), label: s.nombre }));
  });
  marcaOptions = computed<SelectOption[]>(() => this.marcasList().map(m => ({ value: String(m.id), label: m.nombre })));
  presentacionOptions = computed<SelectOption[]>(() => this.presentacionesList().map(p => ({ value: String(p.id), label: p.nombre })));
  tamanoOptions = computed<SelectOption[]>(() => this.tamanosList().map(t => ({ value: String(t.id), label: t.nombre })));

  form = this.fb.group({
    producto_gu: ['', Validators.required],
    cod_prod: [''],
    id_departamento: [null as number | null],
    id_categoria: [null as number | null],
    id_subcategoria: [null as number | null],
    id_marca: [null as number | null],
    id_presentacion: [null as number | null],
    id_clasificacion_tamano: [null as number | null],
    descripcion_bi: [''],
    gramos: [null as number | null],
    inagotable: [false as boolean],
    comentario: [''],
  });

  constructor(
    private api: ApiService,
    private fb: FormBuilder,
    private snack: MatSnackBar,
    private confirmSvc: ConfirmService
  ) { }

  ngOnInit(): void {
    this.loadProductos();
    this.loadFacetOpts();
    this.loadCatalogs();
    this.search$.pipe(debounceTime(350), distinctUntilChanged()).subscribe(() => { this.skipVal.set(0); this.loadProductos(); this.loadFacetOpts(); });
  }

  /** Filtros activos, compartidos entre loadProductos() y loadFacetOpts()
   * (que además necesita saber cuál es cada uno para excluirlo de su propia
   * faceta -- ver comentario del endpoint en el backend). */
  private currentFilters() {
    return {
      busqueda: this.searchText() || undefined,
      id_departamento: this.filterDepartamento() ?? undefined,
      id_categoria: this.filterCategoria() ?? undefined,
      id_subcategoria: this.filterSubcategoria() ?? undefined,
      id_marca: this.filterMarca() ?? undefined,
      id_productora: this.filterProductora() ?? undefined,
      id_presentacion: this.filterPresentacion() ?? undefined,
      id_clasificacion_tamano: this.filterTamano() ?? undefined,
      inagotable: this.filterInagotable() ? this.filterInagotable() === 'si' : undefined,
    };
  }

  loadProductos(): void {
    this.loading.set(true);
    this.api.getProductos({ skip: this.skipVal(), limit: this.pageSize(), ...this.currentFilters() })
      .subscribe({ next: (res) => { this.productos.set(res.items); this.total.set(res.total); this.loading.set(false); }, error: () => this.loading.set(false) });
  }

  loadFacetOpts(): void {
    this.api.getProductosFiltrosDisponibles(this.currentFilters())
      .subscribe({ next: (d) => this.facetOpts.set(d), error: () => { } });
  }

  loadCatalogs(): void {
    this.api.getCatalogosCategorias().subscribe({ next: d => this.catList.set(d), error: () => { } });
    this.api.getCatalogosSubCategorias().subscribe({ next: d => this.subcatList.set(d), error: () => { } });
    this.api.getCatMarcas().subscribe({ next: d => this.marcasList.set(d), error: () => { } });
    this.api.getCatPresentaciones().subscribe({ next: d => this.presentacionesList.set(d), error: () => { } });
    this.api.getCatDepartamentos().subscribe({ next: d => this.departamentosList.set(d), error: () => { } });
    this.api.getCatProductoras().subscribe({ next: d => this.productorasList.set(d), error: () => { } });
    this.api.getCatTamanos().subscribe({ next: d => this.tamanosList.set(d), error: () => { } });
  }

  // ── Handlers de filtros (searchable select → señal) ──
  get filterDeptoStr(): string { return this.filterDepartamento() != null ? String(this.filterDepartamento()!) : ''; }
  get filterCatStr(): string { return this.filterCategoria() != null ? String(this.filterCategoria()!) : ''; }
  get filterSubcatStr(): string { return this.filterSubcategoria() != null ? String(this.filterSubcategoria()!) : ''; }
  get filterMarcaStr(): string { return this.filterMarca() != null ? String(this.filterMarca()!) : ''; }
  get filterProductoraStr(): string { return this.filterProductora() != null ? String(this.filterProductora()!) : ''; }
  get filterPresentacionStr(): string { return this.filterPresentacion() != null ? String(this.filterPresentacion()!) : ''; }
  get filterTamanoStr(): string { return this.filterTamano() != null ? String(this.filterTamano()!) : ''; }

  onFilterDeptoChange(val: string): void { this.filterDepartamento.set(val ? +val : null); this.reload(); }
  onFilterCatChange(val: string): void { this.filterCategoria.set(val ? +val : null); this.reload(); }
  onFilterSubcatChange(val: string): void { this.filterSubcategoria.set(val ? +val : null); this.reload(); }
  onFilterMarcaChange(val: string): void { this.filterMarca.set(val ? +val : null); this.reload(); }
  onFilterProductoraChange(val: string): void { this.filterProductora.set(val ? +val : null); this.reload(); }
  onFilterPresentacionChange(val: string): void { this.filterPresentacion.set(val ? +val : null); this.reload(); }
  onFilterTamanoChange(val: string): void { this.filterTamano.set(val ? +val : null); this.reload(); }

  // ── Handlers del panel (searchable select → señal + form) ──
  get deptStr(): string { return this.formDept() != null ? String(this.formDept()!) : ''; }
  get catStr(): string { return this.formCat() != null ? String(this.formCat()!) : ''; }
  get subcatStr(): string { return this.formSubcat() != null ? String(this.formSubcat()!) : ''; }
  get marcaStr(): string { return this.formMarca() != null ? String(this.formMarca()!) : ''; }
  get presentacionStr(): string { return this.formPresentacion() != null ? String(this.formPresentacion()!) : ''; }
  get tamanoStr(): string { return this.formTamano() != null ? String(this.formTamano()!) : ''; }

  onDeptChange(val: string): void {
    this.formDept.set(val ? +val : null);
    this.formCat.set(null); this.formSubcat.set(null);
    this.form.patchValue({ id_departamento: this.formDept(), id_categoria: null, id_subcategoria: null });
  }
  onCatChange(val: string): void {
    this.formCat.set(val ? +val : null);
    this.formSubcat.set(null);
    this.form.patchValue({ id_categoria: this.formCat(), id_subcategoria: null });
  }
  onSubcatChange(val: string): void {
    this.formSubcat.set(val ? +val : null);
    this.form.patchValue({ id_subcategoria: this.formSubcat() });
  }
  onMarcaChange(val: string): void { this.formMarca.set(val ? +val : null); this.form.patchValue({ id_marca: this.formMarca() }); }
  onPresentacionChange(val: string): void { this.formPresentacion.set(val ? +val : null); this.form.patchValue({ id_presentacion: this.formPresentacion() }); }
  onTamanoChange(val: string): void { this.formTamano.set(val ? +val : null); this.form.patchValue({ id_clasificacion_tamano: this.formTamano() }); }
  onNewParentChange(val: string): void { this.newParent = val ? +val : null; }

  onSearch(val: string): void { this.searchText.set(val); this.search$.next(val); }
  reload(): void { this.skipVal.set(0); this.loadProductos(); this.loadFacetOpts(); }
  get hasFilters(): boolean {
    return !!(this.searchText() || this.filterDepartamento() || this.filterCategoria() || this.filterSubcategoria() ||
      this.filterMarca() || this.filterProductora() || this.filterPresentacion() || this.filterTamano() || this.filterInagotable());
  }
  clearFilters(): void {
    this.searchText.set(''); this.filterDepartamento.set(null); this.filterCategoria.set(null); this.filterSubcategoria.set(null);
    this.filterMarca.set(null); this.filterProductora.set(null); this.filterPresentacion.set(null); this.filterTamano.set(null);
    this.filterInagotable.set(''); this.skipVal.set(0); this.loadProductos(); this.loadFacetOpts();
  }
  prevPage(): void { this.skipVal.update(v => Math.max(0, v - this.pageSize())); this.loadProductos(); }
  nextPage(): void { this.skipVal.update(v => v + this.pageSize()); this.loadProductos(); }
  onPageSize(val: number): void { this.pageSize.set(val); this.skipVal.set(0); this.loadProductos(); }

  openDetails(p: Producto): void {
    this.selectedProduct.set(p);
    this.detailsModalOpen.set(true);
  }

  closeDetails(): void {
    this.detailsModalOpen.set(false);
    this.selectedProduct.set(null);
  }

  openPanel(p: Producto | null): void {
    this.editingId.set(p?.id ?? null);
    this.formDept.set(p?.id_departamento ?? null);
    this.formCat.set(p?.id_categoria ?? null);
    this.formSubcat.set(p?.id_subcategoria ?? null);
    this.formMarca.set(p?.id_marca ?? null);
    this.formPresentacion.set(p?.id_presentacion ?? null);
    this.formTamano.set(p?.id_clasificacion_tamano ?? null);
    this.form.reset({
      producto_gu: p?.producto_gu ?? '', cod_prod: p?.cod_prod ?? '',
      id_departamento: p?.id_departamento ?? null, id_categoria: p?.id_categoria ?? null, id_subcategoria: p?.id_subcategoria ?? null,
      id_marca: p?.id_marca ?? null, id_presentacion: p?.id_presentacion ?? null,
      id_clasificacion_tamano: p?.id_clasificacion_tamano ?? null,
      descripcion_bi: p?.descripcion_bi ?? '', gramos: p?.gramos ?? null,
      inagotable: p?.inagotable ?? false,
      comentario: p?.comentario ?? '',
    });
    this.panelOpen.set(true);
  }
  closePanel(): void {
    this.panelOpen.set(false);
  }

  saveProducto(): void {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    this.saving.set(true);
    const v = this.form.value;
    const payload = {
      producto_gu: v.producto_gu, cod_prod: v.cod_prod || null,
      descripcion_bi: v.descripcion_bi || null,
      gramos: v.gramos != null && v.gramos !== ('' as any) ? Number(v.gramos) : null,
      inagotable: v.inagotable === true,
      comentario: v.comentario || null,
      id_subcategoria: v.id_subcategoria ?? null, id_marca: v.id_marca ?? null, id_presentacion: v.id_presentacion ?? null,
      id_clasificacion_tamano: v.id_clasificacion_tamano ?? null,
    };
    const op = this.editingId() ? this.api.updateProducto(this.editingId()!, payload) : this.api.createProducto(payload);
    op.subscribe({
      next: () => { this.saving.set(false); this.closePanel(); this.loadProductos(); this.snack.open(this.editingId() ? 'Producto actualizado' : 'Producto creado', 'OK', { duration: 3000 }); },
      error: (err) => { this.saving.set(false); this.snack.open(err?.error?.detail ?? 'Error al guardar', 'OK', { duration: 4000 }); },
    });
  }

  deleteProducto(p: Producto): void {
    this.confirmSvc.confirm(`¿Estás seguro de eliminar el producto "${p.producto_gu}"? Esta acción no se puede deshacer.`, {
      title: 'Eliminar Producto',
      confirmText: 'Eliminar',
      danger: true
    }).then(ok => {
      if (!ok) return;
      this.api.deleteProducto(p.id).subscribe({
        next: () => { this.loadProductos(); this.snack.open('Producto eliminado', 'OK', { duration: 3000 }); },
        error: (err) => this.snack.open('Error al eliminar: ' + (err.error?.detail || err.message), 'OK', { duration: 3000 })
      });
    });
  }

  // ── Catálogos (ABM) ──
  openCatalogPanel(): void { this.catalogPanelOpen.set(true); this.loadCatalogs(); }
  closeCatalogPanel(): void { this.catalogPanelOpen.set(false); }
  currentTab() { return this.tabs.find(t => t.key === this.catTab())!; }
  setTab(k: CatTab): void { this.catTab.set(k); this.newName = ''; this.newParent = null; }
  needsParent(): boolean { return this.catTab() === 'categorias' || this.catTab() === 'subcategorias'; }

  private depName(id?: number): string { return this.departamentosList().find(d => d.id === id)?.nombre || ''; }
  private catName(id?: number): string { return this.catList().find(c => c.id_categoria === id)?.nombre || ''; }

  currentCatList(): { id: number; nombre: string; extra?: string }[] {
    switch (this.catTab()) {
      case 'departamentos': return this.departamentosList().map(d => ({ id: d.id, nombre: d.nombre }));
      case 'categorias': return this.catList().map(c => ({ id: c.id_categoria, nombre: c.nombre, extra: this.depName(c.id_departamento) }));
      case 'subcategorias': return this.subcatList().map(s => ({ id: s.id_subcategoria, nombre: s.nombre, extra: this.catName(s.id_categoria) }));
      case 'marcas': return this.marcasList().map(m => ({ id: m.id, nombre: m.nombre }));
      case 'presentaciones': return this.presentacionesList().map(p => ({ id: p.id, nombre: p.nombre }));
      case 'tamanos': return this.tamanosList().map(t => ({ id: t.id, nombre: t.nombre }));
    }
    return [];
  }

  addCatItem(): void {
    const nombre = this.newName.trim();
    if (!nombre) return;
    const p = this.newParent;
    let obs;
    switch (this.catTab()) {
      case 'departamentos': obs = this.api.createCatDepartamento({ nombre }); break;
      case 'categorias': obs = this.api.createCatalogosCategoria({ nombre, id_departamento: p }); break;
      case 'subcategorias': obs = this.api.createCatalogosSubCategoria({ nombre, id_categoria: p }); break;
      case 'marcas': obs = this.api.createCatMarca({ nombre, id_productora: p }); break;
      case 'presentaciones': obs = this.api.createCatPresentacion({ nombre }); break;
      case 'tamanos': obs = this.api.createCatTamano({ nombre }); break;
      default: return;
    }
    obs.subscribe({ next: () => { this.newName = ''; this.newParent = null; this.loadCatalogs(); this.snack.open('Agregado', 'OK', { duration: 2000 }); }, error: (e) => this.snack.open(e?.error?.detail ?? 'Error al agregar', 'OK', { duration: 4000 }) });
  }

  delCatItem(id: number, force: boolean = false): void {
    const doDelete = () => {
      let obs;
      switch (this.catTab()) {
        case 'departamentos': obs = this.api.deleteCatDepartamento(id, force); break;
        case 'categorias': obs = this.api.deleteCatalogosCategoria(id, force); break;
        case 'subcategorias': obs = this.api.deleteCatalogosSubCategoria(id, force); break;
        case 'marcas': obs = this.api.deleteCatMarca(id, force); break;
        case 'presentaciones': obs = this.api.deleteCatPresentacion(id, force); break;
        case 'tamanos': obs = this.api.deleteCatTamano(id, force); break;
        default: return;
      }
      obs.subscribe({
        next: () => { this.loadCatalogs(); this.snack.open('Eliminado', 'OK', { duration: 2000 }); },
        error: (err) => {
          if (err.status === 409 && !force) {
            const detail = err.error?.detail;
            const msg = typeof detail === 'string' ? detail : (detail?.message || 'Este elemento está siendo utilizado por otros registros.');
            this.confirmSvc.confirm(`${msg}\n\n¿Deseas forzar la eliminación de todos modos?`, {
              title: 'Elemento en Uso - Conflicto',
              confirmText: 'Forzar Eliminación',
              danger: true
            }).then(forceOk => {
              if (forceOk) {
                this.delCatItem(id, true);
              }
            });
          } else {
            const errorMsg = typeof err.error?.detail === 'string' ? err.error.detail : (err.error?.detail?.message || err.message);
            this.snack.open('Error al eliminar: ' + errorMsg, 'OK', { duration: 4000 });
          }
        }
      });
    };

    if (!force) {
      this.confirmSvc.confirm('¿Deseas eliminar este elemento del catálogo?', {
        title: 'Eliminar ítem del catálogo',
        confirmText: 'Eliminar',
        danger: true
      }).then(ok => {
        if (ok) doDelete();
      });
    } else {
      doDelete();
    }
  }
}
