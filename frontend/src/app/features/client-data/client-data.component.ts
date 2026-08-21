import { Component, OnInit, ViewChild, signal, computed } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormControl, FormGroup } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { MatPaginator, MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatSort, MatSortModule, Sort } from '@angular/material/sort';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import * as XLSX from 'xlsx';

import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';
import { SearchableSelectComponent, SelectOption } from '../client-visits/searchable-select.component';

@Component({
  selector: 'app-client-data',
  standalone: true,
  imports: [
    CommonModule, FormsModule, ReactiveFormsModule,
    MatCardModule, MatTableModule, MatPaginatorModule, MatSortModule,
    MatButtonModule, MatIconModule, MatSelectModule, MatInputModule,
    MatFormFieldModule, MatDatepickerModule, MatNativeDateModule,
    MatProgressSpinnerModule, MatSnackBarModule,
    SearchableSelectComponent
  ],
  templateUrl: './client-data.component.html',
  styleUrls: ['./client-data.component.scss'],
  providers: [DatePipe]
})
export class ClientDataComponent implements OnInit {
  displayedColumns: string[] = [
    'fecha_balance', 'visita_id', 'region', 'cadena', 'pdv_nombre',
    'mercaderista', 'producto', 'inv_inicial', 'inv_final', 'caras', 'precio_bs', 'fefo'
  ];
  
  dataSource = new MatTableDataSource<any>([]);
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  // Total real que matchea el filtro (para el "X de Y" del paginator) --
  // dataSource.data solo tiene la página actual, ya no todo el resultado.
  totalItems = signal(0);

  loading = signal(false);
  exporting = signal(false);

  // Fase 3: dos vistas — consolidada (tabla) o tarjetas para revisar
  viewMode = signal<'consolidada' | 'tarjetas'>('consolidada');
  expandedVisit = signal<number | null>(null);

  // Filter Options from Backend
  filterOptions = signal({
    productos: [] as string[],
    cadenas: [] as string[],
    regiones: [] as string[],
    mercaderistas: [] as string[],
    pdvs: [] as any[],
    categorias: [] as string[],
    departamentos: [] as string[],
    cuadrantes: [] as string[],
    estados: [] as string[]
  });

  // Opciones transformadas para el componente app-searchable-select
  regionesOpts = computed<SelectOption[]>(() =>
    (this.filterOptions().regiones || []).map(r => ({ value: r, label: r }))
  );

  cadenasOpts = computed<SelectOption[]>(() =>
    (this.filterOptions().cadenas || []).map(c => ({ value: c, label: c }))
  );

  pdvsOpts = computed<SelectOption[]>(() =>
    (this.filterOptions().pdvs || []).map(p => ({ value: String(p.id), label: p.nombre || String(p.id) }))
  );

  mercaderistasOpts = computed<SelectOption[]>(() =>
    (this.filterOptions().mercaderistas || []).map(m => ({ value: m, label: m }))
  );

  productosOpts = computed<SelectOption[]>(() =>
    (this.filterOptions().productos || []).map(p => ({ value: p, label: p }))
  );

  categoriasOpts = computed<SelectOption[]>(() =>
    (this.filterOptions().categorias || []).map(c => ({ value: c, label: c }))
  );

  departamentosOpts = computed<SelectOption[]>(() =>
    (this.filterOptions().departamentos || []).map(d => ({ value: d, label: d }))
  );

  cuadrantesOpts = computed<SelectOption[]>(() =>
    (this.filterOptions().cuadrantes || []).map(q => ({ value: q, label: q }))
  );

  estadosOpts = computed<SelectOption[]>(() =>
    (this.filterOptions().estados || []).map(e => ({ value: e, label: e }))
  );

  onSelectChange(field: string, val: string): void {
    this.filterForm.patchValue({ [field]: val || '' });
  }

  filterForm = new FormGroup({
    fecha_inicio: new FormControl<Date | null>(null),
    fecha_fin: new FormControl<Date | null>(null),
    producto: new FormControl(''),
    cadena: new FormControl(''),
    region: new FormControl(''),
    mercaderista: new FormControl(''),
    pdv: new FormControl(''),
    visita_id: new FormControl(''),
    categoria: new FormControl(''),
    departamento: new FormControl(''),
    cuadrante: new FormControl(''),
    estado: new FormControl('')
  });

  savingVisit = signal<number | null>(null);

  // El cliente/coordinador NO puede editar la data; solo admin/analista.
  get puedeEditar(): boolean {
    const u = this.auth.currentUser();
    return !!u && (u.rol === 'admin' || u.rol === 'analyst');
  }

