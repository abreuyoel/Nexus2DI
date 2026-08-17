import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { RouterLink } from '@angular/router';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/services/auth.service';
import { ConfirmService } from '../../shared/components/confirm-dialog/confirm.service';

type LineaPedido = { id_linea: number; id_producto: number; nombre_producto: string; cantidad: number; precio_unitario: number; descuento_pct: number; subtotal_linea: number };
type PedidoResumen = { id_pedido: number; numero_pedido: string; id_cliente: number; cliente: string; vendedor: string; fecha: string; estado: string; total: number; origen: string };
type PedidoDetalle = PedidoResumen & {
  id_usuario_vendedor: number; identificador_punto_interes: string | null; subtotal: number; descuento_total: number;
  impuestos: number; latitud: number | null; longitud: number | null; notas: string | null;
  firma_cliente_url: string | null; lineas: LineaPedido[];
};

const ESTADO_COLOR: Record<string, string> = {
  Borrador: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
  Enviado: 'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-400',
  Aprobado: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400',
  Rechazado: 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-400',
  Facturado: 'bg-violet-100 text-violet-700 dark:bg-violet-950 dark:text-violet-400',
  Despachado: 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-400',
  Entregado: 'bg-teal-100 text-teal-700 dark:bg-teal-950 dark:text-teal-400',
};

