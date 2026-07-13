import { Component, signal } from '@angular/core';
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

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    CommonModule, ReactiveFormsModule, RouterLink,
    MatCardModule, MatFormFieldModule, MatInputModule,
    MatButtonModule, MatIconModule, MatProgressSpinnerModule, 
    MatSnackBarModule, MatCheckboxModule, FormsModule
  ],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss']
})
export class LoginComponent {
  loading = signal(false);
  error = signal('');
  showPass = signal(false);
  rememberMe = signal(false);

  form = this.fb.group({
    username: ['', [Validators.required, Validators.minLength(2)]],
    password: ['', [Validators.required, Validators.minLength(4)]],
  });

  constructor(private fb: FormBuilder, private auth: AuthService, private router: Router) {
    if (this.auth.isLoggedIn()) {
      this.router.navigateByUrl('/dashboard');
    }
    
    // Load remembered user
    const savedUser = localStorage.getItem('remembered_user');
    if (savedUser) {
      this.form.patchValue({ username: savedUser });
      this.rememberMe.set(true);
    }
  }

  onSubmit(): void {
    if (this.form.invalid) return;
    this.loading.set(true);
    this.error.set('');
    
    const credentials = this.form.value as any;
    
    this.auth.login(credentials).subscribe({
      next: () => {
        this.loading.set(false);
        
        if (this.rememberMe()) {
          localStorage.setItem('remembered_user', credentials.username);
        } else {
          localStorage.removeItem('remembered_user');
        }
        // redirect is handled inside handleAuthSuccess → getMe().subscribe(user => redirect)
      },
      error: (err) => {
        this.loading.set(false);
        this.error.set(err.error?.detail ?? 'Error al iniciar sesión. Verifica tus credenciales.');
      },
    });
  }
}
