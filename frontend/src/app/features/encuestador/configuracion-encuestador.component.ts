import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { ConfirmService } from '../../shared/components/confirm-dialog/confirm.service';

@Component({
  selector: 'app-configuracion-encuestador',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  template: `
    <div class="p-6 max-w-6xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      <!-- Header -->
      <div class="flex justify-between items-center mb-6">
        <h1 class="text-3xl font-bold text-slate-800 dark:text-white flex items-center gap-2">
          <span class="material-icons text-indigo-600 dark:text-indigo-400">settings</span> Configuración de Catálogos
        </h1>
        <button routerLink="/encuestador/dashboard" class="flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-white font-semibold rounded-lg transition-colors shadow-sm">
          <span class="material-icons text-sm">arrow_back</span> Volver al Dashboard
        </button>
      </div>

      <div *ngIf="loading" class="text-slate-800 dark:text-white flex items-center gap-3">
        <div class="animate-spin rounded-full h-5 w-5 border-b-2 border-indigo-600 dark:border-indigo-500"></div> Cargando catálogos...
      </div>

      <!-- Grid Columns -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6" *ngIf="!loading">
        
        <!-- COL 1: Especialidades -->
        <div class="bg-white dark:bg-slate-900 rounded-xl p-6 border border-gray-200 dark:border-white/10 shadow-xl">
          <h3 class="text-lg font-bold text-slate-800 dark:text-white flex items-center gap-2 mb-4 border-b border-gray-100 dark:border-slate-800 pb-2">
            <span class="material-icons text-indigo-600 dark:text-indigo-400">psychology</span> Especialidades
          </h3>
          
          <!-- Add Form -->
          <div class="flex gap-2 mb-4">
            <input type="text" [(ngModel)]="newEspecialidad" (keyup.enter)="agregarItem('especialidad')" placeholder="Nueva especialidad..." class="flex-1 bg-white dark:bg-slate-850 border border-gray-350 dark:border-slate-700 rounded-lg p-2 text-sm text-slate-800 dark:text-white outline-none focus:border-indigo-500">
            <button (click)="agregarItem('especialidad')" class="bg-indigo-600 hover:bg-indigo-700 text-white font-bold px-3 py-2 rounded-lg transition-colors flex items-center justify-center">
              <span class="material-icons">add</span>
            </button>
          </div>

          <!-- List -->
          <div class="max-h-96 overflow-y-auto space-y-2 pr-1 custom-scrollbar">
            <div *ngIf="especialidades.length === 0" class="text-xs text-slate-400 text-center py-4">No hay especialidades cargadas</div>
            <div *ngFor="let item of especialidades" class="flex items-center justify-between bg-slate-50 dark:bg-slate-800/40 p-2.5 rounded-lg border border-gray-100 dark:border-slate-800/60 hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors">
              <span class="text-sm text-slate-800 dark:text-slate-200 font-semibold">{{ item.nombre }}</span>
              <button (click)="eliminarItem(item)" class="text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 p-1 rounded transition-colors">
                <span class="material-icons text-sm">delete</span>
              </button>
            </div>
          </div>
        </div>

        <!-- COL 2: Estados -->
        <div class="bg-white dark:bg-slate-900 rounded-xl p-6 border border-gray-200 dark:border-white/10 shadow-xl">
          <h3 class="text-lg font-bold text-slate-800 dark:text-white flex items-center gap-2 mb-4 border-b border-gray-100 dark:border-slate-800 pb-2">
            <span class="material-icons text-indigo-600 dark:text-indigo-400">map</span> Estados / Provincias
          </h3>
          
          <!-- Add Form -->
          <div class="flex gap-2 mb-4">
            <input type="text" [(ngModel)]="newEstado" (keyup.enter)="agregarItem('estado')" placeholder="Nuevo estado..." class="flex-1 bg-white dark:bg-slate-850 border border-gray-355 dark:border-slate-700 rounded-lg p-2 text-sm text-slate-800 dark:text-white outline-none focus:border-indigo-500">
            <button (click)="agregarItem('estado')" class="bg-indigo-600 hover:bg-indigo-700 text-white font-bold px-3 py-2 rounded-lg transition-colors flex items-center justify-center">
              <span class="material-icons">add</span>
            </button>
          </div>

          <!-- List -->
          <div class="max-h-96 overflow-y-auto space-y-2 pr-1 custom-scrollbar">
            <div *ngIf="estados.length === 0" class="text-xs text-slate-400 text-center py-4">No hay estados cargados</div>
            <div *ngFor="let item of estados" class="flex items-center justify-between bg-slate-50 dark:bg-slate-800/40 p-2.5 rounded-lg border border-gray-100 dark:border-slate-800/60 hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors">
              <span class="text-sm text-slate-800 dark:text-slate-200 font-semibold">{{ item.nombre }}</span>
              <button (click)="eliminarItem(item)" class="text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 p-1 rounded transition-colors">
                <span class="material-icons text-sm">delete</span>
              </button>
            </div>
          </div>
        </div>

        <!-- COL 3: Ciudades -->
        <div class="bg-white dark:bg-slate-900 rounded-xl p-6 border border-gray-200 dark:border-white/10 shadow-xl">
          <h3 class="text-lg font-bold text-slate-800 dark:text-white flex items-center gap-2 mb-4 border-b border-gray-100 dark:border-slate-800 pb-2">
            <span class="material-icons text-indigo-600 dark:text-indigo-400">location_city</span> Ciudades
          </h3>
          
          <!-- Add Form -->
          <div class="flex gap-2 mb-4">
            <input type="text" [(ngModel)]="newCiudad" (keyup.enter)="agregarItem('ciudad')" placeholder="Nueva ciudad..." class="flex-1 bg-white dark:bg-slate-850 border border-gray-355 dark:border-slate-700 rounded-lg p-2 text-sm text-slate-800 dark:text-white outline-none focus:border-indigo-500">
            <button (click)="agregarItem('ciudad')" class="bg-indigo-600 hover:bg-indigo-700 text-white font-bold px-3 py-2 rounded-lg transition-colors flex items-center justify-center">
              <span class="material-icons">add</span>
            </button>
          </div>

          <!-- List -->
          <div class="max-h-96 overflow-y-auto space-y-2 pr-1 custom-scrollbar">
            <div *ngIf="ciudades.length === 0" class="text-xs text-slate-400 text-center py-4">No hay ciudades cargadas</div>
            <div *ngFor="let item of ciudades" class="flex items-center justify-between bg-slate-50 dark:bg-slate-800/40 p-2.5 rounded-lg border border-gray-100 dark:border-slate-800/60 hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors">
              <span class="text-sm text-slate-800 dark:text-slate-200 font-semibold">{{ item.nombre }}</span>
              <button (click)="eliminarItem(item)" class="text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 p-1 rounded transition-colors">
                <span class="material-icons text-sm">delete</span>
              </button>
            </div>
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
  especialidades: any[] = [];
  estados: any[] = [];
  ciudades: any[] = [];

  newEspecialidad = '';
  newEstado = '';
  newCiudad = '';

  ngOnInit() {
    this.cargarCatalogos();
  }

  cargarCatalogos() {
    this.loading = true;
    this.http.get<any>(`${this.API}/catalogos-gestion`).subscribe({
      next: res => {
        const items = res.items || [];
        this.especialidades = items.filter((x: any) => x.tipo === 'especialidad');
        this.estados = items.filter((x: any) => x.tipo === 'estado');
        this.ciudades = items.filter((x: any) => x.tipo === 'ciudad');
        this.loading = false;
      },
      error: err => {
        console.error('Error cargando catálogos:', err);
        this.confirmDialog.info('Error al cargar catálogos desde el servidor. Verifique su conexión.');
        this.loading = false;
      }
    });
  }

  agregarItem(tipo: 'especialidad' | 'estado' | 'ciudad') {
    let nombre = '';
    if (tipo === 'especialidad') { nombre = this.newEspecialidad.trim(); }
    else if (tipo === 'estado') { nombre = this.newEstado.trim(); }
    else if (tipo === 'ciudad') { nombre = this.newCiudad.trim(); }

    if (!nombre) return;

    this.http.post<any>(`${this.API}/catalogos`, { tipo, nombre }).subscribe({
      next: () => {
        if (tipo === 'especialidad') { this.newEspecialidad = ''; }
        else if (tipo === 'estado') { this.newEstado = ''; }
        else if (tipo === 'ciudad') { this.newCiudad = ''; }
        this.cargarCatalogos();
      },
      error: err => {
        console.error('Error agregando item:', err);
        this.confirmDialog.info('Error al guardar el ítem: ' + (err.error?.detail || err.message));
      }
    });
  }

  async eliminarItem(item: any) {
    const ok = await this.confirmDialog.confirm(
      `¿Está seguro de eliminar "${item.nombre}" del catálogo de ${item.tipo}? Esta acción podría causar inconsistencias si hay médicos que ya la usan.`,
      { title: 'Eliminar ítem del catálogo', confirmText: 'Sí, eliminar', danger: true }
    );
    if (!ok) return;

    this.http.delete<any>(`${this.API}/catalogos/${item.id}`).subscribe({
      next: () => {
        this.cargarCatalogos();
      },
      error: err => {
        console.error('Error eliminando item:', err);
        this.confirmDialog.info('Error al eliminar: ' + (err.error?.detail || err.message));
      }
    });
  }
}
