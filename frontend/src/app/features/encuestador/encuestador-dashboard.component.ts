import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { EncuestadorOfflineQueueService, StorageHealth } from './services/encuestador-offline-queue.service';
import { ConfirmService } from '../../shared/components/confirm-dialog/confirm.service';

@Component({
  selector: 'app-encuestador-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  template: `
    <div class="p-6 max-w-4xl mx-auto">
      <div class="flex items-center justify-between mb-6">
        <h1 class="text-3xl font-bold text-white">Dashboard Encuestador</h1>
        <div class="flex items-center gap-2">
          <span class="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-wider px-2 py-1 rounded-full" [ngClass]="isOnline ? 'bg-emerald-950 text-emerald-400' : 'bg-red-950 text-red-400'">
            <span class="w-1.5 h-1.5 rounded-full" [ngClass]="isOnline ? 'bg-emerald-400' : 'bg-red-400'"></span>
            {{ isOnline ? 'En línea' : 'Sin conexión' }}
          </span>
          <button *ngIf="pendingSync > 0" (click)="sincronizar()" [disabled]="!isOnline" class="flex items-center gap-1 text-[10px] font-black uppercase tracking-wider px-2 py-1 rounded-full bg-amber-950 text-amber-400 disabled:opacity-60">
            <span class="material-icons !text-sm">sync</span>{{ pendingSync }} pendientes
          </button>
          <button *ngIf="pendingSync > 0" (click)="verPendientes()" class="text-[10px] font-black uppercase tracking-wider px-2 py-1 rounded-full bg-slate-800 text-slate-300">
            {{ mostrandoPendientes ? 'Ocultar' : 'Ver' }}
          </button>
        </div>
      </div>

      <!-- Sección de Correcciones Requeridas por el Supervisor -->
      <div *ngIf="correccionesPendientes.length > 0" class="mb-6 bg-amber-950/60 border border-amber-500/40 rounded-2xl p-5 shadow-lg shadow-amber-500/5 animate-in slide-in-from-top-4 duration-300 text-left">
        <div class="flex items-center gap-2 mb-3 text-amber-400">
          <span class="material-icons">warning</span>
          <h3 class="font-bold text-lg">Observaciones del Supervisor</h3>
        </div>
        <p class="text-xs text-amber-200/90 mb-4">El supervisor solicitó corregir la información de las siguientes visitas/encuestas:</p>
        
        <div class="space-y-3">
          <div *ngFor="let c of correccionesPendientes" class="bg-slate-950/60 border border-slate-800 rounded-xl p-4 flex flex-col md:flex-row justify-between items-start md:items-center gap-3">
            <div class="flex-1">
              <div class="font-bold text-white text-sm">{{ c.nombre_centro | uppercase }}</div>
              <div class="text-xs text-slate-400 mt-0.5">Fecha de visita: {{ c.fecha_verificacion | date:'dd/MM/yyyy' }}</div>
              <div class="mt-2 text-xs text-amber-350 bg-amber-950/30 border border-amber-900/60 p-2.5 rounded-lg">
                <strong class="text-amber-200">Motivo:</strong> {{ c.observacion_supervisor }}
              </div>
            </div>
            
            <button (click)="iniciarCorreccion(c)" class="shrink-0 text-xs font-black uppercase tracking-wider px-4 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-600 text-slate-950 transition-all flex items-center gap-1 shadow-lg shadow-amber-500/20">
              <span class="material-icons !text-sm">edit</span> Corregir Datos
            </button>
          </div>
        </div>
      </div>

      <div *ngIf="pendingSync > 0" class="mb-4 bg-amber-950/40 border border-amber-900/60 rounded-xl px-3 py-2">
        <p class="text-xs text-amber-200/90 font-semibold">
          {{ pendingSync }} registro(s) guardados en este dispositivo, esperando señal para subir.
          No cierres sesión ni borres los datos del navegador hasta que se sincronicen.
        </p>
        <div *ngIf="mostrandoPendientes" class="mt-2 space-y-1 border-t border-amber-900/50 pt-2">
          <div *ngFor="let e of pendientes" class="flex items-center justify-between gap-2 text-xs">
            <span class="text-amber-100/80 truncate">
              <span class="material-icons !text-xs align-middle" [class.text-red-400]="e.status === 'error'">
                {{ e.status === 'error' ? 'error_outline' : 'schedule' }}
              </span>
              {{ e.label }}
              <span *ngIf="e.error" class="text-red-400/80">— {{ e.error }}</span>
            </span>
            <button (click)="descartarPendiente(e)" class="shrink-0 text-[10px] font-black uppercase px-2 py-0.5 rounded bg-red-900/60 text-red-200">
              Descartar
            </button>
          </div>
        </div>
      </div>

      <!-- Espacio del dispositivo: avisa, NUNCA bloquea. Un médico encolado
           pesa ~2 KB, así que el problema nunca es la cola sino que el
           teléfono esté lleno (fotos, otras apps). -->
      <div *ngIf="storage?.nivel === 'critical'" class="mb-4 bg-red-950/60 border border-red-900 rounded-xl px-3 py-2">
        <p class="text-xs text-red-200 font-semibold">
          El teléfono está casi sin espacio ({{ storagePct }}% usado).
          Buscá señal y subí lo pendiente ahora, o liberá espacio: si se llena del todo,
          los próximos registros no se van a poder guardar.
        </p>
      </div>
      <div *ngIf="storage?.nivel === 'warn'" class="mb-4 bg-amber-950/40 border border-amber-900/60 rounded-xl px-3 py-2">
        <p class="text-xs text-amber-200/90 font-semibold">
          Queda poco espacio en el teléfono ({{ storagePct }}% usado).
          Conviene subir lo pendiente cuando agarres señal; después podés seguir sin conexión normalmente.
        </p>
      </div>
      <div *ngIf="pendingSync > 0 && storage?.soportado && !storage?.persisted" class="mb-4 bg-slate-800/60 border border-slate-700 rounded-xl px-3 py-2">
        <p class="text-xs text-slate-300">
          <span class="material-icons !text-xs align-middle">info</span>
          Este navegador no garantizó guardar los datos de forma permanente: si el teléfono se queda
          sin espacio podría borrarlos. Subí lo pendiente en cuanto tengas señal.
        </p>
      </div>

      <div *ngIf="syncError" class="mb-4 bg-red-950/60 border border-red-900 rounded-xl px-3 py-2 flex items-center justify-between gap-2">
        <span class="text-xs text-red-300 font-semibold">No se pudo sincronizar: {{ syncError }}</span>
        <button (click)="sincronizar()" class="text-[10px] font-black uppercase px-2 py-1 rounded-lg bg-red-900 text-red-200">Reintentar</button>
      </div>

      <div *ngIf="loading" class="text-white">Cargando...</div>
      
      <div *ngIf="!loading && !jornadaActiva" class="bg-slate-900 rounded-xl p-8 border border-white/10 shadow-lg text-center max-w-2xl mx-auto mt-10">
        <div class="mb-4 flex justify-center">
          <div class="w-16 h-16 rounded-full border-2 border-indigo-500 flex items-center justify-center text-indigo-500">
            <span class="material-icons text-4xl ml-1">play_arrow</span>
          </div>
        </div>
        <h2 class="text-2xl font-semibold text-white mb-2">Inicia tu jornada</h2>
        <p class="text-slate-400 mb-8">Activa para comenzar a visitar centros de salud y registrar médicos.</p>
        <button (click)="activarJornada()" class="w-full bg-emerald-500 hover:bg-emerald-600 text-white font-bold py-4 rounded-lg transition-colors flex items-center justify-center gap-2 text-lg">
          <span class="material-icons">rocket_launch</span> Activar Jornada
        </button>
      </div>

      <div *ngIf="!loading && jornadaActiva" class="bg-slate-900 rounded-xl p-6 border border-emerald-500/30 shadow-[0_0_15px_rgba(16,185,129,0.2)]">
        <div class="flex justify-between items-center mb-6">
          <h2 class="text-2xl font-bold text-emerald-400">Jornada en Progreso</h2>
          <button (click)="finalizarJornada()" class="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg transition-colors text-sm font-semibold">
            Finalizar Jornada
          </button>
        </div>
        
        <div class="grid grid-cols-2 gap-4 mb-6">
          <div class="bg-slate-800 p-4 rounded-lg border border-slate-700">
            <div class="text-slate-400 text-sm">Centros Visitados</div>
            <div class="text-3xl font-bold text-white">{{ stats.centros_visitados }}</div>
          </div>
          <div class="bg-slate-800 p-4 rounded-lg border border-slate-700">
            <div class="text-slate-400 text-sm">Médicos Registrados</div>
            <div class="text-3xl font-bold text-white">{{ stats.medicos_registrados }}</div>
          </div>
        </div>
        
        <button routerLink="/encuestador/centro" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-4 rounded-lg transition-colors text-lg shadow-lg">
          Gestionar Centro de Salud
        </button>
      </div>

      <!-- Modal de Corrección de Encuesta -->
      <div *ngIf="showCorreccionModal" class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 overflow-y-auto animate-in fade-in">
        <div class="bg-slate-900 rounded-3xl p-6 max-w-lg w-full border border-slate-700/80 shadow-2xl relative my-8 text-left">
          <div class="absolute top-0 left-0 w-full h-1.5 bg-gradient-to-r from-amber-500 to-orange-500"></div>
          <div class="flex justify-between items-center mb-6">
            <h3 class="text-xl font-bold text-white flex items-center gap-2"><span class="material-icons text-amber-400">warning</span> Corregir Datos de Encuesta</h3>
            <button (click)="showCorreccionModal = false" class="text-slate-400 hover:text-white w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center transition-colors"><span class="material-icons !text-lg">close</span></button>
          </div>

          <div class="space-y-4 max-h-[60vh] overflow-y-auto pr-2 custom-scrollbar">
            <div class="p-3 bg-amber-950/20 border border-amber-900/50 rounded-xl mb-4 text-xs text-amber-200">
              <strong>Observación del Supervisor:</strong> {{ currentCorreccion.observacion_supervisor }}
            </div>

            <div>
              <label class="block text-xs font-bold text-slate-400 mb-1 uppercase tracking-wider">Centro de Salud</label>
              <div class="bg-slate-950 border border-slate-800 rounded-xl p-3 text-slate-300 font-semibold">{{ currentCorreccion.nombre_centro }}</div>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-bold text-slate-400 mb-1 uppercase tracking-wider">Fecha de Visita</label>
                <div class="bg-slate-950 border border-slate-800 rounded-xl p-3 text-slate-300">{{ currentCorreccion.fecha_verificacion | date:'dd/MM/yyyy' }}</div>
              </div>
              <div>
                <label class="block text-xs font-bold text-slate-400 mb-1 uppercase tracking-wider">Fuente de Información *</label>
                <input type="text" [(ngModel)]="currentCorreccion.fuente_informacion" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-white focus:border-amber-500 outline-none">
              </div>
            </div>

            <div>
              <label class="block text-xs font-bold text-slate-400 mb-1 uppercase tracking-wider">Notas Generales</label>
              <textarea [(ngModel)]="currentCorreccion.notas_generales" rows="2" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-white focus:border-amber-500 outline-none resize-none"></textarea>
            </div>

            <!-- Lista de Médicos -->
            <div class="mt-6 border-t border-white/5 pt-4">
              <h4 class="text-xs font-black text-slate-400 uppercase tracking-wider mb-3">Médicos Registrados ({{ currentCorreccion.medicos?.length || 0 }})</h4>
              <div class="space-y-2">
                <div *ngFor="let m of currentCorreccion.medicos" class="bg-slate-800 border border-slate-700 rounded-xl p-3 flex justify-between items-center text-xs">
                  <div>
                    <div class="font-bold text-white">{{ m.apellido1 }} {{ m.apellido2 }}, {{ m.nombre1 }}</div>
                    <div class="text-[10px] text-violet-400 uppercase font-black tracking-wider mt-0.5">{{ m.especialidad }}</div>
                  </div>
                  <button (click)="editarMedico(m)" class="px-2.5 py-1.5 bg-slate-700 hover:bg-slate-600 text-amber-400 hover:text-amber-300 rounded-lg font-bold transition-all flex items-center gap-1 shadow">
                    <span class="material-icons !text-xs">edit</span> Editar
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div class="mt-6 flex gap-3">
            <button (click)="guardarCorreccion()" class="flex-1 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-slate-950 font-bold py-3.5 rounded-xl transition-all shadow-lg shadow-amber-500/10">
              Enviar Corrección
            </button>
            <button (click)="showCorreccionModal = false" class="flex-1 bg-slate-800 hover:bg-slate-700 text-white font-bold py-3.5 rounded-xl border border-slate-700 transition-colors">
              Cancelar
            </button>
          </div>
        </div>
      </div>

      <!-- Modal de Edición de Médico -->
      <div *ngIf="showEditMedicoModal" class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 overflow-y-auto animate-in fade-in">
        <div class="bg-slate-900 rounded-3xl p-6 max-w-lg w-full border border-slate-700/80 shadow-2xl relative my-8 text-left">
          <div class="absolute top-0 left-0 w-full h-1.5 bg-gradient-to-r from-amber-500 to-orange-500"></div>
          <div class="flex justify-between items-center mb-6">
            <h3 class="text-xl font-bold text-white flex items-center gap-2"><span class="material-icons text-amber-400">person_add</span> Corregir Datos de Médico</h3>
            <button (click)="showEditMedicoModal = false" class="text-slate-400 hover:text-white w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center transition-colors"><span class="material-icons !text-lg">close</span></button>
          </div>

          <div class="space-y-4 max-h-[60vh] overflow-y-auto pr-2 custom-scrollbar">
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-bold text-slate-400 mb-1 uppercase tracking-wider">Cédula *</label>
                <input type="text" [(ngModel)]="currentMedico.id_medico_externo" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-white focus:border-amber-500 outline-none">
              </div>
              <div>
                <label class="block text-xs font-bold text-slate-400 mb-1 uppercase tracking-wider">Primer Nombre *</label>
                <input type="text" [(ngModel)]="currentMedico.nombre1" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-white focus:border-amber-500 outline-none">
              </div>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-bold text-slate-400 mb-1 uppercase tracking-wider">Primer Apellido *</label>
                <input type="text" [(ngModel)]="currentMedico.apellido1" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-white focus:border-amber-500 outline-none">
              </div>
              <div>
                <label class="block text-xs font-bold text-slate-400 mb-1 uppercase tracking-wider">Especialidad *</label>
                <input type="text" [(ngModel)]="currentMedico.especialidad" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-white focus:border-amber-500 outline-none">
              </div>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-bold text-slate-400 mb-1 uppercase tracking-wider">Teléfono</label>
                <input type="text" [(ngModel)]="currentMedico.telefono" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-white focus:border-amber-500 outline-none">
              </div>
              <div>
                <label class="block text-xs font-bold text-slate-400 mb-1 uppercase tracking-wider">WhatsApp</label>
                <input type="text" [(ngModel)]="currentMedico.whatsapp" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-white focus:border-amber-500 outline-none">
              </div>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-bold text-slate-400 mb-1 uppercase tracking-wider">Ciudad *</label>
                <input type="text" [(ngModel)]="currentMedico.ciudad" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-white focus:border-amber-500 outline-none">
              </div>
              <div>
                <label class="block text-xs font-bold text-slate-400 mb-1 uppercase tracking-wider">Estado *</label>
                <input type="text" [(ngModel)]="currentMedico.estado" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-white focus:border-amber-500 outline-none">
              </div>
            </div>

            <!-- Consultorios -->
            <div class="mt-4">
              <div class="flex justify-between items-center border-b border-white/5 pb-2 mb-3">
                <h4 class="text-xs font-black text-slate-400 uppercase tracking-wider">Consultorios</h4>
                <button (click)="addConsultorio()" class="text-[10px] font-black bg-slate-800 hover:bg-slate-700 text-amber-400 px-2 py-1 rounded">+ Añadir</button>
              </div>
              <div *ngFor="let c of currentMedico.consultorios; let idx = index" class="bg-slate-950/60 border border-slate-800 rounded-xl p-3 mb-3 relative">
                <button (click)="removeConsultorio(idx)" class="absolute top-2 right-2 text-rose-500"><span class="material-icons !text-base">delete</span></button>
                <div class="grid grid-cols-2 gap-2 mb-2">
                  <div>
                    <label class="block text-[9px] font-bold text-slate-400">Clínica *</label>
                    <input type="text" [(ngModel)]="c.nombre_clinica" class="w-full bg-slate-900 border border-slate-800 rounded p-2 text-xs text-white">
                  </div>
                  <div>
                    <label class="block text-[9px] font-bold text-slate-400">Piso</label>
                    <input type="text" [(ngModel)]="c.piso_consultorio" class="w-full bg-slate-900 border border-slate-800 rounded p-2 text-xs text-white">
                  </div>
                </div>
                <div class="grid grid-cols-2 gap-2">
                  <div>
                    <label class="block text-[9px] font-bold text-slate-400">Valor Consulta</label>
                    <select [(ngModel)]="c.valor_consulta_rango" class="w-full bg-slate-900 border border-slate-800 rounded p-2 text-xs text-white">
                      <option value="Menos de 30$">Menos de 30$</option>
                      <option value="Entre 30$ a 50$">Entre 30$ a 50$</option>
                      <option value="Entre 50$ a 60$">Entre 50$ a 60$</option>
                      <option value="Entre 60$ a 100$">Entre 60$ a 100$</option>
                      <option value="Más de 100$">Más de 100$</option>
                    </select>
                  </div>
                  <div>
                    <label class="block text-[9px] font-bold text-slate-400">Pacientes Semanal</label>
                    <select [(ngModel)]="c.promedio_pacientes_semanal_rango" class="w-full bg-slate-900 border border-slate-800 rounded p-2 text-xs text-white">
                      <option value="1 a 5 pacientes">1 a 5 pacientes</option>
                      <option value="6 a 10 pacientes">6 a 10 pacientes</option>
                      <option value="11 a 15 pacientes">11 a 15 pacientes</option>
                      <option value="16 a 20 pacientes">16 a 20 pacientes</option>
                      <option value="21 a 30 pacientes">21 a 30 pacientes</option>
                      <option value="Más de 30 pacientes">Más de 30 pacientes</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="mt-6 flex gap-3">
            <button (click)="guardarMedico()" class="flex-1 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-slate-950 font-bold py-3 rounded-xl transition-all">
              Aceptar
            </button>
            <button (click)="showEditMedicoModal = false" class="flex-1 bg-slate-800 hover:bg-slate-700 text-white font-bold py-3 rounded-xl border border-slate-700 transition-colors">
              Cancelar
            </button>
          </div>
        </div>
      </div>
    </div>
  `
})
export class EncuestadorDashboardComponent implements OnInit {
  private http = inject(HttpClient);
  private router = inject(Router);
  private offline = inject(EncuestadorOfflineQueueService);
  private confirmDialog = inject(ConfirmService);
  private API = `${environment.apiUrl}/api/encuestador`;

  loading = true;
  jornadaActiva = false;
  stats: any = { centros_visitados: 0, medicos_registrados: 0 };
  isOnline = navigator.onLine;
  pendingSync = 0;
  syncError: string | null = null;
  pendientes: any[] = [];
  mostrandoPendientes = false;
  storage: StorageHealth | null = null;

  // Correcciones del supervisor
  correccionesPendientes: any[] = [];
  showCorreccionModal = false;
  showEditMedicoModal = false;
  currentCorreccion: any = { medicos: [] };
  currentMedico: any = { consultorios: [] };

  get storagePct(): number { return Math.round((this.storage?.pct || 0) * 100); }

  cachedLocation: { lat: number | null, lng: number | null } | null = null;

  ngOnInit() {
    this.checkJornada();
    this.loadCorrecciones();
    this.offline.isOnline$.subscribe(v => this.isOnline = v);
    this.offline.pendingCount$.subscribe(v => { this.pendingSync = v; this.refrescarStorage(); });
    this.offline.syncError$.subscribe(e => this.syncError = e?.error || null);
    if (navigator.onLine) {
      this.offline.syncAll();
      // Deja centros y catálogos en IndexedDB mientras todavía hay señal, que
      // es lo único que hace falta para completar una jornada entera adentro
      // de un centro de salud sin cobertura.
      this.offline.prefetchReference(this.API);
    }
    // Que el navegador no desaloje la cola solo cuando al teléfono le falte
    // espacio -- es la forma más probable de perder una jornada entera en un
    // dispositivo de gama baja.
    this.offline.requestPersistence().then(() => this.refrescarStorage());
    
    // Precargar geolocalización en background
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => { this.cachedLocation = { lat: pos.coords.latitude, lng: pos.coords.longitude }; },
        () => { this.cachedLocation = { lat: null, lng: null }; },
        { timeout: 5000 }
      );
    }
  }

  sincronizar() { this.offline.syncAll(); }

  checkJornada() {
    this.http.get<any>(`${this.API}/jornada-activa`).subscribe({
      next: (res) => {
        this.jornadaActiva = res.activa;
        if (res.activa) {
          this.stats = {
            centros_visitados: res.centros_visitados,
            medicos_registrados: res.medicos_registrados
          };
        }
        this.loading = false;
        this.offline.cacheWrite('jornada-activa', res);
      },
      error: async () => {
        const cached = await this.offline.cacheRead('jornada-activa');
        if (cached) {
          this.jornadaActiva = cached.activa;
          if (cached.activa) this.stats = { centros_visitados: cached.centros_visitados, medicos_registrados: cached.medicos_registrados };
        }
        this.loading = false;
      }
    });
  }

  activarJornada() {
    this.loading = true;
    if (this.cachedLocation) {
      this.doActivar(this.cachedLocation.lat, this.cachedLocation.lng);
    } else if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => this.doActivar(pos.coords.latitude, pos.coords.longitude),
        () => this.doActivar(null, null),
        { timeout: 5000 }
      );
    } else {
      this.doActivar(null, null);
    }
  }

  async doActivar(lat: number | null, lng: number | null) {
    const body = { latitud: lat, longitud: lng, ciudad: '', estado_geo: '' };
    try {
      const { queued } = await this.offline.postOrQueue(
        `${this.API}/activar-jornada`, body, { label: 'Activar jornada' },
      );
      if (queued) {
        await this.offline.cacheWrite('jornada-activa', { success: true, activa: true, centros_visitados: 0, medicos_registrados: 0 });
      }
      // En lugar de quedarse en el dashboard, redirigir directo a seleccionar centro
      this.router.navigate(['/encuestador/centro']);
    } catch (err: any) {
      this.loading = false;
      this.confirmDialog.info('No se pudo activar la jornada: ' + (err.error?.detail || err.message), { title: 'Error' });
    }
  }

  async finalizarJornada() {
    const pend = await this.offline.getPendientes();
    const aviso = pend.length
      ? `\n\nOJO: quedan ${pend.length} registro(s) sin subir. No cierres sesión ni borres los datos del navegador hasta que se sincronicen.`
      : '';
    const ok = await this.confirmDialog.confirm(
      '¿Estás seguro de finalizar la jornada actual?' + aviso,
      { title: 'Finalizar jornada', confirmText: 'Sí, finalizar', danger: true },
    );
    if (!ok) return;
    this.loading = true;
    try {
      const { queued } = await this.offline.postOrQueue(
        `${this.API}/finalizar-jornada`, {}, { label: 'Finalizar jornada' },
      );
      if (queued) {
        await this.offline.cacheWrite('jornada-activa', { success: true, activa: false });
        await this.offline.cacheWrite('encuesta-abierta', { success: true, tiene_encuesta: false, jornada_activa: false });
      }
      this.checkJornada();
    } catch (err: any) {
      this.loading = false;
      this.confirmDialog.info('No se pudo finalizar la jornada: ' + (err.error?.detail || err.message), { title: 'Error' });
    }
  }

  async refrescarStorage() {
    this.storage = await this.offline.getStorageHealth();
  }

  async verPendientes() {
    this.pendientes = await this.offline.getPendientes();
    this.mostrandoPendientes = !this.mostrandoPendientes;
    this.refrescarStorage();
  }

  async descartarPendiente(e: any) {
    const ok = await this.confirmDialog.confirm(
      `Se va a borrar definitivamente "${e.label}" de este dispositivo. Esa carga se pierde y hay que rehacerla. ¿Continuar?`,
      { title: 'Descartar registro pendiente', confirmText: 'Sí, descartar', danger: true },
    );
    if (!ok) return;
    await this.offline.descartar(e.id);
    this.pendientes = await this.offline.getPendientes();
  }

  loadCorrecciones() {
    if (!navigator.onLine) return;
    this.http.get<any[]>(`${environment.apiUrl}/api/encuestador/correcciones-pendientes`).subscribe({
      next: (res) => this.correccionesPendientes = res || [],
      error: () => {}
    });
  }

  iniciarCorreccion(c: any) {
    this.currentCorreccion = JSON.parse(JSON.stringify(c));
    this.showCorreccionModal = true;
  }

  guardarCorreccion() {
    this.loading = true;
    this.http.put(`${environment.apiUrl}/api/encuestador/encuestas/${this.currentCorreccion.id_encuesta}`, {
      fuente_informacion: this.currentCorreccion.fuente_informacion,
      notas_generales: this.currentCorreccion.notas_generales
    }).subscribe({
      next: () => {
        this.showCorreccionModal = false;
        this.loadCorrecciones();
        this.checkJornada();
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        this.confirmDialog.info('Error al guardar corrección: ' + (err.error?.detail || err.message));
      }
    });
  }

  editarMedico(m: any) {
    this.currentMedico = JSON.parse(JSON.stringify(m));
    this.showEditMedicoModal = true;
  }

  addConsultorio() {
    this.currentMedico.consultorios.push({
      nombre_clinica: '',
      piso_consultorio: '',
      valor_consulta_rango: 'Menos de 30$',
      promedio_pacientes_semanal_rango: '1 a 5 pacientes'
    });
  }

  removeConsultorio(idx: number) {
    this.currentMedico.consultorios.splice(idx, 1);
  }

  guardarMedico() {
    this.loading = true;
    this.http.put(`${environment.apiUrl}/api/encuestador/medicos/${this.currentMedico.id_medico}`, this.currentMedico).subscribe({
      next: () => {
        // Actualizar el médico en la lista local de currentCorreccion
        const idx = this.currentCorreccion.medicos.findIndex((x: any) => x.id_medico === this.currentMedico.id_medico);
        if (idx !== -1) {
          this.currentCorreccion.medicos[idx] = { ...this.currentMedico };
        }
        this.showEditMedicoModal = false;
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        this.confirmDialog.info('Error al guardar médico: ' + (err.error?.detail || err.message));
      }
    });
  }
}
