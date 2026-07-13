import { Component, OnInit, OnDestroy, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Subject, debounceTime, distinctUntilChanged, forkJoin } from 'rxjs';
import maplibregl from 'maplibre-gl';
import { ApiService } from '../../../core/services/api.service';
import { PuntoInteres } from '../../../core/models/visita.model';
import { CatalogosComponent } from './catalogos.component';
import { HasPermDirective } from '../../../core/directives/has-perm.directive';

@Component({
  selector: 'app-points',
  standalone: true,
  imports: [
    CommonModule, FormsModule, ReactiveFormsModule,
    MatIconModule, MatSnackBarModule, MatProgressSpinnerModule, MatTooltipModule,
    CatalogosComponent, HasPermDirective,
  ],
  template: `
<div class="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">

  <!-- HEADER -->
  <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
    <div>
      <h1 class="text-3xl font-bold text-slate-800 dark:text-white tracking-tight">Puntos de Venta</h1>
      <p class="text-slate-500 dark:text-slate-400 mt-1">
        @if (view() === 'pdvs') {
          <span class="font-bold text-primary-500">{{ total() }}</span> puntos en total
        } @else {
          Gestiona los catálogos asociados a los PDV
        }
      </p>
    </div>
    <div class="flex items-center gap-2">
      <!-- Toggle vista -->
      <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/5 rounded-xl p-1 flex shadow-sm">
        <button (click)="view.set('pdvs')"
          [class.bg-primary-600]="view() === 'pdvs'" [class.text-white]="view() === 'pdvs'"
          [class.text-slate-500]="view() !== 'pdvs'"
          class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-black transition-all">
          <mat-icon class="!text-base">storefront</mat-icon> PDVs
        </button>
        <button (click)="view.set('catalogos')"
          [class.bg-primary-600]="view() === 'catalogos'" [class.text-white]="view() === 'catalogos'"
          [class.text-slate-500]="view() !== 'catalogos'"
          class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-black transition-all">
          <mat-icon class="!text-base">tune</mat-icon> Catálogos
        </button>
      </div>
      @if (view() === 'pdvs') {
        <button (click)="loadAll()"
          class="w-10 h-10 flex items-center justify-center rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/5 text-slate-500 hover:text-primary-500 transition-all shadow-sm">
          <mat-icon>refresh</mat-icon>
        </button>
        <button *hasPerm="'points'; action:'write'" (click)="openPanel(null)"
          class="flex items-center gap-2 px-5 py-2.5 bg-primary-600 hover:bg-primary-500 text-white font-black rounded-xl shadow-lg transition-all active:scale-95 text-sm">
          <mat-icon class="!text-base">add_location_alt</mat-icon>
          Nuevo PDV
        </button>
      }
    </div>
  </div>

  @if (view() === 'catalogos') {
    <app-catalogos></app-catalogos>
  } @else {

  <!-- FILTROS -->
  <div class="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-white/5 shadow-sm p-5">
    <div class="flex items-center gap-2 mb-3">
      <mat-icon class="!text-base text-primary-500">filter_list</mat-icon>
      <span class="text-xs font-black text-slate-500 uppercase tracking-widest">Filtros</span>
      @if (filterRegion() || filterCiudad() || filterJerarquia() || searchText()) {
        <button (click)="clearFilters()"
          class="ml-auto flex items-center gap-1 text-xs font-bold text-slate-400 hover:text-rose-400 transition-colors">
          <mat-icon class="!text-sm">close</mat-icon> Limpiar
        </button>
      }
    </div>
    <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
      <div class="space-y-1">
        <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Departamento</label>
        <div class="relative">
          <select [ngModel]="filterRegion()" (ngModelChange)="onFilterRegionChange($event)"
            class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-primary-500 text-slate-800 dark:text-white rounded-xl px-3 py-2 pr-8 text-sm font-semibold appearance-none outline-none transition-colors">
            <option value="">Todos</option>
            @for (r of regions(); track r) { <option [value]="r">{{ r }}</option> }
          </select>
          <mat-icon class="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none !text-base">expand_more</mat-icon>
        </div>
      </div>
      <div class="space-y-1">
        <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Ciudad</label>
        <div class="relative">
          <select [ngModel]="filterCiudad()" (ngModelChange)="filterCiudad.set($event); reload()"
            class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-primary-500 text-slate-800 dark:text-white rounded-xl px-3 py-2 pr-8 text-sm font-semibold appearance-none outline-none transition-colors">
            <option value="">Todas</option>
            @for (c of cities(); track c) { <option [value]="c">{{ c }}</option> }
          </select>
          <mat-icon class="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none !text-base">expand_more</mat-icon>
        </div>
      </div>
      <div class="space-y-1">
        <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Tipo de Negocio</label>
        <div class="relative">
          <select [ngModel]="filterJerarquia()" (ngModelChange)="filterJerarquia.set($event); reload()"
            class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-primary-500 text-slate-800 dark:text-white rounded-xl px-3 py-2 pr-8 text-sm font-semibold appearance-none outline-none transition-colors">
            <option value="">Todos</option>
            @for (j of jerarquias(); track j) { <option [value]="j">{{ j }}</option> }
          </select>
          <mat-icon class="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none !text-base">expand_more</mat-icon>
        </div>
      </div>
      <div class="space-y-1">
        <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Buscar</label>
        <div class="relative">
          <mat-icon class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none !text-base">search</mat-icon>
          <input [ngModel]="searchText()" (ngModelChange)="onSearch($event)"
            placeholder="Nombre o identificador..."
            class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-primary-500 text-slate-800 dark:text-white placeholder-slate-400 rounded-xl pl-9 pr-3 py-2 text-sm font-semibold outline-none transition-colors">
        </div>
      </div>
    </div>
  </div>

  <!-- TABLE -->
  @if (loading()) {
    <div class="flex flex-col items-center justify-center py-24 gap-4">
      <mat-spinner diameter="48" strokeWidth="4"></mat-spinner>
      <p class="text-slate-400 font-medium">Cargando directorio...</p>
    </div>
  } @else {
    <div class="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-white/5 shadow-sm overflow-hidden overflow-x-auto">
      <table class="w-full text-left border-collapse min-w-[900px]">
        <thead>
          <tr class="bg-slate-50 dark:bg-slate-950/50 border-b border-slate-100 dark:border-white/5">
            <th class="px-4 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Identificador</th>
            <th class="px-4 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Nombre</th>
            <th class="px-4 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Dirección</th>
            <th class="px-4 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Dpto / Ciudad</th>
            <th class="px-4 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Tipo Negocio</th>
            <th class="px-4 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Subtipo</th>
            <th class="px-4 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Canal</th>
            <th class="px-4 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Coord.</th>
            <th class="px-4 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-right">Acción</th>
          </tr>
        </thead>
        <tbody>
          @for (p of points(); track p.id) {
            <tr class="border-b border-slate-100 dark:border-white/5 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors">
              <td class="px-4 py-3.5">
                <span class="font-mono text-xs font-bold text-primary-600 dark:text-primary-400 bg-primary-50 dark:bg-primary-900/20 px-2 py-1 rounded-lg">{{ p.id }}</span>
              </td>
              <td class="px-4 py-3.5">
                <div class="flex items-center gap-2.5">
                  <div class="w-8 h-8 rounded-lg bg-slate-100 dark:bg-white/5 flex items-center justify-center shrink-0">
                    <mat-icon class="!text-sm text-slate-500">storefront</mat-icon>
                  </div>
                  <span class="font-bold text-slate-800 dark:text-white text-sm">{{ p.nombre || '—' }}</span>
                </div>
              </td>
              <td class="px-4 py-3.5 text-sm text-slate-500 dark:text-slate-400 max-w-[160px]">
                <span class="line-clamp-2">{{ p.direccion || '—' }}</span>
              </td>
              <td class="px-4 py-3.5">
                <div class="flex flex-col">
                  <span class="text-sm font-semibold text-slate-700 dark:text-slate-300">{{ p.departamento || '—' }}</span>
                  <span class="text-xs text-slate-400">{{ p.ciudad }}</span>
                </div>
              </td>
              <td class="px-4 py-3.5 text-sm text-slate-500 dark:text-slate-400">{{ p.jerarquia_n2 || '—' }}</td>
              <td class="px-4 py-3.5 text-sm text-slate-500 dark:text-slate-400">{{ p.jerarquia_n2_2 || '—' }}</td>
              <td class="px-4 py-3.5">
                @if (p.cadena) {
                  <span class="text-xs font-bold px-2 py-1 rounded-full bg-slate-100 dark:bg-white/5 text-slate-600 dark:text-slate-300">{{ p.cadena }}</span>
                } @else { <span class="text-slate-300 dark:text-slate-600">—</span> }
              </td>
              <td class="px-4 py-3.5">
                @if (p.latitud && p.longitud) {
                  <span class="font-mono text-[10px] text-slate-400 leading-tight">{{ p.latitud }},<br>{{ p.longitud }}</span>
                } @else {
                  <span class="text-slate-300 dark:text-slate-600 text-xs">Sin coord.</span>
                }
              </td>
              <td class="px-4 py-3.5 text-right">
                <div class="inline-flex items-center gap-1">
                  <button *hasPerm="'points'; action:'write'" (click)="openPanel(p)" matTooltip="Editar"
                    class="w-8 h-8 rounded-lg bg-slate-100 dark:bg-white/5 hover:bg-primary-500 text-slate-500 dark:text-slate-400 hover:text-white inline-flex items-center justify-center transition-all">
                    <mat-icon class="!text-sm">edit</mat-icon>
                  </button>
                  <button *hasPerm="'points'; action:'delete'" (click)="deletePoint(p)" matTooltip="Eliminar"
                    class="w-8 h-8 rounded-lg bg-slate-100 dark:bg-white/5 hover:bg-rose-500 text-slate-500 dark:text-slate-400 hover:text-white inline-flex items-center justify-center transition-all">
                    <mat-icon class="!text-sm">delete</mat-icon>
                  </button>
                </div>
              </td>
            </tr>
          }
          @if (points().length === 0) {
            <tr>
              <td colspan="9" class="py-20 text-center">
                <div class="flex flex-col items-center gap-3 opacity-40">
                  <mat-icon class="!text-5xl">location_off</mat-icon>
                  <p class="font-bold">No se encontraron puntos</p>
                </div>
              </td>
            </tr>
          }
        </tbody>
      </table>
    </div>

    <!-- PAGINACIÓN -->
    <div class="flex items-center justify-between flex-wrap gap-3">
      <div class="flex items-center gap-3">
        <p class="text-sm text-slate-500">
          Mostrando <span class="font-bold text-slate-800 dark:text-white">{{ skip() + 1 }}–{{ skip() + points().length }}</span>
          de <span class="font-bold text-slate-800 dark:text-white">{{ total() }}</span>
        </p>
        <div class="relative">
          <select [ngModel]="pageSize()" (ngModelChange)="onPageSizeChange($event)"
            class="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-primary-500 text-slate-800 dark:text-white rounded-xl px-3 py-1.5 pr-7 text-sm font-bold appearance-none outline-none transition-colors">
            <option [value]="100">100 / pág</option>
            <option [value]="200">200 / pág</option>
            <option [value]="500">500 / pág</option>
          </select>
          <mat-icon class="absolute right-1.5 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none !text-base">expand_more</mat-icon>
        </div>
      </div>
      <div class="flex gap-2">
        <button (click)="prevPage()" [disabled]="skip() === 0"
          class="flex items-center gap-1 px-4 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/5 hover:border-primary-500 disabled:opacity-40 text-slate-700 dark:text-white rounded-xl text-sm font-bold transition-all">
          <mat-icon class="!text-base">chevron_left</mat-icon> Anterior
        </button>
        <button (click)="nextPage()" [disabled]="skip() + pageSize() >= total()"
          class="flex items-center gap-1 px-4 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/5 hover:border-primary-500 disabled:opacity-40 text-slate-700 dark:text-white rounded-xl text-sm font-bold transition-all">
          Siguiente <mat-icon class="!text-base">chevron_right</mat-icon>
        </button>
      </div>
    </div>
  }
  } <!-- /@else view==='pdvs' -->
</div>

<!-- SLIDE PANEL -->
@if (panelOpen()) {
  <div class="fixed inset-0 z-50 flex justify-end">
    <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" (click)="closePanel()"></div>
    <div class="relative w-full max-w-2xl bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-white/8 h-full flex flex-col shadow-2xl overflow-hidden">

      <div class="bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200 dark:border-white/8 px-6 py-5 shrink-0">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-xl bg-primary-600 flex items-center justify-center">
              <mat-icon class="text-white !text-xl">{{ editingId() ? 'edit_location' : 'add_location_alt' }}</mat-icon>
            </div>
            <div>
              <h3 class="font-black text-slate-900 dark:text-white">{{ editingId() ? 'Editar Punto de Interés' : 'Nuevo Punto de Interés' }}</h3>
              <p class="text-xs text-slate-500 font-mono">{{ editingId() || 'Completa los datos del PDV' }}</p>
            </div>
          </div>
          <button (click)="closePanel()"
            class="w-9 h-9 rounded-xl bg-slate-200 dark:bg-white/10 hover:bg-slate-300 dark:hover:bg-white/15 flex items-center justify-center text-slate-500 dark:text-slate-400 transition-all">
            <mat-icon class="!text-lg">close</mat-icon>
          </button>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto px-6 py-6">
        <form [formGroup]="form" class="space-y-5">

          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-1.5">
              <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Identificador *</label>
              <input formControlName="id"
                [attr.readonly]="editingId() ? true : null"
                [class.opacity-60]="!!editingId()"
                [class.cursor-not-allowed]="!!editingId()"
                placeholder="Ej: AKT0006_1"
                class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-primary-500 rounded-xl px-4 py-2.5 text-sm font-mono font-bold text-slate-900 dark:text-white placeholder-slate-400 outline-none transition-colors"
                [class.border-red-500]="form.get('id')?.invalid && form.get('id')?.touched">
              @if (!editingId()) {
                <p class="text-[10px] text-slate-400">Se genera según la jerarquía del punto</p>
              }
            </div>
            <div class="space-y-1.5">
              <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Nombre del Punto *</label>
              <input formControlName="nombre" placeholder="Nombre del establecimiento"
                class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-primary-500 rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-900 dark:text-white placeholder-slate-400 outline-none transition-colors">
            </div>
          </div>

          <div class="space-y-1.5">
            <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Dirección</label>
            <input formControlName="direccion" placeholder="Dirección completa"
              class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-primary-500 rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-900 dark:text-white placeholder-slate-400 outline-none transition-colors">
          </div>

          <div class="grid grid-cols-3 gap-4">
            <div class="space-y-1.5">
              <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Departamento</label>
              <input formControlName="departamento" placeholder="Ej: Zulia" list="dept-list"
                class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-primary-500 rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-900 dark:text-white placeholder-slate-400 outline-none transition-colors">
              <datalist id="dept-list">@for (r of regions(); track r) { <option [value]="r"> }</datalist>
            </div>
            <div class="space-y-1.5">
              <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Ciudad</label>
              <input formControlName="ciudad" placeholder="Ej: Maracaibo" list="city-list"
                class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-primary-500 rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-900 dark:text-white placeholder-slate-400 outline-none transition-colors">
              <datalist id="city-list">@for (c of cities(); track c) { <option [value]="c"> }</datalist>
            </div>
            <div class="space-y-1.5">
              <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Canal de Venta</label>
              <input formControlName="cadena" placeholder="Ej: Moderno" list="canal-list"
                class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-primary-500 rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-900 dark:text-white placeholder-slate-400 outline-none transition-colors">
              <datalist id="canal-list">@for (c of chains(); track c) { <option [value]="c"> }</datalist>
            </div>
          </div>

          <div class="grid grid-cols-3 gap-4">
            <div class="space-y-1.5">
              <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Tipo de Negocio</label>
              <input formControlName="jerarquia_n2" placeholder="Ej: Supermercado" list="jn2-list"
                class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-primary-500 rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-900 dark:text-white placeholder-slate-400 outline-none transition-colors">
              <datalist id="jn2-list">@for (j of jerarquias(); track j) { <option [value]="j"> }</datalist>
            </div>
            <div class="space-y-1.5">
              <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Subtipo de Negocio</label>
              <input formControlName="jerarquia_n2_2" placeholder="Ej: Alkosto" list="jn22-list"
                class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-primary-500 rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-900 dark:text-white placeholder-slate-400 outline-none transition-colors">
              <datalist id="jn22-list">@for (j of jerarquias2(); track j) { <option [value]="j"> }</datalist>
            </div>
            <div class="space-y-1.5">
              <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Alcance</label>
              <input formControlName="nivel_de_alcance" placeholder="Ej: Regional" list="alcance-list"
                class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-primary-500 rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-900 dark:text-white placeholder-slate-400 outline-none transition-colors">
              <datalist id="alcance-list">@for (n of nivelesAlcance(); track n) { <option [value]="n"> }</datalist>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-1.5">
              <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">RIF</label>
              <input formControlName="rif" placeholder="Ej: J-12345678-9"
                class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-primary-500 rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-900 dark:text-white placeholder-slate-400 outline-none transition-colors">
            </div>
            <div class="space-y-1.5">
              <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Radio (metros)</label>
              <input formControlName="radio" placeholder="100" type="number"
                class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-primary-500 rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-900 dark:text-white placeholder-slate-400 outline-none transition-colors">
            </div>
          </div>

          <!-- COORDENADAS + MAPA -->
          <div class="space-y-3">
            <div class="grid grid-cols-2 gap-4">
              <div class="space-y-1.5">
                <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Latitud</label>
                <input formControlName="latitud" placeholder="Ej: 10.481910" (change)="syncMapCenter()"
                  class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-primary-500 rounded-xl px-4 py-2.5 text-sm font-mono font-semibold text-slate-900 dark:text-white placeholder-slate-400 outline-none transition-colors">
              </div>
              <div class="space-y-1.5">
                <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Longitud</label>
                <input formControlName="longitud" placeholder="Ej: -66.903606" (change)="syncMapCenter()"
                  class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-primary-500 rounded-xl px-4 py-2.5 text-sm font-mono font-semibold text-slate-900 dark:text-white placeholder-slate-400 outline-none transition-colors">
              </div>
            </div>
            <div class="rounded-xl overflow-hidden border border-slate-200 dark:border-slate-700 relative" style="height:280px">
              <div id="punto-map" class="w-full h-full"></div>
              <div class="absolute bottom-2 left-2 bg-white/90 dark:bg-slate-900/90 backdrop-blur text-[10px] text-slate-500 font-semibold px-2 py-1 rounded-lg pointer-events-none">
                Haz clic para establecer coordenadas
              </div>
            </div>
          </div>

        </form>
      </div>

      <div class="px-6 py-5 border-t border-slate-200 dark:border-white/8 shrink-0 flex gap-3">
        <button type="button" (click)="closePanel()"
          class="flex-1 py-2.5 border border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white rounded-xl font-bold text-sm transition-all">
          Cancelar
        </button>
        <button type="button" (click)="save()" [disabled]="form.invalid || saving()"
          class="flex-1 flex items-center justify-center gap-2 py-2.5 bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white font-black rounded-xl text-sm shadow-lg transition-all active:scale-95">
          @if (saving()) { <mat-spinner diameter="16"></mat-spinner> }
          @else { <mat-icon class="!text-base">save</mat-icon> }
          {{ editingId() ? 'Guardar Cambios' : 'Crear PDV' }}
        </button>
      </div>
    </div>
  </div>
}
  `
})
export class PointsComponent implements OnInit, OnDestroy {
  private api = inject(ApiService);
  private snack = inject(MatSnackBar);
  private fb = inject(FormBuilder);

