import { Component, Inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormsModule } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Subject, debounceTime, distinctUntilChanged, switchMap, of } from 'rxjs';
import { ApiService } from '../../core/services/api.service';
import { Ruta } from '../../core/models/ruta.model';

interface DayPriority { dia: string; prioridad: string; }
interface EditorRow { point: any; days: DayPriority[]; prioridad: string; dayChecks: Record<string, boolean>; }

@Component({
  selector: 'app-route-detail-dialog',
  standalone: true,
  imports: [
    CommonModule, ReactiveFormsModule, FormsModule,
    MatDialogModule, MatButtonModule, MatIconModule,
    MatProgressSpinnerModule, MatTooltipModule
  ],
  templateUrl: './route-detail-dialog.component.html',
  styles: []
})
export class RouteDetailDialogComponent implements OnInit {
  ruta!: Ruta;
  tipo = 'T';                       // E | T | A (derivado del nombre)
  clients = signal<any[]>([]);
  routePoints = signal<any[]>([]);
  futureChanges = signal<any[]>([]);

  activeTab = signal<'masivo' | 'points' | 'changes'>('masivo');
  editingRoute = signal(false);
  savingRoute = signal(false);

  // ── Editor Masivo ─────────────────────────────────────────
  pointResults = signal<any[]>([]);
  pointSearchText = signal('');
  searchingPoints = signal(false);
  selectedPoint: any = null;
  editorRows = signal<EditorRow[]>([]);
  savingBulk = signal(false);
  clientSearch = '';
  selectedClientIds = signal<number[]>([]);   // tradex/auditoría
  private pointSearch$ = new Subject<string>();

  // ── Puntos Actuales ───────────────────────────────────────
  selectedProgIds = signal<Set<number>>(new Set());

  dias = [
    { v: 'Lunes', l: 'Lunes' }, { v: 'Martes', l: 'Martes' },
    { v: 'Miercoles', l: 'Miércoles' }, { v: 'Jueves', l: 'Jueves' },
    { v: 'Viernes', l: 'Viernes' }, { v: 'Sabado', l: 'Sábado' },
    { v: 'Domingo', l: 'Domingo' }
  ];

  editRouteForm = this.fb.group({
    cuadrante: [''], servicio: [''],
    coordinador_1: [''], coordinador_2: ['']
  });

  constructor(
    public dialogRef: MatDialogRef<RouteDetailDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { ruta: Ruta; startEdit?: boolean },
    private api: ApiService,
    private fb: FormBuilder,
    private snack: MatSnackBar
  ) { }

  ngOnInit(): void {
    this.ruta = { ...this.data.ruta };
    if (this.data.startEdit) this.editingRoute.set(true);

    // Derivar tipo de "Ruta E1" / "Ruta T12" / "Ruta A2"
    const n = this.ruta.nombre ?? '';
    if (n.startsWith('Ruta ') && n.length > 5 && ['E', 'T', 'A'].includes(n[5])) this.tipo = n[5];

    this.editRouteForm.patchValue({
      cuadrante: this.ruta.cuadrante ?? '',
      servicio: this.ruta.servicio ?? '',
      coordinador_1: this.ruta.coordinador_1 ?? '',
      coordinador_2: this.ruta.coordinador_2 ?? ''
    });

    this.api.getClients().subscribe((d: any) => {
      this.clients.set(d ?? []);
      // Exclusiva: cliente bloqueado al cliente exclusivo de la ruta
      if (this.isExclusiva && this.ruta.id_cliente_exclusivo) {
        this.selectedClientIds.set([Number(this.ruta.id_cliente_exclusivo)]);
      }
    });
    this.loadRoutePoints();

    this.pointSearch$.pipe(
      debounceTime(300),
      distinctUntilChanged(),
      switchMap(term => {
        if (!term || term.length < 2) { this.pointResults.set([]); this.searchingPoints.set(false); return of({ items: [], total: 0 }); }
        this.searchingPoints.set(true);
        return this.api.getPoints({ search: term, limit: 30 });
      })
    ).subscribe({
      next: (res: { items: any[]; total: number }) => { this.pointResults.set(res.items); this.searchingPoints.set(false); },
      error: () => this.searchingPoints.set(false)
    });
  }

