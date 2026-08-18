import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule, formatDate } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { BaseChartDirective } from 'ng2-charts';
import { ChartData, ChartOptions } from 'chart.js';
import { ApiService } from '../../core/services/api.service';
import { SearchableSelectComponent, SelectOption } from '../client-visits/searchable-select.component';

@Component({
  selector: 'app-centro-mando-auditoria',
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule, MatProgressSpinnerModule, MatTooltipModule, BaseChartDirective, SearchableSelectComponent],
  templateUrl: './centro-mando-auditoria.component.html',
  styleUrls: ['./centro-mando-auditoria.component.scss'],
})
export class CentroMandoAuditoriaComponent implements OnInit {
  private static readonly PAGE_SIZE = 10;
  private static readonly ALERTAS_PAGE_SIZE = 10;

  loading = signal(true);
  logPage = signal(1);
  porClienteCategoriaPage = signal(1);
  alertasPage = signal(1);
  expandedIndex = signal<number | null>(null);

  readonly INDICADORES_LABELS: { key: string; label: string }[] = [
    { key: 'aplico_planograma', label: 'Aplicó planograma' },
    { key: 'lineamiento_marca', label: 'Lineamiento de marca' },
    { key: 'precio_correcto', label: 'Precio correcto' },
    { key: 'limpieza_correcta', label: 'Limpieza correcta' },
    { key: 'participacion_correcta', label: 'Participación correcta' },
    { key: 'fifo_correcto', label: 'FIFO correcto' },
  ];

  // Filtros
  desde = '';
  hasta = '';
  idAuditor = '';
  idRuta = '';
  idCliente = '';
  idCategoria = '';
  search = '';

  filtros = signal<{ auditores: any[]; rutas: any[]; clientes: any[]; categorias: any[] }>({
    auditores: [], rutas: [], clientes: [], categorias: [],
  });

  // Adaptadores para el SearchableSelect (búsqueda en vez de scrollear)
  auditorOptions = computed<SelectOption[]>(() => this.filtros().auditores.map(a => ({ value: String(a.id), label: a.nombre })));
  rutaOptions = computed<SelectOption[]>(() => this.filtros().rutas.map(r => ({ value: String(r.id), label: r.nombre })));
  clienteOptions = computed<SelectOption[]>(() => this.filtros().clientes.map(c => ({ value: String(c.id), label: c.nombre })));
  categoriaOptions = computed<SelectOption[]>(() => this.filtros().categorias.map(c => ({ value: String(c.id), label: c.nombre })));

  kpis = signal<any>({
    rutas_auditadas: 0, pdvs_visitados: 0, clientes_auditados: 0,
    cuestionarios_completados: 0, fotos_subidas: 0, cumplimiento_promedio: 0,
  });
  alertasVencimiento = signal<any[]>([]);
  log = signal<any[]>([]);

  // Charts
  indicadoresData: ChartData<'bar'> = { labels: [], datasets: [] };
  competenciaData: ChartData<'bar'> = { labels: [], datasets: [] };
  porDiaData: ChartData<'line'> = { labels: [], datasets: [] };
  porAuditorData: ChartData<'bar'> = { labels: [], datasets: [] };

