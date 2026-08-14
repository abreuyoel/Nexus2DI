import { Component, OnInit, signal, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { environment } from '../../../environments/environment';
import { HasPermDirective } from '../../core/directives/has-perm.directive';

type UsuarioCliente = { id_usuario: number; username: string; id_cliente: number | null; cliente: string | null; n_rutas: number };
type RutaDisp = { id_ruta: number; ruta: string; pdvs: number; asignada: boolean; id_cliente_ruta: number | null };

@Component({
  selector: 'app-clientes-rutas',
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule, MatSnackBarModule, MatProgressSpinnerModule, HasPermDirective],
  template: `
<div class="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-800 dark:text-white">
  <div class="bg-gradient-to-r from-slate-900 to-slate-800 border-b border-white/8 px-8 py-6">
    <div class="flex items-center gap-4">
      <div class="w-12 h-12 rounded-2xl bg-gradient-to-br from-violet-600 to-purple-700 flex items-center justify-center shadow-lg shrink-0">
        <mat-icon class="text-white">alt_route</mat-icon>
      </div>
      <div>
        <h1 class="text-2xl font-black tracking-tight leading-none">Clientes · Rutas</h1>
        <p class="text-slate-400 text-sm mt-0.5">Asigna a cada usuario cliente las rutas que verá (solo las de su programación)</p>
      </div>
    </div>
  </div>

  <div class="px-8 py-6 grid grid-cols-1 lg:grid-cols-[360px_1fr] gap-6 max-w-6xl items-start">
    <!-- IZQUIERDA: usuarios cliente -->
    <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/8 rounded-2xl overflow-hidden">
      <div class="px-4 py-3 border-b border-slate-100 dark:border-white/8">
        <div class="relative">
          <mat-icon class="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 !text-base">search</mat-icon>
          <input [ngModel]="filtro()" (ngModelChange)="filtro.set($event); onFiltroChange()" placeholder="Buscar usuario cliente…"
            class="w-full bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-violet-500 rounded-xl pl-9 pr-3 py-2 text-sm outline-none">
        </div>
      </div>
      <div class="max-h-[68vh] overflow-y-auto">
        @if (loadingUsers()) { <div class="flex justify-center py-10"><mat-spinner diameter="28"></mat-spinner></div> }
        @for (u of paginatedUsuarios(); track u.id_usuario) {
          <button (click)="seleccionar(u)"
            class="w-full text-left px-4 py-3 border-b border-slate-100 dark:border-white/5 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors flex items-center gap-3"
            [class.bg-violet-50]="sel()?.id_usuario === u.id_usuario"
            [class.dark:bg-violet-950]="sel()?.id_usuario === u.id_usuario">
            <div class="w-9 h-9 rounded-xl bg-violet-100 dark:bg-violet-900 flex items-center justify-center shrink-0"><mat-icon class="!text-base text-violet-600 dark:text-violet-400">person</mat-icon></div>
            <div class="min-w-0 flex-1">
              <p class="font-bold text-sm truncate">{{ u.cliente || u.username }}</p>
              <p class="text-xs text-slate-500 dark:text-slate-400 truncate">{{ u.username }}</p>
            </div>
            <span class="text-xs px-2 py-0.5 rounded-full font-bold shrink-0" [ngClass]="u.n_rutas ? 'bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-400' : 'bg-slate-100 dark:bg-slate-800 text-slate-500'">{{ u.n_rutas }}</span>
          </button>
        }
        @if (!loadingUsers() && !paginatedUsuarios().length) { <p class="text-center text-slate-500 dark:text-slate-600 py-10 text-sm">Sin usuarios cliente.</p> }
      </div>
      <div class="px-4 py-3 border-t border-slate-100 dark:border-white/8 flex items-center justify-between gap-2">
        <div class="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
          <select [ngModel]="userPageSize()" (ngModelChange)="onUserPageSizeChange($event)"
            class="bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-white/10 text-slate-700 dark:text-white rounded-lg px-2 py-1 text-sm font-semibold outline-none focus:border-violet-500">
            <option [ngValue]="20">20</option>
            <option [ngValue]="50">50</option>
            <option [ngValue]="100">100</option>
          </select>
          <span>/página</span>
        </div>
        <div class="flex items-center gap-1">
          <button type="button" (click)="goUserPage(userPage() - 1)" [disabled]="userPage() <= 0"
            class="w-8 h-8 rounded-lg border border-slate-200 dark:border-white/10 text-sm font-bold hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40 transition-colors">‹</button>
          <span class="text-sm font-bold px-1">{{ userPage() + 1 }}/{{ totalUserPages }}</span>
          <button type="button" (click)="goUserPage(userPage() + 1)" [disabled]="userPage() >= totalUserPages - 1"
            class="w-8 h-8 rounded-lg border border-slate-200 dark:border-white/10 text-sm font-bold hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40 transition-colors">›</button>
        </div>
      </div>
    </div>

    <!-- DERECHA: rutas del cliente -->
    <div>
      @if (!sel()) {
        <div class="flex flex-col items-center justify-center py-32 text-slate-500 dark:text-slate-600 gap-3">
          <mat-icon class="!text-5xl">alt_route</mat-icon>
          <p class="font-bold">Selecciona un usuario cliente para ver y asignar sus rutas</p>
        </div>
      } @else {
        <div class="flex items-center justify-between mb-4 flex-wrap gap-2">
          <div>
            <h2 class="text-lg font-black">{{ sel()?.cliente || sel()?.username }}</h2>
            <p class="text-slate-500 dark:text-slate-400 text-sm">Rutas donde aparece este cliente en la programación</p>
          </div>
          <span class="text-sm text-slate-500 dark:text-slate-400">{{ asignadas() }} de {{ rutas().length }} asignadas</span>
        </div>

        <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/8 rounded-2xl overflow-hidden">
          <div class="px-4 py-3 border-b border-slate-100 dark:border-white/8">
            <div class="relative">
              <mat-icon class="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 !text-base">search</mat-icon>
              <input [ngModel]="filtroRutas()" (ngModelChange)="filtroRutas.set($event); onRutaFiltroChange()" placeholder="Buscar ruta…"
                class="w-full bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-violet-500 rounded-xl pl-9 pr-3 py-2 text-sm outline-none">
            </div>
          </div>

          @if (loadingRutas()) {
            <div class="flex justify-center py-16"><mat-spinner diameter="36"></mat-spinner></div>
          } @else {
            <div class="max-h-[49vh] min-h-[49vh] overflow-y-auto">
              @for (r of paginatedRutas(); track r.id_ruta) {
                <div class="border-b border-slate-100 dark:border-white/5 px-4 py-3 flex items-center gap-3 transition-colors"
                     [ngClass]="r.asignada ? 'bg-emerald-50/50 dark:bg-emerald-950/20' : ''">
                  <div class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" [ngClass]="r.asignada ? 'bg-emerald-100 dark:bg-emerald-900' : 'bg-slate-100 dark:bg-slate-800'">
                    <mat-icon [ngClass]="r.asignada ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-400'">route</mat-icon>
                  </div>
                  <div class="flex-1 min-w-0">
                    <p class="font-bold truncate">{{ r.ruta }}</p>
                    <p class="text-xs text-slate-500 dark:text-slate-400">{{ r.pdvs }} PDVs de este cliente</p>
                  </div>
                  @if (r.asignada) {
                    <button *hasPerm="'clientes-rutas'; action:'delete'" (click)="quitar(r)" [disabled]="busy()" class="px-4 py-2 bg-red-950 hover:bg-red-900 text-red-300 rounded-xl text-sm font-bold flex items-center gap-1 shrink-0">
                      <mat-icon class="!text-base">link_off</mat-icon> Quitar
                    </button>
                  } @else {
                    <button *hasPerm="'clientes-rutas'; action:'write'" (click)="asignar(r)" [disabled]="busy()" class="px-4 py-2 bg-violet-700 hover:bg-violet-600 text-white rounded-xl text-sm font-bold flex items-center gap-1 shrink-0">
                      <mat-icon class="!text-base">add_link</mat-icon> Asignar
                    </button>
                  }
                </div>
              }
              @if (!paginatedRutas().length) {
                <div class="py-12 text-center text-slate-500 dark:text-slate-400">
                  <mat-icon class="!text-4xl block mx-auto mb-2 text-slate-300 dark:text-slate-700">wrong_location</mat-icon>
                  {{ filtroRutas() ? 'Sin rutas que coincidan con la búsqueda.' : 'Este cliente no aparece en ninguna ruta programada.' }}
                </div>
              }
            </div>

            @if (rutasFiltradas().length) {
              <div class="px-4 py-3 border-t border-slate-100 dark:border-white/8 flex flex-wrap items-center justify-between gap-2">
                <div class="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
                  <span>{{ rutaRangeLabel }}</span>
                  <select [ngModel]="rutaPageSize()" (ngModelChange)="onRutaPageSizeChange($event)"
                    class="bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-white/10 text-slate-700 dark:text-white rounded-lg px-2 py-1 text-sm font-semibold outline-none focus:border-violet-500">
                    <option [ngValue]="20">20</option>
                    <option [ngValue]="50">50</option>
                    <option [ngValue]="100">100</option>
                  </select>
                  <span>por página</span>
                </div>
                <div class="flex items-center gap-2">
                  <button type="button" (click)="goRutaPage(rutaPage() - 1)" [disabled]="rutaPage() <= 0"
                    class="px-3 py-1.5 rounded-xl border border-slate-200 dark:border-white/10 text-sm font-bold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40 transition-colors">
                    Anterior
                  </button>
                  <span class="text-sm font-bold text-slate-600 dark:text-slate-300">{{ rutaPage() + 1 }} / {{ totalRutaPages }}</span>
                  <button type="button" (click)="goRutaPage(rutaPage() + 1)" [disabled]="rutaPage() >= totalRutaPages - 1"
                    class="px-3 py-1.5 rounded-xl border border-slate-200 dark:border-white/10 text-sm font-bold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40 transition-colors">
                    Siguiente
                  </button>
                </div>
              </div>
            }
          }
        </div>
      }
    </div>
  </div>
</div>
  `,
})
export class ClientesRutasComponent implements OnInit {
  private http = inject(HttpClient);
  private snack = inject(MatSnackBar);
  private API = `${environment.apiUrl}/api`;

