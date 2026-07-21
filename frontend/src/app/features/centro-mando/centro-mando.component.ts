import { Component, OnInit, signal, HostListener, inject } from '@angular/core';
import { CommonModule, formatDate } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';
import { RealtimeService } from '../../core/services/realtime.service';
import { RevisionVisitasComponent } from '../revision-visitas/revision-visitas.component';
import { VisitThreadDialogComponent } from '../chat/visit-thread-dialog.component';
import { AuthImgDirective } from '../../shared/directives/auth-img.directive';
import { AuthImageCacheService } from '../../core/services/auth-image-cache.service';

@Component({
  selector: 'app-centro-mando',
  standalone: true,
  imports: [
    CommonModule, FormsModule,
    MatIconModule, MatButtonModule,
    MatProgressSpinnerModule, MatTooltipModule, MatDialogModule,
    RevisionVisitasComponent, AuthImgDirective
  ],
  templateUrl: './centro-mando.component.html',
  styleUrls: ['./centro-mando.component.scss']
})
export class CentroMandoComponent implements OnInit {

  // ─── Vista (toggle Activaciones / Visitas) ─────────────────────────────────
  vista = signal<'activaciones' | 'visitas'>('activaciones');

  // ─── Loading ───────────────────────────────────────────────────────────────
  loadingResumen      = signal(true);
  loadingActivaciones = signal(false);

  // ─── Resumen del Día (top stats) ───────────────────────────────────────────
  resumenDia = signal<any>(null);

  // ─── Activaciones / Tabs ───────────────────────────────────────────────────
  activaciones    = signal<any[]>([]);
  stats           = signal<any>({});
  porMercaderista = signal<any[]>([]);
  pendientes      = signal<any[]>([]);
  gestionPorDia   = signal<any>({ fechas: [], clientes: [] });
  clientes        = signal<any[]>([]);

  // ─── Filtros Globales (Día) ────────────────────────────────────────────────
  get fecha(): string {
    return this.filtroDesde;
  }
  set fecha(val: string) {
    this.filtroDesde = val;
  }

  filtroCliente: number | null  = null;

  // ─── Filtros Rango (Global) ────────────────────────────────────────────────
  filtroDesde: string = this.todayStr();
  filtroHasta: string = this.todayStr();

  // ─── Vista activa ──────────────────────────────────────────────────────────
  activeView: 'dashboard' | 'mercaderistas' | 'gestion' | 'pendientes' | 'lista' = 'dashboard';

  // ─── UI State (Detalle y Modal) ───────────────────────────────────────────
  showDetalle: 'activos' | 'faltantes' | null = null;
  detalleList: any[] = [];
  
  showModalPdvs = false;
  modalPdvs = { pendientes: [] as any[], activos: [] as any[], completados: [] as any[] };

  // ─── Búsqueda / sub-filtros locales ───────────────────────────────────────
  searchText: string = '';
  tabPunto:   'act' | 'com' = 'act';
  tabCliente: 'act' | 'com' = 'act';

  // ─── Helpers ─────────────────────────────────────────────────────────────
  get diaSemana(): string {
    const DIAS = ['Domingo','Lunes','Martes','Miércoles','Jueves','Viernes','Sábado'];
    const d = new Date(this.filtroDesde + 'T12:00:00');
    return DIAS[d.getDay()];
  }

  get fechaDisplay(): string {
    const d = new Date(this.filtroDesde + 'T12:00:00');
    return `${String(d.getDate()).padStart(2,'0')}/${String(d.getMonth()+1).padStart(2,'0')}/${d.getFullYear()}`;
  }

  get isHoy(): boolean {
    return this.filtroDesde === this.todayStr() && this.filtroHasta === this.todayStr();
  }

  get labelPeriodo(): string {
    return this.filtroDesde === this.filtroHasta ? 'HOY' : 'EN PERÍODO';
  }

  get dateRangeDisplay(): string {
    if (this.filtroDesde === this.filtroHasta) {
      const d = new Date(this.filtroDesde + 'T12:00:00');
      const DIAS = ['Domingo','Lunes','Martes','Miércoles','Jueves','Viernes','Sábado'];
      const dia = DIAS[d.getDay()];
      return `${dia} ${this.formatDateDMY(this.filtroDesde)}`;
    } else {
      return `${this.formatDateDMY(this.filtroDesde)} al ${this.formatDateDMY(this.filtroHasta)}`;
    }
  }

