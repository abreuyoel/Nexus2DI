import { Component, OnInit, OnDestroy, computed, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Subject, Subscription, debounceTime, distinctUntilChanged } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';

interface Producto {
  id: number; producto_gu: string; cod_prod?: string; descripcion_bi?: string;
  gramos?: number; inagotable?: boolean; comentario?: string;
  id_subcategoria?: number; subcategoria?: string;
  id_categoria?: number; categoria?: string;
  id_departamento?: number; departamento?: string;
  id_marca?: number; marca?: string; fabricante?: string;
  id_presentacion?: number; presentacion?: string;
  id_clasificacion_tamano?: number; tamano?: string;
}
interface Cat    { id_categoria: number; nombre: string; id_departamento?: number; }
interface SubCat { id_subcategoria: number; nombre: string; id_categoria: number; }
interface Simple { id: number; nombre: string; id_productora?: number; }
type CatTab = 'departamentos' | 'categorias' | 'subcategorias' | 'marcas' | 'presentaciones' | 'tamanos';

@Component({
  selector: 'app-productos',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule,
    MatIconModule, MatSnackBarModule, MatProgressSpinnerModule, MatTooltipModule],
  template: `
<div class="min-h-screen bg-white dark:bg-slate-950 text-slate-900 dark:text-white">

  <!-- ══ HEADER ══ -->
  <div class="bg-gradient-to-r from-slate-50 to-white dark:from-slate-900 dark:to-slate-800 border-b border-slate-200 dark:border-white/8 px-8 py-6">
    <div class="flex items-center justify-between gap-4 flex-wrap">
      <div class="flex items-center gap-4">
        <div class="w-12 h-12 rounded-2xl bg-gradient-to-br from-violet-600 to-purple-700 flex items-center justify-center shadow-lg shrink-0">
          <mat-icon class="text-white !text-2xl">inventory_2</mat-icon>
        </div>
        <div>
          <h1 class="text-2xl font-black tracking-tight leading-none">Productos</h1>
          <p class="text-slate-500 text-sm mt-0.5"><span class="font-bold text-violet-400">{{ total() }}</span> productos en catálogo</p>
        </div>
      </div>
      <div class="flex items-center gap-3">
        <button (click)="openCatalog()"
          class="flex items-center gap-2 px-5 py-2.5 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 font-bold rounded-xl text-sm transition-all">
          <mat-icon class="!text-base">tune</mat-icon> Catálogos
        </button>
        <button (click)="openPanel(null)"
          class="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-violet-700 to-purple-700 hover:from-violet-600 hover:to-purple-600 text-white font-black rounded-xl shadow-lg transition-all active:scale-95 text-sm">
          <mat-icon class="!text-base">add</mat-icon> Nuevo Producto
        </button>
      </div>
    </div>

    <!-- Filtros -->
    <div class="flex flex-wrap gap-3 mt-5">
      <div class="relative flex-1 min-w-52">
        <mat-icon class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none !text-base">search</mat-icon>
        <input [ngModel]="searchText()" (ngModelChange)="onSearch($event)" placeholder="Buscar por nombre o código..."
          class="w-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-violet-500 text-slate-900 dark:text-white placeholder-slate-400 rounded-xl pl-9 pr-4 py-2.5 text-sm font-semibold outline-none transition-colors">
      </div>
      <div class="relative">
        <select [ngModel]="filterCat()" (ngModelChange)="filterCat.set($event); reload()"
          class="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-violet-500 text-slate-900 dark:text-white rounded-xl px-3 py-2.5 pr-8 text-sm font-semibold appearance-none outline-none min-w-44">
          <option [ngValue]="null">Todas las categorías</option>
          @for (c of catList(); track c.id_categoria) { <option [ngValue]="c.id_categoria">{{ c.nombre }}</option> }
        </select>
        <mat-icon class="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none !text-base">expand_more</mat-icon>
      </div>
      <div class="relative">
        <select [ngModel]="filterMarca()" (ngModelChange)="filterMarca.set($event); reload()"
          class="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-violet-500 text-slate-900 dark:text-white rounded-xl px-3 py-2.5 pr-8 text-sm font-semibold appearance-none outline-none min-w-44">
          <option [ngValue]="null">Todas las marcas</option>
          @for (m of marcasList(); track m.id) { <option [ngValue]="m.id">{{ m.nombre }}</option> }
        </select>
        <mat-icon class="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none !text-base">expand_more</mat-icon>
      </div>
      @if (searchText() || filterCat() || filterMarca()) {
        <button (click)="clearFilters()"
          class="flex items-center gap-1.5 px-4 py-2.5 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-700 text-slate-500 hover:text-slate-900 dark:hover:text-white rounded-xl text-sm font-bold transition-all">
          <mat-icon class="!text-base">close</mat-icon> Limpiar
        </button>
      }
    </div>
  </div>

  <!-- ══ TABLA ══ -->
  <div class="px-8 py-6">
    @if (loading()) {
      <div class="flex items-center justify-center py-32"><mat-spinner diameter="40"></mat-spinner></div>
    } @else if (productos().length === 0) {
      <div class="flex flex-col items-center justify-center py-32 gap-4 text-slate-400 dark:text-slate-600">
        <div class="w-20 h-20 rounded-3xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center"><mat-icon class="!text-4xl">inventory_2</mat-icon></div>
        <p class="font-bold text-lg">No se encontraron productos</p>
      </div>
    } @else {
      <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/8 rounded-2xl overflow-hidden overflow-x-auto">
        <div class="grid grid-cols-[2fr_1fr_1fr_1fr_1fr_1fr_1fr_0.7fr_0.6fr_76px] gap-3 px-5 py-3 bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-white/8 text-[10px] font-black text-slate-500 uppercase tracking-widest min-w-[1560px]">
          <span>Producto / Cód. Barras</span><span>Departamento</span><span>Categoría</span><span>Subcategoría</span>
          <span>Marca</span><span>Presentación</span><span>Tamaño</span><span>Gramos</span><span>Inagotable</span><span></span>
        </div>
        @for (p of productos(); track p.id) {
          <div class="grid grid-cols-[2fr_1fr_1fr_1fr_1fr_1fr_1fr_0.7fr_0.6fr_76px] gap-3 items-center px-5 py-3.5 border-b border-slate-100 dark:border-white/5 last:border-0 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors group min-w-[1560px]">
            <div class="flex items-center gap-3 min-w-0">
              <div class="w-9 h-9 rounded-xl bg-violet-100 dark:bg-violet-900 flex items-center justify-center shrink-0">
                <mat-icon class="!text-base text-violet-600 dark:text-violet-400">inventory_2</mat-icon>
              </div>
              <div class="min-w-0">
                <p class="font-bold text-sm truncate">{{ p.producto_gu || '—' }}</p>
                <span class="text-[10px] font-mono text-slate-400">{{ p.cod_prod || '—' }}</span>
              </div>
            </div>
            <span class="text-sm text-slate-500 dark:text-slate-400 truncate">{{ p.departamento || '—' }}</span>
            <span class="text-sm text-slate-500 dark:text-slate-400 truncate">{{ p.categoria || '—' }}</span>
            <span class="text-sm text-slate-500 dark:text-slate-400 truncate">{{ p.subcategoria || '—' }}</span>
            <span class="text-sm text-slate-500 dark:text-slate-400 truncate">{{ p.marca || '—' }}</span>
            <span class="text-sm text-slate-500 dark:text-slate-400 truncate">{{ p.presentacion || '—' }}</span>
            <span class="text-sm text-slate-500 dark:text-slate-400 truncate">{{ p.tamano || '—' }}</span>
            <span class="text-sm text-slate-500 dark:text-slate-400">{{ p.gramos != null ? p.gramos + ' g' : '—' }}</span>
            <span class="flex items-center">
              @if (p.inagotable) {
                <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-900/60 text-emerald-700 dark:text-emerald-400 text-[10px] font-black">
                  <mat-icon class="!text-[11px]">all_inclusive</mat-icon> Sí
                </span>
              } @else {
                <span class="text-slate-400 text-xs">No</span>
              }
            </span>
            <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button (click)="openPanel(p)" matTooltip="Editar" class="w-8 h-8 rounded-lg bg-violet-100 dark:bg-violet-900 hover:bg-violet-200 dark:hover:bg-violet-800 text-violet-600 dark:text-violet-400 flex items-center justify-center">
                <mat-icon class="!text-base">edit</mat-icon>
              </button>
              <button (click)="deleteProducto(p)" matTooltip="Eliminar" class="w-8 h-8 rounded-lg bg-rose-50 dark:bg-red-950 hover:bg-rose-100 dark:hover:bg-red-900 text-rose-600 dark:text-red-400 flex items-center justify-center">
                <mat-icon class="!text-base">delete</mat-icon>
              </button>
            </div>
          </div>
        }
      </div>

      <!-- Paginación -->
      <div class="flex items-center justify-between mt-5 flex-wrap gap-3">
        <div class="flex items-center gap-3">
          <p class="text-sm text-slate-500">Mostrando <span class="font-bold text-slate-900 dark:text-white">{{ skip() + 1 }}–{{ skip() + productos().length }}</span> de <span class="font-bold text-slate-900 dark:text-white">{{ total() }}</span></p>
          <div class="relative">
            <select [ngModel]="pageSize()" (ngModelChange)="onPageSizeChange($event)"
              class="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-violet-500 text-slate-900 dark:text-white rounded-xl px-3 py-1.5 pr-7 text-sm font-bold appearance-none outline-none">
              <option [value]="25">25 / pág</option><option [value]="50">50 / pág</option><option [value]="100">100 / pág</option>
            </select>
            <mat-icon class="absolute right-1.5 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none !text-base">expand_more</mat-icon>
          </div>
        </div>
        <div class="flex gap-2">
          <button (click)="prevPage()" [disabled]="skip() === 0" class="flex items-center gap-1 px-4 py-2 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 disabled:opacity-40 border border-slate-200 dark:border-slate-700 rounded-xl text-sm font-bold transition-all">
            <mat-icon class="!text-base">chevron_left</mat-icon> Anterior
          </button>
          <button (click)="nextPage()" [disabled]="skip() + pageSize() >= total()" class="flex items-center gap-1 px-4 py-2 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 disabled:opacity-40 border border-slate-200 dark:border-slate-700 rounded-xl text-sm font-bold transition-all">
            Siguiente <mat-icon class="!text-base">chevron_right</mat-icon>
          </button>
        </div>
      </div>
    }
  </div>
</div>

<!-- ══════════════════════════════════════
     PANEL: CREAR / EDITAR PRODUCTO
══════════════════════════════════════ -->
@if (panelOpen()) {
  <div class="fixed inset-0 z-50 flex justify-end">
    <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" (click)="closePanel()"></div>
    <div class="relative w-full max-w-md bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-white/8 h-full flex flex-col shadow-2xl">
      <div class="bg-gradient-to-r from-slate-50 to-white dark:from-slate-800 dark:to-slate-900 border-b border-slate-200 dark:border-white/8 px-6 py-5 shrink-0 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-violet-100 dark:bg-violet-900 flex items-center justify-center">
            <mat-icon class="text-violet-600 dark:text-violet-400 !text-xl">{{ editingId() ? 'edit' : 'add_circle' }}</mat-icon>
          </div>
          <div>
            <h3 class="font-black text-slate-900 dark:text-white">{{ editingId() ? 'Editar Producto' : 'Nuevo Producto' }}</h3>
            <p class="text-xs text-slate-500">{{ editingId() ? 'Modifica los datos' : 'Agrega al catálogo' }}</p>
          </div>
        </div>
        <button (click)="closePanel()" class="w-9 h-9 rounded-xl bg-slate-100 dark:bg-white/5 hover:bg-slate-200 dark:hover:bg-white/10 flex items-center justify-center text-slate-500 hover:text-slate-900 dark:hover:text-white transition-all">
          <mat-icon class="!text-lg">close</mat-icon>
        </button>
      </div>

      <div class="flex-1 overflow-y-auto px-6 py-6">
        <form [formGroup]="form" class="space-y-5">
          <!-- Nombre -->
          <div class="space-y-1.5">
            <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Nombre del producto *</label>
            <input formControlName="producto_gu" placeholder="Nombre del producto"
              class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-violet-500 rounded-xl px-4 py-2.5 text-sm font-semibold outline-none transition-colors"
              [class.border-red-500]="form.get('producto_gu')?.invalid && form.get('producto_gu')?.touched">
            @if (form.get('producto_gu')?.invalid && form.get('producto_gu')?.touched) {
              <p class="text-xs text-red-400">El nombre es requerido</p>
            }
          </div>
          <!-- Código barras -->
          <div class="space-y-1.5">
            <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Código de barras</label>
            <input formControlName="cod_prod" placeholder="Ej: 7501234567890"
              class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-violet-500 rounded-xl px-4 py-2.5 text-sm font-semibold font-mono outline-none transition-colors">
          </div>
          <!-- Departamento -->
          <div class="space-y-1.5">
            <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Departamento</label>
            <select formControlName="id_departamento" (change)="onDepChange()"
              class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-violet-500 rounded-xl px-3 py-2.5 text-sm font-semibold outline-none transition-colors">
              <option [ngValue]="null">— Selecciona —</option>
              @for (d of departamentosList(); track d.id) { <option [ngValue]="d.id">{{ d.nombre }}</option> }
            </select>
          </div>
          <!-- Categoría → Subcategoría (cascada reactiva) -->
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-1.5">
              <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Categoría</label>
              <select formControlName="id_categoria" (change)="onCatChange()"
                class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-violet-500 rounded-xl px-3 py-2.5 text-sm font-semibold outline-none transition-colors">
                <option [ngValue]="null">— Selecciona —</option>
                @for (c of catsFiltradas(); track c.id_categoria) { <option [ngValue]="c.id_categoria">{{ c.nombre }}</option> }
              </select>
            </div>
            <div class="space-y-1.5">
              <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Subcategoría</label>
              <select formControlName="id_subcategoria"
                class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-violet-500 rounded-xl px-3 py-2.5 text-sm font-semibold outline-none transition-colors">
                <option [ngValue]="null">— Selecciona —</option>
                @for (s of subcatsFiltradas(); track s.id_subcategoria) { <option [ngValue]="s.id_subcategoria">{{ s.nombre }}</option> }
              </select>
            </div>
          </div>
          <!-- Marca + Presentación -->
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-1.5">
              <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Marca</label>
              <select formControlName="id_marca"
                class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-violet-500 rounded-xl px-3 py-2.5 text-sm font-semibold outline-none transition-colors">
                <option [ngValue]="null">— Selecciona —</option>
                @for (m of marcasList(); track m.id) { <option [ngValue]="m.id">{{ m.nombre }}</option> }
              </select>
            </div>
            <div class="space-y-1.5">
              <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Presentación</label>
              <select formControlName="id_presentacion"
                class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-violet-500 rounded-xl px-3 py-2.5 text-sm font-semibold outline-none transition-colors">
                <option [ngValue]="null">— Selecciona —</option>
                @for (pr of presentacionesList(); track pr.id) { <option [ngValue]="pr.id">{{ pr.nombre }}</option> }
              </select>
            </div>
          </div>
          <!-- Tamaño -->
          <div class="space-y-1.5">
            <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Clasificación de Tamaño</label>
            <select formControlName="id_clasificacion_tamano"
              class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-violet-500 rounded-xl px-3 py-2.5 text-sm font-semibold outline-none transition-colors">
              <option [ngValue]="null">— Selecciona —</option>
              @for (t of tamanosList(); track t.id) { <option [ngValue]="t.id">{{ t.nombre }}</option> }
            </select>
          </div>
          <!-- Descripción BI + Gramos -->
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-1.5">
              <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Descripción BI</label>
              <input formControlName="descripcion_bi" placeholder="Descripción"
                class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-violet-500 rounded-xl px-4 py-2.5 text-sm font-semibold outline-none transition-colors">
            </div>
            <div class="space-y-1.5">
              <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Gramos</label>
              <input formControlName="gramos" type="number" placeholder="0"
                class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-violet-500 rounded-xl px-4 py-2.5 text-sm font-semibold outline-none transition-colors">
            </div>
          </div>
          <!-- Inagotable toggle -->
          <div class="space-y-1.5">
            <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Inagotable</label>
            <label class="flex items-center gap-3 cursor-pointer group/tog">
              <input type="checkbox" formControlName="inagotable" class="sr-only peer">
              <div class="relative w-11 h-6 bg-slate-200 dark:bg-slate-700 peer-checked:bg-emerald-500 rounded-full transition-colors shadow-inner">
                <div class="absolute left-1 top-1 w-4 h-4 bg-white rounded-full shadow transition-transform peer-checked:translate-x-5"></div>
              </div>
              <span class="text-sm font-semibold text-slate-600 dark:text-slate-300">
                {{ form.get('inagotable')?.value ? 'Sí — nunca se agota' : 'No — stock normal' }}
              </span>
            </label>
          </div>
          <!-- Comentario -->
          <div class="space-y-1.5">
            <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Comentario</label>
            <textarea formControlName="comentario" rows="3" placeholder="Notas opcionales..."
              class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-violet-500 rounded-xl px-4 py-2.5 text-sm font-semibold outline-none transition-colors resize-none"></textarea>
          </div>
        </form>
      </div>

      <div class="px-6 py-5 border-t border-slate-200 dark:border-white/8 shrink-0 flex gap-3">
        <button type="button" (click)="closePanel()" class="flex-1 py-2.5 border border-slate-300 dark:border-slate-700 text-slate-500 hover:text-slate-900 dark:hover:text-white rounded-xl font-bold text-sm transition-all">Cancelar</button>
        <button type="button" (click)="save()" [disabled]="form.invalid || saving()"
          class="flex-1 flex items-center justify-center gap-2 py-2.5 bg-gradient-to-r from-violet-700 to-purple-700 hover:from-violet-600 hover:to-purple-600 disabled:opacity-50 text-white font-black rounded-xl text-sm shadow-lg transition-all active:scale-95">
          @if (saving()) { <mat-spinner diameter="16"></mat-spinner> } @else { <mat-icon class="!text-base">{{ editingId() ? 'save' : 'add' }}</mat-icon> }
          {{ editingId() ? 'Guardar Cambios' : 'Crear Producto' }}
        </button>
      </div>
    </div>
  </div>
}

<!-- ══════════════════════════════════════
     PANEL CATÁLOGO — SNOWFLAKE CRUD
══════════════════════════════════════ -->
@if (catalogOpen()) {
  <div class="fixed inset-0 z-[60] flex justify-end">
    <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" (click)="closeCatalog()"></div>
    <div class="relative w-full max-w-lg bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-white/8 h-full flex flex-col shadow-2xl">

      <!-- Catalog header -->
      <div class="bg-gradient-to-r from-slate-50 to-white dark:from-slate-800 dark:to-slate-900 border-b border-slate-200 dark:border-white/8 px-6 py-5 shrink-0">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-xl bg-violet-100 dark:bg-violet-900 flex items-center justify-center">
              <mat-icon class="text-violet-600 dark:text-violet-400 !text-xl">tune</mat-icon>
            </div>
            <div>
              <h3 class="font-black text-slate-900 dark:text-white">Catálogos (Snowflake)</h3>
              <p class="text-[11px] text-slate-500">Crear · Modificar · Eliminar</p>
            </div>
          </div>
          <button (click)="closeCatalog()" class="w-9 h-9 rounded-xl bg-slate-100 dark:bg-white/5 hover:bg-slate-200 dark:hover:bg-white/10 flex items-center justify-center text-slate-500 hover:text-slate-900 dark:hover:text-white transition-all">
            <mat-icon class="!text-lg">close</mat-icon>
          </button>
        </div>
      </div>

      <!-- Tabs -->
      <div class="px-4 pt-4 shrink-0">
        <div class="flex gap-1 bg-slate-100 dark:bg-slate-800 rounded-xl p-1 overflow-x-auto">
          @for (t of tabs; track t.key) {
            <button (click)="setTab(t.key)"
              [class]="catTab() === t.key
                ? 'bg-violet-600 text-white shadow-sm'
                : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-white/60 dark:hover:bg-slate-700'"
              class="flex-1 px-2 py-1.5 rounded-lg text-xs font-bold whitespace-nowrap transition-all min-w-fit">
              {{ t.label }}
            </button>
          }
        </div>
      </div>

      <!-- Add new item -->
      <div class="px-4 pt-4 shrink-0">
        <div class="bg-slate-50 dark:bg-slate-800 rounded-2xl p-4 border border-slate-200 dark:border-slate-700 space-y-3">
          <h4 class="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <mat-icon class="!text-base text-violet-500">add_circle</mat-icon>
            Agregar {{ currentTabLabel() }}
          </h4>
          <div class="flex flex-col gap-2">
            <!-- Parent selector for Categorías -->
            @if (catTab() === 'categorias') {
              <div class="relative">
                <select [(ngModel)]="newParent" class="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm font-semibold outline-none focus:border-violet-500 transition-colors">
                  <option [ngValue]="null">Departamento (opcional)…</option>
                  @for (d of departamentosList(); track d.id) { <option [ngValue]="d.id">{{ d.nombre }}</option> }
                </select>
              </div>
            }
            <!-- Parent selector for Subcategorías -->
            @if (catTab() === 'subcategorias') {
              <div class="relative">
                <select [(ngModel)]="newParent" class="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm font-semibold outline-none focus:border-violet-500 transition-colors">
                  <option [ngValue]="null">Categoría (opcional)…</option>
                  @for (c of catList(); track c.id_categoria) { <option [ngValue]="c.id_categoria">{{ c.nombre }}</option> }
                </select>
              </div>
            }
            <!-- Parent selector for Marcas -->
            @if (catTab() === 'marcas') {
              <div class="relative">
                <select [(ngModel)]="newParent" class="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm font-semibold outline-none focus:border-violet-500 transition-colors">
                  <option [ngValue]="null">Productora (opcional)…</option>
                  @for (p of productorasList(); track p.id) { <option [ngValue]="p.id">{{ p.nombre }}</option> }
                </select>
              </div>
            }
            <div class="flex gap-2">
              <input [(ngModel)]="newName" [placeholder]="'Nombre de ' + currentTabLabel().toLowerCase()"
                (keyup.enter)="addItem()"
                class="flex-1 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm font-semibold outline-none focus:border-violet-500 transition-colors">
              <button (click)="addItem()" [disabled]="!newName.trim() || catSaving()"
                class="px-4 py-2 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white rounded-lg text-sm font-bold transition-all flex items-center gap-1">
                @if (catSaving()) { <mat-spinner diameter="14"></mat-spinner> } @else { <mat-icon class="!text-sm">add</mat-icon> }
                Agregar
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Filter inside catalog panel -->
      <div class="px-4 pt-3 shrink-0 space-y-2">
        <!-- Parent filter for Categorías list (filter by departamento) -->
        @if (catTab() === 'categorias') {
          <div class="relative">
            <select [ngModel]="catParentFilter()" (ngModelChange)="catParentFilter.set($event)"
              class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-sm font-semibold outline-none focus:border-violet-500 transition-colors appearance-none">
              <option [ngValue]="null">Todos los departamentos</option>
              @for (d of departamentosList(); track d.id) { <option [ngValue]="d.id">{{ d.nombre }}</option> }
            </select>
            <mat-icon class="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none !text-sm">expand_more</mat-icon>
          </div>
        }
        <!-- Parent filter for Subcategorías list (filter by categoría) -->
        @if (catTab() === 'subcategorias') {
          <div class="relative">
            <select [ngModel]="catParentFilter()" (ngModelChange)="catParentFilter.set($event)"
              class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-sm font-semibold outline-none focus:border-violet-500 transition-colors appearance-none">
              <option [ngValue]="null">Todas las categorías</option>
              @for (c of catList(); track c.id_categoria) { <option [ngValue]="c.id_categoria">{{ c.nombre }}</option> }
            </select>
            <mat-icon class="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none !text-sm">expand_more</mat-icon>
          </div>
        }
        <!-- Parent filter for Marcas list (filter by productora) -->
        @if (catTab() === 'marcas') {
          <div class="relative">
            <select [ngModel]="catParentFilter()" (ngModelChange)="catParentFilter.set($event)"
              class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-sm font-semibold outline-none focus:border-violet-500 transition-colors appearance-none">
              <option [ngValue]="null">Todas las productoras</option>
              @for (p of productorasList(); track p.id) { <option [ngValue]="p.id">{{ p.nombre }}</option> }
            </select>
            <mat-icon class="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none !text-sm">expand_more</mat-icon>
          </div>
        }
        <!-- Text search -->
        <div class="relative">
          <mat-icon class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none !text-sm">search</mat-icon>
          <input [ngModel]="catSearch()" (ngModelChange)="catSearch.set($event)" placeholder="Filtrar lista…"
            class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl pl-8 pr-4 py-2 text-sm font-semibold outline-none focus:border-violet-500 transition-colors">
        </div>
      </div>

      <!-- Items list -->
      <div class="flex-1 overflow-y-auto p-4 space-y-2">
        @if (catLoading()) {
          <div class="flex justify-center py-8"><mat-spinner diameter="32"></mat-spinner></div>
        } @else {
          @for (it of filteredCatItems(); track it.id) {
            <div class="flex items-center gap-3 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 group/item">
              @if (catEditId() === it.id) {
                <!-- Edit mode -->
                <div class="flex-1 flex gap-2 items-center">
                  <input [(ngModel)]="catEditName" (keyup.enter)="saveEdit(it.id)"
                    class="flex-1 bg-white dark:bg-slate-900 border border-violet-500 rounded-lg px-3 py-1.5 text-sm font-semibold outline-none">
                  <button (click)="saveEdit(it.id)" [disabled]="!catEditName.trim() || catSaving()"
                    class="p-1.5 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white transition-all">
                    <mat-icon class="!text-sm">check</mat-icon>
                  </button>
                  <button (click)="cancelEdit()"
                    class="p-1.5 rounded-lg bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 dark:hover:bg-slate-600 text-slate-600 dark:text-slate-400 transition-all">
                    <mat-icon class="!text-sm">close</mat-icon>
                  </button>
                </div>
              } @else {
                <!-- View mode -->
                <div class="flex-1 min-w-0">
                  <span class="font-bold text-sm text-slate-900 dark:text-white">{{ it.nombre }}</span>
                  @if (it.extra) {
                    <span class="text-xs text-slate-400 ml-2 truncate">↳ {{ it.extra }}</span>
                  }
                </div>
                <div class="flex items-center gap-1 opacity-0 group-hover/item:opacity-100 transition-opacity">
                  <button (click)="startEdit(it)" matTooltip="Editar"
                    class="w-7 h-7 rounded-lg bg-violet-100 dark:bg-violet-900 hover:bg-violet-200 dark:hover:bg-violet-800 text-violet-600 dark:text-violet-400 flex items-center justify-center transition-all">
                    <mat-icon class="!text-sm">edit</mat-icon>
                  </button>
                  <button (click)="deleteItem(it.id)" matTooltip="Eliminar"
                    class="w-7 h-7 rounded-lg bg-rose-50 dark:bg-red-950 hover:bg-rose-100 dark:hover:bg-red-900 text-rose-500 dark:text-red-400 flex items-center justify-center transition-all">
                    <mat-icon class="!text-sm">delete</mat-icon>
                  </button>
                </div>
              }
            </div>
          }
          @if (filteredCatItems().length === 0) {
            <div class="text-center text-slate-400 text-sm py-10 flex flex-col items-center gap-2">
              <mat-icon class="!text-3xl">inbox</mat-icon>
              Sin elementos{{ catSearch() ? ' que coincidan con "' + catSearch() + '"' : '' }}
            </div>
          }
        }
      </div>

      <!-- Catalog footer stats -->
      <div class="px-4 py-3 border-t border-slate-200 dark:border-white/8 shrink-0">
        <p class="text-xs text-slate-400 text-center">
          <span class="font-bold text-slate-600 dark:text-slate-300">{{ filteredCatItems().length }}</span>
          {{ filteredCatItems().length === 1 ? 'elemento' : 'elementos' }} en {{ currentTabLabel() }}
        </p>
      </div>
    </div>
  </div>
}
  `,
})
export class ProductosComponent implements OnInit, OnDestroy {
  private api   = inject(ApiService);
  private snack = inject(MatSnackBar);
  private fb    = inject(FormBuilder);
  private subs  = new Subscription();

