import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';
import { User, TokenResponse, LoginRequest, LoginMercaderistaRequest } from '../models/user.model';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly TOKEN_KEY = 'epran_token';
  private readonly USER_KEY = 'epran_user';

  currentUser = signal<User | null>(this.loadUser());

  constructor(private http: HttpClient, private router: Router) {}

  login(credentials: LoginRequest): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(`${environment.apiUrl}/auth/login`, credentials).pipe(
      tap((res: TokenResponse) => this.handleAuthSuccess(res))
    );
  }

  loginMercaderista(credentials: LoginMercaderistaRequest): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(`${environment.apiUrl}/auth/login-mercaderista`, credentials).pipe(
      tap((res: TokenResponse) => this.handleAuthSuccess(res))
    );
  }

  logout(): void {
    this.http.post(`${environment.apiUrl}/auth/logout`, {}).subscribe({
      complete: () => this.clearSession(),
      error: () => this.clearSession(),
    });
  }

  getMe(): Observable<User> {
    return this.http.get<User>(`${environment.apiUrl}/auth/me`).pipe(
      tap((user: User) => {
        this.currentUser.set(user);
        sessionStorage.setItem(this.USER_KEY, JSON.stringify(user));
      })
    );
  }

  getToken(): string | null {
    return localStorage.getItem(this.TOKEN_KEY);
  }

  isLoggedIn(): boolean {
    return !!this.getToken();
  }

  hasRole(...roles: string[]): boolean {
    const user = this.currentUser();
    return user ? roles.includes(user.rol) : false;
  }

  /** ¿Puede el usuario 'read' | 'write' | 'delete' sobre la clave del módulo/botón?
   *  Admin = todo. Si no hay permiso para la clave → false (a menos que lo implementemos por rol). */
  can(clave: string, action: 'read' | 'write' | 'delete' = 'read'): boolean {
    const u = this.currentUser();
    if (!u) return false;
    if (u.is_admin || u.rol === 'admin') return true;
    
    const p = (u.permisos || []).find((x) => x.module === clave);
    
    // Si NO hay permiso explícito, asumimos false para submódulos específicos 
    // a menos que desarrollemos un mapa completo de roles.
    if (!p) return false;
    
    if (action === 'write') return !!p.can_write;
    if (action === 'delete') return !!p.can_delete;
    return !!p.can_read;
  }

  /** Decide si un usuario puede ACCEDER a un módulo/ruta.
   *  - Admin: siempre.
   *  - Si existe un registro explícito en DB (Permitido o Denegado), manda el permiso (can_read).
   *  - Si NO existe, hereda del rol por defecto. */
  canAccess(clave: string, roles: string[] = []): boolean {
    const u = this.currentUser();
    if (!u) return false;
    if (u.is_admin || u.rol === 'admin') return true;
    
    // 1. Buscar si hay una sobrescritura explícita
    const p = (u.permisos || []).find((x) => x.module === clave);
    if (p) {
      return !!p.can_read;
    }

    // 2. Si no hay sobrescritura, heredar del rol
    return roles.length === 0 || roles.includes(u.rol);
  }

  /** clave del catálogo MODULOS a partir de la ruta (/client/visits → client-visits) */
  static claveFromRoute(route: string): string {
    return (route || '').replace(/^\//, '').replace(/\//g, '-') || 'dashboard';
  }

  redirectAfterLogin(rol: string): void {
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
    this.router.navigateByUrl(routes[rol] ?? '/dashboard');
  }

  private handleAuthSuccess(res: TokenResponse): void {
    localStorage.setItem(this.TOKEN_KEY, res.access_token);
    this.getMe().subscribe((user: User) => {
      this.redirectAfterLogin(user.rol);
    });
  }

  private clearSession(): void {
    localStorage.removeItem(this.TOKEN_KEY);
    sessionStorage.removeItem(this.USER_KEY);
    this.currentUser.set(null);
    this.router.navigateByUrl('/login');
  }

  private loadUser(): User | null {
    try {
      const raw = sessionStorage.getItem(this.USER_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }
}
