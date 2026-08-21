import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { ConfirmService } from '../../shared/components/confirm-dialog/confirm.service';

export interface CatalogoItem {
  id: number;
  tipo: 'especialidad' | 'subespecialidad' | 'universidad' | 'estado' | 'ciudad';
  nombre: string;
  creado_por: string;
  creado_en?: string | null;
  modificado_en?: string | null;
  medicos_count: number;
}

@Component({
  selector: 'app-configuracion-encuestador',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  template: `
    <div class="p-6 max-w-7xl mx-auto space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      <!-- Top Header & Breadcrumb -->
      <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 p-6 rounded-3xl shadow-sm">
        <div>
          <div class="flex items-center gap-2 mb-1">
            <span class="bg-indigo-50 dark:bg-indigo-950/80 text-indigo-600 dark:text-indigo-400 text-[10px] font-black uppercase tracking-widest px-2.5 py-0.5 rounded-full">
              Módulo Encuestador
            </span>
            <span class="text-xs text-slate-400 dark:text-slate-500 font-semibold">· Gestión Global</span>
          </div>
          <h1 class="text-2xl sm:text-3xl font-black text-slate-800 dark:text-white tracking-tight flex items-center gap-3">
            <span class="w-10 h-10 rounded-2xl bg-indigo-600 text-white flex items-center justify-center shadow-lg shadow-indigo-500/25">
              <span class="material-icons text-xl">dataset</span>
            </span>
            Catálogos y Parámetros
          </h1>
          <p class="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
            Administra especialidades, sub-especialidades, universidades, estados y ciudades para las encuestas.
          </p>
        </div>

        <div class="flex items-center gap-3 w-full sm:w-auto">
          <button (click)="openAddModal()" class="flex-1 sm:flex-none flex items-center justify-center gap-2 px-5 py-2.5 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-700 hover:to-indigo-600 text-white text-xs sm:text-sm font-bold rounded-2xl transition-all shadow-lg shadow-indigo-600/20 active:scale-95">
            <span class="material-icons text-base">add_circle</span>
            Nuevo Ítem
          </button>
          <button routerLink="/encuestador/dashboard" class="flex items-center justify-center gap-2 px-4 py-2.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs sm:text-sm font-bold rounded-2xl transition-all active:scale-95">
            <span class="material-icons text-base">arrow_back</span>
            Volver
          </button>
        </div>
      </div>

      <!-- Quick Metrics Summary Cards -->
      <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4">
        <!-- Total -->
        <div (click)="selectedTipo = 'todos'" [class.ring-2]="selectedTipo === 'todos'" class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-2xl p-4 shadow-sm cursor-pointer hover:shadow-md transition-all ring-indigo-500 group">
          <div class="flex items-center justify-between text-slate-400 mb-1">
            <span class="text-[10px] font-black uppercase tracking-wider">Total Ítems</span>
            <span class="material-icons text-slate-400 group-hover:text-indigo-500 text-base transition-colors">apps</span>
          </div>
          <div class="text-2xl font-black text-slate-800 dark:text-white">{{ items.length }}</div>
        </div>

        <!-- Especialidades -->
        <div (click)="selectedTipo = 'especialidad'" [class.ring-2]="selectedTipo === 'especialidad'" class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-2xl p-4 shadow-sm cursor-pointer hover:shadow-md transition-all ring-purple-500 group">
          <div class="flex items-center justify-between text-purple-600 dark:text-purple-400 mb-1">
            <span class="text-[10px] font-black uppercase tracking-wider">Especialidades</span>
            <span class="material-icons text-purple-500 text-base">psychology</span>
          </div>
          <div class="text-2xl font-black text-slate-800 dark:text-white">{{ countByTipo('especialidad') }}</div>
        </div>

        <!-- Subespecialidades -->
        <div (click)="selectedTipo = 'subespecialidad'" [class.ring-2]="selectedTipo === 'subespecialidad'" class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-2xl p-4 shadow-sm cursor-pointer hover:shadow-md transition-all ring-cyan-500 group">
          <div class="flex items-center justify-between text-cyan-600 dark:text-cyan-400 mb-1">
            <span class="text-[10px] font-black uppercase tracking-wider">Sub-especialidad</span>
            <span class="material-icons text-cyan-500 text-base">biotech</span>
          </div>
          <div class="text-2xl font-black text-slate-800 dark:text-white">{{ countByTipo('subespecialidad') }}</div>
        </div>

        <!-- Universidades -->
        <div (click)="selectedTipo = 'universidad'" [class.ring-2]="selectedTipo === 'universidad'" class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-2xl p-4 shadow-sm cursor-pointer hover:shadow-md transition-all ring-emerald-500 group">
          <div class="flex items-center justify-between text-emerald-600 dark:text-emerald-400 mb-1">
            <span class="text-[10px] font-black uppercase tracking-wider">Universidades</span>
            <span class="material-icons text-emerald-500 text-base">school</span>
          </div>
          <div class="text-2xl font-black text-slate-800 dark:text-white">{{ countByTipo('universidad') }}</div>
        </div>

        <!-- Estados -->
        <div (click)="selectedTipo = 'estado'" [class.ring-2]="selectedTipo === 'estado'" class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-2xl p-4 shadow-sm cursor-pointer hover:shadow-md transition-all ring-amber-500 group">
          <div class="flex items-center justify-between text-amber-600 dark:text-amber-400 mb-1">
            <span class="text-[10px] font-black uppercase tracking-wider">Estados</span>
            <span class="material-icons text-amber-500 text-base">map</span>
          </div>
          <div class="text-2xl font-black text-slate-800 dark:text-white">{{ countByTipo('estado') }}</div>
        </div>

        <!-- Ciudades -->
        <div (click)="selectedTipo = 'ciudad'" [class.ring-2]="selectedTipo === 'ciudad'" class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-2xl p-4 shadow-sm cursor-pointer hover:shadow-md transition-all ring-blue-500 group">
          <div class="flex items-center justify-between text-blue-600 dark:text-blue-400 mb-1">
            <span class="text-[10px] font-black uppercase tracking-wider">Ciudades</span>
            <span class="material-icons text-blue-500 text-base">location_city</span>
          </div>
          <div class="text-2xl font-black text-slate-800 dark:text-white">{{ countByTipo('ciudad') }}</div>
        </div>
      </div>

      <!-- Valores huérfanos: ya están en fichas de médicos pero nunca tuvieron
           fila propia en el catálogo (ej. "Distrito capiral", un typo que entró
           por texto libre antes de este fix) -- por eso el BI puede mostrar más
           valores de los que aparecen acá abajo. Solo se muestra si hay algo. -->
      <div *ngIf="huerfanos.length > 0" class="bg-amber-50 dark:bg-amber-950/25 border border-amber-200 dark:border-amber-900/50 rounded-3xl p-5 shadow-sm space-y-3">
        <div class="flex items-center gap-2">
          <span class="material-icons text-amber-500">warning_amber</span>
          <h3 class="text-sm font-black text-amber-800 dark:text-amber-300">Valores sin catalogar ({{ huerfanos.length }})</h3>
        </div>
        <p class="text-xs text-amber-700 dark:text-amber-400">
          Ya están en fichas de médicos pero nunca se agregaron como catálogo oficial -- por eso el BI puede mostrarlos
          como una barra propia aunque no aparezcan en la lista de abajo. Fusionalos con el valor correcto.
        </p>
        <div class="flex flex-wrap gap-2">
          <div *ngFor="let h of huerfanos" class="flex items-center gap-2 bg-white dark:bg-slate-900 border border-amber-200 dark:border-amber-900/50 rounded-xl pl-3 pr-1.5 py-1.5">
            <span [ngClass]="getTipoBadgeClass(h.tipo)" class="text-[9px] px-1.5 py-0.5 rounded-md font-black uppercase">{{ formatTipoLabel(h.tipo) }}</span>
            <span class="text-xs font-bold text-slate-700 dark:text-slate-200">{{ h.valor }}</span>
            <span class="text-[10px] text-slate-400">{{ h.medicos_count }} méd.</span>
            <button (click)="abrirFusionHuerfano(h)" title="Fusionar con un valor del catálogo" class="w-6 h-6 rounded-lg bg-violet-100 hover:bg-violet-200 dark:bg-violet-950/60 dark:hover:bg-violet-900 text-violet-600 dark:text-violet-400 flex items-center justify-center">
              <span class="material-icons !text-sm">call_merge</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Filters and Search Bar Container -->
      <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 p-5 rounded-3xl shadow-sm space-y-4">
        
        <!-- Search & Filter Controls -->
        <div class="flex flex-col md:flex-row gap-3 items-center justify-between">
          
          <!-- Search input -->
          <div class="relative w-full md:w-96">
            <span class="material-icons absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 text-lg">search</span>
            <input
              type="text"
              [(ngModel)]="searchQuery"
              placeholder="Buscar por nombre, categoría o creador..."
              class="w-full bg-slate-50 dark:bg-slate-850 border border-slate-200 dark:border-slate-700/80 rounded-2xl pl-10 pr-4 py-2.5 text-xs sm:text-sm text-slate-800 dark:text-white placeholder:text-slate-400 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none transition-all"
            />
            <button *ngIf="searchQuery" (click)="searchQuery = ''" class="material-icons absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-sm">
              close
            </button>
          </div>

          <!-- Category Filter Pills -->
          <div class="flex items-center gap-1.5 overflow-x-auto w-full md:w-auto pb-1 md:pb-0 custom-scrollbar">
            <button
              (click)="selectedTipo = 'todos'"
              [class]="selectedTipo === 'todos' ? 'bg-indigo-600 text-white font-bold' : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 font-medium'"
              class="px-3.5 py-1.5 rounded-xl text-xs whitespace-nowrap transition-all flex items-center gap-1.5"
            >
              <span>Todos</span>
              <span class="text-[10px] px-1.5 py-0.2 rounded-full" [class]="selectedTipo === 'todos' ? 'bg-white/20' : 'bg-slate-200 dark:bg-slate-700'">{{ items.length }}</span>
            </button>

            <button
              (click)="selectedTipo = 'especialidad'"
              [class]="selectedTipo === 'especialidad' ? 'bg-purple-600 text-white font-bold' : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 font-medium'"
              class="px-3.5 py-1.5 rounded-xl text-xs whitespace-nowrap transition-all flex items-center gap-1.5"
            >
              <span class="material-icons text-xs">psychology</span>
              <span>Especialidades</span>
            </button>

            <button
              (click)="selectedTipo = 'subespecialidad'"
              [class]="selectedTipo === 'subespecialidad' ? 'bg-cyan-600 text-white font-bold' : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 font-medium'"
              class="px-3.5 py-1.5 rounded-xl text-xs whitespace-nowrap transition-all flex items-center gap-1.5"
            >
              <span class="material-icons text-xs">biotech</span>
              <span>Sub-esp.</span>
            </button>

            <button
              (click)="selectedTipo = 'universidad'"
              [class]="selectedTipo === 'universidad' ? 'bg-emerald-600 text-white font-bold' : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 font-medium'"
              class="px-3.5 py-1.5 rounded-xl text-xs whitespace-nowrap transition-all flex items-center gap-1.5"
            >
              <span class="material-icons text-xs">school</span>
              <span>Universidades</span>
            </button>

            <button
              (click)="selectedTipo = 'estado'"
              [class]="selectedTipo === 'estado' ? 'bg-amber-600 text-white font-bold' : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 font-medium'"
              class="px-3.5 py-1.5 rounded-xl text-xs whitespace-nowrap transition-all flex items-center gap-1.5"
            >
              <span class="material-icons text-xs">map</span>
              <span>Estados</span>
            </button>

            <button
              (click)="selectedTipo = 'ciudad'"
              [class]="selectedTipo === 'ciudad' ? 'bg-blue-600 text-white font-bold' : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 font-medium'"
              class="px-3.5 py-1.5 rounded-xl text-xs whitespace-nowrap transition-all flex items-center gap-1.5"
            >
              <span class="material-icons text-xs">location_city</span>
              <span>Ciudades</span>
            </button>
          </div>
        </div>

        <!-- Table View -->
        <div class="overflow-x-auto rounded-2xl border border-slate-100 dark:border-white/5 custom-scrollbar">
          
          <!-- Loading State -->
          <div *ngIf="loading" class="flex flex-col items-center justify-center py-16 gap-3 text-slate-500">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
            <p class="text-xs font-semibold">Cargando catálogos y estadísticas...</p>
          </div>

          <!-- Empty State -->
          <div *ngIf="!loading && filteredItems.length === 0" class="flex flex-col items-center justify-center py-16 text-center">
            <span class="material-icons text-slate-300 dark:text-slate-600 text-5xl mb-2">folder_off</span>
            <h4 class="text-base font-bold text-slate-700 dark:text-slate-300">No se encontraron registros</h4>
            <p class="text-xs text-slate-400 max-w-sm mt-1">Prueba cambiando los filtros o agrega un nuevo ítem con el botón superior.</p>
          </div>

          <table *ngIf="!loading && filteredItems.length > 0" class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50/80 dark:bg-slate-850/50 border-b border-slate-200 dark:border-slate-800 text-[11px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-wider select-none">
                <th class="py-3.5 px-4">Categoría</th>
                <th class="py-3.5 px-4">Nombre / Valor</th>
                <th class="py-3.5 px-4">Médicos Usando</th>
                <th class="py-3.5 px-4">Creado Por</th>
                <th class="py-3.5 px-4">Fecha Creación</th>
                <th class="py-3.5 px-4 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 dark:divide-slate-800 text-xs">
              <tr *ngFor="let item of filteredItems" class="hover:bg-slate-50/80 dark:hover:bg-slate-850/60 transition-colors group">
                
                <!-- Tipo Badge -->
                <td class="py-3 px-4 whitespace-nowrap">
                  <span [ngClass]="getTipoBadgeClass(item.tipo)" class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-black uppercase tracking-wider">
                    <span class="material-icons !text-xs">{{ getTipoIcon(item.tipo) }}</span>
                    {{ formatTipoLabel(item.tipo) }}
                  </span>
                </td>

                <!-- Nombre -->
                <td class="py-3 px-4">
                  <div class="font-bold text-slate-800 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors text-sm">
                    {{ item.nombre }}
                  </div>
                </td>

                <!-- Médicos Usando -->
                <td class="py-3 px-4 whitespace-nowrap">
                  <button (click)="verDetalles(item)" class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold transition-all" [ngClass]="item.medicos_count > 0 ? 'bg-indigo-50 text-indigo-600 dark:bg-indigo-950/60 dark:text-indigo-400 hover:bg-indigo-100' : 'bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500'">
                    <span class="material-icons !text-xs">{{ item.medicos_count > 0 ? 'people' : 'person_outline' }}</span>
                    {{ item.medicos_count }} {{ item.medicos_count === 1 ? 'médico' : 'médicos' }}
                  </button>
                </td>

                <!-- Creado Por -->
                <td class="py-3 px-4 whitespace-nowrap text-slate-600 dark:text-slate-300">
                  <div class="flex items-center gap-2">
                    <div class="w-6 h-6 rounded-full bg-indigo-100 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400 font-black text-[10px] flex items-center justify-center">
                      {{ (item.creado_por || 'S').charAt(0).toUpperCase() }}
                    </div>
                    <span class="font-medium text-xs">{{ item.creado_por || 'Sistema' }}</span>
                  </div>
                </td>

                <!-- Fecha Creación -->
                <td class="py-3 px-4 whitespace-nowrap text-slate-500 dark:text-slate-400">
                  <span>{{ formatFecha(item.creado_en) }}</span>
                </td>

                <!-- Acciones -->
                <td class="py-3 px-4 whitespace-nowrap text-right">
                  <div class="flex items-center justify-end gap-1">
                    
                    <!-- Botón Ver Detalles -->
                    <button (click)="verDetalles(item)" title="Ver detalles y médicos vinculados" class="w-8 h-8 rounded-xl bg-slate-100 hover:bg-indigo-50 dark:bg-slate-800 dark:hover:bg-indigo-950/60 text-slate-500 hover:text-indigo-600 dark:text-slate-400 dark:hover:text-indigo-400 flex items-center justify-center transition-all">
                      <span class="material-icons text-sm">visibility</span>
                    </button>

                    <!-- Botón Editar -->
                    <button (click)="openEditModal(item)" title="Modificar nombre" class="w-8 h-8 rounded-xl bg-slate-100 hover:bg-amber-50 dark:bg-slate-800 dark:hover:bg-amber-950/60 text-slate-500 hover:text-amber-600 dark:text-slate-400 dark:hover:text-amber-400 flex items-center justify-center transition-all">
                      <span class="material-icons text-sm">edit</span>
                    </button>

                    <!-- Botón Fusionar (con otro del mismo tipo -- ej. dos variantes de la misma universidad) -->
                    <button (click)="abrirFusionModal(item)" title="Fusionar con otro ítem del mismo tipo" class="w-8 h-8 rounded-xl bg-slate-100 hover:bg-violet-50 dark:bg-slate-800 dark:hover:bg-violet-950/60 text-slate-500 hover:text-violet-600 dark:text-slate-400 dark:hover:text-violet-400 flex items-center justify-center transition-all">
                      <span class="material-icons text-sm">call_merge</span>
                    </button>

                    <!-- Botón Eliminar -->
                    <button (click)="eliminarItem(item)" title="Eliminar ítem" class="w-8 h-8 rounded-xl bg-slate-100 hover:bg-red-50 dark:bg-slate-800 dark:hover:bg-red-950/60 text-slate-500 hover:text-red-600 dark:text-slate-400 dark:hover:text-red-400 flex items-center justify-center transition-all">
                      <span class="material-icons text-sm">delete</span>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>

        </div>

        <!-- Footer Pagination Info -->
        <div class="flex items-center justify-between text-xs text-slate-400 px-2 pt-2">
          <span>Mostrando <strong>{{ filteredItems.length }}</strong> de <strong>{{ items.length }}</strong> ítems</span>
          <span class="font-medium">Total categorías: 5</span>
        </div>

      </div>

      <!-- MODAL: AGREGAR NUEVO ÍTEM -->
      <div *ngIf="showAddModal" class="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-[9999] flex items-center justify-center p-4 animate-in fade-in duration-200">
        <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-3xl p-6 max-w-lg w-full shadow-2xl space-y-5 animate-in zoom-in-95 duration-200">
          
          <div class="flex justify-between items-center border-b border-slate-100 dark:border-slate-800 pb-4">
            <h3 class="text-lg font-black text-slate-800 dark:text-white flex items-center gap-2">
              <span class="material-icons text-indigo-600">add_box</span>
              Nuevo Ítem de Catálogo
            </h3>
            <button (click)="showAddModal = false" class="text-slate-400 hover:text-slate-600 dark:hover:text-white">
              <span class="material-icons text-lg">close</span>
            </button>
          </div>

          <div class="space-y-4">
            <div>
              <label class="block text-xs font-bold text-slate-600 dark:text-slate-400 mb-1.5 uppercase tracking-wider">Categoría / Tipo</label>
              <select [(ngModel)]="newTipo" class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl p-3 text-sm text-slate-800 dark:text-white outline-none focus:border-indigo-500 font-semibold">
                <option value="especialidad">Especialidad</option>
                <option value="subespecialidad">Sub-especialidad</option>
                <option value="universidad">Universidad</option>
                <option value="estado">Estado / Provincia</option>
                <option value="ciudad">Ciudad</option>
              </select>
            </div>

            <div>
              <label class="block text-xs font-bold text-slate-600 dark:text-slate-400 mb-1.5 uppercase tracking-wider">Nombre del Ítem</label>
              <input
                type="text"
                [(ngModel)]="newNombre"
                placeholder="Ej: Cardiología Pediátrica, UCV, etc."
                (keyup.enter)="guardarNuevoItem()"
                class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl p-3 text-sm text-slate-800 dark:text-white outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <div class="flex justify-end gap-3 pt-4 border-t border-slate-100 dark:border-slate-800">
            <button (click)="showAddModal = false" class="px-5 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 text-xs font-bold transition-all">
              Cancelar
            </button>
            <button (click)="guardarNuevoItem()" [disabled]="!newNombre.trim()" class="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-bold transition-all shadow-lg shadow-indigo-600/20 flex items-center gap-1.5">
              <span class="material-icons text-sm">save</span>
              Guardar Ítem
            </button>
          </div>

        </div>
      </div>

      <!-- MODAL: EDITAR ÍTEM -->
      <div *ngIf="showEditModal" class="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-[9999] flex items-center justify-center p-4 animate-in fade-in duration-200">
        <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-3xl p-6 max-w-lg w-full shadow-2xl space-y-5 animate-in zoom-in-95 duration-200">
          
          <div class="flex justify-between items-center border-b border-slate-100 dark:border-slate-800 pb-4">
            <h3 class="text-lg font-black text-slate-800 dark:text-white flex items-center gap-2">
              <span class="material-icons text-amber-500">edit_note</span>
              Modificar Ítem de Catálogo
            </h3>
            <button (click)="showEditModal = false" class="text-slate-400 hover:text-slate-600 dark:hover:text-white">
              <span class="material-icons text-lg">close</span>
            </button>
          </div>

          <div class="space-y-4" *ngIf="itemEditando">
            <div>
              <span [ngClass]="getTipoBadgeClass(itemEditando.tipo)" class="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10px] font-black uppercase tracking-wider mb-2">
                <span class="material-icons !text-xs">{{ getTipoIcon(itemEditando.tipo) }}</span>
                {{ formatTipoLabel(itemEditando.tipo) }}
              </span>
              <label class="block text-xs font-bold text-slate-600 dark:text-slate-400 mb-1.5 uppercase tracking-wider">Nombre del Ítem</label>
              <input
                type="text"
                [(ngModel)]="editNombre"
                (keyup.enter)="guardarEdicionItem()"
                class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl p-3 text-sm text-slate-800 dark:text-white outline-none focus:border-amber-500"
              />
            </div>

            <div *ngIf="itemEditando.medicos_count > 0" class="p-3 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900/50 rounded-xl text-xs text-amber-800 dark:text-amber-300">
              <strong class="font-bold flex items-center gap-1"><span class="material-icons text-sm">info</span> Actualización en cascada:</strong>
              Hay {{ itemEditando.medicos_count }} médicos usando este valor. Al modificarlo, se actualizará automáticamente en sus fichas.
            </div>
          </div>

          <div class="flex justify-end gap-3 pt-4 border-t border-slate-100 dark:border-slate-800">
            <button (click)="showEditModal = false" class="px-5 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 text-xs font-bold transition-all">
              Cancelar
            </button>
            <button (click)="guardarEdicionItem()" [disabled]="!editNombre.trim()" class="px-5 py-2.5 rounded-xl bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white text-xs font-bold transition-all shadow-lg shadow-amber-600/20 flex items-center gap-1.5">
              <span class="material-icons text-sm">done</span>
              Guardar Cambios
            </button>
          </div>

        </div>
      </div>

      <!-- ── Modal: Fusionar dos ítems del mismo tipo ── -->
      <div *ngIf="showMergeModal" class="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-[9999] flex items-center justify-center p-4 animate-in fade-in duration-200">
        <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-3xl p-6 max-w-lg w-full shadow-2xl space-y-5 animate-in zoom-in-95 duration-200">

          <div class="flex justify-between items-center border-b border-slate-100 dark:border-slate-800 pb-4">
            <h3 class="text-lg font-black text-slate-800 dark:text-white flex items-center gap-2">
              <span class="material-icons text-violet-500">call_merge</span>
              Fusionar Ítem de Catálogo
            </h3>
            <button (click)="showMergeModal = false" class="text-slate-400 hover:text-slate-600 dark:hover:text-white">
              <span class="material-icons text-lg">close</span>
            </button>
          </div>

          <div class="space-y-4" *ngIf="itemFusionando">
            <p class="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
              Todos los médicos que hoy usan <strong class="text-slate-700 dark:text-slate-200">"{{ itemFusionando.nombre }}"</strong>
              van a pasar al valor que elijas abajo, y esta entrada duplicada se va a borrar. Usalo para unir variantes del
              mismo valor real (ej. dos formas de escribir la misma universidad o el mismo estado).
            </p>

            <div>
              <label class="block text-xs font-bold text-slate-600 dark:text-slate-400 mb-1.5 uppercase tracking-wider">Fusionar dentro de</label>
              <select [(ngModel)]="fusionDestinoId" class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl p-3 text-sm text-slate-800 dark:text-white outline-none focus:border-violet-500">
                <option [ngValue]="null" disabled>Elegí el valor correcto...</option>
                <option *ngFor="let opt of opcionesFusionDestino" [ngValue]="opt.id">{{ opt.nombre }} ({{ opt.medicos_count }} médicos)</option>
              </select>
            </div>

            <div *ngIf="itemFusionando.medicos_count > 0" class="p-3 bg-violet-50 dark:bg-violet-950/30 border border-violet-200 dark:border-violet-900/50 rounded-xl text-xs text-violet-800 dark:text-violet-300">
              <strong class="font-bold flex items-center gap-1"><span class="material-icons text-sm">info</span> Reasignación en cascada:</strong>
              {{ itemFusionando.medicos_count }} médicos van a quedar con el nuevo valor automáticamente.
            </div>
          </div>

          <div class="flex justify-end gap-3 pt-4 border-t border-slate-100 dark:border-slate-800">
            <button (click)="showMergeModal = false" class="px-5 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 text-xs font-bold transition-all">
              Cancelar
            </button>
            <button (click)="guardarFusion()" [disabled]="!fusionDestinoId" class="px-5 py-2.5 rounded-xl bg-violet-600 hover:bg-violet-700 disabled:opacity-50 text-white text-xs font-bold transition-all shadow-lg shadow-violet-600/20 flex items-center gap-1.5">
              <span class="material-icons text-sm">call_merge</span>
              Fusionar
            </button>
          </div>

        </div>
      </div>

      <!-- ── Modal: Fusionar un valor huérfano (sin fila propia) con el catálogo ── -->
      <div *ngIf="showHuerfanoMergeModal" class="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-[9999] flex items-center justify-center p-4 animate-in fade-in duration-200">
        <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-3xl p-6 max-w-lg w-full shadow-2xl space-y-5 animate-in zoom-in-95 duration-200">

          <div class="flex justify-between items-center border-b border-slate-100 dark:border-slate-800 pb-4">
            <h3 class="text-lg font-black text-slate-800 dark:text-white flex items-center gap-2">
              <span class="material-icons text-amber-500">warning_amber</span>
              Fusionar Valor Sin Catalogar
            </h3>
            <button (click)="showHuerfanoMergeModal = false" class="text-slate-400 hover:text-slate-600 dark:hover:text-white">
              <span class="material-icons text-lg">close</span>
            </button>
          </div>

          <div class="space-y-4" *ngIf="huerfanoFusionando">
            <p class="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
              <strong class="text-slate-700 dark:text-slate-200">"{{ huerfanoFusionando.valor }}"</strong> no tiene fila propia
              en el catálogo -- solo existe en fichas de médicos. Los {{ huerfanoFusionando.medicos_count }} médicos que lo usan
              van a pasar al valor del catálogo que elijas abajo.
            </p>
            <div>
              <label class="block text-xs font-bold text-slate-600 dark:text-slate-400 mb-1.5 uppercase tracking-wider">Fusionar dentro de</label>
              <select [(ngModel)]="huerfanoFusionDestinoId" class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl p-3 text-sm text-slate-800 dark:text-white outline-none focus:border-violet-500">
                <option [ngValue]="null" disabled>Elegí el valor correcto...</option>
                <option *ngFor="let opt of opcionesFusionHuerfanoDestino" [ngValue]="opt.id">{{ opt.nombre }} ({{ opt.medicos_count }} médicos)</option>
              </select>
            </div>
          </div>

          <div class="flex justify-end gap-3 pt-4 border-t border-slate-100 dark:border-slate-800">
            <button (click)="showHuerfanoMergeModal = false" class="px-5 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 text-xs font-bold transition-all">
              Cancelar
            </button>
            <button (click)="guardarFusionHuerfano()" [disabled]="!huerfanoFusionDestinoId" class="px-5 py-2.5 rounded-xl bg-violet-600 hover:bg-violet-700 disabled:opacity-50 text-white text-xs font-bold transition-all shadow-lg shadow-violet-600/20 flex items-center gap-1.5">
              <span class="material-icons text-sm">call_merge</span>
              Fusionar
            </button>
          </div>

        </div>
      </div>

      <!-- MODAL: VER DETALLES Y MÉDICOS ASOCIADOS -->
      <div *ngIf="showDetailModal" class="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-[9999] flex items-center justify-center p-4 animate-in fade-in duration-200">
        <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-3xl p-6 max-w-2xl w-full shadow-2xl space-y-5 animate-in zoom-in-95 duration-200 flex flex-col max-h-[85vh]">
          
          <!-- Header -->
          <div class="flex justify-between items-start border-b border-slate-100 dark:border-slate-800 pb-4">
            <div>
              <div class="flex items-center gap-2 mb-1" *ngIf="detalleItem">
                <span [ngClass]="getTipoBadgeClass(detalleItem.tipo)" class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg text-[10px] font-black uppercase tracking-wider">
                  <span class="material-icons !text-xs">{{ getTipoIcon(detalleItem.tipo) }}</span>
                  {{ formatTipoLabel(detalleItem.tipo) }}
                </span>
                <span class="text-xs text-slate-400">ID: #{{ detalleItem.id }}</span>
              </div>
              <h3 class="text-xl font-black text-slate-800 dark:text-white">{{ detalleItem?.nombre }}</h3>
            </div>
            <button (click)="showDetailModal = false" class="text-slate-400 hover:text-slate-600 dark:hover:text-white">
              <span class="material-icons text-lg">close</span>
            </button>
          </div>

          <!-- Metadata info cards -->
          <div class="grid grid-cols-2 sm:grid-cols-3 gap-3" *ngIf="detalleItem">
            <div class="bg-slate-50 dark:bg-slate-800/50 p-3 rounded-xl border border-slate-100 dark:border-slate-800">
              <span class="text-[10px] font-black text-slate-400 uppercase tracking-wider block">Registrado Por</span>
              <span class="text-xs font-bold text-slate-800 dark:text-white mt-0.5 block truncate">{{ detalleItem.creado_por || 'Sistema' }}</span>
            </div>
            <div class="bg-slate-50 dark:bg-slate-800/50 p-3 rounded-xl border border-slate-100 dark:border-slate-800">
              <span class="text-[10px] font-black text-slate-400 uppercase tracking-wider block">Fecha Creación</span>
              <span class="text-xs font-bold text-slate-800 dark:text-white mt-0.5 block">{{ formatFecha(detalleItem.creado_en) }}</span>
            </div>
            <div class="bg-slate-50 dark:bg-slate-800/50 p-3 rounded-xl border border-slate-100 dark:border-slate-800 col-span-2 sm:col-span-1">
              <span class="text-[10px] font-black text-slate-400 uppercase tracking-wider block">Médicos Usándolo</span>
              <span class="text-xs font-bold text-indigo-600 dark:text-indigo-400 mt-0.5 block">{{ detalleMedicos.length }} registros vinculados</span>
            </div>
          </div>

          <!-- List of associated doctors -->
          <div class="flex-1 overflow-y-auto space-y-2 pr-1 custom-scrollbar min-h-[200px]">
            <h4 class="text-xs font-black text-slate-400 uppercase tracking-wider mb-2">Médicos con este valor</h4>
            
            <div *ngIf="loadingDetalles" class="flex items-center justify-center py-10 text-slate-400 gap-2">
              <div class="animate-spin rounded-full h-5 w-5 border-b-2 border-indigo-600"></div> Cargando médicos...
            </div>

            <div *ngIf="!loadingDetalles && detalleMedicos.length === 0" class="text-center py-8 text-xs text-slate-400">
              No hay médicos asignados con este valor en sus fichas actualmente.
            </div>

            <div *ngFor="let m of detalleMedicos" class="flex items-center justify-between bg-slate-50 dark:bg-slate-800/40 p-3 rounded-xl border border-slate-100 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
              <div>
                <div class="font-bold text-xs text-slate-800 dark:text-white">{{ m.nombre_completo }}</div>
                <div class="text-[11px] text-slate-400 mt-0.5">ID: {{ m.id_externo || '—' }} · {{ m.ciudad }}, {{ m.estado }}</div>
              </div>
              <span class="text-xs font-semibold text-slate-500 dark:text-slate-400">{{ m.telefono }}</span>
            </div>
          </div>

          <!-- Footer -->
          <div class="flex justify-end pt-3 border-t border-slate-100 dark:border-slate-800">
            <button (click)="showDetailModal = false" class="px-5 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 text-xs font-bold transition-all">
              Cerrar
            </button>
          </div>

        </div>
      </div>

    </div>
  `
})
export class ConfiguracionEncuestadorComponent implements OnInit {
  private http = inject(HttpClient);
  private confirmDialog = inject(ConfirmService);
  private API = `${environment.apiUrl}/api/encuestador`;

