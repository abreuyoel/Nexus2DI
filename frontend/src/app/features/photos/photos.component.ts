import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';
import { Foto } from '../../core/models/visita.model';

@Component({
  selector: 'app-photos',
  standalone: true,
  imports: [
    CommonModule, MatCardModule, MatButtonModule, MatIconModule,
    MatProgressSpinnerModule, MatFormFieldModule, MatSelectModule,
    FormsModule, MatSnackBarModule, MatTooltipModule
  ],
  templateUrl: './photos.component.html',
  styleUrls: ['./photos.component.scss']
})
export class PhotosComponent implements OnInit {
  loading = signal(true);
  photos = signal<Foto[]>([]);

  constructor(private api: ApiService, private snack: MatSnackBar) {}

  ngOnInit(): void { this.loadPhotos(); }

  loadPhotos(): void {
    this.loading.set(true);
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
        this.snack.open('Error al aprobar foto', 'OK', { duration: 3000 }); 
      },
    });
  }

  onImgError(event: Event): void {
    (event.target as HTMLImageElement).src = 'assets/images/no-image.png';
  }
}
