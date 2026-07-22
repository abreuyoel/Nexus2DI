import { Component, OnInit, signal, effect } from '@angular/core';
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
import { User } from '../../core/models/user.model';
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

  analysts = signal<any[]>([]);
  clients = signal<any[]>([]);
  mercaderistas = signal<any[]>([]);
  supervisors = signal<any[]>([]);

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
  ];

  // Solo analistas reales (rol 2) en la pestaña Analistas; los supervisores van aparte
  get realAnalysts(): any[] { return this.analysts().filter(a => (a.id_rol ?? 2) === 2); }

  // Descripciones por entidad (estilo Catálogos)
  tabHints: Record<string, string> = {
    usuarios: 'Accesos al sistema: administrador, analista, supervisor, coordinador (exclusivo / tradex / general), cliente o mercaderista.',
    analistas: 'Analistas que revisan y gestionan las cuentas de clientes.',
    clientes: 'Cuentas / marcas del sistema. El tipo (Exclusiva / Tradex) se define por la ruta a la que se asigna.',
    mercaderistas: 'Personal de campo que ejecuta las visitas en los puntos de venta.',
    supervisores: 'Supervisores de rutas y clientes.',
  };

  // Alta rápida inline (estilo Catálogos)
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

  constructor(private api: ApiService, private fb: FormBuilder, private snack: MatSnackBar, private realtime: RealtimeService, private dialog: MatDialog) {}

  ngOnInit(): void {
    this.loadData();
    this.realtime.events$.subscribe(ev => {
      if (ev.tipo.startsWith('user.') || ev.tipo.startsWith('client.')) this.loadData();
    });
  }

  // --- Alta rápida (estilo Catálogos) ---
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
    this.api.createClient({ cliente, rif: this.quickClienteRif.trim(), id_categoria: 1, id_tipo_cliente: 1 }).subscribe({
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
  }

  getProfilesForSelectedRole() {
    const rol = this.createForm.get('id_rol')?.value;
    if (rol === 1 || rol === 3 || rol === 4) return this.clients();   // Cliente, Coord. Exclusivo, Coord. Tradex → cliente
    if (rol === 2) return this.realAnalysts;                          // Analista
    if (rol === 6) return this.supervisors();                         // Supervisor
    if (rol === 5) return this.mercaderistas();                       // Mercaderista
    return [];
  }

  showProfileSelect() {
    const rol = this.createForm.get('id_rol')?.value;
    return [1, 2, 3, 4, 5, 6].includes(rol || 0);
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
    if (this.createForm.invalid) return;
    this.saving.set(true);
    
    const user = this.editingUser();
    const data = { ...this.createForm.value };
    if (!data.password) delete data.password;

    const request = user 
      ? this.api.updateUser(user.id, data)
      : this.api.createUser(data);

    request.subscribe({
      next: () => {
        this.saving.set(false);
        this.loadData();
        this.showForm.set(false);
        this.snack.open(user ? 'Usuario modificado' : 'Usuario creado', 'OK', { duration: 3000 });
      },
      error: (err) => {
        this.saving.set(false);
        this.snack.open(err.error?.detail ?? 'Error al guardar usuario', 'OK', { duration: 3000 });
      },
    });
  }

  getRoleClasses(idRol: number | undefined): string {
    const map: Record<number, string> = {
      8:  'bg-primary-500 text-white',
      2:  'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
      6:  'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
      5:  'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
      7:  'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300',
      3:  'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300',
      4:  'bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300',
      11: 'bg-fuchsia-100 text-fuchsia-700 dark:bg-fuchsia-900/40 dark:text-fuchsia-300',
      10: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/40 dark:text-cyan-300',
      1:  'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
    };
    return map[idRol ?? 0] ?? 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300';
  }

  deleteUser(user: any): void {
    if (!confirm(`¿Eliminar al usuario "${user.username}"?`)) return;
    this.api.deleteUser(user.id).subscribe({
      next: () => { this.users.update((us) => us.filter((u) => u.id !== user.id)); },
      error: () => { this.snack.open('Error al eliminar usuario', 'OK', { duration: 3000 }); },
    });
  }

  // --- Analysts CRUD Methods ---
  openAnalystForm() {
    this.editingAnalyst.set(null);
    this.analystForm.reset({ id_rol: 2 });
    this.showAnalystForm.set(true);
  }

  editAnalyst(a: any) {
    this.editingAnalyst.set(a);
    this.analystForm.patchValue({ nombre: a.nombre, id_rol: a.id_rol });
    this.showAnalystForm.set(true);
  }

  saveAnalyst() {
    if (this.analystForm.invalid) return;
    this.saving.set(true);
    const a = this.editingAnalyst();
    const request = a 
      ? this.api.updateAnalyst(a.id, this.analystForm.value)
      : this.api.createAnalyst(this.analystForm.value);

    request.subscribe({
      next: () => {
        this.saving.set(false);
        this.api.getAnalystsList().subscribe(data => this.analysts.set(data));
        this.showAnalystForm.set(false);
        this.snack.open(a ? 'Analista modificado' : 'Analista creado', 'OK', { duration: 3000 });
      },
      error: () => { this.saving.set(false); this.snack.open('Error guardando analista', 'OK', { duration: 3000 }); }
    });
  }

  deleteAnalyst(a: any) {
    if (!confirm(`¿Eliminar analista "${a.nombre}"?`)) return;
    this.api.deleteAnalyst(a.id).subscribe({
      next: () => this.api.getAnalystsList().subscribe(data => this.analysts.set(data)),
      error: () => this.snack.open('Error al eliminar', 'OK', { duration: 3000 })
    });
  }

  // --- Clients CRUD Methods ---
  openClientForm() {
    this.editingClient.set(null);
    this.clientForm.reset({ id_categoria: 1, id_tipo_cliente: 1 });
    this.showClientForm.set(true);
  }

  editClient(c: any) {
    this.editingClient.set(c);
    this.clientForm.patchValue({ cliente: c.cliente || c.nombre, rif: c.rif, id_categoria: c.id_categoria, id_tipo_cliente: c.id_tipo_cliente });
    this.showClientForm.set(true);
  }

  saveClient() {
    if (this.clientForm.invalid) return;
    this.saving.set(true);
    const c = this.editingClient();
    const request = c 
      ? this.api.updateClient(c.id, this.clientForm.value)
      : this.api.createClient(this.clientForm.value);

    request.subscribe({
      next: () => {
        this.saving.set(false);
        this.api.getClients().subscribe(data => this.clients.set(data));
        this.showClientForm.set(false);
        this.snack.open(c ? 'Cliente modificado' : 'Cliente creado', 'OK', { duration: 3000 });
      },
      error: () => { this.saving.set(false); this.snack.open('Error guardando cliente', 'OK', { duration: 3000 }); }
    });
  }

  deleteClient(c: any) {
    if (!confirm(`¿Eliminar cliente "${c.cliente || c.nombre}"?`)) return;
    this.api.deleteClient(c.id).subscribe({
      next: () => this.api.getClients().subscribe(data => this.clients.set(data)),
      error: () => this.snack.open('Error al eliminar', 'OK', { duration: 3000 })
    });
  }

  manageClientCategories(c: any) {
    this.dialog.open(ClientCategoriesDialogComponent, {
      width: '760px',
      panelClass: 'premium-dialog-panel',
      data: { cliente: c }
    });
  }

  // --- Mercaderistas CRUD Methods ---
  openMercaderistaForm() {
    this.editingMercaderista.set(null);
    this.mercaderistaForm.reset({ tipo_mercaderista: 'MERCADERISTA', activo: true });
    this.showMercaderistaForm.set(true);
  }

  editMercaderista(m: any) {
    this.editingMercaderista.set(m);
    this.mercaderistaForm.patchValue({
      nombre: m.nombre || m.nombre_completo,
      cedula: m.cedula,
      telefono: m.telefono,
      tipo_mercaderista: m.tipo_mercaderista || 'MERCADERISTA',
      activo: m.activo
    });
    this.showMercaderistaForm.set(true);
  }

  saveMercaderista() {
    if (this.mercaderistaForm.invalid) return;
    this.saving.set(true);
    const m = this.editingMercaderista();
    const request = m 
      ? this.api.updateMercaderista(m.id, this.mercaderistaForm.value)
      : this.api.createMercaderista(this.mercaderistaForm.value);

    request.subscribe({
      next: () => {
        this.saving.set(false);
        this.api.getMercaderistas().subscribe(data => this.mercaderistas.set(data));
        this.showMercaderistaForm.set(false);
        this.snack.open(m ? 'Mercaderista modificado' : 'Mercaderista creado', 'OK', { duration: 3000 });
      },
      error: () => { this.saving.set(false); this.snack.open('Error guardando mercaderista', 'OK', { duration: 3000 }); }
    });
  }

  deleteMercaderista(m: any) {
    if (!confirm(`¿Eliminar mercaderista "${m.nombre || m.nombre_completo}"?`)) return;
    this.api.deleteMercaderista(m.id).subscribe({
      next: () => this.api.getMercaderistas().subscribe(data => this.mercaderistas.set(data)),
      error: () => this.snack.open('Error al eliminar', 'OK', { duration: 3000 })
    });
  }

  // --- Supervisores CRUD Methods ---
  private reloadSupervisors() {
    this.api.getSupervisorsWithAssignments().subscribe(data => this.supervisors.set(data));
  }
  openSupervisorForm() {
    this.editingSupervisor.set(null);
    this.supervisorForm.reset({ nombre: '' });
    this.showSupervisorForm.set(true);
  }
  editSupervisor(s: any) {
    this.editingSupervisor.set(s);
    this.supervisorForm.patchValue({ nombre: s.nombre });
    this.showSupervisorForm.set(true);
  }
  saveSupervisor() {
    if (this.supervisorForm.invalid) return;
    this.saving.set(true);
    const s = this.editingSupervisor();
    const payload = { nombre: this.supervisorForm.value.nombre as string };
    const request = s ? this.api.updateSupervisor(s.id, payload) : this.api.createSupervisor(payload);
    request.subscribe({
      next: () => {
        this.saving.set(false);
        this.reloadSupervisors();
        this.showSupervisorForm.set(false);
        this.snack.open(s ? 'Supervisor modificado' : 'Supervisor creado', 'OK', { duration: 3000 });
      },
      error: () => { this.saving.set(false); this.snack.open('Error guardando supervisor', 'OK', { duration: 3000 }); }
    });
  }
  deleteSupervisor(s: any) {
    if (!confirm(`¿Eliminar supervisor "${s.nombre}"?`)) return;
    this.api.deleteSupervisor(s.id).subscribe({
      next: () => this.reloadSupervisors(),
      error: () => this.snack.open('Error al eliminar', 'OK', { duration: 3000 })
    });
  }
}
