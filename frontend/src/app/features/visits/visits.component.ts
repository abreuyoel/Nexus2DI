import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { Visita } from '../../core/models/visita.model';

@Component({
  selector: 'app-visits',
  standalone: true,
  imports: [
    CommonModule, MatTableModule, MatButtonModule, MatIconModule,
    MatCardModule, MatChipsModule, MatFormFieldModule, MatSelectModule,
    MatProgressSpinnerModule, MatTooltipModule, FormsModule, RouterLink,
  ],
  templateUrl: './visits.component.html',
  styleUrls: ['./visits.component.scss']
})
export class VisitsComponent implements OnInit {
  loading = signal(true);
  visits = signal<Visita[]>([]);
  filterEstado = '';
  columns = ['id', 'mercaderista_id', 'punto_id', 'fecha', 'estado', 'acciones'];

  constructor(private api: ApiService) {}

  ngOnInit(): void { this.loadVisits(); }

  loadVisits(): void {
    this.loading.set(true);
    const params = this.filterEstado ? { estado: this.filterEstado } : {};
    this.api.getVisits(params).subscribe({
      next: (data) => { 
        this.visits.set(data); 
        this.loading.set(false); 
      },
      error: () => { 
        this.loading.set(false); 
      },
    });
  }

  getStatusClasses(estado: string): string {
    const map: Record<string, string> = {
      completada: 'bg-emerald-50 text-emerald-700',
      en_progreso: 'bg-primary-50 text-primary-700',
      pendiente: 'bg-amber-50 text-amber-700',
    };
    return map[estado] ?? 'bg-slate-50 text-slate-700';
  }

  viewPhotos(visit: Visita): void {
    console.log('Ver fotos de visita', visit.id);
  }
}
