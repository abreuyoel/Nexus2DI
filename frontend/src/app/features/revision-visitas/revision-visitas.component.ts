import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';
import { RealtimeService } from '../../core/services/realtime.service';
import { VisitThreadDialogComponent } from '../chat/visit-thread-dialog.component';

type Periodo = 'hoy' | 'semana' | 'mes';
type PhotoFilter = 'todas' | 'pendientes' | 'aprobadas' | 'rechazadas';

@Component({
  selector: 'app-revision-visitas',
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule, MatProgressSpinnerModule, MatSnackBarModule, MatTooltipModule, MatDialogModule],
  templateUrl: './revision-visitas.component.html',
})
export class RevisionVisitasComponent implements OnInit {
  loading = signal(true);
  visitas = signal<any[]>([]);
  periodo: Periodo | 'custom' = 'semana';
  desde = '';
  hasta = '';
  search = '';
  // Filtros (dropdowns)
  filtroRutas: string[] = [];          // multi-select
  filtroPunto = '';
  filtroCliente = '';
  filtroMercaderistas: string[] = [];  // multi-select
  filtroChat = ''; // '', 'con', 'sin'
  filtroEstado = ''; // '', 'Pendiente', 'Revisado', 'Aprobada'
  rutasDropdownOpen = signal(false);
  mercaderistasDropdownOpen = signal(false);

  // Modal de revisión
  reviewOpen = signal(false);
  selectedVisita = signal<any>(null);
  photos = signal<any[]>([]);
  photosLoading = signal(false);
  photoFilter: PhotoFilter = 'todas';
  grupoSel: string = 'all';             // grupo de fotos seleccionado en el modal
  modalGrupos: any[] = [];              // grupos presentes en la visita abierta
  tipoLabels: Record<number, string> = {};
  comparar = true;                      // vista comparativa Antes/Después
  readonly ANTES_IDS = [1, 4, 8];       // Antes / Exhib. Antes / POP Antes
  readonly DESPUES_IDS = [2, 7, 10];    // Despues / Exhib. Después / POP Después

  // Multi-razón de rechazo
  rejectReasons = signal<{ id: number; razon: string }[]>([]);
  rejectDialogOpen = signal(false);
  rejectingPhoto: any = null;
  selectedReasonIds: number[] = [];
  rejecting = signal(false);

  // Lightbox
  lightboxUrl = signal<string | null>(null);

  constructor(
    private api: ApiService, private snack: MatSnackBar, private auth: AuthService, private realtime: RealtimeService,
    private dialog: MatDialog, private router: Router,
  ) {}

  private rtDebounce?: any;

  ngOnInit(): void {
    const r = this.rangeFor('semana');
    this.desde = r.desde; this.hasta = r.hasta;
    this.load();
    this.api.getRejectReasons().subscribe({ next: (rs) => this.rejectReasons.set(rs || []), error: () => {} });
    // Tiempo real: nuevas visitas a revisar / cambios de fotos llegan solos
    this.realtime.events$.subscribe(ev => {
      if (ev.tipo.startsWith('visit.') || ev.tipo.startsWith('photo.')) {
        if (this.reviewOpen()) return; // no interrumpir una revisión en curso
        clearTimeout(this.rtDebounce);
        this.rtDebounce = setTimeout(() => this.load(), 800);
      }
    });
  }

  private rangeFor(p: Periodo): { desde: string; hasta: string } {
    const hoy = new Date();
    const fmt = (d: Date) => d.toISOString().slice(0, 10);
    if (p === 'hoy') return { desde: fmt(hoy), hasta: fmt(hoy) };
    const d = new Date(hoy);
    d.setDate(d.getDate() - (p === 'semana' ? 6 : 29));
    return { desde: fmt(d), hasta: fmt(hoy) };
  }

  setPeriodo(p: Periodo): void {
    this.periodo = p;
    const r = this.rangeFor(p);
    this.desde = r.desde; this.hasta = r.hasta;
    this.load();
  }

  onDateChange(): void { this.periodo = 'custom'; this.load(); }

  load(): void {
    this.loading.set(true);
    this.api.getReviewList({ desde: this.desde, hasta: this.hasta }).subscribe({
      next: (d) => { this.visitas.set(d || []); this.loading.set(false); },
      error: () => { this.visitas.set([]); this.loading.set(false); },
    });
  }