@Component({
  selector: 'app-pedidos-ventas',
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule, MatSnackBarModule, MatProgressSpinnerModule, RouterLink],
  template: `
<div class="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-800 dark:text-white">
  <div class="bg-white dark:bg-gradient-to-r dark:from-slate-900 dark:to-slate-800 border-b border-slate-200 dark:border-white/8 px-6 py-5">
    <div class="flex flex-wrap items-center gap-3 max-w-6xl mx-auto">
      <a routerLink="/ventas-dashboard" class="w-9 h-9 flex items-center justify-center rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"><mat-icon class="!text-base">arrow_back</mat-icon></a>
      <div class="w-11 h-11 rounded-2xl bg-gradient-to-br from-emerald-600 to-teal-700 flex items-center justify-center shadow-lg shadow-emerald-500/20">
        <mat-icon class="text-white">receipt_long</mat-icon>
      </div>
      <div class="flex-1 min-w-[140px]">
        <h1 class="text-xl font-black tracking-tight leading-none">Pedidos</h1>
        <p class="text-slate-500 dark:text-slate-400 text-xs mt-0.5">Gestión y aprobación</p>
      </div>
      <div class="relative">
        <mat-icon class="!text-base absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">search</mat-icon>
        <input [(ngModel)]="search" placeholder="Buscar N°, cliente, vendedor..."
          class="pl-9 pr-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-sm w-56 outline-none focus:border-emerald-500">
      </div>
      <select [(ngModel)]="filtroEstado" (change)="cargar()" class="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm outline-none focus:border-emerald-500">
        <option value="">Todos los estados</option>
        @for (e of estados; track e) { <option [value]="e">{{ e }}</option> }
      </select>
    </div>
  </div>

  <div class="px-6 py-6 max-w-6xl mx-auto">
    @if (loading()) {
      <div class="flex justify-center py-24"><mat-spinner diameter="40"></mat-spinner></div>
    } @else {

    <!-- RESUMEN -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
      <div class="relative overflow-hidden bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/8 rounded-xl p-4">
        <div class="absolute top-0 left-0 w-full h-0.5 bg-gradient-to-r from-indigo-500 to-violet-500"></div>
        <p class="text-[10px] text-slate-400 font-black uppercase tracking-wider">Pedidos</p>
        <p class="text-2xl font-black">{{ pedidosFiltrados().length }}</p>
      </div>
      <div class="relative overflow-hidden bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/8 rounded-xl p-4">
        <div class="absolute top-0 left-0 w-full h-0.5 bg-gradient-to-r from-emerald-500 to-teal-500"></div>
        <p class="text-[10px] text-slate-400 font-black uppercase tracking-wider">Total</p>
        <p class="text-2xl font-black text-emerald-600 dark:text-emerald-400">\${{ totalFiltrado().toFixed(0) }}</p>
      </div>
      <div class="relative overflow-hidden bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/8 rounded-xl p-4">
        <div class="absolute top-0 left-0 w-full h-0.5 bg-gradient-to-r from-amber-500 to-orange-500"></div>
        <p class="text-[10px] text-slate-400 font-black uppercase tracking-wider">Pendientes</p>
        <p class="text-2xl font-black">{{ contarPorEstado('Enviado') }}</p>
      </div>
      <div class="relative overflow-hidden bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/8 rounded-xl p-4">
        <div class="absolute top-0 left-0 w-full h-0.5 bg-gradient-to-r from-rose-500 to-red-500"></div>
        <p class="text-[10px] text-slate-400 font-black uppercase tracking-wider">Rechazados</p>
        <p class="text-2xl font-black">{{ contarPorEstado('Rechazado') }}</p>
      </div>
    </div>

      <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/8 rounded-2xl overflow-hidden shadow-sm">
        <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-slate-50 dark:bg-slate-800 text-xs uppercase text-slate-500 dark:text-slate-400">
            <tr>
              <th class="text-left px-4 py-3">N° Pedido</th>
              <th class="text-left px-4 py-3">Cliente</th>
              <th class="text-left px-4 py-3">Vendedor</th>
              <th class="text-left px-4 py-3">Fecha</th>
              <th class="text-right px-4 py-3">Total</th>
              <th class="text-center px-4 py-3">Estado</th>
              <th class="text-center px-4 py-3">Origen</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 dark:divide-white/5">
            @for (p of pedidosFiltrados(); track p.id_pedido) {
              <tr class="hover:bg-slate-50 dark:hover:bg-slate-800/60 cursor-pointer transition-colors" (click)="abrirDetalle(p.id_pedido)">
                <td class="px-4 py-3 font-bold">{{ p.numero_pedido }}</td>
                <td class="px-4 py-3">{{ p.cliente }}</td>
                <td class="px-4 py-3 text-slate-500 dark:text-slate-400">{{ p.vendedor }}</td>
                <td class="px-4 py-3 text-slate-500 dark:text-slate-400">{{ fmtFecha(p.fecha) }}</td>
                <td class="px-4 py-3 text-right font-bold text-emerald-600 dark:text-emerald-400">\${{ p.total.toFixed(2) }}</td>
                <td class="px-4 py-3 text-center"><span class="px-2 py-1 rounded-full text-xs font-bold" [ngClass]="ESTADO_COLOR[p.estado]">{{ p.estado }}</span></td>
                <td class="px-4 py-3 text-center">
                  @if (p.origen === 'ocr') { <mat-icon class="!text-base text-violet-500" title="Cargado con IA">document_scanner</mat-icon> } @else { <mat-icon class="!text-base text-slate-400" title="Manual">touch_app</mat-icon> }
                </td>
              </tr>
            }
            @if (!pedidosFiltrados().length) {
              <tr><td colspan="7" class="text-center py-16 text-slate-400">
                <mat-icon class="!text-3xl block mx-auto mb-2 opacity-40">receipt_long</mat-icon>
                No hay pedidos con ese filtro
              </td></tr>
            }
          </tbody>
        </table>
        </div>
      </div>
    }
  </div>

  <!-- DETALLE (drawer) -->
  @if (detalle()) {
    <div class="fixed inset-0 bg-black/40 z-40 backdrop-blur-[2px]" (click)="detalle.set(null)"></div>
    <div class="fixed top-0 right-0 h-full w-full max-w-md bg-white dark:bg-slate-900 z-50 shadow-2xl overflow-y-auto animate-in slide-in-from-right duration-300">
      <div class="p-5 border-b border-slate-200 dark:border-white/8 flex items-start justify-between bg-slate-50 dark:bg-slate-800/50">
        <div>
          <h2 class="text-lg font-black">{{ detalle()!.numero_pedido }}</h2>
          <p class="text-sm text-slate-500 dark:text-slate-400 flex items-center gap-1 mt-0.5"><mat-icon class="!text-sm">storefront</mat-icon> {{ detalle()!.cliente }} · {{ fmtFecha(detalle()!.fecha) }}</p>
          <span class="inline-block mt-2 px-2 py-1 rounded-full text-xs font-bold" [ngClass]="ESTADO_COLOR[detalle()!.estado]">{{ detalle()!.estado }}</span>
        </div>
        <button (click)="detalle.set(null)" class="w-8 h-8 flex items-center justify-center rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-white/10 hover:border-rose-300 hover:text-rose-500 transition-colors"><mat-icon class="!text-base">close</mat-icon></button>
      </div>

      <div class="p-5">
        <h3 class="text-xs font-black uppercase text-slate-400 mb-2 flex items-center gap-1.5"><mat-icon class="!text-sm">shopping_cart</mat-icon> Líneas</h3>
        <div class="space-y-2 mb-4">
          @for (l of detalle()!.lineas; track l.id_linea) {
            <div class="flex items-center justify-between text-sm bg-slate-50 dark:bg-slate-800 rounded-lg px-3 py-2 border border-slate-100 dark:border-white/5">
              <div class="flex-1"><p class="font-semibold">{{ l.nombre_producto }}</p><p class="text-xs text-slate-500">{{ l.cantidad }} × \${{ l.precio_unitario.toFixed(2) }}</p></div>
              <p class="font-bold">\${{ l.subtotal_linea.toFixed(2) }}</p>
            </div>
          }
        </div>

        <div class="space-y-1 text-sm mb-4 bg-slate-50 dark:bg-slate-800/50 rounded-xl p-3">
          <div class="flex justify-between"><span class="text-slate-500">Subtotal</span><span>\${{ detalle()!.subtotal.toFixed(2) }}</span></div>
          <div class="flex justify-between"><span class="text-slate-500">Descuento</span><span>-\${{ detalle()!.descuento_total.toFixed(2) }}</span></div>
          <div class="flex justify-between font-black text-base border-t border-slate-200 dark:border-white/8 pt-2 mt-2"><span>Total</span><span class="text-emerald-600 dark:text-emerald-400">\${{ detalle()!.total.toFixed(2) }}</span></div>
        </div>

        @if (detalle()!.notas) {
          <div class="bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900 rounded-lg p-3 mb-4 text-sm flex items-start gap-2">
            <mat-icon class="!text-sm text-amber-600 mt-0.5 shrink-0">sticky_note_2</mat-icon> <span>{{ detalle()!.notas }}</span>
          </div>
        }

        <!-- FIRMA -->
        <h3 class="text-xs font-black uppercase text-slate-400 mb-2 flex items-center gap-1.5"><mat-icon class="!text-sm">draw</mat-icon> Conformidad del cliente</h3>
        @if (detalle()!.firma_cliente_url) {
          <img [src]="detalle()!.firma_cliente_url" class="w-full rounded-lg border border-slate-200 dark:border-white/8 mb-4">
        } @else {
          <label class="block w-full text-center py-3 mb-4 border-2 border-dashed border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-500 cursor-pointer hover:border-emerald-500">
            <mat-icon class="!text-base align-middle">add_a_photo</mat-icon> Subir foto de conformidad / firma
            <input type="file" accept="image/*" capture="environment" class="hidden" (change)="subirFirma($event)">
          </label>
        }

        <!-- ACCIONES DE ESTADO -->
        @if (accionesDisponibles().length) {
          <h3 class="text-xs font-black uppercase text-slate-400 mb-2 flex items-center gap-1.5"><mat-icon class="!text-sm">bolt</mat-icon> Acciones</h3>
          <div class="flex flex-wrap gap-2">
            @for (a of accionesDisponibles(); track a) {
              <button (click)="cambiarEstado(a)" [disabled]="cambiandoEstado()"
                class="px-4 py-2 rounded-xl text-sm font-bold text-white flex items-center gap-1.5 disabled:opacity-50 shadow-sm transition-transform active:scale-95"
                [ngClass]="a === 'Rechazado' ? 'bg-red-600 hover:bg-red-500' : 'bg-emerald-600 hover:bg-emerald-500'">
                @if (cambiandoEstado()) { <mat-spinner diameter="14" strokeWidth="2" class="!text-white"></mat-spinner> }
                @else { <mat-icon class="!text-base">{{ a === 'Rechazado' ? 'cancel' : 'check_circle' }}</mat-icon> }
                {{ a }}
              </button>
            }
          </div>
        }
      </div>
    </div>
  }
</div>
  `,
})
export class PedidosVentasComponent implements OnInit {
  private http = inject(HttpClient);
  private auth = inject(AuthService);
  private snack = inject(MatSnackBar);
  private confirmDialog = inject(ConfirmService);
  private API = `${environment.apiUrl}/api/vendedor`;

