import { Component, OnInit, signal, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ApiService } from '../../core/services/api.service';
import { ConfirmService } from '../../shared/components/confirm-dialog/confirm.service';

const ROL_NAMES: Record<number, string> = {
  1: 'Cliente',
  2: 'Analista',
  3: 'Coordinador Exclusivo',
  4: 'Coordinador Tradex',
  5: 'Mercaderista',
  6: 'Supervisor',
  7: 'Auditor',
  8: 'Administrador',
  9: 'Vendedor',
  10: 'Atención al Cliente',
  11: 'Coordinador General',
  12: 'Encuestador',
  13: 'Cliente Encuestador',
  14: 'Auditor de Campo',
  15: 'Ejecutivo de Cuenta'
};

const MODULE_NAMES: Record<string, string> = {
  'dashboard': 'Dashboard General',
  'centro-mando': 'Centro de Mando Gestión',
  'centro-mando-auditoria': 'Centro de Mando Auditoría',
  'plan-accion': 'Plan de Acción',
  'routes': 'Gestión de Rutas',
  'routes.asignar_merc': 'Asignar Mercaderistas',
  'clientes-rutas': 'Clientes · Rutas',
  'frecuencias-pdvs-cliente': 'Frecuencias de PDVs',
  'atencion-cliente': 'Atención al Cliente',
  'products': 'Productos y Catálogos',
  'users': 'Gestión de Usuarios',
  'auditor-campo': 'Auditoría de Campo',
  'auditoria-data': 'Auditoría de Data',
  'encuestador': 'Módulo Encuestadores',
  'encuestador-configuracion': 'Configuración Encuestas',
  'supervisor-encuestadores': 'Supervisor Encuestadores',
  'portal-mercaderista': 'Portal Mercaderista',
  'merc_rutas': 'Mis Rutas Mercaderista',
  'data': 'Data y Balances',
  'chat': 'Chat y Mensajería',
  'auditoria-usuarios': 'Auditoría de Usuarios'
};

export interface ParsedPermission {
  moduleKey: string;
  moduleName: string;
  canRead: boolean;
  canWrite: boolean;
  canDelete: boolean;
  canSeeAll: boolean;
}

export interface DiffItem {
  field: string;
  oldVal: string;
  newVal: string;
  icon: string;
}

export interface GroupedUserAudit {
  targetName: string;
  targetId: string;
  lastAction: string;
  lastTimestamp: string;
  lastModifier: string;
  lastModifierRole: string;
  totalEdits: number;
  latestLog: any;
  allLogs: any[];
}

@Component({
  selector: 'app-auditoria-usuarios',
  standalone: true,
  imports: [
    CommonModule, FormsModule, MatIconModule, MatButtonModule,
    MatProgressSpinnerModule, MatTooltipModule, MatSnackBarModule
  ],
  templateUrl: './auditoria-usuarios.component.html',
  styleUrl: './auditoria-usuarios.component.scss'
})
export class AuditoriaUsuariosComponent implements OnInit {
  loading = signal(true);
  auditLogs = signal<any[]>([]);
  total = signal(0);
  skip = signal(0);
  limit = 50;

  filterAction = '';
  filterEjecutor = '';
  searchText = '';
  fechaInicio = '';
  fechaFin = '';

  viewMode = signal<'grouped' | 'all'>('grouped');
  mainTab = signal<'usuarios' | 'pdvs'>('usuarios');

  // --- PDV AUDIT SIGNALS ---
  selectedLog = signal<any | null>(null);
  pdvLogs = signal<any[]>([]);
  pdvTotal = signal(0);
  pdvSkip = signal(0);
  pdvLimit = 50;
  pdvActionFilter = '';
  pdvSearchText = '';
  pdvStatusFilter = '';
  restoringPdvId = signal<number | null>(null);
  selectedPdvLog = signal<any | null>(null);
  showPdvModal = signal(false);
  selectedUserHistory = signal<GroupedUserAudit | null>(null);
  showModal = signal(false);
  showHistoryModal = signal(false);
  showRawJsonInModal = signal(false);