  // ── Opciones de filtros (valores distintos del set cargado) ──
  private distinct(key: string, source: any[] = this.visitas()): string[] {
    return Array.from(new Set(source.map(v => v[key]).filter(x => x != null && x !== ''))).sort();
  }
  // Rutas/puntos/mercaderistas se escopan al cliente ya elegido: si filtras
  // por "Laboratorios Fisa" primero, estos 3 dropdowns solo muestran lo que
  // pertenece a ese cliente, no la lista global de todos los clientes.
  private get visitasDelClienteFiltrado(): any[] {
    return this.filtroCliente
      ? this.visitas().filter(v => v.cliente === this.filtroCliente)
      : this.visitas();
  }
  get rutasOpts(): string[] { return this.distinct('ruta', this.visitasDelClienteFiltrado); }
  get puntosOpts(): string[] { return this.distinct('punto_de_interes', this.visitasDelClienteFiltrado); }
  get clientesOpts(): string[] { return this.distinct('cliente'); }
  get mercaderistasOpts(): string[] { return this.distinct('mercaderista', this.visitasDelClienteFiltrado); }

  /** Al cambiar de cliente, las selecciones de ruta/punto/mercaderista
   * previas pueden ya no pertenecer al cliente nuevo -- se limpian para no
   * dejar un filtro "fantasma" que no matchea nada. */
  onClienteFiltroChange(): void {
    this.filtroRutas = []; this.filtroPunto = ''; this.filtroMercaderistas = [];
  }

  toggleRutaFiltro(r: string): void {
    const i = this.filtroRutas.indexOf(r);
    if (i >= 0) this.filtroRutas.splice(i, 1); else this.filtroRutas.push(r);
  }
  toggleMercaderistaFiltro(m: string): void {
    const i = this.filtroMercaderistas.indexOf(m);
    if (i >= 0) this.filtroMercaderistas.splice(i, 1); else this.filtroMercaderistas.push(m);
  }

  clearFilters(): void {
    this.search = ''; this.filtroRutas = []; this.filtroPunto = '';
    this.filtroCliente = ''; this.filtroMercaderistas = []; this.filtroChat = ''; this.filtroEstado = '';
    this.rutasDropdownOpen.set(false); this.mercaderistasDropdownOpen.set(false);
  }

  /** Visita 100% aprobada: tiene fotos revisables y todas quedaron Aprobada
   * (nada pendiente ni rechazado). */
  private esAprobada(v: any): boolean {
    return (v.fotos_revisar || 0) > 0 && v.aprobadas === v.fotos_revisar;
  }

  get filtered(): any[] {
    const s = this.search.trim().toLowerCase();
    return this.visitas().filter(v => {
      if (this.filtroRutas.length && !this.filtroRutas.includes(v.ruta)) return false;
      if (this.filtroPunto && v.punto_de_interes !== this.filtroPunto) return false;
      if (this.filtroCliente && v.cliente !== this.filtroCliente) return false;
      if (this.filtroMercaderistas.length && !this.filtroMercaderistas.includes(v.mercaderista)) return false;
      if (this.filtroChat === 'con' && !v.tiene_chat) return false;
      if (this.filtroChat === 'sin' && v.tiene_chat) return false;
      if (this.filtroEstado === 'Aprobada') { if (!this.esAprobada(v)) return false; }
      else if (this.filtroEstado && v.estado !== this.filtroEstado) return false;
      if (s && !(
        (v.cliente || '').toLowerCase().includes(s) ||
        (v.mercaderista || '').toLowerCase().includes(s) ||
        (v.punto_de_interes || '').toLowerCase().includes(s) ||
        (v.ruta || '').toLowerCase().includes(s) ||
        String(v.id_visita).includes(s)
      )) return false;
      return true;
    });
  }

  get stats() {
    const f = this.filtered;
    const fotos = f.reduce((a, v) => a + (v.fotos_revisar || 0), 0);
    const apr = f.reduce((a, v) => a + (v.aprobadas || 0), 0);
    const rec = f.reduce((a, v) => a + (v.rechazadas || 0), 0);
    const sin = f.reduce((a, v) => a + (v.sin_revisar || 0), 0);
    return {
      visitas: f.length, fotos, aprobadas: apr, rechazadas: rec, sin_revisar: sin,
      progreso: fotos ? Math.round(apr / fotos * 1000) / 10 : 0,
    };
  }

