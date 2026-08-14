import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ApiService } from '../../core/services/api.service';
import { ConfirmService } from '../../shared/components/confirm-dialog/confirm.service';
import { SearchableSelectComponent, SelectOption } from '../client-visits/searchable-select.component';

const FRECUENCIA_HINTS: { valor: number; texto: string }[] = [
  { valor: 5, texto: '5 = 5 días a la semana' },
  { valor: 3, texto: '3 = 3 días a la semana' },
  { valor: 1, texto: '1 = 1 vez a la semana (4/mes)' },
  { valor: 0.5, texto: '0.5 = 2 veces al mes' },
  { valor: 0.25, texto: '0.25 = 1 vez al mes' },
];

@Component({
  selector: 'app-frecuencias-pdvs-cliente',
  standalone: true,
  imports: [CommonModule, FormsModule, MatButtonModule, MatIconModule, MatProgressSpinnerModule, MatSnackBarModule, SearchableSelectComponent],
  templateUrl: './frecuencias-pdvs-cliente.component.html',
  styleUrls: ['./frecuencias-pdvs-cliente.component.scss'],
})
export class FrecuenciasPdvsClienteComponent implements OnInit {
  readonly frecuenciaHints = FRECUENCIA_HINTS;
  Math = Math;

  loading = signal(true);
  saving = signal(false);
  registros = signal<any[]>([]);
  clientes = signal<any[]>([]);
  pdvs = signal<any[]>([]);

  filtroCliente = signal<number | null>(null);
  filtroActivo = signal<string>('');

  showForm = signal(false);
  editing = signal<any>(null);
  pdvFiltro = signal('');

  form = {
    id_cliente: null as number | null,
    id_punto_interes: '' as string,
    frecuencia_semanal: null as number | null,
    observaciones: '',
    activo: true,
  };

  // --- Options para selects searchables ---
  clienteOptions = computed<SelectOption[]>(() =>
    this.clientes().map((c) => ({ value: String(c.id), label: c.nombre }))
  );
  estadoOptions: SelectOption[] = [
    { value: 'true', label: 'Activo' },
    { value: 'false', label: 'Inactivo' },
  ];

  get filtroClienteStr(): string { return this.filtroCliente() != null ? String(this.filtroCliente()) : ''; }
  onFiltroClienteChange(val: string): void { this.filtroCliente.set(val ? +val : null); this.cargar(); }
  get filtroActivoStr(): string { return this.filtroActivo(); }
  onFiltroActivoChange(val: string): void { this.filtroActivo.set(val); this.cargar(); }

  // Form: cliente + PDV
  get formClienteStr(): string { return this.form.id_cliente != null ? String(this.form.id_cliente) : ''; }
  onFormClienteChange(val: string): void { this.form.id_cliente = val ? +val : null; }

  pdvsFiltrados = computed(() => {
    const f = this.pdvFiltro().trim().toLowerCase();
    const list = this.pdvs();
    if (!f) return list.slice(0, 100);
    return list.filter(p => (p.nombre || '').toLowerCase().includes(f) || (p.id || '').toLowerCase().includes(f)).slice(0, 100);
  });
  pdvOptions = computed<SelectOption[]>(() =>
    this.pdvsFiltrados().map(p => ({ value: String(p.id), label: `${p.nombre} (${p.id})` }))
  );
  get formPdvStr(): string { return this.form.id_punto_interes ? String(this.form.id_punto_interes) : ''; }
  onFormPdvChange(val: string): void { this.form.id_punto_interes = val; }

