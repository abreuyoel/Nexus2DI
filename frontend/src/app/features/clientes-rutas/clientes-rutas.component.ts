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
<div class="min-h-screen bg-white dark:bg-slate-950 text-slate-900 dark:text-white">
  <div class="bg-gradient-to-r from-slate-50 to-white dark:from-slate-900 dark:to-slate-800 border-b border-slate-200 dark:border-white/8 px-8 py-6">
    <div class="flex items-center gap-4">
      <div class="w-12 h-12 rounded-2xl bg-gradient-to-br from-violet-600 to-purple-700 flex items-center justify-center shadow-lg shrink-0">
        <mat-icon class="text-white">alt_route</mat-icon>
      </div>
      <div>
        <h1 class="text-2xl font-black tracking-tight leading-none">Clientes · Rutas</h1>
        <p class="text-slate-500 dark:text-slate-400 text-sm mt-0.5">Asigna a cada usuario cliente las rutas que verá (solo las de su programación)</p>
      </div>
    </div>
  </div>

  <div class="px-8 py-6 grid grid-cols-1 lg:grid-cols-[360px_1fr] gap-6 max-w-6xl">
    <!-- IZQUIERDA: usuarios cliente -->
    <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/8 rounded-2xl overflow-hidden self-start">
      <div class="px-4 py-3 border-b border-slate-100 dark:border-white/8">
        <div class="relative">
          <mat-icon class="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 !text-base">search</mat-icon>
          <input [(ngModel)]="filtro" placeholder="Buscar usuario cliente…"
            class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:border-violet-500 rounded-xl pl-9 pr-3 py-2 text-sm text-slate-900 dark:text-white placeholder-slate-400 outline-none">
        </div>
      </div>
      <div class="max-h-[68vh] overflow-y-auto">
        @if (loadingUsers()) { <div class="flex justify-center py-10"><mat-spinner diameter="28"></mat-spinner></div> }
        @for (u of usuariosFiltrados(); track u.id_usuario) {
          <button (click)="seleccionar(u)"
            class="w-full text-left px-4 py-3 border-b border-slate-100 dark:border-white/5 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors flex items-center gap-3"
            [class.bg-violet-50]="sel()?.id_usuario === u.id_usuario"
            [class.dark:!bg-violet-950]="sel()?.id_usuario === u.id_usuario">
            <div class="w-9 h-9 rounded-xl bg-violet-100 dark:bg-violet-900 flex items-center justify-center shrink-0"><mat-icon class="!text-base text-violet-600 dark:text-violet-400">person</mat-icon></div>
            <div class="min-w-0 flex-1">
              <p class="font-bold text-sm text-slate-800 dark:text-slate-100 truncate">{{ u.cliente || u.username }}</p>
              <p class="text-xs text-slate-500 truncate">{{ u.username }}</p>
            </div>
            <span class="text-xs px-2 py-0.5 rounded-full font-bold shrink-0" [ngClass]="u.n_rutas ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400' : 'bg-slate-100 dark:bg-slate-800 text-slate-400 dark:text-slate-500'">{{ u.n_rutas }}</span>
          </button>
        }
        @if (!loadingUsers() && !usuariosFiltrados().length) { <p class="text-center text-slate-400 dark:text-slate-600 py-10 text-sm">Sin usuarios cliente.</p> }
      </div>
    </div>

    <!-- DERECHA: rutas del cliente -->
    <div>
      @if (!sel()) {
        <div class="flex flex-col items-center justify-center py-32 text-slate-400 dark:text-slate-600 gap-3">
          <mat-icon class="!text-5xl">alt_route</mat-icon>
          <p class="font-bold">Selecciona un usuario cliente para ver y asignar sus rutas</p>
        </div>
      } @else {
        <div class="flex items-center justify-between mb-4">
          <div>
            <h2 class="text-lg font-black">{{ sel()?.cliente || sel()?.username }}</h2>
            <p class="text-slate-500 dark:text-slate-400 text-sm">Rutas donde aparece este cliente en la programación</p>
          </div>
          <span class="text-sm text-slate-500 dark:text-slate-400">{{ asignadas() }} de {{ rutas().length }} asignadas</span>
        </div>

        @if (loadingRutas()) { <div class="flex justify-center py-16"><mat-spinner diameter="36"></mat-spinner></div> }
        @else {
          @for (r of rutas(); track r.id_ruta) {
            <div class="bg-white dark:bg-slate-900 border rounded-2xl p-4 mb-3 flex items-center gap-3 transition-colors"
                 [ngClass]="r.asignada ? 'border-emerald-400 dark:border-emerald-800/60' : 'border-slate-200 dark:border-white/8'">
              <div class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" [ngClass]="r.asignada ? 'bg-emerald-100 dark:bg-emerald-900' : 'bg-slate-100 dark:bg-slate-800'">
                <mat-icon [ngClass]="r.asignada ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-500 dark:text-slate-400'">route</mat-icon>
              </div>
              <div class="flex-1 min-w-0">
                <p class="font-bold text-slate-800 dark:text-slate-100 truncate">{{ r.ruta }}</p>
                <p class="text-xs text-slate-500">{{ r.pdvs }} PDVs de este cliente</p>
              </div>
              @if (r.asignada) {
                <button *hasPerm="'clientes-rutas'; action:'delete'" (click)="quitar(r)" [disabled]="busy()" class="px-4 py-2 bg-red-100 dark:bg-red-950 hover:bg-red-200 dark:hover:bg-red-900 text-red-700 dark:text-red-300 rounded-xl text-sm font-bold flex items-center gap-1 transition-colors">
                  <mat-icon class="!text-base">link_off</mat-icon> Quitar
                </button>
              } @else {
                <button *hasPerm="'clientes-rutas'; action:'write'" (click)="asignar(r)" [disabled]="busy()" class="px-4 py-2 bg-violet-600 hover:bg-violet-500 dark:bg-violet-700 dark:hover:bg-violet-600 text-white rounded-xl text-sm font-bold flex items-center gap-1 transition-colors">
                  <mat-icon class="!text-base">add_link</mat-icon> Asignar
                </button>
              }
            </div>
          }
          @if (!rutas().length) {
            <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/8 rounded-2xl py-12 text-center text-slate-500 dark:text-slate-500">
              <mat-icon class="!text-4xl block mx-auto mb-2 text-slate-300 dark:text-slate-700">wrong_location</mat-icon>
              Este cliente no aparece en ninguna ruta programada.
            </div>
          }
        }
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
  filtro = '';

  usuariosFiltrados = computed(() => {
    const f = this.filtro.trim().toLowerCase();
    const list = this.usuarios();
    if (!f) return list;
    return list.filter(u => (u.cliente || '').toLowerCase().includes(f) || u.username.toLowerCase().includes(f));
  });
  asignadas = computed(() => this.rutas().filter(r => r.asignada).length);

  ngOnInit() { this.loadUsuarios(); }

  loadUsuarios() {
    this.loadingUsers.set(true);
    this.http.get<UsuarioCliente[]>(`${this.API}/clientes-rutas-usuarios`).subscribe({
      next: u => { this.usuarios.set(u); this.loadingUsers.set(false); },
      error: e => { this.loadingUsers.set(false); this.err(e); },
    });
  }
  seleccionar(u: UsuarioCliente) {
    this.sel.set(u); this.loadRutas();
  }
  loadRutas() {
    const u = this.sel(); if (!u) return;
    this.loadingRutas.set(true);
    this.http.get<{ rutas: RutaDisp[] }>(`${this.API}/clientes-rutas-disponibles/${u.id_usuario}`).subscribe({
      next: r => { this.rutas.set(r.rutas); this.loadingRutas.set(false); },
      error: e => { this.loadingRutas.set(false); this.err(e); },
    });
  }
  asignar(r: RutaDisp) {
    const u = this.sel(); if (!u) return;
    this.busy.set(true);
    this.http.post<any>(`${this.API}/clientes-rutas`, { id_usuario: u.id_usuario, id_ruta: r.id_ruta, activo: true }).subscribe({
      next: res => { this.busy.set(false); this.marcar(r.id_ruta, true, res.id_cliente_ruta); this.bumpUser(u, 1); this.snack.open('Ruta asignada', 'OK', { duration: 2000 }); },
      error: e => { this.busy.set(false); this.err(e); },
    });
  }
  quitar(r: RutaDisp) {
    const u = this.sel(); if (!u || r.id_cliente_ruta == null) return;
    this.busy.set(true);
    this.http.delete(`${this.API}/clientes-rutas/${r.id_cliente_ruta}`).subscribe({
      next: () => { this.busy.set(false); this.marcar(r.id_ruta, false, null); this.bumpUser(u, -1); this.snack.open('Ruta quitada', 'OK', { duration: 2000 }); },
      error: e => { this.busy.set(false); this.err(e); },
    });
  }
  private marcar(idRuta: number, asignada: boolean, idCr: number | null) {
    this.rutas.update(list => list.map(x => x.id_ruta === idRuta ? { ...x, asignada, id_cliente_ruta: idCr } : x));
  }
  private bumpUser(u: UsuarioCliente, delta: number) {
    this.usuarios.update(list => list.map(x => x.id_usuario === u.id_usuario ? { ...x, n_rutas: Math.max(0, x.n_rutas + delta) } : x));
    this.sel.update(s => s ? { ...s, n_rutas: Math.max(0, s.n_rutas + delta) } : s);
  }
  private err(e: any) { this.snack.open(e?.error?.detail || e?.error?.message || 'Error', 'OK', { duration: 4000 }); }
}