  get isExclusiva(): boolean { return this.tipo === 'E'; }
  get isTradex(): boolean { return this.tipo === 'T'; }

  get exclusiveClientName(): string {
    return this.ruta.cliente_exclusivo_nombre
      ?? this.clients().find(c => c.id === Number(this.ruta.id_cliente_exclusivo))?.nombre
      ?? '—';
  }

  get filteredClients(): any[] {
    const s = this.clientSearch.trim().toLowerCase();
    return this.clients().filter(c => !s || c.nombre?.toLowerCase().includes(s));
  }

  // ── Tabs / route edit ─────────────────────────────────────
  loadTab(tab: 'masivo' | 'points' | 'changes'): void {
    this.activeTab.set(tab);
    if (tab === 'changes') this.api.getFutureChanges(this.ruta.id).subscribe(d => this.futureChanges.set(d));
    if (tab === 'points') this.loadRoutePoints();
  }

  saveRoute(): void {
    this.savingRoute.set(true);
    this.api.updateRoute(this.ruta.id, this.editRouteForm.value).subscribe({
      next: (updated) => {
        this.ruta = { ...this.ruta, ...updated };
        this.savingRoute.set(false);
        this.editingRoute.set(false);
        this.snack.open('Ruta actualizada', 'OK', { duration: 3000 });
      },
      error: () => this.savingRoute.set(false)
    });
  }

  // ── Clientes (selección) ──────────────────────────────────
  isClientSelected(id: number): boolean { return this.selectedClientIds().includes(id); }
  toggleClient(id: number): void {
    if (this.isExclusiva) return; // bloqueado
    this.selectedClientIds.update(list => list.includes(id) ? list.filter(x => x !== id) : [...list, id]);
  }

  // ── Búsqueda de puntos ────────────────────────────────────
  onPointSearch(term: string): void {
    this.pointSearchText.set(term);
    this.selectedPoint = null;
    this.pointSearch$.next(term);
  }
  selectPoint(p: any): void {
    this.selectedPoint = p;
    this.pointSearchText.set(p.nombre ?? '');
    this.pointResults.set([]);
  }
  addPointToEditor(): void {
    if (!this.selectedPoint) return;
    if (this.editorRows().some(r => r.point.id === this.selectedPoint.id)) {
      this.snack.open('Ese punto ya está en el editor', 'OK', { duration: 2500 });
      return;
    }
    this.editorRows.update(rows => [...rows, {
      point: this.selectedPoint,
      days: [],
      prioridad: 'Media',
      dayChecks: {}
    }]);
    this.selectedPoint = null;
    this.pointSearchText.set('');
  }
  removeEditorRow(idx: number): void {
    this.editorRows.update(rows => rows.filter((_, i) => i !== idx));
  }

  // Agrega los días marcados con la prioridad elegida (misma prioridad a varios días)
  addDaysToRow(idx: number): void {
    this.editorRows.update(rows => rows.map((r, i) => {
      if (i !== idx) return r;
      const checked = this.dias.filter(d => r.dayChecks[d.v]).map(d => d.v);
      if (checked.length === 0) return r;
      const days = [...r.days];
      for (const dia of checked) {
        const existing = days.find(d => d.dia === dia);
        if (existing) existing.prioridad = r.prioridad;
        else days.push({ dia, prioridad: r.prioridad });
      }
      return { ...r, days, dayChecks: {} };
    }));
  }
  removeDay(idx: number, dia: string): void {
    this.editorRows.update(rows => rows.map((r, i) =>
      i === idx ? { ...r, days: r.days.filter(d => d.dia !== dia) } : r));
  }
  dayLabel(v: string): string { return this.dias.find(d => d.v === v)?.l ?? v; }

  get canSaveBulk(): boolean {
    return this.selectedClientIds().length > 0 &&
      this.editorRows().length > 0 &&
      this.editorRows().some(r => r.days.length > 0);
  }