  loading = true;
  items: CatalogoItem[] = [];
  selectedTipo: 'todos' | 'especialidad' | 'subespecialidad' | 'universidad' | 'estado' | 'ciudad' = 'todos';
  searchQuery = '';

  // Modales
  showAddModal = false;
  newTipo: 'especialidad' | 'subespecialidad' | 'universidad' | 'estado' | 'ciudad' = 'especialidad';
  newNombre = '';

  showEditModal = false;
  itemEditando: CatalogoItem | null = null;
  editNombre = '';

  showDetailModal = false;
  loadingDetalles = false;
  detalleItem: CatalogoItem | null = null;
  detalleMedicos: any[] = [];

  // Fusionar: distinto de "editar" -- editar renombra una fila sola;
  // fusionar une DOS filas del mismo tipo (ej. "Distrito capiral" con typo
  // y "Distrito Capital" ya existente por separado) en una, reasignando a
  // todos los médicos que usaban la de origen. Renombrar a un nombre que
  // ya existe como su propia fila choca con la restricción de unicidad --
  // por eso hace falta esta operación aparte, no alcanza con "Editar".
  showMergeModal = false;
  itemFusionando: CatalogoItem | null = null;
  fusionDestinoId: number | null = null;

  ngOnInit() {
    this.cargarCatalogos();
    this.cargarHuerfanos();
  }

