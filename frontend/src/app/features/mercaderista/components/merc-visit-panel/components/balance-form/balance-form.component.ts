import { Component, Input, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { ApiService } from '../../../../../../core/services/api.service';

interface ProductBalance {
  id: number;
  sku: string;
  fabricante: string;
  categoria: string;
  inv_inicial: number;
  inv_final: number;
  inv_deposito: number;
  caras: number;
  precio_bs: number;
  precio_ds: number;
  fifo: Date | null;
}

@Component({
  selector: 'app-balance-form',
  standalone: true,
  imports: [
    CommonModule, FormsModule, MatIconModule, MatButtonModule, 
    MatProgressSpinnerModule, MatSnackBarModule, MatDatepickerModule, 
    MatNativeDateModule, MatFormFieldModule, MatInputModule
  ],
  template: `
    <div class="space-y-6">
      
      <!-- Product Search -->
      <div class="relative bg-white dark:bg-slate-900 p-4 rounded-3xl border border-slate-100 dark:border-white/5 shadow-sm">
        <div class="flex items-center justify-between mb-4 px-2">
          <h4 class="text-xs font-black text-slate-400 uppercase tracking-widest">Agregar Producto</h4>
          <span class="text-[10px] font-bold text-primary-500">{{ products().length }} en catálogo</span>
        </div>
        
        <div class="relative mb-4">
          <mat-icon class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">search</mat-icon>
          <input type="text" [(ngModel)]="searchQuery" (ngModelChange)="filterProducts()"
                 placeholder="Buscar por nombre o SKU..." 
                 class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-white/5 rounded-2xl pl-10 pr-4 py-3 text-sm font-bold outline-none focus:ring-2 focus:ring-primary-500 transition-all">
        </div>

        @if (searchQuery && filteredProducts().length > 0) {
          <div class="absolute z-10 left-4 right-4 top-[100%] mt-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-white/10 rounded-2xl shadow-2xl max-h-[300px] overflow-y-auto">
            @for (p of filteredProducts(); track p.id) {
              <div (click)="addProduct(p)" class="p-3 hover:bg-slate-50 dark:hover:bg-white/5 cursor-pointer flex flex-col border-b border-slate-50 dark:border-white/5 last:border-0">
                <span class="text-xs font-bold text-slate-800 dark:text-white">{{ p.sku }}</span>
                <span class="text-[9px] text-slate-400 uppercase tracking-widest">{{ p.fabricante }} | {{ p.categoria }}</span>
              </div>
            }
          </div>
        }
      </div>

      <!-- Added Products List -->
      <div class="space-y-4">
        <h4 class="text-xs font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest px-2">Data Cargada ({{ addedProducts().length }})</h4>
        
        @if (addedProducts().length === 0) {
          <div class="py-12 bg-slate-50 dark:bg-slate-900/50 rounded-[2rem] border border-dashed border-slate-200 dark:border-white/5 flex flex-col items-center gap-4 opacity-40 grayscale">
            <mat-icon class="!text-5xl">inventory_2</mat-icon>
            <p class="text-xs font-bold italic">Busca y agrega productos de este cliente</p>
          </div>
        } @else {
          @for (p of addedProducts(); track p.id) {
            <div class="bg-white dark:bg-slate-900 rounded-[2rem] border border-slate-100 dark:border-white/5 p-6 shadow-sm animate-in slide-in-from-right-4 duration-300 relative overflow-hidden">
              
              <div class="flex items-start justify-between mb-4">
                <div class="flex flex-col min-w-0">
                  <span class="text-[9px] font-black text-primary-500 uppercase tracking-widest mb-0.5">{{ p.categoria }}</span>
                  <h5 class="font-bold text-slate-800 dark:text-white text-sm tracking-tight truncate">{{ p.sku }}</h5>
                </div>
                <button (click)="removeProduct(p.id)" class="w-8 h-8 rounded-lg bg-rose-500/10 text-rose-500 flex items-center justify-center">
                  <mat-icon class="!text-sm">delete</mat-icon>
                </button>
              </div>

              <div class="grid grid-cols-2 gap-4 mb-4">
                <div class="space-y-1">
                  <label class="text-[9px] font-black text-slate-400 uppercase tracking-widest px-1">Inv. Inicial</label>
                  <input type="number" [(ngModel)]="p.inv_inicial" class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-white/5 rounded-xl px-3 py-2 text-sm font-black outline-none">
                </div>
                <div class="space-y-1">
                  <label class="text-[9px] font-black text-slate-400 uppercase tracking-widest px-1">Inv. Final</label>
                  <input type="number" [(ngModel)]="p.inv_final" class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-white/5 rounded-xl px-3 py-2 text-sm font-black outline-none">
                </div>
                <div class="space-y-1">
                  <label class="text-[9px] font-black text-slate-400 uppercase tracking-widest px-1">Caras</label>
                  <input type="number" [(ngModel)]="p.caras" class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-white/5 rounded-xl px-3 py-2 text-sm font-black outline-none">
                </div>
                <div class="space-y-1">
                  <label class="text-[9px] font-black text-slate-400 uppercase tracking-widest px-1">Inv. Deposito</label>
                  <input type="number" [(ngModel)]="p.inv_deposito" class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-white/5 rounded-xl px-3 py-2 text-sm font-black outline-none">
                </div>
              </div>

              <!-- FIFO Datepicker Field -->
              <div class="space-y-1 mb-4">
                <label class="text-[9px] font-black text-slate-400 uppercase tracking-widest px-1">FIFO (Fecha de Vencimiento)</label>
                <div class="relative merc-datepicker-container">
                  <input matInput [matDatepicker]="picker" [(ngModel)]="p.fifo"
                         placeholder="Seleccionar fecha"
                         class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-white/5 rounded-xl px-3 py-2.5 text-sm font-bold outline-none cursor-pointer"
                         (click)="picker.open()">
                  <mat-datepicker-toggle matSuffix [for]="picker" class="absolute right-1 top-1/2 -translate-y-1/2 scale-75"></mat-datepicker-toggle>
                  <mat-datepicker #picker></mat-datepicker>
                </div>
              </div>

              <div class="grid grid-cols-2 gap-4">
                <div class="space-y-1">
                  <label class="text-[9px] font-black text-slate-400 uppercase tracking-widest px-1">Precio BS</label>
                  <div class="relative">
                    <span class="absolute left-3 top-1/2 -translate-y-1/2 text-[10px] font-black text-slate-400">Bs</span>
                    <input type="number" [(ngModel)]="p.precio_bs" class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-white/5 rounded-xl pl-8 pr-3 py-2 text-sm font-black outline-none">
                  </div>
                </div>
                <div class="space-y-1">
                  <label class="text-[9px] font-black text-slate-400 uppercase tracking-widest px-1">Precio USD</label>
                  <div class="relative">
                    <span class="absolute left-3 top-1/2 -translate-y-1/2 text-[10px] font-black text-slate-400">$</span>
                    <input type="number" [(ngModel)]="p.precio_ds" class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-white/5 rounded-xl pl-8 pr-3 py-2 text-sm font-black outline-none">
                  </div>
                </div>
              </div>
            </div>
          }
        }
      </div>

      <!-- Submit Button -->
      <div class="pt-6 pb-12">
        <button (click)="saveBalances()" [disabled]="addedProducts().length === 0 || saving()"
                class="w-full py-4 bg-primary-600 text-white rounded-[2rem] font-black uppercase tracking-widest text-sm shadow-xl shadow-primary-600/20 active:scale-95 transition-all flex items-center justify-center gap-2">
          @if (saving()) { <mat-spinner diameter="18"></mat-spinner> }
          @else { <mat-icon>cloud_upload</mat-icon> }
          Guardar Data de Visita
        </button>
      </div>

    </div>
  `,
  styles: [`
    :host { display: block; }
    .merc-datepicker-container ::ng-deep {
      .mat-mdc-form-field-subscript-wrapper { display: none; }
      .mat-mdc-text-field-wrapper { padding: 0; background: transparent !important; }
      .mat-mdc-form-field-flex { padding: 0 !important; }
      .mdc-line-ripple { display: none; }
    }
  `]
})
export class BalanceFormComponent implements OnInit {
  @Input() visitaId!: number;
  @Input() idCliente!: number;

  private api = inject(ApiService);
  private snack = inject(MatSnackBar);

  searchQuery = '';
  products = signal<any[]>([]);
  filteredProducts = signal<any[]>([]);
  addedProducts = signal<ProductBalance[]>([]);
  saving = signal(false);

  ngOnInit() {
    this.api.getMercProductosCliente(this.idCliente).subscribe(res => {
      this.products.set(res);
    });
  }

  filterProducts() {
    if (!this.searchQuery) {
      this.filteredProducts.set([]);
      return;
    }
    const q = this.searchQuery.toLowerCase();
    this.filteredProducts.set(
      this.products().filter(p => p.sku.toLowerCase().includes(q) || p.fabricante.toLowerCase().includes(q))
    );
  }

  addProduct(p: any) {
    if (this.addedProducts().some(x => x.id === p.id)) {
      this.snack.open('Producto ya agregado', 'OK', { duration: 2000 });
      this.searchQuery = '';
      this.filteredProducts.set([]);
      return;
    }

    const balance: ProductBalance = {
      id: p.id,
      sku: p.sku,
      fabricante: p.fabricante,
      categoria: p.categoria,
      inv_inicial: 0,
      inv_final: 0,
      inv_deposito: 0,
      caras: 0,
      precio_bs: 0,
      precio_ds: 0,
      fifo: null
    };

    this.addedProducts.update(list => [...list, balance]);
    this.searchQuery = '';
    this.filteredProducts.set([]);
  }

  removeProduct(id: number) {
    this.addedProducts.update(list => list.filter(x => x.id !== id));
  }

  saveBalances() {
    this.saving.set(true);
    const payload = {
      visita_id: this.visitaId,
      id_cliente: this.idCliente,
      productos: this.addedProducts().map(p => ({
        ...p,
        // Convert Date object to string if necessary (FastAPI handles ISO strings usually)
        fifo: p.fifo ? p.fifo.toISOString().split('T')[0] : null
      }))
    };

    this.api.guardarMercBalances(payload).subscribe({
      next: () => {
        this.saving.set(false);
        this.snack.open('Data guardada correctamente', 'OK', { duration: 3000 });
        this.addedProducts.set([]);
      },
      error: () => {
        this.saving.set(false);
        this.snack.open('Error al guardar balances', 'OK', { duration: 3000 });
      }
    });
  }
}
