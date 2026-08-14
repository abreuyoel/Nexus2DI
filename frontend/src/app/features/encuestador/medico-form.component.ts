import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router, ActivatedRoute } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { EncuestadorOfflineQueueService } from './services/encuestador-offline-queue.service';
import { ConfirmService } from '../../shared/components/confirm-dialog/confirm.service';
import { MutableSearchSelectComponent } from './components/mutable-search-select.component';

@Component({
  selector: 'app-medico-form',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule, MutableSearchSelectComponent],
  template: `
    <div class="p-6 max-w-5xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      <!-- Header -->
      <div class="flex justify-between items-center mb-6">
        <h1 class="text-3xl font-bold text-slate-800 dark:text-white flex items-center gap-2">
          <span class="material-icons text-indigo-600 dark:text-indigo-400">badge</span>
          {{ modoEdicion ? 'Editar médico' : 'Agregar médico al centro' }}
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
        
        <!-- Búsqueda Superior (no aplica en modo edición: ya se sabe qué médico es) -->
        <div *ngIf="!modoEdicion" class="mb-10 bg-indigo-50 dark:bg-slate-800/50 p-6 rounded-xl border border-indigo-100 dark:border-slate-700 relative">
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
              <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">ID Médico (cédula/ext.)</label>
              <input type="text" [(ngModel)]="medicoData.id_medico_externo" name="id_externo" [readonly]="medicoExistente" class="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg p-2.5 text-slate-800 dark:text-white focus:border-indigo-500 transition-colors outline-none" [class.bg-gray-100]="medicoExistente && !isDark()" [class.opacity-60]="medicoExistente">
            </div>
            <div class="md:col-span-1">
              <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">Apellido 1 <span class="text-red-500 dark:text-red-400">*</span></label>
              <input type="text" [(ngModel)]="medicoData.apellido1" name="apellido1" [readonly]="medicoExistente" class="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg p-2.5 text-slate-800 dark:text-white focus:border-indigo-500 transition-colors outline-none" [class.bg-gray-100]="medicoExistente && !isDark()" [class.opacity-60]="medicoExistente" required>
            </div>
            <div class="md:col-span-2">
              <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">Apellido 2 <span class="text-red-500 dark:text-red-400">*</span></label>
              <input type="text" [(ngModel)]="medicoData.apellido2" name="apellido2" [readonly]="medicoExistente" class="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg p-2.5 text-slate-800 dark:text-white focus:border-indigo-500 transition-colors outline-none" [class.bg-gray-100]="medicoExistente && !isDark()" [class.opacity-60]="medicoExistente" required>
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
              <app-mutable-search-select
                label="Especialidad"
                placeholder="Seleccione especialidad..."
                [options]="especialidadesList"
                [(value)]="medicoData.especialidad"
                tipo="especialidad"
                [disabled]="medicoExistente"
                (addNew)="onAddNewCatalogItem($event)"
              ></app-mutable-search-select>
            </div>

            <div class="md:col-span-2">
              <app-mutable-search-select
                label="Sub-especialidad"
                placeholder="Seleccione sub-especialidad..."
                [options]="subespecialidadesList"
                [(value)]="medicoData.sub_especialidad"
                tipo="subespecialidad"
                [disabled]="medicoExistente"
                (addNew)="onAddNewCatalogItem($event)"
              ></app-mutable-search-select>
            </div>
            <div class="md:col-span-2">
              <app-mutable-search-select
                label="Universidad de graduación"
                placeholder="Seleccione universidad..."
                [options]="universidadesList"
                [(value)]="medicoData.universidad_graduacion"
                tipo="universidad"
                [disabled]="medicoExistente"
                (addNew)="onAddNewCatalogItem($event)"
              ></app-mutable-search-select>
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
              <app-mutable-search-select
                label="Ciudad"
                placeholder="Seleccione ciudad..."
                [options]="ciudadesList"
                [(value)]="medicoData.ciudad"
                tipo="ciudad"
                [disabled]="medicoExistente"
                (addNew)="onAddNewCatalogItem($event)"
              ></app-mutable-search-select>
            </div>
            <div class="md:col-span-1">
              <app-mutable-search-select
                label="Estado"
                placeholder="Seleccione estado..."
                [options]="estadosList"
                [(value)]="medicoData.estado"
                tipo="estado"
                [disabled]="medicoExistente"
                (addNew)="onAddNewCatalogItem($event)"
              ></app-mutable-search-select>
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

          <!-- SECCIÓN 2: Consultorios -->
          <div class="flex items-center gap-2 mb-6 border-l-4 border-indigo-600 dark:border-indigo-500 pl-3">
            <h3 class="text-xl font-bold text-indigo-700 dark:text-indigo-400">2. Datos de Consultorios</h3>
          </div>
          
          <div *ngFor="let c of consultorios; let i = index" class="mb-8 p-6 bg-gray-50 dark:bg-slate-800/50 rounded-xl border border-gray-200 dark:border-slate-700 relative">
            <button type="button" *ngIf="consultorios.length > 1" (click)="removerConsultorio(i)" class="absolute top-4 right-4 text-red-500 hover:bg-red-50 p-2 rounded-full transition-colors">
              <span class="material-icons">delete</span>
            </button>
            <h4 class="font-bold mb-4 text-slate-700 dark:text-slate-300">Consultorio {{ i + 1 }}</h4>
            
            <div class="grid grid-cols-1 md:grid-cols-4 gap-x-5 gap-y-5">
              <div class="md:col-span-2">
                <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">Nombre de la Clínica/Centro <span class="text-red-500 dark:text-red-400">*</span></label>
                <input type="text" [(ngModel)]="c.nombre_clinica" [name]="'clinica_' + i" class="w-full bg-white dark:bg-slate-900 border border-gray-300 dark:border-slate-700 rounded-lg p-2.5 text-slate-800 dark:text-white focus:border-indigo-500 transition-colors outline-none" required>
              </div>
              <div class="md:col-span-2">
                <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1"># Piso / Consultorio</label>
                <input type="text" [(ngModel)]="c.piso_consultorio" [name]="'piso_' + i" class="w-full bg-white dark:bg-slate-900 border border-gray-300 dark:border-slate-700 rounded-lg p-2.5 text-slate-800 dark:text-white focus:border-indigo-500 transition-colors outline-none">
              </div>
              
              <div class="md:col-span-4">
                <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">Dirección específica</label>
                <textarea [(ngModel)]="c.direccion_especifica" [name]="'dir_' + i" rows="2" class="w-full bg-white dark:bg-slate-900 border border-gray-300 dark:border-slate-700 rounded-lg p-2.5 text-slate-800 dark:text-white focus:border-indigo-500 transition-colors outline-none resize-y"></textarea>
              </div>
              
              <!-- Datos Económicos -->
              <div class="md:col-span-2">
                <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">Valor de la consulta <span class="text-red-500 dark:text-red-400">*</span></label>
                <select [(ngModel)]="c.valor_consulta_rango" [name]="'valor_' + i" class="w-full bg-white dark:bg-slate-900 border border-gray-300 dark:border-slate-700 rounded-lg p-2.5 text-slate-800 dark:text-white focus:border-indigo-500 transition-colors outline-none" required>
                  <option value="" disabled selected>Seleccione...</option>
                  <option *ngFor="let r of catalogos.valor_consulta_rangos" [value]="r">{{r}}</option>
                </select>
              </div>
              <div class="md:col-span-2">
                <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">Promedio de pacientes / semana <span class="text-red-500 dark:text-red-400">*</span></label>
                <select [(ngModel)]="c.promedio_pacientes_semanal_rango" [name]="'pacs_' + i" class="w-full bg-white dark:bg-slate-900 border border-gray-300 dark:border-slate-700 rounded-lg p-2.5 text-slate-800 dark:text-white focus:border-indigo-500 transition-colors outline-none" required>
                  <option value="" disabled selected>Seleccione...</option>
                  <option *ngFor="let r of catalogos.promedio_pacientes_rangos" [value]="r">{{r}}</option>
                </select>
              </div>

              <!-- Horarios JSON estructurado -->
              <div class="md:col-span-4 mt-2">
                <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-2">Horarios Estructurados</label>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                   <div *ngFor="let d of diasList" class="flex items-center gap-3 bg-white dark:bg-slate-900 p-3 rounded-lg border border-gray-200 dark:border-slate-700">
                     <label class="flex items-center gap-2 cursor-pointer w-20">
                       <input type="checkbox" [(ngModel)]="c.horarios[d].activo" [name]="'d_' + d + i" class="rounded text-indigo-600 focus:ring-indigo-500">
                       <span class="text-sm font-semibold text-slate-700 dark:text-slate-300">{{ d }}</span>
                     </label>
                     <div class="flex-1 flex gap-2" *ngIf="c.horarios[d].activo">
                       <input type="time" [(ngModel)]="c.horarios[d].desde" [name]="'desde_' + d + i" class="w-full bg-gray-50 dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded p-1.5 text-sm text-slate-800 dark:text-white outline-none">
                       <span class="text-slate-400 pt-1.5">-</span>
                       <input type="time" [(ngModel)]="c.horarios[d].hasta" [name]="'hasta_' + d + i" class="w-full bg-gray-50 dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded p-1.5 text-sm text-slate-800 dark:text-white outline-none">
                     </div>
                   </div>
                </div>
              </div>
            </div>
          </div>
          
          <div class="mb-10">
             <button type="button" (click)="agregarConsultorio()" class="w-full border-2 border-dashed border-indigo-300 dark:border-indigo-500/50 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-500/10 font-bold py-4 rounded-xl transition-colors flex items-center justify-center gap-2">
               <span class="material-icons">add_business</span> Añadir otro consultorio
             </button>
          </div>

          <div class="flex justify-end gap-4 border-t border-gray-200 dark:border-slate-800 pt-6 mt-4">
            <button type="button" routerLink="/encuestador/centro" class="bg-gray-100 hover:bg-gray-200 text-slate-700 dark:bg-slate-700 dark:hover:bg-slate-600 dark:text-white font-semibold py-3 px-8 rounded-lg transition-colors shadow-sm dark:shadow-lg">
              Cancelar
            </button>
            <button type="submit" [disabled]="!f.valid || guardando" class="bg-indigo-600 hover:bg-indigo-700 dark:hover:bg-indigo-500 text-white font-bold py-3 px-8 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-wait flex items-center gap-2 shadow-lg shadow-indigo-600/30 dark:shadow-indigo-500/25">
              @if (guardando) {
                <div class="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin"></div> Guardando...
              } @else {
                <span class="material-icons">check_circle</span> {{ modoEdicion ? 'Guardar cambios' : 'Guardar médico' }}
              }
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
  private route = inject(ActivatedRoute);
  private offline = inject(EncuestadorOfflineQueueService);
  private confirmDialog = inject(ConfirmService);
  private API = `${environment.apiUrl}/api/encuestador`;

  loading = true;
  searchQuery = '';
  medicosResult: any[] = [];
  catalogos: any = { valor_consulta_rangos: [], promedio_pacientes_rangos: [] };
  isOnline = navigator.onLine;
  especialidadesList: string[] = [];
  subespecialidadesList: string[] = [];
  universidadesList: string[] = [];
  estadosList: string[] = [];
  ciudadesList: string[] = [];

  // Modo edición: se llega acá con /encuestador/medico/:idMedico (ej. desde
  // "Editar" en Gestión de Centro) en vez de /encuestador/medico (alta). El
  // médico es una entidad global -- edita sus datos y TODOS sus consultorios,
  // no solo los de la encuesta desde la que se entró a editar.
  modoEdicion = false;
  idMedicoEditando: number | null = null;

  medicoExistente = false;
  consultorios: any[] = [];
  diasList = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];
  // Nombre del centro donde el encuestador ya está parado (viene de la
  // jornada/encuesta activa) -- se usa para pre-llenar el Consultorio 1,
  // ya que preguntarlo ahí es redundante: la razón de estar en este
  // formulario ES ese centro. Se llega a saber recién en ngOnInit (llamada
  // async), por eso medicoData también se corrige apenas resuelve.
  centroNombre = '';
  medicoData: any = this.getEmptyMedico();

  ngOnInit() {
    this.offline.isOnline$.subscribe(v => this.isOnline = v);
    this.http.get<any>(`${this.API}/catalogos`).subscribe({
      next: res => {
        this.catalogos = res;
        this.loading = false;
        this.offline.cacheWrite('catalogos', res);
        this.inicializarListasCatalogos();
      },
      error: async () => {
        this.catalogos = (await this.offline.cacheRead('catalogos')) || this.catalogos;
        this.loading = false;
        this.inicializarListasCatalogos();
      }
    });

    const idParam = this.route.snapshot.paramMap.get('idMedico');
    if (idParam) {
      this.modoEdicion = true;
      this.idMedicoEditando = +idParam;
      this.cargarParaEditar(this.idMedicoEditando);
      return; // en edición no hace falta centroNombre/encuesta-abierta
    }

    this.http.get<any>(`${this.API}/encuesta-abierta`).subscribe({
      next: res => { this.aplicarCentroActivo(res); this.offline.cacheWrite('encuesta-abierta', res); },
      // Sin señal se usa la encuesta cacheada: el nombre del centro tiene que
      // salir igual, es justamente cuando más molesta tener que tipearlo.
      error: async () => this.aplicarCentroActivo(await this.offline.cacheRead('encuesta-abierta')),
    });
  }

  private cargarParaEditar(id: number) {
    this.http.get<any>(`${this.API}/medico/${id}`).subscribe({
      next: res => {
        if (!res?.success) return;
        this.medicoData = {
          id_medico: res.id_medico, id_medico_externo: res.id_medico_externo,
          apellido1: res.apellido1, apellido2: res.apellido2,
          nombre1: res.nombre1, nombre2: res.nombre2,
          especialidad: res.especialidad, sub_especialidad: res.sub_especialidad,
          universidad_graduacion: res.universidad_graduacion,
          nro_MPPS: res.nro_MPPS, nro_colegiado: res.nro_colegiado,
          ciudad: res.ciudad, estado: res.estado,
          telefono: res.telefono, whatsapp: res.whatsapp, email: res.email,
          linkedin: res.linkedin, instagram: res.instagram,
        };
        const cons = (res.consultorios || []).map((c: any) => ({
          nombre_clinica: c.nombre_clinica,
          piso_consultorio: c.piso_consultorio,
          direccion_especifica: c.direccion_especifica,
          valor_consulta_rango: c.valor_consulta_rango,
          promedio_pacientes_semanal_rango: c.promedio_pacientes_semanal_rango,
          horarios: this.parseHorarios(c.horarios_json),
        }));
        this.consultorios = cons.length ? cons : [this.getEmptyConsultorio()];
      },
      error: () => {
        this.confirmDialog.info('No se pudo cargar el médico -- revisá la conexión e intentá de nuevo.', { title: 'Error' });
        this.router.navigate(['/encuestador/centro']);
      },
    });
  }

  /** Inverso de JSON.stringify(c.horarios) al guardar -- si algún día falta
   *  o viene corrupto (dato viejo migrado, ver backfill_medico_consultorios.sql),
   *  se cae a "inactivo" para ese día en vez de romper el formulario. */
  private parseHorarios(horariosJson: string | null | undefined): any {
    let parsed: any = {};
    if (horariosJson) {
      try { parsed = JSON.parse(horariosJson) || {}; } catch { parsed = {}; }
    }
    const horarios: any = {};
    for (const d of this.diasList) {
      horarios[d] = parsed[d] || { activo: false, desde: '08:00', hasta: '12:00' };
    }
    return horarios;
  }

  private aplicarCentroActivo(res: any) {
    if (!res?.tiene_encuesta) return;
    this.centroNombre = res.nombre_centro || '';
    // Si el consultorio 1 sigue como se generó al construir el componente
    // (sin tocar), completarlo ahora que ya sabemos el centro.
    if (this.consultorios.length === 1 && !this.consultorios[0].nombre_clinica) {
      this.consultorios[0].nombre_clinica = this.centroNombre;
    }
  }

  isDark() {
    return document.documentElement.classList.contains('dark');
  }
  
  getEmptyMedico() {
    this.consultorios = [this.getEmptyConsultorio(true)];
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
      instagram: ''
    };
  }

  /** esPrimero: el Consultorio 1 se pre-llena con el centro activo (ver
   *  centroNombre) -- el campo de texto libre solo tiene sentido a partir
   *  del 2do consultorio, para cuando el médico atiende en OTRA clínica. */
  getEmptyConsultorio(esPrimero: boolean = false) {
    const horarios: any = {};
    for (const d of this.diasList) {
      horarios[d] = { activo: false, desde: '08:00', hasta: '12:00' };
    }
    return {
      nombre_clinica: esPrimero ? this.centroNombre : '',
      piso_consultorio: '',
      direccion_especifica: '',
      valor_consulta_rango: '',
      promedio_pacientes_semanal_rango: '',
      horarios
    };
  }

  agregarConsultorio() {
    this.consultorios.push(this.getEmptyConsultorio());
  }

  removerConsultorio(index: number) {
    if (this.consultorios.length > 1) {
      this.consultorios.splice(index, 1);
    }
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

    // Asegurar que el valor del médico seleccionado esté en la lista temporal para que se muestre en el select
    if (m.especialidad && !this.especialidadesList.includes(m.especialidad)) {
      this.especialidadesList.push(m.especialidad);
    }
    if (m.sub_especialidad && !this.subespecialidadesList.includes(m.sub_especialidad)) {
      this.subespecialidadesList.push(m.sub_especialidad);
    }
    if (m.universidad_graduacion && !this.universidadesList.includes(m.universidad_graduacion)) {
      this.universidadesList.push(m.universidad_graduacion);
    }
    if (m.estado && !this.estadosList.includes(m.estado)) {
      this.estadosList.push(m.estado);
    }
    if (m.ciudad && !this.ciudadesList.includes(m.ciudad)) {
      this.ciudadesList.push(m.ciudad);
    }
  }

  guardando = false;

  async guardarMedicoCentro() {
    // Con mala señal el POST puede tardar hasta los 12s del timeout sin
    // ningún feedback visible -- eso invita a tocar "Guardar" de nuevo, y
    // ESE doble tap (más el reintento automático de la cola offline) es la
    // causa confirmada de médicos duplicados reportada en campo. El índice
    // único en el backend ya lo protege a nivel de datos, pero esto evita
    // generar el segundo request en primer lugar.
    if (this.guardando) return;
    this.guardando = true;
    try {
      if (this.modoEdicion) {
        await this._guardarEdicion();
      } else {
        await this._guardarMedicoCentro();
      }
    } finally {
      this.guardando = false;
    }
  }

  private async _guardarEdicion() {
    this.medicoData.consultorios = this.consultorios.map(c => ({
      nombre_clinica: c.nombre_clinica,
      piso_consultorio: c.piso_consultorio,
      direccion_especifica: c.direccion_especifica,
      valor_consulta_rango: c.valor_consulta_rango,
      promedio_pacientes_semanal_rango: c.promedio_pacientes_semanal_rango,
      horarios_json: JSON.stringify(c.horarios),
    }));
    try {
      // Igual que el alta: si no hay señal (o el PUT tarda demasiado) queda
      // encolado y se sube solo al reconectar -- editar también necesita
      // funcionar sin conexión, es el mismo terreno de campo.
      const { queued } = await this.offline.postOrQueue(
        `${this.API}/medico/${this.idMedicoEditando}/editar`, this.medicoData,
        { label: `Editar médico ${this.medicoData.apellido1}, ${this.medicoData.nombre1}` },
      );
      this.confirmDialog.info(
        queued ? 'Cambios guardados en este dispositivo -- se subirán cuando haya señal.' : 'Médico actualizado correctamente.',
        { title: queued ? 'Guardado sin conexión' : 'Médico actualizado' },
      );
      this.router.navigate(['/encuestador/centro']);
    } catch (err: any) {
      if (err?.sinEspacio) {
        this.confirmDialog.info(
          'No hay espacio en este dispositivo para guardar más cambios sin conexión. Este cambio NO se guardó -- buscá señal e intentá de nuevo.',
          { title: 'Sin espacio en el dispositivo' },
        );
        return;
      }
      this.confirmDialog.info('Error al guardar: ' + (err.error?.detail || err.message), { title: 'Error' });
    }
  }

  private async _guardarMedicoCentro() {
    this.medicoData.consultorios = this.consultorios.map(c => ({
       nombre_clinica: c.nombre_clinica,
       piso_consultorio: c.piso_consultorio,
       direccion_especifica: c.direccion_especifica,
       valor_consulta_rango: c.valor_consulta_rango,
       promedio_pacientes_semanal_rango: c.promedio_pacientes_semanal_rango,
       horarios_json: JSON.stringify(c.horarios)
    }));

    // Se refleja en el caché ANTES de intentar subirlo: si queda encolado, el
    // encuestador tiene que verlo igual en la lista del centro (si no, parece
    // que se perdió y lo carga de nuevo, duplicándolo).
    const reflejarEnCache = async () => {
      const cached = await this.offline.cacheRead('encuesta-abierta');
      if (cached) {
        cached.medicos = [...(cached.medicos || []), { ...this.medicoData }];
        await this.offline.cacheWrite('encuesta-abierta', cached);
      }
    };

    try {
      const { queued } = await this.offline.postOrQueue(
        `${this.API}/medico-centro`, this.medicoData,
        { label: `Médico ${this.medicoData.apellido1}, ${this.medicoData.nombre1}` },
      );
      if (queued) {
        await reflejarEnCache();
        this.confirmDialog.info(
          'Médico guardado en este dispositivo — se subirá solo cuando haya señal. Podés seguir cargando.',
          { title: 'Guardado sin conexión' },
        );
      } else {
        this.confirmDialog.info('Médico guardado correctamente en el centro.', { title: 'Médico guardado' });
      }
      this.router.navigate(['/encuestador/centro']);
    } catch (err: any) {
      console.error(err);
      if (err?.sinEspacio) {
        // El dispositivo no tiene más espacio: NO se perdió lo ya encolado,
        // pero esto no entra. Hay que decirle qué hacer, no solo que falló.
        this.confirmDialog.info(
          'No hay espacio en este dispositivo para guardar más registros sin conexión.\n\n'
          + 'Este médico NO se guardó. Buscá señal y esperá a que suba todo lo pendiente '
          + '(el contador del dashboard tiene que llegar a 0), o liberá espacio en el '
          + 'teléfono. Después podés cargarlo de nuevo y seguir sin conexión.',
          { title: 'Sin espacio en el dispositivo' },
        );
        return;
      }
      // Resto: el servidor rechazó el dato (no es falta de señal), reintentarlo
      // igual fallaría, así que se muestra el motivo real.
      this.confirmDialog.info('Error al guardar: ' + (err.error?.detail || err.message), { title: 'Error' });
    }
  }

  inicializarListasCatalogos() {
    this.especialidadesList = [...(this.catalogos.especialidades || [])];
    this.subespecialidadesList = [...(this.catalogos.subespecialidades || [])];
    this.universidadesList = [...(this.catalogos.universidades || [])];
    this.estadosList = [...(this.catalogos.estados || [])];
    this.ciudadesList = [...(this.catalogos.ciudades || [])];
  }

  async onAddNewCatalogItem(event: { tipo: 'especialidad' | 'subespecialidad' | 'universidad' | 'estado' | 'ciudad', value: string }) {
    const { tipo, value } = event;
    const valorFormateado = value.trim();
    if (!valorFormateado) return;

    // Añadir localmente si no existe para actualizar la lista de opciones
    if (tipo === 'especialidad') {
      if (!this.especialidadesList.includes(valorFormateado)) {
        this.especialidadesList.push(valorFormateado);
        this.especialidadesList.sort();
      }
    } else if (tipo === 'subespecialidad') {
      if (!this.subespecialidadesList.includes(valorFormateado)) {
        this.subespecialidadesList.push(valorFormateado);
        this.subespecialidadesList.sort();
      }
    } else if (tipo === 'universidad') {
      if (!this.universidadesList.includes(valorFormateado)) {
        this.universidadesList.push(valorFormateado);
        this.universidadesList.sort();
      }
    } else if (tipo === 'estado') {
      if (!this.estadosList.includes(valorFormateado)) {
        this.estadosList.push(valorFormateado);
        this.estadosList.sort();
      }
    } else if (tipo === 'ciudad') {
      if (!this.ciudadesList.includes(valorFormateado)) {
        this.ciudadesList.push(valorFormateado);
        this.ciudadesList.sort();
      }
    }

    // Encolar o enviar al backend
    try {
      await this.offline.postOrQueue(
        `${this.API}/catalogos`,
        { tipo, nombre: valorFormateado },
        { label: `Agregar ${tipo}: ${valorFormateado}` }
      );
      
      // Actualizar el caché de catálogos local
      const cached = await this.offline.cacheRead('catalogos');
      if (cached) {
        const keyMap: Record<string, string> = {
          'especialidad': 'especialidades',
          'subespecialidad': 'subespecialidades',
          'universidad': 'universidades',
          'estado': 'estados',
          'ciudad': 'ciudades'
        };
        const key = keyMap[tipo];
        if (key) {
          if (!cached[key]) cached[key] = [];
          if (!cached[key].includes(valorFormateado)) {
            cached[key].push(valorFormateado);
            cached[key].sort();
          }
          await this.offline.cacheWrite('catalogos', cached);
        }
      }
    } catch (err) {
      console.error('Error guardando catálogo:', err);
    }
  }
}