  view = signal<'pdvs' | 'catalogos'>('pdvs');
  loading = signal(false);
  saving = signal(false);
  panelOpen = signal(false);
  editingId = signal<string | null>(null);

  points = signal<PuntoInteres[]>([]);
  total = signal(0);
  skip = signal(0);
  pageSize = signal(100);

  regions = signal<string[]>([]);
  cities = signal<string[]>([]);
  chains = signal<string[]>([]);
  jerarquias = signal<string[]>([]);
  jerarquias2 = signal<string[]>([]);
  nivelesAlcance = signal<string[]>([]);

  filterRegion = signal('');
  filterCiudad = signal('');
  filterJerarquia = signal('');
  searchText = signal('');

  private search$ = new Subject<string>();
  private mapInstance: maplibregl.Map | null = null;
  private mapMarker: maplibregl.Marker | null = null;

  form = this.fb.group({
    id: ['', Validators.required],
    nombre: ['', Validators.required],
    direccion: [''],
    departamento: [''],
    ciudad: [''],
    cadena: [''],
    jerarquia_n2: [''],
    jerarquia_n2_2: [''],
    nivel_de_alcance: [''],
    latitud: [''],
    longitud: [''],
    rif: [''],
    radio: ['']
  });

  ngOnInit(): void {
    this.loadAll();
    this.loadDropdowns();
    this.search$.pipe(debounceTime(350), distinctUntilChanged()).subscribe(() => {
      this.skip.set(0); this.reload();
    });

    // Al cambiar departamento en el form, recargar ciudades de ese departamento
    this.form.get('departamento')?.valueChanges.subscribe((dep) => {
      this.api.getCities(dep || undefined).subscribe({
        next: d => this.cities.set(d), error: () => {}
      });
    });
  }

