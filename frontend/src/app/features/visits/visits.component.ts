import { Component, OnInit, signal, computed, AfterViewInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { Visita, VisitaPaginatedResponse } from '../../core/models/visita.model';

@Component({
  selector: 'app-visits',
  standalone: true,
  imports: [
    CommonModule, MatTableModule, MatButtonModule, MatIconModule,
    MatCardModule, MatChipsModule, MatFormFieldModule, MatSelectModule,
    MatProgressSpinnerModule, MatTooltipModule, FormsModule, RouterLink,
  ],
  templateUrl: './visits.component.html',
  styleUrls: ['./visits.component.scss']
})
export class VisitsComponent implements OnInit, AfterViewInit, OnDestroy {
  loading = signal(true);
  visits = signal<Visita[]>([]);
  filterEstado = '';
  columns = ['id', 'mercaderista_id', 'punto_id', 'fecha', 'estado', 'acciones'];

  // UX & Scroll State
  showFilters = signal(true);
  private mainElement: HTMLElement | null = null;
  private lastScrollTop = 0;
  private scrollListener?: () => void;

  // Paginación
  currentPage = signal(1);
  pageSize = signal(20);
  total = signal(0);
  totalPages = signal(0);
  totalPagesArray = computed(() => Array.from({ length: this.totalPages() }, (_, i) => i + 1));

  constructor(private api: ApiService) { }

  ngOnInit(): void { this.loadVisits(); }

  ngAfterViewInit(): void {
    this.mainElement = document.querySelector('main');

    this.scrollListener = () => {
      const currentScrollTop = this.mainElement ? this.mainElement.scrollTop : window.scrollY;
      const delta = currentScrollTop - this.lastScrollTop;

      if (delta > 5 && currentScrollTop > 60) {
        this.showFilters.set(false);
      } else if (delta < -5) {
        this.showFilters.set(true);
      }

      this.lastScrollTop = Math.max(0, currentScrollTop);
    };

    if (this.mainElement) {
      this.mainElement.addEventListener('scroll', this.scrollListener, { passive: true });
    }
    window.addEventListener('scroll', this.scrollListener, { passive: true });
  }

  ngOnDestroy(): void {
    if (this.scrollListener) {
      if (this.mainElement) {
        this.mainElement.removeEventListener('scroll', this.scrollListener);
      }
      window.removeEventListener('scroll', this.scrollListener);
    }
  }

  loadVisits(): void {
    this.loading.set(true);
    const params: any = { page: this.currentPage(), per_page: this.pageSize() };
    if (this.filterEstado) params.estado = this.filterEstado;
    this.api.getVisits(params).subscribe({
      next: (res: VisitaPaginatedResponse) => {
        this.visits.set(res.items);
        this.total.set(res.total);
        this.totalPages.set(res.total_pages);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      },
    });
  }

  prevPage(): void {
    if (this.currentPage() > 1) {
      this.currentPage.update(p => p - 1);
      this.loadVisits();
    }
  }

  nextPage(): void {
    if (this.currentPage() < this.totalPages()) {
      this.currentPage.update(p => p + 1);
      this.loadVisits();
    }
  }

  goToPage(page: number): void {
    if (page !== this.currentPage() && page >= 1 && page <= this.totalPages()) {
      this.currentPage.set(page);
      this.loadVisits();
    }
  }

  getStatusClasses(estado: string): string {
    const map: Record<string, string> = {
      completada: 'bg-emerald-50 text-emerald-700',
      en_progreso: 'bg-primary-50 text-primary-700',
      pendiente: 'bg-amber-50 text-amber-700',
    };
    return map[estado] ?? 'bg-slate-50 text-slate-700';
  }

  viewPhotos(visit: Visita): void {
    console.log('Ver fotos de visita', visit.id);
  }
}