  isPanama(obj: any): boolean {
    if (!obj) return false;
    const dep = (obj.departamento || '').toLowerCase();
    const reg = (obj.region || '').toLowerCase();
    const cuad = (obj.cuadrante || '').toLowerCase();
    return dep.includes('panam') || reg.includes('panam') || cuad.includes('panam');
  }

  constructor(private api: ApiService, private datePipe: DatePipe, private snack: MatSnackBar, private auth: AuthService) {}

  ngOnInit(): void {
    // Set default dates to last 30 days
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(endDate.getDate() - 30);
    
    this.filterForm.patchValue({
      fecha_inicio: startDate,
      fecha_fin: endDate
    });

    this.loadFilters();
    this.loadData();
  }

  loadFilters(): void {
    this.api.getClientDataFilters().subscribe({
      next: (data) => {
        this.filterOptions.set(data);
      }
    });
  }

  /** Solo los filtros del formulario -- compartido entre loadData() (una
   * página) y exportExcel() (todo lo filtrado, export_all=true). */
  private buildFilterParams(): any {
    const formVals = this.filterForm.value;
    const params: any = {};
    if (formVals.fecha_inicio) params.fecha_inicio = this.datePipe.transform(formVals.fecha_inicio, 'yyyy-MM-dd');
    if (formVals.fecha_fin) params.fecha_fin = this.datePipe.transform(formVals.fecha_fin, 'yyyy-MM-dd');
    if (formVals.producto) params.producto = formVals.producto;
    if (formVals.cadena) params.cadena = formVals.cadena;
    if (formVals.region) params.region = formVals.region;
    if (formVals.mercaderista) params.mercaderista = formVals.mercaderista;
    if (formVals.pdv) params.pdv = formVals.pdv;
    if (formVals.visita_id) params.visita_id = formVals.visita_id;
    if (formVals.categoria) params.categoria = formVals.categoria;
    if (formVals.departamento) params.departamento = formVals.departamento;
    if (formVals.cuadrante) params.cuadrante = formVals.cuadrante;
    if (formVals.estado) params.estado = formVals.estado;
    return params;
  }

  /** Trae SOLO la página actual -- antes traía el resultado completo del
   * filtro (podían ser decenas de miles de filas) y paginaba en el
   * navegador con todo ya en memoria, que era la razón real de la demora al
   * aplicar filtros. paginator/sort todavía no existen en el primer llamado
   * (viene desde ngOnInit, antes de AfterViewInit) -- de ahí los `?? `. */
  loadData(): void {
    this.loading.set(true);
    const params: any = {
      ...this.buildFilterParams(),
      page: this.paginator?.pageIndex ?? 0,
      page_size: this.paginator?.pageSize ?? 50,
    };
    if (this.sort?.active && this.sort.direction) {
      params.sort_by = this.sort.active;
      params.sort_dir = this.sort.direction;
    }

    this.api.getClientDataBalances(params).subscribe({
      next: (res) => {
        this.dataSource.data = res.items;
        this.totalItems.set(res.total);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      }
    });
  }

  /** Se llama desde (page) del mat-paginator -- Angular Material ya movió
   * pageIndex/pageSize antes de emitir el evento, loadData() los toma de ahí. */
  onPageChange(_event: PageEvent): void {
    this.loadData();
  }

  /** Se llama desde (matSortChange) -- vuelve a página 0, si no se puede
   * quedar "viendo" una página que ya no corresponde al nuevo orden. */
  onSortChange(_sort: Sort): void {
    if (this.paginator) this.paginator.pageIndex = 0;
    this.loadData();
  }

  applyFilters(): void {
    if (this.paginator) this.paginator.pageIndex = 0;
    this.loadData();
  }

  clearFilters(): void {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(endDate.getDate() - 30);

    this.filterForm.reset({
      fecha_inicio: startDate,
      fecha_fin: endDate,
      producto: '',
      cadena: '',
      region: '',
      mercaderista: '',
      pdv: '',
      visita_id: '',
      categoria: '',
      departamento: '',
      cuadrante: '',
      estado: ''
    });
    if (this.paginator) this.paginator.pageIndex = 0;
    this.loadData();
  }

  /** Agrupa los balances cargados por visita, para la vista de tarjetas. */
  get groupedVisits(): any[] {
    const map = new Map<any, any>();
    for (const r of this.dataSource.data) {
      let g = map.get(r.visita_id);
      if (!g) {
        g = {
          visita_id: r.visita_id,
          fecha: r.fecha_balance,
          region: r.region,
          cadena: r.cadena,
          pdv: r.pdv_nombre,
          mercaderista: r.mercaderista,
          items: [],
        };
        map.set(r.visita_id, g);
      }
      g.items.push(r);
    }
    return [...map.values()];
  }

