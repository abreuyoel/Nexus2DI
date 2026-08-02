import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';
import { ClientCategoriesDialogComponent } from '../users/client-categories-dialog.component';
import { HasPermDirective } from '../../core/directives/has-perm.directive';

@Component({
  selector: 'app-client-categories',
  standalone: true,
  imports: [
    CommonModule, MatCardModule, MatIconModule, MatButtonModule,
    MatDialogModule, MatProgressSpinnerModule, MatTooltipModule, MatSnackBarModule, FormsModule, HasPermDirective
  ],
  template: `
    <div class="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div class="relative rounded-3xl overflow-hidden p-8 bg-gradient-to-r from-indigo-700 via-indigo-600 to-violet-600 shadow-lg shadow-indigo-500/20">
        <div class="absolute -right-10 -top-10 w-48 h-48 rounded-full bg-white/10 blur-2xl"></div>
        <div class="relative z-10">
          <div class="flex items-center gap-3 mb-2">
            <div class="w-11 h-11 rounded-2xl bg-white/20 backdrop-blur-sm flex items-center justify-center"><mat-icon class="text-white">category</mat-icon></div>
            <span class="text-[11px] font-black text-white/80 uppercase tracking-[0.2em]">Administración</span>
          </div>
          <h1 class="text-3xl md:text-4xl font-black text-white tracking-tight leading-tight">Categorías de Clientes</h1>
          <p class="text-indigo-100 mt-1 text-sm font-medium">Asignación de categorías de productos por cada cliente en el sistema.</p>
        </div>
      </div>

      <div class="bg-white dark:bg-slate-900 rounded-2xl shadow-sm border border-slate-200 dark:border-white/5 p-6 mb-8">
        <div class="flex flex-wrap items-center justify-between gap-3 mb-6">
          <div class="flex flex-wrap items-center gap-3 flex-1">
            <div class="relative w-full md:w-72">
              <mat-icon class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 !text-lg">search</mat-icon>
              <input [(ngModel)]="searchTerm" placeholder="Buscar cliente por nombre o RIF..." class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-white/10 focus:border-indigo-500 text-slate-800 dark:text-white placeholder-slate-400 rounded-xl pl-10 pr-3 py-2.5 text-sm font-semibold outline-none transition-colors">
            </div>
            <div class="relative min-w-56">
              <button type="button" (click)="catDropdownOpen.set(!catDropdownOpen())"
                class="w-full flex items-center justify-between gap-1 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-white/10 text-slate-800 dark:text-white rounded-xl px-3 py-2.5 text-sm font-semibold outline-none focus:border-indigo-500">
                <span class="truncate">{{ filterCategoryName() || 'Filtrar por categoría: todas' }}</span>
                <mat-icon class="!text-base shrink-0">expand_more</mat-icon>
              </button>
              @if (catDropdownOpen()) {
                <div class="fixed inset-0 z-10" (click)="catDropdownOpen.set(false)"></div>
                <div class="absolute z-20 mt-1 w-72 max-h-80 overflow-y-auto bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-xl shadow-lg p-2 space-y-0.5" (click)="$event.stopPropagation()">
                  <input [(ngModel)]="catSearchTerm" placeholder="Buscar categoría..." class="w-full mb-1 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-white/10 text-slate-800 dark:text-white rounded-lg px-2.5 py-1.5 text-sm outline-none">
                  <button type="button" (click)="onFilterCategoryChange(null); catDropdownOpen.set(false)" class="w-full text-left px-2 py-1.5 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 text-sm font-semibold text-slate-500">Todas</button>
                  @for (cat of catOptsFiltered(); track cat.id_categoria) {
                    <button type="button" (click)="onFilterCategoryChange(cat.id_categoria); catDropdownOpen.set(false)"
                      class="w-full text-left px-2 py-1.5 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 text-sm text-slate-700 dark:text-slate-200 truncate"
                      [class.font-bold]="filterCategoryId() === cat.id_categoria">{{ cat.nombre }}</button>
                  } @empty {
                    <p class="text-xs text-slate-400 px-2 py-1">Sin categorías para esta búsqueda.</p>
                  }
                </div>
              }
            </div>
            @if (filterCategoryId()) {
              <span class="text-xs font-bold text-indigo-600 dark:text-indigo-400">{{ filteredClients().length }} cliente(s) con esta categoría</span>
            }
          </div>
          <button *hasPerm="'client-categories'; action:'write'" (click)="toggleBulkMode()"
            [ngClass]="bulkMode() ? 'bg-slate-200 dark:bg-white/10 text-slate-700 dark:text-white' : 'bg-indigo-600 hover:bg-indigo-500 text-white'"
            class="flex items-center gap-2 px-4 py-2.5 rounded-xl font-black text-sm transition-all active:scale-95 whitespace-nowrap">
            <mat-icon class="!text-base">{{ bulkMode() ? 'close' : 'playlist_add_check' }}</mat-icon>
            {{ bulkMode() ? 'Cancelar' : 'Asignación Masiva' }}
          </button>
        </div>

        @if (bulkMode()) {
          <div class="mb-6 p-4 rounded-2xl bg-indigo-50 dark:bg-indigo-950/30 border border-indigo-200 dark:border-indigo-900 flex flex-wrap items-center gap-3">
            <div class="relative min-w-56">
              <button type="button" (click)="bulkCatDropdownOpen.set(!bulkCatDropdownOpen())"
                class="w-full flex items-center justify-between gap-1 bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 text-slate-800 dark:text-white rounded-xl px-3 py-2.5 text-sm font-semibold outline-none focus:border-indigo-500">
                <span class="truncate">{{ bulkCategoryName() || 'Elegí la categoría a asignar…' }}</span>
                <mat-icon class="!text-base shrink-0">expand_more</mat-icon>
              </button>
              @if (bulkCatDropdownOpen()) {
                <div class="fixed inset-0 z-10" (click)="bulkCatDropdownOpen.set(false)"></div>
                <div class="absolute z-20 mt-1 w-72 max-h-80 overflow-y-auto bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-xl shadow-lg p-2 space-y-0.5" (click)="$event.stopPropagation()">
                  <input [(ngModel)]="bulkCatSearchTerm" placeholder="Buscar categoría..." class="w-full mb-1 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-white/10 text-slate-800 dark:text-white rounded-lg px-2.5 py-1.5 text-sm outline-none">
                  @for (cat of bulkCatOptsFiltered(); track cat.id_categoria) {
                    <button type="button" (click)="bulkCategoryId = cat.id_categoria; bulkCatDropdownOpen.set(false)"
                      class="w-full text-left px-2 py-1.5 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 text-sm text-slate-700 dark:text-slate-200 truncate"
                      [class.font-bold]="bulkCategoryId === cat.id_categoria">{{ cat.nombre }}</button>
                  } @empty {
                    <p class="text-xs text-slate-400 px-2 py-1">Sin categorías para esta búsqueda.</p>
                  }
                </div>
              }
            </div>
            <span class="text-sm font-bold text-indigo-700 dark:text-indigo-300">{{ bulkSelected().size }} cliente(s) seleccionados</span>
            <button (click)="bulkAssign()" [disabled]="!bulkCategoryId || bulkSelected().size === 0 || bulkSaving()"
              class="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-black rounded-xl text-sm transition-all active:scale-95">
              @if (bulkSaving()) { <mat-spinner diameter="16"></mat-spinner> } @else { <mat-icon class="!text-base">done_all</mat-icon> }
              Asignar a seleccionados
            </button>
          </div>
        }

        @if (loading()) {
          <div class="flex justify-center py-12"><mat-spinner diameter="40"></mat-spinner></div>
        } @else {
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            @for (c of filteredClients(); track c.id) {
              <mat-card class="!shadow-sm !rounded-2xl border border-slate-100 dark:border-white/5 dark:!bg-slate-800 group hover:border-indigo-500 transition-colors" [class.!border-indigo-500]="bulkMode() && bulkSelected().has(c.id)">
                <mat-card-content class="!p-5 flex flex-col h-full justify-between">
                  <div>
                    <div class="flex items-start justify-between mb-2">
                      <div>
                        <h3 class="font-bold text-lg text-slate-800 dark:text-white leading-tight mb-1">{{ c.nombre || c.cliente }}</h3>
                        <p class="text-xs text-slate-500 font-mono">{{ c.rif || 'Sin RIF' }}</p>
                      </div>
                      @if (bulkMode()) {
                        <input type="checkbox" [checked]="bulkSelected().has(c.id)" (change)="toggleBulkClient(c.id)" class="w-5 h-5 rounded accent-indigo-600 shrink-0">
                      } @else {
                        <div class="w-10 h-10 rounded-xl bg-indigo-50 dark:bg-indigo-900/30 flex items-center justify-center shrink-0">
                          <mat-icon class="text-indigo-600 dark:text-indigo-400 !text-xl">storefront</mat-icon>
                        </div>
                      }
                    </div>
                  </div>
                  <div class="mt-4 pt-4 border-t border-slate-100 dark:border-white/5">
                    @if (bulkMode()) {
                      <button (click)="toggleBulkClient(c.id)" class="!rounded-xl w-full py-2 text-sm font-bold border transition-colors"
                        [ngClass]="bulkSelected().has(c.id) ? 'bg-indigo-600 border-indigo-600 text-white' : 'border-slate-200 dark:border-white/10 text-slate-500 hover:border-indigo-400'">
                        {{ bulkSelected().has(c.id) ? 'Seleccionado' : 'Seleccionar' }}
                      </button>
                    } @else {
                      <button mat-flat-button color="primary" class="!rounded-xl !bg-indigo-600 hover:!bg-indigo-500 w-full" *hasPerm="'client-categories'; action:'write'" (click)="manageCategories(c)">
                        <mat-icon class="mr-2">category</mat-icon> Gestionar Categorías
                      </button>
                    }
                  </div>
                </mat-card-content>
              </mat-card>
            }
            @if (filteredClients().length === 0) {
              <div class="col-span-full py-12 text-center text-slate-400">
                <mat-icon class="!text-5xl opacity-30 mb-2">search_off</mat-icon>
                <p class="font-bold text-sm">No se encontraron clientes</p>
              </div>
            }
          </div>
        }
      </div>
    </div>
  `
})
export class ClientCategoriesComponent implements OnInit {
  clients = signal<any[]>([]);
  loading = signal(true);
  searchTerm = '';