  // Valores que ya están en fichas de médicos pero nunca llegaron a tener
  // fila propia en el catálogo (ej. "Distrito capiral", que entró por el
  // formulario web de supervisor cuando ese campo era texto libre --
  // corregido 20-21 ago). Sin esto no hay id de origen para fusionar.
  huerfanos: { tipo: string; valor: string; medicos_count: number }[] = [];
  loadingHuerfanos = false;
  showHuerfanoMergeModal = false;
  huerfanoFusionando: { tipo: string; valor: string; medicos_count: number } | null = null;
  huerfanoFusionDestinoId: number | null = null;

  cargarHuerfanos() {
    this.loadingHuerfanos = true;
    this.http.get<any>(`${this.API}/catalogos/huerfanos`).subscribe({
      next: res => { this.huerfanos = res.huerfanos || []; this.loadingHuerfanos = false; },
      error: () => { this.loadingHuerfanos = false; }
    });
  }

  abrirFusionHuerfano(h: { tipo: string; valor: string; medicos_count: number }) {
    this.huerfanoFusionando = h;
    this.huerfanoFusionDestinoId = null;
    this.showHuerfanoMergeModal = true;
  }

  get opcionesFusionHuerfanoDestino(): CatalogoItem[] {
    if (!this.huerfanoFusionando) return [];
    return this.items.filter(i => i.tipo === this.huerfanoFusionando!.tipo);
  }

