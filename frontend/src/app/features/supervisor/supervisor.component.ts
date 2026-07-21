import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ApiService } from '../../core/services/api.service';
import { Foto } from '../../core/models/visita.model';
import { AuthImgDirective } from '../../shared/directives/auth-img.directive';

@Component({
  selector: 'app-supervisor',
  standalone: true,
  imports: [
    CommonModule, MatCardModule, MatButtonModule, MatIconModule,
    MatProgressSpinnerModule, MatSnackBarModule, AuthImgDirective
  ],
  templateUrl: './supervisor.component.html',
  styleUrls: ['./supervisor.component.scss']
})
export class SupervisorComponent implements OnInit {
  loading = signal(true);
  photos = signal<Foto[]>([]);

  constructor(private api: ApiService, private snack: MatSnackBar) {}

  ngOnInit(): void {
    this.api.getRejectedPhotos().subscribe({
      next: (data) => { 
        this.photos.set(data); 
        this.loading.set(false); 
      },
      error: () => { 
        this.loading.set(false); 
      },
    });
  }

  approvePhoto(foto: Foto): void {
    this.api.approvePhotos([foto.id]).subscribe({
      next: () => {
        this.photos.update((ps) => ps.filter((p) => p.id !== foto.id));
        this.snack.open('Foto aprobada', 'OK', { duration: 2000 });
      },
      error: () => {
        this.snack.open('Error al procesar la aprobación', 'OK', { duration: 3000 });
      }
    });
  }
}
