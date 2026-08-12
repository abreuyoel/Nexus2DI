import { Routes } from '@angular/router';
import { EncuestadorDashboardComponent } from './encuestador-dashboard.component';
import { CentroFormComponent } from './centro-form.component';
import { MedicoFormComponent } from './medico-form.component';
import { ConfiguracionEncuestadorComponent } from './configuracion-encuestador.component';

export const ENCUESTADOR_ROUTES: Routes = [
  { path: 'dashboard', component: EncuestadorDashboardComponent },
  { path: 'centro', component: CentroFormComponent },
  { path: 'medico', component: MedicoFormComponent },
  { path: 'configuracion', component: ConfiguracionEncuestadorComponent },
  { path: '', redirectTo: 'dashboard', pathMatch: 'full' }
];