  guardarFusionHuerfano() {
    if (!this.huerfanoFusionando || !this.huerfanoFusionDestinoId) return;
    this.http.post<any>(`${this.API}/catalogos/huerfanos/fusionar`, {
      tipo: this.huerfanoFusionando.tipo,
      valor_origen: this.huerfanoFusionando.valor,
      id_destino: this.huerfanoFusionDestinoId,
    }).subscribe({
      next: () => {
        this.showHuerfanoMergeModal = false;
        this.huerfanoFusionando = null;
        this.huerfanoFusionDestinoId = null;
        this.cargarCatalogos();
        this.cargarHuerfanos();
      },
      error: err => {
        this.confirmDialog.info('Error al fusionar: ' + (err.error?.detail || err.message));
      }
    });
  }

  cargarCatalogos() {
    this.loading = true;
    this.http.get<any>(`${this.API}/catalogos-gestion`).subscribe({
      next: res => {
        this.items = res.items || [];
        this.loading = false;
      },
      error: err => {
        console.error('Error cargando catálogos:', err);
        this.confirmDialog.info('Error al cargar catálogos desde el servidor.');
        this.loading = false;
      }
    });
  }

  get filteredItems(): CatalogoItem[] {
    let result = this.items;

    // Filtro por tipo
    if (this.selectedTipo !== 'todos') {
      result = result.filter(item => item.tipo === this.selectedTipo);
    }

    // Filtro por búsqueda
    if (this.searchQuery.trim()) {
      const q = this.normalize(this.searchQuery);
      result = result.filter(item =>
        this.normalize(item.nombre).includes(q) ||
        this.normalize(item.tipo).includes(q) ||
        this.normalize(item.creado_por || '').includes(q)
      );
    }

    return result;
  }