  horizontalBarOptions: ChartOptions<'bar'> = {
    responsive: true, maintainAspectRatio: false, indexAxis: 'y',
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' }, min: 0, max: 100 },
      y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
    },
  };
  barOptions: ChartOptions<'bar'> = {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
      y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
    },
  };
  lineOptions: ChartOptions<'line'> = {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
      y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
    },
  };
  auditorBarOptions: ChartOptions<'bar'> = {
    responsive: true, maintainAspectRatio: false, indexAxis: 'y',
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
      y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
    },
  };

  porClienteCategoria: any[] = [];

  // ── Paginación client-side (evita tablas kilométricas cuando hay mucho log) ──
  get totalLogPages(): number {
    return Math.max(1, Math.ceil(this.filteredLog.length / CentroMandoAuditoriaComponent.PAGE_SIZE));
  }

  get logPaginado(): any[] {
    const page = Math.min(this.logPage(), this.totalLogPages);
    const start = (page - 1) * CentroMandoAuditoriaComponent.PAGE_SIZE;
    return this.filteredLog.slice(start, start + CentroMandoAuditoriaComponent.PAGE_SIZE);
  }

  get totalPorClienteCategoriaPages(): number {
    return Math.max(1, Math.ceil(this.porClienteCategoria.length / 9));
  }

  get porClienteCategoriaPaginado(): any[] {
    const page = Math.min(this.porClienteCategoriaPage(), this.totalPorClienteCategoriaPages);
    const start = (page - 1) * 9;
    return this.porClienteCategoria.slice(start, start + 9);
  }

  get totalAlertasPages(): number {
    return Math.max(1, Math.ceil(this.alertasVencimiento().length / CentroMandoAuditoriaComponent.ALERTAS_PAGE_SIZE));
  }

  get alertasPaginado(): any[] {
    const page = Math.min(this.alertasPage(), this.totalAlertasPages);
    const start = (page - 1) * CentroMandoAuditoriaComponent.ALERTAS_PAGE_SIZE;
    return this.alertasVencimiento().slice(start, start + CentroMandoAuditoriaComponent.ALERTAS_PAGE_SIZE);
  }

  indicadoresDe(r: any): { label: string; ok: boolean }[] {
    return this.INDICADORES_LABELS.map(ix => ({ label: ix.label, ok: !!r[ix.key] }));
  }

  toggleExpand(i: number): void {
    this.expandedIndex.set(this.expandedIndex() === i ? null : i);
  }

  goLogPage(p: number): void {
    this.logPage.set(Math.min(Math.max(1, p), this.totalLogPages));
  }

  goPorClienteCategoriaPage(p: number): void {
    this.porClienteCategoriaPage.set(Math.min(Math.max(1, p), this.totalPorClienteCategoriaPages));
  }

  goAlertasPage(p: number): void {
    this.alertasPage.set(Math.min(Math.max(1, p), this.totalAlertasPages));
  }

  resetPages(): void {
    this.logPage.set(1);
    this.porClienteCategoriaPage.set(1);
    this.alertasPage.set(1);
    this.expandedIndex.set(null);
  }

  // Tendencia de presencia de competencia (roadmap predictivo, item S7):
  loadingTendencia = signal(true);
  tendenciaSeries = signal<any[]>([]);
  tendenciaChartData: ChartData<'line'> = { labels: [], datasets: [] };
  tendenciaChartOptions: ChartOptions<'line'> = {
    responsive: true, maintainAspectRatio: false, spanGaps: true,
    plugins: { legend: { display: true, position: 'bottom', labels: { color: '#94a3b8', boxWidth: 10, font: { size: 11 } } } },
    scales: {
      x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
      y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' }, min: 0, suggestedMax: 100 },
    },
  };
  private readonly TENDENCIA_COLORS = ['#f59e0b', '#f43f5e', '#8b5cf6', '#0ea5e9', '#22c55e', '#eab308'];

  constructor(private api: ApiService) { }

  ngOnInit(): void {
    const hoy = new Date();
    // Ventana por defecto de 90 días: los cuestionarios de auditoría se
    // registran de forma esporádica y 7 días dejaba el tablero en 0.
    const hace90 = new Date(hoy); hace90.setDate(hace90.getDate() - 90);
    this.desde = formatDate(hace90, 'yyyy-MM-dd', 'en-US');
    this.hasta = formatDate(hoy, 'yyyy-MM-dd', 'en-US');
    this.api.getCentroMandoAuditoriaFiltros().subscribe({ next: (d) => this.filtros.set(d), error: () => { } });
    this.load();
    this.loadTendencia();
  }

  load(): void {
    this.loading.set(true);
    this.api.getCentroMandoAuditoriaResumen({
      desde: this.desde, hasta: this.hasta,
      id_auditor: this.idAuditor ? Number(this.idAuditor) : undefined,
      id_ruta: this.idRuta ? Number(this.idRuta) : undefined,
      id_cliente: this.idCliente ? Number(this.idCliente) : undefined,
      id_categoria: this.idCategoria ? Number(this.idCategoria) : undefined,
    }).subscribe({
      next: (res) => {
        this.loading.set(false);
        if (!res?.success) { this.resetEmpty(); return; }
        this.resetPages();
        this.kpis.set(res.kpis);
        this.alertasVencimiento.set(res.alertas_vencimiento || []);
        this.log.set(res.log || []);
        this.porClienteCategoria = res.charts?.por_cliente_categoria || [];
        this.buildCharts(res.charts);
      },
      error: () => { this.loading.set(false); this.resetEmpty(); },
    });
    this.loadTendencia();
  }

  loadTendencia(): void {
    this.api.getCentroMandoAuditoriaTendenciaCompetencia({
      id_ruta: this.idRuta ? Number(this.idRuta) : undefined,
      id_cliente: this.idCliente ? Number(this.idCliente) : undefined,
      id_categoria: this.idCategoria ? Number(this.idCategoria) : undefined,
    }).subscribe({
      next: (res) => {
        this.loadingTendencia.set(false);
        if (!res?.success) { this.tendenciaSeries.set([]); this.tendenciaChartData = { labels: [], datasets: [] }; return; }
        this.tendenciaSeries.set(res.series || []);
        this.buildTendenciaChart(res.semanas || [], res.series || []);
      },
      error: () => { this.loadingTendencia.set(false); this.tendenciaSeries.set([]); this.tendenciaChartData = { labels: [], datasets: [] }; },
    });
  }

  private buildTendenciaChart(semanas: string[], series: any[]): void {
    const top = series.slice(0, 6);
    this.tendenciaChartData = {
      labels: semanas.map((s) => formatDate(s, 'dd/MM', 'en-US')),
      datasets: top.map((s, i) => ({
        data: s.media_movil, label: s.categoria,
        borderColor: this.TENDENCIA_COLORS[i % this.TENDENCIA_COLORS.length],
        backgroundColor: 'transparent', tension: 0.35, pointRadius: 2, borderWidth: 2,
      })),
    };
  }

  tendenciaIcon(t: string): string {
    return t === 'subiendo' ? 'trending_up' : t === 'bajando' ? 'trending_down' : 'trending_flat';
  }
  tendenciaColor(t: string): string {
    // Sube presión de competencia = mala noticia (rojo); baja = buena (verde).
    return t === 'subiendo' ? 'text-rose-500' : t === 'bajando' ? 'text-emerald-500' : 'text-slate-400';
  }

  private resetEmpty(): void {
    this.resetPages();
    this.kpis.set({ rutas_auditadas: 0, pdvs_visitados: 0, clientes_auditados: 0, cuestionarios_completados: 0, fotos_subidas: 0, cumplimiento_promedio: 0 });
    this.alertasVencimiento.set([]); this.log.set([]); this.porClienteCategoria = [];
  }

  private buildCharts(charts: any): void {
    const ind = charts?.indicadores || [];
    this.indicadoresData = {
      labels: ind.map((i: any) => i.indicador),
      datasets: [{
        data: ind.map((i: any) => { const t = i.si + i.no; return t ? Math.round((i.si / t) * 1000) / 10 : 0; }),
        label: '% Sí', backgroundColor: '#22c55e',
      }],
    };

    const comp = charts?.competencia || { actividad_pct: 0, material_pop_pct: 0, impulsadora_pct: 0 };
    this.competenciaData = {
      labels: ['Actividad', 'Material POP', 'Impulsadora'],
      datasets: [{
        data: [comp.actividad_pct, comp.material_pop_pct, comp.impulsadora_pct],
        label: '% PDVs con competencia', backgroundColor: '#f59e0b',
      }],
    };

    const porDia = charts?.por_dia || [];
    this.porDiaData = {
      labels: porDia.map((d: any) => d.fecha),
      datasets: [{ data: porDia.map((d: any) => d.auditorias), label: 'Auditorías', borderColor: '#6366f1', backgroundColor: 'rgba(99,102,241,0.2)', tension: 0.3, fill: true }],
    };

    const porAud = (charts?.por_auditor || []).slice(0, 10);
    this.porAuditorData = {
      labels: porAud.map((a: any) => a.auditor),
      datasets: [{ data: porAud.map((a: any) => a.auditorias), label: 'Auditorías', backgroundColor: '#38bdf8' }],
    };
  }

  onAuditorChange(v: string): void { this.idAuditor = v; this.load(); }
  onRutaChange(v: string): void { this.idRuta = v; this.load(); }
  onClienteChange(v: string): void { this.idCliente = v; this.load(); }
  onCategoriaChange(v: string): void { this.idCategoria = v; this.load(); }

  clearFilters(): void {
    this.idAuditor = ''; this.idRuta = ''; this.idCliente = ''; this.idCategoria = ''; this.search = '';
    this.load();
  }

  get filteredLog(): any[] {
    const q = this.search.trim().toLowerCase();
    if (!q) return this.log();
    return this.log().filter((r) =>
      (r.auditor || '').toLowerCase().includes(q) || (r.cliente || '').toLowerCase().includes(q) ||
      (r.punto_de_interes || '').toLowerCase().includes(q) || (r.categoria || '').toLowerCase().includes(q) ||
      (r.ruta || '').toLowerCase().includes(q),
    );
  }

  cumplimientoColor(pct: number): string {
    if (pct >= 80) return 'text-emerald-400';
    if (pct >= 50) return 'text-amber-400';
    return 'text-rose-400';
  }
}
