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

  get storagePct(): number { return Math.round((this.storage?.pct || 0) * 100); }

  cachedLocation: { lat: number | null, lng: number | null } | null = null;

  ngOnInit() {
    this.checkJornada();
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
}
