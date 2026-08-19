import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ApiService } from '../../core/services/api.service';

interface DeptoQuiebre {
  departamento: string;
  sku_pdv_evaluados: number;
  en_quiebre: number;
  tasa_quiebre_pct: number;
}
interface CadenaQuiebre {
  cadena: string;
  sku_pdv_evaluados: number;
  en_quiebre: number;
  tasa_quiebre_pct: number;
  departamentos: DeptoQuiebre[];
}

@Component({
  selector: 'app-quiebre-cadena',
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule, MatProgressSpinnerModule, MatSnackBarModule],
  templateUrl: './quiebre-cadena.component.html',
})
export class QuiebreCadenaComponent implements OnInit {
  loading = signal(false);
  cadenas = signal<CadenaQuiebre[]>([]);
  ventanaDias = signal(0);
  totalEvaluados = signal(0);
  diasVentana = 30;
  expandida = new Set<string>();

  constructor(private api: ApiService, private snack: MatSnackBar) {}

  ngOnInit(): void {
    this.cargar();
  }

  cargar(): void {
    this.loading.set(true);
    this.api.getQuiebrePorCadena(this.diasVentana).subscribe({
      next: (res) => {
        this.cadenas.set(res.cadenas || []);
        this.ventanaDias.set(res.ventana_dias);
        this.totalEvaluados.set(res.sku_pdv_evaluados);
        this.loading.set(false);
      },
      error: () => {
        this.cadenas.set([]);
        this.loading.set(false);
        this.snack.open('Error al calcular el quiebre por cadena', 'OK', { duration: 3000 });
      },
    });
  }

  toggle(cadena: string): void {
    if (this.expandida.has(cadena)) this.expandida.delete(cadena);
    else this.expandida.add(cadena);
  }

  // Semántico, no el accent de la marca -- separado a propósito (mismo
  // criterio del resto de los módulos predictivos de esta sesión).
  claseTasa(pct: number): string {
    if (pct >= 20) return 'text-rose-600 dark:text-rose-400';
    if (pct >= 10) return 'text-amber-600 dark:text-amber-400';
    return 'text-emerald-600 dark:text-emerald-400';
  }
}
