import { Component, Inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogRef, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';
import { ApiService } from '../../core/services/api.service';

@Component({
  selector: 'app-client-categories-dialog',
  standalone: true,
  imports: [
    CommonModule, FormsModule, MatDialogModule, MatButtonModule,
    MatIconModule, MatSelectModule, MatProgressSpinnerModule
  ],
  template: `
    <div class="relative flex flex-col bg-slate-950 text-white rounded-3xl overflow-hidden shadow-[0_0_50px_-12px_rgba(0,0,0,1)] border border-white/5" style="min-height: 500px; max-height: 85vh;">
      <!-- Background glow -->
      <div class="absolute top-0 left-1/2 -translate-x-1/2 w-[400px] h-[150px] bg-indigo-600/30 blur-[70px] pointer-events-none rounded-full"></div>
      
      <!-- Header -->
      <div class="relative z-10 flex items-center justify-between p-6 pb-4 border-b border-white/10 shrink-0">
        <div class="flex items-center gap-4">
          <div class="w-12 h-12 rounded-2xl bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center shadow-lg">
            <mat-icon class="text-indigo-400 !text-2xl">category</mat-icon>
          </div>
          <div>
            <h2 class="text-xl font-black tracking-tight text-white m-0 leading-tight">Categorías Cliente</h2>
            <p class="text-sm text-indigo-200/70 font-medium mt-0.5">{{ data.cliente.nombre || data.cliente.cliente }}</p>
          </div>
        </div>
        <button mat-icon-button mat-dialog-close class="!w-10 !h-10 rounded-xl bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white transition-all flex items-center justify-center shrink-0">
          <mat-icon>close</mat-icon>
        </button>
      </div>

      <div class="relative z-10 p-6 flex flex-col flex-1 min-h-0">
        @if (loading()) {
          <div class="flex-1 flex items-center justify-center py-8">
            <mat-spinner diameter="40" class="text-indigo-500"></mat-spinner>
          </div>
        } @else {
          <div class="flex flex-col md:flex-row gap-6 flex-1 min-h-0">
            <!-- Left Column: Available Categories (Multi-select) -->
            <div class="flex-1 flex flex-col min-h-0 bg-slate-900/60 rounded-2xl border border-white/5 p-4 shadow-inner">
              <label class="block text-[11px] font-black text-indigo-400/80 uppercase tracking-widest mb-3 shrink-0">Disponibles</label>
              
              <!-- Search Bar -->
              <div class="relative mb-3 shrink-0">
                <mat-icon class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 !text-[18px]">search</mat-icon>
                <input [(ngModel)]="searchAvailable" placeholder="Buscar categoría..." 
                       class="w-full bg-slate-950 border border-white/10 focus:border-indigo-500 text-white rounded-xl pl-9 pr-3 py-2 text-sm font-semibold outline-none transition-colors shadow-sm">
                @if (searchAvailable) {
                  <button (click)="searchAvailable = ''" class="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white">
                    <mat-icon class="!text-[16px]">close</mat-icon>
                  </button>
                }
              </div>

              <!-- Available List -->
              <div class="flex-1 overflow-y-auto custom-scrollbar space-y-1 pr-1 mb-3">
                @if (filteredAvailable().length === 0) {
                  <div class="py-6 text-center text-slate-500">
                    <p class="text-xs font-semibold">No se encontraron categorías</p>
                  </div>
                }
                @for (cat of filteredAvailable(); track cat.id_categoria) {
                  <label class="flex items-center gap-3 p-2 rounded-xl hover:bg-slate-800/80 cursor-pointer transition-colors border border-transparent hover:border-white/5">
                    <input type="checkbox" [checked]="isSelected(cat.id_categoria)" (change)="toggleSelection(cat.id_categoria)" 
                           class="w-4 h-4 rounded border-slate-700 bg-slate-950 text-indigo-500 focus:ring-indigo-500 focus:ring-offset-slate-900">
                    <span class="text-sm font-bold text-slate-300 select-none">{{ cat.nombre }}</span>
                  </label>
                }
              </div>
              
              <button (click)="addSelectedCategories()" [disabled]="selectedIds.length === 0 || saving()"
                      class="shrink-0 flex items-center justify-center gap-2 w-full py-2.5 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 disabled:opacity-50 disabled:grayscale text-white font-bold rounded-xl transition-all shadow-lg active:scale-95">
                <mat-icon class="!text-[18px]">add_task</mat-icon> Asignar ({{ selectedIds.length }})
              </button>
            </div>

            <!-- Right Column: Assigned Categories -->
            <div class="flex-1 flex flex-col min-h-0 bg-slate-900/40 rounded-2xl border border-white/5 p-4">
              <label class="block text-[11px] font-black text-slate-500 uppercase tracking-widest mb-3 flex items-center justify-between shrink-0">
                <span>Asignadas</span>
                <span class="px-2 py-0.5 rounded-full bg-slate-800 text-slate-300">{{ assignedCategories().length }}</span>
              </label>
              
              <!-- Search Assigned -->
              <div class="relative mb-3 shrink-0">
                <mat-icon class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 !text-[18px]">search</mat-icon>
                <input [(ngModel)]="searchAssigned" placeholder="Filtrar asignadas..." 
                       class="w-full bg-slate-900/50 border border-white/5 focus:border-slate-500 text-white rounded-xl pl-9 pr-3 py-2 text-sm font-semibold outline-none transition-colors">
              </div>

              <div class="flex-1 overflow-y-auto pr-1 custom-scrollbar space-y-2">
                @if (filteredAssigned().length === 0) {
                  <div class="flex flex-col items-center justify-center py-10 px-4 text-center bg-slate-900/30 rounded-xl border border-dashed border-white/5 h-full">
                    <mat-icon class="!text-3xl text-slate-600 mb-2">inventory_2</mat-icon>
                    <p class="text-xs text-slate-500 font-bold">{{ assignedCategories().length === 0 ? 'Sin categorías' : 'Ninguna coincide' }}</p>
                  </div>
                } @else {
                  @for (cat of filteredAssigned(); track cat.id_categoria) {
                    <div class="flex items-center justify-between bg-slate-950/50 hover:bg-slate-800 border border-white/5 rounded-xl p-3 shadow-sm transition-all group">
                      <div class="flex items-center gap-3">
                        <div class="relative flex items-center justify-center w-2 h-2">
                          <div class="absolute inset-0 bg-emerald-500 rounded-full animate-ping opacity-20"></div>
                          <div class="relative w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]"></div>
                        </div>
                        <span class="font-bold text-xs text-slate-300 group-hover:text-white transition-colors">{{ cat.categoria_nombre }}</span>
                      </div>
                      <button (click)="removeCategory(cat.id_categoria)" [disabled]="saving()"
                              class="!w-7 !h-7 rounded-lg bg-slate-900 flex items-center justify-center text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-colors opacity-60 group-hover:opacity-100">
                        <mat-icon class="!text-[16px]">close</mat-icon>
                      </button>
                    </div>
                  }
                }
              </div>
            </div>
          </div>
        }
      </div>
    </div>
  `,
  styles: [`
    .premium-dialog-panel .mdc-dialog__surface {
      background: transparent !important;
      box-shadow: none !important;
      padding: 0 !important;
      border-radius: 1.5rem !important; /* 24px */
    }

    .custom-scrollbar::-webkit-scrollbar { width: 6px; }
    .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
    .custom-scrollbar::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }
    .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #475569; }
  `]
})
export class ClientCategoriesDialogComponent implements OnInit {
  loading = signal(true);
  saving = signal(false);
  
  assignedCategories = signal<any[]>([]);
  allCategories = signal<any[]>([]);
  
  searchAvailable = '';
  searchAssigned = '';
  selectedIds: number[] = [];

  constructor(
    @Inject(MAT_DIALOG_DATA) public data: { cliente: any },
    private dialogRef: MatDialogRef<ClientCategoriesDialogComponent>,
    private api: ApiService,
    private snack: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.loadData();
  }

  loadData() {
    this.loading.set(true);
    this.api.getClientCategories(this.data.cliente.id).subscribe({
      next: (assigned) => {
        this.assignedCategories.set(assigned);
        this.api.getCatalogosCategorias().subscribe({
          next: (all) => {
            this.allCategories.set(all);
            this.loading.set(false);
          },
          error: () => {
            this.snack.open('Error al cargar catálogos de categorías', 'OK', { duration: 3000 });
            this.loading.set(false);
          }
        });
      },
      error: () => {
        this.snack.open('Error al cargar categorías del cliente', 'OK', { duration: 3000 });
        this.loading.set(false);
      }
    });
  }

  availableCategories() {
    const assignedIds = new Set(this.assignedCategories().map(c => c.id_categoria));
    return this.allCategories().filter(c => !assignedIds.has(c.id_categoria));
  }

  filteredAvailable() {
    let list = this.availableCategories();
    const term = this.searchAvailable.toLowerCase().trim();
    if (term) {
      list = list.filter(c => c.nombre.toLowerCase().includes(term));
    }
    return list;
  }

  filteredAssigned() {
    let list = this.assignedCategories();
    const term = this.searchAssigned.toLowerCase().trim();
    if (term) {
      list = list.filter(c => c.categoria_nombre.toLowerCase().includes(term));
    }
    return list;
  }

  isSelected(id: number) {
    return this.selectedIds.includes(id);
  }

  toggleSelection(id: number) {
    if (this.isSelected(id)) {
      this.selectedIds = this.selectedIds.filter(i => i !== id);
    } else {
      this.selectedIds.push(id);
    }
  }

  addSelectedCategories() {
    if (this.selectedIds.length === 0) return;
    this.saving.set(true);
    
    let completed = 0;
    const total = this.selectedIds.length;
    let hasError = false;

    this.selectedIds.forEach(id => {
      this.api.addClientCategory(this.data.cliente.id, id).subscribe({
        next: () => {
          completed++;
          if (completed === total) this.finishBulkAdd(hasError);
        },
        error: () => {
          hasError = true;
          completed++;
          if (completed === total) this.finishBulkAdd(hasError);
        }
      });
    });
  }

  private finishBulkAdd(hasError: boolean) {
    this.saving.set(false);
    this.selectedIds = [];
    if (hasError) {
      this.snack.open('Algunas categorías no se pudieron asignar', 'OK', { duration: 3000 });
    } else {
      this.snack.open('Categorías asignadas correctamente', 'OK', { duration: 2500 });
    }
    this.reloadAssigned();
  }

  removeCategory(categoryId: number) {
    if (!confirm('¿Seguro que deseas remover esta categoría?')) return;
    this.saving.set(true);
    
    this.api.removeClientCategory(this.data.cliente.id, categoryId).subscribe({
      next: () => {
        this.snack.open('Categoría removida', 'OK', { duration: 2000 });
        this.saving.set(false);
        this.reloadAssigned();
      },
      error: (err) => {
        this.snack.open(err.error?.detail || 'Error al remover', 'OK', { duration: 3000 });
        this.saving.set(false);
      }
    });
  }
  
  private reloadAssigned() {
    this.api.getClientCategories(this.data.cliente.id).subscribe({
      next: (assigned) => {
        this.assignedCategories.set(assigned);
      }
    });
  }
}