  ngOnDestroy(): void {
    this.destroyMap();
  }

  private filterParams() {
    return {
      region: this.filterRegion() || undefined,
      ciudad: this.filterCiudad() || undefined,
      jerarquia_n2: this.filterJerarquia() || undefined,
      search: this.searchText() || undefined,
    };
  }

  loadAll(): void {
    this.loading.set(true);
    forkJoin({
      items: this.api.getPoints({ ...this.filterParams(), skip: this.skip(), limit: this.pageSize() }),
      count: this.api.getPointsCount(this.filterParams())
    }).subscribe({
      next: ({ items, count }) => {
        this.points.set(items);
        this.total.set(count.total);
        this.loading.set(false);
      },
      error: () => this.loading.set(false)
    });
  }

  reload(): void { this.skip.set(0); this.loadAll(); }

  loadDropdowns(): void {
    this.api.getRegions().subscribe({ next: d => this.regions.set(d), error: () => {} });
    this.api.getCities(this.filterRegion() || undefined).subscribe({ next: d => this.cities.set(d), error: () => {} });
    this.api.getChains().subscribe({ next: d => this.chains.set(d), error: () => {} });
    this.api.getJerarquiaN2().subscribe({ next: d => this.jerarquias.set(d), error: () => {} });
    this.api.getJerarquiaN2_2().subscribe({ next: d => this.jerarquias2.set(d), error: () => {} });
    this.api.getNivelesAlcance().subscribe({ next: d => this.nivelesAlcance.set(d), error: () => {} });
  }

