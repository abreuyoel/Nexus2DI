import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormsModule, FormBuilder, Validators } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { ApiService } from '../../core/services/api.service';
import { RealtimeService } from '../../core/services/realtime.service';
import { ClientCategoriesDialogComponent } from './client-categories-dialog.component';

@Component({
  selector: 'app-users',
  standalone: true,
  imports: [
    CommonModule, ReactiveFormsModule, MatCardModule, MatTableModule,
    MatButtonModule, MatIconModule, MatFormFieldModule, MatInputModule,
    MatSelectModule, MatProgressSpinnerModule, MatSnackBarModule, MatTabsModule, MatTooltipModule, FormsModule,
    MatDialogModule
  ],
  templateUrl: './users.component.html',
  styleUrls: ['./users.component.scss']
})
export class UsersComponent implements OnInit {
  loading = signal(true);
  saving = signal(false);
  activeTab = signal('usuarios');
  users = signal<any[]>([]);
  showForm = signal(false);
  editingUser = signal<any>(null);
  columns = ['id', 'username', 'email', 'rol', 'perfil', 'activo', 'acciones'];

  searchText = '';
  get filteredUsers(): any[] {
    const q = this.searchText.trim().toLowerCase();
    if (!q) return this.users();
    return this.users().filter(u =>
      (u.username || '').toLowerCase().includes(q) ||
      (u.email || '').toLowerCase().includes(q) ||
      (u.rol_nombre || u.rol || '').toLowerCase().includes(q) ||
      (u.perfil_nombre || u.perfil || '').toLowerCase().includes(q)
    );
  }

  analysts = signal<any[]>([]);
  clients = signal<any[]>([]);
  mercaderistas = signal<any[]>([]);
  supervisors = signal<any[]>([]);
  encuestadores = signal<any[]>([]);

  rolesDisponibles = [
    { id: 8, nombre: 'Administrador' },
    { id: 2, nombre: 'Analista' },
    { id: 6, nombre: 'Supervisor' },
    { id: 3, nombre: 'Coordinador Exclusivo' },
    { id: 4, nombre: 'Coordinador Tradex' },
    { id: 11, nombre: 'Coordinador General' },
    { id: 10, nombre: 'Atención al Cliente' },
    { id: 9, nombre: 'Vendedor' },
    { id: 1, nombre: 'Cliente' },
    { id: 5, nombre: 'Mercaderista' },
    { id: 7, nombre: 'Auditor' },
    { id: 14, nombre: 'Auditor de Campo' },
    { id: 12, nombre: 'Encuestador' },
  ];

  get realAnalysts(): any[] { return this.analysts().filter(a => (a.id_rol ?? 2) === 2); }
  get encuestadorUsers(): any[] { return this.users().filter(u => u.id_rol === 12 || u.id_rol === 13); }
  get auditorsList(): any[] {
    return this.mercaderistas().filter(m => {
      const t = (m.tipo || '').toLowerCase();
      return t.includes('auditor') || m.is_auditor || t === 'auditor de campo' || t === 'auditor de gestión';
    });
  }

  tabHints: Record<string, string> = {
    usuarios: 'Accesos al sistema: administrador, analista, supervisor, coordinador, cliente, mercaderista o auditor.',
    analistas: 'Analistas que revisan y gestionan las cuentas de clientes.',
    clientes: 'Cuentas / marcas del sistema.',
    mercaderistas: 'Personal de campo que ejecuta las visitas en los puntos de venta.',
    supervisors: 'Supervisores de rutas y clientes.',
    auditores: 'Personal auditor de campo y auditor de gestión encargados del control de calidad e inspecciones.',
  };

  quickAnalyst = '';
  quickSupervisor = '';
  quickClienteNombre = '';
  quickClienteRif = '';

  createForm = this.fb.group({
    username: ['', Validators.required],
    email: [''],
    password: [''],
    id_rol: [2, Validators.required],
    id_perfil: [null as number | null],
    activo: [true],
  });

  // --- Analysts CRUD State ---
  showAnalystForm = signal(false);
  editingAnalyst = signal<any>(null);
  analystForm = this.fb.group({
    nombre: ['', Validators.required],
    id_rol: [2]
  });