  countByTipo(tipo: string): number {
    return this.items.filter(i => i.tipo === tipo).length;
  }

  openAddModal() {
    this.newTipo = this.selectedTipo !== 'todos' ? this.selectedTipo : 'especialidad';
    this.newNombre = '';
    this.showAddModal = true;
  }

  guardarNuevoItem() {
    const nombre = this.newNombre.trim();
    if (!nombre) return;

    this.http.post<any>(`${this.API}/catalogos`, { tipo: this.newTipo, nombre }).subscribe({
      next: () => {
        this.showAddModal = false;
        this.newNombre = '';
        this.cargarCatalogos();
      },
      error: err => {
        this.confirmDialog.info('Error al guardar: ' + (err.error?.detail || err.message));
      }
    });
  }

  openEditModal(item: CatalogoItem) {
    this.itemEditando = item;
    this.editNombre = item.nombre;
    this.showEditModal = true;
  }

  guardarEdicionItem() {
    if (!this.itemEditando) return;
    const nombre = this.editNombre.trim();
    if (!nombre) return;

    this.http.put<any>(`${this.API}/catalogos/${this.itemEditando.id}`, { nombre }).subscribe({
      next: () => {
        this.showEditModal = false;
        this.itemEditando = null;
        this.cargarCatalogos();
      },
      error: err => {
        this.confirmDialog.info('Error al modificar: ' + (err.error?.detail || err.message));
      }
    });
  }

