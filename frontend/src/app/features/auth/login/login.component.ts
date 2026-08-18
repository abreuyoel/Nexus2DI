import { Component, signal, HostListener, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators, FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { AuthService } from '../../../core/services/auth.service';
import { ConfirmService } from '../../../shared/components/confirm-dialog/confirm.service';
import { ConfirmDialogComponent } from '../../../shared/components/confirm-dialog/confirm-dialog.component';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    CommonModule, ReactiveFormsModule, RouterLink,
    MatCardModule, MatFormFieldModule, MatInputModule,
    MatButtonModule, MatIconModule, MatProgressSpinnerModule, 
    MatSnackBarModule, MatCheckboxModule, FormsModule,
    ConfirmDialogComponent
  ],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss']
})
export class LoginComponent implements OnInit {
  loading = signal(false);
  error = signal('');
  showPass = signal(false);
  rememberMe = signal(false);

  private wasMobile = window.innerWidth <= 1024;

  form = this.fb.group({
    username: ['', [Validators.required, Validators.minLength(2)]],
    password: ['', [Validators.required, Validators.minLength(4)]],
  });

  constructor(
    private fb: FormBuilder,
    private auth: AuthService,
    private router: Router,
    private confirmSvc: ConfirmService
  ) {
    if (this.auth.isLoggedIn()) {
      const u = this.auth.currentUser();
      if (u && (u.rol === 'mercaderista' || u.is_mercaderista)) {
        this.router.navigateByUrl('/mercaderista');
      } else {
        this.router.navigateByUrl('/dashboard');
      }
    }
    
    // Load remembered user
    const savedUser = localStorage.getItem('remembered_user');
    if (savedUser) {
      this.form.patchValue({ username: savedUser });
      this.rememberMe.set(true);
    }
  }

  ngOnInit(): void {
    if (this.wasMobile) {
      this.promptMobileRedirect();
    }
  }

  @HostListener('window:resize', ['$event'])
  onResize(): void {
    const mobile = window.innerWidth <= 1024;
    if (mobile && !this.wasMobile) {
      this.promptMobileRedirect();
    }
    this.wasMobile = mobile;
  }

  private promptMobileRedirect(): void {
    this.confirmSvc.confirm(
      'Detectamos que estás utilizando un tamaño de pantalla móvil. ¿Deseas ir al portal de inicio de sesión de mercaderistas?',
      { title: 'Cambiar de Vista', confirmText: 'Ir a Login Mercaderista', cancelText: 'Permanecer' }
    ).then(change => {
      if (change) {
        this.router.navigateByUrl('/login-mercaderista');
      }
    });
  }

  onSubmit(): void {
    if (this.form.invalid) return;
    this.loading.set(true);
    this.error.set('');
    
    const credentials = this.form.value as any;
    
    if (this.rememberMe()) {
      localStorage.setItem('remembered_user', credentials.username);
    } else {
      localStorage.removeItem('remembered_user');
    }

    this.auth.login(credentials).subscribe({
      next: () => {
        // La redirección ya fue iniciada por el pipeline de auth.login().
        // Mantenemos loading en true para que el spinner siga activo hasta la redirección.
      },
      error: (err) => {
        this.loading.set(false);
        this.error.set(err.error?.detail ?? 'Error al iniciar sesión. Verifica tus credenciales.');
      },
    });
  }
}