  // Group audit logs by unique target user
  groupedUserLogs = computed<GroupedUserAudit[]>(() => {
    const logs = this.auditLogs();
    const map = new Map<string, GroupedUserAudit>();

    for (const log of logs) {
      const targetKey = String(log.entity_name || log.entity_id || 'Desconocido');
      if (!map.has(targetKey)) {
        map.set(targetKey, {
          targetName: targetKey,
          targetId: String(log.entity_id || 'N/A'),
          lastAction: log.action,
          lastTimestamp: log.timestamp,
          lastModifier: log.username || 'Sistema',
          lastModifierRole: log.rol || 'N/A',
          totalEdits: 1,
          latestLog: log,
          allLogs: [log]
        });
      } else {
        const item = map.get(targetKey)!;
        item.totalEdits += 1;
        item.allLogs.push(log);
      }
    }

    return Array.from(map.values());
  });

  private api = inject(ApiService);
  private snack = inject(MatSnackBar);
  private confirmSvc = inject(ConfirmService);

  ngOnInit(): void {
    this.loadLogs();
    this.loadPdvLogs();
  }

  loadLogs(): void {
    this.loading.set(true);
    this.api.getAuditoriaUsuarios({
      skip: this.skip(),
      limit: this.limit,
      accion: this.filterAction || undefined,
      ejecutor: this.filterEjecutor || undefined,
      search: this.searchText || undefined,
      fecha_inicio: this.fechaInicio || undefined,
      fecha_fin: this.fechaFin || undefined,
    }).subscribe({
      next: (res) => {
        this.auditLogs.set(res?.data || []);
        this.total.set(res?.total || 0);
        this.loading.set(false);
      },
      error: () => {
        this.auditLogs.set([]);
        this.loading.set(false);
      }
    });
  }

  onFilterChange(): void {
    this.skip.set(0);
    // Auto-switch to detailed list if user typed a search or filter
    if (this.searchText || this.filterAction || this.filterEjecutor) {
      this.viewMode.set('all');
    }
    this.loadLogs();
  }

  resetFilters(): void {
    this.filterAction = '';
    this.filterEjecutor = '';
    this.searchText = '';
    this.fechaInicio = '';
    this.fechaFin = '';
    this.skip.set(0);
    this.loadLogs();
  }

  // --- METODOS DE AUDITORIA DE PDVS ---

  loadPdvLogs(): void {
    this.loading.set(true);
    this.api.getPdvAuditLogs({
      offset: this.pdvSkip(),
      limit: this.pdvLimit,
      action: this.pdvActionFilter || undefined,
      search: this.pdvSearchText || undefined,
      status: this.pdvStatusFilter || undefined,
    }).subscribe({
      next: (res) => {
        this.pdvLogs.set(res?.items || []);
        this.pdvTotal.set(res?.total || 0);
        this.loading.set(false);
      },
      error: (err) => {
        console.error(err);
        this.pdvLogs.set([]);
        this.loading.set(false);
      }
    });
  }

  pdvPage = computed(() => Math.floor(this.pdvSkip() / this.pdvLimit) + 1);
  pdvTotalPages = computed(() => Math.max(1, Math.ceil(this.pdvTotal() / this.pdvLimit)));

  nextPdvPage(): void {
    if (this.pdvSkip() + this.pdvLimit < this.pdvTotal()) {
      this.pdvSkip.set(this.pdvSkip() + this.pdvLimit);
      this.loadPdvLogs();
    }
  }

  prevPdvPage(): void {
    if (this.pdvSkip() > 0) {
      this.pdvSkip.set(Math.max(0, this.pdvSkip() - this.pdvLimit));
      this.loadPdvLogs();
    }
  }

  onPdvLimitChange(limit: number): void {
    this.pdvLimit = +limit;
    this.pdvSkip.set(0);
    this.loadPdvLogs();
  }

  onPdvFilterChange(): void {
    this.pdvSkip.set(0);
    this.loadPdvLogs();
  }

  resetPdvFilters(): void {
    this.pdvActionFilter = '';
    this.pdvSearchText = '';
    this.pdvStatusFilter = '';
    this.pdvSkip.set(0);
    this.loadPdvLogs();
  }

