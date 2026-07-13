import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';

const ROLES_SOLICITABLES = [
  { id_rol: 1, label: 'Cliente' },
  { id_rol: 2, label: 'Analista' },
  { id_rol: 5, label: 'Mercaderista' },
  { id_rol: 6, label: 'Supervisor' },
  { id_rol: 7, label: 'Auditor' },
  { id_rol: 9, label: 'Vendedor' },
  { id_rol: 10, label: 'Atención al Cliente' },
  { id_rol: 12, label: 'Encuestador' },
  { id_rol: 14, label: 'Auditor de Campo' },
];

const TIPO_LABELS: Record<string, string> = {
  creacion_usuario: 'Nuevo usuario',
  creacion_pdv: 'Nuevo PDV',
  creacion_producto: 'Nuevo producto',
};

@Component({
  selector: 'app-atencion-cliente',
  standalone: true,
  imports: [
    CommonModule, FormsModule, MatButtonModule, MatIconModule,
    MatProgressSpinnerModule, MatSnackBarModule,
  ],
  templateUrl: './atencion-cliente.component.html',
  styleUrls: ['./atencion-cliente.component.scss']
})
export class AtencionClienteComponent implements OnInit {
  loadingSolicitudes = signal(true);
  solicitudes = signal<any[]>([]);
  today = new Date();

  isAtcOrAdmin = computed(() => this.auth.hasRole('admin', 'atc'));
  isAnalyst = computed(() => this.auth.hasRole('analyst'));

  filtroEstado = signal<string>('pendiente');
  filtroTipo = signal<string>('');
  readonly tipoLabels = TIPO_LABELS;
  readonly rolesSolicitables = ROLES_SOLICITABLES;

  // --- Formulario "nueva solicitud" (analista/admin) ---
  showForm = signal(false);
  formTipo = signal<'creacion_usuario' | 'creacion_pdv' | 'creacion_producto'>('creacion_usuario');
  submitting = signal(false);

  usuarioForm = { username: '', email: '', id_rol: null as number | null, id_perfil: null as number | null, password: '' };
  pdvForm = { nombre: '', direccion: '', latitud: '', longitud: '', rif: '' };
  productoForm = {
    producto_gu: '', cod_prod: '', descripcion_bi: '', gramos: null as number | null,
    inagotable: false, comentario: '',
    id_subcategoria: null as number | null, id_marca: null as number | null,
    id_presentacion: null as number | null, id_clasificacion_tamano: null as number | null,
  };

  clientesList = signal<any[]>([]);
  categoriasList = signal<any[]>([]);
  subcategoriasList = signal<any[]>([]);
  marcasList = signal<any[]>([]);
  presentacionesList = signal<any[]>([]);
  tamanosList = signal<any[]>([]);

  // --- Panel "editar/completar al aprobar" (ATC/admin) — disponible para
  // cualquier tipo de solicitud pendiente: el vendedor/analista puede no haber
  // mandado todos los datos, o ATC puede necesitar corregir algo antes de
  // insertar. Se pre-llena con lo que mandó el solicitante.
  editandoId = signal<number | null>(null);
  completarForm: Record<string, any> = {};

  constructor(private api: ApiService, private snack: MatSnackBar, private auth: AuthService) {}

  ngOnInit(): void {
    this.cargarSolicitudes();
    if (this.isAnalyst() || this.isAtcOrAdmin()) {
      this.api.getClients().subscribe({ next: d => this.clientesList.set(d), error: () => {} });
      this.api.getCatalogosCategorias().subscribe({ next: d => this.categoriasList.set(d), error: () => {} });
      this.api.getCatalogosSubCategorias().subscribe({ next: d => this.subcategoriasList.set(d), error: () => {} });
      this.api.getCatMarcas().subscribe({ next: d => this.marcasList.set(d), error: () => {} });
      this.api.getCatPresentaciones().subscribe({ next: d => this.presentacionesList.set(d), error: () => {} });
      this.api.getCatTamanos().subscribe({ next: d => this.tamanosList.set(d), error: () => {} });
    }
  }

  cargarSolicitudes(): void {
    this.loadingSolicitudes.set(true);
    this.api.getSolicitudes(this.filtroEstado() || undefined, this.filtroTipo() || undefined).subscribe({
      next: (data) => { this.solicitudes.set(data); this.loadingSolicitudes.set(false); },
      error: () => this.loadingSolicitudes.set(false)
    });
  }

  onFiltroChange(): void {
    this.cargarSolicitudes();
  }

  toggleForm(): void {
    this.showForm.update(v => !v);
  }

  enviarSolicitud(): void {
    let descripcion: Record<string, any>;
    const tipo = this.formTipo();
    if (tipo === 'creacion_usuario') {
      if (!this.usuarioForm.username || !this.usuarioForm.password || !this.usuarioForm.id_rol) {
        this.snack.open('Usuario, contraseña y rol son requeridos', 'OK', { duration: 3000 });
        return;
      }
      descripcion = { ...this.usuarioForm };
    } else if (tipo === 'creacion_pdv') {
      if (!this.pdvForm.nombre || !this.pdvForm.direccion || !this.pdvForm.latitud || !this.pdvForm.longitud) {
        this.snack.open('Nombre, dirección y coordenadas son requeridos', 'OK', { duration: 3000 });
        return;
      }
      descripcion = { ...this.pdvForm };
    } else {
      if (!this.productoForm.producto_gu) {
        this.snack.open('El nombre del producto es requerido', 'OK', { duration: 3000 });
        return;
      }
      descripcion = { ...this.productoForm };
    }

    this.submitting.set(true);
    this.api.crearSolicitud({ tipo, descripcion: JSON.stringify(descripcion) }).subscribe({
      next: () => {
        this.submitting.set(false);
        this.showForm.set(false);
        this.resetForms();
        this.snack.open('Solicitud enviada', 'OK', { duration: 2000 });
        this.cargarSolicitudes();
      },
      error: (err) => {
        this.submitting.set(false);
        this.snack.open(err?.error?.detail || 'Error al enviar la solicitud', 'OK', { duration: 3000 });
      }
    });
  }

