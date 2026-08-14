import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators, FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatTooltipModule } from '@angular/material/tooltip';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';
import { RealtimeService } from '../../core/services/realtime.service';
import { Ruta } from '../../core/models/ruta.model';
import { RouteDetailDialogComponent } from './route-detail-dialog.component';
import { SearchableSelectComponent, SelectOption } from '../client-visits/searchable-select.component';

interface AssignedRoute {
  id: number;
  nombre: string;
  servicio?: string;
  tipo_ruta: string;
}

interface CatalogItem { id: number; nombre: string; activo: boolean; prefijo?: string | null; }

@Component({
  selector: 'app-routes',
  standalone: true,
  imports: [
    CommonModule, ReactiveFormsModule, FormsModule,
    MatButtonModule, MatIconModule, MatTableModule,
    MatFormFieldModule, MatInputModule, MatDialogModule,
    MatProgressSpinnerModule, MatSlideToggleModule, MatSnackBarModule,
    MatSelectModule, MatTooltipModule,
    SearchableSelectComponent,
  ],
  templateUrl: './routes.component.html',
  styleUrls: ['./routes.component.scss']
})
export class RoutesComponent implements OnInit {
  private static readonly RUTAS_PAGE_SIZE = 12;
  private static readonly MERC_PAGE_SIZE = 12;

  // ── Rutas ─────────────────────────────────────────────────
  loading = signal(true);
  page = signal(1);
  saving = signal(false);
  routes = signal<Ruta[]>([]);
  showCreateForm = signal(false);
  nextNumber = signal<number | null>(null);

  // Catálogos (dropdowns + ABM)
  servicios = signal<CatalogItem[]>([]);
  cuadrantes = signal<CatalogItem[]>([]);
  clients = signal<{ id: number; nombre: string }[]>([]);

  // Filtros dinámicos (lista de rutas)
  searchTerm = '';
  filterCuadrante = '';
  filterCliente = '';
  filterServicio = '';

  createForm = this.fb.group({
    nombre_previsto: [{ value: '', disabled: true }],
    servicio: ['', Validators.required],
    coordinador_1: ['', Validators.required],
    coordinador_2: [''],
    cuadrante: ['', Validators.required],
    id_cliente_exclusivo: [''],
    activa: [true],
  });

  // ── Tab ───────────────────────────────────────────────────
  activeTab = signal<'rutas' | 'mercaderistas' | 'analistas' | 'supervisores'>('rutas');

  // ── Mercaderistas grid ────────────────────────────────────
  mercLoading = signal(false);
  mercList = signal<any[]>([]);
  mercSearch = '';
  mercFilterTipo = '';
  mercPage = signal(1);

  // ── Assignment panel ──────────────────────────────────────
  panelOpen = signal(false);
  panelSaving = signal(false);
  selectedMerc = signal<any>(null);
  assignedRoutes = signal<AssignedRoute[]>([]);
  panelRouteSearch = '';

  // ── Catálogo ABM modal ────────────────────────────────────
  catalogModalOpen = signal(false);
  catalogKind = signal<'cuadrantes' | 'servicios'>('cuadrantes');
  catalogNewName = '';
  catalogSaving = signal(false);

  // ── Analistas / Supervisores (Fase 2/3) ───────────────────
  analystLoading = signal(false);
  analystList = signal<any[]>([]);
  analystSearch = '';
  supervisorLoading = signal(false);
  supervisorList = signal<any[]>([]);
  supervisorSearch = '';

  // Panel de asignación (compartido: analista o supervisor)
  assignKind = signal<'analista' | 'supervisor'>('analista');
  analystPanelOpen = signal(false);
  analystPanelSaving = signal(false);
  selectedAnalyst = signal<any>(null);
  analystTab = signal<'rutas' | 'clientes'>('rutas');
  assignedAnalystRoutes = signal<{ id: number; nombre: string; servicio?: string }[]>([]);
  analystRouteSearch = '';
  routeClientOptions = signal<{ id: number; nombre: string }[]>([]);
  selectedAnalystClientIds = signal<number[]>([]);

  constructor(
    private api: ApiService,
    private fb: FormBuilder,
    private snack: MatSnackBar,
    private dialog: MatDialog,
    public auth: AuthService,
    private realtime: RealtimeService,
  ) { }

  ngOnInit(): void {
    this.loadRoutes();
    this.loadCatalogs();
    this.loadClients();
    this.realtime.events$.subscribe(ev => {
      if (ev.tipo.startsWith('route.')) this.loadRoutes();
    });
  }

