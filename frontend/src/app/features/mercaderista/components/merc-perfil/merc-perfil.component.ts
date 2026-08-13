import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Router } from '@angular/router';
import { ApiService } from '../../../../core/services/api.service';
import { AuthService } from '../../../../core/services/auth.service';
import { OfflineQueueService } from '../../services/offline-queue.service';
import { ConfirmService } from '../../../../shared/components/confirm-dialog/confirm.service';
import { ConfirmDialogComponent } from '../../../../shared/components/confirm-dialog/confirm-dialog.component';

@Component({
  selector: 'app-merc-perfil',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatButtonModule, MatProgressSpinnerModule, ConfirmDialogComponent],
  template: `
    <div class="p-6 space-y-6 pb-20">

      <!-- Profile Hero -->
      <div class="flex flex-col items-center text-center space-y-4 py-4">
        <div class="relative">
          <div class="w-24 h-24 rounded-[2.5rem] bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-xl shadow-primary-500/30">
            <mat-icon class="!text-5xl text-white">person</mat-icon>
          </div>
          <div class="absolute -bottom-1 -right-1 w-8 h-8 rounded-2xl bg-emerald-500 border-4 border-white dark:border-slate-900 flex items-center justify-center text-white shadow">
            <mat-icon class="!text-sm">verified</mat-icon>
          </div>
        </div>
        <div>
          <h2 class="text-2xl font-black text-slate-800 dark:text-white tracking-tight">{{ nombreDisplay() }}</h2>
          <p class="text-xs font-black text-primary-500 uppercase tracking-[0.2em] opacity-80 mt-1">Mercaderista Autorizado</p>
        </div>
      </div>

      <!-- Info Cards -->
      <div class="grid grid-cols-1 gap-3">
        <div class="bg-white dark:bg-slate-900 p-5 rounded-3xl border border-slate-100 dark:border-white/5 shadow-sm flex items-center gap-4">
          <div class="w-10 h-10 rounded-2xl bg-slate-50 dark:bg-white/5 flex items-center justify-center text-slate-400">
            <mat-icon>badge</mat-icon>
          </div>
          <div class="flex flex-col">
            <span class="text-[9px] font-black text-slate-400 uppercase tracking-widest">Cédula</span>
            <span class="font-bold text-slate-700 dark:text-slate-200">{{ cedulaDisplay() }}</span>
          </div>
        </div>

        <div class="bg-white dark:bg-slate-900 p-5 rounded-3xl border border-slate-100 dark:border-white/5 shadow-sm flex items-center gap-4">
          <div class="w-10 h-10 rounded-2xl bg-slate-50 dark:bg-white/5 flex items-center justify-center text-slate-400">
            <mat-icon>email</mat-icon>
          </div>
          <div class="flex flex-col min-w-0">
            <span class="text-[9px] font-black text-slate-400 uppercase tracking-widest">Correo</span>
            <span class="font-bold text-slate-700 dark:text-slate-200 truncate">{{ perfil()?.email || 'N/A' }}</span>
          </div>
        </div>

        @if (perfil()?.rutas?.length > 0) {
          <div class="bg-white dark:bg-slate-900 p-5 rounded-3xl border border-slate-100 dark:border-white/5 shadow-sm">
            <div class="flex items-center gap-3 mb-3">
              <div class="w-10 h-10 rounded-2xl bg-slate-50 dark:bg-white/5 flex items-center justify-center text-slate-400">
                <mat-icon>route</mat-icon>
              </div>
              <span class="text-[9px] font-black text-slate-400 uppercase tracking-widest">Rutas Asignadas</span>
            </div>
            <div class="space-y-1.5">
              @for (r of perfil().rutas; track r.id_ruta) {
                <div class="flex items-center justify-between px-3 py-2 bg-slate-50 dark:bg-white/5 rounded-xl">
                  <span class="text-xs font-bold text-slate-700 dark:text-slate-200">{{ r.nombre }}</span>
                  <span class="text-[9px] font-black text-primary-500 uppercase tracking-widest">{{ r.tipo }}</span>
                </div>
              }
            </div>
          </div>
        }
      </div>

      <!-- Sincronización -->
      <div class="bg-indigo-600/5 dark:bg-indigo-500/5 rounded-[2rem] p-6 border border-indigo-500/10 space-y-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <mat-icon class="text-indigo-500">cloud_sync</mat-icon>
            <h3 class="font-bold text-slate-800 dark:text-white text-sm">Estado de Sincronización</h3>
          </div>
          @if (syncing()) {
            <mat-spinner diameter="16" strokeWidth="3"></mat-spinner>
          }
        </div>
        <div class="flex items-center justify-between p-4 bg-white dark:bg-slate-900/50 rounded-2xl border border-indigo-500/5 shadow-sm">
          <div class="flex flex-col">
            <span class="text-[9px] font-black text-slate-400 uppercase tracking-widest">Elementos Pendientes</span>
            <span class="text-xl font-black text-slate-800 dark:text-white">{{ pendingCount() }}</span>
          </div>
          <button (click)="syncNow()" [disabled]="pendingCount() === 0 || syncing() || !isOnline()"
                  class="px-4 py-2 bg-indigo-600 text-white rounded-xl text-[10px] font-black uppercase tracking-widest disabled:opacity-30 active:scale-95 transition-all">
            Sincronizar
          </button>
        </div>
        <p class="text-[9px] text-slate-400 italic text-center px-4">
          {{ isOnline() ? 'Conectado — las gestiones se suben automáticamente.' : 'Sin conexión — las gestiones se guardan localmente.' }}
        </p>
      </div>

      <!-- Cerrar Sesión -->
      <button (click)="logout()"
              class="w-full flex items-center justify-center gap-3 py-4 rounded-[2rem] bg-rose-500/10 text-rose-500 border border-rose-500/10 font-black uppercase tracking-widest text-xs hover:bg-rose-500 hover:text-white transition-all active:scale-95">
        <mat-icon>logout</mat-icon>
        Cerrar Sesión
      </button>

      <div class="text-center space-y-1 py-2">
        <p class="text-[10px] font-black text-slate-300 dark:text-slate-700 uppercase tracking-[0.3em]">AstroWeb V2.0</p>
        <p class="text-[8px] text-slate-400">Desarrollado por Antigravity</p>
      </div>
    </div>
    <app-confirm-dialog />
  `,
  styles: [`:host { display: block; }`]
})
export class MercPerfilComponent implements OnInit {
  private api = inject(ApiService);
  private auth = inject(AuthService);
  private offline = inject(OfflineQueueService);
  private confirmSvc = inject(ConfirmService);
  private router = inject(Router);