  // --- Clients CRUD State ---
  showClientForm = signal(false);
  editingClient = signal<any>(null);
  clientForm = this.fb.group({
    cliente: ['', Validators.required],
    rif: [''],
    id_categoria: [1],
    id_tipo_cliente: [1]
  });

  // --- Mercaderistas CRUD State ---
  showMercaderistaForm = signal(false);
  editingMercaderista = signal<any>(null);
  mercaderistaForm = this.fb.group({
    nombre: ['', Validators.required],
    cedula: ['', Validators.required],
    telefono: [''],
    tipo_mercaderista: ['MERCADERISTA'],
    activo: [true]
  });

  // --- Supervisores CRUD State ---
  showSupervisorForm = signal(false);
  editingSupervisor = signal<any>(null);
  supervisorForm = this.fb.group({
    nombre: ['', Validators.required],
  });

  // --- Auditores CRUD State ---
  showAuditorForm = signal(false);
  editingAuditor = signal<any>(null);
  auditorForm = this.fb.group({
    nombre: ['', Validators.required],
    cedula: ['', Validators.required],
    telefono: [''],
    tipo: ['Auditor de Campo', Validators.required],
    activo: [true]
  });

  constructor(private api: ApiService, private fb: FormBuilder, private snack: MatSnackBar, private realtime: RealtimeService, private dialog: MatDialog) { }

  ngOnInit(): void {
    this.loadData();
    this.realtime.events$.subscribe(ev => {
      if (ev.tipo.startsWith('user.') || ev.tipo.startsWith('client.')) this.loadData();
    });
  }

  addQuickAnalyst(): void {
    const nombre = this.quickAnalyst.trim();
    if (!nombre) return;
    this.saving.set(true);
    this.api.createAnalyst({ nombre: nombre, id_rol: 2 }).subscribe({
      next: () => { this.saving.set(false); this.quickAnalyst = ''; this.api.getAnalystsList().subscribe(d => this.analysts.set(d)); this.snack.open('Analista creado', 'OK', { duration: 2500 }); },
      error: () => { this.saving.set(false); this.snack.open('Error al crear analista', 'OK', { duration: 3000 }); },
    });
  }
  addQuickSupervisor(): void {
    const nombre = this.quickSupervisor.trim();
    if (!nombre) return;
    this.saving.set(true);
    this.api.createSupervisor({ nombre }).subscribe({
      next: () => { this.saving.set(false); this.quickSupervisor = ''; this.reloadSupervisors(); this.snack.open('Supervisor creado', 'OK', { duration: 2500 }); },
      error: () => { this.saving.set(false); this.snack.open('Error al crear supervisor', 'OK', { duration: 3000 }); },
    });
  }
  addQuickClient(): void {
    const cliente = this.quickClienteNombre.trim();
    if (!cliente) return;
    this.saving.set(true);
    this.api.createClient({ nombre: cliente }).subscribe({
      next: () => { this.saving.set(false); this.quickClienteNombre = ''; this.quickClienteRif = ''; this.api.getClients().subscribe(d => this.clients.set(d)); this.snack.open('Cliente creado', 'OK', { duration: 2500 }); },
      error: () => { this.saving.set(false); this.snack.open('Error al crear cliente', 'OK', { duration: 3000 }); },
    });
  }

  toggleActivo(user: any): void {
    const nuevo = !user.activo;
    this.api.updateUser(user.id, { activo: nuevo }).subscribe({
      next: () => {
        this.users.update(us => us.map(u => u.id === user.id ? { ...u, activo: nuevo } : u));
        this.snack.open(nuevo ? 'Usuario activado' : 'Usuario desactivado', 'OK', { duration: 2500 });
      },
      error: () => this.snack.open('Error al cambiar estado', 'OK', { duration: 3000 }),
    });
  }

  loadData(): void {
    this.api.getUsers().subscribe(data => { this.users.set(data); this.loading.set(false); });
    this.api.getAnalystsList().subscribe(data => this.analysts.set(data));
    this.api.getClients().subscribe(data => this.clients.set(data));
    this.api.getMercaderistas().subscribe(data => this.mercaderistas.set(data));
    this.api.getSupervisorsWithAssignments().subscribe(data => this.supervisors.set(data));
    this.api.getEncuestadores().subscribe({ next: data => this.encuestadores.set(data || []), error: () => {} });
  }

