import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators, FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Subject, debounceTime, distinctUntilChanged } from 'rxjs';
import { ApiService } from '../../core/services/api.service';
import { HasPermDirective } from '../../core/directives/has-perm.directive';

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
  imports: [CommonModule, ReactiveFormsModule, FormsModule, MatIconModule, MatSnackBarModule, MatProgressSpinnerModule, MatTooltipModule, HasPermDirective],
  template: `
<div class="min-h-screen bg-slate-950 text-white">

  <!-- HEADER -->
  <div class="bg-gradient-to-r from-slate-900 via-slate-900 to-slate-800 border-b border-white/8 px-8 py-6">
    <div class="flex items-center justify-between gap-4 flex-wrap">
      <div class="flex items-center gap-4">
        <div class="w-12 h-12 rounded-2xl bg-gradient-to-br from-violet-600 to-purple-700 flex items-center justify-center shadow-lg shrink-0">
          <mat-icon class="text-white !text-2xl">inventory_2</mat-icon>
        </div>
        <div>
          <h1 class="text-2xl font-black tracking-tight text-white leading-none">Productos</h1>
          <p class="text-slate-400 text-sm mt-0.5"><span class="font-bold text-violet-400">{{ total() }}</span> productos en catálogo</p>
        </div>
      </div>
      <div class="flex items-center gap-3">
        <button *hasPerm="'products'; action:'write'" (click)="openCatalogPanel()" class="flex items-center gap-2 px-5 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold rounded-xl shadow-sm transition-all active:scale-95 text-sm border border-slate-700">
          <mat-icon class="!text-base">tune</mat-icon> Catálogos
        </button>
        <button *hasPerm="'products'; action:'write'" (click)="openPanel(null)" class="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-violet-700 to-purple-700 hover:from-violet-600 hover:to-purple-600 text-white font-black rounded-xl shadow-lg transition-all active:scale-95 text-sm">
          <mat-icon class="!text-base">add</mat-icon> Nuevo Producto
        </button>
      </div>
    </div>

    <!-- SEARCH + FILTERS -->
    <div class="flex flex-wrap gap-3 mt-5">
      <div class="relative flex-1 min-w-52">
        <mat-icon class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none !text-base">search</mat-icon>
        <input [ngModel]="searchText()" (ngModelChange)="onSearch($event)" placeholder="Buscar por nombre o código..."
          class="w-full bg-slate-800 border border-slate-700 focus:border-violet-500 text-white placeholder-slate-500 rounded-xl pl-9 pr-4 py-2.5 text-sm font-semibold outline-none transition-colors">
      </div>
      <div class="relative">
        <select [ngModel]="filterCategoria()" (ngModelChange)="filterCategoria.set($event); reload()"
          class="bg-slate-800 border border-slate-700 focus:border-violet-500 text-white rounded-xl px-3 py-2.5 pr-8 text-sm font-semibold appearance-none outline-none min-w-36">
          <option [ngValue]="null">Todas las categorías</option>
          @for (c of catList(); track c.id_categoria) { <option [ngValue]="c.id_categoria">{{ c.nombre }}</option> }
        </select>
        <mat-icon class="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none !text-base">expand_more</mat-icon>
      </div>
      <div class="relative">
        <select [ngModel]="filterMarca()" (ngModelChange)="filterMarca.set($event); reload()"
          class="bg-slate-800 border border-slate-700 focus:border-violet-500 text-white rounded-xl px-3 py-2.5 pr-8 text-sm font-semibold appearance-none outline-none min-w-36">
          <option [ngValue]="null">Todas las marcas</option>
          @for (m of marcasList(); track m.id) { <option [ngValue]="m.id">{{ m.nombre }}</option> }
        </select>
        <mat-icon class="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none !text-base">expand_more</mat-icon>
      </div>
      @if (searchText() || filterCategoria() || filterMarca()) {
        <button (click)="clearFilters()" class="flex items-center gap-1.5 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-400 hover:text-white rounded-xl text-sm font-bold transition-all">
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
      <div class="flex flex-col items-center justify-center py-32 gap-4 text-slate-600">
        <div class="w-20 h-20 rounded-3xl bg-slate-800 flex items-center justify-center"><mat-icon class="!text-4xl">inventory_2</mat-icon></div>
        <p class="font-bold text-lg tracking-tight">No se encontraron productos</p>
      </div>
    } @else {
      <div class="bg-slate-900 border border-white/8 rounded-2xl overflow-hidden overflow-x-auto">
        <div class="grid grid-cols-[1.7fr_1fr_1fr_1.1fr_1.1fr_1fr_1fr_0.9fr_0.7fr_56px] gap-3 px-5 py-3 bg-slate-800 border-b border-white/8 text-[10px] font-black text-slate-500 uppercase tracking-widest min-w-[1380px]">
          <span>Producto</span><span>Cód. Barras</span><span>Departamento</span><span>Categoría</span><span>Subcategoría</span><span>Marca</span><span>Presentación</span><span>Tamaño</span><span>Inagotable</span><span></span>
        </div>
        @for (p of productos(); track p.id) {
          <div class="grid grid-cols-[1.7fr_1fr_1fr_1.1fr_1.1fr_1fr_1fr_0.9fr_0.7fr_56px] gap-3 items-center px-5 py-3.5 border-b border-white/5 hover:bg-slate-800 transition-colors group min-w-[1380px]">
            <div class="flex items-center gap-3 min-w-0">
              <div class="w-9 h-9 rounded-xl bg-violet-900 flex items-center justify-center shrink-0"><mat-icon class="!text-base text-violet-400">inventory_2</mat-icon></div>
              <p class="font-bold text-white text-sm truncate">{{ p.producto_gu || '—' }}</p>
            </div>
            <span class="text-xs font-mono text-slate-400 truncate">{{ p.cod_prod || '—' }}</span>
            <span class="text-sm text-slate-400 truncate">{{ p.departamento || '—' }}</span>
            <span class="text-sm text-slate-400 truncate">{{ p.categoria || '—' }}</span>
            <span class="text-sm text-slate-400 truncate">{{ p.subcategoria || '—' }}</span>
            <span class="text-sm text-slate-400 truncate">{{ p.marca || '—' }}</span>
            <span class="text-sm text-slate-400 truncate">{{ p.presentacion || '—' }}</span>
            <span class="text-sm text-slate-400 truncate">{{ p.tamano || '—' }}</span>
            <span class="flex items-center">
              @if (p.inagotable) {
                <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-900/60 text-emerald-400 text-[10px] font-black">
                  <mat-icon class="!text-[11px]">all_inclusive</mat-icon> Sí
                </span>
              } @else {
                <span class="text-slate-600 text-xs">No</span>
              }
            </span>
            <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button *hasPerm="'products'; action:'write'" (click)="openPanel(p)" matTooltip="Editar" class="w-8 h-8 rounded-lg bg-violet-900 hover:bg-violet-800 text-violet-400 flex items-center justify-center"><mat-icon class="!text-base">edit</mat-icon></button>
              <button *hasPerm="'products'; action:'delete'" (click)="deleteProducto(p)" matTooltip="Eliminar" class="w-8 h-8 rounded-lg bg-red-950 hover:bg-red-900 text-red-400 flex items-center justify-center"><mat-icon class="!text-base">delete</mat-icon></button>
            </div>
          </div>
        }
      </div>

      <div class="flex items-center justify-between mt-5">
        <p class="text-sm text-slate-500">Mostrando <span class="text-white font-bold">{{ skipVal() + 1 }}–{{ skipVal() + productos().length }}</span> de <span class="text-white font-bold">{{ total() }}</span></p>
        <div class="flex gap-2">
          <button (click)="prevPage()" [disabled]="skipVal() === 0" class="flex items-center gap-1 px-4 py-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 border border-slate-700 text-white rounded-xl text-sm font-bold"><mat-icon class="!text-base">chevron_left</mat-icon> Anterior</button>
          <button (click)="nextPage()" [disabled]="skipVal() + pageSize >= total()" class="flex items-center gap-1 px-4 py-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 border border-slate-700 text-white rounded-xl text-sm font-bold">Siguiente <mat-icon class="!text-base">chevron_right</mat-icon></button>
        </div>
      </div>
    }
  </div>
</div>

<!-- SLIDE PANEL: PRODUCTO -->
@if (panelOpen()) {
  <div class="fixed inset-0 z-50 flex justify-end">
    <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" (click)="closePanel()"></div>
    <div class="relative w-full max-w-md bg-slate-900 border-l border-white/8 h-full flex flex-col shadow-2xl">
      <div class="bg-gradient-to-r from-slate-800 to-slate-900 border-b border-white/8 px-6 py-5 shrink-0 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-violet-900 flex items-center justify-center"><mat-icon class="text-violet-400 !text-xl">{{ editingId() ? 'edit' : 'add_circle' }}</mat-icon></div>
          <div><h3 class="font-black text-white">{{ editingId() ? 'Editar Producto' : 'Nuevo Producto' }}</h3><p class="text-xs text-slate-500">{{ editingId() ? 'Modifica los datos' : 'Agrega al catálogo' }}</p></div>
        </div>
        <button (click)="closePanel()" class="w-9 h-9 rounded-xl bg-white/5 hover:bg-white/10 flex items-center justify-center text-slate-400 hover:text-white"><mat-icon class="!text-lg">close</mat-icon></button>
      </div>

      <form [formGroup]="form" class="flex-1 px-6 py-6 space-y-5 overflow-y-auto">
        <div class="space-y-1.5">
          <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Nombre del producto *</label>
          <input formControlName="producto_gu" placeholder="Nombre del producto" class="w-full bg-slate-800 border border-slate-700 focus:border-violet-500 rounded-xl px-4 py-2.5 text-sm font-semibold text-white placeholder-slate-500 outline-none" [class.border-red-600]="form.get('producto_gu')?.invalid && form.get('producto_gu')?.touched">
          @if (form.get('producto_gu')?.invalid && form.get('producto_gu')?.touched) { <p class="text-xs text-red-400">El nombre es requerido</p> }
        </div>
        <div class="space-y-1.5">
          <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Código de barras / SKU</label>
          <input formControlName="cod_prod" placeholder="Ej: 7501234567890" class="w-full bg-slate-800 border border-slate-700 focus:border-violet-500 rounded-xl px-4 py-2.5 text-sm font-semibold font-mono text-white placeholder-slate-500 outline-none">
        </div>

        <!-- Departamento -> Categoría -> Subcategoría (cascada) -->
        <div class="space-y-1.5">
          <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Departamento</label>
          <select formControlName="id_departamento" (change)="onDepartamentoChange()" class="w-full bg-slate-800 border border-slate-700 focus:border-violet-500 rounded-xl px-3 py-2.5 text-sm font-semibold text-white outline-none">
            <option [ngValue]="null">— Selecciona —</option>
            @for (d of departamentosList(); track d.id) { <option [ngValue]="d.id">{{ d.nombre }}</option> }
          </select>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-1.5">
            <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Categoría</label>
            <select formControlName="id_categoria" (change)="onCategoriaChange()" class="w-full bg-slate-800 border border-slate-700 focus:border-violet-500 rounded-xl px-3 py-2.5 text-sm font-semibold text-white outline-none">
              <option [ngValue]="null">— Selecciona —</option>
              @for (c of catsFiltradas(); track c.id_categoria) { <option [ngValue]="c.id_categoria">{{ c.nombre }}</option> }
            </select>
          </div>
          <div class="space-y-1.5">
            <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Subcategoría</label>
            <select formControlName="id_subcategoria" class="w-full bg-slate-800 border border-slate-700 focus:border-violet-500 rounded-xl px-3 py-2.5 text-sm font-semibold text-white outline-none">
              <option [ngValue]="null">— Selecciona —</option>
              @for (s of subcatsFiltradas(); track s.id_subcategoria) { <option [ngValue]="s.id_subcategoria">{{ s.nombre }}</option> }
            </select>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-1.5">
            <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Marca / Fabricante</label>
            <select formControlName="id_marca" class="w-full bg-slate-800 border border-slate-700 focus:border-violet-500 rounded-xl px-3 py-2.5 text-sm font-semibold text-white outline-none">
              <option [ngValue]="null">— Selecciona —</option>
              @for (m of marcasList(); track m.id) { <option [ngValue]="m.id">{{ m.nombre }}</option> }
            </select>
          </div>
          <div class="space-y-1.5">
            <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Presentación</label>
            <select formControlName="id_presentacion" class="w-full bg-slate-800 border border-slate-700 focus:border-violet-500 rounded-xl px-3 py-2.5 text-sm font-semibold text-white outline-none">
              <option [ngValue]="null">— Selecciona —</option>
              @for (pr of presentacionesList(); track pr.id) { <option [ngValue]="pr.id">{{ pr.nombre }}</option> }
            </select>
          </div>
        </div>

        <div class="space-y-1.5">
          <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Tamaño</label>
          <select formControlName="id_clasificacion_tamano" class="w-full bg-slate-800 border border-slate-700 focus:border-violet-500 rounded-xl px-3 py-2.5 text-sm font-semibold text-white outline-none">
            <option [ngValue]="null">— Selecciona —</option>
            @for (t of tamanosList(); track t.id) { <option [ngValue]="t.id">{{ t.nombre }}</option> }
          </select>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-1.5">
            <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Descripción BI</label>
            <input formControlName="descripcion_bi" placeholder="Descripción" class="w-full bg-slate-800 border border-slate-700 focus:border-violet-500 rounded-xl px-4 py-2.5 text-sm font-semibold text-white placeholder-slate-500 outline-none">
          </div>
          <div class="space-y-1.5">
            <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Gramos</label>
            <input formControlName="gramos" type="number" placeholder="0" class="w-full bg-slate-800 border border-slate-700 focus:border-violet-500 rounded-xl px-4 py-2.5 text-sm font-semibold text-white placeholder-slate-500 outline-none">
          </div>
        </div>
        <div class="space-y-1.5">
          <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Inagotable</label>
          <label class="flex items-center gap-3 cursor-pointer">
            <input type="checkbox" formControlName="inagotable" class="sr-only peer">
            <div class="relative w-11 h-6 bg-slate-700 peer-checked:bg-emerald-600 rounded-full transition-colors">
              <div class="absolute left-1 top-1 w-4 h-4 bg-white rounded-full shadow transition-transform peer-checked:translate-x-5 translate-x-0"></div>
            </div>
            <span class="text-sm text-slate-300 font-semibold peer-checked:text-emerald-400">{{ form.get('inagotable')?.value ? 'Sí — el producto nunca se agota' : 'No — stock normal' }}</span>
          </label>
        </div>
        <div class="space-y-1.5">
          <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Comentario</label>
          <textarea formControlName="comentario" rows="2" placeholder="Notas (opcional)" class="w-full bg-slate-800 border border-slate-700 focus:border-violet-500 rounded-xl px-4 py-2.5 text-sm font-semibold text-white placeholder-slate-500 outline-none resize-none"></textarea>
        </div>
      </form>

      <div class="px-6 py-5 border-t border-white/8 bg-slate-900 shrink-0 flex gap-3">
        <button type="button" (click)="closePanel()" class="flex-1 py-2.5 border border-slate-700 text-slate-400 hover:text-white rounded-xl font-bold text-sm">Cancelar</button>
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
    <div class="relative w-full max-w-lg bg-slate-900 border-l border-white/8 h-full flex flex-col shadow-2xl">
      <div class="bg-gradient-to-r from-slate-800 to-slate-900 border-b border-white/8 px-6 py-5 shrink-0 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-violet-900 flex items-center justify-center"><mat-icon class="text-violet-400 !text-xl">tune</mat-icon></div>
          <div><h3 class="font-black text-white">Catálogos (Snowflake)</h3><p class="text-xs text-slate-500">Departamentos → Categorías → Subcategorías · Marcas · Presentaciones · Tamaños</p></div>
        </div>
        <button (click)="closeCatalogPanel()" class="w-9 h-9 rounded-xl bg-white/5 hover:bg-white/10 flex items-center justify-center text-slate-400 hover:text-white"><mat-icon class="!text-lg">close</mat-icon></button>
      </div>

      <!-- Tabs -->
      <div class="px-4 pt-4 shrink-0">
        <div class="flex gap-1 bg-slate-800 rounded-xl p-1 overflow-x-auto">
          @for (t of tabs; track t.key) {
            <button (click)="setTab(t.key)" [ngClass]="catTab() === t.key ? 'bg-violet-600 text-white' : 'text-slate-400 hover:text-white'" class="flex-1 px-3 py-1.5 rounded-lg text-xs font-bold whitespace-nowrap transition-all">{{ t.label }}</button>
          }
        </div>
      </div>

      <!-- Add row -->
      <div class="px-4 pt-4 shrink-0">
        <div class="bg-slate-800 rounded-2xl p-4 border border-slate-700 space-y-3">
          <h4 class="text-sm font-bold text-white">Agregar {{ currentTab().singular }}</h4>
          <div class="flex flex-wrap gap-2">
            <input [(ngModel)]="newName" [placeholder]="'Nombre de ' + currentTab().singular.toLowerCase()" class="flex-1 min-w-40 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white outline-none focus:border-violet-500">
            @if (catTab() === 'categorias') {
              <select [(ngModel)]="newParent" class="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white outline-none focus:border-violet-500">
                <option [ngValue]="null">Departamento…</option>
                @for (d of departamentosList(); track d.id) { <option [ngValue]="d.id">{{ d.nombre }}</option> }
              </select>
            }
            @if (catTab() === 'subcategorias') {
              <select [(ngModel)]="newParent" class="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white outline-none focus:border-violet-500">
                <option [ngValue]="null">Categoría…</option>
                @for (c of catList(); track c.id_categoria) { <option [ngValue]="c.id_categoria">{{ c.nombre }}</option> }
              </select>
            }
            @if (catTab() === 'marcas') {
              <select [(ngModel)]="newParent" class="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white outline-none focus:border-violet-500">
                <option [ngValue]="null">Productora (opcional)…</option>
                @for (pr of productorasList(); track pr.id) { <option [ngValue]="pr.id">{{ pr.nombre }}</option> }
              </select>
            }
            <button (click)="addCatItem()" [disabled]="!newName || (needsParent() && !newParent)" class="px-4 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-sm font-bold disabled:opacity-50">Agregar</button>
          </div>
        </div>
      </div>

      <!-- List -->
      <div class="flex-1 overflow-y-auto p-4 space-y-2">
        @for (it of currentCatList(); track it.id) {
          <div class="flex items-center justify-between bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5">
            <div class="min-w-0">
              <span class="font-bold text-sm text-white">{{ it.nombre }}</span>
              @if (it.extra) { <span class="text-xs text-slate-500 ml-2">({{ it.extra }})</span> }
            </div>
            <button (click)="delCatItem(it.id)" class="text-red-400 hover:text-red-300"><mat-icon class="!text-lg">delete</mat-icon></button>
          </div>
        }
        @if (currentCatList().length === 0) { <p class="text-center text-slate-600 text-sm py-8">Sin elementos</p> }
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
  filterCategoria = signal<number | null>(null);
  filterMarca = signal<number | null>(null);
  skipVal = signal(0);
  pageSize = 25;
  private search$ = new Subject<string>();

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

  constructor(private api: ApiService, private fb: FormBuilder, private snack: MatSnackBar) {}

  ngOnInit(): void {
    this.loadProductos();
    this.loadCatalogs();
    this.search$.pipe(debounceTime(350), distinctUntilChanged()).subscribe(() => { this.skipVal.set(0); this.loadProductos(); });
  }

  loadProductos(): void {
    this.loading.set(true);
    this.api.getProductos({ skip: this.skipVal(), limit: this.pageSize, busqueda: this.searchText() || undefined, id_categoria: this.filterCategoria() ?? undefined, id_marca: this.filterMarca() ?? undefined })
      .subscribe({ next: (res) => { this.productos.set(res.items); this.total.set(res.total); this.loading.set(false); }, error: () => this.loading.set(false) });
  }

  loadCatalogs(): void {
    this.api.getCatalogosCategorias().subscribe({ next: d => this.catList.set(d), error: () => {} });
    this.api.getCatalogosSubCategorias().subscribe({ next: d => this.subcatList.set(d), error: () => {} });
    this.api.getCatMarcas().subscribe({ next: d => this.marcasList.set(d), error: () => {} });
    this.api.getCatPresentaciones().subscribe({ next: d => this.presentacionesList.set(d), error: () => {} });
    this.api.getCatDepartamentos().subscribe({ next: d => this.departamentosList.set(d), error: () => {} });
    this.api.getCatProductoras().subscribe({ next: d => this.productorasList.set(d), error: () => {} });
    this.api.getCatTamanos().subscribe({ next: d => this.tamanosList.set(d), error: () => {} });
  }

  catsFiltradas(): Cat[] {
    const idd = this.form.get('id_departamento')?.value;
    return idd ? this.catList().filter(c => c.id_departamento === idd) : this.catList();
  }
  subcatsFiltradas(): SubCat[] {
    const idc = this.form.get('id_categoria')?.value;
    return idc ? this.subcatList().filter(s => s.id_categoria === idc) : this.subcatList();
  }
  onDepartamentoChange(): void { this.form.patchValue({ id_categoria: null, id_subcategoria: null }); }
  onCategoriaChange(): void { this.form.patchValue({ id_subcategoria: null }); }

  onSearch(val: string): void { this.searchText.set(val); this.search$.next(val); }
  reload(): void { this.skipVal.set(0); this.loadProductos(); }
  clearFilters(): void { this.searchText.set(''); this.filterCategoria.set(null); this.filterMarca.set(null); this.skipVal.set(0); this.loadProductos(); }
  prevPage(): void { this.skipVal.update(v => Math.max(0, v - this.pageSize)); this.loadProductos(); }
  nextPage(): void { this.skipVal.update(v => v + this.pageSize); this.loadProductos(); }

  openPanel(p: Producto | null): void {
    this.editingId.set(p?.id ?? null);
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
  closePanel(): void { this.panelOpen.set(false); }

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
    if (!confirm(`¿Eliminar "${p.producto_gu}"?`)) return;
    this.api.deleteProducto(p.id).subscribe({ next: () => { this.loadProductos(); this.snack.open('Producto eliminado', 'OK', { duration: 3000 }); }, error: () => this.snack.open('Error al eliminar', 'OK', { duration: 3000 }) });
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

  delCatItem(id: number): void {
    if (!confirm('¿Eliminar este elemento del catálogo?')) return;
    let obs;
    switch (this.catTab()) {
      case 'departamentos': obs = this.api.deleteCatDepartamento(id); break;
      case 'categorias': obs = this.api.deleteCatalogosCategoria(id); break;
      case 'subcategorias': obs = this.api.deleteCatalogosSubCategoria(id); break;
      case 'marcas': obs = this.api.deleteCatMarca(id); break;
      case 'presentaciones': obs = this.api.deleteCatPresentacion(id); break;
      case 'tamanos': obs = this.api.deleteCatTamano(id); break;
      default: return;
    }
    obs.subscribe({ next: () => { this.loadCatalogs(); this.snack.open('Eliminado', 'OK', { duration: 2000 }); }, error: (e) => this.snack.open(e?.error?.detail ?? 'Error al eliminar', 'OK', { duration: 4000 }) });
  }
}
