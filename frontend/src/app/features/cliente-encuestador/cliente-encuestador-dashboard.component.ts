import { Component, OnInit, inject, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { environment } from '../../../environments/environment';
import { BaseChartDirective } from 'ng2-charts';
import { ChartData, ChartOptions } from 'chart.js';
import * as L from 'leaflet';
import { Subject, Subscription } from 'rxjs';
import { debounceTime } from 'rxjs/operators';
import { SearchableSelectComponent, SearchableOption } from '../../shared/components/searchable-select/searchable-select.component';

@Component({
  selector: 'app-cliente-encuestador-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, BaseChartDirective, MatIconModule, SearchableSelectComponent],
  templateUrl: './cliente-encuestador-dashboard.component.html',
  styles: [`
    .glass-panel {
      background: rgba(15, 23, 42, 0.7);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255, 255, 255, 0.05);
    }
    .custom-scrollbar::-webkit-scrollbar {
      width: 6px;
    }
    .custom-scrollbar::-webkit-scrollbar-track {
      background: rgba(15, 23, 42, 0.5);
    }
    .custom-scrollbar::-webkit-scrollbar-thumb {
      background: rgba(99, 102, 241, 0.5);
      border-radius: 10px;
    }
  `]
})
export class ClienteEncuestadorDashboardComponent implements OnInit, OnDestroy {
  private http = inject(HttpClient);
  private filterSubject = new Subject<void>();
  private filterSub!: Subscription;

  loading = true;
  kpis: any = null;
  medicos: any[] = [];

  // Filters
  filters = {
    fecha_desde: '', fecha_hasta: '',
    estados: [] as string[], ciudades: [] as string[],
    especialidades: [] as string[], sub_especialidades: [] as string[],
    universidades: [] as string[], centros: [] as number[],
    encuestadores: [] as number[], fuentes: [] as string[],
    valor_consulta_rangos: [] as string[], promedio_pacientes_rangos: [] as string[],
    dias_consulta: [] as string[]
  };

  // Filter Dropdown Data (raw from API)
  catalogs = {
    estados: [], ciudades: [], especialidades: [], sub_especialidades: [],
    universidades: [], centros: [] as any[], encuestadores: [] as any[],
    fuentes: [], valor_consulta_rangos: [], promedio_pacientes_rangos: [], dias_consulta: []
  };

  // SearchableSelect options (built from catalogs)
  estadoOptions: SearchableOption<string>[] = [];
  ciudadOptions: SearchableOption<string>[] = [];
  especialidadOptions: SearchableOption<string>[] = [];
  subEspecialidadOptions: SearchableOption<string>[] = [];
  universidadOptions: SearchableOption<string>[] = [];
  centroOptions: SearchableOption<number>[] = [];
  encuestadorOptions: SearchableOption<number>[] = [];
  fuenteOptions: SearchableOption<string>[] = [];
  valorConsultaOptions: SearchableOption<string>[] = [];
  promedioPacientesOptions: SearchableOption<string>[] = [];
  diasConsultaOptions: SearchableOption<string>[] = [];

  // Charts Options
  doughnutOptions: ChartOptions<'doughnut'> = {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { position: 'right', labels: { color: '#94a3b8' } } }
  };

  barOptions: ChartOptions<'bar'> = {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
      y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } }
    }
  };

  horizontalBarOptions: ChartOptions<'bar'> = {
    responsive: true, maintainAspectRatio: false, indexAxis: 'y',
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
      y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } }
    }
  };

  // Chart Data
  espChartData: ChartData<'doughnut'> = { labels: [], datasets: [] };
  valChartData: ChartData<'doughnut'> = { labels: [], datasets: [] };
  pacChartData: ChartData<'doughnut'> = { labels: [], datasets: [] };
  estChartData: ChartData<'bar'> = { labels: [], datasets: [] };
  uniChartData: ChartData<'bar'> = { labels: [], datasets: [] };
  cenChartData: ChartData<'bar'> = { labels: [], datasets: [] };
  diasChartData: ChartData<'bar'> = { labels: [], datasets: [] };
  contactData: ChartData<'bar'> = { labels: [], datasets: [] };
  ranking: any[] = [];

  ngOnInit() {
    this.loadData();
    this.loadFilters();
    this.filterSub = this.filterSubject.pipe(debounceTime(600)).subscribe(() => {
      this.loadData();
    });
  }

  ngOnDestroy() {
    if (this.filterSub) this.filterSub.unsubscribe();
  }

  onFilterChange() {
    this.filterSubject.next();
  }

  loadFilters() {
    this.http.get<any>(`${environment.apiUrl}/api/cliente-encuestador/filtros`).subscribe((res: any) => {
      if (res.success) {
        this.catalogs = res;
        this.buildFilterOptions();
      }
    });
  }

  /** Build SearchableOption arrays from raw catalogs */
  private buildFilterOptions() {
    this.estadoOptions = (this.catalogs.estados || []).map(e => ({ value: e, label: e }));
    this.ciudadOptions = (this.catalogs.ciudades || []).map(c => ({ value: c, label: c }));
    this.especialidadOptions = (this.catalogs.especialidades || []).map(e => ({ value: e, label: e }));
    this.subEspecialidadOptions = (this.catalogs.sub_especialidades || []).map(e => ({ value: e, label: e }));
    this.universidadOptions = (this.catalogs.universidades || []).map(u => ({ value: u, label: u }));
    this.centroOptions = (this.catalogs.centros || []).map((c: any) => ({ value: c.id_centro, label: c.nombre_centro }));
    this.encuestadorOptions = (this.catalogs.encuestadores || []).map((e: any) => ({ value: e.id_usuario, label: e.username }));
    this.fuenteOptions = (this.catalogs.fuentes || []).map(f => ({ value: f, label: f }));
    this.valorConsultaOptions = (this.catalogs.valor_consulta_rangos || []).map(v => ({ value: v, label: v }));
    this.promedioPacientesOptions = (this.catalogs.promedio_pacientes_rangos || []).map(p => ({ value: p, label: p }));
    this.diasConsultaOptions = (this.catalogs.dias_consulta || []).map(d => ({ value: d, label: d }));
  }

  /** When a searchable-select value changes, update filters and trigger debounced load */
  onFiltroChange(key: string, value: any): void {
    (this.filters as any)[key] = value;
    this.filterSubject.next();
  }

  /** Detect dark mode from <html> class */
  isDark(): boolean {
    return document.documentElement.classList.contains('dark');
  }

  loadData() {
    this.loading = true;

    let params = new URLSearchParams();
    Object.keys(this.filters).forEach(k => {
      const v = (this.filters as any)[k];
      if (Array.isArray(v)) {
        v.forEach(val => { if (val) params.append(k, val); });
      } else if (v) {
        params.append(k, v);
      }
    });

    this.http.get<any>(`${environment.apiUrl}/api/cliente-encuestador/kpis?${params.toString()}`).subscribe({
      next: (res: any) => {
        this.kpis = res;
        if (res.charts) {
          this.buildCharts(res.charts);
        }

        this.http.get<any>(`${environment.apiUrl}/api/cliente-encuestador/medicos?page=1&per_page=1000&${params.toString()}`).subscribe((medRes: any) => {
          this.medicos = medRes.medicos || [];
          this.loading = false;
          setTimeout(() => this.initMap(), 100);
        });
      },
      error: () => this.loading = false
    });
  }

  buildCharts(charts: any) {
    // Helper to generate gradient or colors
    const bgColors = ['#8b5cf6', '#0ea5e9', '#10b981', '#f59e0b', '#ec4899', '#6366f1'];

    this.espChartData = {
      labels: charts.especialidades.map((c: any) => c.name),
      datasets: [{ data: charts.especialidades.map((c: any) => c.value), backgroundColor: bgColors, borderWidth: 0 }]
    };

    this.valChartData = {
      labels: charts.valor_consulta.map((c: any) => c.name),
      datasets: [{ data: charts.valor_consulta.map((c: any) => c.value), backgroundColor: bgColors, borderWidth: 0 }]
    };

    this.pacChartData = {
      labels: charts.pacientes_semana.map((c: any) => c.name),
      datasets: [{ data: charts.pacientes_semana.map((c: any) => c.value), backgroundColor: bgColors, borderWidth: 0 }]
    };

    this.estChartData = {
      labels: charts.estados.map((c: any) => c.name),
      datasets: [{ data: charts.estados.map((c: any) => c.value), backgroundColor: '#8b5cf6', borderRadius: 4 }]
    };

    this.uniChartData = {
      labels: charts.universidades.map((c: any) => c.name),
      datasets: [{ data: charts.universidades.map((c: any) => c.value), backgroundColor: ['#8b5cf6', '#0ea5e9'], borderRadius: 4 }]
    };

    this.cenChartData = {
      labels: charts.centros.map((c: any) => c.name),
      datasets: [{ data: charts.centros.map((c: any) => c.value), backgroundColor: ['#8b5cf6', '#0ea5e9'], borderRadius: 4 }]
    };

    this.diasChartData = {
      labels: charts.dias_consulta.map((c: any) => c.name),
      datasets: [{ data: charts.dias_consulta.map((c: any) => c.value), backgroundColor: bgColors, borderRadius: 4 }]
    };

    this.ranking = charts.ranking_encuestadores || [];

    this.contactData = {
      labels: ['WhatsApp', 'Email', 'Teléfono', 'Instagram', 'LinkedIn'],
      datasets: [{
        data: [this.kpis.pct_whatsapp, this.kpis.pct_email, this.kpis.pct_telefono, this.kpis.pct_instagram, this.kpis.pct_linkedin],
        backgroundColor: bgColors,
        borderRadius: 4
      }]
    };
  }

  initMap() {
    const mapEl = document.getElementById('map');
    if (!mapEl) return;

    // Clear previous map instance if exists
    if ((window as any)._map) {
      (window as any)._map.remove();
    }

    const map = L.map('map').setView([10.4806, -66.9036], 6); // Default Caracas
    (window as any)._map = map;
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '© OpenStreetMap, © CartoDB'
    }).addTo(map);

    // Simplistic approach: we don't have lat/lng in medicos, we can't accurately map them without geocoding.
    // Assuming backend will provide lat/lng in future, or we just put a central marker for now.
  }
}