  allCategories = signal<{ id_categoria: number; nombre: string }[]>([]);
  filterCategoryId = signal<number | null>(null);
  private categoryClientIds = signal<Set<number> | null>(null);

  // Dropdowns custom (no <select> nativo): con 100+ categorías el <select>
  // del navegador se corta contra el borde de la ventana y no deja ver/
  // scrollear el resto de las opciones -- este panel sí tiene su propio
  // scroll garantizado (max-h + overflow-y-auto).
  catDropdownOpen = signal(false);
  catSearchTerm = '';
  bulkCatDropdownOpen = signal(false);
  bulkCatSearchTerm = '';

  bulkMode = signal(false);
  bulkCategoryId: number | null = null;
  bulkSelected = signal<Set<number>>(new Set());
  bulkSaving = signal(false);

  constructor(private api: ApiService, private dialog: MatDialog, private snack: MatSnackBar) {}

  ngOnInit() {
    this.api.getClients().subscribe(data => {
      this.clients.set(data);
      this.loading.set(false);
    });
    this.api.getCatalogosCategorias().subscribe({ next: d => this.allCategories.set(d), error: () => {} });
  }

  filterCategoryName(): string {
    return this.allCategories().find(c => c.id_categoria === this.filterCategoryId())?.nombre || '';
  }
  bulkCategoryName(): string {
    return this.allCategories().find(c => c.id_categoria === this.bulkCategoryId)?.nombre || '';
  }
  catOptsFiltered() {
    const q = this.catSearchTerm.trim().toLowerCase();
    return !q ? this.allCategories() : this.allCategories().filter(c => c.nombre.toLowerCase().includes(q));
  }
  bulkCatOptsFiltered() {
    const q = this.bulkCatSearchTerm.trim().toLowerCase();
    return !q ? this.allCategories() : this.allCategories().filter(c => c.nombre.toLowerCase().includes(q));
  }

