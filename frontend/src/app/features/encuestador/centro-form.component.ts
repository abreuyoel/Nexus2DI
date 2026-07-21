import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { ApiService } from '../../core/services/api.service';
import { EncuestadorOfflineQueueService } from './services/encuestador-offline-queue.service';
import { ConfirmService } from '../../shared/components/confirm-dialog/confirm.service';

@Component({
  selector: 'app-centro-form',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  template: `
    <div class="p-6 max-w-7xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div class="flex justify-between items-center mb-6">
        <h1 class="text-3xl font-bold text-slate-800 dark:text-white">Gesti&oacute;n de Centro</h1>
        <div class="flex items-center gap-2">
          <span class="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-wider px-2 py-1 rounded-full" [ngClass]="isOnline ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400' : 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-400'">
            <span class="w-1.5 h-1.5 rounded-full" [ngClass]="isOnline ? 'bg-emerald-500' : 'bg-red-500'"></span>
            {{ isOnline ? 'En l&iacute;nea' : 'Sin conexi&oacute;n' }}
          </span>
          <button *ngIf="pendingSync > 0" (click)="sincronizar()" [disabled]="!isOnline" class="flex items-center gap-1 text-[10px] font-black uppercase tracking-wider px-2 py-1 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-400">
            <span class="material-icons !text-sm">sync</span>{{ pendingSync }} pendientes
          </button>
          <button routerLink="/encuestador/dashboard" class="text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white transition-colors">Volver al Dashboard</button>
        </div>
      </div>
      <div *ngIf="syncError" class="mb-4 bg-red-50 dark:bg-red-950/60 border border-red-200 dark:border-red-900 rounded-xl px-3 py-2 flex items-center justify-between gap-2">
        <span class="text-xs text-red-600 dark:text-red-300 font-semibold">No se pudo sincronizar: {{ syncError }}</span>
        <button (click)="sincronizar()" class="text-[10px] font-black uppercase px-2 py-1 rounded-lg bg-red-200 text-red-700 dark:bg-red-900 dark:text-red-200">Reintentar</button>
      </div>

      <div *ngIf="loading" class="text-slate-600 dark:text-white flex items-center gap-3">
        <div class="animate-spin rounded-full h-5 w-5 border-b-2 border-indigo-500"></div> Cargando...
      </div>
      
      <div *ngIf="!loading && encuestaActiva" class="bg-white dark:bg-slate-900 rounded-xl p-6 border border-emerald-300 dark:border-emerald-500/30 shadow-lg mb-6">
        <div class="flex justify-between items-start mb-4">
          <div>
            <h2 class="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{{ encuestaActiva.nombre_centro }}</h2>
            <p class="text-slate-500 dark:text-slate-400">{{ encuestaActiva.ciudad }}, {{ encuestaActiva.estado }}</p>
          </div>
          <button (click)="cerrarEncuesta()" class="bg-red-500 hover:bg-red-600 dark:bg-red-600 dark:hover:bg-red-700 text-white px-4 py-2 rounded-lg text-sm font-semibold transition-colors shadow-lg">
            Cerrar Centro
          </button>
        </div>
        
        <div class="mt-6 flex justify-between items-center">
          <h3 class="text-lg font-semibold text-slate-800 dark:text-white">M&eacute;dicos Registrados ({{ encuestaActiva.medicos?.length || 0 }})</h3>
          <button routerLink="/encuestador/medico" class="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg font-semibold transition-colors shadow-lg shadow-indigo-500/20">
            + Agregar M&eacute;dico
          </button>
        </div>
        
        <div class="mt-4 space-y-2">
          <div *ngFor="let m of encuestaActiva.medicos" class="bg-gray-50 dark:bg-slate-800 p-4 rounded-lg border border-gray-200 dark:border-slate-700 flex justify-between items-center">
            <div>
              <div class="font-bold text-slate-800 dark:text-white">{{ m.apellido1 }} {{ m.apellido2 }}, {{ m.nombre1 }} {{ m.nombre2 }}</div>
              <div class="text-sm text-slate-500 dark:text-slate-400">{{ m.especialidad }}</div>
            </div>
            <div class="text-right">
              <span class="inline-block px-2 py-1 bg-gray-100 dark:bg-slate-700 text-xs rounded text-slate-600 dark:text-slate-300">{{ m.valor_consulta_rango }}</span>
            </div>
          </div>
          <div *ngIf="!encuestaActiva.medicos?.length" class="text-slate-400 dark:text-slate-500 italic py-4">No hay m&eacute;dicos registrados en este centro a&uacute;n.</div>
        </div>
      </div>

      <div *ngIf="!loading && !encuestaActiva" class="bg-white dark:bg-slate-900 rounded-xl p-8 border border-gray-200 dark:border-white/10 shadow-xl max-w-4xl mx-auto">
        <div class="flex items-center gap-2 mb-6">
          <span class="material-icons text-indigo-500 dark:text-indigo-400 !text-3xl">domain</span>
          <h2 class="text-2xl font-bold text-slate-800 dark:text-white">Selecciona un centro</h2>
        </div>
        
        <div class="mb-4 relative">
          <span class="material-icons absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 dark:text-slate-500">search</span>
          <input type="text" [(ngModel)]="searchQuery" (input)="buscarCentros()" class="w-full bg-gray-50 dark:bg-slate-800/80 border border-gray-300 dark:border-slate-700 rounded-xl py-4 pl-12 pr-4 text-slate-800 dark:text-white focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors shadow-inner" placeholder="Buscar por nombre, ciudad o estado...">
        </div>
        
        <div class="max-h-96 overflow-y-auto mb-6 rounded-xl border border-gray-200 dark:border-slate-700 bg-gray-50/50 dark:bg-slate-800/30 custom-scrollbar" *ngIf="centrosResult.length">
          <div *ngFor="let c of centrosResult; let last = last" 
               class="p-5 hover:bg-indigo-50 dark:hover:bg-slate-700/80 cursor-pointer transition-colors group" 
               [class.border-b]="!last" 
               [class.border-gray-200]="!last"
               [class.dark:border-slate-700]="!last"
               (click)="confirmarApertura(c)">
            <div class="font-bold text-slate-800 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-300 transition-colors">{{ c.nombre_centro | uppercase }}</div>
            <div class="text-sm text-slate-500 dark:text-slate-400 mt-1">{{ c.direccion_completa }}</div>
          </div>
        </div>
        
        <div class="mt-6 pt-6 border-t border-gray-200 dark:border-slate-800" *ngIf="!mostrandoCrearCentro">
          <button (click)="mostrandoCrearCentro = true" class="w-full border-2 border-dashed border-indigo-400 dark:border-indigo-500/50 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-500/10 hover:border-indigo-500 dark:hover:border-indigo-400 font-bold py-4 rounded-xl transition-colors flex items-center justify-center gap-2">
            <span class="material-icons text-xl">add_business</span> Crear nuevo centro de salud
          </button>
        </div>
        
        <div class="mt-6 pt-6 border-t border-gray-200 dark:border-slate-800 animate-in slide-in-from-top-4 duration-300" *ngIf="mostrandoCrearCentro">
          <div class="flex justify-between items-center mb-6">
            <h3 class="text-xl font-bold text-indigo-600 dark:text-indigo-300 flex items-center gap-2"><span class="material-icons">add_location_alt</span> Solicitud de Nuevo Centro</h3>
            <button (click)="mostrandoCrearCentro = false" class="text-slate-400 hover:text-slate-600 dark:hover:text-white transition-colors bg-gray-100 dark:bg-slate-800 w-8 h-8 rounded-full flex items-center justify-center"><span class="material-icons !text-lg">close</span></button>
          </div>
          <div class="bg-gray-50 dark:bg-slate-800/50 p-6 rounded-xl border border-gray-200 dark:border-slate-700 mb-6">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div class="md:col-span-2">
                <label class="block text-xs font-bold text-slate-500 dark:text-slate-400 mb-1 uppercase tracking-wider">Nombre del Centro *</label>
                <input type="text" [(ngModel)]="nuevoCentro.nombre_centro" class="w-full bg-white dark:bg-slate-900 border border-gray-300 dark:border-slate-700 rounded-lg p-3 text-slate-800 dark:text-white focus:border-indigo-500 outline-none transition-colors">
              </div>
              <div class="md:col-span-2">
                <label class="block text-xs font-bold text-slate-500 dark:text-slate-400 mb-1 uppercase tracking-wider">Direcci&oacute;n Completa *</label>
                <input type="text" [(ngModel)]="nuevoCentro.direccion_completa" class="w-full bg-white dark:bg-slate-900 border border-gray-300 dark:border-slate-700 rounded-lg p-3 text-slate-800 dark:text-white focus:border-indigo-500 outline-none transition-colors">
              </div>
              <div>
                <label class="block text-xs font-bold text-slate-500 dark:text-slate-400 mb-1 uppercase tracking-wider">Ciudad</label>
                <input type="text" [(ngModel)]="nuevoCentro.ciudad" class="w-full bg-white dark:bg-slate-900 border border-gray-300 dark:border-slate-700 rounded-lg p-3 text-slate-800 dark:text-white focus:border-indigo-500 outline-none transition-colors">
              </div>
              <div>
                <label class="block text-xs font-bold text-slate-500 dark:text-slate-400 mb-1 uppercase tracking-wider">Estado</label>
                <select [(ngModel)]="nuevoCentro.estado" class="w-full bg-white dark:bg-slate-900 border border-gray-300 dark:border-slate-700 rounded-lg p-3 text-slate-800 dark:text-white focus:border-indigo-500 outline-none transition-colors">
                  <option value="">Seleccione un estado</option>
                  <option *ngFor="let est of estados" [value]="est.nombre">{{ est.nombre }}</option>
                </select>
              </div>
            </div>
            
            <div class="mt-6 p-4 bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200 dark:border-indigo-500/20 rounded-lg flex gap-3 text-indigo-600 dark:text-indigo-300">
              <span class="material-icons mt-0.5">info</span>
              <p class="text-sm">Al enviar este formulario, se crear&aacute; una solicitud que deber&aacute; ser aprobada por el equipo de ATC antes de que el centro aparezca en la lista.</p>
            </div>
          </div>
          
          <button (click)="crearCentro()" class="bg-indigo-600 hover:bg-indigo-700 text-white font-bold px-6 py-3.5 rounded-xl transition-colors w-full flex items-center justify-center gap-2 shadow-lg disabled:opacity-50 disabled:grayscale" [disabled]="!nuevoCentro.nombre_centro || !nuevoCentro.direccion_completa">
            <span class="material-icons">send</span> Enviar Solicitud a ATC
          </button>
        </div>
      </div>
    </div>

    <!-- Confirm Modal -->
    <div *ngIf="centroAConfirmar" class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in">
      <div class="bg-white dark:bg-slate-900 rounded-3xl p-8 max-w-md w-full border border-gray-200 dark:border-slate-700 shadow-2xl text-center relative overflow-hidden">
        <div class="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-indigo-500 to-purple-500"></div>
        <div class="w-20 h-20 bg-indigo-100 dark:bg-indigo-500/20 rounded-full flex items-center justify-center mx-auto mb-6 border-4 border-indigo-200 dark:border-indigo-500/30">
          <span class="material-icons text-4xl text-indigo-500 dark:text-indigo-400">add_task</span>
        </div>
        <h3 class="text-2xl font-black text-slate-800 dark:text-white mb-2">&iquest;Iniciar encuesta?</h3>
        <p class="text-slate-600 dark:text-slate-300 font-medium mb-8">{{ centroAConfirmar.nombre_centro }}</p>
        
        <div class="flex gap-4 justify-center">
          <button (click)="abrirEncuesta(centroAConfirmar)" class="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3 px-6 rounded-xl transition-colors shadow-lg shadow-indigo-500/20">
            S&iacute;, iniciar
          </button>
          <button (click)="centroAConfirmar = null" class="flex-1 bg-gray-100 hover:bg-gray-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-white font-bold py-3 px-6 rounded-xl transition-colors border border-gray-200 dark:border-slate-700">
            Cancelar
          </button>
        </div>
      </div>
    </div>
  `
})
export class CentroFormComponent implements OnInit {
  private http = inject(HttpClient);
  private router = inject(Router);
  private apiService = inject(ApiService);
  private offline = inject(EncuestadorOfflineQueueService);
  private confirmDialog = inject(ConfirmService);
  private API = `${environment.apiUrl}/api/encuestador`;