  formatDateDMY(dateStr: string): string {
    const d = new Date(dateStr + 'T12:00:00');
    return `${String(d.getDate()).padStart(2,'0')}/${String(d.getMonth()+1).padStart(2,'0')}/${d.getFullYear()}`;
  }

  constructor(
    private api: ApiService, private auth: AuthService, private realtime: RealtimeService,
    private dialog: MatDialog, private router: Router,
  ) {}

  private rtDebounce?: any;

  ngOnInit() {
    this.loadClientes();
    this.loadResumenDia();
    this.loadActivaciones();
    // Tiempo real: refrescar al crear/revisar visitas o decidir fotos (con debounce)
    this.realtime.events$.subscribe(ev => {
      if (ev.tipo.startsWith('visit.') || ev.tipo.startsWith('photo.')) {
        clearTimeout(this.rtDebounce);
        this.rtDebounce = setTimeout(() => { this.loadResumenDia(); this.loadActivaciones(); }, 800);
      }
    });
  }

  private todayStr(): string {
    return formatDate(new Date(), 'yyyy-MM-dd', 'en-US');
  }

  private addDays(dateStr: string, n: number): string {
    const d = new Date(dateStr + 'T12:00:00');
    d.setDate(d.getDate() + n);
    return formatDate(d, 'yyyy-MM-dd', 'en-US');
  }

  // ─── Cargas ───────────────────────────────────────────────────────────────
  loadClientes() {
    this.api.getCentroMandoClientes().subscribe({
      next: (res) => { if (res.success) this.clientes.set(res.clientes); },
      error: () => {}
    });
  }

  loadResumenDia() {
    this.loadingResumen.set(true);
    const opts: any = { desde: this.filtroDesde, hasta: this.filtroHasta };
    if (this.filtroCliente) opts.cliente_id = this.filtroCliente;

    this.api.getCentroMandoResumenDia(opts).subscribe({
      next: (res) => {
        if (res.success) {
          this.resumenDia.set(res);
          // Actualizar detalle si está abierto
          if (this.showDetalle === 'activos') {
            this.detalleList = res.mercaderistas?.activos || [];
          } else if (this.showDetalle === 'faltantes') {
            this.detalleList = res.mercaderistas?.faltantes || [];
          }
        }
        this.loadingResumen.set(false);
      },
      error: () => this.loadingResumen.set(false)
    });
  }

  loadActivaciones() {
    this.loadingActivaciones.set(true);
    const opts: any = { desde: this.filtroDesde, hasta: this.filtroHasta };
    if (this.filtroCliente) opts.cliente_id = this.filtroCliente;

    this.api.getCentroMandoActivaciones(opts).subscribe({
      next: (res) => {
        if (res.success) {
          this.activaciones.set(res.activaciones || []);
          this.stats.set(res.stats || {});
          this.porMercaderista.set(res.por_mercaderista || []);
          this.pendientes.set(res.pendientes || []);
          this.gestionPorDia.set(res.gestion_por_dia || { fechas: [], clientes: [] });
        }
        this.loadingActivaciones.set(false);
      },
      error: () => this.loadingActivaciones.set(false)
    });
  }

  // ─── Acciones Top UI ──────────────────────────────────────────────────────
  irHoy() {
    const today = this.todayStr();
    this.filtroDesde = today;
    this.filtroHasta = today;
    this.refresh();
  }

  navegarFecha(dias: number) {
    this.filtroDesde = this.addDays(this.filtroDesde, dias);
    this.filtroHasta = this.addDays(this.filtroHasta, dias);
    this.refresh();
  }

  refresh() {
    this.loadResumenDia();
    this.loadActivaciones();
  }

  onClienteChange() {
    this.refresh();
  }

  buscarRango() {
    this.refresh();
  }

  // ─── Toggle Detalle Mercaderistas ─────────────────────────────────────────
  toggleDetalle(tipo: 'activos' | 'faltantes') {
    if (this.showDetalle === tipo) {
      this.showDetalle = null;
      this.detalleList = [];
    } else {
      this.showDetalle = tipo;
      const r = this.resumenDia();
      if (!r) return;
      this.detalleList = tipo === 'activos' ? r.mercaderistas.activos : r.mercaderistas.faltantes;
    }
  }

