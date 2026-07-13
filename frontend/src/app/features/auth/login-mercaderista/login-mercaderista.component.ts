import { Component, signal } from '@angular/core';
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

@Component({
  selector: 'app-login-mercaderista',
  standalone: true,
  imports: [
    CommonModule, ReactiveFormsModule, RouterLink,
    MatCardModule, MatFormFieldModule, MatInputModule,
    MatButtonModule, MatIconModule, MatProgressSpinnerModule,
  ],
  templateUrl: './login-mercaderista.component.html',
  styleUrls: ['./login-mercaderista.component.scss']
})
export class LoginMercaderistaComponent {
  loading = signal(false);
  error = signal('');
  showPass = signal(false);

  form = this.fb.group({
    cedula: ['', Validators.required],
    password: ['', Validators.required],
  });

  constructor(private fb: FormBuilder, private auth: AuthService, private router: Router) {}

  onSubmit(): void {
    if (this.form.invalid) return;
    this.loading.set(true);
    this.error.set('');
    this.auth.loginMercaderista(this.form.value as any).subscribe({
      next: () => {
        this.loading.set(false);
        this.router.navigateByUrl('/mercaderista');
      },
      error: (err) => {
        this.loading.set(false);
        this.error.set(err.error?.detail ?? 'Error al ingresar');
      },
    });
  }
}
