import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { ActivatedRoute } from '@angular/router';
import { environment } from '../../../environments/environment';
import { ConfirmService } from '../../shared/components/confirm-dialog/confirm.service';

@Component({
  selector: 'app-supervisor-encuestadores',
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule, MatSnackBarModule],
  templateUrl: './supervisor-encuestadores.component.html',
  styleUrls: ['./supervisor-encuestadores.component.scss']
})
export class SupervisorEncuestadoresComponent implements OnInit {
  private http = inject(HttpClient);
  private snack = inject(MatSnackBar);
  private confirmSvc = inject(ConfirmService);
  private sanitizer = inject(DomSanitizer);
  private route = inject(ActivatedRoute);
  private API = `${environment.apiUrl}/api/supervisor-encuestadores`;

  isStandaloneDetailView = false;
  activeTab = signal<'jornadas' | 'encuestas' | 'medicos'>('jornadas');
  loading = signal(false);

  // Catálogos / Filtros
  encuestadores = signal<any[]>([]);
  selectedUserFilter = signal<number | null>(null);
  searchEncuestadorQuery = 'Todos los encuestadores';
  showEncuestadorDropdown = false;

  // Form Searchable Selects
  searchJornadaUserQuery = '';
  showJornadaUserDropdown = false;
  searchEncuestaUserQuery = '';
  showEncuestaUserDropdown = false;

  // Filtros de fecha y estado
  startDateFilter = signal<string>('');
  endDateFilter = signal<string>('');
  statusJornadaFilter = signal<'all' | 'active' | 'finished'>('all');
  statusEncuestaFilter = signal<'all' | 'correction' | 'ok'>('all');

  // Location Modal
  showLocationModal = false;
  selectedJornadaForLocation: any = null;

  // Journey Detail Modal
  showJornadaDetailModal = false;
  currentJornadaDetail: any = null;

  // Medico Detail Modal
  showMedicoDetailModal = false;
  currentMedicoDetail: any = null;

  // Listas de datos
  jornadas = signal<any[]>([]);
  encuestas = signal<any[]>([]);
  medicos = signal<any[]>([]);
  centros = signal<any[]>([]); // Para selector de centros en nueva encuesta

  // Búsqueda de médicos
  searchQueryMedicos = '';
  medicoSuggestions = signal<any[]>([]);
  showMedicoDropdown = false;
  medicoSearchLoading = signal(false);
  private medicoDebounceTimer: any = null;

  // Control de Modales
  showJornadaModal = false;
  showEncuestaModal = false;
  showMedicoModal = false;