  loading = true;
  encuestaActiva: any = null;
  searchQuery = '';
  centrosResult: any[] = [];
  centroAConfirmar: any = null;
  mostrandoCrearCentro = false;
  estados: any[] = [];
  isOnline = navigator.onLine;
  pendingSync = 0;
  syncError: string | null = null;

  nuevoCentro = { nombre_centro: '', direccion_completa: '', ciudad: '', estado: '' };

  ngOnInit() {
    this.checkEncuesta();
    this.buscarCentros();
    this.apiService.getEstados().subscribe(res => {
      this.estados = res || [];
    });
    this.offline.isOnline$.subscribe(v => this.isOnline = v);
    this.offline.pendingCount$.subscribe(v => this.pendingSync = v);
    this.offline.syncError$.subscribe(e => this.syncError = e?.error || null);
  }

  sincronizar() { this.offline.syncAll(); }

  checkEncuesta() {
    this.loading = true;
    this.http.get<any>(`${this.API}/encuesta-abierta`).subscribe({
      next: (res) => {
        if (!res.jornada_activa) {
          this.router.navigate(['/encuestador/dashboard']);
          return;
        }
        this.encuestaActiva = res.tiene_encuesta ? res : null;
        this.loading = false;
        this.offline.cacheWrite('encuesta-abierta', res);
      },
      error: async () => {
        const cached = await this.offline.cacheRead('encuesta-abierta');
        if (!cached?.jornada_activa) {
          this.loading = false;
          this.router.navigate(['/encuestador/dashboard']);
          return;
        }
        this.encuestaActiva = cached.tiene_encuesta ? cached : null;
        this.loading = false;
      }
    });
  }