  getProfilesForSelectedRole() {
    const rol = this.createForm.get('id_rol')?.value;
    if (rol === 1 || rol === 3 || rol === 4) return this.clients();   // Cliente, Coord. Exclusivo, Coord. Tradex → cliente
    if (rol === 2) return this.realAnalysts;                          // Analista
    if (rol === 6) return this.supervisors();                         // Supervisor
    if (rol === 5) return this.mercaderistas();                       // Mercaderista
    if (rol === 7 || rol === 14) return this.auditorsList;            // Auditor / Auditor de Campo
    if (rol === 12 || rol === 13) return this.encuestadores();        // Encuestador / IQVIA
    return [];
  }

  showProfileSelect() {
    const rol = this.createForm.get('id_rol')?.value;
    return [1, 2, 3, 4, 5, 6, 7, 14, 12, 13].includes(rol || 0);
  }

  editUser(user: any): void {
    this.editingUser.set(user);
    this.showForm.set(true);
    this.createForm.patchValue({
      username: user.username,
      email: user.email,
      id_rol: user.id_rol,
      id_perfil: user.id_perfil,
      activo: user.activo ?? true,
    });
    this.createForm.get('password')?.clearValidators();
    this.createForm.get('password')?.updateValueAndValidity();
  }

  openCreateForm(): void {
    this.editingUser.set(null);
    this.createForm.reset({ id_rol: 2, activo: true });
    this.createForm.get('password')?.setValidators([Validators.required, Validators.minLength(6)]);
    this.createForm.get('password')?.updateValueAndValidity();
    this.showForm.set(true);
  }

  saveUser(): void {
    if (this.createForm.invalid) {
      this.createForm.markAllAsTouched();
      this.snack.open('Por favor completa todos los campos obligatorios del formulario', 'OK', { duration: 3000 });
      return;
    }
    this.saving.set(true);

    const user = this.editingUser();
    const data: any = { ...this.createForm.value };
    if (!data.password || data.password.trim() === '') {
      delete data.password;
    }

    const request = user
      ? this.api.updateUser(user.id, data)
      : this.api.createUser(data);

    request.subscribe({
      next: () => {
        this.saving.set(false);
        this.editingUser.set(null);
        this.showForm.set(false);
        this.loadData();
        this.snack.open(user ? 'Usuario modificado exitosamente' : 'Usuario creado exitosamente', 'OK', { duration: 3000 });
      },
      error: (err) => {
        this.saving.set(false);
        const errorMsg = typeof err.error?.detail === 'string' ? err.error.detail : 'Error al guardar usuario';
        this.snack.open(errorMsg, 'OK', { duration: 4000 });
      },
    });
  }

  // --- Analysts CRUD ---
  openAnalystForm(): void {
    this.editingAnalyst.set(null);
    this.analystForm.reset({ id_rol: 2 });
    this.showAnalystForm.set(true);
  }

  editAnalyst(a: any): void {
    this.editingAnalyst.set(a);
    this.analystForm.patchValue({ nombre: a.nombre, id_rol: a.id_rol ?? 2 });
    this.showAnalystForm.set(true);
  }

  saveAnalyst(): void {
    if (this.analystForm.invalid) return;
    this.saving.set(true);
    const a = this.editingAnalyst();
    const data: any = { nombre: this.analystForm.value.nombre || '', id_rol: this.analystForm.value.id_rol ?? 2 };
    const req = a ? this.api.updateAnalyst(a.id, data) : this.api.createAnalyst(data);
    req.subscribe({
      next: () => {
        this.saving.set(false);
        this.showAnalystForm.set(false);
        this.api.getAnalystsList().subscribe(d => this.analysts.set(d));
        this.snack.open('Analista guardado', 'OK', { duration: 2500 });
      },
      error: () => {
        this.saving.set(false);
        this.snack.open('Error al guardar analista', 'OK', { duration: 3000 });
      }
    });
  }

  deleteAnalyst(a: any): void {
    if (confirm(`¿Deseas eliminar al analista ${a.nombre}?`)) {
      this.api.deleteAnalyst(a.id).subscribe({
        next: () => {
          this.api.getAnalystsList().subscribe(d => this.analysts.set(d));
          this.snack.open('Analista eliminado', 'OK', { duration: 2500 });
        },
        error: () => this.snack.open('Error al eliminar analista', 'OK', { duration: 3000 })
      });
    }
  }