  // Formularios en Modal
  currentJornada: any = {};
  currentEncuesta: any = {};
  currentMedico: any = { consultorios: [] };
  diasList = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];

  ngOnInit(): void {
    this.loadEncuestadores();
    this.loadCentros();

    this.route.queryParams.subscribe(params => {
      if (params['jornadaId']) {
        this.isStandaloneDetailView = true;
        this.verDetalleJornadaStandalone(Number(params['jornadaId']));
      } else {
        this.isStandaloneDetailView = false;
        this.loadData();
      }
    });
  }

  loadEncuestadores(): void {
    this.http.get<any[]>(`${this.API}/encuestadores`).subscribe({
      next: (res) => this.encuestadores.set(res),
      error: () => this.snack.open('Error al cargar encuestadores', 'OK', { duration: 3000 })
    });
  }

  filteredEncuestadoresForSearch() {
    const q = this.searchEncuestadorQuery.toLowerCase().trim();
    if (!q || q === 'todos los encuestadores') {
      return this.encuestadores();
    }
    return this.encuestadores().filter(u =>
      (u.nombre || '').toLowerCase().includes(q) ||
      (u.username || '').toLowerCase().includes(q)
    );
  }

  selectEncuestador(u: any): void {
    if (u) {
      this.selectedUserFilter.set(u.id);
      this.searchEncuestadorQuery = u.nombre;
    } else {
      this.selectedUserFilter.set(null);
      this.searchEncuestadorQuery = 'Todos los encuestadores';
    }
    this.loadData();
  }

  onFocusSearch(): void {
    if (this.searchEncuestadorQuery === 'Todos los encuestadores') {
      this.searchEncuestadorQuery = '';
    }
    this.showEncuestadorDropdown = true;
  }

  hideDropdownWithDelay(): void {
    setTimeout(() => {
      this.showEncuestadorDropdown = false;
      if (!this.searchEncuestadorQuery) {
        const selected = this.encuestadores().find(x => x.id === this.selectedUserFilter());
        this.searchEncuestadorQuery = selected ? selected.nombre : 'Todos los encuestadores';
      }
    }, 200);
  }

  // --- JORNADA FORM USER DROPDOWN ---
  filteredEncuestadoresForJornada() {
    const q = this.searchJornadaUserQuery.toLowerCase().trim();
    if (!q) return this.encuestadores();
    return this.encuestadores().filter(u =>
      (u.nombre || '').toLowerCase().includes(q) ||
      (u.username || '').toLowerCase().includes(q)
    );
  }

  selectEncuestadorForJornada(u: any): void {
    this.currentJornada.id_usuario = u.id;
    this.searchJornadaUserQuery = u.nombre;
    this.showJornadaUserDropdown = false;
  }

  onFocusSearchJornada(): void {
    this.searchJornadaUserQuery = '';
    this.showJornadaUserDropdown = true;
  }

  hideJornadaDropdownWithDelay(): void {
    setTimeout(() => {
      this.showJornadaUserDropdown = false;
      const selected = this.encuestadores().find(x => x.id === this.currentJornada.id_usuario);
      this.searchJornadaUserQuery = selected ? selected.nombre : '';
    }, 200);
  }

  // --- ENCUESTA FORM USER DROPDOWN ---
  filteredEncuestadoresForEncuesta() {
    const q = this.searchEncuestaUserQuery.toLowerCase().trim();
    if (!q) return this.encuestadores();
    return this.encuestadores().filter(u =>
      (u.nombre || '').toLowerCase().includes(q) ||
      (u.username || '').toLowerCase().includes(q)
    );
  }

  selectEncuestadorForEncuesta(u: any): void {
    this.currentEncuesta.id_usuario = u.id;
    this.searchEncuestaUserQuery = u.nombre;
    this.showEncuestaUserDropdown = false;
  }

  onFocusSearchEncuesta(): void {
    this.searchEncuestaUserQuery = '';
    this.showEncuestaUserDropdown = true;
  }

  hideEncuestaDropdownWithDelay(): void {
    setTimeout(() => {
      this.showEncuestaUserDropdown = false;
      const selected = this.encuestadores().find(x => x.id === this.currentEncuesta.id_usuario);
      this.searchEncuestaUserQuery = selected ? selected.nombre : '';
    }, 200);
  }

  // --- LOCATION MAPS MODAL ---
  openLocationModal(j: any): void {
    this.selectedJornadaForLocation = j;
    this.showLocationModal = true;
  }

  getGoogleMapsUrl(lat: number, lng: number): SafeResourceUrl {
    return this.sanitizer.bypassSecurityTrustResourceUrl(`https://maps.google.com/maps?q=${lat},${lng}&z=15&output=embed`);
  }

  filteredJornadas() {
    let list = this.jornadas();

    // Filtro por fecha
    if (this.startDateFilter()) {
      const start = new Date(this.startDateFilter() + 'T00:00:00');
      list = list.filter(j => j.fecha_inicio && new Date(j.fecha_inicio) >= start);
    }
    if (this.endDateFilter()) {
      const end = new Date(this.endDateFilter() + 'T23:59:59');
      list = list.filter(j => j.fecha_inicio && new Date(j.fecha_inicio) <= end);
    }

    // Filtro por estado
    if (this.statusJornadaFilter() === 'active') {
      list = list.filter(j => j.estado === 'En Progreso');
    } else if (this.statusJornadaFilter() === 'finished') {
      list = list.filter(j => j.estado === 'Finalizada');
    }

    return list;
  }

  filteredEncuestas() {
    let list = this.encuestas();

    // Filtro por fecha
    if (this.startDateFilter()) {
      const start = new Date(this.startDateFilter() + 'T00:00:00');
      list = list.filter(e => e.fecha_verificacion && new Date(e.fecha_verificacion) >= start);
    }
    if (this.endDateFilter()) {
      const end = new Date(this.endDateFilter() + 'T23:59:59');
      list = list.filter(e => e.fecha_verificacion && new Date(e.fecha_verificacion) <= end);
    }

    // Filtro por corrección
    if (this.statusEncuestaFilter() === 'correction') {
      list = list.filter(e => e.requiere_correccion);
    } else if (this.statusEncuestaFilter() === 'ok') {
      list = list.filter(e => !e.requiere_correccion);
    }

    return list;
  }

  clearFilters(): void {
    this.startDateFilter.set('');
    this.endDateFilter.set('');
    this.statusJornadaFilter.set('all');
    this.statusEncuestaFilter.set('all');
  }

  verDetalleJornada(idJornada: number): void {
    // Abrir detalle en una pestaña nueva del navegador
    const currentHref = window.location.href.split('?')[0];
    const url = `${currentHref}?jornadaId=${idJornada}`;
    window.open(url, '_blank');
  }

  verDetalleJornadaStandalone(idJornada: number): void {
    this.loading.set(true);
    this.http.get<any>(`${this.API}/jornadas/${idJornada}/detalle`).subscribe({
      next: (res) => {
        this.currentJornadaDetail = res;
        this.loading.set(false);
      },
      error: () => {
        this.snack.open('Error al obtener el detalle de la jornada', 'OK', { duration: 3000 });
        this.loading.set(false);
      }
    });
  }

  closeStandaloneWindow(): void {
    window.close();
  }

  verDetalleMedico(m: any): void {
    this.currentMedicoDetail = JSON.parse(JSON.stringify(m));
    this.showMedicoDetailModal = true;
  }

  parseHorarios(horariosJson: string): any[] {
    try {
      if (!horariosJson) return [];
      const parsed = JSON.parse(horariosJson);
      if (Array.isArray(parsed)) {
        return parsed.map(x => ({
          dia: x.dia || x.day || '',
          inicio: x.inicio || x.start || '',
          fin: x.fin || x.end || ''
        }));
      }
      const list: any[] = [];
      const diasOrder = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];
      for (const d of diasOrder) {
        if (parsed[d] && parsed[d].activo) {
          list.push({
            dia: d,
            inicio: parsed[d].desde || '',
            fin: parsed[d].hasta || ''
          });
        }
      }
      return list;
    } catch {
      return [];
    }
  }

  puedeEditarMedico(m: any): boolean {
    if (this.isStandaloneDetailView && this.currentJornadaDetail) {
      return this.currentJornadaDetail.estado !== 'Aprobada';
    }
    return this.esMedicoReciente(m);
  }

  esMedicoReciente(m: any): boolean {
    if (!m) return false;

    if (this.isStandaloneDetailView && this.currentJornadaDetail) {
      if (this.currentJornadaDetail.estado === 'Aprobada') return false;
      if (!m.fecha_registro || !this.currentJornadaDetail.fecha_inicio) return false;
      const docReg = new Date(m.fecha_registro);
      const jStart = new Date(this.currentJornadaDetail.fecha_inicio);
      return docReg.getTime() >= (jStart.getTime() - 24 * 60 * 60 * 1000);
    }

    if (!m.fecha_registro) return false;
    const docReg = new Date(m.fecha_registro);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return docReg.getTime() >= today.getTime();
  }

  filterCentrosForClinica(query: string): any[] {
    const q = (query || '').toLowerCase().trim();
    if (!q) return this.centros();
    return this.centros().filter(item =>
      (item.nombre_centro || '').toLowerCase().includes(q)
    );
  }

  selectClinicaForConsultorio(c: any, item: any): void {
    c.nombre_clinica = item.nombre_centro;
    c.showDropdown = false;
  }

  hideClinicaDropdownWithDelay(c: any): void {
    setTimeout(() => {
      c.showDropdown = false;
    }, 200);
  }

  aprobarJornada(id: number): void {
    this.confirmSvc.confirm(
      '¿Estás seguro de aprobar esta jornada? Esto bloqueará cualquier cambio posterior en sus encuestas y médicos.',
      { title: 'Aprobar Jornada', confirmText: 'Aprobar', danger: false }
    ).then(ok => {
      if (!ok) return;
      this.loading.set(true);
      const j = this.jornadas().find(x => x.id_jornada === id);
      if (j) {
        const updated = { ...j, estado: 'Aprobada' };
        this.http.put(`${this.API}/jornadas/${id}`, updated).subscribe({
          next: () => {
            this.snack.open('Jornada aprobada con éxito', 'OK', { duration: 2000 });
            this.loadData();
          },
          error: () => {
            this.snack.open('Error al aprobar jornada', 'OK', { duration: 3000 });
            this.loading.set(false);
          }
        });
      }
    });
  }

  aprobarEncuesta(e: any): void {
    this.confirmSvc.confirm(
      '¿Estás seguro de aprobar esta encuesta? Esto resolverá cualquier observación de corrección y la bloqueará.',
      { title: 'Aprobar Encuesta', confirmText: 'Aprobar', danger: false }
    ).then(ok => {
      if (!ok) return;
      this.loading.set(true);
      const updated = {
        ...e,
        estado: 'Aprobada',
        requiere_correccion: false,
        observacion_supervisor: ''
      };
      this.http.put(`${this.API}/encuestas/${e.id_encuesta}`, updated).subscribe({
        next: () => {
          this.snack.open('Encuesta aprobada con éxito', 'OK', { duration: 2000 });
          this.loadData();
        },
        error: () => {
          this.snack.open('Error al aprobar encuesta', 'OK', { duration: 3000 });
          this.loading.set(false);
        }
      });
    });
  }

  loadCentros(): void {
    this.http.get<any>(`${this.API}/centros`).subscribe({
      next: (res) => this.centros.set(res.centros || []),
      error: () => { }
    });
  }

  loadData(): void {
    this.loading.set(true);
    const userId = this.selectedUserFilter();
    const params: any = {};
    if (userId) params.user_id = userId;

    if (this.activeTab() === 'jornadas') {
      this.http.get<any[]>(`${this.API}/jornadas`, { params }).subscribe({
        next: (res) => { this.jornadas.set(res); this.loading.set(false); },
        error: () => { this.snack.open('Error al cargar jornadas', 'OK', { duration: 3000 }); this.loading.set(false); }
      });
    } else if (this.activeTab() === 'encuestas') {
      this.http.get<any[]>(`${this.API}/encuestas`, { params }).subscribe({
        next: (res) => { this.encuestas.set(res); this.loading.set(false); },
        error: () => { this.snack.open('Error al cargar encuestas', 'OK', { duration: 3000 }); this.loading.set(false); }
      });
    } else if (this.activeTab() === 'medicos') {
      this.http.get<any[]>(`${this.API}/medicos`, { params: { q: this.searchQueryMedicos } }).subscribe({
        next: (res) => { this.medicos.set(res); this.loading.set(false); },
        error: () => { this.snack.open('Error al cargar médicos', 'OK', { duration: 3000 }); this.loading.set(false); }
      });
    }
  }

  /** Autocomplete del buscador de médicos: sugiere al escribir (con debounce)
   *  y permite abrir el detalle directo sin recargar toda la grilla. */
  onMedicoSearchInput(): void {
    if (this.medicoDebounceTimer) clearTimeout(this.medicoDebounceTimer);
    const q = this.searchQueryMedicos.trim();
    if (q.length < 2) {
      this.medicoSuggestions.set([]);
      this.showMedicoDropdown = false;
      this.medicoSearchLoading.set(false);
      return;
    }
    this.showMedicoDropdown = true;
    this.medicoSearchLoading.set(true);
    this.medicoDebounceTimer = setTimeout(() => {
      this.http.get<any[]>(`${this.API}/medicos`, { params: { q } }).subscribe({
        next: (res) => {
          this.medicoSuggestions.set((res || []).slice(0, 8));
          this.medicoSearchLoading.set(false);
        },
        error: () => {
          this.medicoSuggestions.set([]);
          this.medicoSearchLoading.set(false);
        }
      });
    }, 250);
  }

  selectMedicoSuggestion(m: any): void {
    const nombre = [m.apellido1, m.apellido2, m.nombre1, m.nombre2].filter(Boolean).join(' ');
    this.searchQueryMedicos = `${m.id_medico_externo} — ${nombre}`;
    this.showMedicoDropdown = false;
    this.medicoSuggestions.set([]);
    this.verDetalleMedico(m);
  }

  clearMedicoSearch(): void {
    this.searchQueryMedicos = '';
    this.medicoSuggestions.set([]);
    this.showMedicoDropdown = false;
    this.loadData();
  }

  closeMedicoDropdown(): void {
    // Pequeño retraso para que el click en una sugerencia se registre antes de cerrar
    setTimeout(() => {
      this.showMedicoDropdown = false;
    }, 150);
  }

  onFilterChange(userId: any): void {
    this.selectedUserFilter.set(userId ? Number(userId) : null);
    this.loadData();
  }

  switchTab(tab: 'jornadas' | 'encuestas' | 'medicos'): void {
    this.activeTab.set(tab);
    this.loadData();
  }

  // --- CRUD JORNADAS ---

  openJornadaModal(jornada?: any): void {
    if (jornada) {
      this.currentJornada = { ...jornada };
      const selected = this.encuestadores().find(x => x.id === this.currentJornada.id_usuario);
      this.searchJornadaUserQuery = selected ? selected.nombre : 'Desconocido';
    } else {
      const defaultUser = this.encuestadores()[0];
      this.currentJornada = {
        id_usuario: defaultUser?.id || 0,
        fecha_inicio: new Date().toISOString().substring(0, 16),
        estado: 'En Progreso',
        latitud: null,
        longitud: null,
        ciudad: '',
        estado_geo: '',
        notas: ''
      };
      this.searchJornadaUserQuery = defaultUser ? defaultUser.nombre : '';
    }
    this.showJornadaModal = true;
  }

  saveJornada(): void {
    if (!this.currentJornada.id_usuario || !this.currentJornada.fecha_inicio || !this.currentJornada.estado) {
      this.snack.open('Faltan campos requeridos', 'OK', { duration: 2500 });
      return;
    }

    this.loading.set(true);
    const isEdit = !!this.currentJornada.id_jornada;
    const req = this.http.request(
      isEdit ? 'PUT' : 'POST',
      isEdit ? `${this.API}/jornadas/${this.currentJornada.id_jornada}` : `${this.API}/jornadas`,
      { body: this.currentJornada }
    );

    req.subscribe({
      next: () => {
        this.snack.open(`Jornada ${isEdit ? 'actualizada' : 'creada'} con éxito`, 'OK', { duration: 2000 });
        this.showJornadaModal = false;
        this.loadData();
      },
      error: (err) => {
        this.snack.open('Error al guardar la jornada: ' + (err.error?.detail || err.message), 'OK', { duration: 3000 });
        this.loading.set(false);
      }
    });
  }

  deleteJornada(id: number): void {
    this.confirmSvc.confirm(
      '¿Estás seguro de eliminar esta jornada? Se eliminarán todas las encuestas y visitas asociadas a ella.',
      { title: 'Eliminar Jornada', confirmText: 'Eliminar', danger: true }
    ).then(ok => {
      if (!ok) return;
      this.loading.set(true);
      this.http.delete(`${this.API}/jornadas/${id}`).subscribe({
        next: () => {
          this.snack.open('Jornada eliminada', 'OK', { duration: 2000 });
          this.loadData();
        },
        error: () => {
          this.snack.open('Error al eliminar jornada', 'OK', { duration: 3000 });
          this.loading.set(false);
        }
      });
    });
  }

  // --- CRUD ENCUESTAS ---

  openEncuestaModal(encuesta?: any): void {
    if (encuesta) {
      this.currentEncuesta = {
        ...encuesta,
        fecha_verificacion: encuesta.fecha_verificacion ? encuesta.fecha_verificacion.substring(0, 10) : ''
      };
      const selected = this.encuestadores().find(x => x.id === this.currentEncuesta.id_usuario);
      this.searchEncuestaUserQuery = selected ? selected.nombre : 'Desconocido';
    } else {
      const defaultUser = this.encuestadores()[0];
      this.currentEncuesta = {
        id_usuario: defaultUser?.id || 0,
        id_centro: this.centros()[0]?.id_centro || 0,
        fecha_verificacion: new Date().toISOString().substring(0, 10),
        fuente_informacion: 'Visita presencial',
        notas_generales: '',
        estado: 'Cerrada',
        observacion_supervisor: '',
        requiere_correccion: false
      };
      this.searchEncuestaUserQuery = defaultUser ? defaultUser.nombre : '';
    }
    this.showEncuestaModal = true;
  }

  saveEncuesta(): void {
    if (!this.currentEncuesta.id_usuario || !this.currentEncuesta.id_centro || !this.currentEncuesta.fecha_verificacion) {
      this.snack.open('Campos requeridos vacíos', 'OK', { duration: 2500 });
      return;
    }

    this.loading.set(true);
    const isEdit = !!this.currentEncuesta.id_encuesta;
    const req = this.http.request(
      isEdit ? 'PUT' : 'POST',
      isEdit ? `${this.API}/encuestas/${this.currentEncuesta.id_encuesta}` : `${this.API}/encuestas`,
      { body: this.currentEncuesta }
    );

    req.subscribe({
      next: () => {
        this.snack.open(`Encuesta ${isEdit ? 'actualizada' : 'creada'} exitosamente`, 'OK', { duration: 2000 });
        this.showEncuestaModal = false;
        this.loadData();
      },
      error: (err) => {
        this.snack.open('Error al guardar encuesta: ' + (err.error?.detail || err.message), 'OK', { duration: 3000 });
        this.loading.set(false);
      }
    });
  }

  deleteEncuesta(id: number): void {
    this.confirmSvc.confirm(
      '¿Estás seguro de eliminar esta encuesta? Se desvincularán los médicos registrados en ella.',
      { title: 'Eliminar Encuesta', confirmText: 'Eliminar', danger: true }
    ).then(ok => {
      if (!ok) return;
      this.loading.set(true);
      this.http.delete(`${this.API}/encuestas/${id}`).subscribe({
        next: () => {
          this.snack.open('Encuesta eliminada', 'OK', { duration: 2000 });
          this.loadData();
        },
        error: () => {
          this.snack.open('Error al eliminar la encuesta', 'OK', { duration: 3000 });
          this.loading.set(false);
        }
      });
    });
  }

  // --- CRUD MEDICOS ---

  getEmptyHorarios(): any {
    const horarios: any = {};
    for (const d of this.diasList) {
      horarios[d] = { activo: false, desde: '08:00', hasta: '12:00' };
    }
    return horarios;
  }

  getHorariosObject(horariosJson: string): any {
    const empty = this.getEmptyHorarios();
    try {
      if (!horariosJson) return empty;
      const parsed = JSON.parse(horariosJson);
      if (Array.isArray(parsed)) {
        for (const x of parsed) {
          const dia = x.dia || x.day || '';
          if (empty[dia]) {
            empty[dia].activo = true;
            empty[dia].desde = x.inicio || x.start || '08:00';
            empty[dia].hasta = x.fin || x.end || '12:00';
          }
        }
        return empty;
      }
      for (const d of this.diasList) {
        if (parsed[d]) {
          empty[d].activo = !!parsed[d].activo;
          empty[d].desde = parsed[d].desde || '08:00';
          empty[d].hasta = parsed[d].hasta || '12:00';
        }
      }
      return empty;
    } catch {
      return empty;
    }
  }

  openMedicoModal(medico?: any, idEncuesta?: number): void {
    if (medico) {
      this.currentMedico = JSON.parse(JSON.stringify(medico));
      (this.currentMedico.consultorios || []).forEach((c: any) => {
        c.horarios = this.getHorariosObject(c.horarios_json);
      });
    } else {
      this.currentMedico = {
        id_encuesta: idEncuesta || 0,
        id_medico_externo: '',
        apellido1: '',
        apellido2: '',
        nombre1: '',
        nombre2: '',
        especialidad: '',
        sub_especialidad: '',
        universidad_graduacion: '',
        nro_MPPS: '',
        nro_colegiado: '',
        ciudad: '',
        estado: '',
        telefono: '',
        whatsapp: '',
        email: '',
        linkedin: '',
        instagram: '',
        consultorios: []
      };
    }
    this.showMedicoModal = true;
  }

  addConsultorio(): void {
    this.currentMedico.consultorios.push({
      nombre_clinica: '',
      piso_consultorio: '',
      direccion_especifica: '',
      horarios: this.getEmptyHorarios(),
      valor_consulta_rango: 'Menos de 30$',
      promedio_pacientes_semanal_rango: '1 a 5 pacientes'
    });
  }

  removeConsultorio(idx: number): void {
    this.currentMedico.consultorios.splice(idx, 1);
  }

  saveMedico(): void {
    if (!this.currentMedico.id_medico_externo || !this.currentMedico.apellido1 || !this.currentMedico.nombre1 || !this.currentMedico.especialidad) {
      this.snack.open('Campos obligatorios del médico faltantes', 'OK', { duration: 2500 });
      return;
    }

    this.loading.set(true);
    const isEdit = !!this.currentMedico.id_medico;

    const payload: any = { ...this.currentMedico };
    payload.consultorios = (this.currentMedico.consultorios || []).map((c: any) => ({
      nombre_clinica: c.nombre_clinica,
      piso_consultorio: c.piso_consultorio,
      direccion_especifica: c.direccion_especifica,
      valor_consulta_rango: c.valor_consulta_rango,
      promedio_pacientes_semanal_rango: c.promedio_pacientes_semanal_rango,
      horarios_json: JSON.stringify(c.horarios || this.getEmptyHorarios())
    }));

    const req = isEdit
      ? this.http.put(`${this.API}/medicos/${this.currentMedico.id_medico}`, payload)
      : this.http.post(`${this.API}/medicos`, {
        id_encuesta: this.currentMedico.id_encuesta,
        medico_data: payload
      });

    req.subscribe({
      next: () => {
        this.snack.open(`Médico ${isEdit ? 'actualizado' : 'registrado'} con éxito`, 'OK', { duration: 2000 });
        this.showMedicoModal = false;
        this.loadData();
      },
      error: (err) => {
        this.snack.open('Error al guardar médico: ' + (err.error?.detail || err.message), 'OK', { duration: 3000 });
        this.loading.set(false);
      }
    });
  }

  deleteMedicoRelacion(idMedico: number, idEncuesta: number): void {
    this.confirmSvc.confirm(
      '¿Estás seguro de desvincular a este médico de la encuesta?',
      { title: 'Desvincular Médico', confirmText: 'Desvincular', danger: true }
    ).then(ok => {
      if (!ok) return;
      this.loading.set(true);
      this.http.delete(`${this.API}/medicos/${idMedico}?id_encuesta=${idEncuesta}`).subscribe({
        next: () => {
          this.snack.open('Médico desvinculado de la encuesta', 'OK', { duration: 2000 });
          this.loadData();
        },
        error: () => {
          this.snack.open('Error al desvincular médico', 'OK', { duration: 3000 });
          this.loading.set(false);
        }
      });
    });
  }
}
