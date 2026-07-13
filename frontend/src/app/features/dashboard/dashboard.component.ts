import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonModule } from '@angular/material/button';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatProgressSpinnerModule, MatButtonModule, RouterLink],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss']
})
export class DashboardComponent implements OnInit {
  loading = signal(true);
  summary = signal<any>(null);
  clientSummary = signal<any>(null);
  clientDashboardUrl = signal<SafeHtml | null>(null);
  activeView = signal<'summary' | 'powerbi'>('summary');

  isClientUser = computed(() => {
    const u = this.auth.currentUser();
    if (!u) return false;
    // Check all client-type roles: Cliente, Coord.Exclusivo, Coord.Tradex, Vendedor, AtCliente, Coord.General, Encuestador
    const clientRols = ['client', 'coordinador_exclusivo', 'coordinador_tradex'];
    return u.is_client || clientRols.includes(u.rol);
  });

  today = new Date().toLocaleDateString('es-VE', { 
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' 
  });

  constructor(
    private api: ApiService, 
    public auth: AuthService,
    private sanitizer: DomSanitizer
  ) {}

  ngOnInit(): void {
    if (this.isClientUser()) {
      this.loadClientData();
    } else {
      this.loadSummary();
    }
  }

  private loadSummary(): void {
    this.api.getReportSummary().subscribe({
      next: (data) => { this.summary.set(data); this.loading.set(false); },
      error: () => { this.loading.set(false); },
    });
  }

  private loadClientData(): void {
    // Usar forkJoin para esperar ambas respuestas antes de quitar el spinner
    forkJoin({
      summaryData: this.api.getClientSummary().pipe(
        catchError(() => of({ recent_visits: 0, recent_photos: 0, recent_messages: 0, period: 'Últimos 7 días' }))
      ),
      dashboardData: this.api.getClientDashboard().pipe(
        catchError(() => of({ has_dashboard: false, url_html: null }))
      ),
    }).subscribe({
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
        this.clientSummary.set({ recent_visits: 0, recent_photos: 0, recent_messages: 0, period: 'Últimos 7 días' });
        this.loading.set(false);
      },
    });
  }
}