  pct(v: any): number {
    const t = v.fotos_revisar || 0;
    return t ? Math.round((v.aprobadas || 0) / t * 100) : 0;
  }

  // Agrupación de tipos de foto (para no mostrar tantos chips)
  readonly GRUPOS: { key: string; label: string; icon: string; ids: number[]; revisable: boolean }[] = [
    { key: 'gestion',      label: 'Gestión',              icon: 'photo_camera',  ids: [1, 2],  revisable: true  },
    { key: 'exhibiciones', label: 'Exhibiciones',         icon: 'view_carousel', ids: [4, 7],  revisable: true  },
    { key: 'pop',          label: 'Material POP',         icon: 'campaign',      ids: [8, 10], revisable: true  },
    { key: 'precio',       label: 'Precio',               icon: 'sell',          ids: [3],     revisable: true  },
    { key: 'activacion',   label: 'Activación / Desact.', icon: 'bolt',          ids: [5, 6],  revisable: false },
  ];

  /** Agrupa el desglose `v.tipos` en grupos con total/rechazadas, omitiendo los vacíos. */
  gruposDe(v: any): any[] {
    const tipos: any[] = v?.tipos || [];
    const out: any[] = [];
    const used = new Set<number>();
    for (const g of this.GRUPOS) {
      const items = tipos.filter(t => g.ids.includes(t.id_tipo_foto));
      if (!items.length) continue;
      items.forEach(t => used.add(t.id_tipo_foto));
      out.push({
        key: g.key, label: g.label, icon: g.icon, revisable: g.revisable,
        ids: items.map(t => t.id_tipo_foto),
        total: items.reduce((a, t) => a + (t.total || 0), 0),
        rechazadas: items.reduce((a, t) => a + (t.rechazadas || 0), 0),
      });
    }
    const otros = tipos.filter(t => !used.has(t.id_tipo_foto));
    if (otros.length) {
      out.push({
        key: 'otros', label: 'Otros', icon: 'image', revisable: true,
        ids: otros.map(t => t.id_tipo_foto),
        total: otros.reduce((a, t) => a + (t.total || 0), 0),
        rechazadas: otros.reduce((a, t) => a + (t.rechazadas || 0), 0),
      });
    }
    return out;
  }

  // ── Modal ──────────────────────────────────────────────
  openReview(v: any, grupoKey?: string): void {
    this.selectedVisita.set(v);
    this.photoFilter = 'todas';
    this.modalGrupos = this.gruposDe(v);
    this.tipoLabels = {};
    (v.tipos || []).forEach((t: any) => this.tipoLabels[t.id_tipo_foto] = t.label);
    // grupo inicial: el del chip pulsado, o el primero revisable, o todos
    this.grupoSel = grupoKey ?? (this.modalGrupos.find(g => g.revisable)?.key ?? 'all');
    this.reviewOpen.set(true);
    this.photosLoading.set(true);
    this.api.getVisitPhotos(v.id_visita).subscribe({
      next: (ph) => { this.photos.set(ph as any[]); this.photosLoading.set(false); },
      error: () => { this.photos.set([]); this.photosLoading.set(false); },
    });
  }
  closeReview(): void {
    this.reviewOpen.set(false);
    this.selectedVisita.set(null); this.photos.set([]); this.modalGrupos = [];
  }

  setGrupoSel(key: string): void { this.grupoSel = key; this.photoFilter = 'todas'; }
  isReviewable(f: any): boolean { return ![5, 6].includes(f.id_tipo_foto); }

  estadoDe(f: any): string { return f?.estado ?? 'pendiente'; }
  isAprobada(f: any): boolean { return this.estadoDe(f) === 'Aprobada'; }
  isRechazada(f: any): boolean { return this.estadoDe(f) === 'Rechazada'; }