  usuarios = signal<UsuarioCliente[]>([]);
  rutas = signal<RutaDisp[]>([]);
  sel = signal<UsuarioCliente | null>(null);
  loadingUsers = signal(false);
  loadingRutas = signal(false);
  busy = signal(false);
  filtro = signal('');
  filtroRutas = signal('');

  usuariosFiltrados = computed(() => {
    const f = this.filtro().trim().toLowerCase();
    const list = this.usuarios();
    if (!f) return list;
    return list.filter(u => (u.cliente || '').toLowerCase().includes(f) || u.username.toLowerCase().includes(f));
  });
  asignadas = computed(() => this.rutas().filter(r => r.asignada).length);

  // Paginación client-side — usuarios
  userPage = signal(0);
  userPageSize = signal(20);
  paginatedUsuarios = computed<UsuarioCliente[]>(() => {
    const size = this.userPageSize();
    const start = this.userPage() * size;
    return this.usuariosFiltrados().slice(start, start + size);
  });
  get totalUserPages(): number { return Math.max(1, Math.ceil(this.usuariosFiltrados().length / this.userPageSize())); }
  goUserPage(p: number): void { this.userPage.set(p); }
  onUserPageSizeChange(val: number): void { this.userPageSize.set(val); this.userPage.set(0); }
  onFiltroChange(): void { this.userPage.set(0); }