  // ── Tabla de productos ──
  productos   = signal<Producto[]>([]);
  total       = signal(0);
  loading     = signal(false);
  saving      = signal(false);
  panelOpen   = signal(false);
  editingId   = signal<number | null>(null);

  // ── Catálogos (para dropdowns) ──
  catList            = signal<Cat[]>([]);
  subcatList         = signal<SubCat[]>([]);
  marcasList         = signal<Simple[]>([]);
  presentacionesList = signal<Simple[]>([]);
  departamentosList  = signal<Simple[]>([]);
  productorasList    = signal<Simple[]>([]);
  tamanosList        = signal<Simple[]>([]);

  // ── Cascade reactiva: IDs seleccionados en el form (signals propios) ──
  private _depId = signal<number | null>(null);
  private _catId = signal<number | null>(null);

  catsFiltradas  = computed(() => {
    const idd = this._depId();
    if (!idd) return this.catList();
    return this.catList().filter(c => Number(c.id_departamento) === Number(idd));
  });
  subcatsFiltradas = computed(() => {
    const idc = this._catId();
    if (!idc) return this.subcatList();
    return this.subcatList().filter(s => Number(s.id_categoria) === Number(idc));
  });

  // ── Filtros de tabla ──
  searchText  = signal('');
  filterCat   = signal<number | null>(null);
  filterMarca = signal<number | null>(null);
  skip        = signal(0);
  pageSize    = signal(25);
  private search$ = new Subject<string>();

