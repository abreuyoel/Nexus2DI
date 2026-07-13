import { inject } from '@angular/core';
import { CanActivateFn, Router, ActivatedRouteSnapshot } from '@angular/router';
import { AuthService } from '../services/auth.service';

export const roleGuard: CanActivateFn = (route: ActivatedRouteSnapshot) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const requiredRoles: string[] = route.data['roles'] ?? [];

  if (!auth.isLoggedIn()) {
    router.navigateByUrl('/login');
    return false;
  }

  // canAccess: admin siempre; si el usuario tiene permisos configurados manda el
  // permiso (can_read de la clave del módulo); si no, se cae al rol.
  const clave = AuthService.claveFromRoute(route.routeConfig?.path || '');
  if (auth.canAccess(clave, requiredRoles)) return true;

  router.navigateByUrl('/unauthorized');
  return false;
};