  // ── Carga ─────────────────────────────────────────────────
  loadCatalogs(): void {
    this.api.listServicios(true).subscribe(d => this.servicios.set(d));
    this.api.listCatalog('cuadrantes', true).subscribe(d => this.cuadrantes.set(d));
  }

  loadClients(): void {
    this.api.getClients().subscribe(d => this.clients.set(d ?? []));
  }

  loadRoutes(): void {
    this.loading.set(true);
    this.api.getRoutes().subscribe({
      next: (data) => { this.routes.set(data); this.loading.set(false); this.resetPage(); },
      error: () => this.loading.set(false),
    });
  }

  // ── Filtros dinámicos ─────────────────────────────────────
  get filteredRoutes(): Ruta[] {
    const s = this.searchTerm.trim().toLowerCase();
    const cu = this.filterCuadrante;
    const cl = this.filterCliente;
    const se = this.filterServicio;
    return this.routes().filter(r =>
      (!s || r.nombre?.toLowerCase().includes(s)) &&
      (!cu || (r.region ?? r.cuadrante) === cu) &&
      (!cl || (r.clientes ?? []).includes(cl)) &&
      (!se || r.servicio === se)
    );
  }

  // ── Paginación de rutas ───────────────────────────────────
  get totalPages(): number {
    return Math.max(1, Math.ceil(this.filteredRoutes.length / RoutesComponent.RUTAS_PAGE_SIZE));
  }
  get paginatedRoutes(): Ruta[] {
    const p = Math.min(this.page(), this.totalPages);
    const start = (p - 1) * RoutesComponent.RUTAS_PAGE_SIZE;
    return this.filteredRoutes.slice(start, start + RoutesComponent.RUTAS_PAGE_SIZE);
  }
  goPage(p: number): void { this.page.set(Math.min(Math.max(1, p), this.totalPages)); }
  resetPage(): void { this.page.set(1); }
  onSearchTermChange(): void { this.resetPage(); }

  // Opciones para los select de búsqueda (SearchableSelectComponent)
  cuadranteOpts = computed<SelectOption[]>(() =>
    this.cuadrantes().map(c => ({ value: c.nombre, label: c.nombre })));

  clienteOpts = computed<SelectOption[]>(() => {
    const set = new Set<string>();
    this.routes().forEach(r => (r.clientes ?? []).forEach(c => set.add(c)));
    return [...set].sort().map(c => ({ value: c, label: c }));
  });

  servicioOpts = computed<SelectOption[]>(() =>
    this.servicios().map(s => ({ value: s.nombre, label: s.nombre })));

  mercTipoOpts = computed<SelectOption[]>(() =>
    [...new Set(this.mercList().map(m => m.tipo).filter(Boolean))].map(t => ({ value: t, label: t })));

  onCuadranteChange(v: string): void { this.filterCuadrante = v; this.resetPage(); }
  onClienteChange(v: string): void { this.filterCliente = v; this.resetPage(); }
  onFilterServicioChange(v: string): void { this.filterServicio = v; this.resetPage(); }
  onMercTipoChange(v: string): void { this.mercFilterTipo = v; this.resetMercPage(); }

  clearFilters(): void { this.searchTerm = ''; this.filterCuadrante = ''; this.filterCliente = ''; this.filterServicio = ''; this.resetPage(); }

  // ── Crear ─────────────────────────────────────────────────
  get isExclusiva(): boolean { return this.createForm.get('servicio')?.value === 'Exclusivo'; }

  onServicioChange(servicio: string): void {
    if (!servicio) return;
    // Cliente exclusivo sólo es obligatorio para el servicio "Exclusivo"
    const clienteCtrl = this.createForm.get('id_cliente_exclusivo');
    if (servicio === 'Exclusivo') {
      clienteCtrl?.setValidators([Validators.required]);
    } else {
      clienteCtrl?.clearValidators();
      clienteCtrl?.setValue('');
    }
    clienteCtrl?.updateValueAndValidity();

    this.api.getNextRouteNumber(servicio).subscribe({
      next: (data) => {
        this.nextNumber.set(data.next_number);
        this.createForm.patchValue({ nombre_previsto: `Ruta ${data.prefijo}${data.next_number}` });
      },
      error: () => this.createForm.patchValue({ nombre_previsto: '' }),
    });
  }

