import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { EncuestadorOfflineQueueService } from './services/encuestador-offline-queue.service';
import { ConfirmService } from '../../shared/components/confirm-dialog/confirm.service';

@Component({
  selector: 'app-medico-form',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  template: `
    <div class="p-6 max-w-5xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      <!-- Header -->
      <div class="flex justify-between items-center mb-6">
        <h1 class="text-3xl font-bold text-slate-800 dark:text-white flex items-center gap-2">
          <span class="material-icons text-indigo-600 dark:text-indigo-400">badge</span> Agregar médico al centro
        </h1>
        <div class="flex items-center gap-2">
          <span class="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-wider px-2 py-1 rounded-full" [ngClass]="isOnline ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400' : 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-400'">
            <span class="w-1.5 h-1.5 rounded-full" [ngClass]="isOnline ? 'bg-emerald-500' : 'bg-red-500'"></span>
            {{ isOnline ? 'En línea' : 'Sin conexión' }}
          </span>
          <button routerLink="/encuestador/centro" class="text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white transition-colors">
            <span class="material-icons">close</span>
          </button>
        </div>
      </div>

      <div *ngIf="loading" class="text-slate-800 dark:text-white flex items-center gap-3">
        <div class="animate-spin rounded-full h-5 w-5 border-b-2 border-indigo-600 dark:border-indigo-500"></div> Cargando datos...
      </div>

      <div class="bg-white dark:bg-slate-900 rounded-xl p-8 border border-gray-200 dark:border-white/10 shadow-xl relative" *ngIf="!loading">
        
        <!-- Búsqueda Superior -->
        <div class="mb-10 bg-indigo-50 dark:bg-slate-800/50 p-6 rounded-xl border border-indigo-100 dark:border-slate-700 relative">
          <label class="block text-sm font-semibold text-indigo-800 dark:text-indigo-300 mb-2">¿Ya existe el médico? Búscalo por ID o apellido:</label>
          <div class="relative">
            <span class="material-icons absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 dark:text-slate-500">search</span>
            <input type="text" [(ngModel)]="searchQuery" (input)="buscarMedicos()" 
                   class="w-full bg-white dark:bg-slate-900 border border-gray-300 dark:border-slate-700 rounded-lg py-3 pl-12 pr-4 text-slate-800 dark:text-white focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors shadow-sm dark:shadow-inner" 
                   placeholder="Ej: V-12345678 o Pérez">
          </div>
          
          <div *ngIf="medicosResult.length > 0" class="absolute z-10 w-full left-0 mt-1 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg shadow-2xl max-h-60 overflow-y-auto custom-scrollbar">
            <div *ngFor="let m of medicosResult" class="p-4 hover:bg-gray-50 dark:hover:bg-slate-700 cursor-pointer border-b border-gray-100 dark:border-slate-700 last:border-0 transition-colors" (click)="seleccionarMedico(m)">
              <div class="font-bold text-slate-800 dark:text-white">{{ m.apellido1 }} {{ m.apellido2 }}, {{ m.nombre1 }} {{ m.nombre2 }}</div>
              <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">ID: {{ m.id_medico_externo }} | {{ m.especialidad }} | {{ m.ciudad }}</div>
            </div>
          </div>
        </div>

        <form (ngSubmit)="guardarMedicoCentro()" #f="ngForm">
          
          <!-- SECCIÓN 1: Datos del Médico -->
          <div class="flex items-center gap-2 mb-6 border-l-4 border-indigo-600 dark:border-indigo-500 pl-3">
            <h3 class="text-xl font-bold text-indigo-700 dark:text-indigo-400">1. Datos del médico</h3>
          </div>
          
          <div class="grid grid-cols-1 md:grid-cols-4 gap-x-5 gap-y-5 mb-10">
            <div class="md:col-span-1">
              <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">ID Médico (cédula/ext.) <span class="text-red-500 dark:text-red-400">*</span></label>
              <input type="text" [(ngModel)]="medicoData.id_medico_externo" name="id_externo" [readonly]="medicoExistente" class="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg p-2.5 text-slate-800 dark:text-white focus:border-indigo-500 transition-colors outline-none" [class.bg-gray-100]="medicoExistente && !isDark()" [class.opacity-60]="medicoExistente" required>
            </div>
            <div class="md:col-span-1">
              <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">Apellido 1 <span class="text-red-500 dark:text-red-400">*</span></label>
              <input type="text" [(ngModel)]="medicoData.apellido1" name="apellido1" [readonly]="medicoExistente" class="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg p-2.5 text-slate-800 dark:text-white focus:border-indigo-500 transition-colors outline-none" [class.bg-gray-100]="medicoExistente && !isDark()" [class.opacity-60]="medicoExistente" required>
            </div>
            <div class="md:col-span-2">
              <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">Apellido 2</label>
              <input type="text" [(ngModel)]="medicoData.apellido2" name="apellido2" [readonly]="medicoExistente" class="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg p-2.5 text-slate-800 dark:text-white focus:border-indigo-500 transition-colors outline-none" [class.bg-gray-100]="medicoExistente && !isDark()" [class.opacity-60]="medicoExistente">
            </div>

            <div class="md:col-span-1">
              <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">Nombre 1 <span class="text-red-500 dark:text-red-400">*</span></label>
              <input type="text" [(ngModel)]="medicoData.nombre1" name="nombre1" [readonly]="medicoExistente" class="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg p-2.5 text-slate-800 dark:text-white focus:border-indigo-500 transition-colors outline-none" [class.bg-gray-100]="medicoExistente && !isDark()" [class.opacity-60]="medicoExistente" required>
            </div>
            <div class="md:col-span-1">
              <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">Nombre 2</label>
              <input type="text" [(ngModel)]="medicoData.nombre2" name="nombre2" [readonly]="medicoExistente" class="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg p-2.5 text-slate-800 dark:text-white focus:border-indigo-500 transition-colors outline-none" [class.bg-gray-100]="medicoExistente && !isDark()" [class.opacity-60]="medicoExistente">
            </div>
            <div class="md:col-span-2">
              <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">Especialidad <span class="text-red-500 dark:text-red-400">*</span></label>
              <input type="text" [(ngModel)]="medicoData.especialidad" name="especialidad" [readonly]="medicoExistente" class="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg p-2.5 text-slate-800 dark:text-white focus:border-indigo-500 transition-colors outline-none" [class.bg-gray-100]="medicoExistente && !isDark()" [class.opacity-60]="medicoExistente" required>
            </div>

            <div class="md:col-span-2">
              <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">Sub-especialidad</label>
              <input type="text" [(ngModel)]="medicoData.sub_especialidad" name="sub_especialidad" [readonly]="medicoExistente" class="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg p-2.5 text-slate-800 dark:text-white focus:border-indigo-500 transition-colors outline-none" [class.bg-gray-100]="medicoExistente && !isDark()" [class.opacity-60]="medicoExistente">
            </div>
            <div class="md:col-span-2">
              <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">Universidad de graduación</label>
              <input type="text" [(ngModel)]="medicoData.universidad_graduacion" name="universidad_graduacion" [readonly]="medicoExistente" class="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg p-2.5 text-slate-800 dark:text-white focus:border-indigo-500 transition-colors outline-none" [class.bg-gray-100]="medicoExistente && !isDark()" [class.opacity-60]="medicoExistente">
            </div>

            <div class="md:col-span-1">
              <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">Nº MPPS</label>
              <input type="text" [(ngModel)]="medicoData.nro_MPPS" name="mpps" [readonly]="medicoExistente" class="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg p-2.5 text-slate-800 dark:text-white focus:border-indigo-500 transition-colors outline-none" [class.bg-gray-100]="medicoExistente && !isDark()" [class.opacity-60]="medicoExistente">
            </div>
            <div class="md:col-span-1">
              <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">Nº Colegiado</label>
              <input type="text" [(ngModel)]="medicoData.nro_colegiado" name="colegiado" [readonly]="medicoExistente" class="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg p-2.5 text-slate-800 dark:text-white focus:border-indigo-500 transition-colors outline-none" [class.bg-gray-100]="medicoExistente && !isDark()" [class.opacity-60]="medicoExistente">
            </div>
            <div class="md:col-span-1">
              <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">Ciudad <span class="text-red-500 dark:text-red-400">*</span></label>
              <input type="text" [(ngModel)]="medicoData.ciudad" name="ciudad" [readonly]="medicoExistente" class="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg p-2.5 text-slate-800 dark:text-white focus:border-indigo-500 transition-colors outline-none" [class.bg-gray-100]="medicoExistente && !isDark()" [class.opacity-60]="medicoExistente" required>
            </div>
            <div class="md:col-span-1">
              <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">Estado <span class="text-red-500 dark:text-red-400">*</span></label>
              <input type="text" [(ngModel)]="medicoData.estado" name="estado" [readonly]="medicoExistente" class="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg p-2.5 text-slate-800 dark:text-white focus:border-indigo-500 transition-colors outline-none" [class.bg-gray-100]="medicoExistente && !isDark()" [class.opacity-60]="medicoExistente" required>
            </div>

            <div class="md:col-span-1">
              <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">Teléfono</label>
              <input type="text" [(ngModel)]="medicoData.telefono" name="telefono" [readonly]="medicoExistente" class="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg p-2.5 text-slate-800 dark:text-white focus:border-indigo-500 transition-colors outline-none" [class.bg-gray-100]="medicoExistente && !isDark()" [class.opacity-60]="medicoExistente">
            </div>
            <div class="md:col-span-1">
              <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">WhatsApp</label>
              <input type="text" [(ngModel)]="medicoData.whatsapp" name="whatsapp" [readonly]="medicoExistente" class="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg p-2.5 text-slate-800 dark:text-white focus:border-indigo-500 transition-colors outline-none" [class.bg-gray-100]="medicoExistente && !isDark()" [class.opacity-60]="medicoExistente">
            </div>
            <div class="md:col-span-1">
              <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">Email</label>
              <input type="email" [(ngModel)]="medicoData.email" name="email" [readonly]="medicoExistente" class="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg p-2.5 text-slate-800 dark:text-white focus:border-indigo-500 transition-colors outline-none" [class.bg-gray-100]="medicoExistente && !isDark()" [class.opacity-60]="medicoExistente">
            </div>
            <div class="md:col-span-1">
              <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">Instagram</label>
              <input type="text" [(ngModel)]="medicoData.instagram" name="instagram" [readonly]="medicoExistente" class="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg p-2.5 text-slate-800 dark:text-white focus:border-indigo-500 transition-colors outline-none" [class.bg-gray-100]="medicoExistente && !isDark()" [class.opacity-60]="medicoExistente">
            </div>

            <div class="md:col-span-4">
              <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">LinkedIn</label>
              <input type="text" [(ngModel)]="medicoData.linkedin" name="linkedin" [readonly]="medicoExistente" class="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg p-2.5 text-slate-800 dark:text-white focus:border-indigo-500 transition-colors outline-none" [class.bg-gray-100]="medicoExistente && !isDark()" [class.opacity-60]="medicoExistente">
            </div>
          </div>

          <!-- SECCIÓN 2: Consultorio 1 -->
          <div class="flex items-center gap-2 mb-6 border-l-4 border-indigo-600 dark:border-indigo-500 pl-3">
            <h3 class="text-xl font-bold text-indigo-700 dark:text-indigo-400">2. Datos del consultorio 1 (en este centro)</h3>
          </div>
          
          <div class="grid grid-cols-1 md:grid-cols-4 gap-x-5 gap-y-5 mb-10">
            <div class="md:col-span-1">
              <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1"># Piso / Consultorio</label>
              <input type="text" [(ngModel)]="medicoData.piso_consultorio" name="piso_consultorio" class="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg p-2.5 text-slate-800 dark:text-white focus:border-indigo-500 transition-colors outline-none">
            </div>
            <div class="md:col-span-1">
              <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">Horarios de consulta</label>
              <input type="text" [(ngModel)]="medicoData.horarios_consulta" name="horarios_consulta" class="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg p-2.5 text-slate-800 dark:text-white focus:border-indigo-500 transition-colors outline-none" placeholder="Ej: 8:00 - 12:00">
            </div>
            <div class="md:col-span-2">
              <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-2">Días de consulta</label>
              <div class="flex flex-wrap gap-3 mt-1">
                <label *ngFor="let dia of diasList" class="flex items-center gap-1.5 cursor-pointer text-sm text-slate-700 dark:text-slate-300 hover:text-indigo-600 dark:hover:text-indigo-300 transition-colors">
                  <input type="checkbox" [(ngModel)]="selectedDias[dia]" [name]="'dia_' + dia" class="rounded border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-indigo-600 dark:text-indigo-500 focus:ring-indigo-500">
                  {{ dia }}
                </label>
              </div>
            </div>

            <div class="md:col-span-4">
              <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">Dirección específica</label>
              <textarea [(ngModel)]="medicoData.direccion_especifica" name="direccion_especifica" rows="2" class="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg p-2.5 text-slate-800 dark:text-white focus:border-indigo-500 transition-colors outline-none resize-y"></textarea>
            </div>
          </div>

          <!-- SECCIÓN 3: Consultorio 2 -->
          <div class="flex items-center gap-2 mb-6 border-l-4 border-indigo-600 dark:border-indigo-500 pl-3">
            <h3 class="text-xl font-bold text-indigo-700 dark:text-indigo-400">3. Consultorio 2 (opcional)</h3>
          </div>
          
          <div class="grid grid-cols-1 md:grid-cols-4 gap-x-5 gap-y-5 mb-10">
            <div class="md:col-span-1">
              <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">Clínica 2 (nombre)</label>
              <input type="text" [(ngModel)]="medicoData.clinica2_nombre" name="clinica2_nombre" class="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg p-2.5 text-slate-800 dark:text-white focus:border-indigo-500 transition-colors outline-none">
            </div>
            <div class="md:col-span-1">
              <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1"># Piso</label>
              <input type="text" [(ngModel)]="medicoData.piso_consultorio2" name="piso_consultorio2" class="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg p-2.5 text-slate-800 dark:text-white focus:border-indigo-500 transition-colors outline-none">
            </div>
            <div class="md:col-span-1">
              <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">Horarios</label>
              <input type="text" [(ngModel)]="medicoData.horarios_consulta2" name="horarios_consulta2" class="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg p-2.5 text-slate-800 dark:text-white focus:border-indigo-500 transition-colors outline-none">
            </div>
            <div class="md:col-span-1">
              <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-2">Días</label>
              <div class="flex flex-wrap gap-3 mt-1">
                <label *ngFor="let dia of diasList" class="flex items-center gap-1.5 cursor-pointer text-sm text-slate-700 dark:text-slate-300 hover:text-indigo-600 dark:hover:text-indigo-300 transition-colors">
                  <input type="checkbox" [(ngModel)]="selectedDias2[dia]" [name]="'dia2_' + dia" class="rounded border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-indigo-600 dark:text-indigo-500 focus:ring-indigo-500">
                  {{ dia }}
                </label>
              </div>
            </div>

            <div class="md:col-span-4">
              <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">Dirección 2</label>
              <textarea [(ngModel)]="medicoData.direccion_especifica2" name="direccion_especifica2" rows="2" class="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg p-2.5 text-slate-800 dark:text-white focus:border-indigo-500 transition-colors outline-none resize-y"></textarea>
            </div>
          </div>

          <!-- SECCIÓN 4: Datos Económicos -->
          <div class="flex items-center gap-2 mb-6 border-l-4 border-indigo-600 dark:border-indigo-500 pl-3">
            <h3 class="text-xl font-bold text-indigo-700 dark:text-indigo-400">4. Datos económicos</h3>
          </div>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-x-5 gap-y-5 mb-8">
            <div>
              <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">Valor de la consulta <span class="text-red-500 dark:text-red-400">*</span></label>
              <select [(ngModel)]="medicoData.valor_consulta_rango" name="valor" class="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg p-2.5 text-slate-800 dark:text-white focus:border-indigo-500 transition-colors outline-none" required>
                <option value="" disabled selected>Seleccione...</option>
                <option *ngFor="let r of catalogos.valor_consulta_rangos" [value]="r">{{r}}</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">Promedio de pacientes / semana <span class="text-red-500 dark:text-red-400">*</span></label>
              <select [(ngModel)]="medicoData.promedio_pacientes_semanal_rango" name="pacientes" class="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg p-2.5 text-slate-800 dark:text-white focus:border-indigo-500 transition-colors outline-none" required>
                <option value="" disabled selected>Seleccione...</option>
                <option *ngFor="let r of catalogos.promedio_pacientes_rangos" [value]="r">{{r}}</option>
              </select>
            </div>
          </div>

          <div class="flex justify-end gap-4 border-t border-gray-200 dark:border-slate-800 pt-6 mt-4">
            <button type="button" routerLink="/encuestador/centro" class="bg-gray-100 hover:bg-gray-200 text-slate-700 dark:bg-slate-700 dark:hover:bg-slate-600 dark:text-white font-semibold py-3 px-8 rounded-lg transition-colors shadow-sm dark:shadow-lg">
              Cancelar
            </button>
            <button type="submit" [disabled]="!f.valid" class="bg-indigo-600 hover:bg-indigo-700 dark:hover:bg-indigo-500 text-white font-bold py-3 px-8 rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2 shadow-lg shadow-indigo-600/30 dark:shadow-indigo-500/25">
              <span class="material-icons">check_circle</span> Guardar médico
            </button>
          </div>
        </form>
      </div>
    </div>
  `
})
export class MedicoFormComponent implements OnInit {
  private http = inject(HttpClient);
  private router = inject(Router);
  private offline = inject(EncuestadorOfflineQueueService);
  private confirmDialog = inject(ConfirmService);
  private API = `${environment.apiUrl}/api/encuestador`;

