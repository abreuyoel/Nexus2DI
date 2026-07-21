import { Component, OnInit, signal, inject, computed, HostListener, OnDestroy, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Subject, debounceTime, distinctUntilChanged } from 'rxjs';
import { ApiService } from '../../core/services/api.service';
import { Foto } from '../../core/models/visita.model';
import { SearchableSelectComponent } from '../../shared/components/searchable-select';
import type { SearchableOption } from '../../shared/components/searchable-select';

@Component({
  selector: 'app-supervisor',
  standalone: true,
  imports: [
    CommonModule, FormsModule, MatCardModule, MatButtonModule, MatIconModule,
    MatProgressSpinnerModule, MatSnackBarModule, SearchableSelectComponent
  ],
  templateUrl: './supervisor.component.html',
  styleUrls: ['./supervisor.component.scss']
})
export class SupervisorComponent implements OnInit, AfterViewInit, OnDestroy {
  private api = inject(ApiService);
  private snack = inject(MatSnackBar);
  private cedulaSubject = new Subject<string>();

  loading = signal(true);
  loadingMore = signal(false);
  photos = signal<Foto[]>([]);

  // ── Paginación ─────────────────────────────────────────────────
  currentPage = signal(1);
  totalPages = signal(1);
  totalItems = signal(0);
  perPage = 20;

  // ── Filtros ────────────────────────────────────────────────────
  fechaDesde = signal('');
  fechaHasta = signal('');
  filtroMercaderista = signal<string | null>(null);
  filtroCedula = signal('');

  // ── Opciones para SearchableSelect ─────────────────────────────
  mercaderistaOptions = signal<SearchableOption<string>[]>([]);

  // ── UX ─────────────────────────────────────────────────────────
  showScrollTop = signal(false);
  showFilters = signal(true);

  private mainElement: HTMLElement | null = null;
  private lastScrollTop = 0;
  private scrollListener?: () => void;

  // ── Computed ───────────────────────────────────────────────────
  hasMorePages = computed(() => this.currentPage() < this.totalPages());

  ngAfterViewInit(): void {
    this.mainElement = document.querySelector('main');

    this.scrollListener = () => {
      const currentScrollTop = this.mainElement ? this.mainElement.scrollTop : window.scrollY;

      this.showScrollTop.set(currentScrollTop > 400);

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

  @HostListener('window:scroll', ['$event'])
  onScroll(_e: Event): void {
    if (this.scrollListener) {
      this.scrollListener();
    }
  }

  scrollToTop(): void {
    const main = document.querySelector('main');
    if (main) main.scrollTo({ top: 0, behavior: 'smooth' });
    else window.scrollTo({ top: 0, behavior: 'smooth' });
    this.showFilters.set(true);
  }

  constructor() {
    this.cedulaSubject.pipe(
      debounceTime(400),
      distinctUntilChanged(),
    ).subscribe(term => {
      this.filtroCedula.set(term);
      this.resetAndLoad();
    });
  }

  ngOnInit(): void {
    this.loadFilterOptions();
    this.resetAndLoad();
  }

  // ── Cargar opciones de filtros (cacheadas con Redis 5 min) ────
  private loadFilterOptions(): void {
    this.api.getRejectedPhotoFilters().subscribe({
      next: (res) => {
        this.mercaderistaOptions.set(res.mercaderistas);
      },
    });
  }

  // ── Cargar primera página ──────────────────────────────────────
  private resetAndLoad(): void {
    this.currentPage.set(1);
    this.photos.set([]);
    this.loadPhotos();
  }

  // ── Cargar fotos (página actual) ───────────────────────────────
  loadPhotos(): void {
    const isInitial = this.currentPage() === 1;
    if (isInitial) this.loading.set(true);
    else this.loadingMore.set(true);

    const filters: Record<string, string> = {};
    if (this.fechaDesde()) filters['fecha_desde'] = this.fechaDesde();
    if (this.fechaHasta()) filters['fecha_hasta'] = this.fechaHasta();
    if (this.filtroMercaderista()) filters['mercaderista'] = this.filtroMercaderista()!;
    if (this.filtroCedula()) filters['cedula'] = this.filtroCedula();

    this.api.getRejectedPhotos(this.currentPage(), this.perPage, filters).subscribe({
      next: (res) => {
        if (this.currentPage() === 1) {
          this.photos.set(res.items);
        } else {
          this.photos.update(prev => [...prev, ...res.items]);
        }
        this.totalPages.set(res.total_pages);
        this.totalItems.set(res.total);
        this.loading.set(false);
        this.loadingMore.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.loadingMore.set(false);
      },
    });
  }

  // ── Cargar más (siguiente página) ──────────────────────────────
  loadMore(): void {
    if (this.loadingMore() || !this.hasMorePages()) return;
    this.currentPage.update(p => p + 1);
    this.loadPhotos();
  }

  // ── Handlers de filtros ────────────────────────────────────────
  onFechaDesde(ev: Event): void {
    this.fechaDesde.set((ev.target as HTMLInputElement).value);
    this.resetAndLoad();
  }
  onFechaHasta(ev: Event): void {
    this.fechaHasta.set((ev.target as HTMLInputElement).value);
    this.resetAndLoad();
  }
  onMercaderistaChange(val: string | null): void {
    this.filtroMercaderista.set(val);
    this.resetAndLoad();
  }
  onCedulaInput(ev: Event): void {
    const val = (ev.target as HTMLInputElement).value;
    this.cedulaSubject.next(val);
  }

  clearFilters(): void {
    this.fechaDesde.set('');
    this.fechaHasta.set('');
    this.filtroMercaderista.set(null);
    this.filtroCedula.set('');
    this.resetAndLoad();
  }

  hasActiveFilters(): boolean {
    return !!(
      this.fechaDesde() || this.fechaHasta() ||
      this.filtroMercaderista() || this.filtroCedula()
    );
  }

  // ── Utility ────────────────────────────────────────────────────
  formatDate(dt: string | undefined | null): string {
    if (!dt) return '—';
    try {
      const d = new Date(dt);
      return d.toLocaleDateString('es-VE', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dt;
    }
  }

  // ── Acción ─────────────────────────────────────────────────────
  approvePhoto(foto: Foto): void {
    this.api.approvePhotos([foto.id]).subscribe({
      next: () => {
        this.photos.update((ps) => ps.filter((p) => p.id !== foto.id));
        this.totalItems.update(t => Math.max(0, t - 1));
        this.snack.open('Foto aprobada', 'OK', { duration: 2000 });
      },
      error: () => {
        this.snack.open('Error al procesar la aprobación', 'OK', { duration: 3000 });
      }
    });
  }
}
