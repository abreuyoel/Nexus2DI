import { Routes } from '@angular/router';
import { ClienteEncuestadorDashboardComponent } from './cliente-encuestador-dashboard.component';

export const CLIENTE_ENCUESTADOR_ROUTES: Routes = [
  { path: 'dashboard', component: ClienteEncuestadorDashboardComponent },
  { path: '', redirectTo: 'dashboard', pathMatch: 'full' }
];
