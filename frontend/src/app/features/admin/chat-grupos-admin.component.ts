import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';

@Component({
  selector: 'app-chat-grupos-admin',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="p-6 max-w-6xl mx-auto space-y-6">
      <!-- Encabezado -->
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div class="flex items-center gap-2 mb-1">
            <span class="material-icons text-indigo-500 dark:text-indigo-400 !text-3xl">forum</span>
            <h1 class="text-2xl font-bold text-slate-800 dark:text-white">Grupos de Chat</h1>
          </div>
          <p class="text-slate-500 dark:text-slate-400 text-sm">
            La membresía de cada grupo se calcula dinámicamente por ruta, rol o cliente. Gestión y control de miembros adicionales.
          </p>
        </div>
      </div>

      <!-- Crear grupos para un cliente nuevo -->
      <div class="bg-white dark:bg-slate-900 rounded-xl border border-gray-200 dark:border-white/10 p-5">
        <h3 class="text-sm font-bold text-slate-700 dark:text-slate-300 mb-1">Crear grupos para un cliente</h3>
        <p class="text-xs text-slate-500 dark:text-slate-400 mb-3">
          Normalmente los grupos se crean solos al asignar rutas. Use esta opción para aprovisionar por adelantado.
        </p>
        <div class="relative">
          <input type="text" [(ngModel)]="buscarCliente" (ngModelChange)="onBuscarCliente()"
                 placeholder="Buscar cliente..."
                 class="w-full max-w-md bg-slate-50 dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg p-2.5 text-sm text-slate-800 dark:text-white outline-none focus:border-indigo-500">
          @if (clientesResult().length > 0) {
            <div class="absolute z-10 mt-1 w-full max-w-md bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg shadow-xl max-h-56 overflow-y-auto divide-y divide-slate-100 dark:divide-slate-700/50">
              @for (c of clientesResult(); track c.id_cliente) {
                <div class="flex items-center justify-between px-4 py-2.5 hover:bg-gray-50 dark:hover:bg-slate-700 text-sm">
                  <span class="text-slate-700 dark:text-slate-200 font-medium">{{ c.cliente }}</span>
                  @if (c.grupos_completos) {
                    <span class="text-[10px] font-bold uppercase text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60 px-2 py-0.5 rounded">Ya tiene grupos</span>
                  } @else {
                    <button (click)="crearGrupos(c)" class="text-[11px] font-bold uppercase bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-1 rounded-lg transition-colors">
                      Crear
                    </button>
                  }
                </div>
              }
            </div>
          }
        </div>
      </div>

      <!-- Listado de grupos con Buscador Destacado y Paginación -->
      <div class="bg-white dark:bg-slate-900 rounded-xl border border-gray-200 dark:border-white/10 overflow-hidden shadow-sm">
        <!-- Buscador Destacado Principal -->
        <div class="p-4 bg-slate-50/90 dark:bg-slate-950/60 border-b border-gray-200 dark:border-slate-800 flex flex-col md:flex-row items-center justify-between gap-4">
          <div class="relative w-full md:w-1/2">
            <span class="material-icons absolute left-3.5 top-3 text-indigo-500 dark:text-indigo-400 !text-xl">search</span>
            <input type="text" [(ngModel)]="searchGrupoInput" (ngModelChange)="onSearchGrupoChange()"
                   placeholder="🔍 Buscar grupo por cliente, nombre o tipo..."
                   class="w-full bg-white dark:bg-slate-800 border-2 border-indigo-200 dark:border-indigo-500/40 rounded-xl pl-11 pr-10 py-2.5 text-sm font-medium text-slate-800 dark:text-white outline-none focus:border-indigo-600 focus:ring-4 focus:ring-indigo-500/20 shadow-sm transition-all">
            @if (searchGrupoInput) {
              <button (click)="limpiarBusquedaGrupo()" class="absolute right-3 top-2.5 text-slate-400 hover:text-slate-700 dark:hover:text-white p-0.5 rounded-full hover:bg-slate-100 dark:hover:bg-slate-700">
                <span class="material-icons !text-lg">clear</span>
              </button>
            }
          </div>
          <div class="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400 font-medium">
            @if (searchGrupoInput.trim()) {
              <span class="bg-indigo-100 dark:bg-indigo-950/80 text-indigo-700 dark:text-indigo-300 font-bold px-2.5 py-1 rounded-lg flex items-center gap-1">
                <span class="material-icons !text-sm">filter_alt</span>
                Filtrando: "{{ searchGrupoInput.trim() }}"
              </span>
            }
            <span>Mostrando <strong>{{ grupos().length }}</strong> de <strong>{{ totalGrupos() }}</strong> grupos</span>
          </div>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left text-sm">
            <thead class="bg-gray-50 dark:bg-slate-950/60">
              <tr>
                <th class="py-3 px-4 text-[10px] font-black text-slate-500 uppercase tracking-wider">Cliente / Alcance</th>
                <th class="py-3 px-4 text-[10px] font-black text-slate-500 uppercase tracking-wider">Tipo</th>
                <th class="py-3 px-4 text-[10px] font-black text-slate-500 uppercase tracking-wider">Nombre del Grupo</th>
                <th class="py-3 px-4 text-[10px] font-black text-slate-500 uppercase tracking-wider text-center">Miembros Totales</th>
                <th class="py-3 px-4 text-[10px] font-black text-slate-500 uppercase tracking-wider text-center">Extras</th>
                <th class="py-3 px-4 text-right text-[10px] font-black text-slate-500 uppercase tracking-wider">Acción</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100 dark:divide-white/5">
              @for (g of grupos(); track g.id_grupo) {
                <tr class="hover:bg-gray-50/80 dark:hover:bg-white/[.02] transition-colors">
                  <td class="py-3 px-4 text-slate-800 dark:text-slate-200 font-semibold">{{ g.cliente_nombre || '—' }}</td>
                  <td class="py-3 px-4">
                    <span class="text-[10px] font-bold uppercase px-2.5 py-1 rounded-full"
                          [class]="g.tipo_grupo === 'encuestador' ? 'bg-violet-100 text-violet-700 dark:bg-violet-950 dark:text-violet-400' : g.tipo_grupo === 'operativo_cliente' ? 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-400' : 'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-400'">
                      {{ g.tipo_grupo }}
                    </span>
                  </td>
                  <td class="py-3 px-4 text-slate-600 dark:text-slate-300 font-medium">{{ g.nombre }}</td>
                  <td class="py-3 px-4 text-center">
                    <span class="inline-flex items-center gap-1 font-bold text-xs bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 px-2.5 py-1 rounded-full">
                      <span class="material-icons !text-sm">people</span>
                      {{ g.miembros_count ?? g.extra_count }}
                    </span>
                  </td>
                  <td class="py-3 px-4 text-center text-slate-500 font-medium">{{ g.extra_count }}</td>
                  <td class="py-3 px-4 text-right">
                    <button (click)="abrirModalMiembros(g)"
                            class="inline-flex items-center gap-1 text-xs font-bold bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-1.5 rounded-lg shadow-sm transition-all">
                      <span class="material-icons !text-sm">visibility</span>
                      Ver miembros
                    </button>
                  </td>
                </tr>
              }
              @if (loadingGrupos()) {
                <tr><td colspan="6" class="py-12 text-center text-slate-400 text-sm">Cargando grupos...</td></tr>
              } @else if (grupos().length === 0) {
                <tr><td colspan="6" class="py-12 text-center text-slate-400 text-sm">No se encontraron grupos.</td></tr>
              }
            </tbody>
          </table>
        </div>

        <!-- Paginación de Grupos -->
        @if (totalGrupos() > 0) {
          <div class="px-4 py-3 bg-gray-50/50 dark:bg-slate-950/40 border-t border-gray-100 dark:border-white/5 flex items-center justify-between text-xs text-slate-500">
            <div>
              Página <strong>{{ pageGrupo() }}</strong> de <strong>{{ totalPagesGrupo() }}</strong>
            </div>
            <div class="flex items-center gap-2">
              <button (click)="changePageGrupo(-1)" [disabled]="pageGrupo() <= 1"
                      class="px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors font-medium">
                Anterior
              </button>
              <button (click)="changePageGrupo(1)" [disabled]="pageGrupo() >= totalPagesGrupo()"
                      class="px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors font-medium">
                Siguiente
              </button>
            </div>
          </div>
        }
      </div>

      <!-- MODAL DE MIEMBROS CON BUSCADOR Y PAGINACIÓN -->
      @if (modalMiembrosOpen()) {
        <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm animate-fade-in"
             (click)="cerrarModalMiembros()">
          <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl w-full max-w-3xl overflow-hidden flex flex-col max-h-[90vh]"
               (click)="$event.stopPropagation()">
            
            <!-- Modal Header -->
            <div class="p-5 border-b border-gray-100 dark:border-slate-800 flex items-center justify-between bg-slate-50/80 dark:bg-slate-950/50">
              <div>
                <div class="flex items-center gap-2">
                  <span class="material-icons text-indigo-500 !text-xl">group</span>
                  <h3 class="text-base font-bold text-slate-800 dark:text-white">
                    Miembros de "{{ grupoActivo()?.nombre }}"
                  </h3>
                </div>
                <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Total: <strong class="text-indigo-600 dark:text-indigo-400">{{ todosLosMiembros().length }} miembros</strong>
                  ({{ miembrosFiltrados().length }} coincidentes con la búsqueda)
                </p>
              </div>
              <button (click)="cerrarModalMiembros()" class="p-1 text-slate-400 hover:text-slate-700 dark:hover:text-white rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
                <span class="material-icons !text-xl">close</span>
              </button>
            </div>

            <!-- Modal Content / Body -->
            <div class="p-5 overflow-y-auto flex-grow space-y-4">
              <!-- Buscador de Miembros dentro del Modal -->
              <div class="relative">
                <span class="material-icons absolute left-3.5 top-2.5 text-indigo-500 dark:text-indigo-400 !text-lg">search</span>
                <input type="text" [ngModel]="searchMiembroQuery()" (ngModelChange)="onSearchMiembroChange($event)"
                       placeholder="🔍 Filtrar por nombre, usuario, cédula..."
                       class="w-full bg-slate-50 dark:bg-slate-800 border-2 border-indigo-200 dark:border-indigo-500/40 rounded-xl pl-10 pr-9 py-2 text-xs font-semibold text-slate-800 dark:text-white outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-500/20 transition-all">
                @if (searchMiembroQuery()) {
                  <button (click)="limpiarBusquedaMiembro()" class="absolute right-3 top-2 text-slate-400 hover:text-slate-700 dark:hover:text-white p-0.5 rounded-full">
                    <span class="material-icons !text-base">clear</span>
                  </button>
                }
              </div>

              <!-- Lista de Miembros Paginada -->
              @if (loadingMiembros()) {
                <div class="py-12 text-center text-slate-400 text-xs">Cargando miembros del grupo...</div>
              } @else {
                <div class="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                  @for (m of miembrosPaginados(); track m.id_usuario) {
                    <div class="flex items-center justify-between gap-3 bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-700/50 rounded-xl p-3">
                      <div class="flex items-center gap-2.5 min-w-0">
                        <div class="w-8 h-8 rounded-full bg-indigo-100 dark:bg-indigo-950/80 text-indigo-600 dark:text-indigo-300 flex items-center justify-center font-bold text-xs shrink-0">
                          {{ (m.nombre || m.username || 'U').charAt(0).toUpperCase() }}
                        </div>
                        <div class="min-w-0">
                          <div class="text-xs font-semibold text-slate-800 dark:text-slate-200 truncate">{{ m.nombre || m.username }}</div>
                          <div class="text-[10px] text-slate-400 truncate">
                            {{ m.nombre ? m.username + ' · ' : '' }}
                            <span class="font-medium text-indigo-500 uppercase">{{ m.origen }}</span>
                          </div>
                        </div>
                      </div>
                      @if (m.origen === 'agregado') {
                        <button (click)="quitarExtra(m)" class="text-[10px] font-bold uppercase text-red-600 hover:text-red-700 dark:text-red-400 bg-red-50 dark:bg-red-950/50 px-2 py-1 rounded-md hover:bg-red-100 transition-colors shrink-0">
                          Quitar
                        </button>
                      }
                    </div>
                  }
                  @if (miembrosFiltrados().length === 0) {
                    <div class="text-xs text-slate-400 col-span-2 text-center py-8">
                      No se encontraron miembros con ese filtro.
                    </div>
                  }
                </div>
              }

              <!-- Paginación de Miembros en Modal -->
              @if (miembrosFiltrados().length > limitMiembro) {
                <div class="pt-2 flex items-center justify-between text-xs text-slate-500 border-t border-slate-100 dark:border-slate-800">
                  <div>
                    Página <strong>{{ pageMiembro() }}</strong> de <strong>{{ totalPagesMiembro() }}</strong>
                  </div>
                  <div class="flex items-center gap-2">
                    <button (click)="changePageMiembro(-1)" [disabled]="pageMiembro() <= 1"
                            class="px-2.5 py-1 rounded-md border border-slate-200 dark:border-slate-700 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-100 dark:hover:bg-slate-800 text-xs">
                      Anterior
                    </button>
                    <button (click)="changePageMiembro(1)" [disabled]="pageMiembro() >= totalPagesMiembro()"
                            class="px-2.5 py-1 rounded-md border border-slate-200 dark:border-slate-700 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-100 dark:hover:bg-slate-800 text-xs">
                      Siguiente
                    </button>
                  </div>
                </div>
              }

              <!-- Sección para agregar miembro adicional -->
              <div class="border-t border-slate-100 dark:border-slate-800 pt-4 mt-2">
                <label class="block text-[11px] font-bold text-slate-600 dark:text-slate-400 mb-1.5 uppercase tracking-wider">
                  Agregar miembro puntual
                </label>
                <div class="relative">
                  <input type="text" [(ngModel)]="buscarUsuario" (ngModelChange)="onBuscarUsuario()"
                         placeholder="Buscar usuario por username o nombre real..."
                         class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-2.5 text-xs text-slate-800 dark:text-white outline-none focus:border-indigo-500">
                  @if (usuariosResult().length > 0) {
                    <div class="absolute z-20 bottom-full mb-1 w-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-2xl max-h-48 overflow-y-auto divide-y divide-slate-100 dark:divide-slate-700/50">
                      @for (u of usuariosResult(); track u.id_usuario) {
                        <div class="flex items-center justify-between px-3.5 py-2 hover:bg-gray-50 dark:hover:bg-slate-700/80 text-xs">
                          <div>
                            <div class="text-slate-800 dark:text-slate-200 font-semibold">{{ u.nombre_real || u.username }}</div>
                            <div class="text-[10px] text-slate-400">{{ u.username }} · {{ u.rol_nombre }}</div>
                          </div>
                          <button (click)="agregarExtra(u)" class="text-[10px] font-bold uppercase bg-indigo-600 hover:bg-indigo-700 text-white px-2.5 py-1 rounded-lg shrink-0">
                            Agregar
                          </button>
                        </div>
                      }
                    </div>
                  }
                </div>
              </div>
            </div>

            <!-- Modal Footer -->
            <div class="p-4 bg-slate-50/80 dark:bg-slate-950/50 border-t border-gray-100 dark:border-slate-800 flex justify-end">
              <button (click)="cerrarModalMiembros()" class="px-4 py-2 bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-bold rounded-xl transition-colors">
                Cerrar
              </button>
            </div>

          </div>
        </div>
      }
    </div>
  `,
})
export class ChatGruposAdminComponent implements OnInit {
  // Paginación y búsqueda de Grupos
  grupos = signal<any[]>([]);
  totalGrupos = signal<number>(0);
  pageGrupo = signal<number>(1);
  limitGrupo = 10;
  searchGrupoInput = '';
  loadingGrupos = signal<boolean>(false);

  // Modal de Miembros
  modalMiembrosOpen = signal<boolean>(false);
  grupoActivo = signal<any>(null);
  todosLosMiembros = signal<any[]>([]);
  loadingMiembros = signal<boolean>(false);

  // Buscador y Paginación dentro del Modal de Miembros
  searchMiembroQuery = signal<string>('');
  pageMiembro = signal<number>(1);
  limitMiembro = 8;

  // Búsqueda de clientes para crear grupos
  buscarCliente = '';
  clientesResult = signal<any[]>([]);

  // Búsqueda de usuarios para agregar como miembro extra
  buscarUsuario = '';
  usuariosResult = signal<any[]>([]);

  // Miembros filtrados y ordenados dinámicamente según la búsqueda en el modal
  miembrosFiltrados = computed(() => {
    const q = this.searchMiembroQuery().trim().toLowerCase();
    const list = this.todosLosMiembros();
    if (!q) return list;

    const filtered = list.filter((m) =>
      String(m.id_usuario || '').toLowerCase().includes(q) ||
      String(m.nombre || '').toLowerCase().includes(q) ||
      String(m.username || '').toLowerCase().includes(q) ||
      String(m.origen || '').toLowerCase().includes(q)
    );

    // Priorizar coincidencias exactas y prefijos al inicio de la lista
    return filtered.sort((a, b) => {
      const aUser = String(a.username || '').toLowerCase();
      const bUser = String(b.username || '').toLowerCase();
      const aNom = String(a.nombre || '').toLowerCase();
      const bNom = String(b.nombre || '').toLowerCase();
      const aId = String(a.id_usuario || '');
      const bId = String(b.id_usuario || '');

      const aExact = aUser === q || aNom === q || aId === q;
      const bExact = bUser === q || bId === q || bNom === q;
      if (aExact && !bExact) return -1;
      if (!aExact && bExact) return 1;

      const aStart = aUser.startsWith(q) || aNom.startsWith(q) || aId.startsWith(q);
      const bStart = bUser.startsWith(q) || bNom.startsWith(q) || bId.startsWith(q);
      if (aStart && !bStart) return -1;
      if (!aStart && bStart) return 1;

      return 0;
    });
  });

  // Miembros paginados para la vista del modal
  miembrosPaginados = computed(() => {
    const list = this.miembrosFiltrados();
    const page = this.pageMiembro();
    const start = (page - 1) * this.limitMiembro;
    return list.slice(start, start + this.limitMiembro);
  });

  totalPagesGrupo = computed(() => Math.ceil(this.totalGrupos() / this.limitGrupo) || 1);
  totalPagesMiembro = computed(() => Math.ceil(this.miembrosFiltrados().length / this.limitMiembro) || 1);

  constructor(private api: ApiService) {}

  ngOnInit() {
    this.cargarGrupos();
  }

  cargarGrupos() {
    this.loadingGrupos.set(true);
    this.api.adminListarGruposChat(this.searchGrupoInput.trim(), this.pageGrupo(), this.limitGrupo).subscribe({
      next: (res) => {
        if (res && res.items !== undefined) {
          this.grupos.set(res.items || []);
          this.totalGrupos.set(res.total || 0);
        } else {
          this.grupos.set(res || []);
          this.totalGrupos.set((res || []).length);
        }
        this.loadingGrupos.set(false);
      },
      error: () => this.loadingGrupos.set(false),
    });
  }

  onSearchGrupoChange() {
    this.pageGrupo.set(1);
    this.cargarGrupos();
  }

  limpiarBusquedaGrupo() {
    this.searchGrupoInput = '';
    this.pageGrupo.set(1);
    this.cargarGrupos();
  }

  changePageGrupo(delta: number) {
    const newPage = this.pageGrupo() + delta;
    if (newPage >= 1 && newPage <= this.totalPagesGrupo()) {
      this.pageGrupo.set(newPage);
      this.cargarGrupos();
    }
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

  // Abrir Modal de Miembros
  abrirModalMiembros(g: any) {
    this.grupoActivo.set(g);
    this.searchMiembroQuery.set('');
    this.pageMiembro.set(1);
    this.buscarUsuario = '';
    this.usuariosResult.set([]);
    this.modalMiembrosOpen.set(true);
    this.loadingMiembros.set(true);

    this.api.adminMiembrosGrupo(g.id_grupo).subscribe({
      next: (res) => {
        this.todosLosMiembros.set(res || []);
        this.loadingMiembros.set(false);
      },
      error: () => this.loadingMiembros.set(false),
    });
  }

  cerrarModalMiembros() {
    this.modalMiembrosOpen.set(false);
    this.grupoActivo.set(null);
  }

  onSearchMiembroChange(val: string) {
    this.searchMiembroQuery.set(val || '');
    this.pageMiembro.set(1);
  }

  limpiarBusquedaMiembro() {
    this.searchMiembroQuery.set('');
    this.pageMiembro.set(1);
  }

  changePageMiembro(delta: number) {
    const newPage = this.pageMiembro() + delta;
    if (newPage >= 1 && newPage <= this.totalPagesMiembro()) {
      this.pageMiembro.set(newPage);
    }
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
      this.recarregarMiembros(g.id_grupo);
    });
  }

  quitarExtra(m: any) {
    const g = this.grupoActivo();
    if (!g) return;
    this.api.adminQuitarMiembroExtra(g.id_grupo, m.id_usuario).subscribe(() => {
      this.recarregarMiembros(g.id_grupo);
    });
  }

  private recarregarMiembros(idGrupo: number) {
    this.api.adminMiembrosGrupo(idGrupo).subscribe(res => {
      this.todosLosMiembros.set(res || []);
      this.cargarGrupos();
    });
  }
}
