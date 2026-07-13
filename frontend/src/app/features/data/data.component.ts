import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, FormArray } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ApiService } from '../../core/services/api.service';
import { Visita, Balance } from '../../core/models/visita.model';

@Component({
  selector: 'app-data',
  standalone: true,
  imports: [
    CommonModule, FormsModule, ReactiveFormsModule,
    MatTableModule, MatButtonModule, MatIconModule,
    MatFormFieldModule, MatInputModule, MatProgressSpinnerModule, MatSnackBarModule
  ],
  templateUrl: './data.component.html',
  styleUrls: ['./data.component.scss']
})
export class DataComponent implements OnInit {
  loadingVisits = signal(true);
  loadingBalances = signal(false);
  isReviewMode = signal(false);

  visits = signal<Visita[]>([]);
  selectedVisit = signal<Visita | null>(null);
  balancesForm: FormGroup;

  // Filter options
  clients = signal<any[]>([]);
  mercaderistas = signal<any[]>([]);

  // Filter values
  fechaInicio = '';
  fechaFin = '';
  clienteId = '';
  mercaderistaId = '';
  puntoSearch = '';

  visitColumns = ['fecha', 'cliente', 'pdv', 'mercaderista', 'acciones'];
  balanceColumns = ['producto', 'categoria', 'inv_inicial', 'inv_final', 'inv_deposito', 'caras', 'precio_bs', 'precio_usd'];

  constructor(
    private api: ApiService,
    private fb: FormBuilder,
    private snack: MatSnackBar
  ) {
    this.balancesForm = this.fb.group({ balances: this.fb.array([]) });
  }

  get balancesArray() { return this.balancesForm.get('balances') as FormArray; }

  ngOnInit(): void {
    this.loadVisits();
    this.api.getClients().subscribe({ next: (d: any) => this.clients.set(d), error: () => {} });
    this.api.getMercaderistas().subscribe({ next: (d) => this.mercaderistas.set(d), error: () => {} });
  }

  loadVisits(): void {
    this.loadingVisits.set(true);
    const opts: any = {};
    if (this.fechaInicio) opts.fecha_inicio = this.fechaInicio;
    if (this.fechaFin)    opts.fecha_fin    = this.fechaFin;
    if (this.clienteId)   opts.cliente_id   = +this.clienteId;
    if (this.mercaderistaId) opts.mercaderista_id = +this.mercaderistaId;
    if (this.puntoSearch) opts.punto_id = this.puntoSearch;

    this.api.getVisitsWithBalances(opts).subscribe({
      next: (data) => { this.visits.set(data); this.loadingVisits.set(false); },
      error: () => this.loadingVisits.set(false)
    });
  }

  clearFilters(): void {
    this.fechaInicio = ''; this.fechaFin = '';
    this.clienteId = ''; this.mercaderistaId = ''; this.puntoSearch = '';
    this.loadVisits();
  }

  get hasFilters(): boolean {
    return !!(this.fechaInicio || this.fechaFin || this.clienteId || this.mercaderistaId || this.puntoSearch);
  }

  reviewVisit(visit: Visita): void {
    this.selectedVisit.set(visit);
    this.isReviewMode.set(true);
    this.loadingBalances.set(true);
    this.api.getVisitBalances(visit.id).subscribe({
      next: (balances) => { this.setBalances(balances); this.loadingBalances.set(false); },
      error: () => this.loadingBalances.set(false)
    });
  }

  setBalances(balances: Balance[]): void {
    const formGroups = balances.map(b => this.fb.group({
      id_balance: [b.id], producto: [b.producto], categoria: [b.categoria],
      inv_inicial: [b.inv_inicial], inv_final: [b.inv_final], inv_deposito: [b.inv_deposito],
      caras: [b.caras], precio_bs: [b.precio_bs], precio_usd: [b.precio_ds]
    }));
    this.balancesForm.setControl('balances', this.fb.array(formGroups));
  }

  goBack(): void { this.isReviewMode.set(false); this.selectedVisit.set(null); }

  saveChanges(): void {
    if (this.balancesForm.invalid) return;
    this.api.saveBalances({ visita_id: this.selectedVisit()?.id!, balances: this.balancesForm.value.balances }).subscribe({
      next: () => { this.snack.open('Cambios guardados', 'Cerrar', { duration: 3000 }); this.goBack(); },
      error: (err) => this.snack.open('Error al guardar: ' + err.message, 'Cerrar', { duration: 5000 })
    });
  }
}
