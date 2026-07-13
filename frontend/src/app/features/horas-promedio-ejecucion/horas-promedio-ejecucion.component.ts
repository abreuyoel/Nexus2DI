import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ApiService } from '../../core/services/api.service';
import { ConfirmService } from '../../shared/components/confirm-dialog/confirm.service';

@Component({
  selector: 'app-horas-promedio-ejecucion',
  standalone: true,
  imports: [CommonModule, FormsModule, MatButtonModule, MatIconModule, MatProgressSpinnerModule, MatSnackBarModule],
  templateUrl: './horas-promedio-ejecucion.component.html',
  styleUrls: ['./horas-promedio-ejecucion.component.scss'],
})
export class HorasPromedioEjecucionComponent implements OnInit {
  loading = signal(true);
  saving = signal(false);
  registros = signal<any[]>([]);
  clientes = signal<any[]>([]);
  tiposNegocio = signal<{ id: number; nombre: string; activo: boolean }[]>([]);

  filtroCliente = signal<number | null>(null);
  filtroTipoNegocio = signal<number | null>(null);

  showForm = signal(false);
  editing = signal<any>(null);

  form = {
    id_cliente: null as number | null,
    id_tipo_negocio: null as number | null,
    minutos_promedio: null as number | null,
  };

  constructor(private api: ApiService, private snack: MatSnackBar, private confirmSvc: ConfirmService) {}

  ngOnInit(): void {
    this.cargar();
    this.api.getClients().subscribe({ next: d => this.clientes.set(d), error: () => {} });
    this.api.listCatalog('tipo-negocio').subscribe({ next: d => this.tiposNegocio.set(d), error: () => {} });
  }

  cargar(): void {
    this.loading.set(true);
    const opts: any = {};
    if (this.filtroCliente() != null) opts.id_cliente = this.filtroCliente();
    if (this.filtroTipoNegocio() != null) opts.id_tipo_negocio = this.filtroTipoNegocio();
    this.api.getHorasPromedioEjecucion(opts).subscribe({
      next: d => { this.registros.set(d); this.loading.set(false); },
      error: () => { this.loading.set(false); this.snack.open('Error al cargar', 'OK', { duration: 3000 }); },
    });
  }

  horasTexto(minutos: number): string {
    if (minutos == null) return '';
    const h = Math.floor(minutos / 60);
    const m = minutos % 60;
    if (h === 0) return `${m} min`;
    if (m === 0) return `${h} h`;
    return `${h} h ${m} min`;
  }

  openCreate(): void {
    this.editing.set(null);
    this.form = { id_cliente: null, id_tipo_negocio: null, minutos_promedio: null };
    this.showForm.set(true);
  }

  openEdit(r: any): void {
    this.editing.set(r);
    this.form = { id_cliente: r.id_cliente, id_tipo_negocio: r.id_tipo_negocio, minutos_promedio: r.minutos_promedio };
    this.showForm.set(true);
  }

  cancelar(): void {
    this.showForm.set(false);
    this.editing.set(null);
  }

  guardar(): void {
    if (!this.form.id_cliente || !this.form.id_tipo_negocio || !this.form.minutos_promedio) {
      this.snack.open('Cliente, clasificación de PDV y tiempo son requeridos', 'OK', { duration: 3000 });
      return;
    }
    this.saving.set(true);
    const editing = this.editing();
    const req = editing
      ? this.api.updateHorasPromedioEjecucion(editing.id, this.form)
      : this.api.createHorasPromedioEjecucion(this.form);
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

  async eliminar(r: any): Promise<void> {
    const ok = await this.confirmSvc.confirm(
      `¿Eliminar el tiempo promedio de "${r.tipo_negocio_nombre || r.id_tipo_negocio}" para "${r.cliente_nombre || r.id_cliente}"?`,
      { title: 'Eliminar registro', danger: true, confirmText: 'Eliminar' },
    );
    if (!ok) return;
    this.api.deleteHorasPromedioEjecucion(r.id).subscribe({
      next: () => {
        this.registros.update(rs => rs.filter(x => x.id !== r.id));
        this.snack.open('Registro eliminado', 'OK', { duration: 2500 });
      },
      error: () => this.snack.open('Error al eliminar', 'OK', { duration: 3000 }),
    });
  }
}
