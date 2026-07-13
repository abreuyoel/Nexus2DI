import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { EncuestadorOfflineQueueService } from './services/encuestador-offline-queue.service';
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
          <button *ngIf="pendingSync > 0" (click)="sincronizar()" [disabled]="!isOnline" class="flex items-center gap-1 text-[10px] font-black uppercase tracking-wider px-2 py-1 rounded-full bg-amber-950 text-amber-400">
            <span class="material-icons !text-sm">sync</span>{{ pendingSync }} pendientes
          </button>
        </div>
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

  ngOnInit() {
    this.checkJornada();
    this.offline.isOnline$.subscribe(v => this.isOnline = v);
    this.offline.pendingCount$.subscribe(v => this.pendingSync = v);
    this.offline.syncError$.subscribe(e => this.syncError = e?.error || null);
    if (navigator.onLine) this.offline.syncAll();
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
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => this.doActivar(pos.coords.latitude, pos.coords.longitude),
        () => this.doActivar(null, null),
        { timeout: 5000 }
      );
    } else {
      this.doActivar(null, null);
    }
  }

  doActivar(lat: number | null, lng: number | null) {
    const body = { latitud: lat, longitud: lng, ciudad: '', estado_geo: '' };
    if (!navigator.onLine) {
      this.offline.enqueue({ url: `${this.API}/activar-jornada`, jsonBody: body, label: 'Activar jornada' });
      this.offline.cacheWrite('jornada-activa', { success: true, activa: true, centros_visitados: 0, medicos_registrados: 0 });
      this.router.navigate(['/encuestador/centro']);
      return;
    }
    this.http.post<any>(`${this.API}/activar-jornada`, body).subscribe({
      next: () => {
        // En lugar de quedarse en el dashboard, redirigir directo a seleccionar centro
        this.router.navigate(['/encuestador/centro']);
      },
      error: () => this.loading = false
    });
  }

  async finalizarJornada() {
    const ok = await this.confirmDialog.confirm('¿Estás seguro de finalizar la jornada actual?', { title: 'Finalizar jornada', confirmText: 'Sí, finalizar', danger: true });
    if (!ok) return;
    this.loading = true;
    if (!navigator.onLine) {
      this.offline.enqueue({ url: `${this.API}/finalizar-jornada`, jsonBody: {}, label: 'Finalizar jornada' });
      this.offline.cacheWrite('jornada-activa', { success: true, activa: false });
      this.offline.cacheWrite('encuesta-abierta', { success: true, tiene_encuesta: false, jornada_activa: false });
      this.checkJornada();
      return;
    }
    this.http.post(`${this.API}/finalizar-jornada`, {}).subscribe({
      next: () => this.checkJornada(),
      error: () => this.loading = false
    });
  }
}