  /** Aprobar/Rechazar se guarda EN VIVO: el cliente las ve a medida que se aprueban. */
  setDecision(f: any, estado: 'Aprobada' | 'Rechazada'): void {
    if (!f || this.estadoDe(f) === estado) return;
    const prev = f.estado;
    this.photos.update(list => list.map(x => x.id === f.id ? { ...x, estado } : x));
    const req = estado === 'Aprobada'
      ? this.api.approvePhotos([f.id])
      : this.api.rejectPhoto(f.id, 'Rechazada por analista');
    req.subscribe({
      next: () => this.syncVisitaCounts(),
      error: () => {
        this.photos.update(list => list.map(x => x.id === f.id ? { ...x, estado: prev } : x));
        this.snack.open('No se pudo guardar el cambio', 'OK', { duration: 3000 });
      },
    });
  }

  /** Refleja al instante los conteos en la tarjeta de la lista. */
  private syncVisitaCounts(): void {
    const v = this.selectedVisita(); if (!v) return;
    const rev = this.photos().filter(f => this.isReviewable(f));
    const apr = rev.filter(f => f.estado === 'Aprobada').length;
    const rec = rev.filter(f => f.estado === 'Rechazada').length;
    const upd = { aprobadas: apr, rechazadas: rec, sin_revisar: Math.max(rev.length - apr - rec, 0) };
    this.visitas.update(list => list.map(x => x.id_visita === v.id_visita ? { ...x, ...upd } : x));
  }

  // ── Rechazo con múltiples razones ─────────────────────────
  promptReject(f: any): void {
    this.rejectingPhoto = f;
    this.selectedReasonIds = Array.isArray(f?.razones_ids) ? [...f.razones_ids] : [];
    this.rejectDialogOpen.set(true);
  }
  toggleReason(id: number): void {
    const i = this.selectedReasonIds.indexOf(id);
    if (i >= 0) this.selectedReasonIds.splice(i, 1); else this.selectedReasonIds.push(id);
  }
  isReasonSel(id: number): boolean { return this.selectedReasonIds.includes(id); }
  cancelReject(): void { this.rejectDialogOpen.set(false); this.rejectingPhoto = null; this.selectedReasonIds = []; }

  confirmReject(): void {
    const f = this.rejectingPhoto;
    if (!f || this.selectedReasonIds.length === 0) {
      this.snack.open('Selecciona al menos una razón', 'OK', { duration: 2500 }); return;
    }
    const ids = [...this.selectedReasonIds];
    const nombres = this.rejectReasons().filter(r => ids.includes(r.id)).map(r => r.razon);
    const prev = { estado: f.estado, razones: f.razones, razones_ids: f.razones_ids, rechazado_por_nombre: f.rechazado_por_nombre };
    const quien = this.auth.currentUser()?.username || 'Tú';
    this.photos.update(list => list.map(x => x.id === f.id ? { ...x, estado: 'Rechazada', razones: nombres, razones_ids: ids, rechazado_por_nombre: quien } : x));
    this.rejecting.set(true);
    this.api.rejectPhoto(f.id, '', ids).subscribe({
      next: () => {
        this.rejecting.set(false); this.rejectDialogOpen.set(false);
        this.rejectingPhoto = null; this.selectedReasonIds = [];
        this.syncVisitaCounts();
      },
      error: () => {
        this.photos.update(list => list.map(x => x.id === f.id ? { ...x, ...prev } : x));
        this.rejecting.set(false);
        this.snack.open('No se pudo rechazar', 'OK', { duration: 3000 });
      },
    });
  }

  // ── Marcar Revisada ──────────────────────────────────────
  revisando = signal(false);
  get isRevisada(): boolean { return !!this.selectedVisita()?.revisada; }
  toggleRevisada(): void {
    const v = this.selectedVisita(); if (!v) return;
    const next = !v.revisada;
    this.revisando.set(true);
    this.api.markVisitReviewed(v.id_visita, next).subscribe({
      next: () => {
        v.revisada = next; v.estado = next ? 'Revisado' : 'Pendiente'; this.selectedVisita.set({ ...v });
        this.visitas.update(list => list.map(x => x.id_visita === v.id_visita ? { ...x, revisada: next, estado: next ? 'Revisado' : 'Pendiente' } : x));
        this.revisando.set(false);
        this.snack.open(next ? 'Visita marcada como revisada' : 'Marca de revisada quitada', 'OK', { duration: 2500 });
      },
      error: () => { this.revisando.set(false); this.snack.open('No se pudo actualizar', 'OK', { duration: 3000 }); },
    });
  }