  // Filtro + paginación client-side — rutas
  rutasFiltradas = computed<RutaDisp[]>(() => {
    const f = this.filtroRutas().trim().toLowerCase();
    const list = this.rutas();
    if (!f) return list;
    return list.filter(r => r.ruta.toLowerCase().includes(f));
  });
  rutaPage = signal(0);
  rutaPageSize = signal(20);
  paginatedRutas = computed<RutaDisp[]>(() => {
    const size = this.rutaPageSize();
    const start = this.rutaPage() * size;
    return this.rutasFiltradas().slice(start, start + size);
  });
  get totalRutaPages(): number { return Math.max(1, Math.ceil(this.rutasFiltradas().length / this.rutaPageSize())); }
  get rutaRangeLabel(): string {
    const total = this.rutasFiltradas().length;
    if (!total) return '0–0 de 0';
    const start = this.rutaPage() * this.rutaPageSize() + 1;
    const end = Math.min((this.rutaPage() + 1) * this.rutaPageSize(), total);
    return `Mostrando ${start}–${end} de ${total}`;
  }
  goRutaPage(p: number): void { this.rutaPage.set(p); }
  onRutaPageSizeChange(val: number): void { this.rutaPageSize.set(val); this.rutaPage.set(0); }
  onRutaFiltroChange(): void { this.rutaPage.set(0); }