  ESTADO_COLOR = ESTADO_COLOR;
  estados = ['Borrador', 'Enviado', 'Aprobado', 'Rechazado', 'Facturado', 'Despachado', 'Entregado'];
  filtroEstado = '';
  search = '';

  loading = signal(true);
  pedidos = signal<PedidoResumen[]>([]);
  detalle = signal<PedidoDetalle | null>(null);
  cambiandoEstado = signal(false);

  private TRANSICIONES_GESTOR: Record<string, string[]> = {
    Enviado: ['Aprobado', 'Rechazado'], Aprobado: ['Facturado'], Facturado: ['Despachado'], Despachado: ['Entregado'],
  };
  private TRANSICIONES_VENDEDOR: Record<string, string[]> = { Borrador: ['Enviado'] };

  get esGestor(): boolean {
    const rol = this.auth.currentUser()?.rol;
    return rol === 'admin' || rol === 'supervisor';
  }

  ngOnInit() { this.cargar(); }

  cargar() {
    this.loading.set(true);
    const params = this.filtroEstado ? `?estado=${this.filtroEstado}` : '';
    this.http.get<PedidoResumen[]>(`${this.API}/pedidos${params}`).subscribe({
      next: r => { this.pedidos.set(r); this.loading.set(false); },
      error: () => { this.loading.set(false); this.snack.open('Error cargando pedidos', 'OK', { duration: 3000 }); },
    });
  }