  createRoute(): void {
    if (this.createForm.invalid) return;
    this.saving.set(true);
    const v = this.createForm.value;
    const payload: any = {
      servicio: v.servicio,
      coordinador_1: v.coordinador_1,
      coordinador_2: v.coordinador_2 || null,
      cuadrante: v.cuadrante,
      id_cliente_exclusivo: v.servicio === 'Exclusivo' && v.id_cliente_exclusivo ? Number(v.id_cliente_exclusivo) : null,
    };
    this.api.createRoute(payload).subscribe({
      next: (ruta) => {
        this.saving.set(false);
        this.routes.update((rs: Ruta[]) => [...rs, ruta].sort((a, b) => a.nombre.localeCompare(b.nombre)));
        this.createForm.reset({ activa: true });
        this.nextNumber.set(null);
        this.showCreateForm.set(false);
        this.snack.open('Ruta creada exitosamente', 'OK', { duration: 3000 });
      },
      error: (err) => {
        this.saving.set(false);
        this.snack.open(err.error?.detail ?? 'Error al crear ruta', 'OK', { duration: 4000 });
      },
    });
  }

  // ── Acciones de ruta ──────────────────────────────────────
  viewPoints(ruta: Ruta, startEdit = false): void {
    const ref = this.dialog.open(RouteDetailDialogComponent, {
      data: { ruta, startEdit }, width: '100%', maxWidth: '1100px', panelClass: 'custom-dialog'
    });
    ref.afterClosed().subscribe(() => this.loadRoutes());
  }

  duplicateRoute(ruta: Ruta): void {
    this.api.duplicateRoute(ruta.id).subscribe({
      next: (nueva) => {
        this.routes.update((rs: Ruta[]) => [...rs, nueva].sort((a, b) => a.nombre.localeCompare(b.nombre)));
        this.snack.open(`Ruta duplicada como ${nueva.nombre}`, 'OK', { duration: 3000 });
      },
      error: (err) => this.snack.open(err.error?.detail ?? 'Error al duplicar', 'OK', { duration: 4000 }),
    });
  }

  deleteRoute(ruta: Ruta): void {
    if (!confirm(`¿Eliminar la ruta ${ruta.nombre}? Se borrarán sus puntos y asignaciones.`)) return;
    this.api.deleteRoute(ruta.id).subscribe({
      next: () => {
        this.routes.update((rs: Ruta[]) => rs.filter(r => r.id !== ruta.id));
        this.snack.open('Ruta eliminada', 'OK', { duration: 3000 });
      },
      error: (err) => this.snack.open(err.error?.detail ?? 'Error al eliminar', 'OK', { duration: 4000 }),
    });
  }

  // ── Catálogo ABM ──────────────────────────────────────────
  catalogNewPrefijo = '';

  openCatalogModal(kind: 'cuadrantes' | 'servicios'): void {
    this.catalogKind.set(kind);
    this.catalogNewName = '';
    this.catalogNewPrefijo = '';
    this.catalogModalOpen.set(true);
  }
  closeCatalogModal(): void { this.catalogModalOpen.set(false); }

  get catalogItems(): CatalogItem[] {
    return this.catalogKind() === 'cuadrantes' ? this.cuadrantes() : this.servicios();
  }
  private refreshCatalog(kind: 'cuadrantes' | 'servicios'): void {
    if (kind === 'servicios') {
      this.api.listServicios(true).subscribe(d => this.servicios.set(d));
    } else {
      this.api.listCatalog(kind, true).subscribe(d => this.cuadrantes.set(d));
    }
  }

  addCatalogItem(): void {
    const nombre = this.catalogNewName.trim();
    if (!nombre) return;
    const kind = this.catalogKind();
    if (kind === 'servicios') {
      const prefijo = this.catalogNewPrefijo.trim();
      if (!prefijo) { this.snack.open('El prefijo es obligatorio (ej. "PR" para Promovendedor)', 'OK', { duration: 3500 }); return; }
      this.catalogSaving.set(true);
      this.api.createServicio({ nombre, prefijo }).subscribe({
        next: () => { this.catalogNewName = ''; this.catalogNewPrefijo = ''; this.catalogSaving.set(false); this.refreshCatalog(kind); },
        error: (err) => { this.catalogSaving.set(false); this.snack.open(err.error?.detail ?? 'Error', 'OK', { duration: 3500 }); },
      });
      return;
    }
    this.catalogSaving.set(true);
    this.api.createCatalogItem(kind, { nombre }).subscribe({
      next: () => { this.catalogNewName = ''; this.catalogSaving.set(false); this.refreshCatalog(kind); },
      error: (err) => { this.catalogSaving.set(false); this.snack.open(err.error?.detail ?? 'Error', 'OK', { duration: 3500 }); },
    });
  }

