import { Component, OnInit, inject, ViewChild, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatTooltipModule } from '@angular/material/tooltip';
import { environment } from '../../../environments/environment';
import { BaseChartDirective } from 'ng2-charts';
import { ChartConfiguration, ChartData, ChartType, ChartOptions } from 'chart.js';
import * as maplibregl from 'maplibre-gl';
import { Subject, Subscription } from 'rxjs';
import { debounceTime } from 'rxjs/operators';

@Component({
  selector: 'app-cliente-encuestador-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, BaseChartDirective, MatIconModule, MatFormFieldModule, MatSelectModule, MatTooltipModule],
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
    .dense-field {
      ::ng-deep .mat-mdc-text-field-wrapper {
        background-color: rgba(15, 23, 42, 0.5) !important;
        border-radius: 8px !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
      }
      ::ng-deep .mat-mdc-form-field-flex { padding: 0 12px !important; height: 40px !important; align-items: center !important; }
      ::ng-deep .mat-mdc-select-value,
      ::ng-deep .mat-mdc-select-placeholder,
      ::ng-deep .mat-mdc-select-value-text,
      ::ng-deep .mdc-text-field .mdc-text-field__input {
        color: rgba(255,255,255,0.7) !important;
        font-size: 12px !important;
        -webkit-text-fill-color: rgba(255,255,255,0.7) !important;
      }
      ::ng-deep .mat-mdc-select-arrow svg { fill: rgba(255, 255, 255, 0.7) !important; color: rgba(255, 255, 255, 0.7) !important; }
      ::ng-deep .mdc-notched-outline { display: none !important; }
      ::ng-deep .mat-mdc-form-field-infix { padding-top: 0 !important; padding-bottom: 0 !important; min-height: auto !important; }
    }
    ::ng-deep .dark-dropdown {
      background-color: #0f172a !important;
      border: 1px solid rgba(255,255,255,0.1) !important;
      border-radius: 8px !important;
      box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5) !important;
    }
    ::ng-deep .dark-dropdown .mat-mdc-option {
      min-height: 36px !important;
      font-size: 12px !important;
      color: #cbd5e1 !important;
    }
    ::ng-deep .dark-dropdown .mat-mdc-option:hover {
      background-color: rgba(99, 102, 241, 0.2) !important;
    }
    ::ng-deep .dark-dropdown .mdc-list-item__primary-text {
      color: #cbd5e1 !important;
    }
    ::ng-deep .dark-dropdown .mat-pseudo-checkbox {
      transform: scale(0.8) !important;
      border-color: rgba(255,255,255,0.5) !important;
    }
  `]
})
export class ClienteEncuestadorDashboardComponent implements OnInit, OnDestroy {
  private http = inject(HttpClient);
  private filterSubject = new Subject<void>();
  private filterSub!: Subscription;
  
  loading = true;
  exportando = false;
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

  // Filter Dropdown Data
  catalogs = {
    estados: [], ciudades: [], especialidades: [], sub_especialidades: [],
    universidades: [], centros: [] as any[], encuestadores: [] as any[],
    fuentes: [], valor_consulta_rangos: [], promedio_pacientes_rangos: [], dias_consulta: []
  };

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
  espChartData: ChartData<'bar'> = { labels: [], datasets: [] };
  valChartData: ChartData<'doughnut'> = { labels: [], datasets: [] };
  pacChartData: ChartData<'doughnut'> = { labels: [], datasets: [] };
  estChartData: ChartData<'bar'> = { labels: [], datasets: [] };
  uniChartData: ChartData<'bar'> = { labels: [], datasets: [] };
  cenChartData: ChartData<'bar'> = { labels: [], datasets: [] };
  diasChartData: ChartData<'bar'> = { labels: [], datasets: [] };
  horasChartData: ChartData<'bar'> = { labels: [], datasets: [] };
  contactData: ChartData<'bar'> = { labels: [], datasets: [] };
  ranking: any[] = [];

  private readonly palette = ['#8b5cf6', '#0ea5e9', '#10b981', '#f59e0b', '#ec4899', '#6366f1'];
  private readonly colorDim = 'rgba(148,163,184,0.15)';

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

  /** Toggle genérico: click en una porción/barra la agrega como filtro (o
   *  la saca si ya estaba) y dispara el refresco -- así cualquier gráfico
   *  puede filtrar a los demás, estilo Power BI. `mapper` traduce el label
   *  del gráfico (lo que se ve) al valor real del filtro cuando difieren
   *  (ej. centros: el label es el nombre, el filtro guarda el id). */
  private toggleChartFilter(filterKey: string, chartData: ChartData<any>, event: { active?: any[] }, mapper?: (label: string) => any) {
    const idx = event?.active?.[0]?.index;
    if (idx == null) return;
    const label = chartData.labels?.[idx] as string | undefined;
    if (label == null || label === 'N/A') return;
    const value = mapper ? mapper(label) : label;
    if (value == null) return;
    const arr = (this.filters as any)[filterKey] as any[];
    const pos = arr.indexOf(value);
    if (pos === -1) arr.push(value); else arr.splice(pos, 1);
    this.onFilterChange();
  }

  onEspClick(e: any) { this.toggleChartFilter('especialidades', this.espChartData, e); }
  onValClick(e: any) { this.toggleChartFilter('valor_consulta_rangos', this.valChartData, e); }
  onPacClick(e: any) { this.toggleChartFilter('promedio_pacientes_rangos', this.pacChartData, e); }
  onEstClick(e: any) { this.toggleChartFilter('estados', this.estChartData, e); }
  onUniClick(e: any) { this.toggleChartFilter('universidades', this.uniChartData, e); }
  onCenClick(e: any) { this.toggleChartFilter('centros', this.cenChartData, e, this.centroIdFor); }
  onDiasClick(e: any) { this.toggleChartFilter('dias_consulta', this.diasChartData, e); }

  /** Chips de todos los filtros activos (los de los dropdowns Y los que
   *  vinieron de click en un gráfico -- son el mismo estado) para poder
   *  verlos y sacarlos de a uno sin tener que abrir cada dropdown. */
  get activeFilterChips(): { key: string; value: any; label: string }[] {
    const out: { key: string; value: any; label: string }[] = [];
    const push = (key: string, labelFn?: (v: any) => string) => {
      for (const v of ((this.filters as any)[key] as any[])) {
        out.push({ key, value: v, label: labelFn ? labelFn(v) : String(v) });
      }
    };
    push('estados'); push('ciudades'); push('especialidades'); push('sub_especialidades');
    push('universidades');
    push('centros', (id) => this.catalogs.centros.find((c: any) => c.id_centro === id)?.nombre_centro || String(id));
    push('encuestadores', (id) => this.catalogs.encuestadores.find((u: any) => u.id_usuario === id)?.username || String(id));
    push('fuentes'); push('valor_consulta_rangos'); push('promedio_pacientes_rangos'); push('dias_consulta');
    return out;
  }

  removeChip(chip: { key: string; value: any }) {
    const arr = (this.filters as any)[chip.key] as any[];
    const pos = arr.indexOf(chip.value);
    if (pos !== -1) { arr.splice(pos, 1); this.onFilterChange(); }
  }

  clearAllFilters() {
    this.filters = {
      fecha_desde: this.filters.fecha_desde, fecha_hasta: this.filters.fecha_hasta,
      estados: [], ciudades: [], especialidades: [], sub_especialidades: [],
      universidades: [], centros: [], encuestadores: [], fuentes: [],
      valor_consulta_rangos: [], promedio_pacientes_rangos: [], dias_consulta: []
    };
    this.onFilterChange();
  }

  loadFilters() {
    this.http.get<any>(`${environment.apiUrl}/api/cliente-encuestador/filtros`).subscribe((res: any) => {
      if (res.success) {
        this.catalogs = res;
      }
    });
  }

  /** Mismo query string para /kpis, /medicos y /export -- los tres tienen que
   *  respetar exactamente los filtros activos (dropdowns + clicks en gráficos). */
  private buildFilterParams(): URLSearchParams {
    const params = new URLSearchParams();
    Object.keys(this.filters).forEach(k => {
      const v = (this.filters as any)[k];
      if (Array.isArray(v)) {
        v.forEach(val => { if (val) params.append(k, val); });
      } else if (v) {
        params.append(k, v);
      }
    });
    return params;
  }

  loadData() {
    this.loading = true;
    const params = this.buildFilterParams();

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

  /** Colores por índice, atenuando (gris) las categorías que NO están
   *  seleccionadas cuando ya hay un filtro activo en esa dimensión -- así
   *  se ve cuál gráfico originó el filtro (estilo Power BI). */
  private colorsFor(labels: string[], activeValues: any[], mapper?: (label: string) => any): string[] {
    const hasSelection = activeValues && activeValues.length > 0;
    return labels.map((l, i) => {
      if (hasSelection) {
        const v = mapper ? mapper(l) : l;
        if (!activeValues.includes(v)) return this.colorDim;
      }
      return this.palette[i % this.palette.length];
    });
  }

  private centroIdFor = (nombre: string) => this.catalogs.centros.find((c: any) => c.nombre_centro === nombre)?.id_centro;

  /** Alto del canvas de especialidades en base a la cantidad real de
   *  categorías (28px por barra, mínimo 320) -- el contenedor scrollea, así
   *  que da igual si son 5 o 150: cada barra queda con alto legible. */
  espChartHeightPx(): number {
    const n = this.espChartData.labels?.length || 0;
    return Math.max(320, n * 28);
  }

  exportarExcel() {
    this.exportando = true;
    const params = this.buildFilterParams();
    this.http.get(`${environment.apiUrl}/api/cliente-encuestador/export?${params.toString()}`, { responseType: 'blob' }).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `IQVIA_Medicos_${new Date().toISOString().slice(0, 10)}.xlsx`;
        a.click();
        window.URL.revokeObjectURL(url);
        this.exportando = false;
      },
      error: () => { this.exportando = false; },
    });
  }

  buildCharts(charts: any) {
    const espLabels = charts.especialidades.map((c: any) => c.name);
    this.espChartData = {
      labels: espLabels,
      datasets: [{ data: charts.especialidades.map((c: any) => c.value), backgroundColor: this.colorsFor(espLabels, this.filters.especialidades), borderRadius: 4 }]
    };

    const valLabels = charts.valor_consulta.map((c: any) => c.name);
    this.valChartData = {
      labels: valLabels,
      datasets: [{ data: charts.valor_consulta.map((c: any) => c.value), backgroundColor: this.colorsFor(valLabels, this.filters.valor_consulta_rangos), borderWidth: 0 }]
    };

    const pacLabels = charts.pacientes_semana.map((c: any) => c.name);
    this.pacChartData = {
      labels: pacLabels,
      datasets: [{ data: charts.pacientes_semana.map((c: any) => c.value), backgroundColor: this.colorsFor(pacLabels, this.filters.promedio_pacientes_rangos), borderWidth: 0 }]
    };

    const estLabels = charts.estados.map((c: any) => c.name);
    this.estChartData = {
      labels: estLabels,
      datasets: [{ data: charts.estados.map((c: any) => c.value), backgroundColor: this.colorsFor(estLabels, this.filters.estados), borderRadius: 4 }]
    };

    const uniLabels = charts.universidades.map((c: any) => c.name);
    this.uniChartData = {
      labels: uniLabels,
      datasets: [{ data: charts.universidades.map((c: any) => c.value), backgroundColor: this.colorsFor(uniLabels, this.filters.universidades), borderRadius: 4 }]
    };

    const cenLabels = charts.centros.map((c: any) => c.name);
    this.cenChartData = {
      labels: cenLabels,
      datasets: [{ data: charts.centros.map((c: any) => c.value), backgroundColor: this.colorsFor(cenLabels, this.filters.centros, this.centroIdFor), borderRadius: 4 }]
    };

    const diasLabels = charts.dias_consulta.map((c: any) => c.name);
    this.diasChartData = {
      labels: diasLabels,
      datasets: [{ data: charts.dias_consulta.map((c: any) => c.value), backgroundColor: this.colorsFor(diasLabels, this.filters.dias_consulta), borderRadius: 4 }]
    };

    // Horas: solo lectura -- no hay dimensión "hora" en los filtros (son
    // franjas/rangos, no valores discretos como el resto), así que no suma
    // al cross-filter, pero sí muestra en qué horario hay más consultorios
    // abiertos a la vez.
    this.horasChartData = {
      labels: (charts.horas_consulta || []).map((c: any) => c.name),
      datasets: [{ data: (charts.horas_consulta || []).map((c: any) => c.value), backgroundColor: '#0ea5e9', borderRadius: 4 }]
    };

    this.ranking = charts.ranking_encuestadores || [];

    this.contactData = {
      labels: ['WhatsApp', 'Email', 'Teléfono', 'Instagram', 'LinkedIn'],
      datasets: [{
        data: [this.kpis.pct_whatsapp, this.kpis.pct_email, this.kpis.pct_telefono, this.kpis.pct_instagram, this.kpis.pct_linkedin],
        backgroundColor: this.palette,
        borderRadius: 4
      }]
    };
  }

  initMap() {
    const mapEl = document.getElementById('map');
    if (!mapEl) return;
    
    if ((window as any)._map) {
      (window as any)._map.remove();
    }
    
    const map = new maplibregl.Map({
      container: 'map',
      style: 'https://tiles.openfreemap.org/styles/liberty', // O cualquier estilo de tiles
      center: [-66.9036, 10.4806], // Longitud, Latitud (Caracas)
      zoom: 5,
      attributionControl: false
    });
    
    map.addControl(new maplibregl.NavigationControl(), 'top-right');
    
    (window as any)._map = map;

    // Convert medicos to GeoJSON Features
    const features = this.medicos
      .filter(m => m.latitud != null && m.longitud != null)
      .map(m => ({
        type: 'Feature' as const,
        geometry: {
          type: 'Point' as const,
          coordinates: [Number(m.longitud), Number(m.latitud)]
        },
        properties: {
          id: m.id_medico,
          nombre: m.nombre_completo,
          especialidad: m.especialidad,
          centro: m.centro
        }
      }));

    const geojson = {
      type: 'FeatureCollection' as const,
      features: features
    };

    map.on('load', () => {
      map.addSource('medicos', {
        type: 'geojson',
        data: geojson,
        cluster: true,
        clusterMaxZoom: 14,
        clusterRadius: 50
      });

      // Cluster circle layer
      map.addLayer({
        id: 'clusters',
        type: 'circle',
        source: 'medicos',
        filter: ['has', 'point_count'],
        paint: {
          'circle-color': [
            'step',
            ['get', 'point_count'],
            '#a78bfa', // < 5 medicos
            5,
            '#8b5cf6', // 5-15 medicos
            15,
            '#6d28d9'  // >= 15 medicos
          ],
          'circle-radius': [
            'step',
            ['get', 'point_count'],
            15,
            5,
            20,
            15,
            25
          ],
          'circle-stroke-width': 2,
          'circle-stroke-color': '#ffffff'
        }
      });

      // Cluster count label layer
      map.addLayer({
        id: 'cluster-count',
        type: 'symbol',
        source: 'medicos',
        filter: ['has', 'point_count'],
        layout: {
          'text-field': '{point_count}',
          'text-font': ['Open Sans Regular', 'Arial HTML5'],
          'text-size': 12
        },
        paint: {
          'text-color': '#ffffff'
        }
      });

      // Unclustered single points layer
      map.addLayer({
        id: 'unclustered-point',
        type: 'circle',
        source: 'medicos',
        filter: ['!', ['has', 'point_count']],
        paint: {
          'circle-color': '#10b981', // emerald color
          'circle-radius': 7,
          'circle-stroke-width': 1.5,
          'circle-stroke-color': '#ffffff'
        }
      });

      // Click event to expand clusters
      map.on('click', 'clusters', (e) => {
        const features = map.queryRenderedFeatures(e.point, { layers: ['clusters'] });
        const clusterId = features[0].properties['cluster_id'];
        const source = map.getSource('medicos') as any;
        source.getClusterExpansionZoom(clusterId, (err: any, zoom: number) => {
          if (err) return;
          const geom = features[0].geometry as any;
          map.easeTo({
            center: geom.coordinates,
            zoom: zoom
          });
        });
      });

      // Click event for details popup on single points
      map.on('click', 'unclustered-point', (e) => {
        const features = map.queryRenderedFeatures(e.point, { layers: ['unclustered-point'] });
        if (!features.length) return;
        const f = features[0];
        const geom = f.geometry as any;
        const props = f.properties as any;

        new maplibregl.Popup({ offset: 10 })
          .setLngLat(geom.coordinates)
          .setHTML(`
            <div style="color: #0f172a; font-family: sans-serif; font-size: 12px; padding: 4px;">
              <strong style="font-size: 14px; display: block; margin-bottom: 2px;">${props.nombre}</strong>
              <span style="color: #64748b; display: block; margin-bottom: 2px;">${props.especialidad}</span>
              <span style="color: #6366f1; font-weight: 500; display: block;">${props.centro}</span>
            </div>
          `)
          .addTo(map);
      });

      // Hover states
      map.on('mouseenter', 'clusters', () => { map.getCanvas().style.cursor = 'pointer'; });
      map.on('mouseleave', 'clusters', () => { map.getCanvas().style.cursor = ''; });
      map.on('mouseenter', 'unclustered-point', () => { map.getCanvas().style.cursor = 'pointer'; });
      map.on('mouseleave', 'unclustered-point', () => { map.getCanvas().style.cursor = ''; });
    });
  }
}
