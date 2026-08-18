import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ApiService } from '../../core/services/api.service';
import { User } from '../../core/models/user.model';
import { SearchableSelectComponent, SelectOption } from '../client-visits/searchable-select.component';

interface Modulo { id: number; clave: string; nombre: string; id_padre: number | null; tipo: string; ruta?: string; icono?: string; orden: number; }
interface Perm { state: 'inherit' | 'allow' | 'deny'; can_write: boolean; can_delete: boolean; can_see_all: boolean; }

@Component({
  selector: 'app-permissions',
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule, MatProgressSpinnerModule, MatSnackBarModule, SearchableSelectComponent],
  template: `
<div class="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white">
  <div class="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-white/8 px-8 py-6">
    <div class="flex items-center justify-between gap-4 flex-wrap">
      <div class="flex items-center gap-4">
        <div class="w-12 h-12 rounded-2xl bg-gradient-to-br from-violet-600 to-purple-700 flex items-center justify-center shadow-lg shrink-0">
          <mat-icon class="text-white">admin_panel_settings</mat-icon>
        </div>
        <div>
          <h1 class="text-2xl font-black tracking-tight leading-none">Panel de Control de Accesos</h1>
          <p class="text-slate-500 dark:text-slate-400 text-sm mt-0.5">Permisos por usuario para cada módulo y botón del sistema</p>
        </div>
      </div>
      <div class="flex items-center gap-3 flex-wrap">
        <div class="w-52 sm:w-60">
          <app-searchable-select [options]="roleOptions()" [value]="roleFilterStr"
            (valueChange)="onRoleFilterChange($event)" placeholder="Todos los roles"
            searchPlaceholder="Buscar rol..." allLabel="Todos los roles" icon="group" align="right"></app-searchable-select>
        </div>
        <div class="w-64 sm:w-80">
          <app-searchable-select [options]="userOptions()" [value]="selectedUserStr"
            (valueChange)="onUserSelectChange($event)"
            (searchChange)="onUserSearch($event)"
            placeholder="— Selecciona un usuario ({{ filteredUsers().length }}) —"
            searchPlaceholder="Buscar usuario..." allLabel="Seleccionar usuario..." icon="person" align="right"></app-searchable-select>
        </div>
        <button (click)="save()" [disabled]="!selectedUserId || saving()"
          class="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-violet-700 to-purple-700 hover:from-violet-600 hover:to-purple-600 disabled:opacity-50 rounded-xl font-black text-sm shadow-lg">
          @if (saving()) { <mat-spinner diameter="16"></mat-spinner> } @else { <mat-icon class="!text-base">save</mat-icon> }
          Guardar
        </button>
      </div>
    </div>
  </div>

  <div class="px-8 py-6 max-w-5xl">
    @if (!selectedUserId) {
      <div class="flex flex-col items-center justify-center py-32 text-slate-400 dark:text-slate-600 gap-3">
        <mat-icon class="!text-5xl">manage_accounts</mat-icon>
        <p class="font-bold">Selecciona un usuario para configurar sus permisos</p>
      </div>
    } @else if (loading()) {
      <div class="flex justify-center py-24"><mat-spinner diameter="40"></mat-spinner></div>
    } @else {
      <!-- Encabezado de columnas -->
      <div class="grid grid-cols-[1fr_90px_90px_90px_90px] gap-2 px-4 py-2 text-[10px] font-black text-slate-500 uppercase tracking-widest sticky top-0 bg-slate-50 dark:bg-slate-950 z-10">
        <span>Módulo / Botón</span><span class="text-center">Lectura</span><span class="text-center">Modificar</span><span class="text-center">Eliminar</span><span class="text-center">Ver todo</span>
      </div>
      @for (root of roots(); track root.id) {
        <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/8 rounded-2xl mb-3 overflow-hidden">
          <!-- fila del módulo raíz -->
          <div class="grid grid-cols-[1fr_90px_90px_90px_90px] gap-2 items-center px-4 py-3 bg-slate-50 dark:bg-slate-800/60 border-b border-slate-100 dark:border-white/5">
            <div class="flex items-center gap-2 font-bold flex-wrap">
              @if (root.icono) { <mat-icon class="!text-base text-violet-400">{{ root.icono }}</mat-icon> }
              {{ root.nombre }}
              <button (click)="setModulo(root, 'allow')" class="ml-2 text-[10px] px-2 py-0.5 rounded-full bg-violet-950 text-violet-300 font-bold">Permitir Todo</button>
              <button (click)="setModulo(root, 'inherit')" class="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 font-bold">Heredar Todo</button>
            </div>
            <span class="text-center">
              <select [(ngModel)]="perms[root.clave].state" class="bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-white text-xs rounded p-1 outline-none w-full appearance-none text-center">
                <option value="inherit" class="text-slate-500">Heredar</option>
                <option value="allow" class="text-emerald-500">Permitir</option>
                <option value="deny" class="text-rose-500">Denegar</option>
              </select>
            </span>
            <span class="text-center"><input type="checkbox" [(ngModel)]="perms[root.clave].can_write" class="w-5 h-5 accent-violet-600"></span>
            <span class="text-center"><input type="checkbox" [(ngModel)]="perms[root.clave].can_delete" class="w-5 h-5 accent-violet-600"></span>
            <span class="text-center"><input type="checkbox" [(ngModel)]="perms[root.clave].can_see_all" class="w-5 h-5 accent-amber-500"></span>
          </div>
          <!-- acciones/botones hijos -->
          @for (h of hijos(root.id); track h.id) {
            <div class="grid grid-cols-[1fr_90px_90px_90px_90px] gap-2 items-center px-4 py-2.5 border-b border-slate-100 dark:border-white/5 last:border-0">
              <div class="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300 pl-6">
                <mat-icon class="!text-sm text-slate-400 dark:text-slate-600">subdirectory_arrow_right</mat-icon>{{ h.nombre }}
              </div>
              <span class="text-center">
                <select [(ngModel)]="perms[h.clave].state" class="bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-white text-xs rounded p-1 outline-none w-full appearance-none text-center">
                  <option value="inherit" class="text-slate-500">Heredar</option>
                  <option value="allow" class="text-emerald-500">Permitir</option>
                  <option value="deny" class="text-rose-500">Denegar</option>
                </select>
              </span>
              <span class="text-center"><input type="checkbox" [(ngModel)]="perms[h.clave].can_write" class="w-5 h-5 accent-violet-600"></span>
              <span class="text-center"><input type="checkbox" [(ngModel)]="perms[h.clave].can_delete" class="w-5 h-5 accent-violet-600"></span>
              <span class="text-center text-slate-400 dark:text-slate-700">—</span>
            </div>
          }
        </div>
      }
    }
  </div>
</div>
  `,
})
export class PermissionsComponent implements OnInit {
  users = signal<User[]>([]);
  modulos = signal<Modulo[]>([]);
  selectedUserId: number | null = null;
  saving = signal(false);
  loading = signal(false);
  perms: Record<string, Perm> = {};

