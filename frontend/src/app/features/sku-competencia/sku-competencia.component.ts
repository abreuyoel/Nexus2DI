import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Subject, debounceTime, distinctUntilChanged } from 'rxjs';
import { ApiService } from '../../core/services/api.service';

interface Grupo {
  id_producto_cliente: number;
  producto_cliente: string;
  marca_cliente: string | null;
  competencia: { id_sku_competencia: number; id_producto: number; producto: string; marca: string | null }[];
}

@Component({
  selector: 'app-sku-competencia',
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule, MatProgressSpinnerModule, MatSnackBarModule, MatTooltipModule],
  templateUrl: './sku-competencia.component.html',
})
export class SkuCompetenciaComponent implements OnInit {
  loading = signal(false);
  clientes = signal<any[]>([]);
  clienteId: number | null = null;
  grupos = signal<Grupo[]>([]);

  // Buscador para agregar un SKU propio nuevo
  buscarPropio = '';
  resultadosPropio = signal<any[]>([]);
  buscandoPropio = signal(false);
  private buscarPropio$ = new Subject<string>();

  // Buscador de competencia -- uno activo a la vez, identificado por el
  // id_producto_cliente del grupo que lo abrió.
  grupoCompetenciaAbierto: number | null = null;
  buscarCompetencia = '';
  resultadosCompetencia = signal<any[]>([]);
  buscandoCompetencia = signal(false);
  seleccionCompetencia = new Set<number>();
  private buscarCompetencia$ = new Subject<string>();

  constructor(private api: ApiService, private snack: MatSnackBar) {}

  ngOnInit(): void {
    this.api.getClients().subscribe({ next: (d) => this.clientes.set(d || []), error: () => {} });
    this.buscarPropio$.pipe(debounceTime(300), distinctUntilChanged()).subscribe((term) => this.ejecutarBusquedaPropio(term));
    this.buscarCompetencia$.pipe(debounceTime(300), distinctUntilChanged()).subscribe((term) => this.ejecutarBusquedaCompetencia(term));
  }

  onClienteChange(): void {
    this.resultadosPropio.set([]); this.buscarPropio = '';
    this.cerrarBuscadorCompetencia();
    if (!this.clienteId) { this.grupos.set([]); return; }
    this.loadGrupos();
  }

  loadGrupos(): void {
    if (!this.clienteId) return;
    this.loading.set(true);
    this.api.getSkuCompetenciaMapeos(this.clienteId).subscribe({
      next: (d) => { this.grupos.set(d || []); this.loading.set(false); },
      error: () => { this.grupos.set([]); this.loading.set(false); this.snack.open('Error al cargar los mapeos', 'OK', { duration: 3000 }); },
    });
  }

  // ── Buscar/agregar el SKU propio ──
  onBuscarPropioChange(val: string): void { this.buscarPropio$.next(val); }
  private ejecutarBusquedaPropio(term: string): void {
    if (!term || term.trim().length < 2) { this.resultadosPropio.set([]); return; }
    this.buscandoPropio.set(true);
    this.api.getProductos({ busqueda: term, limit: 15 }).subscribe({
      next: (res) => { this.resultadosPropio.set(res.items || []); this.buscandoPropio.set(false); },
      error: () => { this.resultadosPropio.set([]); this.buscandoPropio.set(false); },
    });
  }
  agregarSkuPropio(p: any): void {
    if (!this.clienteId) return;
    if (this.grupos().some((g) => g.id_producto_cliente === p.id)) {
      this.snack.open('Ese SKU ya está en la lista', 'OK', { duration: 2500 });
      return;
    }
    this.grupos.update((list) => [{ id_producto_cliente: p.id, producto_cliente: p.producto_gu, marca_cliente: p.marca ?? null, competencia: [] }, ...list]);
    this.buscarPropio = ''; this.resultadosPropio.set([]);
    this.abrirBuscadorCompetencia(p.id);
  }

  // ── Buscar/agregar competencia dentro de un grupo ──
  abrirBuscadorCompetencia(idProductoCliente: number): void {
    this.grupoCompetenciaAbierto = idProductoCliente;
    this.buscarCompetencia = ''; this.resultadosCompetencia.set([]); this.seleccionCompetencia.clear();
  }
  cerrarBuscadorCompetencia(): void {
    this.grupoCompetenciaAbierto = null;
    this.buscarCompetencia = ''; this.resultadosCompetencia.set([]); this.seleccionCompetencia.clear();
  }
  onBuscarCompetenciaChange(val: string): void { this.buscarCompetencia$.next(val); }
  private ejecutarBusquedaCompetencia(term: string): void {
    if (!term || term.trim().length < 2) { this.resultadosCompetencia.set([]); return; }
    this.buscandoCompetencia.set(true);
    this.api.getProductos({ busqueda: term, limit: 15 }).subscribe({
      next: (res) => { this.resultadosCompetencia.set(res.items || []); this.buscandoCompetencia.set(false); },
      error: () => { this.resultadosCompetencia.set([]); this.buscandoCompetencia.set(false); },
    });
  }
  toggleSeleccionCompetencia(idProducto: number): void {
    if (this.seleccionCompetencia.has(idProducto)) this.seleccionCompetencia.delete(idProducto);
    else this.seleccionCompetencia.add(idProducto);
  }
  yaEsCompetencia(grupo: Grupo, idProducto: number): boolean {
    return grupo.competencia.some((c) => c.id_producto === idProducto);
  }

  guardarCompetenciaSeleccionada(grupo: Grupo): void {
    if (!this.clienteId || this.seleccionCompetencia.size === 0) return;
    const ids = Array.from(this.seleccionCompetencia);
    this.api.bulkCreateSkuCompetencia(this.clienteId, grupo.id_producto_cliente, ids).subscribe({
      next: (res) => {
        this.snack.open(`${res.agregados} competidor(es) agregado(s)${res.ya_existian ? ` (${res.ya_existian} ya estaban)` : ''}`, 'OK', { duration: 3500 });
        this.cerrarBuscadorCompetencia();
        this.loadGrupos();
      },
      error: () => this.snack.open('Error al agregar competencia', 'OK', { duration: 3000 }),
    });
  }

  quitarCompetencia(grupo: Grupo, idSkuCompetencia: number): void {
    this.api.deleteSkuCompetencia(idSkuCompetencia).subscribe({
      next: () => {
        this.grupos.update((list) => list.map((g) => g.id_producto_cliente === grupo.id_producto_cliente
          ? { ...g, competencia: g.competencia.filter((c) => c.id_sku_competencia !== idSkuCompetencia) }
          : g));
      },
      error: () => this.snack.open('Error al quitar', 'OK', { duration: 3000 }),
    });
  }
}