  loading = true;
  searchQuery = '';
  medicosResult: any[] = [];
  catalogos: any = { valor_consulta_rangos: [], promedio_pacientes_rangos: [] };
  isOnline = navigator.onLine;

  medicoExistente = false;
  medicoData: any = this.getEmptyMedico();

  diasList = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];
  selectedDias: Record<string, boolean> = {};
  selectedDias2: Record<string, boolean> = {};

  ngOnInit() {
    this.offline.isOnline$.subscribe(v => this.isOnline = v);
    this.http.get<any>(`${this.API}/catalogos`).subscribe({
      next: res => { this.catalogos = res; this.loading = false; this.offline.cacheWrite('catalogos', res); },
      error: async () => { this.catalogos = (await this.offline.cacheRead('catalogos')) || this.catalogos; this.loading = false; }
    });
  }

  isDark() {
    return document.documentElement.classList.contains('dark');
  }
  
  getEmptyMedico() {
    this.selectedDias = {};
    this.selectedDias2 = {};
    return {
      id_medico: null,
      id_medico_externo: '',
      apellido1: '',
      apellido2: '',
      nombre1: '',
      nombre2: '',
      especialidad: '',
      sub_especialidad: '',
      universidad_graduacion: '',
      nro_MPPS: '',
      nro_colegiado: '',
      ciudad: '',
      estado: '',
      telefono: '',
      whatsapp: '',
      email: '',
      linkedin: '',
      instagram: '',
      piso_consultorio: '',
      horarios_consulta: '',
      dias_consulta: '',
      direccion_especifica: '',
      clinica2_nombre: '',
      piso_consultorio2: '',
      horarios_consulta2: '',
      dias_consulta2: '',
      direccion_especifica2: '',
      valor_consulta_rango: '',
      promedio_pacientes_semanal_rango: ''
    };
  }

  buscarMedicos() {
    if (this.searchQuery.length < 3) {
      this.medicosResult = [];
      return;
    }
    const key = `medicos:${this.searchQuery}`;
    // Nota: el endpoint real es /medicos/buscar (no /medicos) — la búsqueda estaba rota (404) antes de este fix.
    this.http.get<any>(`${this.API}/medicos/buscar?q=${this.searchQuery}`).subscribe({
      next: res => { this.medicosResult = res.medicos || []; this.offline.cacheWrite(key, res.medicos || []); },
      error: async () => { this.medicosResult = (await this.offline.cacheRead(key)) || []; }
    });
  }

  seleccionarMedico(m: any) {
    this.medicoExistente = true;
    this.medicoData = { ...this.getEmptyMedico(), ...m };
    this.medicosResult = [];
    this.searchQuery = m.id_medico_externo;
  }

  guardarMedicoCentro() {
    this.medicoData.dias_consulta = this.diasList.filter(d => this.selectedDias[d]).join(', ');
    this.medicoData.dias_consulta2 = this.diasList.filter(d => this.selectedDias2[d]).join(', ');

    if (!navigator.onLine) {
      this.offline.enqueue({
        url: `${this.API}/medico-centro`, jsonBody: this.medicoData,
        label: `Médico ${this.medicoData.apellido1}, ${this.medicoData.nombre1}`,
      });
      this.offline.cacheRead('encuesta-abierta').then(cached => {
        if (cached) {
          cached.medicos = [...(cached.medicos || []), { ...this.medicoData }];
          this.offline.cacheWrite('encuesta-abierta', cached);
        }
      });
      this.confirmDialog.info('Médico guardado localmente — se sincronizará al reconectar.', { title: 'Guardado sin conexión' });
      this.router.navigate(['/encuestador/centro']);
      return;
    }
    this.http.post<any>(`${this.API}/medico-centro`, this.medicoData).subscribe({
      next: () => {
        this.confirmDialog.info('Médico guardado correctamente en el centro.', { title: 'Médico guardado' });
        this.router.navigate(['/encuestador/centro']);
      },
      error: (err) => {
        console.error(err);
        this.confirmDialog.info('Error al guardar: ' + (err.error?.detail || err.message), { title: 'Error' });
      }
    });
  }
}