  onSearch(val: string): void { this.searchText.set(val); this.search$.next(val); }
  onFilterRegionChange(val: string): void {
    this.filterRegion.set(val);
    this.filterCiudad.set('');
    this.api.getCities(val || undefined).subscribe({ next: d => this.cities.set(d), error: () => {} });
    this.reload();
  }
  clearFilters(): void {
    this.filterRegion.set(''); this.filterCiudad.set(''); this.filterJerarquia.set(''); this.searchText.set('');
    this.api.getCities().subscribe({ next: d => this.cities.set(d), error: () => {} });
    this.reload();
  }
  prevPage(): void { this.skip.update(v => Math.max(0, v - this.pageSize())); this.loadAll(); }
  nextPage(): void { this.skip.update(v => v + this.pageSize()); this.loadAll(); }
  onPageSizeChange(size: number): void { this.pageSize.set(+size); this.skip.set(0); this.loadAll(); }

  openPanel(p: PuntoInteres | null): void {
    this.editingId.set(p?.id ?? null);
    this.form.reset({
      id: p?.id ?? '', nombre: p?.nombre ?? '', direccion: p?.direccion ?? '',
      departamento: p?.departamento ?? '', ciudad: p?.ciudad ?? '', cadena: p?.cadena ?? '',
      jerarquia_n2: p?.jerarquia_n2 ?? '', jerarquia_n2_2: p?.jerarquia_n2_2 ?? '',
      nivel_de_alcance: p?.nivel_de_alcance ?? '', latitud: p?.latitud ?? '',
      longitud: p?.longitud ?? '', rif: p?.rif ?? '', radio: p?.radio ?? ''
    });
    this.panelOpen.set(true);
    setTimeout(() => this.initMap(), 250);
  }

