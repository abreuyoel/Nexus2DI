import { Component, computed, signal, HostListener, OnInit } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive, Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';
import { CommonModule } from '@angular/common';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatMenuModule } from '@angular/material/menu';
import { MatBadgeModule } from '@angular/material/badge';
import { MatTooltipModule } from '@angular/material/tooltip';
import { AuthService } from '../../core/services/auth.service';
import { ApiService } from '../../core/services/api.service';
import { RealtimeService } from '../../core/services/realtime.service';
import { ConfirmDialogComponent } from '../../shared/components/confirm-dialog/confirm-dialog.component';
import { ConfirmService } from '../../shared/components/confirm-dialog/confirm.service';
import { EncuestadorOfflineQueueService } from '../../features/encuestador/services/encuestador-offline-queue.service';

interface NavItem {
  label: string;
  icon: string;
  route: string;
  roles: string[];
  module?: string;
  hideForAdmin?: boolean;
}

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [
    CommonModule, RouterOutlet, RouterLink, RouterLinkActive,
    MatToolbarModule, MatSidenavModule, MatListModule,
    MatIconModule, MatButtonModule, MatMenuModule, MatBadgeModule, MatTooltipModule,
    ConfirmDialogComponent,
  ],
  templateUrl: './shell.component.html',
  styleUrls: ['./shell.component.scss']
})
export class ShellComponent implements OnInit {
  sidenavOpen = signal(window.innerWidth > 1024);
  isMobile = signal(window.innerWidth <= 1024);
  isDark = signal(false);
  notifCount = 0;

  user = computed(() => this.auth.currentUser());
  hasClientDashboard = signal(false);

  private navItems: NavItem[] = [
    { label: 'Dashboard', icon: 'dashboard', route: '/dashboard', roles: ['admin', 'analyst', 'supervisor', 'coordinador_general', 'coordinador_exclusivo'] },
    { label: 'Centro de Mando Gestión', icon: 'bolt', route: '/centro-mando', roles: ['admin', 'superadmin', 'analyst', 'coordinador_general', 'coordinador_exclusivo'] },
    { label: 'Centro de Mando Auditoría', icon: 'fact_check', route: '/centro-mando-auditoria', roles: ['admin', 'analyst'] },
    { label: 'Plan de Acción', icon: 'assignment_late', route: '/plan-accion', roles: ['admin', 'analyst'] },
    { label: 'Rutas', icon: 'route', route: '/routes', roles: ['admin', 'analyst'], module: 'rutas' },
    { label: 'Puntos de Venta', icon: 'store', route: '/points', roles: ['admin', 'supervisor', 'atc'] },
    { label: 'Usuarios', icon: 'people', route: '/users', roles: ['admin'], module: 'users' },
    { label: 'Permisos', icon: 'admin_panel_settings', route: '/permissions', roles: ['admin'] },
    { label: 'Productos', icon: 'inventory_2', route: '/products', roles: ['admin', 'atc'] },
    { label: 'Categorías Cliente', icon: 'category', route: '/client-categories', roles: ['admin'] },
    { label: 'SKU vs SKU', icon: 'compare_arrows', route: '/sku-competencia', roles: ['admin'] },
    { label: 'Clientes · Rutas', icon: 'alt_route', route: '/clientes-rutas', roles: ['admin', 'analyst'] },
    { label: 'Frecuencias PDVs', icon: 'event_repeat', route: '/frecuencias-pdvs-cliente', roles: ['admin', 'analyst'] },
    { label: 'Horas Promedio Ejecución', icon: 'schedule', route: '/horas-promedio-ejecucion', roles: ['admin'] },
    { label: 'Mis Rutas', icon: 'route', route: '/mercaderista', roles: ['mercaderista'], hideForAdmin: true },
    { label: 'Portal Mercaderista', icon: 'storefront', route: '/portal-mercaderista', roles: ['admin', 'mercaderista', 'supervisor'], hideForAdmin: false },
    { label: 'Auditoría de Campo', icon: 'fact_check', route: '/auditor-campo', roles: ['auditor_campo', 'admin'] },
    { label: 'Auditoría de Data', icon: 'inventory_2', route: '/auditoria-data', roles: ['auditor', 'admin'] },
    { label: 'Chat', icon: 'chat', route: '/chat', roles: [], module: 'chat' },
    { label: 'Supervisor', icon: 'supervisor_account', route: '/supervisor', roles: ['admin', 'supervisor'] },
    { label: 'Solicitudes', icon: 'support_agent', route: '/atencion-cliente', roles: ['admin', 'atc', 'analyst'] },
    { label: 'Auditoría Logs', icon: 'fact_check', route: '/audit', roles: ['admin'], module: 'audit' },
    { label: 'Grupos de Chat', icon: 'forum', route: '/admin/chat-grupos', roles: ['admin'] },
    { label: 'Mis Fotos', icon: 'photo_library', route: '/client', roles: ['coordinador_exclusivo', 'coordinador_tradex'], hideForAdmin: true },
    { label: 'Mis Visitas', icon: 'today', route: '/client/visits', roles: ['client', 'coordinador_exclusivo', 'coordinador_tradex'], hideForAdmin: true },
    { label: 'Data', icon: 'table_chart', route: '/data', roles: ['admin', 'analyst', 'client', 'coordinador_exclusivo', 'coordinador_tradex', 'coordinador_general'] },
    { label: 'Encuestador', icon: 'assignment', route: '/encuestador', roles: ['encuestador', 'admin'] },
    { label: 'Catálogos Encuestador', icon: 'settings', route: '/encuestador/configuracion', roles: ['encuestador', 'admin'] },
    { label: 'BI Encuestas', icon: 'pie_chart', route: '/cliente-encuestador', roles: ['cliente_encuestador', 'admin'] },
    { label: 'Supervisor Encuestadores', icon: 'supervisor_account', route: '/supervisor-encuestadores', roles: ['admin', 'supervisor'] },
    { label: 'Ventas', icon: 'point_of_sale', route: '/ventas', roles: ['vendedor', 'admin'] },

  ];