  buscarCentros() {
    const key = `centros:${this.searchQuery}`;
    this.http.get<any>(`${this.API}/centros?q=${this.searchQuery}`).subscribe({
      next: res => { this.centrosResult = res.centros || []; this.offline.cacheWrite(key, res.centros || []); },
      error: async () => { this.centrosResult = (await this.offline.cacheRead(key)) || []; }
    });
  }

  crearCentro() {
    this.loading = true;
    if (!navigator.onLine) {
      this.offline.enqueue({ url: `${this.API}/centros`, jsonBody: this.nuevoCentro, label: `Solicitud de centro ${this.nuevoCentro.nombre_centro}` });
      this.loading = false;
      this.mostrandoCrearCentro = false;
      this.confirmDialog.info('Solicitud guardada localmente — se enviará a ATC al reconectar.', { title: 'Guardado sin conexión' });
      this.nuevoCentro = { nombre_centro: '', direccion_completa: '', ciudad: '', estado: '' };
      return;
    }
    this.http.post<any>(`${this.API}/centros`, this.nuevoCentro).subscribe({
      next: (res) => {
        this.loading = false;
        this.mostrandoCrearCentro = false;
        this.confirmDialog.info(res.message || 'Solicitud enviada exitosamente.', { title: 'Solicitud enviada' });
        this.nuevoCentro = { nombre_centro: '', direccion_completa: '', ciudad: '', estado: '' };
      },
      error: () => {
        this.loading = false;
        this.confirmDialog.info('Hubo un error al enviar la solicitud.', { title: 'Error' });
      }
    });
  }

