import { Component, OnInit, Input, signal, inject, computed, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTabsModule } from '@angular/material/tabs';
import { MatIconModule } from '@angular/material/icon';
import { MatBadgeModule } from '@angular/material/badge';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Router } from '@angular/router';
import { MercRutaComponent } from './components/merc-ruta/merc-ruta.component';
import { MercVisitasComponent } from './components/merc-visitas/merc-visitas.component';
import { MercVisitPanelComponent } from './components/merc-visit-panel/merc-visit-panel.component';
import { MercVisitaDetalleComponent } from './components/merc-visita-detalle/merc-visita-detalle.component';
import { MercPdvActivosComponent } from './components/merc-pdv-activos/merc-pdv-activos.component';
import { OfflineQueueService } from './services/offline-queue.service';
import { MercUiService } from './services/merc-ui.service';
import { AuthService } from '../../core/services/auth.service';
import { ApiService } from '../../core/services/api.service';
import { ConfirmService } from '../../shared/components/confirm-dialog/confirm.service';
import { ConfirmDialogComponent } from '../../shared/components/confirm-dialog/confirm-dialog.component';
import { BrowserNotificationService } from './services/browser-notification.service';

@Component({
  selector: 'app-mercaderista',
  standalone: true,
  imports: [
    CommonModule, MatTabsModule, MatIconModule, MatBadgeModule, MatButtonModule, MatProgressSpinnerModule,
    MercRutaComponent, MercVisitasComponent, MercVisitPanelComponent,
    MercVisitaDetalleComponent,
    MercPdvActivosComponent,
    ConfirmDialogComponent
  ],
  templateUrl: './mercaderista.component.html',
  styleUrls: ['./mercaderista.component.scss']
})
export class MercaderistaComponent implements OnInit {
  @Input() titulo = 'Panel Mercaderista';

  isOnline = signal(navigator.onLine);
  pendingPhotos = signal(0);
  today = new Date().toLocaleDateString('es-VE', { weekday: 'long', day: 'numeric', month: 'long' });

  activeScreen = signal<'dashboard' | 'carga-menu' | 'ruta' | 'visitas' | 'pdv-activos' | 'sync'>('dashboard');
  tipoRuta = signal<'fija' | 'variable'>('fija');
  syncSteps = signal<any[]>([]);
  loadingSync = signal(false);
  greeting = signal('');
  greetingIcon = signal('');

  // PDVs activos con trabajo pendiente hoy (desde /api/merc/pdv-activos)
  pdvActivos = signal<any[]>([]);
  activeRouteData = signal<{ id_ruta: number; nombre: string; tipo: string; pdvs_total: number; pdvs_visitados: number } | null>(null);
  loadingPdvActivos = signal(false);
  todayVisitsCount = signal(0);

  // True si hay un panel de visita abierto, PDVs activos pendientes, O una ruta activa en progreso
  hasActivePdv = computed(() =>
    this.ui.activeVisit() !== null ||
    this.pdvActivos().length > 0 ||
    this.ui.activeRouteId() !== null ||
    this.activeRouteData() !== null
  );

  private confirmSvc = inject(ConfirmService);
  ui = inject(MercUiService);
  private offline = inject(OfflineQueueService);
  private auth = inject(AuthService);
  private api = inject(ApiService);
  private router = inject(Router);
  private notif = inject(BrowserNotificationService);

  user = computed(() => this.auth.currentUser());

  constructor() {
    effect(() => {
      const active = this.ui.activeVisit();
      if (!active) {
        this.loadPdvActivos();
        this.loadTodayVisitsCount();
      }
    }, { allowSignalWrites: true });
  }

  ngOnInit(): void {
    this.offline.isOnline$.subscribe(v => this.isOnline.set(v));
    this.offline.pendingCount$.subscribe(v => this.pendingPhotos.set(v));
    this.updateGreeting();
    // Solicitar permiso de notificaciones del navegador al abrir el portal
    this.notif.requestPermission();
  }

  updateGreeting() {
    const h = new Date().getHours();
    if (h < 12) {
      this.greeting.set('Buenos días');
      this.greetingIcon.set('lightmode');
    } else if (h < 18) {
      this.greeting.set('Buenas tardes');
      this.greetingIcon.set('wb_sunny');
    } else {
      this.greeting.set('Buenas noches');
      this.greetingIcon.set('bedtime');
    }
  }