  saveBulk(): void {
    if (!this.canSaveBulk) {
      this.snack.open('Selecciona cliente(s), punto(s) y al menos un día', 'OK', { duration: 3500 });
      return;
    }
    const inserts: any[] = [];
    for (const row of this.editorRows()) {
      for (const cid of this.selectedClientIds()) {
        for (const dp of row.days) {
          inserts.push({ point_id: row.point.id, client_id: cid, dia: dp.dia, prioridad: dp.prioridad });
        }
      }
    }
    if (inserts.length === 0) return;
    this.savingBulk.set(true);
    this.api.bulkApply(this.ruta.id, { inserts }).subscribe({
      next: (res) => {
        this.savingBulk.set(false);
        this.editorRows.set([]);
        this.loadRoutePoints();
        this.snack.open(res?.message ?? 'Cambios guardados', 'OK', { duration: 4000 });
      },
      error: (err) => {
        this.savingBulk.set(false);
        this.snack.open(err.error?.detail ?? 'Error al guardar', 'OK', { duration: 4000 });
      }
    });
  }

  // ── Puntos Actuales ───────────────────────────────────────
  loadRoutePoints(): void {
    this.api.getRoutePoints(this.ruta.id, true).subscribe(d => {
      this.routePoints.set(d);
      // Exclusiva sin cliente exclusivo definido: inferirlo de los puntos existentes
      if (this.isExclusiva && this.selectedClientIds().length === 0) {
        const cid = d.find((x: any) => x.cliente?.id)?.cliente?.id;
        if (cid) this.selectedClientIds.set([cid]);
      }
    });
  }

  toggleActive(p: any): void {
    const nuevo = !p.activo;
    this.api.setPointActive(p.id, nuevo).subscribe({
      next: () => {
        this.routePoints.update(list => list.map(x => x.id === p.id ? { ...x, activo: nuevo } : x));
      },
      error: () => this.snack.open('No se pudo cambiar el estado', 'OK', { duration: 3000 })
    });
  }

  removePoint(point: any): void {
    if (!confirm('¿Eliminar este punto de la ruta?')) return;
    this.api.removePointFromRoute(point.id).subscribe({
      next: () => { this.loadRoutePoints(); this.snack.open('Punto eliminado', 'OK', { duration: 3000 }); }
    });
  }

  isProgSelected(id: number): boolean { return this.selectedProgIds().has(id); }
  toggleProgSelected(id: number): void {
    this.selectedProgIds.update(set => {
      const s = new Set(set);
      s.has(id) ? s.delete(id) : s.add(id);
      return s;
    });
  }
  get selectedCount(): number { return this.selectedProgIds().size; }

  // ── Borrado: helper genérico + 4 modos ────────────────────
  private deleteByIds(ids: number[], msg: string): void {
    if (ids.length === 0) return;
    this.api.bulkApply(this.ruta.id, { deletes: ids.map(id => ({ programacion_id: id })) }).subscribe({
      next: (res) => {
        this.selectedProgIds.set(new Set());
        this.loadRoutePoints();
        this.snack.open(res?.message ?? msg, 'OK', { duration: 3500 });
      },
      error: () => this.snack.open('Error al eliminar', 'OK', { duration: 3000 })
    });
  }

  bulkDelete(): void {
    const ids = [...this.selectedProgIds()];
    if (ids.length === 0) return;
    if (!confirm(`¿Eliminar ${ids.length} punto(s) seleccionado(s)?`)) return;
    this.deleteByIds(ids, 'Puntos eliminados');
  }

  // Eliminar un PDV en TODOS sus días (todas las programaciones de ese punto)
  deletePdvAllDays(p: any): void {
    const pid = p.punto?.id ?? p.punto_id;
    const ids = this.routePoints().filter(x => (x.punto?.id ?? x.punto_id) === pid).map(x => x.id);
    if (!confirm(`¿Eliminar "${p.punto?.nombre || p.punto_interes_nombre}" de TODOS los días (${ids.length})?`)) return;
    this.deleteByIds(ids, 'PDV eliminado de todos los días');
  }