  private resetForms(): void {
    this.usuarioForm = { username: '', email: '', id_rol: null, id_perfil: null, password: '' };
    this.pdvForm = { nombre: '', direccion: '', latitud: '', longitud: '', rif: '' };
    this.productoForm = {
      producto_gu: '', cod_prod: '', descripcion_bi: '', gramos: null,
      inagotable: false, comentario: '',
      id_subcategoria: null, id_marca: null, id_presentacion: null, id_clasificacion_tamano: null,
    };
  }

  parseDescripcion(raw: string): Record<string, any> {
    try { return JSON.parse(raw) || {}; } catch { return {}; }
  }

  /** Entradas de la descripción sin las fotos (que se muestran aparte como imágenes). */
  descripcionEntries(raw: string): [string, any][] {
    return Object.entries(this.parseDescripcion(raw)).filter(([k]) => k !== 'foto_tienda' && k !== 'foto_rif');
  }

  fotoTienda(raw: string): string | null { return this.parseDescripcion(raw)['foto_tienda'] || null; }
  fotoRif(raw: string): string | null { return this.parseDescripcion(raw)['foto_rif'] || null; }

  verFotoGrande(dataUrl: string): void {
    const w = window.open('', '_blank');
    if (w) w.document.write(`<img src="${dataUrl}" style="max-width:100%">`);
  }

  /** Abre el panel de edición pre-llenado con lo que mandó el solicitante
   * (normaliza nombres de campo: el vendedor manda punto_de_interes/jerarquia_nivel_2_2,
   * el analista manda nombre/jerarquia_n2_2 — el panel siempre edita con los
   * nombres normalizados que espera el backend). */
  iniciarEdicion(sol: any): void {
    const datos = this.parseDescripcion(sol.descripcion);
    if (sol.tipo === 'creacion_pdv') {
      this.completarForm = {
        nombre: datos['nombre'] ?? datos['punto_de_interes'] ?? '',
        direccion: datos['direccion'] ?? datos['Direccion'] ?? '',
        latitud: datos['latitud'] ?? '',
        longitud: datos['longitud'] ?? '',
        rif: datos['rif'] ?? '',
        jerarquia_n2_2: datos['jerarquia_n2_2'] ?? datos['jerarquia_nivel_2_2'] ?? '',
        jerarquia_n2: datos['jerarquia_n2'] ?? datos['jerarquia_nivel_2'] ?? '',
        departamento: datos['departamento'] ?? '',
        ciudad: datos['ciudad'] ?? '',
        cadena: datos['cadena'] ?? datos['clasificacion_de_canal'] ?? '',
        nivel_de_alcance: datos['nivel_de_alcance'] ?? '',
        radio: datos['radio'] ?? '',
      };
    } else {
      this.completarForm = { ...datos };
    }
    this.editandoId.set(sol.id);
  }

  cancelarEdicion(): void {
    this.editandoId.set(null);
    this.completarForm = {};
  }

  /** Aprueba directamente con los datos originales (sin abrir el panel de edición). */
  aprobar(sol: any): void {
    this.confirmarAprobacion(sol, {});
  }

  /** Confirma la aprobación desde el panel de edición, con los campos editados por ATC. */
  confirmarConEdicion(sol: any): void {
    this.confirmarAprobacion(sol, { ...this.completarForm });
  }

  private confirmarAprobacion(sol: any, completar: object): void {
    this.api.aprobarSolicitud(sol.id, completar).subscribe({
      next: () => {
        this.solicitudes.update(ss => ss.map(s => s.id === sol.id ? { ...s, estado: 'aprobada' } : s));
        this.cancelarEdicion();
        this.snack.open('Solicitud aprobada', 'OK', { duration: 2000 });
      },
      error: (err) => this.snack.open(err?.error?.detail || 'No se pudo aprobar la solicitud', 'OK', { duration: 3000 })
    });
  }

  rechazar(id: number): void {
    this.api.rechazarSolicitud(id).subscribe({
      next: () => {
        this.solicitudes.update(ss => ss.map(s => s.id === id ? { ...s, estado: 'rechazada' } : s));
        this.cancelarEdicion();
        this.snack.open('Solicitud rechazada', 'OK', { duration: 2000 });
      }
    });
  }

  getSolicitudClasses(estado: string): string {
    const map: Record<string, string> = {
      aprobada: 'bg-emerald-100 text-emerald-700',
      rechazada: 'bg-rose-100 text-rose-700',
      pendiente: 'bg-amber-100 text-amber-700'
    };
    return map[estado] ?? 'bg-slate-100 text-slate-500';
  }
}
