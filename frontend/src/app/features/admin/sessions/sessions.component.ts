import { Component, OnInit, signal } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { ApiService } from '../../../core/services/api.service';

interface ActiveSession {
  id: number;
  user_id: number;
  username: string;
  rol: string;
  ip_address: string;
  user_agent: string;
  created_at: string;
  last_active: string;
}

@Component({
  selector: 'app-sessions',
  standalone: true,
  imports: [
    CommonModule, MatTableModule, MatButtonModule, MatIconModule,
    MatProgressSpinnerModule, MatSnackBarModule, MatTooltipModule, DatePipe,
  ],
  templateUrl: './sessions.component.html',
})
export class SessionsComponent implements OnInit {
  loading = signal(true);
  sessions = signal<ActiveSession[]>([]);
  columns = ['username', 'rol', 'ip_address', 'user_agent', 'created_at', 'last_active', 'acciones'];

  constructor(private api: ApiService, private snack: MatSnackBar) {}

  ngOnInit(): void { this.load(); }

  load(): void {
    this.loading.set(true);
    this.api.getActiveSessions().subscribe({
      next: (data) => { this.sessions.set(data as ActiveSession[]); this.loading.set(false); },
      error: () => { this.loading.set(false); },
    });
  }

  kill(id: number): void {
    if (!confirm('¿Terminar esta sesión? El usuario será desconectado.')) return;
    this.api.killSession(id).subscribe({
      next: () => {
        this.sessions.update((s) => s.filter((x) => x.id !== id));
        this.snack.open('Sesión terminada', 'OK', { duration: 2500 });
      },
      error: () => this.snack.open('Error al terminar sesión', 'OK', { duration: 3000 }),
    });
  }

  killAll(userId: number, username: string): void {
    if (!confirm(`¿Terminar TODAS las sesiones de ${username}?`)) return;
    this.api.killUserSessions(userId).subscribe({
      next: () => {
        this.sessions.update((s) => s.filter((x) => x.user_id !== userId));
        this.snack.open(`Todas las sesiones de ${username} terminadas`, 'OK', { duration: 3000 });
      },
      error: () => this.snack.open('Error', 'OK', { duration: 3000 }),
    });
  }

  parseAgent(ua: string): string {
    if (!ua) return '—';
    if (ua.includes('Chrome')) return 'Chrome';
    if (ua.includes('Firefox')) return 'Firefox';
    if (ua.includes('Safari')) return 'Safari';
    if (ua.includes('Edge')) return 'Edge';
    return ua.slice(0, 30);
  }
}
