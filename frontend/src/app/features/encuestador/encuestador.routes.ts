import { Routes } from '@angular/router';
import { EncuestadorDashboardComponent } from './encuestador-dashboard.component';
import { CentroFormComponent } from './centro-form.component';
import { MedicoFormComponent } from './medico-form.component';

export const ENCUESTADOR_ROUTES: Routes = [
  { path: 'dashboard', component: EncuestadorDashboardComponent },
  { path: 'centro', component: CentroFormComponent },
  { path: 'medico', component: MedicoFormComponent },
  { path: '', redirectTo: 'dashboard', pathMatch: 'full' }
];