  // ─── Modal PDVs ───────────────────────────────────────────────────────────
  openPdvsModal() {
    const pts = this.resumenDia()?.puntos_interes?.detalle || [];
    this.modalPdvs = { pendientes: [], activos: [], completados: [] };

    // En modo rango (varios días), "detalle" trae una fila por PDV+mercaderista
    // POR DÍA — el mismo par puede repetirse. El @for del modal usa
    // id_punto+id_mercaderista como track, así que las claves duplicadas
    // rompen el render de esa sección entera (Angular NG0955). Dedupe por
    // bucket quedándonos con la fila "más avanzada" (completado > activo).
    const dedup = (arr: any[]) => {
      const map = new Map<string, any>();
      for (const p of arr) map.set(p.id_punto + '_' + p.id_mercaderista, p);
      return [...map.values()];
    };

    for (const p of pts) {
      const com = p.com ?? (p.clientes_com ?? 0);  // integer in range mode, boolean in single-day
      const act = p.act ?? (p.clientes_act ?? 0);
      if (com > 0 || com === true) {
        this.modalPdvs.completados.push(p);
      } else if (act > 0 || act === true) {
        this.modalPdvs.activos.push(p);
      } else {
        this.modalPdvs.pendientes.push(p);
      }
    }
    this.modalPdvs.pendientes = dedup(this.modalPdvs.pendientes);
    this.modalPdvs.activos = dedup(this.modalPdvs.activos);
    this.modalPdvs.completados = dedup(this.modalPdvs.completados);
    this.showModalPdvs = true;
  }

  closeModal() {
    this.showModalPdvs = false;
  }

  @HostListener('document:keydown.escape')
  onEscape() {
    this.closeModal();
  }

  // ─── Utils UI ─────────────────────────────────────────────────────────────
  irATab(tab: typeof this.activeView) {
    this.activeView = tab;
  }

  /** Lista completa de mercaderistas ASIGNADOS (del resumen) + métricas de
   *  ejecución (del detalle de activaciones). Así aparecen TODOS, no solo los
   *  que ya subieron foto, y los conteos cuadran con el resumen de arriba. */
  get mercaderistasUnificados(): any[] {
    // El backend ya devuelve por_mercaderista a nivel ejecución (PDV×cliente),
    // incluyendo a los que tienen 0 actividad (vienen de la programación de ruta).
    return this.porMercaderista();
  }

  get filteredMercaderistas() {
    const q = this.searchText.toLowerCase();
    return this.mercaderistasUnificados.filter(m =>
      !q || (m.nombre || '').toLowerCase().includes(q)
    );
  }

  /** PDV/clientes pendientes (sin activación) del mercaderista del modal. */
  get mercPendientes(): any[] {
    const m = this.selectedMercDet();
    if (!m) return [];
    return this.pendientes().filter(p => p.id_mercaderista === m.id_mercaderista);
  }

  // Lightbox de fotos
  lightboxOpen = signal(false);
  lightboxUrl = signal<string | null>(null);
  lightboxTitle = '';
  openLightbox(url: string | null | undefined, title: string): void {
    if (!url) return;
    this.lightboxUrl.set(url);
    this.lightboxTitle = title;
    this.lightboxOpen.set(true);
  }
  closeLightbox(): void { this.lightboxOpen.set(false); this.lightboxUrl.set(null); }

  private authImageCache = inject(AuthImageCacheService);
  /** El botón de descarga usaba <a href download>, pero /api/media/foto exige
   * JWT y una navegación de <a> no lo envía (igual que un <img src>). Se
   * descarga el blob vía HttpClient (con el token) y se dispara la descarga
   * desde el Object URL resultante. */
  downloadLightboxImage(): void {
    const url = this.lightboxUrl();
    if (!url) return;
    if (!url.startsWith('/api/media/')) {
      window.open(url, '_blank');
      return;
    }
    this.authImageCache.get(url).subscribe(objectUrl => {
      const a = document.createElement('a');
      a.href = objectUrl;
      a.download = '';
      a.click();
    });
  }

  /** Duración legible: minutos, pero en horas cuando es >= 60 min. */
  formatDuracion(min: number | null | undefined): string {
    if (min == null) return '—';
    if (min < 60) return `${min}m`;
    const h = Math.floor(min / 60);
    const m = min % 60;
    return m ? `${h}h ${m}m` : `${h}h`;
  }