  // --- Paginación client-side — tabla de registros ---
  registrosPage = signal(0);
  registrosPageSize = signal(20);
  paginatedRegistros = computed<any[]>(() => {
    const size = this.registrosPageSize();
    const start = this.registrosPage() * size;
    return this.registros().slice(start, start + size);
  });
  get totalRegistroPages(): number { return Math.max(1, Math.ceil(this.registros().length / this.registrosPageSize())); }
  get registroRangeLabel(): string {
    const total = this.registros().length;
    if (!total) return 'Mostrando 0–0 de 0';
    const start = this.registrosPage() * this.registrosPageSize() + 1;
    const end = Math.min((this.registrosPage() + 1) * this.registrosPageSize(), total);
    return `Mostrando ${start}–${end} de ${total}`;
  }
  goRegistroPage(p: number): void { this.registrosPage.set(p); }
  onRegistroPageSizeChange(val: number): void { this.registrosPageSize.set(val); this.registrosPage.set(0); }

  // --- Carga masiva: cliente -> PDVs únicos de su programación de ruta ---
  showBulk = signal(false);
  bulkCliente: number | null = null;
  bulkLoading = signal(false);
  bulkSaving = signal(false);
  bulkPdvs = signal<{ id_punto_interes: string; pdv_nombre: string; id_frecuencia: number | null; frecuencia_semanal: number | null; observaciones: string | null }[]>([]);
  bulkAplicarTodos: number | null = null;

  bulkPendientesCount = computed(() => this.bulkPdvs().filter(p => p.frecuencia_semanal != null).length);

  get bulkClienteStr(): string { return this.bulkCliente != null ? String(this.bulkCliente) : ''; }

  // --- Paginación client-side — tabla de carga masiva ---
  bulkPage = signal(0);
  bulkPageSize = signal(20);
  paginatedBulkPdvs = computed(() => {
    const size = this.bulkPageSize();
    const start = this.bulkPage() * size;
    return this.bulkPdvs().slice(start, start + size);
  });
  get totalBulkPages(): number { return Math.max(1, Math.ceil(this.bulkPdvs().length / this.bulkPageSize())); }
  get bulkRangeLabel(): string {
    const total = this.bulkPdvs().length;
    if (!total) return 'Mostrando 0–0 de 0';
    const start = this.bulkPage() * this.bulkPageSize() + 1;
    const end = Math.min((this.bulkPage() + 1) * this.bulkPageSize(), total);
    return `Mostrando ${start}–${end} de ${total}`;
  }
  goBulkPage(p: number): void { this.bulkPage.set(p); }
  onBulkPageSizeChange(val: number): void { this.bulkPageSize.set(val); this.bulkPage.set(0); }

  constructor(private api: ApiService, private snack: MatSnackBar, private confirmSvc: ConfirmService) { }

  ngOnInit(): void {
    this.cargar();
    this.api.getClients().subscribe({ next: d => this.clientes.set(d), error: () => { } });
    this.api.getPDVList().subscribe({ next: d => this.pdvs.set(d), error: () => { } });
  }

  cargar(): void {
    this.loading.set(true);
    this.registrosPage.set(0);
    const opts: any = {};
    if (this.filtroCliente() != null) opts.id_cliente = this.filtroCliente();
    if (this.filtroActivo() !== '') opts.activo = this.filtroActivo() === 'true';
    this.api.getFrecuenciasPdvsCliente(opts).subscribe({
      next: d => { this.registros.set(d); this.loading.set(false); },
      error: () => { this.loading.set(false); this.snack.open('Error al cargar', 'OK', { duration: 3000 }); },
    });
  }

  clienteNombre(id: number): string {
    return this.clientes().find(c => c.id === id)?.nombre || '';
  }

  openCreate(): void {
    this.showBulk.set(false);
    this.editing.set(null);
    this.form = { id_cliente: null, id_punto_interes: '', frecuencia_semanal: null, observaciones: '', activo: true };
    this.pdvFiltro.set('');
    this.showForm.set(true);
  }

  openEdit(r: any): void {
    this.editing.set(r);
    this.form = {
      id_cliente: r.id_cliente, id_punto_interes: r.id_punto_interes,
      frecuencia_semanal: r.frecuencia_semanal, observaciones: r.observaciones || '', activo: r.activo,
    };
    this.pdvFiltro.set(r.pdv_nombre || r.id_punto_interes || '');
    this.showForm.set(true);
  }

  cancelar(): void {
    this.showForm.set(false);
    this.editing.set(null);
  }

