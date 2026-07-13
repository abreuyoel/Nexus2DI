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

interface NavItem {
  label: string;
  icon: string;
  route: string;
  roles: string[];
  module?: string;
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
    { label: 'Dashboard', icon: 'dashboard', route: '/dashboard', roles: [] },
    { label: 'Centro de Mando', icon: 'bolt', route: '/centro-mando', roles: ['admin', 'superadmin', 'analyst', 'coordinador_general', 'coordinador_exclusivo'] },
    { label: 'Rutas', icon: 'route', route: '/routes', roles: ['admin', 'analyst'], module: 'rutas' },
    { label: 'Puntos de Venta', icon: 'store', route: '/points', roles: ['admin', 'supervisor', 'atc'] },
    { label: 'Usuarios', icon: 'people', route: '/users', roles: ['admin'], module: 'users' },
    { label: 'Permisos', icon: 'admin_panel_settings', route: '/permissions', roles: ['admin'] },
    { label: 'Productos', icon: 'inventory_2', route: '/products', roles: ['admin', 'atc'] },
    { label: 'Categorías Cliente', icon: 'category', route: '/client-categories', roles: ['admin'] },
    { label: 'Clientes · Rutas', icon: 'alt_route', route: '/clientes-rutas', roles: ['admin', 'analyst'] },
    { label: 'Frecuencias PDVs', icon: 'event_repeat', route: '/frecuencias-pdvs-cliente', roles: ['admin', 'analyst'] },
    { label: 'Horas Promedio Ejecución', icon: 'schedule', route: '/horas-promedio-ejecucion', roles: ['admin'] },
    { label: 'Mis Rutas', icon: 'route', route: '/mercaderista', roles: ['mercaderista'] },
    { label: 'Auditoría de Campo', icon: 'fact_check', route: '/auditor-campo', roles: ['auditor_campo', 'admin'] },
    { label: 'Auditoría de Data', icon: 'inventory_2', route: '/auditoria-data', roles: ['auditor', 'admin'] },
    { label: 'Chat', icon: 'chat', route: '/chat', roles: [], module: 'chat' },
    { label: 'Supervisor', icon: 'supervisor_account', route: '/supervisor', roles: ['admin', 'supervisor'] },
    { label: 'Solicitudes', icon: 'support_agent', route: '/atencion-cliente', roles: ['admin', 'atc', 'analyst'] },
    { label: 'Auditoría Logs', icon: 'fact_check', route: '/audit', roles: ['admin'] },
    { label: 'Mis Fotos', icon: 'photo_library', route: '/client', roles: ['coordinador_exclusivo', 'coordinador_tradex'] },
    { label: 'Mis Visitas', icon: 'today', route: '/client/visits', roles: ['client', 'coordinador_exclusivo', 'coordinador_tradex'] },
    { label: 'Data', icon: 'table_chart', route: '/data', roles: ['admin', 'analyst', 'client', 'coordinador_exclusivo', 'coordinador_tradex', 'coordinador_general'] },
    { label: 'Encuestador', icon: 'assignment', route: '/encuestador', roles: ['encuestador', 'admin'] },
    { label: 'BI Encuestas', icon: 'pie_chart', route: '/cliente-encuestador', roles: ['cliente_encuestador', 'admin'] },
    { label: 'Ventas', icon: 'point_of_sale', route: '/ventas', roles: ['vendedor', 'admin'] },
  ];

  visibleNavItems = computed(() => {
    const u = this.user();
    if (!u) return [];

    return this.navItems.filter((item) => {
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
    private realtime: RealtimeService
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

  logout(): void { this.auth.logout(); }

  private loadNotifications(): void {
    this.api.getRejectionNotifications().subscribe({
      next: (notifs: any[]) => { this.notifCount = notifs.length; },
      error: () => {},
    });
  }
}