  changeScreen(screen: 'dashboard' | 'carga-menu' | 'ruta' | 'visitas' | 'pdv-activos' | 'sync') {
    this.activeScreen.set(screen);
    if (screen === 'dashboard' || screen === 'carga-menu') {
      this.loadPdvActivos();
      this.loadTodayVisitsCount();
    } else if (screen === 'sync') {
      this.cargarSyncSteps();
    }
  }

  goToCargaMenu() {
    this.activeScreen.set('carga-menu');
    this.loadPdvActivos();
  }

  resumeActiveVisit() {
    if (this.ui.activeVisit()) {
      // Ya hay panel abierto: simplemente volver al dashboard
      this.activeScreen.set('dashboard');
    } else if (this.pdvActivos().length > 0) {
      // Hay PDV activo pero sin panel abierto → navegar a pantalla PDV activos
      this.activeScreen.set('pdv-activos');
    } else if (this.activeRouteData() || this.ui.activeRouteId()) {
      const r = this.activeRouteData();
      if (r?.tipo?.toLowerCase() === 'variable') {
        this.tipoRuta.set('variable');
      } else {
        this.tipoRuta.set('fija');
      }
      this.activeScreen.set('ruta');
    }
  }

  private loadTodayVisitsCount() {
    const todayStr = new Date().toISOString().split('T')[0];
    this.api.getMercMisVisitas({ fecha_inicio: todayStr, fecha_fin: todayStr }).subscribe({
      next: (res) => {
        this.todayVisitsCount.set(res ? res.length : 0);
      },
      error: () => {
        this.todayVisitsCount.set(0);
      }
    });
  }

  private loadPdvActivos() {
    if (this.ui.cachedPdvActivos) {
      this.pdvActivos.set(this.ui.cachedPdvActivos);
      this.loadingPdvActivos.set(false);
    } else {
      this.loadingPdvActivos.set(true);
    }

    this.api.get<any[]>('/api/merc/pdv-activos').subscribe({
      next: (res) => {
        this.ui.cachedPdvActivos = res || [];
        this.pdvActivos.set(res || []);
        this.loadingPdvActivos.set(false);
      },
      error: () => {
        this.loadingPdvActivos.set(false);
      }
    });

    // Consultar estado de rutas activas hoy
    this.api.getMercMiRuta().subscribe({
      next: (res) => {
        this.ui.cachedMisRutas = res;
        const todas = [...(res.rutas_fijas || []), ...(res.rutas_variables || [])];
        const activa = todas.find((r: any) => r.activada === true && !r.finalizada);
        if (activa) {
          const pdvs = activa.pdvs || [];
          const visitados = pdvs.filter((p: any) => (p.clientes || []).some((c: any) => c.visitado || c.id_visita)).length;
          this.ui.setActiveRoute(activa.id_ruta);
          this.tipoRuta.set(activa.tipo?.toLowerCase() === 'variable' ? 'variable' : 'fija');
          this.activeRouteData.set({
            id_ruta: activa.id_ruta,
            nombre: activa.nombre,
            tipo: activa.tipo,
            pdvs_total: pdvs.length,
            pdvs_visitados: visitados,
          });
        } else {
          this.activeRouteData.set(null);
          this.ui.clearActiveRoute();
        }
      },
      error: () => {}
    });
  }

  goToRutaFija() {
    this.tipoRuta.set('fija');
    this.activeScreen.set('ruta');
  }

  goToRutaVariable() {
    this.tipoRuta.set('variable');
    this.activeScreen.set('ruta');
  }

  async cargarSyncSteps() {
    this.loadingSync.set(true);
    try {
      const chains = await this.offline.getChains();
      const steps: any[] = [];
      chains.forEach(c => {
        if (c.steps) {
          c.steps.forEach(s => {
            steps.push(s);
          });
        }
      });
      this.syncSteps.set(steps);
    } catch (e) {
      // ignore
    } finally {
      this.loadingSync.set(false);
    }
  }

  async logout() {
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
