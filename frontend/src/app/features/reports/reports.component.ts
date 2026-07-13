import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTabsModule } from '@angular/material/tabs';
import { ApiService } from '../../core/services/api.service';

@Component({
  selector: 'app-reports',
  standalone: true,
  imports: [
    CommonModule, FormsModule, MatCardModule, MatButtonModule, MatIconModule,
    MatFormFieldModule, MatInputModule, MatProgressSpinnerModule, MatTabsModule,
  ],
  templateUrl: './reports.component.html',
  styleUrls: ['./reports.component.scss']
})
export class ReportsComponent implements OnInit {
  loading = signal(false);
  summary = signal<any>(null);
  fechaInicio = '';
  fechaFin = '';

  constructor(private api: ApiService) {
    const now = new Date();
    this.fechaFin = now.toISOString().split('T')[0];
    const start = new Date();
    start.setDate(now.getDate() - 30);
    this.fechaInicio = start.toISOString().split('T')[0];
  }

  ngOnInit(): void { this.loadReport(); }

  loadReport(): void {
    this.loading.set(true);
    this.api.getReportSummary({ 
      fecha_inicio: this.fechaInicio, 
      fecha_fin: this.fechaFin 
    }).subscribe({
      next: (data) => { 
        this.summary.set(data); 
        this.loading.set(false); 
      },
      error: () => { 
        this.loading.set(false); 
      },
    });
  }
}
