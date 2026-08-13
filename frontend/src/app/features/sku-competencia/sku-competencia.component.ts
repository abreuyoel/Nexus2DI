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

  // ── Filtros de browse (productoras / categorías) ──────────────────────
  cargandoFiltros = signal(false);
  todasProductoras = signal<any[]>([]);
  todasCategorias  = signal<any[]>([]);
  // Solo las categorías que pertenecen a la productora seleccionada
  categoriasFiltradas = signal<any[]>([]);
  productoraFiltroId: number | null = null;
  categoriaFiltroId: number | null = null;

  // ── Buscador + resultados para SKU propio ─────────────────────────────
  buscarPropio = '';
  resultadosPropio = signal<any[]>([]);
  buscandoPropio   = signal(false);
  private buscarPropio$ = new Subject<string>();

  // ── Panel de competencia (uno a la vez) ───────────────────────────────
  grupoCompetenciaAbierto: number | null = null;
  buscarCompetencia = '';
  resultadosCompetencia = signal<any[]>([]);
  buscandoCompetencia   = signal(false);
  seleccionCompetencia  = new Set<number>();
  // Filtros de browse dentro del panel de competencia
  productoraCompId: number | null = null;
  categoriaCompId: number | null = null;
  categoriasComp  = signal<any[]>([]);
  private buscarCompetencia$ = new Subject<string>();

  constructor(private api: ApiService, private snack: MatSnackBar) {}

  ngOnInit(): void {
    this.api.getClients().subscribe({ next: (d) => this.clientes.set(d || []), error: () => {} });
    this.buscarPropio$
      .pipe(debounceTime(300), distinctUntilChanged())
      .subscribe((term) => this.ejecutarBusquedaPropio(term));
    this.buscarCompetencia$
      .pipe(debounceTime(300), distinctUntilChanged())
      .subscribe((term) => this.ejecutarBusquedaCompetencia(term));
  }

  onClienteChange(): void {
    this.resultadosPropio.set([]); this.buscarPropio = '';
    this.productoraFiltroId = null; this.categoriaFiltroId = null;
    this.categoriasFiltradas.set([]);
    this.cerrarBuscadorCompetencia();
    if (!this.clienteId) { this.grupos.set([]); this.todasProductoras.set([]); this.todasCategorias.set([]); return; }
    this.loadGrupos();
    this.loadFiltros();
  }

  loadGrupos(): void {
    if (!this.clienteId) return;
    this.loading.set(true);
    this.api.getSkuCompetenciaMapeos(this.clienteId).subscribe({
      next: (d) => { this.grupos.set(d || []); this.loading.set(false); },
      error: () => { this.grupos.set([]); this.loading.set(false); this.snack.open('Error al cargar los mapeos', 'OK', { duration: 3000 }); },
    });
  }

  // ── Cargar filtros (productoras + categorías) ──────────────────────────
  loadFiltros(): void {
    this.cargandoFiltros.set(true);
    this.api.getProductosFiltrosDisponibles({}).subscribe({
      next: (f) => {
        this.todasProductoras.set(f.productoras || []);
        this.todasCategorias.set(f.categorias || []);
        this.cargandoFiltros.set(false);
      },
      error: () => this.cargandoFiltros.set(false),
    });
  }

  // ── Selección de productora en el panel de SKU propio ─────────────────
  selectProductora(id: number | null): void {
    this.productoraFiltroId = id;
    this.categoriaFiltroId  = null;
    // Filtrar categorías que tienen productos de esa productora
    if (id) {
      this.categoriasFiltradas.set(this.todasCategorias());
    } else {
      this.categoriasFiltradas.set([]);
    }
    this.cargarProductosPropio();
  }

  selectCategoria(id: number | null): void {
    this.categoriaFiltroId = id;
    this.cargarProductosPropio();
  }

  cargarProductosPropio(): void {
    const opts: any = { limit: 60 };
    if (this.productoraFiltroId) opts.id_productora = this.productoraFiltroId;
    if (this.categoriaFiltroId)  opts.id_categoria  = this.categoriaFiltroId;
    if (this.buscarPropio.trim()) opts.busqueda = this.buscarPropio.trim();

    // Si no hay ningún filtro activo, limpiar y salir
    if (!opts.id_productora && !opts.id_categoria && !opts.busqueda) {
      this.resultadosPropio.set([]);
      return;
    }
    this.buscandoPropio.set(true);
    this.api.getProductos(opts).subscribe({
      next: (res) => { this.resultadosPropio.set(res.items || []); this.buscandoPropio.set(false); },
      error: () => { this.resultadosPropio.set([]); this.buscandoPropio.set(false); },
    });
  }

  // ── Búsqueda de texto (complementaria a los filtros) ──────────────────
  onBuscarPropioChange(val: string): void { this.buscarPropio$.next(val); }
  private ejecutarBusquedaPropio(term: string): void {
    this.cargarProductosPropio();
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

  // ── Buscar/agregar competencia dentro de un grupo ─────────────────────
  abrirBuscadorCompetencia(idProductoCliente: number): void {
    this.grupoCompetenciaAbierto = idProductoCliente;
    this.buscarCompetencia = '';
    this.resultadosCompetencia.set([]);
    this.seleccionCompetencia.clear();
    this.productoraCompId = null;
    this.categoriaCompId  = null;
    this.categoriasComp.set([]);
  }
  cerrarBuscadorCompetencia(): void {
    this.grupoCompetenciaAbierto = null;
    this.buscarCompetencia = '';
    this.resultadosCompetencia.set([]);
    this.seleccionCompetencia.clear();
    this.productoraCompId = null;
    this.categoriaCompId  = null;
    this.categoriasComp.set([]);
  }

  selectProductoraComp(id: number | null): void {
    this.productoraCompId = id;
    this.categoriaCompId  = null;
    this.categoriasComp.set(id ? this.todasCategorias() : []);
    this.cargarProductosCompetencia();
  }

  selectCategoriaComp(id: number | null): void {
    this.categoriaCompId = id;
    this.cargarProductosCompetencia();
  }

  onBuscarCompetenciaChange(val: string): void { this.buscarCompetencia$.next(val); }
  private ejecutarBusquedaCompetencia(term: string): void {
    this.cargarProductosCompetencia();
  }

  cargarProductosCompetencia(): void {
    const opts: any = { limit: 60 };
    if (this.productoraCompId) opts.id_productora = this.productoraCompId;
    if (this.categoriaCompId)  opts.id_categoria  = this.categoriaCompId;
    if (this.buscarCompetencia.trim()) opts.busqueda = this.buscarCompetencia.trim();

    if (!opts.id_productora && !opts.id_categoria && !opts.busqueda) {
      this.resultadosCompetencia.set([]);
      return;
    }
    this.buscandoCompetencia.set(true);
    this.api.getProductos(opts).subscribe({
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