  abrirFusionModal(item: CatalogoItem) {
    this.itemFusionando = item;
    this.fusionDestinoId = null;
    this.showMergeModal = true;
  }

  get opcionesFusionDestino(): CatalogoItem[] {
    if (!this.itemFusionando) return [];
    return this.items.filter(i => i.tipo === this.itemFusionando!.tipo && i.id !== this.itemFusionando!.id);
  }

  guardarFusion() {
    if (!this.itemFusionando || !this.fusionDestinoId) return;
    this.http.post<any>(`${this.API}/catalogos/${this.itemFusionando.id}/fusionar`, { id_destino: this.fusionDestinoId }).subscribe({
      next: () => {
        this.showMergeModal = false;
        this.itemFusionando = null;
        this.fusionDestinoId = null;
        this.cargarCatalogos();
      },
      error: err => {
        this.confirmDialog.info('Error al fusionar: ' + (err.error?.detail || err.message));
      }
    });
  }

  verDetalles(item: CatalogoItem) {
    this.detalleItem = item;
    this.detalleMedicos = [];
    this.loadingDetalles = true;
    this.showDetailModal = true;

    this.http.get<any>(`${this.API}/catalogos/${item.id}/detalles`).subscribe({
      next: res => {
        if (res.item) {
          this.detalleMedicos = res.item.medicos || [];
        }
        this.loadingDetalles = false;
      },
      error: () => {
        this.loadingDetalles = false;
      }
    });
  }

