import { Component, OnInit, OnDestroy, signal, computed, inject, NgZone } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Subject, debounceTime, distinctUntilChanged, forkJoin } from 'rxjs';
import maplibregl from 'maplibre-gl';
import { ApiService } from '../../../core/services/api.service';
import { AuthService } from '../../../core/services/auth.service';
import { PuntoInteres } from '../../../core/models/visita.model';
import { CatalogosComponent } from './catalogos.component';
import { SearchableSelectComponent, SelectOption } from '../../client-visits/searchable-select.component';
import { HasPermDirective } from '../../../core/directives/has-perm.directive';
import { ConfirmService } from '../../../shared/components/confirm-dialog/confirm.service';

@Component({
  selector: 'app-points',
  standalone: true,
  imports: [
    CommonModule, FormsModule, ReactiveFormsModule,
    MatIconModule, MatSnackBarModule, MatProgressSpinnerModule, MatTooltipModule,
    CatalogosComponent, HasPermDirective, SearchableSelectComponent,
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
      <!-- Toggle vista: Catálogos oculto para cliente -->
      <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/5 rounded-xl p-1 flex shadow-sm">
        <button (click)="view.set('pdvs')"
          [class.bg-primary-600]="view() === 'pdvs'" [class.text-white]="view() === 'pdvs'"
          [class.text-slate-500]="view() !== 'pdvs'"
          class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-black transition-all">
          <mat-icon class="!text-base">storefront</mat-icon> PDVs
        </button>
        @if (!isClientePuro()) {
          <button (click)="view.set('catalogos')"
            [class.bg-primary-600]="view() === 'catalogos'" [class.text-white]="view() === 'catalogos'"
            [class.text-slate-500]="view() !== 'catalogos'"
            class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-black transition-all">
            <mat-icon class="!text-base">tune</mat-icon> Catálogos
          </button>
        }
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
      @if (filterRegion() || filterCiudad() || filterJerarquia() || filterJerarquia2() || filterNivelAlcance() || filterCadena() || searchText()) {
        <button (click)="clearFilters()"
          class="ml-auto flex items-center gap-1 text-xs font-bold text-slate-400 hover:text-rose-400 transition-colors">
          <mat-icon class="!text-sm">close</mat-icon> Limpiar
        </button>
      }
    </div>
    <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
      <div class="space-y-1">
        <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Departamento</label>
        <app-searchable-select [options]="regionOpts()" [value]="filterRegion()" icon="public"
          placeholder="Todos" searchPlaceholder="Buscar departamento..." allLabel="Todos"
          (valueChange)="onFilterRegionChange($event)"></app-searchable-select>
      </div>
      <div class="space-y-1">
        <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Ciudad</label>
        <app-searchable-select [options]="ciudadOpts()" [value]="filterCiudad()" icon="location_city"
          placeholder="Todas" searchPlaceholder="Buscar ciudad..." allLabel="Todas"
          (valueChange)="onCiudadChange($event)"></app-searchable-select>
      </div>
      <div class="space-y-1">
        <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Tipo de Negocio</label>
        <app-searchable-select [options]="jerarquiaOpts()" [value]="filterJerarquia()" icon="store"
          placeholder="Todos" searchPlaceholder="Buscar tipo..." allLabel="Todos"
          (valueChange)="onJerarquiaChange($event)"></app-searchable-select>
      </div>
      <div class="space-y-1">
        <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Jerarquía Nivel 2_2</label>
        <app-searchable-select [options]="jerarquia2Opts()" [value]="filterJerarquia2()" icon="account_tree"
          placeholder="Todos" searchPlaceholder="Buscar jerarquía..." allLabel="Todos"
          (valueChange)="onJerarquia2Change($event)"></app-searchable-select>
      </div>
      <div class="space-y-1">
        <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Nivel de Alcance</label>
        <app-searchable-select [options]="nivelAlcanceOpts()" [value]="filterNivelAlcance()" icon="radar"
          placeholder="Todos" searchPlaceholder="Buscar alcance..." allLabel="Todos"
          (valueChange)="onNivelAlcanceChange($event)"></app-searchable-select>
      </div>
      <div class="space-y-1">
        <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Clasificación de Canal</label>
        <app-searchable-select [options]="cadenaOpts()" [value]="filterCadena()" icon="hub"
          placeholder="Todos" searchPlaceholder="Buscar canal..." allLabel="Todos"
          (valueChange)="onCadenaChange($event)"></app-searchable-select>
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
                  <button (click)="openDetails(p)" matTooltip="Detalles"
                    class="w-8 h-8 rounded-lg bg-slate-100 dark:bg-white/5 hover:bg-sky-500 text-slate-500 dark:text-slate-400 hover:text-white inline-flex items-center justify-center transition-all">
                    <mat-icon class="!text-sm">visibility</mat-icon>
                  </button>
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
            <option [value]="20">20 / pág</option>
            <option [value]="50">50 / pág</option>
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
              <div class="flex items-center justify-between">
                <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Identificador *</label>
                @if (!editingId()) {
                  <button type="button" (click)="forceGenerateId()" class="text-[10px] font-bold text-primary-600 hover:text-primary-500 select-none bg-transparent border-none p-0 outline-none cursor-pointer">
                    Autogenerar
                  </button>
                }
              </div>
              <input formControlName="id"
                readonly="true"
                placeholder="Se generará al escribir el nombre..."
                class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-primary-500 rounded-xl px-4 py-2.5 text-sm font-mono font-bold text-slate-900 dark:text-white placeholder-slate-400 outline-none transition-colors opacity-60 cursor-not-allowed"
                [class.border-red-500]="form.get('id')?.invalid && form.get('id')?.touched">
              @if (!editingId()) {
                <p class="text-[10px] text-slate-400">Se genera según la jerarquía del punto</p>
              }
            </div>
            <div class="space-y-1.5">
              <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Nombre del Punto *</label>
              <input formControlName="nombre" placeholder="Nombre del establecimiento"
                class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-primary-500 rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-900 dark:text-white placeholder-slate-400 outline-none transition-colors"
                [class.border-red-500]="form.get('nombre')?.invalid && form.get('nombre')?.touched">
              @if (form.get('nombre')?.invalid && form.get('nombre')?.touched) {
                <p class="text-[11px] text-red-500 font-semibold mt-1">El nombre es obligatorio.</p>
              }
            </div>
          </div>

          <div class="space-y-1.5">
            <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Dirección</label>
            <input formControlName="direccion" placeholder="Dirección completa"
              class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-primary-500 rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-900 dark:text-white placeholder-slate-400 outline-none transition-colors">
          </div>

          <div class="grid grid-cols-2 xl:grid-cols-4 gap-4">
            <div class="space-y-1.5">
              <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Departamento *</label>
              <app-searchable-select [options]="regionOpts()" [value]="form.get('departamento')?.value || ''"
                (valueChange)="form.get('departamento')?.setValue($event)" icon="public"
                placeholder="Seleccionar..." searchPlaceholder="Buscar departamento..." allLabel="Ninguno"
                [class.border-red-500]="form.get('departamento')?.invalid && form.get('departamento')?.touched"></app-searchable-select>
              @if (form.get('departamento')?.invalid && form.get('departamento')?.touched) {
                <p class="text-[11px] text-red-500 font-semibold mt-1">El departamento es obligatorio.</p>
              }
            </div>
            <div class="space-y-1.5">
              <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Ciudad *</label>
              <app-searchable-select [options]="formCiudadOpts()" [value]="form.get('ciudad')?.value || ''"
                (valueChange)="form.get('ciudad')?.setValue($event)" icon="location_city"
                placeholder="Seleccionar..." searchPlaceholder="Buscar ciudad..." allLabel="Ninguno"
                [class.border-red-500]="form.get('ciudad')?.invalid && form.get('ciudad')?.touched"></app-searchable-select>
              @if (form.get('ciudad')?.invalid && form.get('ciudad')?.touched) {
                <p class="text-[11px] text-red-500 font-semibold mt-1">La ciudad es obligatoria.</p>
              }
            </div>
            <div class="space-y-1.5">
              <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Localidad</label>
              <input formControlName="localidad" placeholder="Ej: Centro"
                class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-primary-500 rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-900 dark:text-white placeholder-slate-400 outline-none transition-colors">
            </div>
            <div class="space-y-1.5">
              <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Canal de Venta *</label>
              <app-searchable-select [options]="cadenaOpts()" [value]="form.get('cadena')?.value || ''"
                (valueChange)="form.get('cadena')?.setValue($event)" icon="hub"
                placeholder="Seleccionar..." searchPlaceholder="Buscar canal..." allLabel="Ninguno"
                [class.border-red-500]="form.get('cadena')?.invalid && form.get('cadena')?.touched"></app-searchable-select>
              @if (form.get('cadena')?.invalid && form.get('cadena')?.touched) {
                <p class="text-[11px] text-red-500 font-semibold mt-1">El canal es obligatorio.</p>
              }
            </div>
          </div>

          <div class="grid grid-cols-3 gap-4">
            <div class="space-y-1.5">
              <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Tipo de Negocio *</label>
              <app-searchable-select [options]="jerarquiaOpts()" [value]="form.get('jerarquia_n2')?.value || ''"
                (valueChange)="form.get('jerarquia_n2')?.setValue($event)" icon="store"
                placeholder="Seleccionar..." searchPlaceholder="Buscar tipo..." allLabel="Ninguno"
                [class.border-red-500]="form.get('jerarquia_n2')?.invalid && form.get('jerarquia_n2')?.touched"></app-searchable-select>
              @if (form.get('jerarquia_n2')?.invalid && form.get('jerarquia_n2')?.touched) {
                <p class="text-[11px] text-red-500 font-semibold mt-1">El tipo de negocio es obligatorio.</p>
              }
            </div>
            <div class="space-y-1.5">
              <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Subtipo de Negocio *</label>
              <app-searchable-select [options]="jerarquia2Opts()" [value]="form.get('jerarquia_n2_2')?.value || ''"
                (valueChange)="form.get('jerarquia_n2_2')?.setValue($event)" icon="account_tree"
                placeholder="Seleccionar..." searchPlaceholder="Buscar subtipo..." allLabel="Ninguno"
                [class.border-red-500]="form.get('jerarquia_n2_2')?.invalid && form.get('jerarquia_n2_2')?.touched"></app-searchable-select>
              @if (form.get('jerarquia_n2_2')?.invalid && form.get('jerarquia_n2_2')?.touched) {
                <p class="text-[11px] text-red-500 font-semibold mt-1">El subtipo de negocio es obligatorio.</p>
              }
            </div>
            <div class="space-y-1.5">
              <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Alcance *</label>
              <app-searchable-select [options]="nivelAlcanceOpts()" [value]="form.get('nivel_de_alcance')?.value || ''"
                (valueChange)="form.get('nivel_de_alcance')?.setValue($event)" icon="radar"
                placeholder="Seleccionar..." searchPlaceholder="Buscar alcance..." allLabel="Ninguno"
                [class.border-red-500]="form.get('nivel_de_alcance')?.invalid && form.get('nivel_de_alcance')?.touched"></app-searchable-select>
              @if (form.get('nivel_de_alcance')?.invalid && form.get('nivel_de_alcance')?.touched) {
                <p class="text-[11px] text-red-500 font-semibold mt-1">El alcance es obligatorio.</p>
              }
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-1.5">
              <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">RIF</label>
              <input formControlName="rif" placeholder="Ej: J-12345678-9"
                class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-primary-500 rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-900 dark:text-white placeholder-slate-400 outline-none transition-colors">
            </div>
            <div class="space-y-1.5">
              <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Radio (metros) *</label>
              <input formControlName="radio" placeholder="100" type="number"
                class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-primary-500 rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-900 dark:text-white placeholder-slate-400 outline-none transition-colors"
                [class.border-red-500]="form.get('radio')?.invalid && form.get('radio')?.touched">
              @if (form.get('radio')?.invalid && form.get('radio')?.touched) {
                <p class="text-[11px] text-red-500 font-semibold mt-1">
                  @if (form.get('radio')?.errors?.['required']) { El radio es obligatorio. }
                  @else { Debe ser un número mayor o igual a 1. }
                </p>
              }
            </div>
          </div>

          <!-- COORDENADAS + MAPA -->
          <div class="space-y-3">
            <div class="grid grid-cols-2 gap-4">
              <div class="space-y-1.5">
                <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Latitud *</label>
                <input formControlName="latitud" placeholder="Ej: 10.481910" (change)="syncMapCenter()"
                  class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-primary-500 rounded-xl px-4 py-2.5 text-sm font-mono font-semibold text-slate-900 dark:text-white placeholder-slate-400 outline-none transition-colors"
                  [class.border-red-500]="form.get('latitud')?.invalid && form.get('latitud')?.touched">
                @if (form.get('latitud')?.invalid && form.get('latitud')?.touched) {
                  <p class="text-[11px] text-red-500 font-semibold mt-1">
                    @if (form.get('latitud')?.errors?.['required']) { La latitud es obligatoria. }
                    @else { Debe ser un número válido (ej: 10.48). }
                  </p>
                }
              </div>
              <div class="space-y-1.5">
                <label class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Longitud *</label>
                <input formControlName="longitud" placeholder="Ej: -66.903606" (change)="syncMapCenter()"
                  class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-primary-500 rounded-xl px-4 py-2.5 text-sm font-mono font-semibold text-slate-900 dark:text-white placeholder-slate-400 outline-none transition-colors"
                  [class.border-red-500]="form.get('longitud')?.invalid && form.get('longitud')?.touched">
                @if (form.get('longitud')?.invalid && form.get('longitud')?.touched) {
                  <p class="text-[11px] text-red-500 font-semibold mt-1">
                    @if (form.get('longitud')?.errors?.['required']) { La longitud es obligatoria. }
                    @else { Debe ser un número válido (ej: -66.90). }
                  </p>
                }
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

<!-- DETALLES MODAL -->
@if (detailsOpen() && detailPoint()) {
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" (click)="closeDetails()"></div>
    <div class="relative w-full max-w-lg bg-white dark:bg-slate-900 rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
      <div class="bg-gradient-to-r from-primary-700 to-indigo-600 px-6 py-5 flex items-center justify-between shrink-0">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-white/15 flex items-center justify-center">
            <mat-icon class="text-white !text-xl">storefront</mat-icon>
          </div>
          <div>
            <h3 class="font-black text-white">{{ detailPoint()!.nombre || 'Detalle del PDV' }}</h3>
            <p class="text-xs text-white/70 font-mono">{{ detailPoint()!.id }}</p>
          </div>
        </div>
        <button (click)="closeDetails()"
          class="w-9 h-9 rounded-xl bg-white/15 hover:bg-white/25 flex items-center justify-center text-white transition-all">
          <mat-icon class="!text-lg">close</mat-icon>
        </button>
      </div>

      <div class="flex-1 overflow-y-auto px-6 py-5">
        <div class="grid grid-cols-2 gap-3">
          <div class="space-y-1 bg-slate-50 dark:bg-slate-800 rounded-xl px-3 py-2.5">
            <span class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Dirección</span>
            <p class="text-sm font-semibold text-slate-800 dark:text-white">{{ detailPoint()!.direccion || '—' }}</p>
          </div>
          <div class="space-y-1 bg-slate-50 dark:bg-slate-800 rounded-xl px-3 py-2.5">
            <span class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Dpto / Ciudad</span>
            <p class="text-sm font-semibold text-slate-800 dark:text-white">{{ detailPoint()!.departamento || '—' }} / {{ detailPoint()!.ciudad || '—' }}</p>
          </div>
          <div class="space-y-1 bg-slate-50 dark:bg-slate-800 rounded-xl px-3 py-2.5">
            <span class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Tipo de Negocio</span>
            <p class="text-sm font-semibold text-slate-800 dark:text-white">{{ detailPoint()!.jerarquia_n2 || '—' }}</p>
          </div>
          <div class="space-y-1 bg-slate-50 dark:bg-slate-800 rounded-xl px-3 py-2.5">
            <span class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Subtipo</span>
            <p class="text-sm font-semibold text-slate-800 dark:text-white">{{ detailPoint()!.jerarquia_n2_2 || '—' }}</p>
          </div>
          <div class="space-y-1 bg-slate-50 dark:bg-slate-800 rounded-xl px-3 py-2.5">
            <span class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Canal</span>
            <p class="text-sm font-semibold text-slate-800 dark:text-white">{{ detailPoint()!.cadena || '—' }}</p>
          </div>
          <div class="space-y-1 bg-slate-50 dark:bg-slate-800 rounded-xl px-3 py-2.5">
            <span class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Alcance</span>
            <p class="text-sm font-semibold text-slate-800 dark:text-white">{{ detailPoint()!.nivel_de_alcance || '—' }}</p>
          </div>
          <div class="space-y-1 bg-slate-50 dark:bg-slate-800 rounded-xl px-3 py-2.5">
            <span class="text-[10px] font-black text-slate-400 uppercase tracking-widest">RIF</span>
            <p class="text-sm font-semibold text-slate-800 dark:text-white">{{ detailPoint()!.rif || '—' }}</p>
          </div>
          <div class="space-y-1 bg-slate-50 dark:bg-slate-800 rounded-xl px-3 py-2.5">
            <span class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Radio (m)</span>
            <p class="text-sm font-semibold text-slate-800 dark:text-white">{{ detailPoint()!.radio || '—' }}</p>
          </div>
          <div class="space-y-1 bg-slate-50 dark:bg-slate-800 rounded-xl px-3 py-2.5 col-span-2">
            <span class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Coordenadas</span>
            <p class="text-sm font-mono font-semibold text-slate-800 dark:text-white">
              @if (detailPoint()!.latitud && detailPoint()!.longitud) {
                {{ detailPoint()!.latitud }}, {{ detailPoint()!.longitud }}
              } @else { Sin coordenadas }
            </p>
          </div>
        </div>

        <div class="relative mt-3">
          @if (mapTileInfo()) {
            <div class="rounded-xl overflow-hidden border border-slate-200 dark:border-slate-700 relative group bg-slate-200 dark:bg-slate-800" style="height:260px">
              <div class="absolute left-1/2 top-1/2" style="transform: translate(-50%, -50%);">
                <div [style.transform]="'translate(' + mapTileInfo()!.ox + 'px,' + mapTileInfo()!.oy + 'px)'"
                  style="width:768px;height:768px;">
                  <div class="grid grid-cols-3" style="width:768px;height:768px;">
                    @for (row of tileRows; track row) {
                      @for (col of tileRows; track col) {
                        <img [src]="tileSrc(mapTileInfo()!.x + col - 1, mapTileInfo()!.y + row - 1)"
                          alt="" class="block" style="width:256px;height:256px;" draggable="false"
                          referrerpolicy="no-referrer-when-downgrade">
                      }
                    }
                  </div>
                </div>
              </div>
              <div class="absolute inset-0 pointer-events-none flex items-center justify-center">
                <mat-icon class="!text-4xl text-rose-600" style="filter: drop-shadow(0 2px 3px rgba(0,0,0,.5));">location_on</mat-icon>
              </div>
              <div class="absolute inset-0 cursor-pointer" (click)="openInGoogleMaps()" matTooltip="Abrir en Google Maps"></div>
              <div class="absolute bottom-2 right-2 flex items-center gap-1.5 bg-white/90 dark:bg-slate-900/90 backdrop-blur text-[11px] font-bold text-slate-700 dark:text-slate-200 px-2.5 py-1.5 rounded-lg shadow pointer-events-none">
                <mat-icon class="!text-sm">open_in_new</mat-icon> Google Maps
              </div>
            </div>
          } @else {
            <div class="rounded-xl overflow-hidden border border-slate-200 dark:border-slate-700 relative flex flex-col items-center justify-center gap-2 bg-slate-100 dark:bg-slate-800 text-slate-400" style="height:160px">
              <mat-icon class="!text-4xl">location_off</mat-icon>
              <span class="text-sm font-semibold">Sin coordenadas</span>
            </div>
          }
        </div>
      </div>

      <div class="px-6 py-4 border-t border-slate-200 dark:border-white/8 shrink-0 flex gap-3">
        <button type="button" (click)="closeDetails()"
          class="flex-1 py-2.5 border border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white rounded-xl font-bold text-sm transition-all">
          Cerrar
        </button>
        <button type="button" *hasPerm="'points'; action:'write'" (click)="editFromDetails()"
          class="flex-1 flex items-center justify-center gap-2 py-2.5 bg-primary-600 hover:bg-primary-500 text-white font-black rounded-xl text-sm shadow-lg transition-all active:scale-95">
          <mat-icon class="!text-base">edit</mat-icon>
          Editar
        </button>
      </div>
    </div>
  </div>
}
  `
})
export class PointsComponent implements OnInit, OnDestroy {
  private api = inject(ApiService);
  private auth = inject(AuthService);
  private snack = inject(MatSnackBar);
  private fb = inject(FormBuilder);
  private confirmSvc = inject(ConfirmService);
  private ngZone = inject(NgZone);

  /** El usuario es cliente puro (id_rol=1): solo lectura, sin catálogos, sin coordenadas */
  isClientePuro = signal(false);

  view = signal<'pdvs' | 'catalogos'>('pdvs');
  loading = signal(false);
  saving = signal(false);
  panelOpen = signal(false);
  editingId = signal<string | null>(null);
  detailsOpen = signal(false);
  detailPoint = signal<PuntoInteres | null>(null);

  points = signal<PuntoInteres[]>([]);
  total = signal(0);
  skip = signal(0);
  pageSize = signal(20);

  regions = signal<string[]>([]);
  filterCities = signal<string[]>([]);
  formCities = signal<string[]>([]);
  chains = signal<string[]>([]);
  jerarquias = signal<string[]>([]);
  jerarquias2 = signal<string[]>([]);
  nivelesAlcance = signal<string[]>([]);

  filterRegion = signal('');
  filterCiudad = signal('');
  filterJerarquia = signal('');
  filterJerarquia2 = signal('');
  filterNivelAlcance = signal('');
  filterCadena = signal('');
  searchText = signal('');

  regionOpts = computed<SelectOption[]>(() => this.regions().map(r => ({ value: r, label: r })));
  ciudadOpts = computed<SelectOption[]>(() => this.filterCities().map(c => ({ value: c, label: c })));
  jerarquiaOpts = computed<SelectOption[]>(() => this.jerarquias().map(j => ({ value: j, label: j })));
  jerarquia2Opts = computed<SelectOption[]>(() => this.jerarquias2().map(j => ({ value: j, label: j })));
  nivelAlcanceOpts = computed<SelectOption[]>(() => this.nivelesAlcance().map(n => ({ value: n, label: n })));
  cadenaOpts = computed<SelectOption[]>(() => this.chains().map(c => ({ value: c, label: c })));
  formCiudadOpts = computed<SelectOption[]>(() => this.formCities().map(c => ({ value: c, label: c })));

  private search$ = new Subject<string>();
  private mapInstance: maplibregl.Map | null = null;
  private mapMarker: maplibregl.Marker | null = null;

  readonly tileRows = [0, 1, 2];
  mapTileInfo = signal<{ x: number; y: number; z: number; ox: number; oy: number } | null>(null);

  form = this.fb.group({
    id: ['', Validators.required],
    nombre: ['', Validators.required],
    direccion: [''],
    departamento: [''],
    ciudad: [''],
    localidad: [''],
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
    console.log('[PointsComponent] ngOnInit initialized. User is client pure:', this.auth.currentUser()?.id_rol === 1);
    this.isClientePuro.set(this.auth.currentUser()?.id_rol === 1);
    this.loadAll();
    this.loadDropdowns();
    this.search$.pipe(debounceTime(350), distinctUntilChanged()).subscribe((q) => {
      console.log('[PointsComponent] Search triggered:', q);
      this.skip.set(0); this.reload();
    });

    // Al cambiar departamento en el form, recargar ciudades de ese departamento
    this.form.get('departamento')?.valueChanges.pipe(
      debounceTime(200),
      distinctUntilChanged()
    ).subscribe((dep) => {
      const depStr = typeof dep === 'string' ? dep.trim() : '';
      console.log('[PointsComponent] Form departamento changed:', depStr);
      if (!depStr) {
        this.formCities.set([]);
        return;
      }
      this.api.getCities(depStr).subscribe({
        next: d => {
          const list = Array.isArray(d) ? d.filter(x => typeof x === 'string') : [];
          console.log('[PointsComponent] Form cities updated:', list.length);
          this.formCities.set(list);
        },
        error: (err) => console.error('[PointsComponent] Error fetching form cities:', err)
      });
    });

    // Al cambiar el nombre del punto, autogenerar el identificador si estamos creando uno nuevo
    this.form.get('nombre')?.valueChanges.pipe(
      debounceTime(400),
      distinctUntilChanged()
    ).subscribe((name) => {
      const nameStr = typeof name === 'string' ? name.trim() : '';
      if (!this.editingId() && nameStr && nameStr.length >= 3) {
        const currentId = this.form.get('id')?.value?.trim();
        if (!currentId) {
          this.api.generatePointId(nameStr).subscribe({
            next: (res) => {
              if (res && res.id) {
                this.form.patchValue({ id: res.id });
              }
            },
            error: (err) => console.error('[PointsComponent] Error generating point ID:', err)
          });
        }
      }
    });
  }

  ngOnDestroy(): void {
    console.log('[PointsComponent] ngOnDestroy - destroying map');
    this.destroyMap();
  }

  private filterParams() {
    return {
      region: this.filterRegion() || undefined,
      ciudad: this.filterCiudad() || undefined,
      jerarquia_n2: this.filterJerarquia() || undefined,
      jerarquia_n2_2: this.filterJerarquia2() || undefined,
      nivel_de_alcance: this.filterNivelAlcance() || undefined,
      cadena: this.filterCadena() || undefined,
      search: this.searchText() || undefined,
    };
  }

  loadAll(): void {
    const params = this.filterParams();
    console.log('[PointsComponent] loadAll called with params:', params, 'skip:', this.skip(), 'limit:', this.pageSize());
    this.loading.set(true);
    forkJoin({
      items: this.api.getPoints({ ...params, skip: this.skip(), limit: this.pageSize() }),
      count: this.api.getPointsCount(params)
    }).subscribe({
      next: ({ items, count }) => {
        console.log('[PointsComponent] loadAll success. Received items:', items?.length, 'total count:', count?.total);
        this.points.set(items || []);
        this.total.set(count?.total || 0);
        this.loading.set(false);
      },
      error: (err) => {
        console.error('[PointsComponent] loadAll error:', err);
        this.loading.set(false);
      }
    });
  }

  reload(): void {
    console.log('[PointsComponent] reload - resetting skip to 0');
    this.skip.set(0);
    this.loadAll();
  }

  loadDropdowns(): void {
    console.log('[PointsComponent] loadDropdowns called');
    this.api.getRegions().subscribe({
      next: d => { console.log('[PointsComponent] Regions loaded:', d?.length); this.regions.set(d || []); },
      error: err => console.error('[PointsComponent] Error loading regions:', err)
    });
    this.api.getCities(this.filterRegion() || undefined).subscribe({
      next: d => { console.log('[PointsComponent] Cities loaded:', d?.length); this.filterCities.set(d || []); },
      error: err => console.error('[PointsComponent] Error loading cities:', err)
    });
    this.api.getChains().subscribe({
      next: d => { console.log('[PointsComponent] Chains loaded:', d?.length); this.chains.set(d || []); },
      error: err => console.error('[PointsComponent] Error loading chains:', err)
    });
    this.api.getJerarquiaN2().subscribe({
      next: d => { console.log('[PointsComponent] JerarquiaN2 loaded:', d?.length); this.jerarquias.set(d || []); },
      error: err => console.error('[PointsComponent] Error loading JerarquiaN2:', err)
    });
    this.api.getJerarquiaN2_2().subscribe({
      next: d => { console.log('[PointsComponent] JerarquiaN2_2 loaded:', d?.length); this.jerarquias2.set(d || []); },
      error: err => console.error('[PointsComponent] Error loading JerarquiaN2_2:', err)
    });
    this.api.getNivelesAlcance().subscribe({
      next: d => { console.log('[PointsComponent] NivelesAlcance loaded:', d?.length); this.nivelesAlcance.set(d || []); },
      error: err => console.error('[PointsComponent] Error loading NivelesAlcance:', err)
    });
  }

  onSearch(val: string): void { this.searchText.set(val); this.search$.next(val); }
  onFilterRegionChange(val: string): void {
    console.log('[PointsComponent] Filter region changed:', val);
    this.filterRegion.set(val);
    this.filterCiudad.set('');
    this.api.getCities(val || undefined).subscribe({ next: d => this.filterCities.set(d || []), error: () => { } });
    this.reload();
  }
  onCiudadChange(val: string): void { console.log('[PointsComponent] Filter city changed:', val); this.filterCiudad.set(val); this.reload(); }
  onJerarquiaChange(val: string): void { console.log('[PointsComponent] Filter jerarquia changed:', val); this.filterJerarquia.set(val); this.reload(); }
  onJerarquia2Change(val: string): void { console.log('[PointsComponent] Filter jerarquia2 changed:', val); this.filterJerarquia2.set(val); this.reload(); }
  onNivelAlcanceChange(val: string): void { console.log('[PointsComponent] Filter nivelAlcance changed:', val); this.filterNivelAlcance.set(val); this.reload(); }
  onCadenaChange(val: string): void { console.log('[PointsComponent] Filter cadena changed:', val); this.filterCadena.set(val); this.reload(); }
  clearFilters(): void {
    console.log('[PointsComponent] Clearing all filters');
    this.filterRegion.set(''); this.filterCiudad.set(''); this.filterJerarquia.set('');
    this.filterJerarquia2.set(''); this.filterNivelAlcance.set(''); this.filterCadena.set('');
    this.searchText.set('');
    this.api.getCities().subscribe({ next: d => this.filterCities.set(d || []), error: () => { } });
    this.reload();
  }
  prevPage(): void { this.skip.update(v => Math.max(0, v - this.pageSize())); this.loadAll(); }
  nextPage(): void { this.skip.update(v => v + this.pageSize()); this.loadAll(); }
  onPageSizeChange(size: number): void { this.pageSize.set(+size); this.skip.set(0); this.loadAll(); }
  forceGenerateId(): void {
    const name = this.form.get('nombre')?.value?.trim() || '';
    if (!name) {
      this.snack.open('Primero escribe el nombre del punto', 'OK', { duration: 2500 });
      return;
    }
    this.api.generatePointId(name).subscribe({
      next: (res) => {
        if (res && res.id) {
          this.form.patchValue({ id: res.id });
          this.snack.open('Identificador generado', 'OK', { duration: 2000 });
        }
      },
      error: (err) => {
        console.error('[PointsComponent] Error generating point ID:', err);
        this.snack.open('Error al generar el identificador', 'OK', { duration: 3000 });
      }
    });
  }

  openPanel(p: PuntoInteres | null): void {
    console.log('[PointsComponent] openPanel called. Point:', p);
    this.editingId.set(p?.id ?? null);
    this.form.reset({
      id: p?.id ?? '', nombre: p?.nombre ?? '', direccion: p?.direccion ?? '',
      departamento: p?.departamento ?? '', ciudad: p?.ciudad ?? '', localidad: p?.localidad ?? '',
      cadena: p?.cadena ?? '',
      jerarquia_n2: p?.jerarquia_n2 ?? '', jerarquia_n2_2: p?.jerarquia_n2_2 ?? '',
      nivel_de_alcance: p?.nivel_de_alcance ?? '', latitud: p?.latitud ?? '',
      longitud: p?.longitud ?? '', rif: p?.rif ?? '', radio: p?.radio ?? ''
    });
    this.panelOpen.set(true);
    setTimeout(() => this.initMap(), 250);
  }

  closePanel(): void {
    console.log('[PointsComponent] closePanel called');
    try { this.destroyMap(); } catch (e) { console.warn('[PointsComponent] Error in destroyMap catch:', e); this.mapInstance = null; this.mapMarker = null; }
    this.editingId.set(null);
    this.panelOpen.set(false);
  }

  openDetails(p: PuntoInteres): void {
    console.log('[PointsComponent] openDetails called. Point:', p);
    this.detailPoint.set(p);
    this.detailsOpen.set(true);
    this.buildMapTiles();
  }

  private buildMapTiles(): void {
    const p = this.detailPoint();
    const latStr = this.normCoord(p?.latitud);
    const lngStr = this.normCoord(p?.longitud);
    if (!latStr || !lngStr || isNaN(+latStr) || isNaN(+lngStr)) {
      console.log('[PointsComponent] buildMapTiles - No valid coords for details point');
      this.mapTileInfo.set(null);
      return;
    }
    const lat = +latStr;
    const lng = +lngStr;
    const z = 14;
    const n = Math.pow(2, z);
    const xt = ((lng + 180) / 360) * n;
    const latRad = (lat * Math.PI) / 180;
    const yt = ((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2) * n;
    const x = Math.floor(xt);
    const y = Math.floor(yt);
    const fx = xt - x;
    const fy = yt - y;
    this.mapTileInfo.set({ x, y, z, ox: 128 - fx * 256, oy: 128 - fy * 256 });
  }

  tileSrc(x: number, y: number): string {
    const z = this.mapTileInfo()?.z ?? 14;
    return `https://tile.openstreetmap.org/${z}/${x}/${y}.png`;
  }

  private normCoord(v: string | number | undefined | null): string {
    return ((v ?? '').toString().trim()).replace(',', '.');
  }

  openInGoogleMaps(): void {
    const p = this.detailPoint();
    const lat = this.normCoord(p?.latitud);
    const lng = this.normCoord(p?.longitud);
    if (!lat || !lng || isNaN(+lat) || isNaN(+lng)) return;
    const url = `https://www.google.com/maps?q=${lat},${lng}`;
    window.open(url, '_blank', 'noopener');
  }

  closeDetails(): void {
    console.log('[PointsComponent] closeDetails called');
    this.detailPoint.set(null);
    this.detailsOpen.set(false);
  }

  editFromDetails(): void {
    const p = this.detailPoint();
    console.log('[PointsComponent] editFromDetails called. Point:', p);
    this.closeDetails();
    if (p) {
      this.openPanel(p);
    }
  }

  initMap(): void {
    if (!this.panelOpen()) {
      console.log('[PointsComponent] initMap skipped - panel not open');
      return;
    }
    const el = document.getElementById('punto-map');
    if (!el) {
      console.warn('[PointsComponent] initMap skipped - #punto-map container element not found in DOM');
      return;
    }
    this.destroyMap();

    const latStr = this.normCoord(this.form.get('latitud')?.value as string);
    const lngStr = this.normCoord(this.form.get('longitud')?.value as string);
    const hasCoords = latStr !== '' && lngStr !== '' && !isNaN(+latStr) && !isNaN(+lngStr);
    const lat = hasCoords ? +latStr : 10.48;
    const lng = hasCoords ? +lngStr : -66.90;
    const nombre = this.form.get('nombre')?.value || 'PDV';

    console.log('[PointsComponent] initMap starting for container #punto-map. Coords:', { lat, lng, hasCoords });

    this.ngZone.runOutsideAngular(() => {
      try {
        this.mapInstance = new maplibregl.Map({
          container: el,
          style: {
            version: 8,
            sources: {
              'osm-tiles': {
                type: 'raster',
                tiles: [
                  'https://a.tile.openstreetmap.org/{z}/{x}/{y}.png',
                  'https://b.tile.openstreetmap.org/{z}/{x}/{y}.png',
                  'https://c.tile.openstreetmap.org/{z}/{x}/{y}.png'
                ],
                tileSize: 256,
                attribution: 'OpenStreetMap'
              }
            },
            layers: [
              {
                id: 'osm-tiles-layer',
                type: 'raster',
                source: 'osm-tiles',
                minzoom: 0,
                maxzoom: 19
              }
            ]
          },
          center: [lng, lat],
          zoom: hasCoords ? 15 : 7,
          scrollZoom: false,
          cooperativeGestures: true
        });

        this.mapInstance.on('error', (err) => {
          console.warn('[PointsComponent] MapLibre suppressed error:', err);
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
          console.log('[PointsComponent] Map clicked. Selected coords:', { newLat, newLng });

          this.ngZone.run(() => {
            this.form.patchValue({ latitud: newLat, longitud: newLng });
          });

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
        console.log('[PointsComponent] MapLibre instance created successfully.');
      } catch (err) {
        console.error('[PointsComponent] initMap catch block ERROR:', err);
        this.mapInstance = null;
        this.mapMarker = null;
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
    console.log('[PointsComponent] syncMapCenter called with coords:', { latStr, lngStr });
    if (!this.mapInstance || !latStr || !lngStr || isNaN(+latStr) || isNaN(+lngStr)) return;
    const lat = +latStr;
    const lng = +lngStr;
    const nombre = this.form.get('nombre')?.value || 'PDV';
    this.ngZone.runOutsideAngular(() => {
      try {
        this.mapInstance!.flyTo({ center: [lng, lat], zoom: 15, duration: 800 });
        if (this.mapMarker) {
          this.mapMarker.setLngLat([lng, lat]);
          this.mapMarker.getPopup()?.setHTML(this.popupHtml(nombre, latStr, lngStr));
        } else {
          const popup = new maplibregl.Popup({ offset: 42, closeButton: false })
            .setHTML(this.popupHtml(nombre, latStr, lngStr));
          this.mapMarker = new maplibregl.Marker({ color: '#7c3aed', scale: 1.2 })
            .setLngLat([lng, lat])
            .setPopup(popup)
            .addTo(this.mapInstance!);
          this.mapMarker.togglePopup();
        }
      } catch (e) {
        console.warn('[PointsComponent] syncMapCenter failed:', e);
      }
    });
  }

  destroyMap(): void {
    if (this.mapInstance) {
      console.log('[PointsComponent] destroyMap - removing map instance');
      this.ngZone.runOutsideAngular(() => {
        try {
          this.mapInstance?.remove();
        } catch (e) {
          console.warn('[PointsComponent] Error removing map instance:', e);
        } finally {
          this.mapInstance = null;
          this.mapMarker = null;
        }
      });
    }
  }

  async deletePoint(p: PuntoInteres): Promise<void> {
    console.log('[PointsComponent] deletePoint called for point:', p);
    const ok = await this.confirmSvc.confirm(`¿Eliminar "${p.nombre || p.id}"? Esta acción no se puede deshacer.`, {
      title: 'Eliminar punto de venta', confirmText: 'Eliminar', cancelText: 'Cancelar', danger: true,
    });
    if (!ok) return;
    this.api.deletePoint(p.id).subscribe({
      next: () => {
        console.log('[PointsComponent] deletePoint success');
        this.loadAll();
        this.snack.open('PDV eliminado', 'OK', { duration: 3000 });
      },
      error: (err) => {
        console.error('[PointsComponent] deletePoint error:', err);
        this.snack.open(err?.error?.detail ?? 'Error al eliminar', 'OK', { duration: 4000 });
      }
    });
  }

  save(): void {
    console.log('[PointsComponent] save called. Form valid:', this.form.valid, 'Form value:', this.form.value);
    if (this.form.invalid) {
      console.warn('[PointsComponent] save blocked - form is invalid');
      this.form.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    const v = this.form.value;
    const payload = {
      nombre: v.nombre, direccion: v.direccion, departamento: v.departamento,
      ciudad: v.ciudad, localidad: v.localidad, cadena: v.cadena, jerarquia_n2: v.jerarquia_n2,
      jerarquia_n2_2: v.jerarquia_n2_2, nivel_de_alcance: v.nivel_de_alcance,
      latitud: v.latitud, longitud: v.longitud, rif: v.rif, radio: v.radio
    };
    const op = this.editingId()
      ? this.api.updatePoint(this.editingId()!, payload)
      : this.api.createPoint({ id: v.id, ...payload });
    console.log('[PointsComponent] Sending save API call. EditingId:', this.editingId(), 'Payload:', payload);
    op.subscribe({
      next: (res) => {
        console.log('[PointsComponent] save success response:', res);
        this.saving.set(false);
        this.closePanel();
        this.loadAll();
        this.snack.open(this.editingId() ? 'PDV actualizado' : 'PDV creado', 'OK', { duration: 3000 });
      },
      error: (err) => {
        console.error('[PointsComponent] save error response:', err);
        this.saving.set(false);
        this.snack.open(err?.error?.detail ?? 'Error al guardar', 'OK', { duration: 4000 });
      }
    });
  }
}