  roleFilter = signal<string | null>(null);
  roleFilterStr = '';
  selectedUserStr = '';

  readonly systemRoles = [
    { code: 'admin', label: 'Administrador', id: 8 },
    { code: 'analyst', label: 'Analista', id: 2 },
    { code: 'supervisor', label: 'Supervisor', id: 6 },
    { code: 'coordinador_exclusivo', label: 'Coordinador Exclusivo', id: 3 },
    { code: 'coordinador_tradex', label: 'Coordinador Tradex', id: 4 },
    { code: 'coordinador_general', label: 'Coordinador General', id: 11 },
    { code: 'atc', label: 'Atención al Cliente', id: 10 },
    { code: 'vendedor', label: 'Vendedor', id: 9 },
    { code: 'client', label: 'Cliente', id: 1 },
    { code: 'mercaderista', label: 'Mercaderista', id: 5 },
    { code: 'auditor', label: 'Auditor', id: 7 },
    { code: 'auditor_campo', label: 'Auditor de Campo', id: 14 },
    { code: 'encuestador', label: 'Encuestador', id: 12 },
    { code: 'cliente_encuestador', label: 'Cliente Encuestador', id: 13 },
    { code: 'ejecutivo_cuenta', label: 'Ejecutivo de Cuenta', id: 15 },
  ];

  roleOptions = computed<SelectOption[]>(() => {
    const options: SelectOption[] = this.systemRoles.map(r => ({
      value: r.code,
      label: r.label
    }));
    
    const knownCodes = new Set(this.systemRoles.map(r => r.code));
    const knownLabels = new Set(this.systemRoles.map(r => r.label));
    
    for (const u of this.users()) {
      const rVal = u.rol || u.rol_nombre || (u.id_rol ? String(u.id_rol) : '');
      if (rVal && !knownCodes.has(rVal) && !knownLabels.has(rVal)) {
        options.push({ value: rVal, label: u.rol_nombre || rVal });
        knownCodes.add(rVal);
      }
    }
    
    return options.sort((a, b) => a.label.localeCompare(b.label));
  });