  confirmarApertura(centro: any) {
    this.centroAConfirmar = centro;
  }

  abrirEncuesta(centro: any) {
    this.centroAConfirmar = null;
    this.loading = true;
    if (!navigator.onLine) {
      const localId = this.offline.newLocalId();
      this.offline.enqueue({
        url: `${this.API}/encuestas`, jsonBody: { id_centro: centro.id_centro, fuente_informacion: 'Visita presencial', notas_generales: null },
        label: `Abrir encuesta ${centro.nombre_centro}`, producesLocalId: localId, idField: 'id_encuesta',
      });
      const optimista = {
        success: true, tiene_encuesta: true, jornada_activa: true,
        id_encuesta: localId, id_centro: centro.id_centro, nombre_centro: centro.nombre_centro,
        ciudad: centro.ciudad, estado: centro.estado, medicos: [],
      };
      this.encuestaActiva = optimista;
      this.offline.cacheWrite('encuesta-abierta', optimista);
      this.loading = false;
      return;
    }
    this.http.post<any>(`${this.API}/encuestas`, { id_centro: centro.id_centro }).subscribe({
      next: () => this.checkEncuesta(),
      error: () => this.loading = false
    });
  }

  async cerrarEncuesta() {
    const ok = await this.confirmDialog.confirm('¿Estás seguro de cerrar este centro?', { title: 'Cerrar centro', confirmText: 'Sí, cerrar' });
    if (!ok) return;
    this.loading = true;
    if (!navigator.onLine) {
      this.offline.enqueue({ url: `${this.API}/encuestas/${this.encuestaActiva.id_encuesta}/cerrar`, jsonBody: {}, label: `Cerrar encuesta ${this.encuestaActiva.nombre_centro}` });
      this.encuestaActiva = null;
      this.offline.cacheWrite('encuesta-abierta', { success: true, tiene_encuesta: false, jornada_activa: true });
      this.loading = false;
      return;
    }
    this.http.post(`${this.API}/encuestas/${this.encuestaActiva.id_encuesta}/cerrar`, {}).subscribe({
      next: () => this.checkEncuesta(),
      error: () => this.loading = false
    });
  }
}
