import { Component, signal, HostListener, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { AuthService } from '../../../core/services/auth.service';
import { ConfirmService } from '../../../shared/components/confirm-dialog/confirm.service';
import { ConfirmDialogComponent } from '../../../shared/components/confirm-dialog/confirm-dialog.component';

@Component({
  selector: 'app-login-mercaderista',
  standalone: true,
  imports: [
    CommonModule, ReactiveFormsModule, RouterLink,
    MatCardModule, MatFormFieldModule, MatInputModule,
    MatButtonModule, MatIconModule, MatProgressSpinnerModule,
    ConfirmDialogComponent
  ],
  templateUrl: './login-mercaderista.component.html',
  styleUrls: ['./login-mercaderista.component.scss']
})
export class LoginMercaderistaComponent implements OnInit {
  loading = signal(false);
  error = signal('');
  showPass = signal(false);

  private wasMobile = window.innerWidth <= 1024;

  form = this.fb.group({
    cedula: ['', Validators.required],
    password: ['', Validators.required],
  });

  constructor(
    private fb: FormBuilder,
    private auth: AuthService,
    private router: Router,
    private confirmSvc: ConfirmService
  ) {
    if (this.auth.isLoggedIn()) {
      const u = this.auth.currentUser();
      if (u) {
        this.auth.redirectAfterLogin(u.rol);
      } else {
        this.router.navigateByUrl('/mercaderista');
      }
    }
  }

  ngOnInit(): void {
    if (!this.wasMobile) {
      this.promptDesktopRedirect();
    }
  }

  @HostListener('window:resize', ['$event'])
  onResize(): void {
    const mobile = window.innerWidth <= 1024;
    if (!mobile && this.wasMobile) {
      this.promptDesktopRedirect();
    }
    this.wasMobile = mobile;
  }

  private promptDesktopRedirect(): void {
    this.confirmSvc.confirm(
      'Detectamos que estás utilizando un tamaño de pantalla de escritorio. ¿Deseas ir al portal de inicio de sesión general?',
      { title: 'Cambiar de Vista', confirmText: 'Ir a Login General', cancelText: 'Permanecer' }
    ).then(change => {
      if (change) {
        this.router.navigateByUrl('/login');
      }
    });
  }

  onSubmit(): void {
    if (this.form.invalid) return;
    this.loading.set(true);
    this.error.set('');
    this.auth.loginMercaderista(this.form.value as any).subscribe({
      next: () => {
        this.loading.set(false);
        // Redirect is handled inside handleAuthSuccess -> getMe().subscribe(user => redirect)
      },
      error: (err) => {
        this.loading.set(false);
        this.error.set(err.error?.detail ?? 'Error al ingresar');
      },
    });
  }
}