  filteredUsers = computed(() => {
    const rf = this.roleFilter();
    const list = this.users();
    if (!rf) return list;
    
    const matchedSysRole = this.systemRoles.find(r => r.code === rf || r.label === rf || String(r.id) === rf);
    
    return list.filter(u => {
      if (u.rol === rf || u.rol_nombre === rf || String(u.id_rol) === rf) return true;
      if (matchedSysRole) {
        return u.rol === matchedSysRole.code ||
               u.rol_nombre === matchedSysRole.label ||
               u.id_rol === matchedSysRole.id;
      }
      return false;
    });
  });

  userOptions = computed<SelectOption[]>(() =>
    this.filteredUsers().map((u: any) => {
      const roleLabel = (u as any).rol_nombre ||
        this.systemRoles.find(r => r.code === (u as any).rol || r.id === u.id_rol)?.label ||
        (u as any).rol || '';
      return { value: String(u.id), label: `${u.username} (${roleLabel})` };
    })
  );

  roots = computed(() => this.modulos().filter(m => !m.id_padre).sort((a, b) => a.orden - b.orden));

  userSearchTerm = '';
  private searchTimeout: any = null;

  constructor(private api: ApiService, private snack: MatSnackBar) { }

  ngOnInit(): void {
    // No cargamos usuarios en ngOnInit — lazy load cuando el usuario interactúa con el selector
    this.api.getModulos().subscribe(m => { this.modulos.set(m); this.ensurePerms(); });
  }

  loadUsers(search?: string, role?: string | null): void {
    const r = role || undefined;
    // Usa el endpoint slim: sin JOINs, 10x más rápido que /api/users
    this.api.getUsersSlim(300, search, r).subscribe({
      next: (newUsers: any[]) => {
        const currentSelectedId = this.selectedUserId;
        if (currentSelectedId) {
          const selUser = this.users().find((u: any) => u.id === currentSelectedId);
          if (selUser && !newUsers.some((u: any) => u.id === currentSelectedId)) {
            newUsers.unshift(selUser);
          }
        }
        this.users.set(newUsers as any);
      },
      error: (err) => console.error('Error cargando usuarios:', err)
    });
  }

  onUserSearch(term: string): void {
    this.userSearchTerm = term;
    if (this.searchTimeout) clearTimeout(this.searchTimeout);
    this.searchTimeout = setTimeout(() => {
      this.loadUsers(term, this.roleFilter());
    }, 250);
  }

  hijos(idPadre: number): Modulo[] {
    return this.modulos().filter(m => m.id_padre === idPadre).sort((a, b) => a.orden - b.orden);
  }

  private ensurePerms() {
    for (const m of this.modulos()) {
      if (!this.perms[m.clave]) this.perms[m.clave] = { state: 'inherit', can_write: false, can_delete: false, can_see_all: false };
    }
  }

  onRoleFilterChange(val: string): void {
    this.roleFilterStr = val;
    this.roleFilter.set(val || null);
    this.loadUsers(this.userSearchTerm, val || null);
  }

  onUserSelectChange(val: string): void {
    const id = val ? +val : null;
    this.selectedUserId = id;
    this.selectedUserStr = val;
    this.onUserChange(id);
  }

  onUserChange(userId: number | null) {
    // reset
    this.perms = {};
    this.ensurePerms();
    if (!userId) return;
    this.loading.set(true);
    this.api.getUserPermissions(userId).subscribe({
      next: (list: any[]) => {
        for (const p of list) {
          this.perms[p.module] = {
            state: p.can_read ? 'allow' : 'deny',
            can_write: !!p.can_write,
            can_delete: !!p.can_delete,
            can_see_all: !!p.can_see_all,
          };
        }
        this.ensurePerms();
        this.loading.set(false);
      },
      error: () => { this.loading.set(false); },
    });
  }

  setModulo(root: Modulo, val: 'inherit' | 'allow' | 'deny') {
    const apply = (clave: string) => {
      const p = this.perms[clave];
      p.state = val;
      p.can_write = val === 'allow';
      p.can_delete = val === 'allow';
    };
    apply(root.clave);
    for (const h of this.hijos(root.id)) apply(h.clave);
  }

  save() {
    if (!this.selectedUserId) return;
    this.saving.set(true);
    const permissions = this.modulos()
      .filter(m => this.perms[m.clave].state !== 'inherit')
      .map(m => ({
        module: m.clave,
        can_read: this.perms[m.clave].state === 'allow',
        can_write: this.perms[m.clave].can_write,
        can_delete: this.perms[m.clave].can_delete,
        can_see_all: this.perms[m.clave].can_see_all,
      }));
    this.api.updateUserPermissions(this.selectedUserId, permissions).subscribe({
      next: () => { this.saving.set(false); this.snack.open('Permisos guardados', 'OK', { duration: 2500 }); },
      error: () => { this.saving.set(false); this.snack.open('Error al guardar', 'OK', { duration: 3000 }); },
    });
  }
}
