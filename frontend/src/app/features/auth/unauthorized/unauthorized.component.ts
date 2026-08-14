import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-unauthorized',
  standalone: true,
  imports: [RouterLink, MatButtonModule, MatIconModule],
  templateUrl: './unauthorized.component.html',
  styleUrls: ['./unauthorized.component.scss']
})
export class UnauthorizedComponent {
  private auth = inject(AuthService);

  getHomeRoute(): string {
    const user = this.auth.currentUser();
    if (!user) return '/login';

    const routes: Record<string, string> = {
      admin: '/dashboard',
      analyst: '/dashboard',
      supervisor: '/supervisor',
      client: '/client',
      mercaderista: '/mercaderista',
      auditor_campo: '/auditor-campo',
      vendedor: '/ventas',
      encuestador: '/encuestador/dashboard',
      cliente_encuestador: '/cliente-encuestador/dashboard',
    };
    return routes[user.rol] ?? '/dashboard';
  }
}
