import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';

@Component({
    selector: 'app-chat-grupos-admin',
    standalone: true,
    imports: [CommonModule, FormsModule],
    template: `
    <div class="p-6 max-w-6xl mx-auto">
      <div class="flex items-center gap-2 mb-2">
        <span class="material-icons text-indigo-500 dark:text-indigo-400 !text-3xl">forum</span>
        <h1 class="text-2xl font-bold text-slate-800 dark:text-white">Grupos de Chat</h1>
      </div>
      <p class="text-slate-500 dark:text-slate-400 text-sm mb-6">
        La membresía de cada grupo se calcula sola (por ruta, rol o cliente) -- acá solo se ven los grupos
        existentes y se puede agregar gente puntual que no encaje en ningún criterio automático.
      </p>

      <!-- Crear grupos para un cliente nuevo -->
      <div class="bg-white dark:bg-slate-900 rounded-xl border border-gray-200 dark:border-white/10 p-5 mb-6">
        <h3 class="text-sm font-bold text-slate-700 dark:text-slate-300 mb-3">Crear grupos para un cliente</h3>
        <p class="text-xs text-slate-500 dark:text-slate-400 mb-3">
          Normalmente no hace falta: los grupos "Equipo operativo" y "Equipo + Cliente" de un cliente se crean
          solos la primera vez que alguien con ruta asignada ahí abre el chat. Usá esto solo si querés
          adelantarlo (ej. antes de asignar rutas).
        </p>
        <div class="relative">
          <input type="text" [(ngModel)]="buscarCliente" (ngModelChange)="onBuscarCliente()"
                 placeholder="Buscar cliente..."
                 class="w-full max-w-md bg-slate-50 dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg p-2.5 text-sm text-slate-800 dark:text-white outline-none focus:border-indigo-500">
          @if (clientesResult().length > 0) {
            <div class="absolute z-10 mt-1 w-full max-w-md bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg shadow-xl max-h-56 overflow-y-auto">
              @for (c of clientesResult(); track c.id_cliente) {
                <div class="flex items-center justify-between px-4 py-2.5 hover:bg-gray-50 dark:hover:bg-slate-700 text-sm">
                  <span class="text-slate-700 dark:text-slate-200">{{ c.cliente }}</span>
                  @if (c.grupos_completos) {
                    <span class="text-[10px] font-bold uppercase text-emerald-600 dark:text-emerald-400">Ya tiene grupos</span>
                  } @else {
                    <button (click)="crearGrupos(c)" class="text-[11px] font-bold uppercase bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-1 rounded-lg">
                      Crear
                    </button>
                  }
                </div>
              }
            </div>
          }
        </div>
      </div>

      <!-- Listado de grupos -->
      <div class="bg-white dark:bg-slate-900 rounded-xl border border-gray-200 dark:border-white/10 overflow-hidden">
        <table class="w-full text-left text-sm">
          <thead class="bg-gray-50 dark:bg-slate-950/60">
            <tr>
              <th class="py-3 px-4 text-[10px] font-black text-slate-500 uppercase">Cliente / Alcance</th>
              <th class="py-3 px-4 text-[10px] font-black text-slate-500 uppercase">Tipo</th>
              <th class="py-3 px-4 text-[10px] font-black text-slate-500 uppercase">Nombre</th>
              <th class="py-3 px-4 text-[10px] font-black text-slate-500 uppercase text-center">Extra</th>
              <th class="py-3 px-4"></th>
            </tr>
          </thead>
          <tbody>
            @for (g of grupos(); track g.id_grupo) {
              <tr class="border-t border-gray-100 dark:border-white/5 hover:bg-gray-50 dark:hover:bg-white/[.02]">
                <td class="py-3 px-4 text-slate-700 dark:text-slate-200 font-semibold">{{ g.cliente_nombre || '—' }}</td>
                <td class="py-3 px-4">
                  <span class="text-[10px] font-bold uppercase px-2 py-1 rounded-full"
                        [class]="g.tipo_grupo === 'encuestador' ? 'bg-violet-100 text-violet-700 dark:bg-violet-950 dark:text-violet-400' : g.tipo_grupo === 'operativo_cliente' ? 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-400' : 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300'">
                    {{ g.tipo_grupo }}
                  </span>
                </td>
                <td class="py-3 px-4 text-slate-500 dark:text-slate-400">{{ g.nombre }}</td>
                <td class="py-3 px-4 text-center text-slate-600 dark:text-slate-300 font-bold">{{ g.extra_count }}</td>
                <td class="py-3 px-4 text-right">
                  <button (click)="verMiembros(g)" class="text-xs font-bold text-indigo-600 dark:text-indigo-400 hover:underline">
                    Ver miembros
                  </button>
                </td>
              </tr>
            }
            @if (grupos().length === 0) {
              <tr><td colspan="5" class="py-8 text-center text-slate-500 text-sm">Cargando...</td></tr>
            }
          </tbody>
        </table>
      </div>

      <!-- Panel de miembros del grupo seleccionado -->
      @if (grupoActivo()) {
        <div class="mt-6 bg-white dark:bg-slate-900 rounded-xl border border-indigo-200 dark:border-indigo-500/30 p-5">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-sm font-bold text-slate-800 dark:text-white">
              Miembros de "{{ grupoActivo().nombre }}"
            </h3>
            <button (click)="grupoActivo.set(null)" class="text-slate-400 hover:text-slate-700 dark:hover:text-white">
              <span class="material-icons !text-lg">close</span>
            </button>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-3 mb-5">
            @for (m of miembros(); track m.id_usuario) {
              <div class="flex items-center justify-between gap-2 bg-slate-50 dark:bg-slate-800 rounded-lg px-3 py-2">
                <div>
                  <div class="text-sm font-semibold text-slate-700 dark:text-slate-200">{{ m.nombre || m.username }}</div>
                  <div class="text-[11px] text-slate-500">{{ m.nombre ? m.username + ' · ' : '' }}{{ m.origen }}</div>
                </div>
                @if (m.origen === 'agregado') {
                  <button (click)="quitarExtra(m)" class="text-[10px] font-bold uppercase text-red-600 dark:text-red-400 hover:underline shrink-0">
                    Quitar
                  </button>
                }
              </div>
            }
            @if (miembros().length === 0) {
              <div class="text-sm text-slate-500 col-span-2 text-center py-4">Sin miembros todavía.</div>
            }
          </div>

          <div class="border-t border-gray-100 dark:border-white/5 pt-4">
            <label class="block text-xs font-bold text-slate-600 dark:text-slate-400 mb-2 uppercase tracking-wide">
              Agregar miembro puntual (para gente que no entra por rol/ruta/cliente)
            </label>
            <div class="relative">
              <input type="text" [(ngModel)]="buscarUsuario" (ngModelChange)="onBuscarUsuario()"
                     placeholder="Buscar por usuario o nombre..."
                     class="w-full max-w-md bg-slate-50 dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg p-2.5 text-sm text-slate-800 dark:text-white outline-none focus:border-indigo-500">
              @if (usuariosResult().length > 0) {
                <div class="absolute z-10 mt-1 w-full max-w-md bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg shadow-xl max-h-56 overflow-y-auto">
                  @for (u of usuariosResult(); track u.id_usuario) {
                    <div class="flex items-center justify-between px-4 py-2.5 hover:bg-gray-50 dark:hover:bg-slate-700 text-sm">
                      <div>
                        <div class="text-slate-700 dark:text-slate-200 font-semibold">{{ u.nombre_real || u.username }}</div>
                        <div class="text-[11px] text-slate-500">{{ u.username }} · {{ u.rol_nombre }}</div>
                      </div>
                      <button (click)="agregarExtra(u)" class="text-[11px] font-bold uppercase bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-1 rounded-lg shrink-0">
                        Agregar
                      </button>
                    </div>
                  }
                </div>
              }
            </div>
          </div>
        </div>
      }
    </div>
  `,
})
export class ChatGruposAdminComponent implements OnInit {
    grupos = signal<any[]>([]);
    grupoActivo = signal<any>(null);
    miembros = signal<any[]>([]);