  onFilterCategoryChange(id: number | null): void {
    this.filterCategoryId.set(id);
    if (!id) { this.categoryClientIds.set(null); return; }
    this.api.getClientsByCategory(id).subscribe({
      next: (ids) => this.categoryClientIds.set(new Set(ids)),
      error: () => { this.categoryClientIds.set(new Set()); this.snack.open('Error al cargar clientes de esta categoría', 'OK', { duration: 3000 }); },
    });
  }

  filteredClients() {
    const term = this.searchTerm.toLowerCase().trim();
    const catIds = this.categoryClientIds();
    return this.clients().filter(c => {
      if (catIds && !catIds.has(c.id)) return false;
      if (!term) return true;
      return (c.nombre && c.nombre.toLowerCase().includes(term)) ||
        (c.cliente && c.cliente.toLowerCase().includes(term)) ||
        (c.rif && c.rif.toLowerCase().includes(term));
    });
  }

  manageCategories(c: any) {
    this.dialog.open(ClientCategoriesDialogComponent, {
      width: '760px',
      panelClass: 'premium-dialog-panel',
      data: { cliente: c }
    });
  }

  // ── Asignación masiva ──
  toggleBulkMode(): void {
    this.bulkMode.update(v => !v);
    this.bulkSelected.set(new Set());
    this.bulkCategoryId = null;
  }
  toggleBulkClient(id: number): void {
    this.bulkSelected.update(set => {
      const next = new Set(set);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }
  bulkAssign(): void {
    if (!this.bulkCategoryId || this.bulkSelected().size === 0) return;
    this.bulkSaving.set(true);
    this.api.bulkAssignCategory(this.bulkCategoryId, Array.from(this.bulkSelected())).subscribe({
      next: (res) => {
        this.bulkSaving.set(false);
        this.snack.open(`Categoría asignada a ${res.asignados} cliente(s)${res.ya_tenian ? ` (${res.ya_tenian} ya la tenían)` : ''}`, 'OK', { duration: 4000 });
        this.bulkSelected.set(new Set());
        if (this.filterCategoryId() === this.bulkCategoryId) this.onFilterCategoryChange(this.bulkCategoryId);
      },
      error: () => { this.bulkSaving.set(false); this.snack.open('Error al asignar la categoría', 'OK', { duration: 3000 }); },
    });
  }
}