  perfil = signal<any>(null);
  pendingCount = signal(0);
  isOnline = signal(navigator.onLine);
  syncing = signal(false);

  nombreDisplay = () => {
    const p = this.perfil();
    if (p?.nombre) return p.nombre;
    const u = this.auth.currentUser();
    return (u as any)?.nombre || (u as any)?.username || 'Mercaderista';
  };

  cedulaDisplay = () => {
    const p = this.perfil();
    if (p?.cedula) return p.cedula;
    const u = this.auth.currentUser();
    return (u as any)?.cedula || 'N/A';
  };

  ngOnInit(): void {
    this.api.getMercMiPerfil().subscribe({
      next: (res) => this.perfil.set(res),
      error: () => {} // usa datos del token como fallback
    });
    this.offline.pendingCount$.subscribe(v => this.pendingCount.set(v));
    this.offline.isOnline$.subscribe(v => this.isOnline.set(v));
  }

  async syncNow(): Promise<void> {
    this.syncing.set(true);
    await this.offline.syncQueue();
    this.syncing.set(false);
  }

  async logout(): Promise<void> {
    const confirmed = await this.confirmSvc.confirm('¿Confirmas cerrar sesión?', {
      title: 'Cerrar Sesión',
      confirmText: 'Cerrar Sesión',
      cancelText: 'Cancelar',
      danger: true
    });
    if (confirmed) {
      await this.auth.logout();
      this.router.navigateByUrl('/login');
    }
  }
}
