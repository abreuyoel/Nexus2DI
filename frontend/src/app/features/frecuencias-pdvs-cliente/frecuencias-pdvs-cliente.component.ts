import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ApiService } from '../../core/services/api.service';
import { ConfirmService } from '../../shared/components/confirm-dialog/confirm.service';

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
  imports: [CommonModule, FormsModule, MatButtonModule, MatIconModule, MatProgressSpinnerModule, MatSnackBarModule],
  templateUrl: './frecuencias-pdvs-cliente.component.html',
  styleUrls: ['./frecuencias-pdvs-cliente.component.scss'],
})
export class FrecuenciasPdvsClienteComponent implements OnInit {
  readonly frecuenciaHints = FRECUENCIA_HINTS;

  loading = signal(true);
  saving = signal(false);
  registros = signal<any[]>([]);
  clientes = signal<any[]>([]);
  pdvs = signal<any[]>([]);

  filtroCliente = signal<number | null>(null);
  filtroActivo = signal<string>('');

  showForm = signal(false);
  editing = signal<any>(null);
  pdvFiltro = '';

  form = {
    id_cliente: null as number | null,
    id_punto_interes: '' as string,
    frecuencia_semanal: null as number | null,
    observaciones: '',
    activo: true,
  };

  pdvsFiltrados = computed(() => {
    const f = this.pdvFiltro.trim().toLowerCase();
    const list = this.pdvs();
    if (!f) return list.slice(0, 100);
    return list.filter(p => (p.nombre || '').toLowerCase().includes(f) || (p.id || '').toLowerCase().includes(f)).slice(0, 100);
  });

  // --- Carga masiva: cliente -> PDVs únicos de su programación de ruta ---
  showBulk = signal(false);
  bulkCliente: number | null = null;
  bulkLoading = signal(false);
  bulkSaving = signal(false);
  bulkPdvs = signal<{ id_punto_interes: string; pdv_nombre: string; id_frecuencia: number | null; frecuencia_semanal: number | null; observaciones: string | null }[]>([]);
  bulkAplicarTodos: number | null = null;

  bulkPendientesCount = computed(() => this.bulkPdvs().filter(p => p.frecuencia_semanal != null).length);

  constructor(private api: ApiService, private snack: MatSnackBar, private confirmSvc: ConfirmService) {}

  ngOnInit(): void {
    this.cargar();
    this.api.getClients().subscribe({ next: d => this.clientes.set(d), error: () => {} });
    this.api.getPDVList().subscribe({ next: d => this.pdvs.set(d), error: () => {} });
  }

  cargar(): void {
    this.loading.set(true);
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
    this.pdvFiltro = '';
    this.showForm.set(true);
  }

  openEdit(r: any): void {
    this.editing.set(r);
    this.form = {
      id_cliente: r.id_cliente, id_punto_interes: r.id_punto_interes,
      frecuencia_semanal: r.frecuencia_semanal, observaciones: r.observaciones || '', activo: r.activo,
    };
    this.pdvFiltro = r.pdv_nombre || r.id_punto_interes || '';
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
    this.showBulk.set(true);
  }

  cancelarBulk(): void {
    this.showBulk.set(false);
  }

  onBulkClienteChange(): void {
    this.bulkPdvs.set([]);
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