  // Detalle de visita (modal con fotos + chat) — pestaña "Todas las visitas"
  visitDetailOpen = signal(false);
  selectedVisit = signal<any>(null);
  openVisitDetail(v: any): void { this.selectedVisit.set(v); this.visitDetailOpen.set(true); }
  closeVisitDetail(): void { this.visitDetailOpen.set(false); this.selectedVisit.set(null); }
  verMercDesdeVisita(v: any): void {
    const m = this.mercaderistasUnificados.find(x => x.id_mercaderista === v.id_mercaderista);
    this.closeVisitDetail();
    if (m) this.openMercDetail(m);
  }
  estadoVisitaLabel(v: any): string {
    return v.estado_presencia === 'completa' ? 'Completa'
      : v.estado_presencia === 'activo' ? 'Activa' : 'Solo salida';
  }

  get filteredPendientes() {
    const q = this.searchText.toLowerCase();
    return this.pendientes().filter(p =>
      !q || (p.mercaderista||'').toLowerCase().includes(q) ||
            (p.cliente||'').toLowerCase().includes(q) ||
            (p.punto_de_interes||'').toLowerCase().includes(q)
    );
  }

  get filteredLista() {
    const q = this.searchText.toLowerCase();
    return this.activaciones().filter(v =>
      !q || (v.mercaderista||'').toLowerCase().includes(q) ||
            (v.cliente||'').toLowerCase().includes(q) ||
            (v.punto_de_interes||'').toLowerCase().includes(q)
    );
  }

  get pendientesGroupedByMerc() {
    const groups: { [k: string]: any[] } = {};
    for (const p of this.filteredPendientes) {
      const k = p.mercaderista || 'Sin asignar';
      if (!groups[k]) groups[k] = [];
      groups[k].push(p);
    }
    return Object.keys(groups).sort().map(k => ({ mercaderista: k, items: groups[k] }));
  }

  getCompletadoForId(id: any, type: 'punto' | 'cliente'): any {
    const arr = type === 'punto' ? this.stats()?.pp_completas : this.stats()?.pc_completas;
    if (!arr) return null;
    return arr.find((x: any) => x.id === id) || null;
  }

  pct(n: number, t: number) {
    return t ? Math.round(n / t * 100) : 0;
  }

  getBarColor(pct: number): string {
    if (pct >= 90) return '#22c55e';
    if (pct >= 60) return '#f59e0b';
    return '#ef4444';
  }

  /** % de la barra según el toggle Act./Comp. (estilo v1). */
  pctFor(t: any, type: 'punto' | 'cliente'): number {
    const tab = type === 'punto' ? this.tabPunto : this.tabCliente;
    if (tab === 'com') return this.getCompletadoForId(t.id, type)?.porcentaje || 0;
    return t.porcentaje || 0;
  }

  /** Conteo "con/total" según el toggle Act./Comp. */
  countFor(t: any, type: 'punto' | 'cliente'): string {
    const tab = type === 'punto' ? this.tabPunto : this.tabCliente;
    if (tab === 'com') return `${this.getCompletadoForId(t.id, type)?.con || 0}/${t.total}`;
    return `${t.con || 0}/${t.total}`;
  }

  /** Texto de ayuda según el toggle activo. */
  helpFor(tab: 'act' | 'com'): string {
    return tab === 'act'
      ? 'Activado = la visita tiene foto de activación (apertura).'
      : 'Completado = la visita tiene activación (apertura) y cierre.';
  }

  /** Tooltip detallado para el ícono de info. */
  get barsTooltip(): string {
    return 'Cada fila es un PDV (Por Punto) o un cliente (Por Cliente). '
      + 'El número con/total = visitas con la foto requerida / visitas PLANIFICADAS en el período. '
      + 'Act.: cuenta las visitas con foto de activación (apertura). '
      + 'Comp.: cuenta las visitas con activación Y cierre. '
      + 'Por eso en Act. un punto puede salir <100% si alguna visita solo tiene foto de cierre sin activación, '
      + 'y en Comp. baja si se activó pero no se cerró.';
  }

  // ─── Detalle de mercaderista (modal) ──────────────────────────────────────
  mercDetailOpen = signal(false);
  selectedMercDet = signal<any>(null);

