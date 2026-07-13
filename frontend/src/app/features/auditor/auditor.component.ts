import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatListModule } from '@angular/material/list';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-auditor',
  standalone: true,
  imports: [
    CommonModule, FormsModule, MatCardModule, MatButtonModule, MatIconModule,
    MatFormFieldModule, MatInputModule, MatProgressSpinnerModule, MatListModule, 
    MatSnackBarModule, MatTooltipModule
  ],
  templateUrl: './auditor.component.html',
  styleUrls: ['./auditor.component.scss']
})
export class AuditorComponent implements OnInit {
  stats = signal<any>(null);
  rutas = signal<any[]>([]);
  loadingRoutes = signal(true);

  constructor(private api: ApiService, private auth: AuthService, private snack: MatSnackBar) {}

  ngOnInit(): void {
    const user = this.auth.currentUser();
    if (user) {
      this.api.getActiveSessions().subscribe();
    }
    this.loadingRoutes.set(false);
  }

  activateRoute(rutaId: number): void {
    this.snack.open('Ruta activada para auditoría', 'OK', { duration: 2000 });
  }
}