  // Eliminar todos los PDV de un día
  bulkDeleteDay = '';
  applyDeleteDay(): void {
    if (!this.bulkDeleteDay) return;
    const ids = this.routePoints().filter(x => x.dia === this.bulkDeleteDay).map(x => x.id);
    if (ids.length === 0) { this.snack.open('No hay puntos ese día', 'OK', { duration: 2500 }); return; }
    if (!confirm(`¿Eliminar los ${ids.length} punto(s) del día ${this.dayLabel(this.bulkDeleteDay)}?`)) return;
    this.deleteByIds(ids, `Puntos del ${this.dayLabel(this.bulkDeleteDay)} eliminados`);
    this.bulkDeleteDay = '';
  }

  // Eliminar TODOS los PDV de la ruta
  deleteAllRoute(): void {
    const ids = this.routePoints().map(x => x.id);
    if (ids.length === 0) return;
    if (!confirm(`¿Eliminar TODOS los ${ids.length} puntos de la ruta? Esta acción no se puede deshacer.`)) return;
    this.deleteByIds(ids, 'Todos los puntos eliminados');
  }

  // ── Programar cambio futuro (modal) ───────────────────────
  futureModalOpen = signal(false);
  futurePoint: any = null;
  futureForm: Record<string, any> = {};

  openFutureModal(p: any): void {
    this.futurePoint = p;
    this.futureForm = {
      fecha_ejecucion: '',
      tipo_cambio: 'modificacion',
      dia: p.dia ?? 'Lunes',
      prioridad: p.prioridad ?? 'Media',
      activa: true,
      observaciones: '',
    };
    this.futureModalOpen.set(true);
  }
  closeFutureModal(): void { this.futureModalOpen.set(false); this.futurePoint = null; }

  savingFuture = signal(false);
  saveFutureChange(): void {
    if (!this.futureForm['fecha_ejecucion']) {
      this.snack.open('La fecha de ejecución es obligatoria', 'OK', { duration: 3000 });
      return;
    }
    const p = this.futurePoint;
    const payload = {
      id_programacion: p.id,
      id_punto_interes: p.punto?.id ?? p.punto_id,
      punto_interes_nombre: p.punto?.nombre ?? p.punto_interes_nombre,
      id_cliente: p.cliente?.id,
      cliente_nombre: p.cliente?.nombre,
      dia: this.futureForm['dia'],
      prioridad: this.futureForm['prioridad'],
      tipo_cambio: this.futureForm['tipo_cambio'],
      fecha_ejecucion: this.futureForm['fecha_ejecucion'],
      observaciones: this.futureForm['observaciones'],
    };
    this.savingFuture.set(true);
    this.api.scheduleChange(this.ruta.id, payload).subscribe({
      next: () => {
        this.savingFuture.set(false);
        this.closeFutureModal();
        this.api.getFutureChanges(this.ruta.id).subscribe(d => this.futureChanges.set(d));
        this.snack.open('Cambio futuro programado', 'OK', { duration: 3000 });
      },
      error: () => { this.savingFuture.set(false); this.snack.open('No se pudo programar', 'OK', { duration: 3000 }); }
    });
  }

  // ── Helpers de estilo ─────────────────────────────────────
  getPriorityClass(p: string): string {
    switch (p) {
      case 'Alta': return 'bg-red-950 text-red-400 border border-red-900';
      case 'Media': return 'bg-amber-950 text-amber-400 border border-amber-900';
      case 'Baja': return 'bg-sky-950 text-sky-400 border border-sky-900';
      default: return 'bg-slate-800 text-slate-400';
    }
  }
  getChangeBadge(c: any): string {
    if (c.estado === 'pendiente' || !c.estado) return 'bg-amber-950 text-amber-400';
    if (c.estado === 'ejecutado') return 'bg-emerald-950 text-emerald-400';
    return 'bg-slate-800 text-slate-400';
  }
}