    buscarCliente = '';
    clientesResult = signal<any[]>([]);

    buscarUsuario = '';
    usuariosResult = signal<any[]>([]);

    constructor(private api: ApiService) { }

    ngOnInit() {
        this.cargarGrupos();
    }

    cargarGrupos() {
        this.api.adminListarGruposChat().subscribe(res => this.grupos.set(res || []));
    }

    onBuscarCliente() {
        const q = this.buscarCliente.trim();
        if (!q) { this.clientesResult.set([]); return; }
        this.api.adminListarClientesParaGrupos(q).subscribe(res => this.clientesResult.set(res || []));
    }

    crearGrupos(c: any) {
        this.api.adminAsegurarGruposCliente(c.id_cliente).subscribe(() => {
            this.buscarCliente = '';
            this.clientesResult.set([]);
            this.cargarGrupos();
        });
    }

    verMiembros(g: any) {
        this.grupoActivo.set(g);
        this.buscarUsuario = '';
        this.usuariosResult.set([]);
        this.api.adminMiembrosGrupo(g.id_grupo).subscribe(res => this.miembros.set(res || []));
    }

    onBuscarUsuario() {
        const q = this.buscarUsuario.trim();
        if (!q) { this.usuariosResult.set([]); return; }
        this.api.adminBuscarUsuarios(q).subscribe(res => this.usuariosResult.set(res || []));
    }

    agregarExtra(u: any) {
        const g = this.grupoActivo();
        if (!g) return;
        this.api.adminAgregarMiembroExtra(g.id_grupo, u.id_usuario).subscribe(() => {
            this.buscarUsuario = '';
            this.usuariosResult.set([]);
            this.verMiembros(g);
            this.cargarGrupos();
        });
    }

    quitarExtra(m: any) {
        const g = this.grupoActivo();
        if (!g) return;
        this.api.adminQuitarMiembroExtra(g.id_grupo, m.id_usuario).subscribe(() => {
            this.verMiembros(g);
            this.cargarGrupos();
        });
    }
}