  renameCatalogItem(item: CatalogItem, nuevo: string): void {
    const nombre = nuevo.trim();
    const kind = this.catalogKind();
    if (!nombre || nombre === item.nombre) return;
    if (kind === 'servicios') {
      this.api.updateServicio(item.id, { nombre }).subscribe({
        next: () => { this.refreshCatalog(kind); this.loadRoutes(); },
        error: (err) => this.snack.open(err.error?.detail ?? 'Error', 'OK', { duration: 3500 }),
      });
      return;
    }
    this.api.updateCatalogItem(kind, item.id, { nombre }).subscribe({
      next: () => { this.refreshCatalog(kind); this.loadRoutes(); },
      error: (err) => this.snack.open(err.error?.detail ?? 'Error', 'OK', { duration: 3500 }),
    });
  }

  renameServicioPrefijo(item: CatalogItem, nuevo: string): void {
    const prefijo = nuevo.trim().toUpperCase();
    if (!prefijo || prefijo === item.prefijo) return;
    this.api.updateServicio(item.id, { prefijo }).subscribe({
      next: () => this.refreshCatalog('servicios'),
      error: (err) => this.snack.open(err.error?.detail ?? 'Error', 'OK', { duration: 3500 }),
    });
  }

  deleteCatalogItem(item: CatalogItem): void {
    const kind = this.catalogKind();
    const del = (force = false) => kind === 'servicios' ? this.api.deleteServicio(item.id, force) : this.api.deleteCatalogItem(kind, item.id, force);
    del().subscribe({
      next: () => this.refreshCatalog(kind),
      error: (err) => {
        const detail = err.error?.detail;
        const msg = typeof detail === 'object' ? detail.message : detail;
        if (err.status === 409 && confirm(`${msg}\n\n¿Eliminar de todos modos?`)) {
          del(true).subscribe({
            next: () => { this.refreshCatalog(kind); this.loadRoutes(); },
            error: () => this.snack.open('No se pudo eliminar', 'OK', { duration: 3500 }),
          });
        } else {
          this.snack.open(msg ?? 'Error al eliminar', 'OK', { duration: 4000 });
        }
      },
    });
  }

  // ── Tab switch ────────────────────────────────────────────
  switchTab(tab: 'rutas' | 'mercaderistas' | 'analistas' | 'supervisores'): void {
    this.activeTab.set(tab);
    if (tab === 'mercaderistas' && this.mercList().length === 0) this.loadMercaderistas();
    if (tab === 'analistas' && this.analystList().length === 0) this.loadAnalysts();
    if (tab === 'supervisores' && this.supervisorList().length === 0) this.loadSupervisors();
  }

  // ── Analistas / Supervisores (panel compartido) ───────────
  loadAnalysts(): void {
    this.analystLoading.set(true);
    this.api.getAnalystsWithAssignments().subscribe({
      next: (data) => { this.analystList.set(data); this.analystLoading.set(false); },
      error: () => this.analystLoading.set(false),
    });
  }
  loadSupervisors(): void {
    this.supervisorLoading.set(true);
    this.api.getSupervisorsWithAssignments().subscribe({
      next: (data) => { this.supervisorList.set(data); this.supervisorLoading.set(false); },
      error: () => this.supervisorLoading.set(false),
    });
  }

  get filteredAnalysts(): any[] {
    const s = this.analystSearch.trim().toLowerCase();
    return this.analystList().filter(a => !s || a.nombre?.toLowerCase().includes(s));
  }
  get filteredSupervisors(): any[] {
    const s = this.supervisorSearch.trim().toLowerCase();
    return this.supervisorList().filter(a => !s || a.nombre?.toLowerCase().includes(s));
  }

  get assignKindLabel(): string { return this.assignKind() === 'supervisor' ? 'Supervisor' : 'Analista'; }

