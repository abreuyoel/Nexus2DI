import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { roleGuard } from './core/guards/role.guard';

export const routes: Routes = [
  { path: '', redirectTo: '/login', pathMatch: 'full' },

  {
    path: 'login',
    loadComponent: () => import('./features/auth/login/login.component').then((m) => m.LoginComponent),
  },
  {
    path: 'login-mercaderista',
    loadComponent: () => import('./features/auth/login-mercaderista/login-mercaderista.component').then((m) => m.LoginMercaderistaComponent),
  },
  {
    path: 'mercaderista',
    canActivate: [authGuard, roleGuard],
    data: { roles: ['mercaderista', 'admin'] },
    loadComponent: () => import('./features/mercaderista/mercaderista.component').then((m) => m.MercaderistaComponent),
  },

  {
    path: '',
    canActivate: [authGuard],
    loadComponent: () => import('./layout/shell/shell.component').then((m) => m.ShellComponent),
    children: [
      {
        path: 'dashboard',
        loadComponent: () => import('./features/dashboard/dashboard.component').then((m) => m.DashboardComponent),
      },
      {
        path: 'centro-mando',
        loadComponent: () => import('./features/centro-mando/centro-mando.component').then((m) => m.CentroMandoComponent),
        canActivate: [roleGuard],
        data: { roles: ['admin', 'superadmin', 'analyst', 'coordinador_general', 'coordinador_exclusivo', 'client'] },
      },
      {
        path: 'centro-mando-auditoria',
        loadComponent: () => import('./features/centro-mando-auditoria/centro-mando-auditoria.component').then((m) => m.CentroMandoAuditoriaComponent),
        canActivate: [roleGuard],
        data: { roles: ['admin', 'analyst'] },
      },
      {
        path: 'visits',
        loadComponent: () => import('./features/visits/visits.component').then((m) => m.VisitsComponent),
      },
      {
        path: 'routes',
        loadComponent: () => import('./features/routes/routes.component').then((m) => m.RoutesComponent),
        canActivate: [roleGuard],
        data: { roles: ['admin', 'analyst'] },
      },
      {
        path: 'points',
        loadComponent: () => import('./features/visits/points/points.component').then((m) => m.PointsComponent),
        canActivate: [roleGuard],
        data: { roles: ['admin', 'supervisor', 'atc', 'client'] },
      },
      {
        path: 'photos',
        loadComponent: () => import('./features/photos/photos.component').then((m) => m.PhotosComponent),
      },
      {
        path: 'reports',
        loadComponent: () => import('./features/reports/reports.component').then((m) => m.ReportsComponent),
        canActivate: [roleGuard],
        data: { roles: ['admin'] },
      },
      {
        path: 'users',
        loadComponent: () => import('./features/users/users.component').then((m) => m.UsersComponent),
        canActivate: [roleGuard],
        data: { roles: ['admin', 'client'] },
      },
      {
        path: 'client-categories',
        loadComponent: () => import('./features/client-categories/client-categories.component').then((m) => m.ClientCategoriesComponent),
        canActivate: [roleGuard],
        data: { roles: ['admin', 'client'] },
      },
      {
        path: 'sku-competencia',
        loadComponent: () => import('./features/sku-competencia/sku-competencia.component').then((m) => m.SkuCompetenciaComponent),
        canActivate: [roleGuard],
        data: { roles: ['admin'] },
      },
      {
        path: 'plan-accion',
        loadComponent: () => import('./features/plan-accion/plan-accion.component').then((m) => m.PlanAccionComponent),
        canActivate: [roleGuard],
        data: { roles: ['admin', 'analyst'] },
      },
      {
        path: 'quiebre',
        loadComponent: () => import('./features/quiebre/quiebre.component').then((m) => m.QuiebreComponent),
        canActivate: [roleGuard],
        data: { roles: ['admin', 'analyst'] },
      },
      {
        path: 'clientes-rutas',
        loadComponent: () => import('./features/clientes-rutas/clientes-rutas.component').then((m) => m.ClientesRutasComponent),
        canActivate: [roleGuard],
        data: { roles: ['admin', 'analyst'] },
      },
      {
        path: 'frecuencias-pdvs-cliente',
        loadComponent: () => import('./features/frecuencias-pdvs-cliente/frecuencias-pdvs-cliente.component').then((m) => m.FrecuenciasPdvsClienteComponent),
        canActivate: [roleGuard],
        data: { roles: ['admin', 'analyst'] },
      },
      {
        path: 'horas-promedio-ejecucion',
        loadComponent: () => import('./features/horas-promedio-ejecucion/horas-promedio-ejecucion.component').then((m) => m.HorasPromedioEjecucionComponent),
        canActivate: [roleGuard],
        data: { roles: ['admin'] },
      },
      {
        path: 'permissions',
        loadComponent: () => import('./features/admin/permissions.component').then((m) => m.PermissionsComponent),
        canActivate: [roleGuard],
        data: { roles: ['admin'] },
      },
      {
        path: 'admin/chat-grupos',
        loadComponent: () => import('./features/admin/chat-grupos-admin.component').then((m) => m.ChatGruposAdminComponent),
        canActivate: [roleGuard],
        data: { roles: ['admin'] },
      },
      {
        path: 'sessions',
        loadComponent: () => import('./features/admin/sessions/sessions.component').then((m) => m.SessionsComponent),
        canActivate: [roleGuard],
        data: { roles: ['admin'] },
      },
      {
        path: 'audit',
        loadComponent: () => import('./features/admin/audit-log/audit-log.component').then((m) => m.AuditLogComponent),
        canActivate: [roleGuard],
        data: { roles: ['admin'] },
      },
      {
        path: 'chat',
        loadComponent: () => import('./features/chat/chat.component').then((m) => m.ChatComponent),
      },
      {
        path: 'supervisor',
        loadComponent: () => import('./features/supervisor/supervisor.component').then((m) => m.SupervisorComponent),
        canActivate: [roleGuard],
        data: { roles: ['admin', 'supervisor'] },
      },
      {
        path: 'auditor',
        loadComponent: () => import('./features/auditor/auditor.component').then((m) => m.AuditorComponent),
      },
      {
        path: 'atencion-cliente',
        loadComponent: () => import('./features/atencion-cliente/atencion-cliente.component').then((m) => m.AtencionClienteComponent),
        canActivate: [roleGuard],
        data: { roles: ['admin', 'atc', 'analyst'] },
      },
      {
        path: 'client-photos',
        canActivate: [roleGuard],
        data: { roles: ['client', 'coordinador_exclusivo', 'coordinador_tradex'] },
        loadComponent: () => import('./features/client-photos/client-photos.component').then(m => m.ClientPhotosComponent)
      },
      {
        path: 'data',
        canActivate: [roleGuard],
        data: { roles: ['client', 'coordinador_exclusivo', 'coordinador_tradex', 'coordinador_general', 'admin', 'analyst'] },
        loadComponent: () => import('./features/client-data/client-data.component').then(m => m.ClientDataComponent)
      },
      {
        path: 'revision-visitas',
        canActivate: [roleGuard],
        data: { roles: ['admin', 'analyst', 'supervisor'] },
        loadComponent: () => import('./features/revision-visitas/revision-visitas.component').then(m => m.RevisionVisitasComponent)
      },
      {
        path: 'client',
        loadComponent: () => import('./features/client-photos/client-photos.component').then(m => m.ClientPhotosComponent),
        canActivate: [roleGuard],
        data: { roles: ['coordinador_exclusivo', 'coordinador_tradex'] },
      },
      {
        path: 'client/visits',
        loadComponent: () => import('./features/client-visits/client-visits.component').then(m => m.ClientVisitsComponent),
        canActivate: [roleGuard],
        data: { roles: ['coordinador_exclusivo', 'coordinador_tradex'] },
      },

      {
        path: 'auditoria-data',
        canActivate: [roleGuard],
        data: { roles: ['auditor', 'admin'] },
        loadComponent: () => import('./features/auditoria-data/auditoria-data.component').then((m) => m.AuditoriaDataComponent),
      },
      {
        path: 'auditoria-usuarios',
        canActivate: [roleGuard],
        data: { roles: ['admin', 'analyst', 'auditor'] },
        loadComponent: () => import('./features/auditoria-usuarios/auditoria-usuarios.component').then((m) => m.AuditoriaUsuariosComponent),
      },
      {
        path: 'auditor-campo',
        canActivate: [roleGuard],
        data: { roles: ['auditor_campo', 'admin'] },
        loadComponent: () => import('./features/auditor-campo/auditor-campo.component').then((m) => m.AuditorCampoComponent),
      },
      {
        path: 'products',
        loadComponent: () => import('./features/products/products.component').then(m => m.ProductsComponent),
        canActivate: [roleGuard],
        data: { roles: ['admin', 'atc', 'client'] },
      },
      {
        path: 'data',
        loadComponent: () => import('./features/data/data.component').then((m) => m.DataComponent),
        canActivate: [roleGuard],
        data: { roles: ['admin', 'analyst'] },
      },
      {
        path: 'encuestador',
        loadChildren: () => import('./features/encuestador/encuestador.routes').then(m => m.ENCUESTADOR_ROUTES),
        canActivate: [roleGuard],
        // cliente_encuestador (IQVIA) también puede activar jornadas y
        // cargar médicos -- ver check_rol_encuestador en el backend.
        data: { roles: ['encuestador', 'cliente_encuestador', 'admin'] }
      },
      {
        path: 'cliente-encuestador',
        loadChildren: () => import('./features/cliente-encuestador/cliente-encuestador.routes').then(m => m.CLIENTE_ENCUESTADOR_ROUTES),
        canActivate: [roleGuard],
        data: { roles: ['cliente_encuestador', 'admin'] }
      },
      {
        path: 'supervisor-encuestadores',
        // Force recompilation
        loadComponent: () => import('./features/supervisor-encuestadores/supervisor-encuestadores.component').then(m => m.SupervisorEncuestadoresComponent),
        canActivate: [roleGuard],
        data: { roles: ['admin', 'supervisor'] }
      },
      {
        path: 'portal-mercaderista',
        canActivate: [roleGuard],
        data: { roles: ['admin', 'supervisor', 'mercaderista'] },
        loadComponent: () => import('./features/mercaderista/mercaderista.component').then((m) => m.MercaderistaComponent),
      },
      {
        path: 'ventas',
        canActivate: [roleGuard],
        data: { roles: ['vendedor', 'admin'] },
        loadComponent: () => import('./features/ventas/ventas.component').then((m) => m.VentasComponent),
      },
      {
        path: 'ventas-dashboard',
        canActivate: [roleGuard],
        data: { roles: ['vendedor', 'supervisor', 'admin'] },
        loadComponent: () => import('./features/ventas/ventas-dashboard.component').then((m) => m.VentasDashboardComponent),
      },
      {
        path: 'pedidos-ventas',
        canActivate: [roleGuard],
        data: { roles: ['vendedor', 'supervisor', 'admin'] },
        loadComponent: () => import('./features/ventas/pedidos-ventas.component').then((m) => m.PedidosVentasComponent),
      },
    ],
  },

  {
    path: 'unauthorized',
    loadComponent: () => import('./features/auth/unauthorized/unauthorized.component').then((m) => m.UnauthorizedComponent),
  },
  { path: '**', redirectTo: '/login' },
];