  async restorePdv(log: any): Promise<void> {
    const pdvName = log.entity_name || log.entity_id || 'este registro';
    const isCatalog = (log.action || '').includes('CATALOG');
    const label = isCatalog ? 'el ítem de catálogo' : 'el punto de venta';

    const ok = await this.confirmSvc.confirm(
      `¿Estás seguro de restablecer ${label} "${pdvName}" a su estado original?`,
      {
        title: 'Restablecer Registro',
        confirmText: 'Sí, restablecer',
        cancelText: 'Cancelar',
        danger: false
      }
    );
    if (!ok) return;

    this.restoringPdvId.set(log.id);
    this.api.restorePdvFromAudit(log.id).subscribe({
      next: (res: any) => {
        this.restoringPdvId.set(null);
        this.loadPdvLogs();
        this.snack.open(res?.message || 'Restablecido con éxito', 'OK', { duration: 3000 });
      },
      error: (err) => {
        this.restoringPdvId.set(null);
        this.snack.open(err?.error?.detail || 'Error al restablecer', 'OK', { duration: 4000 });
      }
    });
  }

  approvePdv(log: any): void {
    this.api.approvePdvAudit(log.id).subscribe({
      next: () => {
        this.loadPdvLogs();
      },
      error: (err) => alert('Error al aprobar: ' + (err.error?.detail || err.message))
    });
  }

  openPdvDetailModal(log: any): void {
    this.selectedPdvLog.set(log);
    this.showPdvModal.set(true);
  }

  getPdvDiffItems(log: any): DiffItem[] {
    if (!log || !log.changes) return [];
    const changes = typeof log.changes === 'string' ? JSON.parse(log.changes) : log.changes;
    const before = changes.before || changes.old || {};
    const after = changes.after || changes.new || {};

    const keys = Array.from(new Set([...Object.keys(before), ...Object.keys(after)]));
    const diffs: DiffItem[] = [];

    const labels: Record<string, string> = {
      'nombre': 'Nombre',
      'catalog': 'Tipo de Catálogo',
      'activo': 'Estado Activo',
      'direccion': 'Dirección',
      'latitud': 'Latitud',
      'longitud': 'Longitud',
      'departamento': 'Región / Depto',
      'ciudad': 'Ciudad',
      'localidad': 'Localidad',
      'cadena': 'Cadena / Canal',
      'jerarquia_n2': 'Tipo Negocio',
      'jerarquia_n2_2': 'Subtipo Negocio',
      'radio': 'Radio (m)',
      'tiempo_minimo': 'Tiempo Mínimo',
      'nivel_de_alcance': 'Nivel Alcance',
      'rif': 'RIF'
    };

    for (const k of keys) {
      const oldVal = before[k] !== undefined && before[k] !== null ? String(before[k]) : '—';
      const newVal = after[k] !== undefined && after[k] !== null ? String(after[k]) : '—';

      if (oldVal !== newVal) {
        diffs.push({
          field: labels[k] || k,
          oldVal,
          newVal,
          icon: k === 'catalog' ? 'category' : 'storefront'
        });
      }
    }

    return diffs;
  }

  getPdvActionBadgeClass(action: string): string {
    if (action === 'CREATE_POINT' || action === 'CREATE_CATALOG_ITEM') return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300';
    if (action === 'UPDATE_POINT' || action === 'UPDATE_CATALOG_ITEM') return 'bg-indigo-100 text-indigo-800 dark:bg-indigo-950 dark:text-indigo-300';
    if (action === 'DELETE_POINT' || action === 'DELETE_CATALOG_ITEM') return 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300';
    if (action === 'RESTORE_POINT' || action === 'RESTORE_CATALOG_ITEM') return 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300';
    return 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300';
  }

  getPdvActionLabel(action: string): string {
    if (action === 'CREATE_POINT') return 'Creación de PDV';
    if (action === 'UPDATE_POINT') return 'Edición de PDV';
    if (action === 'DELETE_POINT') return 'Eliminación de PDV';
    if (action === 'RESTORE_POINT') return 'PDV Restablecido';
    if (action === 'CREATE_CATALOG_ITEM') return 'Creación de Catálogo';
    if (action === 'UPDATE_CATALOG_ITEM') return 'Edición de Catálogo';
    if (action === 'DELETE_CATALOG_ITEM') return 'Eliminación de Catálogo';
    if (action === 'RESTORE_CATALOG_ITEM') return 'Catálogo Restablecido';
    return action;
  }