  closePanel(): void { this.destroyMap(); this.panelOpen.set(false); }

  initMap(): void {
    const el = document.getElementById('punto-map');
    if (!el) return;
    this.destroyMap();

    const latStr = this.form.get('latitud')?.value?.trim() ?? '';
    const lngStr = this.form.get('longitud')?.value?.trim() ?? '';
    const hasCoords = latStr !== '' && lngStr !== '' && !isNaN(+latStr) && !isNaN(+lngStr);
    const lat = hasCoords ? +latStr : 10.48;
    const lng = hasCoords ? +lngStr : -66.90;
    const nombre = this.form.get('nombre')?.value || 'PDV';

    this.mapInstance = new maplibregl.Map({
      container: el,
      style: 'https://tiles.openfreemap.org/styles/liberty',
      center: [lng, lat],
      zoom: hasCoords ? 15 : 7,
    });

    this.mapInstance.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');

    if (hasCoords) {
      const popup = new maplibregl.Popup({ offset: 42, closeButton: false })
        .setHTML(this.popupHtml(nombre, latStr, lngStr));

      this.mapMarker = new maplibregl.Marker({ color: '#7c3aed', scale: 1.2 })
        .setLngLat([lng, lat])
        .setPopup(popup)
        .addTo(this.mapInstance);

      this.mapMarker.togglePopup();
    }

    this.mapInstance.on('click', (e: maplibregl.MapMouseEvent) => {
      const newLat = e.lngLat.lat.toFixed(6);
      const newLng = e.lngLat.lng.toFixed(6);
      this.form.patchValue({ latitud: newLat, longitud: newLng });
      const n = this.form.get('nombre')?.value || 'PDV';
      if (this.mapMarker) {
        this.mapMarker.setLngLat([+newLng, +newLat]);
        this.mapMarker.getPopup()?.setHTML(this.popupHtml(n, newLat, newLng));
        if (!this.mapMarker.getPopup()?.isOpen()) this.mapMarker.togglePopup();
      } else {
        const p = new maplibregl.Popup({ offset: 42, closeButton: false })
          .setHTML(this.popupHtml(n, newLat, newLng));
        this.mapMarker = new maplibregl.Marker({ color: '#7c3aed', scale: 1.2 })
          .setLngLat([+newLng, +newLat])
          .setPopup(p)
          .addTo(this.mapInstance!);
        this.mapMarker.togglePopup();
      }
    });
  }