  async eliminarItem(item: CatalogoItem, force: boolean = false) {
    if (!force) {
      const advertencia = item.medicos_count > 0
        ? `Actualmente hay ${item.medicos_count} médicos usando este valor. ¿Deseas eliminarlo de todas formas?`
        : `¿Estás seguro de eliminar "${item.nombre}" del catálogo de ${this.formatTipoLabel(item.tipo)}?`;

      const ok = await this.confirmDialog.confirm(advertencia, {
        title: 'Eliminar ítem del catálogo',
        confirmText: 'Sí, eliminar',
        danger: true
      });
      if (!ok) return;
    }

    const url = force ? `${this.API}/catalogos/${item.id}?force=true` : `${this.API}/catalogos/${item.id}`;
    this.http.delete<any>(url).subscribe({
      next: () => {
        this.cargarCatalogos();
      },
      error: async (err) => {
        if (err.status === 409 && !force) {
          const detail = err.error?.detail;
          const msg = typeof detail === 'string' ? detail : (detail?.message || 'Este elemento está siendo utilizado por otros registros.');
          const forceOk = await this.confirmDialog.confirm(`${msg}\n\n¿Deseas forzar la eliminación de todos modos?`, {
            title: 'Elemento en Uso - Conflicto',
            confirmText: 'Forzar Eliminación',
            danger: true
          });
          if (forceOk) {
            this.eliminarItem(item, true);
          }
        } else {
          const errorMsg = typeof err.error?.detail === 'string' ? err.error.detail : (err.error?.detail?.message || err.message);
          this.confirmDialog.info('Error al eliminar: ' + errorMsg);
        }
      }
    });
  }