  ngOnInit() { this.loadUsuarios(); }

  loadUsuarios() {
    this.loadingUsers.set(true);
    this.userPage.set(0);
    this.http.get<UsuarioCliente[]>(`${this.API}/clientes-rutas-usuarios`).subscribe({
      next: u => { this.usuarios.set(u); this.loadingUsers.set(false); },
      error: e => { this.loadingUsers.set(false); this.err(e); },
    });
  }
  seleccionar(u: UsuarioCliente) {
    this.sel.set(u); this.rutaPage.set(0); this.filtroRutas.set(''); this.loadRutas();
  }
  loadRutas() {
    const u = this.sel(); if (!u) return;
    this.loadingRutas.set(true);
    this.rutaPage.set(0);
    this.http.get<{ rutas: RutaDisp[] }>(`${this.API}/clientes-rutas-disponibles/${u.id_usuario}`).subscribe({
      next: r => { this.rutas.set(r.rutas); this.loadingRutas.set(false); },
      error: e => { this.loadingRutas.set(false); this.err(e); },
    });
  }
  asignar(r: RutaDisp) {
    const u = this.sel(); if (!u) return;
    this.busy.set(true);
    this.http.post<any>(`${this.API}/clientes-rutas`, { id_usuario: u.id_usuario, id_ruta: r.id_ruta, activo: true }).subscribe({
      next: res => { this.busy.set(false); this.marcar(r.id_ruta, true, res.id_cliente_ruta); this.snack.open('Ruta asignada', 'OK', { duration: 2000 }); },
      error: e => { this.busy.set(false); this.err(e); },
    });
  }
  quitar(r: RutaDisp) {
    const u = this.sel(); if (!u || r.id_cliente_ruta == null) return;
    this.busy.set(true);
    this.http.delete(`${this.API}/clientes-rutas/${r.id_cliente_ruta}`).subscribe({
      next: () => { this.busy.set(false); this.marcar(r.id_ruta, false, null); this.snack.open('Ruta quitada', 'OK', { duration: 2000 }); },
      error: e => { this.busy.set(false); this.err(e); },
    });
  }
  private marcar(idRuta: number, asignada: boolean, idCr: number | null) {
    this.rutas.update(list => list.map(x => x.id_ruta === idRuta ? { ...x, asignada, id_cliente_ruta: idCr } : x));
  }
  private err(e: any) { this.snack.open(e?.error?.detail || e?.error?.message || 'Error', 'OK', { duration: 4000 }); }
}