  visibleNavItems = computed(() => {
    const u = this.user();
    if (!u) return [];

    const isAdmin = !!u.is_admin || u.rol === 'admin';

    return this.navItems.filter((item) => {
      if (isAdmin && item.hideForAdmin) return false;

      // Admin ve todo su set; si el usuario tiene permisos configurados manda el
      // permiso (can_read de la clave del módulo); si no, se cae al rol.
      const clave = AuthService.claveFromRoute(item.route);
      return this.auth.canAccess(clave, item.roles);
    });
  });

  constructor(
    private auth: AuthService,
    private api: ApiService,
    private router: Router,
    private realtime: RealtimeService,
    private confirmDialog: ConfirmService,
    private offline: EncuestadorOfflineQueueService
  ) {
    this.loadNotifications();
  }

  ngOnInit(): void {
    // Conectar canal de eventos en tiempo real
    this.realtime.connect();

    // Inicializar tema
    this.initTheme();

    // Verificar dashboard si es cliente
    this.checkClientDashboard();

    // Cerrar sidebar al navegar en móviles
    this.router.events.pipe(
      filter((event: any) => event instanceof NavigationEnd)
    ).subscribe(() => {
      if (this.isMobile()) {
        this.sidenavOpen.set(false);
      }
    });
  }

  private checkClientDashboard(): void {
    const u = this.user();
    if (u && (u.is_client || u.rol === 'coordinador_exclusivo')) {
      this.api.getClientDashboard().subscribe({
        next: (res: any) => this.hasClientDashboard.set(res.has_dashboard),
        error: () => this.hasClientDashboard.set(false)
      });
    }
  }

  @HostListener('window:resize', ['$event'])
  onResize(): void {
    const mobile = window.innerWidth <= 1024;
    this.isMobile.set(mobile);
    if (mobile && this.sidenavOpen()) {
      this.sidenavOpen.set(false);
    } else if (!mobile && !this.sidenavOpen()) {
      this.sidenavOpen.set(true);
    }
  }

  toggleSidenav(): void { this.sidenavOpen.update((v) => !v); }

  toggleTheme(): void {
    this.isDark.update((v: boolean) => {
      const newVal = !v;
      localStorage.setItem('theme', newVal ? 'dark' : 'light');
      this.applyTheme(newVal);
      return newVal;
    });
  }

  private initTheme(): void {
    const savedTheme = localStorage.getItem('theme');
    const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const isDark = savedTheme === 'dark' || (!savedTheme && systemDark);

    this.isDark.set(isDark);
    this.applyTheme(isDark);
  }

  private applyTheme(dark: boolean): void {
    if (dark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }

  async intentarLogout(): Promise<void> {
    if (this.user()?.rol === 'encuestador') {
      const pendientes = await this.offline.getPendientes();
      if (pendientes.length > 0) {
        const ok = await this.confirmDialog.confirm(
          `Tienes ${pendientes.length} registros pendientes por subir o sincronizar porque estabas sin conexión. Si cierras sesión sin sincronizar, podrías causar problemas si otro usuario ingresa en este dispositivo. ¿Estás seguro de cerrar sesión?`,
          { title: 'Sincronización pendiente', confirmText: 'Sí, cerrar sesión', danger: true }
        );
        if (!ok) return;
      }
    }
    this.auth.logout();
  }

  private loadNotifications(): void {
    this.api.getRejectionNotifications().subscribe({
      next: (notifs: any[]) => { this.notifCount = notifs.length; },
      error: () => { },
    });
  }
}
