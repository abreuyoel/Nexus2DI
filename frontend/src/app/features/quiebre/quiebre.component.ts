import { Component, OnInit, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';
import { SearchableSelectComponent, SelectOption } from '../client-visits/searchable-select.component';

@Component({
  selector: 'app-quiebre',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatTooltipModule,
    SearchableSelectComponent,
  ],
  templateUrl: './quiebre.component.html',
})
export class QuiebreComponent implements OnInit {
  loading = signal(true);
  recalculandoAlertas = signal(false);
  recalculandoBase = signal(false);
  items = signal<any[]>([]);
  totalAlertas = signal(0);
  totalUrgentes = signal(0);

  lineaBaseCalculada = signal(false);
  lineaBaseFecha = signal<string | null>(null);
  lineaBaseGrupos = signal(0);

  filtroRiesgo = '';
  filtroUrgente = false;
  filtroCliente = '';
  search = '';

  constructor(private api: ApiService, private snack: MatSnackBar, public auth: AuthService) {}

  ngOnInit(): void {
    this.load();
    this.loadLineaBaseInfo();
  }

  autoRecalculated = false;

  load(): void {
    this.loading.set(true);
    this.api.getQuiebreAlertas().subscribe({
      next: (res) => {
        const list = res?.items || [];
        this.items.set(list);
        this.totalAlertas.set(res?.total || 0);
        this.totalUrgentes.set(res?.urgentes || 0);

        if (list.length === 0 && !this.autoRecalculated) {
          this.autoRecalculated = true;
          this.recalculandoAlertas.set(true);
          this.api.recalcularQuiebreAlertas(true).subscribe({
            next: () => {
              this.recalculandoAlertas.set(false);
              this.api.getQuiebreAlertas().subscribe({
                next: (res2) => {
                  this.loading.set(false);
                  this.items.set(res2?.items || []);
                  this.totalAlertas.set(res2?.total || 0);
                  this.totalUrgentes.set(res2?.urgentes || 0);
                },
                error: () => this.loading.set(false),
              });
            },
            error: () => {
              this.recalculandoAlertas.set(false);
              this.loading.set(false);
            }
          });
        } else {
          this.loading.set(false);
        }
      },
      error: () => { this.loading.set(false); this.items.set([]); this.snack.open('Error al cargar las alertas de quiebre', 'OK', { duration: 3000 }); },
    });
  }

  loadLineaBaseInfo(): void {
    this.api.getQuiebreLineaBaseInfo().subscribe({
      next: (res) => {
        this.lineaBaseCalculada.set(!!res?.calculada);
        this.lineaBaseFecha.set(res?.fecha_calculo || null);
        this.lineaBaseGrupos.set(res?.grupos || 0);
      },
      error: () => {},
    });
  }

  recalcularAlertas(): void {
    this.recalculandoAlertas.set(true);
    this.api.recalcularQuiebreAlertas().subscribe({
      next: () => {
        this.snack.open('Recalculando alertas en background, actualizando en unos segundos...', 'OK', { duration: 4000 });
        setTimeout(() => { this.recalculandoAlertas.set(false); this.load(); }, 15000);
      },
      error: () => { this.recalculandoAlertas.set(false); this.snack.open('Error al recalcular alertas', 'OK', { duration: 3000 }); },
    });
  }

  recalcularLineaBase(): void {
    this.recalculandoBase.set(true);
    this.api.recalcularQuiebreLineaBase().subscribe({
      next: () => {
        this.snack.open('Recalculando línea base en background (puede tardar un poco más)...', 'OK', { duration: 4000 });
        setTimeout(() => { this.recalculandoBase.set(false); this.loadLineaBaseInfo(); }, 20000);
      },
      error: () => { this.recalculandoBase.set(false); this.snack.open('Error al recalcular la línea base', 'OK', { duration: 3000 }); },
    });
  }

  clientesOpts = computed<SelectOption[]>(() =>
    Array.from(new Set(this.items().map((i) => i.cliente).filter(Boolean))).sort().map(c => ({ value: c, label: c }))
  );
  riesgoOpts: SelectOption[] = [
    { value: 'Riesgo ALTO', label: 'Riesgo ALTO' },
    { value: 'Riesgo MEDIO', label: 'Riesgo MEDIO' },
  ];

  totalRiesgoAlto = computed(() => this.items().filter((i) => i.riesgo === 'Riesgo ALTO').length);
  totalRiesgoMedio = computed(() => this.items().filter((i) => i.riesgo === 'Riesgo MEDIO').length);

  get filteredItems(): any[] {
    const q = this.search.trim().toLowerCase();
    return this.items().filter((i) => {
      if (this.filtroRiesgo && i.riesgo !== this.filtroRiesgo) return false;
      if (this.filtroUrgente && !i.urgente) return false;
      if (this.filtroCliente && i.cliente !== this.filtroCliente) return false;
      if (!q) return true;
      return (i.punto_de_interes || i.identificador_pdv || '').toLowerCase().includes(q) ||
        (i.producto || '').toLowerCase().includes(q) ||
        (i.cliente || '').toLowerCase().includes(q);
    });
  }

  quiebrePage = signal(0);
  pageSize = 20;

  paginatedItems = computed(() => {
    const list = this.filteredItems;
    const start = this.quiebrePage() * this.pageSize;
    return list.slice(start, start + this.pageSize);
  });

  totalQuiebrePages = computed(() => Math.ceil(this.filteredItems.length / this.pageSize) || 1);

  goQuiebrePage(page: number): void {
    if (page >= 0 && page < this.totalQuiebrePages()) {
      this.quiebrePage.set(page);
    }
  }

  clearFilters(): void {
    this.filtroRiesgo = '';
    this.filtroUrgente = false;
    this.filtroCliente = '';
    this.search = '';
    this.quiebrePage.set(0);
  }

  riesgoBadgeClass(riesgo: string): string {
    if (riesgo === 'Riesgo ALTO') return 'bg-rose-100 dark:bg-rose-900/30 text-rose-600 dark:text-rose-400';
    if (riesgo === 'Riesgo MEDIO') return 'bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400';
    return 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400';
  }

  tendenciaClass(tendencia: number | null): string {
    if (tendencia == null) return 'text-slate-400';
    return tendencia < 0 ? 'text-rose-500 dark:text-rose-400' : 'text-emerald-500 dark:text-emerald-400';
  }

  diasClass(dias: number | null): string {
    if (dias == null) return 'text-slate-400';
    if (dias <= 1) return 'text-rose-500 dark:text-rose-400';
    if (dias <= 3) return 'text-amber-500 dark:text-amber-400';
    return 'text-slate-500 dark:text-slate-400';
  }
}