  openMercDetail(m: any): void {
    this.selectedMercDet.set(m);
    this.mercDetailOpen.set(true);
  }
  closeMercDetail(): void {
    this.mercDetailOpen.set(false);
    this.selectedMercDet.set(null);
  }
  get mercVisitas(): any[] {
    const m = this.selectedMercDet();
    if (!m) return [];
    return this.activaciones().filter(v => v.id_mercaderista === m.id_mercaderista);
  }
  estadoLabel(v: any): string {
    return v.estado_presencia === 'completa' ? 'Completa'
      : v.estado_presencia === 'activo' ? 'Activo' : 'Solo salida';
  }
  estadoClass(v: any): string {
    return v.estado_presencia === 'completa' ? 'bg-emerald-950 text-emerald-400'
      : v.estado_presencia === 'activo' ? 'bg-amber-950 text-amber-400' : 'bg-red-950 text-red-400';
  }

  // ─── Chat por visita (sub-hilo de CHAT_GRUPOS: solo equipo / equipo+cliente) ─
  // Mismas tablas que AppWeb v1 y la APK del mercaderista — el botón de chat
  // navega al ChatComponent con el sub-hilo ya auto-provisionado. El chat
  // legacy del cliente (tab "Cliente" del inbox de ChatComponent) no se toca.
  openChat(v: any): void {
    if (!v?.id_visita) return;
    const ref = this.dialog.open(VisitThreadDialogComponent, {
      data: { visitaId: v.id_visita, puntoNombre: v.punto_de_interes },
      autoFocus: false,
    });
    ref.afterClosed().subscribe(thread => {
      if (thread?.id_grupo) {
        this.router.navigate(['/chat'], { queryParams: {
          grupo_cliente: thread.id_cliente, tipo_grupo: thread.tipo_grupo,
          grupo_visita: thread.id_visita, titulo: thread.titulo,
        } });
      }
    });
  }

  getGestionColorClass(pct: number): string {
    if (pct >= 95) return 'cell-green';
    if (pct >= 75) return 'cell-amber';
    return 'cell-red';
  }

  // ─── Export Excel Modal ─────────────────────────────────────────────────────
  showExportModal = false;
  exportLoading = false;
  exportFilters = { cuadrante: '', departamento: '', categoria: '' };
  exportFiltrosOpts: { cuadrantes: string[]; departamentos: string[]; categorias: string[] } =
    { cuadrantes: [], departamentos: [], categorias: [] };
  exportFiltrosLoading = false;

  openExportModal(): void {
    if (!this.filtroCliente) {
      alert('Selecciona un cliente antes de exportar.');
      return;
    }
    this.exportFilters = { cuadrante: '', departamento: '', categoria: '' };
    this.exportFiltrosOpts = { cuadrantes: [], departamentos: [], categorias: [] };
    this.showExportModal = true;
    this.exportFiltrosLoading = true;
    this.api.getExportVisitasFiltros({
      id_cliente: this.filtroCliente, fecha_inicio: this.filtroDesde, fecha_fin: this.filtroHasta,
    }).subscribe({
      next: (opts) => { this.exportFiltrosOpts = opts; this.exportFiltrosLoading = false; },
      error: () => { this.exportFiltrosLoading = false; },
    });
  }
  closeExportModal(): void {
    this.showExportModal = false;
  }
  exportVisitas(): void {
    if (!this.filtroCliente) return;
    this.exportLoading = true;
    const opts: any = {
      id_cliente: this.filtroCliente,
      fecha_inicio: this.filtroDesde,
      fecha_fin: this.filtroHasta
    };
    if (this.exportFilters.cuadrante) opts.cuadrante = this.exportFilters.cuadrante;
    if (this.exportFilters.departamento) opts.departamento = this.exportFilters.departamento;
    if (this.exportFilters.categoria) opts.categoria = this.exportFilters.categoria;

    this.api.exportVisitasExcel(opts).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Reporte_Visitas_${this.filtroDesde}_al_${this.filtroHasta}.xlsx`;
        a.click();
        window.URL.revokeObjectURL(url);
        this.exportLoading = false;
        this.showExportModal = false;
      },
      error: (err) => {
        console.error('Error al exportar:', err);
        alert('Error al generar el archivo Excel. Intenta de nuevo.');
        this.exportLoading = false;
      }
    });
  }
}