  guardar(): void {
    if (!this.form.id_cliente || !this.form.id_punto_interes || this.form.frecuencia_semanal == null) {
      this.snack.open('Cliente, PDV y frecuencia son requeridos', 'OK', { duration: 3000 });
      return;
    }
    this.saving.set(true);
    const editing = this.editing();
    const req = editing
      ? this.api.updateFrecuenciaPdvCliente(editing.id, this.form)
      : this.api.createFrecuenciaPdvCliente(this.form);
    req.subscribe({
      next: () => {
        this.saving.set(false);
        this.showForm.set(false);
        this.editing.set(null);
        this.snack.open(editing ? 'Registro modificado' : 'Registro creado', 'OK', { duration: 2500 });
        this.cargar();
      },
      error: (err) => {
        this.saving.set(false);
        this.snack.open(err?.error?.detail || 'Error al guardar', 'OK', { duration: 3000 });
      },
    });
  }

  abrirBulk(): void {
    this.showForm.set(false);
    this.bulkCliente = null;
    this.bulkPdvs.set([]);
    this.bulkAplicarTodos = null;
    this.bulkPage.set(0);
    this.showBulk.set(true);
  }

  cancelarBulk(): void {
    this.showBulk.set(false);
  }

  onBulkClienteChange(val: string): void {
    this.bulkCliente = val ? +val : null;
    this.bulkPdvs.set([]);
    this.bulkPage.set(0);
    if (this.bulkCliente == null) return;
    this.bulkLoading.set(true);
    this.api.getPdvsDisponiblesParaFrecuencia(this.bulkCliente).subscribe({
      next: d => { this.bulkPdvs.set(d); this.bulkLoading.set(false); },
      error: () => { this.bulkLoading.set(false); this.snack.open('Error al cargar los PDVs del cliente', 'OK', { duration: 3000 }); },
    });
  }

  aplicarATodos(): void {
    if (this.bulkAplicarTodos == null) return;
    const valor = this.bulkAplicarTodos;
    this.bulkPdvs.update(list => list.map(p => ({ ...p, frecuencia_semanal: valor })));
  }

  guardarBulk(): void {
    const cliente = this.bulkCliente;
    if (!cliente) return;
    const items = this.bulkPdvs()
      .filter(p => p.frecuencia_semanal != null)
      .map(p => ({ id_punto_interes: p.id_punto_interes, frecuencia_semanal: p.frecuencia_semanal, observaciones: p.observaciones }));
    if (!items.length) {
      this.snack.open('Asigna al menos una frecuencia antes de guardar', 'OK', { duration: 3000 });
      return;
    }
    this.bulkSaving.set(true);
    this.api.bulkUpsertFrecuenciasPdvCliente({ id_cliente: cliente, items }).subscribe({
      next: (res) => {
        this.bulkSaving.set(false);
        this.showBulk.set(false);
        this.snack.open(`Guardado: ${res.creados} creados, ${res.actualizados} actualizados`, 'OK', { duration: 3000 });
        this.cargar();
      },
      error: (err) => {
        this.bulkSaving.set(false);
        this.snack.open(err?.error?.detail || 'Error al guardar la carga masiva', 'OK', { duration: 3000 });
      },
    });
  }

  async eliminar(r: any): Promise<void> {
    const ok = await this.confirmSvc.confirm(
      `¿Eliminar la frecuencia de "${r.pdv_nombre || r.id_punto_interes}" para "${r.cliente_nombre || r.id_cliente}"?`,
      { title: 'Eliminar registro', danger: true, confirmText: 'Eliminar' },
    );
    if (!ok) return;
    this.api.deleteFrecuenciaPdvCliente(r.id).subscribe({
      next: () => {
        this.registros.update(rs => rs.filter(x => x.id !== r.id));
        this.snack.open('Registro eliminado', 'OK', { duration: 2500 });
      },
      error: () => this.snack.open('Error al eliminar', 'OK', { duration: 3000 }),
    });
  }
}