  // Selección de endpoints según el tipo de persona
  private kindRoutes(id: number) {
    return this.assignKind() === 'supervisor' ? this.api.getSupervisorRoutes(id) : this.api.getAnalystRoutes(id);
  }
  private kindSyncRoutes(id: number, ids: number[]) {
    return this.assignKind() === 'supervisor' ? this.api.syncSupervisorRoutes(id, ids) : this.api.syncAnalystRoutes(id, ids);
  }
  private kindClients(id: number) {
    return this.assignKind() === 'supervisor' ? this.api.getSupervisorClients(id) : this.api.getAnalystClients(id);
  }
  private kindRouteClients(id: number) {
    return this.assignKind() === 'supervisor' ? this.api.getSupervisorRouteClients(id) : this.api.getAnalystRouteClients(id);
  }
  private kindSyncClients(id: number, ids: number[]) {
    return this.assignKind() === 'supervisor' ? this.api.syncSupervisorClients(id, ids) : this.api.syncAnalystClients(id, ids);
  }
  private updatePersonCount(id: number, patch: any): void {
    const sig = this.assignKind() === 'supervisor' ? this.supervisorList : this.analystList;
    sig.update(list => list.map(x => x.id === id ? { ...x, ...patch } : x));
  }

  openAssignPanel(person: any, kind: 'analista' | 'supervisor'): void {
    this.assignKind.set(kind);
    this.selectedAnalyst.set(person);
    this.analystPanelOpen.set(true);
    this.analystTab.set('rutas');
    this.analystRouteSearch = '';
    this.kindRoutes(person.id).subscribe({
      next: (r) => this.assignedAnalystRoutes.set(r),
      error: () => this.assignedAnalystRoutes.set([]),
    });
  }
  closeAnalystPanel(): void {
    this.analystPanelOpen.set(false);
    this.selectedAnalyst.set(null);
    this.assignedAnalystRoutes.set([]);
    this.routeClientOptions.set([]);
    this.selectedAnalystClientIds.set([]);
  }

  switchAnalystTab(tab: 'rutas' | 'clientes'): void {
    this.analystTab.set(tab);
    const a = this.selectedAnalyst();
    if (tab === 'clientes' && a) {
      this.kindRouteClients(a.id).subscribe(opts => this.routeClientOptions.set(opts));
      this.kindClients(a.id).subscribe(cli => this.selectedAnalystClientIds.set(cli.map((c: any) => c.id)));
    }
  }

  // Rutas del analista
  isAnalystRouteAssigned(id: number): boolean { return this.assignedAnalystRoutes().some(r => r.id === id); }
  addAnalystRoute(r: Ruta): void {
    if (this.isAnalystRouteAssigned(r.id)) return;
    this.assignedAnalystRoutes.update(list => [...list, { id: r.id, nombre: r.nombre, servicio: r.servicio }]);
  }
  removeAnalystRoute(id: number): void {
    this.assignedAnalystRoutes.update(list => list.filter(r => r.id !== id));
  }
  get availableAnalystRoutes(): Ruta[] {
    const s = this.analystRouteSearch.toLowerCase();
    return this.routes().filter(r =>
      !this.isAnalystRouteAssigned(r.id) &&
      (!s || r.nombre?.toLowerCase().includes(s) || r.servicio?.toLowerCase().includes(s))
    );
  }
  saveAnalystRoutes(): void {
    const a = this.selectedAnalyst();
    if (!a) return;
    this.analystPanelSaving.set(true);
    const ids = this.assignedAnalystRoutes().map(r => r.id);
    this.kindSyncRoutes(a.id, ids).subscribe({
      next: () => {
        this.analystPanelSaving.set(false);
        this.updatePersonCount(a.id, { rutas_count: ids.length });
        this.snack.open(`Rutas del ${this.assignKindLabel.toLowerCase()} guardadas`, 'OK', { duration: 3000 });
      },
      error: (err) => { this.analystPanelSaving.set(false); this.snack.open(err.error?.detail ?? 'Error', 'OK', { duration: 4000 }); },
    });
  }

  // Clientes del analista
  isAnalystClientSelected(id: number): boolean { return this.selectedAnalystClientIds().includes(id); }
  toggleAnalystClient(id: number): void {
    this.selectedAnalystClientIds.update(list => list.includes(id) ? list.filter(x => x !== id) : [...list, id]);
  }
  saveAnalystClients(): void {
    const a = this.selectedAnalyst();
    if (!a) return;
    this.analystPanelSaving.set(true);
    const ids = this.selectedAnalystClientIds();
    this.kindSyncClients(a.id, ids).subscribe({
      next: () => {
        this.analystPanelSaving.set(false);
        this.updatePersonCount(a.id, { clientes_count: ids.length });
        this.snack.open(`Clientes del ${this.assignKindLabel.toLowerCase()} guardados`, 'OK', { duration: 3000 });
      },
      error: (err) => { this.analystPanelSaving.set(false); this.snack.open(err.error?.detail ?? 'Error', 'OK', { duration: 4000 }); },
    });
  }