  // --- Clients CRUD ---
  openClientForm(): void {
    this.editingClient.set(null);
    this.clientForm.reset({ id_categoria: 1, id_tipo_cliente: 1 });
    this.showClientForm.set(true);
  }

  editClient(c: any): void {
    this.editingClient.set(c);
    this.clientForm.patchValue({
      cliente: c.cliente || c.nombre,
      rif: c.rif || '',
      id_categoria: c.id_categoria || 1,
      id_tipo_cliente: c.id_tipo_cliente || 1
    });
    this.showClientForm.set(true);
  }

  saveClient(): void {
    if (this.clientForm.invalid) return;
    this.saving.set(true);
    const c = this.editingClient();
    const data: any = { ...this.clientForm.value };
    const req = c ? this.api.updateClient(c.id, data) : this.api.createClient(data);
    req.subscribe({
      next: () => {
        this.saving.set(false);
        this.showClientForm.set(false);
        this.api.getClients().subscribe(d => this.clients.set(d));
        this.snack.open('Cliente guardado', 'OK', { duration: 2500 });
      },
      error: () => {
        this.saving.set(false);
        this.snack.open('Error al guardar cliente', 'OK', { duration: 3000 });
      }
    });
  }

  deleteClient(c: any): void {
    if (confirm(`¿Deseas eliminar al cliente ${c.cliente || c.nombre}?`)) {
      this.api.deleteClient(c.id).subscribe({
        next: () => {
          this.api.getClients().subscribe(d => this.clients.set(d));
          this.snack.open('Cliente eliminado', 'OK', { duration: 2500 });
        },
        error: () => this.snack.open('Error al eliminar cliente', 'OK', { duration: 3000 })
      });
    }
  }

  manageClientCategories(c: any): void {
    this.dialog.open(ClientCategoriesDialogComponent, { data: { client: c }, width: '600px' });
  }

  // --- Mercaderistas CRUD ---
  openMercaderistaForm(): void {
    this.editingMercaderista.set(null);
    this.mercaderistaForm.reset({ tipo_mercaderista: 'MERCADERISTA', activo: true });
    this.showMercaderistaForm.set(true);
  }

  editMercaderista(m: any): void {
    this.editingMercaderista.set(m);
    this.mercaderistaForm.patchValue({
      nombre: m.nombre,
      cedula: m.cedula,
      telefono: m.telefono || '',
      tipo_mercaderista: m.tipo || 'MERCADERISTA',
      activo: m.activo ?? true
    });
    this.showMercaderistaForm.set(true);
  }

  saveMercaderista(): void {
    if (this.mercaderistaForm.invalid) return;
    this.saving.set(true);
    const m = this.editingMercaderista();
    const data: any = { ...this.mercaderistaForm.value };
    const req = m ? this.api.updateMercaderista(m.id, data) : this.api.createMercaderista(data);
    req.subscribe({
      next: () => {
        this.saving.set(false);
        this.showMercaderistaForm.set(false);
        this.api.getMercaderistas().subscribe(d => this.mercaderistas.set(d));
        this.snack.open('Mercaderista guardado', 'OK', { duration: 2500 });
      },
      error: () => {
        this.saving.set(false);
        this.snack.open('Error al guardar mercaderista', 'OK', { duration: 3000 });
      }
    });
  }

  deleteMercaderista(m: any): void {
    if (confirm(`¿Deseas eliminar al mercaderista ${m.nombre}?`)) {
      this.api.deleteMercaderista(m.id).subscribe({
        next: () => {
          this.api.getMercaderistas().subscribe(d => this.mercaderistas.set(d));
          this.snack.open('Mercaderista eliminado', 'OK', { duration: 2500 });
        },
        error: () => this.snack.open('Error al eliminar mercaderista', 'OK', { duration: 3000 })
      });
    }
  }

  // --- Supervisores CRUD ---
  openSupervisorForm(): void {
    this.editingSupervisor.set(null);
    this.supervisorForm.reset();
    this.showSupervisorForm.set(true);
  }

  editSupervisor(s: any): void {
    this.editingSupervisor.set(s);
    this.supervisorForm.patchValue({ nombre: s.nombre });
    this.showSupervisorForm.set(true);
  }