  private popupHtml(nombre: string, lat: string, lng: string): string {
    return `<div style="font-family:system-ui,sans-serif;padding:2px 4px">
      <div style="font-weight:700;font-size:13px;color:#1e1b4b;margin-bottom:2px">${nombre}</div>
      <div style="font-family:monospace;font-size:11px;color:#6b7280">${lat}, ${lng}</div>
    </div>`;
  }

  syncMapCenter(): void {
    const latStr = this.form.get('latitud')?.value?.trim() ?? '';
    const lngStr = this.form.get('longitud')?.value?.trim() ?? '';
    if (!this.mapInstance || !latStr || !lngStr || isNaN(+latStr) || isNaN(+lngStr)) return;
    const lat = +latStr;
    const lng = +lngStr;
    const nombre = this.form.get('nombre')?.value || 'PDV';
    this.mapInstance.flyTo({ center: [lng, lat], zoom: 15, duration: 800 });
    if (this.mapMarker) {
      this.mapMarker.setLngLat([lng, lat]);
      this.mapMarker.getPopup()?.setHTML(this.popupHtml(nombre, latStr, lngStr));
    } else {
      const popup = new maplibregl.Popup({ offset: 42, closeButton: false })
        .setHTML(this.popupHtml(nombre, latStr, lngStr));
      this.mapMarker = new maplibregl.Marker({ color: '#7c3aed', scale: 1.2 })
        .setLngLat([lng, lat])
        .setPopup(popup)
        .addTo(this.mapInstance);
      this.mapMarker.togglePopup();
    }
  }