  setViewMode(mode: 'grouped' | 'all'): void {
    this.viewMode.set(mode);
  }

  nextPage(): void {
    if (this.skip() + this.limit < this.total()) {
      this.skip.set(this.skip() + this.limit);
      this.loadLogs();
    }
  }

  prevPage(): void {
    if (this.skip() > 0) {
      this.skip.set(Math.max(0, this.skip() - this.limit));
      this.loadLogs();
    }
  }

  openDetailModal(log: any): void {
    this.selectedLog.set(log);
    this.showRawJsonInModal.set(false);
    this.showModal.set(true);
  }

  closeDetailModal(): void {
    this.showModal.set(false);
    this.selectedLog.set(null);
  }

  openUserHistoryModal(grouped: GroupedUserAudit): void {
    this.selectedUserHistory.set(grouped);
    this.showHistoryModal.set(true);
  }

  closeUserHistoryModal(): void {
    this.showHistoryModal.set(false);
    this.selectedUserHistory.set(null);
  }

  filterByUser(userName: string): void {
    this.searchText = userName;
    this.viewMode.set('all');
    this.onFilterChange();
  }

  toggleRawJson(): void {
    this.showRawJsonInModal.set(!this.showRawJsonInModal());
  }

  getActionBadgeClass(action: string): string {
    switch (action) {
      case 'CREATE_USER':
        return 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800/50';
      case 'UPDATE_USER':
        return 'bg-sky-50 text-sky-700 dark:bg-sky-950/60 dark:text-sky-300 border-sky-200 dark:border-sky-800/50';
      case 'UPDATE_PERMISSIONS':
        return 'bg-purple-50 text-purple-700 dark:bg-purple-950/60 dark:text-purple-300 border-purple-200 dark:border-purple-800/50';
      case 'DELETE_USER':
        return 'bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300 border-rose-200 dark:border-rose-800/50';
      default:
        return 'bg-slate-50 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border-slate-200 dark:border-slate-700';
    }
  }

  getActionIcon(action: string): string {
    switch (action) {
      case 'CREATE_USER': return 'person_add';
      case 'UPDATE_USER': return 'manage_accounts';
      case 'UPDATE_PERMISSIONS': return 'admin_panel_settings';
      case 'DELETE_USER': return 'person_remove';
      default: return 'history';
    }
  }

  getActionLabel(action: string): string {
    switch (action) {
      case 'CREATE_USER': return 'Creación de Usuario';
      case 'UPDATE_USER': return 'Edición de Datos';
      case 'UPDATE_PERMISSIONS': return 'Cambio de Permisos';
      case 'DELETE_USER': return 'Eliminación de Usuario';
      default: return action;
    }
  }

  /** Extrae permisos por módulo */
  extractPermissionsList(changes: any): ParsedPermission[] {
    if (!changes) return [];
    let data = changes;
    if (typeof changes === 'string') {
      try { data = JSON.parse(changes); } catch { return []; }
    }

    let arr: any[] = [];
    if (Array.isArray(data)) {
      arr = data;
    } else if (data && typeof data === 'object') {
      if (Array.isArray(data.new)) arr = data.new;
      else if (Array.isArray(data.permissions)) arr = data.permissions;
      else if (Array.isArray(data.permisos)) arr = data.permisos;
      else if (typeof data.Permissions === 'string') {
        try { arr = JSON.parse(data.Permissions); } catch { }
      }
    }

    if (!Array.isArray(arr)) return [];

    return arr.map(item => {
      const key = item.module || item.clave || 'modulo';
      return {
        moduleKey: key,
        moduleName: MODULE_NAMES[key] || key,
        canRead: !!(item.can_read ?? item.read),
        canWrite: !!(item.can_write ?? item.write),
        canDelete: !!(item.can_delete ?? item.delete),
        canSeeAll: !!(item.can_see_all ?? item.see_all)
      };
    });
  }

