import { Component, OnInit, ViewChild, signal } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormControl, FormGroup } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule } from '@angular/material/sort';
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

@Component({
  selector: 'app-client-data',
  standalone: true,
  imports: [
    CommonModule, FormsModule, ReactiveFormsModule,
    MatCardModule, MatTableModule, MatPaginatorModule, MatSortModule,
    MatButtonModule, MatIconModule, MatSelectModule, MatInputModule,
    MatFormFieldModule, MatDatepickerModule, MatNativeDateModule,
    MatProgressSpinnerModule, MatSnackBarModule
  ],
  templateUrl: './client-data.component.html',
  styleUrls: ['./client-data.component.scss'],
  providers: [DatePipe]
})
export class ClientDataComponent implements OnInit {
  displayedColumns: string[] = [
    'fecha_balance', 'visita_id', 'region', 'cadena', 'pdv_nombre', 
    'mercaderista', 'producto', 'inv_inicial', 'inv_final', 'caras', 'precio_bs'
  ];
  
  dataSource = new MatTableDataSource<any>([]);
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  loading = signal(false);

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

  loadData(): void {
    this.loading.set(true);
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

    this.api.getClientDataBalances(params).subscribe({
      next: (data) => {
        this.dataSource = new MatTableDataSource(data);
        this.dataSource.paginator = this.paginator;
        this.dataSource.sort = this.sort;
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      }
    });
  }

  applyFilters(): void {
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
    const data = v.items.map((it: any) => ({
      'Producto': it.producto,
      'Categoría': it.categoria,
      'Departamento': it.departamento,
      'Cuadrante': it.cuadrante,
      'Estado': it.estado,
      'Inv. Inicial': it.inv_inicial,
      'Inv. Final': it.inv_final,
      'Inv. Depósito': it.inv_deposito,
      'Caras': it.caras,
      'Precio Bs': it.precio_bs,
      'Precio $': it.precio_ds,
    }));
    const ws = XLSX.utils.json_to_sheet(data);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, `Visita ${v.visita_id}`);
    XLSX.writeFile(wb, `Visita_${v.visita_id}_${this.datePipe.transform(new Date(), 'yyyyMMdd_HHmm')}.xlsx`);
  }

  exportExcel(): void {
    // Generate an Excel sheet from the current data source
    const dataToExport = this.dataSource.data.map(item => ({
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
      'Precio Bs': item.precio_bs,
      'Precio $': item.precio_ds
    }));

    const ws: XLSX.WorkSheet = XLSX.utils.json_to_sheet(dataToExport);
    const wb: XLSX.WorkBook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Balances');
    XLSX.writeFile(wb, `Data_Balances_${this.datePipe.transform(new Date(), 'yyyyMMdd_HHmm')}.xlsx`);
  }
}