  // ── Mercaderistas grid methods ────────────────────────────
  loadMercaderistas(): void {
    this.mercLoading.set(true);
    this.api.getMercaderistasConRutas().subscribe({
      next: (data) => { this.mercList.set(data); this.mercLoading.set(false); this.resetMercPage(); },
      error: () => this.mercLoading.set(false),
    });
  }

  get filteredMercaderistas(): any[] {
    const s = this.mercSearch.toLowerCase();
    const t = this.mercFilterTipo;
    return this.mercList().filter(m =>
      (!s || m.nombre?.toLowerCase().includes(s) || String(m.cedula ?? '').includes(s) || m.email?.toLowerCase().includes(s) ||
        (m.rutas_nombres || []).some((rn: string) => rn.toLowerCase().includes(s))) &&
      (!t || m.tipo === t)
    );
  }

  get totalMercPages(): number {
    return Math.max(1, Math.ceil(this.filteredMercaderistas.length / RoutesComponent.MERC_PAGE_SIZE));
  }
  get paginatedMercaderistas(): any[] {
    const p = Math.min(this.mercPage(), this.totalMercPages);
    const start = (p - 1) * RoutesComponent.MERC_PAGE_SIZE;
    return this.filteredMercaderistas.slice(start, start + RoutesComponent.MERC_PAGE_SIZE);
  }
  goMercPage(p: number): void { this.mercPage.set(Math.min(Math.max(1, p), this.totalMercPages)); }
  resetMercPage(): void { this.mercPage.set(1); }
  onMercSearchChange(): void { this.resetMercPage(); }

  get mercTipos(): string[] {
    return [...new Set(this.mercList().map(m => m.tipo).filter(Boolean))];
  }

  // ── Assignment panel methods ──────────────────────────────
  openPanel(merc: any): void {
    this.selectedMerc.set(merc);
    this.panelOpen.set(true);
    this.panelRouteSearch = '';
    this.api.getMercaderistaRoutes(merc.id).subscribe({
      next: (routes) => this.assignedRoutes.set(routes as AssignedRoute[]),
      error: () => this.assignedRoutes.set([]),
    });
  }

  closePanel(): void { this.panelOpen.set(false); this.selectedMerc.set(null); this.assignedRoutes.set([]); }

  isAssigned(routeId: number): boolean {
    return this.assignedRoutes().some(r => r.id === routeId);
  }

  addRoute(ruta: Ruta): void {
    if (this.isAssigned(ruta.id)) return;
    this.assignedRoutes.update(list => [...list, { id: ruta.id, nombre: ruta.nombre, servicio: ruta.servicio, tipo_ruta: 'Variable' }]);
  }

  removeRoute(routeId: number): void {
    this.assignedRoutes.update(list => list.filter(r => r.id !== routeId));
  }

  setTipoRuta(routeId: number, tipo: string): void {
    this.assignedRoutes.update(list => list.map(r => r.id === routeId ? { ...r, tipo_ruta: tipo } : r));
  }

  get availableRoutes(): Ruta[] {
    const s = this.panelRouteSearch.toLowerCase();
    return this.routes().filter(r =>
      !this.isAssigned(r.id) &&
      (!s || r.nombre?.toLowerCase().includes(s) || r.servicio?.toLowerCase().includes(s))
    );
  }

  saveRoutes(): void {
    const merc = this.selectedMerc();
    if (!merc) return;
    this.panelSaving.set(true);
    const payload = this.assignedRoutes().map(r => ({ ruta_id: r.id, tipo_ruta: r.tipo_ruta }));
    this.api.syncMercaderistaRoutes(merc.id, payload).subscribe({
      next: () => {
        this.panelSaving.set(false);
        this.snack.open('Asignaciones guardadas', 'OK', { duration: 3000 });
        this.mercList.update(list => list.map(m =>
          m.id === merc.id ? { ...m, rutas_count: this.assignedRoutes().length } : m
        ));
        this.closePanel();
      },
      error: (err) => {
        this.panelSaving.set(false);
        this.snack.open(err?.error?.detail ?? 'Error al guardar', 'OK', { duration: 4000 });
      },
    });
  }
}