  // ── Chat por visita (sub-hilo de CHAT_GRUPOS: solo equipo / equipo+cliente) ─
  // Mismas tablas que AppWeb v1 y la APK del mercaderista — el botón navega
  // al ChatComponent con el sub-hilo ya auto-provisionado. El chat legacy
  // del cliente (tab "Cliente" del inbox) no se toca.
  openChat(): void {
    const v = this.selectedVisita();
    if (!v?.id_visita) return;
    const ref = this.dialog.open(VisitThreadDialogComponent, {
      data: { visitaId: v.id_visita, puntoNombre: v.punto_de_interes },
      autoFocus: false,
    });
    ref.afterClosed().subscribe(thread => {
      if (thread?.id_grupo) {
        this.router.navigate(['/chat'], { queryParams: {
          grupo_cliente: thread.id_cliente, tipo_grupo: thread.tipo_grupo,
          grupo_visita: thread.id_visita, titulo: thread.titulo,
        } });
      }
    });
  }

  // fotos del grupo seleccionado en el modal
  private photosByGrupo(): any[] {
    const ph = this.photos();
    if (this.grupoSel === 'all') return ph;
    const ids: number[] = this.modalGrupos.find(g => g.key === this.grupoSel)?.ids || [];
    return ph.filter(f => ids.includes(f.id_tipo_foto));
  }
  get grupoTotal(): number { return this.photosByGrupo().length; }

  get filteredPhotos(): any[] {
    const ph = this.photosByGrupo();
    if (this.photoFilter === 'todas') return ph;
    return ph.filter(f => {
      const e = this.estadoDe(f);
      if (this.photoFilter === 'aprobadas') return e === 'Aprobada';
      if (this.photoFilter === 'rechazadas') return e === 'Rechazada';
      return e !== 'Aprobada' && e !== 'Rechazada'; // pendientes
    });
  }

  countBy(estado: 'Aprobada' | 'Rechazada' | 'pendiente'): number {
    return this.photosByGrupo().filter(f => {
      const e = this.estadoDe(f);
      if (estado === 'pendiente') return e !== 'Aprobada' && e !== 'Rechazada';
      return e === estado;
    }).length;
  }

  tipoLabel(id: number): string { return this.tipoLabels[id] || ('Tipo ' + id); }

  // ── Comparación Antes / Después ───────────────────────────
  private estadoMatch(f: any): boolean {
    if (this.photoFilter === 'todas') return true;
    const e = this.estadoDe(f);
    if (this.photoFilter === 'aprobadas') return e === 'Aprobada';
    if (this.photoFilter === 'rechazadas') return e === 'Rechazada';
    return e !== 'Aprobada' && e !== 'Rechazada';
  }

  /** El grupo seleccionado tiene fotos de Antes y de Después → se puede comparar. */
  get groupHasPairs(): boolean {
    const ph = this.photosByGrupo();
    return ph.some(f => this.ANTES_IDS.includes(f.id_tipo_foto)) &&
           ph.some(f => this.DESPUES_IDS.includes(f.id_tipo_foto));
  }

  get showCompare(): boolean { return this.comparar && this.groupHasPairs; }

  /** Empareja la N-ésima foto "Antes" con la N-ésima "Después" (orden por id). */
  get comparePairs(): { antes: any; despues: any }[] {
    const ph = this.photosByGrupo();
    const byId = (a: any, b: any) => (a.id || 0) - (b.id || 0);
    const antes = ph.filter(f => this.ANTES_IDS.includes(f.id_tipo_foto) && this.estadoMatch(f)).sort(byId);
    const despues = ph.filter(f => this.DESPUES_IDS.includes(f.id_tipo_foto) && this.estadoMatch(f)).sort(byId);
    const n = Math.max(antes.length, despues.length);
    const pairs: { antes: any; despues: any }[] = [];
    for (let i = 0; i < n; i++) pairs.push({ antes: antes[i] || null, despues: despues[i] || null });
    return pairs;
  }

  openLightbox(url: string | null | undefined): void { if (url) this.lightboxUrl.set(url); }
  closeLightbox(): void { this.lightboxUrl.set(null); }
}
