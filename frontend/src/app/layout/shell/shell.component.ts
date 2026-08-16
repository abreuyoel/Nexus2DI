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
  // Estos son la navegación PROPIA de otro rol (mercaderista/cliente) --
  // como canAccess() da acceso total a admin sin importar `roles`, sin esto
  // le aparecían igual en el sidebar aunque no tenga sentido para su flujo.
  hideForAdmin?: boolean;
  // Sub-ítems del sidebar (p.ej. Power BI bajo Dashboard)
  children?: NavItem[];
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
  notifCount = signal(0);
  private wasMobile = window.innerWidth <= 1024;

  user = computed(() => this.auth.currentUser());
  hasClientDashboard = signal(false);

  private navItems: NavItem[] = [
    // --- Items admin/analyst/supervisor/coordinador ---
    {
      label: 'Dashboard', icon: 'dashboard', route: '/dashboard',
      roles: ['admin', 'analyst', 'supervisor', 'coordinador_general', 'coordinador_exclusivo'],
    },
    { label: 'Centro de Mando Gestión', icon: 'bolt', route: '/centro-mando', roles: ['admin', 'superadmin', 'analyst', 'coordinador_general', 'coordinador_exclusivo'] },
    { label: 'Centro de Mando Auditoría', icon: 'fact_check', route: '/centro-mando-auditoria', roles: ['admin', 'analyst'] },
    { label: 'Plan de Acción', icon: 'assignment_late', route: '/plan-accion', roles: ['admin', 'analyst'] },
    { label: 'Quiebre Dinámico', icon: 'trending_down', route: '/quiebre', roles: ['admin', 'analyst'] },
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
    { label: 'Auditoría Logs', icon: 'fact_check', route: '/audit', roles: ['admin'] },
    { label: 'Grupos de Chat', icon: 'forum', route: '/admin/chat-grupos', roles: ['admin'] },
    // Mis Fotos solo para coordinadores (no para cliente puro)
    { label: 'Mis Fotos', icon: 'photo_library', route: '/client', roles: ['coordinador_exclusivo', 'coordinador_tradex'], hideForAdmin: true },
    { label: 'Mis Visitas', icon: 'today', route: '/client/visits', roles: ['coordinador_exclusivo', 'coordinador_tradex'], hideForAdmin: true },
    { label: 'Data', icon: 'table_chart', route: '/data', roles: ['admin', 'analyst', 'coordinador_exclusivo', 'coordinador_tradex', 'coordinador_general'] },
    { label: 'Encuestador', icon: 'assignment', route: '/encuestador', roles: ['encuestador', 'admin'] },
    { label: 'Catálogos Encuestador', icon: 'settings', route: '/encuestador/configuracion', roles: ['encuestador', 'admin'] },
    { label: 'BI Encuestas', icon: 'pie_chart', route: '/cliente-encuestador', roles: ['cliente_encuestador', 'admin'] },
    { label: 'Supervisor Encuestadores', icon: 'supervisor_account', route: '/supervisor-encuestadores', roles: ['admin', 'supervisor'] },
    { label: 'Ventas', icon: 'point_of_sale', route: '/ventas', roles: ['vendedor', 'admin'] },

    // --- Items exclusivos para rol cliente (id_rol=1) ---
    {
      // El sub-ítem "Power BI" que vivía acá se quitó: quedaba redundante
      // con las pestañas "Resumen | Power BI" que ya tiene la propia página
      // del dashboard (dashboard.component.ts, activeView) -- "Power BI"
      // aparecía dos veces en pantalla a la vez. Esa pestaña interna sigue
      // siendo la única forma de llegar a la vista Power BI.
      label: 'Dashboard', icon: 'dashboard', route: '/dashboard',
      roles: ['client'], hideForAdmin: true,
    },
    { label: 'Centro de Mando', icon: 'bolt', route: '/centro-mando', roles: ['client'], hideForAdmin: true },
    { label: 'Puntos de Venta', icon: 'store', route: '/points', roles: ['client'], hideForAdmin: true },
    { label: 'Productos', icon: 'inventory_2', route: '/products', roles: ['client'], hideForAdmin: true },
    { label: 'Data', icon: 'table_chart', route: '/data', roles: ['client'], hideForAdmin: true },
    { label: 'Chat', icon: 'chat', route: '/chat', roles: ['client'], module: 'chat', hideForAdmin: true },
    { label: 'Usuarios', icon: 'people', route: '/users', roles: ['client'], module: 'users', hideForAdmin: true },
    { label: 'Categorías', icon: 'category', route: '/client-categories', roles: ['client'], hideForAdmin: true },
  ];

  visibleNavItems = computed(() => {
    const u = this.user();
    if (!u) return [];
    const isAdmin = !!u.is_admin || u.rol === 'admin';
    const isClient = u.rol === 'client';

    return this.navItems
      .filter((item) => {
        if (isAdmin && item.hideForAdmin) return false;
        // El cliente puro (rol=client) NO ve los ítems genéricos (sin hideForAdmin)
        // que corresponden a admin/analyst; SOLO ve los marcados hideForAdmin=true con rol 'client'
        if (isClient && !item.hideForAdmin) return false;
        const clave = AuthService.claveFromRoute(item.route);
        return this.auth.canAccess(clave, item.roles);
      })
      .map(item => ({
        ...item,
        // Filtrar sub-ítems visibles
        children: (item.children || []).filter(child => {
          const clave = AuthService.claveFromRoute(child.route);
          return this.auth.canAccess(clave, child.roles);
        }),
      }));
  });

  constructor(
    private auth: AuthService,
    private api: ApiService,
    private router: Router,
    private realtime: RealtimeService,
    private confirmSvc: ConfirmService
  ) {
    this.loadNotifications();
  }

  ngOnInit(): void {
    const u = this.user();
    if (u && (u.rol === 'mercaderista' || u.is_mercaderista)) {
      this.router.navigateByUrl('/mercaderista');
      return;
    }

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

  /** Convierte 'ruta?key=val&k2=v2' en { key: 'val', k2: 'v2' } para [queryParams] */
  parseQueryParams(route: string): Record<string, string> {
    const qs = route.split('?')[1];
    if (!qs) return {};
    return Object.fromEntries(qs.split('&').map(kv => kv.split('=')));
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
    const transitioning = mobile !== this.wasMobile;
    this.isMobile.set(mobile);
    if (mobile && this.sidenavOpen()) {
      this.sidenavOpen.set(false);
    } else if (!mobile && !this.sidenavOpen()) {
      this.sidenavOpen.set(true);
    }
    if (transitioning) {
      this.wasMobile = mobile;
      this.handleResizeRedirect(mobile);
    }
  }

  reloadNotifications(): void {
    this.loadNotifications();
  }

  private handleResizeRedirect(mobile: boolean): void {
    const u = this.user();
    if (!u) return;

    const isAdmin = !!u.is_admin || u.rol === 'admin';
    const isMercaderista = u.rol === 'mercaderista';
    const currentUrl = this.router.url;

    if (mobile) {
      if (currentUrl !== '/mercaderista' && (isAdmin || isMercaderista)) {
        this.confirmSvc.confirm(
          'Detectamos que la pantalla se redujo a tamaño móvil. ¿Deseás continuar al Portal Mercaderista o permanecer en la web normal?',
          { title: 'Cambiar de Vista', confirmText: 'Ir a Portal Mercaderista', cancelText: 'Permanecer' }
        ).then(change => {
          if (change) {
            this.router.navigateByUrl('/mercaderista');
          }
        });
      }
    } else {
      if (currentUrl === '/mercaderista' && (isAdmin || u.rol !== 'mercaderista')) {
        this.confirmSvc.confirm(
          'Detectamos que la pantalla se amplió a tamaño escritorio. ¿Deseás volver al Portal de Gestión o permanecer en el de Mercaderistas?',
          { title: 'Cambiar de Vista', confirmText: 'Ir a Portal de Gestión', cancelText: 'Permanecer' }
        ).then(change => {
          if (change) {
            this.router.navigateByUrl('/dashboard');
          }
        });
      }
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

  async logout(): Promise<void> {
    const confirmed = await this.confirmSvc.confirm('¿Confirmas cerrar sesión?', {
      title: 'Cerrar Sesión',
      confirmText: 'Cerrar Sesión',
      cancelText: 'Cancelar',
      danger: true
    });
    if (confirmed) {
      this.auth.logout();
    }
  }

  private loadNotifications(): void {
    const u = this.user();

    // Admin/analyst notifications: rejection notifications
    if (!u || u.rol !== 'mercaderista') {
      this.api.getRejectionNotifications().subscribe({
        next: (notifs: any[]) => { this.notifCount.set(notifs.length); },
        error: () => { },
      });
    }

    // Mercaderista notifications: chat pendientes + foto rechazos
    if (u && (u.rol === 'mercaderista' || u.is_mercaderista)) {
      this.api.get<any>('/api/merc/chat/notificaciones').subscribe({
        next: (res: any) => {
          const chatPendientes = res.chat_no_leidos || 0;
          const rechazos = res.fotos_rechazadas || 0;
          this.notifCount.set(chatPendientes + rechazos);
        },
        error: () => { },
      });
    }
  }
}