  saveSupervisor(): void {
    if (this.supervisorForm.invalid) return;
    this.saving.set(true);
    const s = this.editingSupervisor();
    const data: any = { nombre: this.supervisorForm.value.nombre || '' };
    const req = s ? this.api.updateSupervisor(s.id, data) : this.api.createSupervisor(data);
    req.subscribe({
      next: () => {
        this.saving.set(false);
        this.showSupervisorForm.set(false);
        this.reloadSupervisors();
        this.snack.open('Supervisor guardado', 'OK', { duration: 2500 });
      },
      error: () => {
        this.saving.set(false);
        this.snack.open('Error al guardar supervisor', 'OK', { duration: 3000 });
      }
    });
  }

  deleteSupervisor(s: any): void {
    if (confirm(`¿Deseas eliminar al supervisor ${s.nombre}?`)) {
      this.api.deleteSupervisor(s.id).subscribe({
        next: () => {
          this.reloadSupervisors();
          this.snack.open('Supervisor eliminado', 'OK', { duration: 2500 });
        },
        error: () => this.snack.open('Error al eliminar supervisor', 'OK', { duration: 3000 })
      });
    }
  }

  // --- Auditores CRUD ---
  openCreateAuditorForm(): void {
    this.editingAuditor.set(null);
    this.auditorForm.reset({ tipo: 'Auditor de Campo', activo: true });
    this.showAuditorForm.set(true);
  }

  editAuditor(auditor: any): void {
    this.editingAuditor.set(auditor);
    this.auditorForm.patchValue({
      nombre: auditor.nombre,
      cedula: auditor.cedula,
      telefono: auditor.telefono || '',
      tipo: auditor.tipo || 'Auditor de Campo',
      activo: auditor.activo ?? true
    });
    this.showAuditorForm.set(true);
  }

  saveAuditor(): void {
    if (this.auditorForm.invalid) {
      this.auditorForm.markAllAsTouched();
      this.snack.open('Por favor completa los campos requeridos', 'OK', { duration: 3000 });
      return;
    }

    this.saving.set(true);
    const auditor = this.editingAuditor();
    const data = { ...this.auditorForm.value };

    const req = auditor
      ? this.api.updateMercaderista(auditor.id, data)
      : this.api.createMercaderista(data);

    req.subscribe({
      next: () => {
        this.saving.set(false);
        this.showAuditorForm.set(false);
        this.editingAuditor.set(null);
        this.api.getMercaderistas().subscribe(d => this.mercaderistas.set(d));
        this.snack.open(auditor ? 'Auditor modificado exitosamente' : 'Auditor creado exitosamente', 'OK', { duration: 3000 });
      },
      error: (err) => {
        this.saving.set(false);
        this.snack.open(err.error?.detail ?? 'Error al guardar auditor', 'OK', { duration: 3000 });
      }
    });
  }

  deleteAuditor(auditor: any): void {
    if (!confirm(`¿Deseas eliminar al auditor ${auditor.nombre}?`)) return;
    this.api.deleteMercaderista(auditor.id).subscribe({
      next: () => {
        this.api.getMercaderistas().subscribe(d => this.mercaderistas.set(d));
        this.snack.open('Auditor eliminado', 'OK', { duration: 2500 });
      },
      error: () => this.snack.open('Error al eliminar auditor', 'OK', { duration: 3000 })
    });
  }

  getRoleClasses(idRol: number | undefined): string {
    const map: Record<number, string> = {
      8: 'bg-primary-500 text-white',
      2: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
      6: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
      5: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
      7: 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300',
      14: 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300',
      3: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300',
      4: 'bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300',
      11: 'bg-fuchsia-100 text-fuchsia-700 dark:bg-fuchsia-900/40 dark:text-fuchsia-300',
    };
    return map[idRol || 0] || 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300';
  }

  deleteUser(user: any): void {
    if (confirm(`¿Estás seguro de eliminar el usuario "${user.username}"?`)) {
      this.api.deleteUser(user.id).subscribe({
        next: () => {
          this.loadData();
          this.snack.open('Usuario eliminado', 'OK', { duration: 2500 });
        },
        error: () => this.snack.open('Error al eliminar usuario', 'OK', { duration: 3000 })
      });
    }
  }

  reloadSupervisors(): void {
    this.api.getSupervisorsWithAssignments().subscribe(d => this.supervisors.set(d));
  }
}