  pedidosFiltrados(): PedidoResumen[] {
    const q = this.search.trim().toLowerCase();
    if (!q) return this.pedidos();
    return this.pedidos().filter(p =>
      p.numero_pedido.toLowerCase().includes(q) || p.cliente.toLowerCase().includes(q) || p.vendedor.toLowerCase().includes(q),
    );
  }

  totalFiltrado(): number { return this.pedidosFiltrados().reduce((a, p) => a + p.total, 0); }
  contarPorEstado(estado: string): number { return this.pedidosFiltrados().filter(p => p.estado === estado).length; }

  fmtFecha(iso: string): string {
    try { return new Date(iso).toLocaleString('es-VE', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }); }
    catch { return iso; }
  }

  abrirDetalle(id: number) {
    this.http.get<PedidoDetalle>(`${this.API}/pedidos/${id}`).subscribe({
      next: d => this.detalle.set(d),
      error: e => this.snack.open(e?.error?.detail || 'Error cargando el pedido', 'OK', { duration: 3000 }),
    });
  }

  accionesDisponibles(): string[] {
    const d = this.detalle();
    if (!d) return [];
    return this.esGestor ? (this.TRANSICIONES_GESTOR[d.estado] || []) : (this.TRANSICIONES_VENDEDOR[d.estado] || []);
  }

  async cambiarEstado(nuevoEstado: string) {
    const d = this.detalle();
    if (!d) return;
    if (nuevoEstado === 'Rechazado') {
      const ok = await this.confirmDialog.confirm(`¿Rechazar el pedido ${d.numero_pedido}?`, { title: 'Rechazar pedido', danger: true, confirmText: 'Sí, rechazar' });
      if (!ok) return;
    }
    this.cambiandoEstado.set(true);
    this.http.post<any>(`${this.API}/pedidos/${d.id_pedido}/estado`, { estado: nuevoEstado }).subscribe({
      next: () => {
        this.cambiandoEstado.set(false);
        this.detalle.set({ ...d, estado: nuevoEstado });
        this.snack.open(`Pedido actualizado a "${nuevoEstado}"`, 'OK', { duration: 2500 });
        this.cargar();
      },
      error: e => { this.cambiandoEstado.set(false); this.snack.open(e?.error?.detail || 'Error', 'OK', { duration: 3000 }); },
    });
  }

  subirFirma(ev: Event) {
    const file = (ev.target as HTMLInputElement).files?.[0];
    (ev.target as HTMLInputElement).value = '';
    const d = this.detalle();
    if (!file || !d) return;
    const fd = new FormData();
    fd.append('file', file);
    this.http.post<any>(`${this.API}/pedidos/${d.id_pedido}/firma`, fd).subscribe({
      next: res => { this.detalle.set({ ...d, firma_cliente_url: res.url }); this.snack.open('Foto de conformidad guardada', 'OK', { duration: 2500 }); },
      error: e => this.snack.open(e?.error?.detail || 'Error subiendo la foto', 'OK', { duration: 3000 }),
    });
  }
}
