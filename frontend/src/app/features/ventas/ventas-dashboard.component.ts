import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule, formatDate } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterLink } from '@angular/router';
import { BaseChartDirective } from 'ng2-charts';
import { ChartData, ChartOptions } from 'chart.js';
import { environment } from '../../../environments/environment';

type DashboardData = {
  periodo: { desde: string; hasta: string };
  resumen: { pedidos: number; total_vendido: number; ticket_promedio: number };
  por_vendedor: { vendedor: string; pedidos: number; total: number }[];
  por_dia: { dia: string; total: number; pedidos: number }[];
  top_productos: { producto: string; unidades: number; total: number }[];
  por_estado: { estado: string; cantidad: number }[];
  top_clientes: { cliente: string; pedidos: number; total: number }[];
};

type PuntoSerie = { semana: string; total: number };
type PuntoPronostico = { semana: string; total_esperado: number; rango_bajo: number; rango_alto: number };
type ClientePronostico = {
  id_cliente: number; cliente: string;
  semanas_con_historial: number; semanas_con_pedidos: number; total_historico: number;
  serie_historica: PuntoSerie[];
  suficiente_historial: boolean; semanas_faltantes: number;
  pronostico: PuntoPronostico[];
};

@Component({
  selector: 'app-ventas-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule, MatProgressSpinnerModule, MatTooltipModule, RouterLink, BaseChartDirective],
  templateUrl: './ventas-dashboard.component.html',
})
export class VentasDashboardComponent implements OnInit {
  private http = inject(HttpClient);
  private API = `${environment.apiUrl}/api/vendedor`;

  loading = signal(true);
  data = signal<DashboardData | null>(null);

  desde = this._isoHace(30);
  hasta = this._isoHoy();

  porDiaChart: ChartData<'line'> = { labels: [], datasets: [] };
  porEstadoChart: ChartData<'doughnut'> = { labels: [], datasets: [] };