  toggleExpand(visitaId: number): void {
    this.expandedVisit.set(this.expandedVisit() === visitaId ? null : visitaId);
  }

  /** Guarda los balances editados de una visita (vista de tarjetas). */
  saveVisitBalances(v: any): void {
    this.savingVisit.set(v.visita_id);
    const balances = v.items.map((it: any) => ({
      id_balance: it.id_balance,
      inv_inicial: Number(it.inv_inicial) || 0,
      inv_final: Number(it.inv_final) || 0,
      inv_deposito: Number(it.inv_deposito) || 0,
      caras: Number(it.caras) || 0,
      precio_bs: Number(it.precio_bs) || 0,
      precio_ds: Number(it.precio_ds) || 0,
    }));
    this.api.saveBalances({ visita_id: v.visita_id, balances }).subscribe({
      next: () => { this.savingVisit.set(null); this.snack.open('Cambios guardados', 'OK', { duration: 3000 }); },
      error: () => { this.savingVisit.set(null); this.snack.open('Error al guardar', 'OK', { duration: 3500 }); },
    });
  }

  /** Descarga el Excel de una sola visita. */
  exportVisit(v: any): void {
    const data = v.items.map((it: any) => {
      const isPan = this.isPanama(it);
      return {
        'Producto': it.producto,
        'Categoría': it.categoria,
        'Departamento': it.departamento,
        'Cuadrante': it.cuadrante,
        'Estado': it.estado,
        'Inv. Inicial': it.inv_inicial,
        'Inv. Final': it.inv_final,
        'Inv. Depósito': it.inv_deposito,
        'Caras': it.caras,
        'Precio Bs': isPan ? null : it.precio_bs,
        // Panamá no llena precio_bs (no hay bolívares) -- el precio real
        // capturado por el mercaderista SIEMPRE queda en precio_ds, para
        // Panamá y para Venezuela por igual (mismo campo que ya usa la
        // tabla en pantalla, ver isPanama() ahí). Antes leía precio_bs acá
        // para Panamá -- que da NULL siempre -- y el Excel salía vacío
        // aunque la pantalla mostrara el precio en dólares bien.
        'Precio $': it.precio_ds,
        'FEFO': it.fefo ? this.datePipe.transform(it.fefo, 'dd/MM/yyyy') : '',
      };
    });
    const ws = XLSX.utils.json_to_sheet(data);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, `Visita ${v.visita_id}`);
    XLSX.writeFile(wb, `Visita_${v.visita_id}_${this.datePipe.transform(new Date(), 'yyyyMMdd_HHmm')}.xlsx`);
  }

  /** dataSource.data ya no sirve acá -- solo tiene la página visible. Pide
   * TODO lo que matchea el filtro actual (export_all=true, el backend
   * ignora el paginado en ese caso) en un único llamado aparte, solo cuando
   * el usuario realmente pide el Excel -- no en cada aplicación de filtro. */
  exportExcel(): void {
    this.exporting.set(true);
    const params = { ...this.buildFilterParams(), export_all: true };
    this.api.getClientDataBalances(params).subscribe({
      next: (res) => {
        const dataToExport = res.items.map(item => {
          const isPan = this.isPanama(item);
          return {
            'Visita ID': item.visita_id,
            'Fecha': item.fecha_balance ? this.datePipe.transform(item.fecha_balance, 'dd/MM/yyyy HH:mm') : '',
            'Región': item.region,
            'Cadena': item.cadena,
            'PDV': item.pdv_nombre,
            'Mercaderista': item.mercaderista,
            'Producto': item.producto,
            'Categoría': item.categoria,
            'Departamento': item.departamento,
            'Cuadrante': item.cuadrante,
            'Estado': item.estado,
            'Inventario Inicial': item.inv_inicial,
            'Inventario Final': item.inv_final,
            'Caras': item.caras,
            'Precio Bs': isPan ? null : item.precio_bs,
            // Mismo fix que exportarVisita(): precio_ds siempre, no
            // precio_bs para Panamá (ver comentario ahí).
            'Precio $': item.precio_ds,
            'FEFO': item.fefo ? this.datePipe.transform(item.fefo, 'dd/MM/yyyy') : '',
          };
        });

        const ws: XLSX.WorkSheet = XLSX.utils.json_to_sheet(dataToExport);
        const wb: XLSX.WorkBook = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, 'Balances');
        XLSX.writeFile(wb, `Data_Balances_${this.datePipe.transform(new Date(), 'yyyyMMdd_HHmm')}.xlsx`);
        this.exporting.set(false);
      },
      error: () => {
        this.snack.open('Error al generar el Excel', 'OK', { duration: 3500 });
        this.exporting.set(false);
      }
    });
  }
}