  // ── Form ──
  form = this.fb.group({
    producto_gu:             ['', Validators.required],
    cod_prod:                [''],
    id_departamento:         [null as number | null],
    id_categoria:            [null as number | null],
    id_subcategoria:         [null as number | null],
    id_marca:                [null as number | null],
    id_presentacion:         [null as number | null],
    id_clasificacion_tamano: [null as number | null],
    descripcion_bi:          [''],
    gramos:                  [null as number | null],
    inagotable:              [false as boolean],
    comentario:              [''],
  });

  // ── Panel Catálogo ──
  catalogOpen = signal(false);
  catTab      = signal<CatTab>('departamentos');
  catLoading  = signal(false);
  catSaving   = signal(false);
  catEditId       = signal<number | null>(null);
  catSearch       = signal('');
  catParentFilter = signal<number | null>(null);
  catEditName = '';
  catEditParent: number | null = null;
  newName     = '';
  newParent: number | null = null;

  // Current items for the active catalog tab
  private catItemsRaw = signal<{id: number; nombre: string; extra?: string; parentId?: number}[]>([]);

  filteredCatItems = computed(() => {
    const q      = this.catSearch().toLowerCase().trim();
    const parent = this.catParentFilter();
    let items    = this.catItemsRaw();
    // filter by parent (dep→cat, cat→subcat, prod→marca)
    if (parent != null) {
      items = items.filter(i => i.parentId != null && Number(i.parentId) === Number(parent));
    }
    // filter by text
    if (q) {
      items = items.filter(i => i.nombre.toLowerCase().includes(q));
    }
    return items;
  });

