import { Component, OnInit, signal, inject, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { firstValueFrom } from 'rxjs';
import { ApiService } from '../../../../core/services/api.service';
import { MercUiService } from '../../services/merc-ui.service';
import { ConfirmService } from '../../../../shared/components/confirm-dialog/confirm.service';
import { ConfirmDialogComponent } from '../../../../shared/components/confirm-dialog/confirm-dialog.component';
import { SkeletonLoaderComponent } from '../../../../shared/components/skeleton-loader/skeleton-loader.component';

interface PdvActivo {
  punto_id: string;
  punto_nombre: string;
  ruta_id?: number;
  ruta_nombre?: string;
  clientes_listos: string[];
  clientes_pendientes: string[];
  falta_desactivacion: boolean;
  ultima_visita_local_id: number | null;
  ultima_visita_cliente_id: number | null;
  ultima_visita_cliente_nombre: string | null;
}

@Component({
  selector: 'app-merc-pdv-activos',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatButtonModule, MatProgressSpinnerModule, MatSnackBarModule, SkeletonLoaderComponent, ConfirmDialogComponent],
  template: `
    <div class="flex flex-col h-full bg-slate-50 dark:bg-slate-950">
      <div class="flex-grow overflow-y-auto p-4 space-y-4">
        @if (loading()) {
          <app-skeleton-loader [count]="3"></app-skeleton-loader>
        } @else if (pdvs().length === 0) {
          <div class="py-16 text-center opacity-40 space-y-3">
            <mat-icon class="!text-5xl text-slate-400">storefront</mat-icon>
            <p class="text-sm font-bold">No hay puntos de venta activos con trabajo pendiente hoy.</p>
          </div>
        } @else {
          @for (p of pdvs(); track p.punto_id) {
            <div class="bg-white dark:bg-slate-900 border border-slate-100 dark:border-white/5 rounded-3xl p-5 shadow-sm space-y-3">

              <!-- Header -->
              <div class="flex items-start justify-between">
                <div>
                  <h4 class="font-bold text-sm text-slate-800 dark:text-white leading-snug">{{ p.punto_nombre }}</h4>
                  <p class="text-[10px] text-slate-400 dark:text-slate-500 font-bold uppercase tracking-wider mt-0.5">
                    {{ p.ruta_nombre || 'Sin Ruta' }}
                  </p>
                </div>
                @if (p.falta_desactivacion) {
                  <span class="bg-rose-500/10 text-rose-500 border border-rose-500/20 text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full">
                    Falta Desactivar
                  </span>
                }
              </div>

              <!-- Clientes -->
              <div class="space-y-1.5 text-xs">
                <p class="text-slate-600 dark:text-slate-400">
                  <strong class="font-bold text-slate-700 dark:text-slate-200">Listos:</strong>
                  {{ p.clientes_listos.join(', ') || 'Ninguno' }}
                </p>
                <p class="text-slate-600 dark:text-slate-400">
                  <strong class="font-bold text-slate-700 dark:text-slate-200">Pendientes:</strong>
                  {{ p.clientes_pendientes.join(', ') || 'Ninguno' }}
                </p>
              </div>

              <!-- Action Buttons -->
              <div class="flex gap-2 pt-1">
                <button (click)="continuarVisita(p)"
                        class="flex-1 py-2.5 bg-primary-500/10 text-primary-600 border border-primary-500/20 rounded-xl text-[10px] font-black uppercase tracking-widest flex items-center justify-center gap-1.5 hover:bg-primary-500/20 transition-all active:scale-95">
                  <mat-icon class="!text-sm">arrow_forward</mat-icon>
                  Continuar Visita
                </button>
                @if (p.falta_desactivacion) {
                  <button (click)="desactivarPdv(p)" [disabled]="desactivando() === p.punto_id"
                          class="flex-1 py-2.5 bg-rose-500/10 text-rose-600 border border-rose-500/20 rounded-xl text-[10px] font-black uppercase tracking-widest flex items-center justify-center gap-1.5 hover:bg-rose-500/20 transition-all active:scale-95 disabled:opacity-50">
                    @if (desactivando() === p.punto_id) {
                      <mat-spinner diameter="14" color="warn"></mat-spinner>
                    } @else {
                      <mat-icon class="!text-sm">power_settings_new</mat-icon>
                    }
                    Desactivar PDV
                  </button>
                }
              </div>

            </div>
          }
        }
      </div>
    </div>
  `,
  styles: [`:host { display: block; height: 100%; }`]
})
export class MercPdvActivosComponent implements OnInit {
  private api = inject(ApiService);
  private ui = inject(MercUiService);
  private snack = inject(MatSnackBar);
  private confirmSvc = inject(ConfirmService);

  pdvs = signal<PdvActivo[]>([]);
  loading = signal(true);
  desactivando = signal<string | null>(null);

  constructor() {
    effect(() => {
      const active = this.ui.activeVisit();
      if (!active) {
        this.cargar();
      }
    }, { allowSignalWrites: true });
  }

  ngOnInit(): void {
  }

  cargar(): void {
    this.loading.set(true);
    this.api.get<PdvActivo[]>('/api/merc/pdv-activos').subscribe({
      next: (res) => {
        this.pdvs.set(res || []);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  continuarVisita(p: PdvActivo): void {
    if (!p.ultima_visita_local_id || !p.ultima_visita_cliente_id) {
      this.snack.open('No hay información suficiente para continuar la visita.', 'OK', { duration: 4000 });
      return;
    }
    this.ui.openVisit({
      id_visita: p.ultima_visita_local_id,
      pdv_nombre: p.punto_nombre,
      id_punto: p.punto_id,
      id_cliente: p.ultima_visita_cliente_id,
      cliente: p.ultima_visita_cliente_nombre || undefined,
    });
  }

  async desactivarPdv(p: PdvActivo): Promise<void> {
    const confirmado = await this.confirmSvc.confirm(
      `¿Estás seguro de desactivar el PDV "${p.punto_nombre}"? Todos los clientes deben estar visitados.`,
      { title: 'Desactivar PDV', confirmText: 'Sí, desactivar', cancelText: 'Cancelar', danger: true }
    );
    if (!confirmado) return;

    this.desactivando.set(p.punto_id);
    try {
      await firstValueFrom(this.api.desactivarPdv(p.punto_id));
      this.snack.open(`PDV "${p.punto_nombre}" desactivado.`, 'OK', { duration: 3000 });
      this.cargar();
    } catch (e: any) {
      const detail = e?.error?.detail || e?.error?.mensaje || e?.error;
      const mensaje = typeof detail === 'string' ? detail : 'Error al desactivar PDV';
      this.snack.open(mensaje, 'OK', { duration: 5000 });
    } finally {
      this.desactivando.set(null);
    }
  }
}
