import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';
import { ClientCategoriesDialogComponent } from '../users/client-categories-dialog.component';
import { HasPermDirective } from '../../core/directives/has-perm.directive';

@Component({
  selector: 'app-client-categories',
  standalone: true,
  imports: [
    CommonModule, MatCardModule, MatIconModule, MatButtonModule,
    MatDialogModule, MatProgressSpinnerModule, MatTooltipModule, FormsModule, HasPermDirective
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
        <div class="flex items-center justify-between mb-6">
          <div class="relative w-full md:w-72">
            <mat-icon class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 !text-lg">search</mat-icon>
            <input [(ngModel)]="searchTerm" placeholder="Buscar cliente por nombre o RIF..." class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-white/10 focus:border-indigo-500 text-slate-800 dark:text-white placeholder-slate-400 rounded-xl pl-10 pr-3 py-2.5 text-sm font-semibold outline-none transition-colors">
          </div>
        </div>

        @if (loading()) {
          <div class="flex justify-center py-12"><mat-spinner diameter="40"></mat-spinner></div>
        } @else {
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            @for (c of filteredClients(); track c.id) {
              <mat-card class="!shadow-sm !rounded-2xl border border-slate-100 dark:border-white/5 dark:!bg-slate-800 group hover:border-indigo-500 transition-colors">
                <mat-card-content class="!p-5 flex flex-col h-full justify-between">
                  <div>
                    <div class="flex items-start justify-between mb-2">
                      <div>
                        <h3 class="font-bold text-lg text-slate-800 dark:text-white leading-tight mb-1">{{ c.nombre || c.cliente }}</h3>
                        <p class="text-xs text-slate-500 font-mono">{{ c.rif || 'Sin RIF' }}</p>
                      </div>
                      <div class="w-10 h-10 rounded-xl bg-indigo-50 dark:bg-indigo-900/30 flex items-center justify-center shrink-0">
                        <mat-icon class="text-indigo-600 dark:text-indigo-400 !text-xl">storefront</mat-icon>
                      </div>
                    </div>
                  </div>
                  <div class="mt-4 pt-4 border-t border-slate-100 dark:border-white/5">
                    <button mat-flat-button color="primary" class="!rounded-xl !bg-indigo-600 hover:!bg-indigo-500 w-full" *hasPerm="'client-categories'; action:'write'" (click)="manageCategories(c)">
                      <mat-icon class="mr-2">category</mat-icon> Gestionar Categorías
                    </button>
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

  constructor(private api: ApiService, private dialog: MatDialog) {}

  ngOnInit() {
    this.api.getClients().subscribe(data => {
      this.clients.set(data);
      this.loading.set(false);
    });
  }

  filteredClients() {
    const term = this.searchTerm.toLowerCase().trim();
    if (!term) return this.clients();
    return this.clients().filter(c => 
      (c.nombre && c.nombre.toLowerCase().includes(term)) || 
      (c.cliente && c.cliente.toLowerCase().includes(term)) ||
      (c.rif && c.rif.toLowerCase().includes(term))
    );
  }

  manageCategories(c: any) {
    this.dialog.open(ClientCategoriesDialogComponent, {
      width: '760px',
      panelClass: 'premium-dialog-panel',
      data: { cliente: c }
    });
  }
}