  /** Extrae la comparativa Antes vs Después */
  extractDiffItems(log: any): DiffItem[] {
    if (!log || !log.changes) return [];

    let obj = log.changes;
    if (typeof log.changes === 'string') {
      try { obj = JSON.parse(log.changes); } catch {
        return [{ field: 'Detalle', oldVal: '-', newVal: log.changes, icon: 'info' }];
      }
    }

    if (typeof obj !== 'object' || obj === null || Array.isArray(obj)) return [];

    const diffs: DiffItem[] = [];

    const oldObj = obj.old || obj.anterior || obj.old_values || null;
    const newObj = obj.new || obj.nuevo || obj.new_values || obj;

    const sourceObj = (typeof newObj === 'object' && newObj !== null && !Array.isArray(newObj)) ? newObj : obj;

    for (const key of Object.keys(sourceObj)) {
      if (key === 'permissions' || key === 'Permissions' || key === 'permisos' || key === 'old' || key === 'new' || key === 'modified_fields') continue;

      const rawNew = sourceObj[key];
      const rawOld = (oldObj && typeof oldObj === 'object') ? oldObj[key] : null;

      let fieldLabel = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
      let oldValStr = rawOld !== null && rawOld !== undefined ? this.formatFieldValue(key, rawOld) : '(Anterior)';
      let newValStr = this.formatFieldValue(key, rawNew);
      let iconName = 'tune';

      if (key === 'email') {
        fieldLabel = 'Correo Electrónico';
        iconName = 'email';
      } else if (key === 'id_rol') {
        fieldLabel = 'Rol Asignado';
        iconName = 'badge';
      } else if (key === 'activo') {
        fieldLabel = 'Estado de Cuenta';
        iconName = rawNew ? 'check_circle' : 'block';
      } else if (key === 'username') {
        fieldLabel = 'Nombre de Usuario';
        iconName = 'account_circle';
      } else if (key === 'id_perfil') {
        fieldLabel = 'ID Perfil Persona';
        iconName = 'badge';
      }

      if (log.action === 'CREATE_USER') {
        oldValStr = '(Ninguno - Usuario Creado)';
      }

      diffs.push({
        field: fieldLabel,
        oldVal: oldValStr,
        newVal: newValStr,
        icon: iconName
      });
    }

    return diffs;
  }

  formatFieldValue(key: string, val: any): string {
    if (val === null || val === undefined) return 'Sin valor';
    if (key === 'id_rol') {
      return ROL_NAMES[Number(val)] || `Rol #${val}`;
    }
    if (key === 'activo') {
      return (val === true || val === 1) ? 'Activo / Habilitado' : 'Inactivo / Bloqueado';
    }
    if (typeof val === 'object') return JSON.stringify(val);
    return String(val);
  }

  isPermissionChange(log: any): boolean {
    if (log?.action === 'UPDATE_PERMISSIONS') return true;
    const perms = this.extractPermissionsList(log?.changes);
    return perms.length > 0;
  }

  getSummaryLine(log: any): string {
    if (!log) return '';
    if (log.action === 'DELETE_USER') {
      return `Usuario ${log.entity_name || log.entity_id} eliminado del sistema por ${log.username}`;
    }
    if (this.isPermissionChange(log)) {
      const perms = this.extractPermissionsList(log.changes);
      const activeCount = perms.filter(p => p.canRead).length;
      return `Permisos de acceso actualizados (${activeCount} módulos concedidos)`;
    }

    const diffs = this.extractDiffItems(log);
    if (diffs.length === 0) return 'Modificación de usuario registrada';
    return diffs.map(d => `${d.field}: ${d.newVal}`).join(' • ');
  }

  formatJson(obj: any): string {
    if (!obj) return '{}';
    if (typeof obj === 'string') {
      try { return JSON.stringify(JSON.parse(obj), null, 2); } catch { return obj; }
    }
    return JSON.stringify(obj, null, 2);
  }

  mathMin(a: number, b: number): number {
    return Math.min(a, b);
  }
}
