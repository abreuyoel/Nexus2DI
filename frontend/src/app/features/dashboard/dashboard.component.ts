import { Component, OnInit, signal, computed, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterLink, ActivatedRoute } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { forkJoin, of, Subject } from 'rxjs';
import { catchError, takeUntil } from 'rxjs/operators';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatButtonModule,
    MatTooltipModule,
    RouterLink,
  ],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss'],
})
export class DashboardComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();

  loading = signal(true);
  summary = signal<any>(null);
  clientSummary = signal<any>(null);
  clientDashboardUrl = signal<SafeHtml | null>(null);
  activeView = signal<'summary' | 'powerbi'>('summary');

  // ─── Filtros por fecha (formato ISO yyyy-MM-dd) ─────────────────────────────
  fechaInicio: string = this.dateToIso(this.daysAgo(30));
  fechaFin: string = this.dateToIso(new Date());

  // Percent de la barra de fotos aprobadas (calculado en vez de hardcodeado).
  fotosAprobadasPct = computed(() => {
    const f = this.summary()?.fotos;
    const total = f?.total ?? 0;
    const aprobadas = f?.aprobadas ?? 0;
    return total > 0 ? Math.round((aprobadas / total) * 100) : 0;
  });
  fotosPendientesPct = computed(() => {
    const f = this.summary()?.fotos;
    const total = f?.total ?? 0;
    const pendientes = f?.pendientes ?? 0;
    return total > 0 ? Math.round((pendientes / total) * 100) : 0;
  });
  fotosRechazadasPct = computed(() => {
    const f = this.summary()?.fotos;
    const total = f?.total ?? 0;
    const rechazadas = f?.rechazadas ?? 0;
    return total > 0 ? Math.round((rechazadas / total) * 100) : 0;
  });

  isClientUser = computed(() => {
    const u = this.auth.currentUser();
    if (!u) return false;
    // Check all client-type roles: Cliente, Coord.Exclusivo, Coord.Tradex, Vendedor, AtCliente, Coord.General, Encuestador
    const clientRols = ['client', 'coordinador_exclusivo', 'coordinador_tradex'];
    return u.is_client || clientRols.includes(u.rol);
  });

  today = new Date().toLocaleDateString('es-VE', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  constructor(
    private api: ApiService,
    public auth: AuthService,
    private sanitizer: DomSanitizer,
    private route: ActivatedRoute
  ) { }

  ngOnInit(): void {
    // Leer queryParam ?view=powerbi para activar directamente la pestaña Power BI
    this.route.queryParams.subscribe(params => {
      if (params['view'] === 'powerbi') {
        this.activeView.set('powerbi');
      }
    });
    this.refresh();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  /** Recarga los datos según el tipo de usuario y el rango de fechas elegido. */
  refresh(): void {
    this.loading.set(true);
    if (this.isClientUser()) {
      this.loadClientData();
    } else {
      this.loadSummary();
    }
  }

  /** Restablece el rango a los últimos 30 días y recarga. */
  resetFechas(): void {
    this.fechaInicio = this.dateToIso(this.daysAgo(30));
    this.fechaFin = this.dateToIso(new Date());
    this.refresh();
  }

  private loadSummary(): void {
    this.api
      .getReportSummary({ fecha_inicio: this.fechaInicio, fecha_fin: this.fechaFin })
      .pipe(
        takeUntil(this.destroy$),
        catchError(() => of(null))
      )
      .subscribe({
        next: (data) => {
          this.summary.set(data);
          this.loading.set(false);
        },
        error: () => this.loading.set(false),
      });
  }

  private loadClientData(): void {
    // Usar forkJoin para esperar ambas respuestas antes de quitar el spinner.
    // El resumen del cliente ya recibe el rango de fechas elegido.
    forkJoin({
      summaryData: this.api
        .getClientSummary({ fecha_inicio: this.fechaInicio, fecha_fin: this.fechaFin })
        .pipe(
          catchError(() =>
            of({
              recent_visits: 0,
              recent_photos: 0,
              recent_messages: 0,
              period: `${this.fechaInicio} al ${this.fechaFin}`,
            })
          )
        ),
      dashboardData: this.api.getClientDashboard().pipe(
        catchError(() => of({ has_dashboard: false, url_html: null }))
      ),
    })
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: ({ summaryData, dashboardData }) => {
          // Siempre setear el summary (puede tener todos los valores en 0, pero existe)
          this.clientSummary.set(summaryData);

          if (dashboardData?.has_dashboard && dashboardData?.url_html) {
            this.clientDashboardUrl.set(
              this.sanitizer.bypassSecurityTrustHtml(dashboardData.url_html)
            );
          }
          this.loading.set(false);
        },
        error: () => {
          // Aún en error, mostrar el resumen vacío
          this.clientSummary.set({
            recent_visits: 0,
            recent_photos: 0,
            recent_messages: 0,
            period: `${this.fechaInicio} al ${this.fechaFin}`,
          });
          this.loading.set(false);
        },
      });
  }

  // ─── Helpers de fecha ──────────────────────────────────────────────────────
  private dateToIso(d: Date): string {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  private daysAgo(n: number): Date {
    const d = new Date();
    d.setDate(d.getDate() - n);
    return d;
  }
}
