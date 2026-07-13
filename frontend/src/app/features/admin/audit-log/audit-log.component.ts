import { Component, OnInit, signal } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { ApiService } from '../../../core/services/api.service';

export interface AuditEntry {
  id: number;
  timestamp: string;
  user_id: number;
  username: string;
  rol: string;
  ip_address: string;
  action: string;
  entity_type: string;
  entity_id: string;
  entity_name: string;
  changes: string | null;
  status: string;
}

@Component({
  selector: 'app-audit-log',
  standalone: true,
  imports: [
    CommonModule, FormsModule, MatTableModule, MatButtonModule, MatIconModule,
    MatFormFieldModule, MatInputModule, MatSelectModule,
    MatProgressSpinnerModule, MatTooltipModule, DatePipe,
  ],
  templateUrl: './audit-log.component.html',
})
export class AuditLogComponent implements OnInit {
  loading = signal(false);
  entries = signal<AuditEntry[]>([]);
  total = signal(0);
  expandedId = signal<number | null>(null);

  columns = ['timestamp', 'username', 'action', 'entity_type', 'entity_name', 'ip_address', 'status', 'expand'];

  entityTypes: string[] = [];
  filters = { username: '', action: '', entity_type: '', from_date: '', to_date: '' };
  limit = 100;
  offset = 0;

  ACTION_COLORS: Record<string, string> = {
    LOGIN: 'bg-emerald-50 text-emerald-700',
    LOGOUT: 'bg-slate-100 text-slate-600',
    LOGIN_FAILED: 'bg-rose-50 text-rose-600',
    CHANGE_PASSWORD: 'bg-amber-50 text-amber-700',
    CREATE_USER: 'bg-blue-50 text-blue-700',
    DELETE_USER: 'bg-rose-50 text-rose-700',
    UPDATE_USER: 'bg-indigo-50 text-indigo-700',
    UPDATE_PERMISSIONS: 'bg-purple-50 text-purple-700',
    CREATE_POINT: 'bg-teal-50 text-teal-700',
    UPDATE_POINT: 'bg-cyan-50 text-cyan-700',
    DELETE_POINT: 'bg-rose-50 text-rose-700',
    CREATE_PRODUCT: 'bg-lime-50 text-lime-700',
    UPDATE_PRODUCT: 'bg-yellow-50 text-yellow-700',
    DELETE_PRODUCT: 'bg-rose-50 text-rose-700',
    APPROVE_PHOTOS: 'bg-emerald-50 text-emerald-700',
    REJECT_PHOTO: 'bg-orange-50 text-orange-700',
    REPLACE_PHOTO: 'bg-sky-50 text-sky-700',
    KILL_SESSION: 'bg-rose-50 text-rose-700',
    KILL_ALL_SESSIONS: 'bg-rose-100 text-rose-800',
  };

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.getAuditEntityTypes().subscribe({ next: (t) => (this.entityTypes = t as string[]) });
    this.load();
  }

  load(): void {
    this.loading.set(true);
    // Eliminar campos vacíos: si el backend recibe from_date="" intenta parsear
    // a datetime y devuelve 422. Solo enviamos los filtros con valor real.
    const cleanFilters: Record<string, string> = {};
    for (const [k, v] of Object.entries(this.filters)) {
      if (v && String(v).trim() !== '') cleanFilters[k] = v;
    }
    this.api.getAuditLogs({ ...cleanFilters, limit: this.limit, offset: this.offset }).subscribe({
      next: (res: any) => {
        this.entries.set(res.items);
        this.total.set(res.total);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  applyFilters(): void {
    this.offset = 0;
    this.load();
  }

  clearFilters(): void {
    this.filters = { username: '', action: '', entity_type: '', from_date: '', to_date: '' };
    this.offset = 0;
    this.load();
  }

  prevPage(): void { this.offset = Math.max(0, this.offset - this.limit); this.load(); }
  nextPage(): void { this.offset += this.limit; this.load(); }

  get currentPage(): number { return Math.floor(this.offset / this.limit) + 1; }
  get totalPages(): number { return Math.ceil(this.total() / this.limit); }
  get showingEnd(): number { return Math.min(this.offset + this.limit, this.total()); }

  toggleExpand(id: number): void {
    this.expandedId.set(this.expandedId() === id ? null : id);
  }

  actionClass(action: string): string {
    return (this.ACTION_COLORS[action] ?? 'bg-slate-100 text-slate-600') + ' px-2.5 py-1 rounded-lg text-xs font-bold uppercase tracking-wider';
  }

  formatChanges(raw: string | null): string {
    if (!raw) return '—';
    try { return JSON.stringify(JSON.parse(raw), null, 2); }
    catch { return raw; }
  }
}
