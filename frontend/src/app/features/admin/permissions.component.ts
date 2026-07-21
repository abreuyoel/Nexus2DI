import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ApiService } from '../../core/services/api.service';
import { User } from '../../core/models/user.model';
import { SearchableSelectComponent } from '../../shared/components/searchable-select';
import type { SearchableOption } from '../../shared/components/searchable-select';

interface Modulo { id: number; clave: string; nombre: string; id_padre: number | null; tipo: string; ruta?: string; icono?: string; orden: number; }
interface Perm { can_read: boolean; can_write: boolean; can_delete: boolean; can_see_all: boolean; }

@Component({
  selector: 'app-permissions',
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule, MatProgressSpinnerModule, MatSnackBarModule, SearchableSelectComponent],
  template: `
<div class="min-h-screen bg-white dark:bg-slate-950 text-slate-900 dark:text-white">
  <div class="bg-gradient-to-r from-slate-50 to-white dark:from-slate-900 dark:to-slate-800 border-b border-slate-200 dark:border-white/5 px-8 py-6">
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
      <div class="flex items-center gap-3">
        <app-searchable-select
          [options]="userOptions()"
          [value]="selectedUserId"
          [placeholder]="'— Selecciona un usuario —'"
          [searchPlaceholder]="'Buscar por usuario o rol...'"
          [clearable]="true"
          [label]="'Usuario'"
          (valueChange)="onUserChange($event)"
          class="min-w-64">
        </app-searchable-select>
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
      <div class="grid grid-cols-[1fr_90px_90px_90px_90px] gap-2 px-4 py-2 text-[10px] font-black text-slate-500 uppercase tracking-widest sticky top-0 bg-white dark:bg-slate-950 z-10">
        <span>Módulo / Botón</span><span class="text-center">Lectura</span><span class="text-center">Modificar</span><span class="text-center">Eliminar</span><span class="text-center">Ver todo</span>
      </div>
      @for (root of roots(); track root.id) {
        <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/5 rounded-2xl mb-3 overflow-hidden">
          <!-- fila del módulo raíz -->
          <div class="grid grid-cols-[1fr_90px_90px_90px_90px] gap-2 items-center px-4 py-3 bg-slate-50 dark:bg-slate-800/60 border-b border-slate-100 dark:border-white/5">
            <div class="flex items-center gap-2 font-bold">
              @if (root.icono) { <mat-icon class="!text-base text-violet-500 dark:text-violet-400">{{ root.icono }}</mat-icon> }
              {{ root.nombre }}
              <button (click)="setModulo(root, true)" class="ml-2 text-[10px] px-2 py-0.5 rounded-full bg-violet-100 dark:bg-violet-950 text-violet-700 dark:text-violet-300 font-bold">Todo</button>
              <button (click)="setModulo(root, false)" class="text-[10px] px-2 py-0.5 rounded-full bg-slate-200 dark:bg-slate-800 text-slate-500 dark:text-slate-400 font-bold">Nada</button>
            </div>
            <span class="text-center"><input type="checkbox" [(ngModel)]="perms[root.clave].can_read" class="w-5 h-5 accent-violet-600"></span>
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
              <span class="text-center"><input type="checkbox" [(ngModel)]="perms[h.clave].can_read" class="w-5 h-5 accent-violet-600"></span>
              <span class="text-center"><input type="checkbox" [(ngModel)]="perms[h.clave].can_write" class="w-5 h-5 accent-violet-600"></span>
              <span class="text-center"><input type="checkbox" [(ngModel)]="perms[h.clave].can_delete" class="w-5 h-5 accent-violet-600"></span>
              <span class="text-center text-slate-400 dark:text-slate-600">—</span>
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

  userOptions = computed<SearchableOption<number>[]>(() =>
    this.users().map(u => ({
      value: u.id,
      label: u.username,
      secondary: u.rol,
      icon: 'person',
    }))
  );
  saving = signal(false);
  loading = signal(false);
  perms: Record<string, Perm> = {};

  roots = computed(() => this.modulos().filter(m => !m.id_padre).sort((a, b) => a.orden - b.orden));

  constructor(private api: ApiService, private snack: MatSnackBar) { }

  ngOnInit(): void {
    this.api.getUsers().subscribe(u => this.users.set(u));
    this.api.getModulos().subscribe(m => { this.modulos.set(m); this.ensurePerms(); });
  }

  hijos(idPadre: number): Modulo[] {
    return this.modulos().filter(m => m.id_padre === idPadre).sort((a, b) => a.orden - b.orden);
  }

  private ensurePerms() {
    for (const m of this.modulos()) {
      if (!this.perms[m.clave]) this.perms[m.clave] = { can_read: false, can_write: false, can_delete: false, can_see_all: false };
    }
  }

  onUserChange(userId: number | null) {
    this.selectedUserId = userId;
    // reset
    this.perms = {};
    this.ensurePerms();
    if (!userId) return;
    this.loading.set(true);
    this.api.getUserPermissions(userId).subscribe({
      next: (list: any[]) => {
        for (const p of list) {
          this.perms[p.module] = {
            can_read: !!p.can_read, can_write: !!p.can_write,
            can_delete: !!p.can_delete, can_see_all: !!p.can_see_all,
          };
        }
        this.ensurePerms();
        this.loading.set(false);
      },
      error: () => { this.loading.set(false); },
    });
  }

  setModulo(root: Modulo, val: boolean) {
    const apply = (clave: string) => {
      const p = this.perms[clave];
      p.can_read = val; p.can_write = val; p.can_delete = val;
    };
    apply(root.clave);
    for (const h of this.hijos(root.id)) apply(h.clave);
  }

  save() {
    if (!this.selectedUserId) return;
    this.saving.set(true);
    const permissions = this.modulos().map(m => ({
      module: m.clave,
      can_read: this.perms[m.clave].can_read,
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