  destroyMap(): void {
    if (this.mapInstance) { this.mapInstance.remove(); this.mapInstance = null; this.mapMarker = null; }
  }

  deletePoint(p: PuntoInteres): void {
    if (!confirm(`¿Eliminar "${p.nombre || p.id}"? Esta acción no se puede deshacer.`)) return;
    this.api.deletePoint(p.id).subscribe({
      next: () => { this.loadAll(); this.snack.open('PDV eliminado', 'OK', { duration: 3000 }); },
      error: (err) => this.snack.open(err?.error?.detail ?? 'Error al eliminar', 'OK', { duration: 4000 })
    });
  }

  save(): void {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    this.saving.set(true);
    const v = this.form.value;
    const payload = {
      nombre: v.nombre, direccion: v.direccion, departamento: v.departamento,
      ciudad: v.ciudad, cadena: v.cadena, jerarquia_n2: v.jerarquia_n2,
      jerarquia_n2_2: v.jerarquia_n2_2, nivel_de_alcance: v.nivel_de_alcance,
      latitud: v.latitud, longitud: v.longitud, rif: v.rif, radio: v.radio
    };
    const op = this.editingId()
      ? this.api.updatePoint(this.editingId()!, payload)
      : this.api.createPoint({ id: v.id, ...payload });
    op.subscribe({
      next: () => { this.saving.set(false); this.closePanel(); this.loadAll(); this.snack.open(this.editingId() ? 'PDV actualizado' : 'PDV creado', 'OK', { duration: 3000 }); },
      error: (err) => { this.saving.set(false); this.snack.open(err?.error?.detail ?? 'Error al guardar', 'OK', { duration: 4000 }); }
    });
  }
}