  lineOptions: ChartOptions<'line'> = {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(148,163,184,0.08)' } },
      y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(148,163,184,0.08)' }, beginAtZero: true },
    },
  };
  doughnutOptions: ChartOptions<'doughnut'> = {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8', boxWidth: 10, font: { size: 11 } } } },
  };

  // ── Pronóstico de pedidos (roadmap predictivo, item S2) ─────────────────
  loadingPronostico = signal(true);
  pronosticoClientes = signal<ClientePronostico[]>([]);
  pronosticoSeleccionado = signal<ClientePronostico | null>(null);
  idClientePronostico: number | null = null;
  pronosticoChart: ChartData<'line'> = { labels: [], datasets: [] };
  pronosticoOptions: ChartOptions<'line'> = {
    responsive: true, maintainAspectRatio: false, spanGaps: false,
    interaction: { intersect: false, mode: 'index' },
    plugins: {
      legend: {
        display: true, position: 'bottom',
        labels: {
          color: '#94a3b8', boxWidth: 10, font: { size: 11 },
          filter: (item) => !!item.text && !item.text.startsWith('_'),
        },
      },
    },
    scales: {
      x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(148,163,184,0.08)' } },
      y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(148,163,184,0.08)' }, beginAtZero: true },
    },
  };

  ngOnInit() { this.cargar(); this.cargarPronostico(); }

  private _isoHoy(): string { return new Date().toISOString().slice(0, 10); }
  private _isoHace(dias: number): string { const d = new Date(); d.setDate(d.getDate() - dias); return d.toISOString().slice(0, 10); }
  private _fmtSemana(iso: string): string { return formatDate(iso, 'dd/MM', 'en-US'); }

  cargar() {
    this.loading.set(true);
    this.http.get<DashboardData>(`${this.API}/dashboard`, { params: { desde: this.desde, hasta: this.hasta } }).subscribe({
      next: d => {
        this.data.set(d);
        this.porDiaChart = {
          labels: d.por_dia.map(x => x.dia.slice(5)),
          datasets: [{ data: d.por_dia.map(x => x.total), label: 'Ventas', borderColor: '#059669', backgroundColor: 'rgba(5,150,105,0.15)', fill: true, tension: 0.3, pointRadius: 2 }],
        };
        this.porEstadoChart = {
          labels: d.por_estado.map(x => x.estado),
          datasets: [{ data: d.por_estado.map(x => x.cantidad), backgroundColor: ['#94a3b8', '#3b82f6', '#10b981', '#ef4444', '#8b5cf6', '#f59e0b', '#14b8a6'], borderWidth: 0 }],
        };
        this.loading.set(false);
      },
      error: () => { this.loading.set(false); },
    });
  }

  // Ventana propia de 6 semanas hacia adelante -- independiente del filtro
  // Desde/Hasta de arriba, igual que la tendencia de competencia de
  // Auditoría de Campo (una proyección necesita más historia que el rango
  // corto que se usa para las tarjetas de resumen).
  cargarPronostico() {
    this.loadingPronostico.set(true);
    this.http.get<any>(`${this.API}/pronostico`, { params: { horizonte_semanas: 6 } }).subscribe({
      next: (res) => {
        this.loadingPronostico.set(false);
        const clientes: ClientePronostico[] = res?.clientes || [];
        this.pronosticoClientes.set(clientes);
        if (clientes.length) {
          const preferido = clientes.find(c => c.suficiente_historial) || clientes[0];
          this.idClientePronostico = preferido.id_cliente;
          this.seleccionarPronostico(preferido.id_cliente);
        }
      },
      error: () => { this.loadingPronostico.set(false); this.pronosticoClientes.set([]); },
    });
  }

  seleccionarPronostico(idCliente: number | null) {
    const c = this.pronosticoClientes().find(x => x.id_cliente === idCliente) || null;
    this.pronosticoSeleccionado.set(c);
    this.buildPronosticoChart(c);
  }

  private buildPronosticoChart(c: ClientePronostico | null): void {
    if (!c || !c.suficiente_historial || !c.serie_historica.length) {
      this.pronosticoChart = { labels: [], datasets: [] };
      return;
    }
    const nHist = c.serie_historica.length;
    const labels = [...c.serie_historica.map(p => this._fmtSemana(p.semana)), ...c.pronostico.map(p => this._fmtSemana(p.semana))];
    const huecoAntesForecast = new Array(nHist - 1).fill(null);
    const ultimoHistorico = c.serie_historica[nHist - 1].total;

    const historico = [...c.serie_historica.map(p => p.total), ...new Array(c.pronostico.length).fill(null)];
    const pronostico = [...huecoAntesForecast, ultimoHistorico, ...c.pronostico.map(p => p.total_esperado)];
    const bandaAlta = [...huecoAntesForecast, ultimoHistorico, ...c.pronostico.map(p => p.rango_alto)];
    const bandaBaja = [...huecoAntesForecast, ultimoHistorico, ...c.pronostico.map(p => p.rango_bajo)];

    this.pronosticoChart = {
      labels,
      datasets: [
        { data: bandaAlta, label: '_rango', borderColor: 'transparent', backgroundColor: 'rgba(16,185,129,0.12)', fill: '+1', pointRadius: 0, tension: 0.2 },
        { data: bandaBaja, label: '_rango', borderColor: 'transparent', backgroundColor: 'transparent', fill: false, pointRadius: 0, tension: 0.2 },
        { data: pronostico, label: 'Pronóstico', borderColor: '#10b981', borderDash: [6, 4], backgroundColor: 'transparent', tension: 0.2, pointRadius: 3, borderWidth: 2 },
        { data: historico, label: 'Histórico', borderColor: '#6366f1', backgroundColor: 'rgba(99,102,241,0.12)', fill: true, tension: 0.25, pointRadius: 3, borderWidth: 2 },
      ] as any,
    };
  }
}
