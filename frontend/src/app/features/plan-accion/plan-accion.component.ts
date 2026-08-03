import { Component, OnInit, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-plan-accion',
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule, MatProgressSpinnerModule, MatSnackBarModule, MatTooltipModule],
  templateUrl: './plan-accion.component.html',
})
export class PlanAccionComponent implements OnInit {
  loading = signal(true);
  recalculando = signal(false);
  items = signal<any[]>([]);
  fechaCalculo = signal<string | null>(null);
  totalCriticos = signal(0);

  vista = signal<'lista' | 'clusters'>('lista');
  clusters = signal<any[]>([]);
  loadingClusters = signal(false);
  totalBackupsSugeridos = signal(0);

  mercaderistas = signal<any[]>([]);
  seleccionMerc: Record<number, number | null> = {};
  confirmandoIdx = signal<number | null>(null);

  filtroRuta: string | null = null;
  filtroCliente: string | null = null;
  filtroTipo: string | null = null;
  filtroPrioridad: string | null = null;
  search = '';

  constructor(private api: ApiService, private snack: MatSnackBar, public auth: AuthService) {}

  ngOnInit(): void {
    this.load();
    this.api.getMercaderistas().subscribe({ next: (d) => this.mercaderistas.set(d || []), error: () => {} });
  }

  load(): void {
    this.loading.set(true);
    this.api.getPlanAccionPendientes().subscribe({
      next: (res) => {
        this.loading.set(false);
        this.items.set(res?.items || []);
        this.fechaCalculo.set(res?.fecha_calculo || null);
        this.totalCriticos.set(res?.total_criticos || 0);
      },
      error: () => { this.loading.set(false); this.items.set([]); this.snack.open('Error al cargar el plan de acción', 'OK', { duration: 3000 }); },
    });
  }

  toggleVista(v: 'lista' | 'clusters'): void {
    this.vista.set(v);
    if (v === 'clusters' && !this.clusters().length) this.loadClusters();
  }

  loadClusters(): void {
    this.loadingClusters.set(true);
    this.api.getPlanAccionClusters().subscribe({
      next: (res) => { this.loadingClusters.set(false); this.clusters.set(res?.grupos || []); this.totalBackupsSugeridos.set(res?.total_backups_sugeridos || 0); },
      error: () => { this.loadingClusters.set(false); this.clusters.set([]); this.snack.open('Error al agrupar por cercanía', 'OK', { duration: 3000 }); },
    });
  }

  confirmarRuta(g: any, idx: number): void {
    const idMerc = this.seleccionMerc[idx];
    if (!idMerc) { this.snack.open('Elegí un mercaderista primero', 'OK', { duration: 2500 }); return; }
    this.confirmandoIdx.set(idx);
    this.api.confirmarRutaBck(g.items, idMerc).subscribe({
      next: (res) => {
        this.confirmandoIdx.set(null);
        this.snack.open(`${res.nombre_ruta} creada con ${res.cantidad_pdvs} PDV(s) para hoy`, 'OK', { duration: 4500 });
        this.clusters.update((list) => list.filter((x) => x !== g));
      },
      error: () => { this.confirmandoIdx.set(null); this.snack.open('Error al crear la ruta', 'OK', { duration: 3000 }); },
    });
  }

  recalcular(): void {
    // El backend corre esto en background (la query puede tardar) -- el POST
    // vuelve al toque, así que esperamos unos segundos y recargamos solos.
    this.recalculando.set(true);
    this.api.recalcularPlanAccion().subscribe({
      next: () => {
        this.snack.open('Recalculando en background, actualizando en unos segundos...', 'OK', { duration: 4000 });
        setTimeout(() => {
          this.recalculando.set(false);
          this.load();
          if (this.vista() === 'clusters') this.loadClusters();
        }, 12000);
      },
      error: () => { this.recalculando.set(false); this.snack.open('Error al recalcular', 'OK', { duration: 3000 }); },
    });
  }

  rutasOpts = computed(() => Array.from(new Set(this.items().map((i) => i.ruta_nombre).filter(Boolean))).sort());
  clientesOpts = computed(() => Array.from(new Set(this.items().map((i) => i.cliente_nombre).filter(Boolean))).sort());
  totalRechazadas = computed(() => this.items().filter((i) => i.tipo_pendiente === 'fotos_rechazadas').length);

  get filteredItems(): any[] {
    const q = this.search.trim().toLowerCase();
    return this.items().filter((i) => {
      if (this.filtroRuta && i.ruta_nombre !== this.filtroRuta) return false;
      if (this.filtroCliente && i.cliente_nombre !== this.filtroCliente) return false;
      if (this.filtroTipo && i.tipo_pendiente !== this.filtroTipo) return false;
      if (this.filtroPrioridad && i.prioridad_ruta !== this.filtroPrioridad) return false;
      if (!q) return true;
      return (i.punto_de_interes || '').toLowerCase().includes(q) ||
        (i.cliente_nombre || '').toLowerCase().includes(q) ||
        (i.ruta_nombre || '').toLowerCase().includes(q) ||
        (i.departamento || '').toLowerCase().includes(q);
    });
  }

  clearFilters(): void {
    this.filtroRuta = null; this.filtroCliente = null; this.filtroTipo = null; this.filtroPrioridad = null; this.search = '';
  }

  scoreColor(score: number): string {
    if (score >= 1) return 'text-rose-500 dark:text-rose-400';
    if (score >= 0.5) return 'text-amber-500 dark:text-amber-400';
    return 'text-slate-500 dark:text-slate-400';
  }

  tipoLabel(tipo: string): string {
    return tipo === 'fotos_rechazadas' ? 'Fotos rechazadas' : 'Nunca visitado';
  }

  prioridadBadgeClass(prioridad: string | null): string {
    if (prioridad === 'Alta') return 'bg-rose-100 dark:bg-rose-900/30 text-rose-600 dark:text-rose-400';
    if (prioridad === 'Media') return 'bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400';
    return 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400';
  }

  tipoBadgeClass(tipo: string): string {
    return tipo === 'fotos_rechazadas'
      ? 'bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400'
      : 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400';
  }
}