  tabs: { key: CatTab; label: string; singular: string }[] = [
    { key: 'departamentos', label: 'Departamentos', singular: 'Departamento' },
    { key: 'categorias',    label: 'Categorías',    singular: 'Categoría'    },
    { key: 'subcategorias', label: 'Subcategorías', singular: 'Subcategoría' },
    { key: 'marcas',        label: 'Marcas',        singular: 'Marca'        },
    { key: 'presentaciones',label: 'Presentaciones',singular: 'Presentación' },
    { key: 'tamanos',       label: 'Tamaños',       singular: 'Tamaño'       },
  ];

  currentTabLabel(): string {
    return this.tabs.find(t => t.key === this.catTab())?.singular ?? '';
  }

  // ────────────────────────────────────────────────
  ngOnInit(): void {
    this.load();
    this.loadCatalogs();
    this.subs.add(
      this.search$.pipe(debounceTime(350), distinctUntilChanged()).subscribe(() => {
        this.skip.set(0); this.load();
      })
    );
  }
  ngOnDestroy(): void { this.subs.unsubscribe(); }

  // ── Tabla principal ──
  load(): void {
    this.loading.set(true);
    this.api.getProductos({
      skip: this.skip(), limit: this.pageSize(),
      busqueda: this.searchText() || undefined,
      id_categoria: this.filterCat() ?? undefined,
      id_marca:     this.filterMarca() ?? undefined,
    }).subscribe({
      next: (res) => { this.productos.set(res.items); this.total.set(res.total); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
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

  // Cascade handlers (update reactive signals)
  onDepChange(): void {
    const val = this.form.get('id_departamento')?.value;
    this._depId.set(val != null ? Number(val) : null);
    this._catId.set(null);
    this.form.patchValue({ id_categoria: null, id_subcategoria: null });
  }
  onCatChange(): void {
    const val = this.form.get('id_categoria')?.value;
    this._catId.set(val != null ? Number(val) : null);
    this.form.patchValue({ id_subcategoria: null });
  }

  onSearch(val: string): void { this.searchText.set(val); this.search$.next(val); }
  reload(): void { this.skip.set(0); this.load(); }
  clearFilters(): void { this.searchText.set(''); this.filterCat.set(null); this.filterMarca.set(null); this.skip.set(0); this.load(); }
  prevPage(): void { this.skip.update(v => Math.max(0, v - this.pageSize())); this.load(); }
  nextPage(): void { this.skip.update(v => v + this.pageSize()); this.load(); }
  onPageSizeChange(size: number): void { this.pageSize.set(+size); this.skip.set(0); this.load(); }

  openPanel(p: Producto | null): void {
    this.editingId.set(p?.id ?? null);
    this._depId.set(p?.id_departamento ?? null);
    this._catId.set(p?.id_categoria ?? null);
    this.form.reset({
      producto_gu:             p?.producto_gu             ?? '',
      cod_prod:                p?.cod_prod                ?? '',
      id_departamento:         p?.id_departamento         ?? null,
      id_categoria:            p?.id_categoria            ?? null,
      id_subcategoria:         p?.id_subcategoria         ?? null,
      id_marca:                p?.id_marca                ?? null,
      id_presentacion:         p?.id_presentacion         ?? null,
      id_clasificacion_tamano: p?.id_clasificacion_tamano ?? null,
      descripcion_bi:          p?.descripcion_bi          ?? '',
      gramos:                  p?.gramos                  ?? null,
      inagotable:              p?.inagotable              ?? false,
      comentario:              p?.comentario              ?? '',
    });
    this.panelOpen.set(true);
  }
  closePanel(): void { this.panelOpen.set(false); }

  save(): void {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    this.saving.set(true);
    const v = this.form.value;
    const payload = {
      producto_gu:             v.producto_gu,
      cod_prod:                v.cod_prod || null,
      descripcion_bi:          v.descripcion_bi || null,
      gramos:                  v.gramos != null && v.gramos !== ('' as any) ? Number(v.gramos) : null,
      inagotable:              v.inagotable === true,
      comentario:              v.comentario || null,
      id_subcategoria:         v.id_subcategoria         ?? null,
      id_marca:                v.id_marca                ?? null,
      id_presentacion:         v.id_presentacion         ?? null,
      id_clasificacion_tamano: v.id_clasificacion_tamano ?? null,
    };
    const op = this.editingId()
      ? this.api.updateProducto(this.editingId()!, payload)
      : this.api.createProducto(payload);
    op.subscribe({
      next: () => {
        this.saving.set(false); this.closePanel(); this.load();
        this.snack.open(this.editingId() ? 'Producto actualizado' : 'Producto creado', 'OK', { duration: 3000 });
      },
      error: (err) => { this.saving.set(false); this.snack.open(err?.error?.detail ?? 'Error al guardar', 'OK', { duration: 4000 }); },
    });
  }

  deleteProducto(p: Producto): void {
    if (!confirm(`¿Eliminar "${p.producto_gu}"?`)) return;
    this.api.deleteProducto(p.id).subscribe({
      next: () => { this.load(); this.snack.open('Producto eliminado', 'OK', { duration: 3000 }); },
      error: () => this.snack.open('Error al eliminar', 'OK', { duration: 3000 }),
    });
  }

  // ── Panel Catálogo ──
  openCatalog(): void {
    this.catalogOpen.set(true);
    this.loadCatItems();
  }
  closeCatalog(): void { this.catalogOpen.set(false); this.cancelEdit(); }

  setTab(key: CatTab): void {
    this.catTab.set(key);
    this.catSearch.set('');
    this.catParentFilter.set(null);
    this.newName = '';
    this.newParent = null;
    this.cancelEdit();
    this.loadCatItems();
  }

  private loadCatItems(): void {
    this.catLoading.set(true);
    const depName  = (id?: number) => this.departamentosList().find(d => d.id === id)?.nombre ?? '';
    const catName  = (id?: number) => this.catList().find(c => c.id_categoria === id)?.nombre ?? '';
    const prodName = (id?: number) => this.productorasList().find(p => p.id === id)?.nombre ?? '';

    switch (this.catTab()) {
      case 'departamentos':
        this.catItemsRaw.set(this.departamentosList().map(d => ({ id: d.id, nombre: d.nombre })));
        this.catLoading.set(false); break;
      case 'categorias':
        this.api.getCatalogosCategorias().subscribe({
          next: list => {
            this.catList.set(list);
            this.catItemsRaw.set(list.map((c: any) => ({
              id: c.id_categoria, nombre: c.nombre,
              extra: c.id_departamento ? depName(c.id_departamento) : undefined,
              parentId: c.id_departamento,
            })));
            this.catLoading.set(false);
          }, error: () => this.catLoading.set(false),
        }); break;
      case 'subcategorias':
        this.api.getCatalogosSubCategorias().subscribe({
          next: list => {
            this.subcatList.set(list);
            this.catItemsRaw.set(list.map((s: any) => ({
              id: s.id_subcategoria, nombre: s.nombre,
              extra: s.id_categoria ? catName(s.id_categoria) : undefined,
              parentId: s.id_categoria,
            })));
            this.catLoading.set(false);
          }, error: () => this.catLoading.set(false),
        }); break;
      case 'marcas':
        this.api.getCatMarcas().subscribe({
          next: list => {
            this.marcasList.set(list);
            this.catItemsRaw.set(list.map((m: any) => ({
              id: m.id, nombre: m.nombre,
              extra: m.id_productora ? prodName(m.id_productora) : undefined,
              parentId: m.id_productora,
            })));
            this.catLoading.set(false);
          }, error: () => this.catLoading.set(false),
        }); break;
      case 'presentaciones':
        this.api.getCatPresentaciones().subscribe({
          next: list => {
            this.presentacionesList.set(list);
            this.catItemsRaw.set(list.map((p: any) => ({ id: p.id, nombre: p.nombre })));
            this.catLoading.set(false);
          }, error: () => this.catLoading.set(false),
        }); break;
      case 'tamanos':
        this.api.getCatTamanos().subscribe({
          next: list => {
            this.tamanosList.set(list);
            this.catItemsRaw.set(list.map((t: any) => ({ id: t.id, nombre: t.nombre })));
            this.catLoading.set(false);
          }, error: () => this.catLoading.set(false),
        }); break;
    }
  }

  addItem(): void {
    const nombre = this.newName.trim();
    if (!nombre) return;
    this.catSaving.set(true);
    let obs: any;
    switch (this.catTab()) {
      case 'departamentos':  obs = this.api.createCatDepartamento({ nombre }); break;
      case 'categorias':     obs = this.api.createCatalogosCategoria({ nombre, id_departamento: this.newParent }); break;
      case 'subcategorias':  obs = this.api.createCatalogosSubCategoria({ nombre, id_categoria: this.newParent }); break;
      case 'marcas':         obs = this.api.createCatMarca({ nombre, id_productora: this.newParent }); break;
      case 'presentaciones': obs = this.api.createCatPresentacion({ nombre }); break;
      case 'tamanos':        obs = this.api.createCatTamano({ nombre }); break;
      default: return;
    }
    obs.subscribe({
      next: () => {
        this.catSaving.set(false); this.newName = ''; this.newParent = null;
        this.loadCatItems(); this.loadCatalogs();
        this.snack.open('Elemento agregado', 'OK', { duration: 2000 });
      },
      error: (e: any) => { this.catSaving.set(false); this.snack.open(e?.error?.detail ?? 'Error al agregar', 'OK', { duration: 4000 }); },
    });
  }

  startEdit(it: {id: number; nombre: string; parentId?: number}): void {
    this.catEditId.set(it.id);
    this.catEditName = it.nombre;
    this.catEditParent = it.parentId ?? null;
  }
  cancelEdit(): void { this.catEditId.set(null); this.catEditName = ''; this.catEditParent = null; }

  saveEdit(id: number): void {
    const nombre = this.catEditName.trim();
    if (!nombre) return;
    this.catSaving.set(true);
    let obs: any;
    switch (this.catTab()) {
      case 'departamentos':  obs = this.api.updateCatDepartamento(id, { nombre }); break;
      case 'categorias':     obs = this.api.updateCatalogosCategoria(id, { nombre }); break;
      case 'subcategorias':  obs = this.api.updateCatalogosSubCategoria(id, { nombre }); break;
      case 'marcas':         obs = this.api.updateCatMarca(id, { nombre }); break;
      case 'presentaciones': obs = this.api.updateCatPresentacion(id, { nombre }); break;
      case 'tamanos':        obs = this.api.updateCatTamano(id, { nombre }); break;
      default: return;
    }
    obs.subscribe({
      next: () => {
        this.catSaving.set(false); this.cancelEdit();
        this.loadCatItems(); this.loadCatalogs();
        this.snack.open('Elemento actualizado', 'OK', { duration: 2000 });
      },
      error: (e: any) => { this.catSaving.set(false); this.snack.open(e?.error?.detail ?? 'Error al actualizar', 'OK', { duration: 4000 }); },
    });
  }

  deleteItem(id: number): void {
    if (!confirm('¿Eliminar este elemento? Si está en uso no se podrá eliminar.')) return;
    let obs: any;
    switch (this.catTab()) {
      case 'departamentos':  obs = this.api.deleteCatDepartamento(id); break;
      case 'categorias':     obs = this.api.deleteCatalogosCategoria(id); break;
      case 'subcategorias':  obs = this.api.deleteCatalogosSubCategoria(id); break;
      case 'marcas':         obs = this.api.deleteCatMarca(id); break;
      case 'presentaciones': obs = this.api.deleteCatPresentacion(id); break;
      case 'tamanos':        obs = this.api.deleteCatTamano(id); break;
      default: return;
    }
    obs.subscribe({
      next: () => { this.loadCatItems(); this.loadCatalogs(); this.snack.open('Elemento eliminado', 'OK', { duration: 2000 }); },
      error: (e: any) => this.snack.open(e?.error?.detail ?? 'Error: puede estar en uso', 'OK', { duration: 5000 }),
    });
  }
}