  getTipoIcon(tipo: string): string {
    switch (tipo) {
      case 'especialidad': return 'psychology';
      case 'subespecialidad': return 'biotech';
      case 'universidad': return 'school';
      case 'estado': return 'map';
      case 'ciudad': return 'location_city';
      default: return 'label';
    }
  }

  getTipoBadgeClass(tipo: string): string {
    switch (tipo) {
      case 'especialidad':
        return 'bg-purple-100 text-purple-700 dark:bg-purple-950/60 dark:text-purple-300 border border-purple-200 dark:border-purple-800/40';
      case 'subespecialidad':
        return 'bg-cyan-100 text-cyan-700 dark:bg-cyan-950/60 dark:text-cyan-300 border border-cyan-200 dark:border-cyan-800/40';
      case 'universidad':
        return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/40';
      case 'estado':
        return 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300 border border-amber-200 dark:border-amber-800/40';
      case 'ciudad':
        return 'bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300 border border-blue-200 dark:border-blue-800/40';
      default:
        return 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300';
    }
  }

  formatTipoLabel(tipo: string): string {
    switch (tipo) {
      case 'especialidad': return 'Especialidad';
      case 'subespecialidad': return 'Sub-especialidad';
      case 'universidad': return 'Universidad';
      case 'estado': return 'Estado';
      case 'ciudad': return 'Ciudad';
      default: return tipo;
    }
  }

  formatFecha(fechaStr?: string | null): string {
    if (!fechaStr) return '—';
    try {
      const d = new Date(fechaStr);
      return d.toLocaleDateString('es-VE', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return fechaStr;
    }
  }

  private normalize(str: string): string {
    return (str || '')
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '');
  }
}

