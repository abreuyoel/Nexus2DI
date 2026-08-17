import { Component, OnInit, OnDestroy, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { Subscription } from 'rxjs';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';
import { RealtimeService } from '../../core/services/realtime.service';
import { VisitThreadDialogComponent } from '../chat/visit-thread-dialog.component';
import { AuthImgDirective } from '../../shared/directives/auth-img.directive';

type Periodo = 'hoy' | 'semana' | 'mes';
type PhotoFilter = 'todas' | 'pendientes' | 'aprobadas' | 'rechazadas';

@Component({
  selector: 'app-revision-visitas',
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule, MatProgressSpinnerModule, MatSnackBarModule, MatTooltipModule, MatDialogModule, AuthImgDirective],
  templateUrl: './revision-visitas.component.html',
  styleUrls: ['./revision-visitas.component.scss'],
})
export class RevisionVisitasComponent implements OnInit, OnDestroy {
  loading = signal(true);
  visitas = signal<any[]>([]);
  isClientePuro = signal(false);

  // ─── Realtime: Pending Events (pulse + sonido + auto-refresh) ──────────────
  pendingEvents = signal(0);
  hasPendingUpdates = signal(false);
  private autoRefreshInterval?: any;
  private audioCtx?: AudioContext;
  // Roster de mercaderistas (vía MERCADERISTAS -> MERCADERISTAS_RUTAS ->
  // RUTA_PROGRAMACION -> CLIENTES): se muestra primero, antes que las
  // tarjetas de visitas -- incluye mercaderistas sin visitas todavía. Sin
  // cliente elegido trae el de todos los clientes visibles (ordenado por
  // sin_revisar en `rosterFiltrado`); al elegir cliente se reescopa server-side.
  loadingRoster = signal(true);
  mercaderistasRoster = signal<any[]>([]);
  selectedMercaderista = signal<any>(null);
  // Catálogo liviano {id_cliente, cliente} para poblar el selector "Cliente"
  // completo (incluye clientes sin ninguna visita todavía) y resolver el id
  // que necesita /review-mercaderistas a partir del nombre elegido.
  clientesCatalogo = signal<{ id_cliente: number; cliente: string }[]>([]);
  periodo: Periodo | 'custom' = 'hoy';
  desde = '';
  hasta = '';
  search = '';
  // Filtros (dropdowns)
  filtroRutas: string[] = [];          // multi-select
  filtroPunto = '';
  filtroCliente = '';
  filtroDepartamento = '';
  filtroMercaderistas: string[] = [];  // multi-select
  filtroChat = ''; // '', 'con', 'sin'
  filtroEstado = ''; // '', 'Pendiente', 'Revisado', 'Aprobada'
  rutasDropdownOpen = signal(false);
  mercaderistasDropdownOpen = signal(false);

  // ─── Paginación client-side ─────────────────────────────────────────────
  // El backend ya trae todo el set filtrado por rango de fechas (y cliente
  // cuando aplica). Paginar en el cliente evita re-consultar el servidor en
  // cada cambio de página y mantiene la búsqueda/filtros instantáneos.
  readonly PAGE_ROSTER = 12;    // tarjetas de mercaderistas por página
  readonly PAGE_VISITAS = 9;    // tarjetas de visitas por página
  rosterPage = signal(1);
  visitasPage = signal(1);

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
  ) { }

  private rtSubscription?: Subscription;

  ngOnInit(): void {
    this.isClientePuro.set(this.auth.currentUser()?.id_rol === 1);
    const r = this.rangeFor('hoy');
    this.desde = r.desde; this.hasta = r.hasta;
    this.load();
    this.loadRoster();
    this.api.getRejectReasons().subscribe({ next: (rs) => this.rejectReasons.set(rs || []), error: () => { } });
    this.api.getCentroMandoClientes().subscribe({
      next: (res) => {
        if (this.isClientePuro()) {
          const myId = this.auth.currentUser()?.id_perfil;
          this.clientesCatalogo.set(res.clientes?.filter((c: any) => c.id_cliente === myId) || []);
          this.filtroCliente = this.clientesCatalogo()[0]?.cliente || '';
          this.onClienteFiltroChange();
        } else {
          this.clientesCatalogo.set(res?.clientes || []);
        }
      },
      error: () => {},
    });
    // Tiempo real: acumular eventos y mostrar indicador visual (pulse),
    // en vez de refrescar agresivamente cada 800ms.
    this.rtSubscription = this.realtime.events$.subscribe(ev => {
      if (ev.tipo.startsWith('visit.') || ev.tipo.startsWith('photo.')) {
        if (this.reviewOpen()) return; // no interrumpir una revisión en curso
        const prev = this.pendingEvents();
        this.pendingEvents.set(prev + 1);
        if (!this.hasPendingUpdates()) {
          this.hasPendingUpdates.set(true);
          this.playNotifSound();
        }
      }
    });

    // Auto-refresh silencioso cada 60s SI hay eventos pendientes
    this.autoRefreshInterval = setInterval(() => {
      if (this.hasPendingUpdates() && !this.reviewOpen()) {
        this.dismissAndRefresh();
      }
    }, 60_000);
  }

  ngOnDestroy(): void {
    this.rtSubscription?.unsubscribe();
    clearInterval(this.autoRefreshInterval);
  }

  /** Refresca y resetea el indicador de actualizaciones pendientes. */
  dismissAndRefresh(): void {
    this.pendingEvents.set(0);
    this.hasPendingUpdates.set(false);
    this.resetPages();
    this.load();
    this.loadRoster();
  }

  /** Redirige a Auditoría de Data (misma SPA, carga lazy → rápido). Si se pasa
   *  una visita (o hay una en revisión), va directo a su revisión de data. */
  openAuditoriaData(visita?: any): void {
    const src = visita ?? this.selectedVisita();
    const id = src?.id_visita ?? src?.id;
    this.router.navigate(['/auditoria-data'], {
      queryParams: id ? { visita: id } : {},
    });
  }

  /** Vuelve a la página 1 de ambos niveles (roster y visitas). */
  private resetPages(): void { this.rosterPage.set(1); this.visitasPage.set(1); }

  goRosterPage(p: number): void { this.rosterPage.set(Math.max(1, Math.min(p, this.totalRosterPages))); }
  goVisitasPage(p: number): void { this.visitasPage.set(Math.max(1, Math.min(p, this.totalVisitasPages))); }

  private playNotifSound(): void {
    try {
      if (!this.audioCtx) {
        this.audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
      }
      const ctx = this.audioCtx;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.frequency.value = 880;
      osc.type = 'sine';
      gain.gain.setValueAtTime(0.15, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.3);
    } catch {
      // Silenciar errores de audio (autoplay policy, etc.)
    }
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
    this.visitasPage.set(1);
    this.api.getReviewList({ desde: this.desde, hasta: this.hasta }).subscribe({
      next: (d) => { this.visitas.set(d || []); this.loading.set(false); },
      error: () => { this.visitas.set([]); this.loading.set(false); },
    });
  }

  /** Roster (no depende del rango de fechas): quién está asignado a rutas
   * activas, tenga o no visitas cargadas todavía. Sin cliente_id trae el de
   * todos los clientes visibles para el usuario -- es el default de la
   * pantalla, ordenado en `rosterFiltrado` por quién tiene más sin revisar. */
  private loadRoster(clienteId?: number): void {
    this.loadingRoster.set(true);
    this.rosterPage.set(1);
    this.api.getReviewMercaderistas(clienteId ? { cliente_id: clienteId } : {}).subscribe({
      next: (rs) => { this.mercaderistasRoster.set(rs || []); this.loadingRoster.set(false); },
      error: () => { this.mercaderistasRoster.set([]); this.loadingRoster.set(false); },
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
  private get rosterDelClienteFiltrado(): any[] {
    return this.filtroCliente
      ? this.mercaderistasRoster().filter(r => r.cliente === this.filtroCliente)
      : this.mercaderistasRoster();
  }
  // Clientes/rutas/mercaderistas salen de la UNIÓN visitas+roster: el roster
  // trae asignaciones aunque todavía no haya ni una visita cargada (por eso
  // no basta con derivarlos solo de `visitas()`, que solo tiene fotos ya
  // subidas -- HAVING revisar > 0 en review-list).
  get rutasOpts(): string[] {
    const b = this.rosterDelClienteFiltrado.map(r => r.ruta).filter((x): x is string => !!x);
    return Array.from(new Set([...this.distinct('ruta', this.visitasDelClienteFiltrado), ...b])).sort();
  }
  get puntosOpts(): string[] { return this.distinct('punto_de_interes', this.visitasDelClienteFiltrado); }
  get clientesOpts(): string[] {
    const b = this.clientesCatalogo().map(c => c.cliente).filter((x): x is string => !!x);
    return Array.from(new Set([...this.distinct('cliente'), ...b])).sort();
  }
  get mercaderistasOpts(): string[] {
    const b = this.rosterDelClienteFiltrado.map(r => r.mercaderista).filter((x): x is string => !!x);
    return Array.from(new Set([...this.distinct('mercaderista', this.visitasDelClienteFiltrado), ...b])).sort();
  }
  /** El roster trae "departamentos" como un solo string ("Miranda, Distrito
   * Capital") por ruta -- son los departamentos de los PDV de esa ruta. Acá
   * se separan para armar la lista de opciones del filtro. */
  get departamentosOpts(): string[] {
    const set = new Set<string>();
    for (const r of this.rosterDelClienteFiltrado) {
      (r.departamentos || '').split(',').map((d: string) => d.trim()).filter(Boolean).forEach((d: string) => set.add(d));
    }
    return Array.from(set).sort();
  }

  /** Al cambiar de cliente, las selecciones de ruta/punto/mercaderista
   * previas pueden ya no pertenecer al cliente nuevo -- se limpian para no
   * dejar un filtro "fantasma" que no matchea nada. Volver también a la
   * vista de mercaderistas (el mercaderista elegido era de otro cliente), y
   * repedir el roster escopado a ese cliente (o al global si se limpió el
   * filtro). */
  onClienteFiltroChange(): void {
    this.filtroRutas = []; this.filtroPunto = ''; this.filtroMercaderistas = []; this.filtroDepartamento = '';
    this.selectedMercaderista.set(null);
    if (!this.filtroCliente) { this.loadRoster(); return; }
    const c = this.clientesCatalogo().find(x => x.cliente === this.filtroCliente);
    if (c) this.loadRoster(c.id_cliente); else this.mercaderistasRoster.set([]);
  }

  /** Roster filtrado por cliente/ruta/mercaderista/búsqueda -- es lo que se
   * muestra POR DEFECTO en vez de las tarjetas de visitas. Cada fila trae
   * sus stats (visitas/fotos/sin_revisar) ya calculadas contra el rango de
   * fechas activo, y quedan ordenadas por quién tiene más fotos sin revisar
   * primero -- así se ve de un vistazo a quién hay que atender. */
  /** Roster + mercaderistas que TIENEN visitas en el período pero no salen en
   *  el roster (sin ruta activa asignada, ruta dada de baja, etc.). Sin esto
   *  sus visitas quedaban inalcanzables: contaban en las tarjetas de arriba
   *  (VISITAS/FOTOS salen de review-list) pero no había ninguna tarjeta que
   *  abrir, y la pantalla decía "No hay mercaderistas asignados con estos
   *  filtros" con el contador en 1. Reportado en campo como "busqué esa visita
   *  y no me sale la tarjeta". */
  private get rosterConVisitasHuerfanas(): any[] {
    const roster = this.mercaderistasRoster();
    const vistos = new Set(roster.map(r => `${r.id_mercaderista}_${r.cliente}`));
    const extra: any[] = [];
    for (const v of this.visitas()) {
      const k = `${v.id_mercaderista}_${v.cliente}`;
      if (vistos.has(k)) continue;
      vistos.add(k);
      extra.push({
        id_mercaderista: v.id_mercaderista, mercaderista: v.mercaderista,
        id_cliente: v.id_cliente, cliente: v.cliente,
        ruta: v.ruta, departamentos: v.ciudad || '',
        _sinRuta: true,   // se marca en la tarjeta: tiene visitas pero no ruta activa
      });
    }
    return [...roster, ...extra];
  }

  /** Agrega las visitas por mercaderista+cliente en UNA sola pasada: así el
   * `rosterFiltrado` no recorre el array completo de visitas por cada tarjeta
   * (antes era O(roster × visitas), lo que se notaba lento con muchos datos). */
  private get statsPorMercaderista(): Map<string, { visitas: number; fotos: number; aprobadas: number; sin_revisar: number }> {
    const map = new Map<string, { visitas: number; fotos: number; aprobadas: number; sin_revisar: number }>();
    for (const v of this.visitas()) {
      const k = `${v.id_mercaderista}_${v.cliente}`;
      const acc = map.get(k) || { visitas: 0, fotos: 0, aprobadas: 0, sin_revisar: 0 };
      acc.visitas += 1;
      acc.fotos += v.fotos_revisar || 0;
      acc.aprobadas += v.aprobadas || 0;
      acc.sin_revisar += v.sin_revisar || 0;
      map.set(k, acc);
    }
    return map;
  }

  get rosterFiltrado(): any[] {
    const s = this.search.trim().toLowerCase();
    const stats = this.statsPorMercaderista;
    return this.rosterConVisitasHuerfanas
      .filter(r => {
        if (this.filtroCliente && r.cliente !== this.filtroCliente) return false;
        if (this.filtroRutas.length && !this.filtroRutas.includes(r.ruta)) return false;
        if (this.filtroMercaderistas.length && !this.filtroMercaderistas.includes(r.mercaderista)) return false;
        if (this.filtroDepartamento && !(r.departamentos || '').split(',').map((d: string) => d.trim()).includes(this.filtroDepartamento)) return false;
        if (s && !((r.mercaderista || '').toLowerCase().includes(s) || (r.cliente || '').toLowerCase().includes(s))) return false;
        return true;
      })
      .map(r => ({ ...r, _stats: stats.get(`${r.id_mercaderista}_${r.cliente}`) || { visitas: 0, fotos: 0, aprobadas: 0, sin_revisar: 0 } }))
      .sort((a, b) => {
        if (b._stats.sin_revisar !== a._stats.sin_revisar) return b._stats.sin_revisar - a._stats.sin_revisar;
        if (b._stats.visitas !== a._stats.visitas) return b._stats.visitas - a._stats.visitas;
        return (a.mercaderista || '').localeCompare(b.mercaderista || '');
      });
  }

  // ── Paginación (roster y visitas) ──────────────────────────────────────
  // El clamp implícito evita páginas vacías: si un filtro reduce el total,
  // se aterriza automáticamente a la última página disponible.
  get totalRosterPages(): number { return Math.max(1, Math.ceil(this.rosterFiltrado.length / this.PAGE_ROSTER)); }
  get rosterPaginado(): any[] {
    const page = Math.min(this.rosterPage(), this.totalRosterPages);
    const start = (page - 1) * this.PAGE_ROSTER;
    return this.rosterFiltrado.slice(start, start + this.PAGE_ROSTER);
  }
  get totalVisitasPages(): number { return Math.max(1, Math.ceil(this.filtered.length / this.PAGE_VISITAS)); }
  get visitasPaginado(): any[] {
    const page = Math.min(this.visitasPage(), this.totalVisitasPages);
    const start = (page - 1) * this.PAGE_VISITAS;
    return this.filtered.slice(start, start + this.PAGE_VISITAS);
  }

  selectMercaderista(r: any): void { this.selectedMercaderista.set(r); this.visitasPage.set(1); }
  backToRoster(): void { this.selectedMercaderista.set(null); this.rosterPage.set(1); }

  toggleRutaFiltro(r: string): void {
    const i = this.filtroRutas.indexOf(r);
    if (i >= 0) this.filtroRutas.splice(i, 1); else this.filtroRutas.push(r);
  }
  toggleMercaderistaFiltro(m: string): void {
    const i = this.filtroMercaderistas.indexOf(m);
    if (i >= 0) this.filtroMercaderistas.splice(i, 1); else this.filtroMercaderistas.push(m);
  }

  clearFilters(): void {
    const teniaCliente = !!this.filtroCliente;
    this.search = ''; this.filtroRutas = []; this.filtroPunto = '';
    this.filtroCliente = ''; this.filtroDepartamento = ''; this.filtroMercaderistas = []; this.filtroChat = ''; this.filtroEstado = '';
    this.rutasDropdownOpen.set(false); this.mercaderistasDropdownOpen.set(false);
    this.selectedMercaderista.set(null);
    if (teniaCliente) this.loadRoster();
  }

  /** Visita 100% aprobada: tiene fotos revisables y todas quedaron Aprobada
   * (nada pendiente ni rechazado). */
  private esAprobada(v: any): boolean {
    return (v.fotos_revisar || 0) > 0 && v.aprobadas === v.fotos_revisar;
  }

  get filtered(): any[] {
    const s = this.search.trim().toLowerCase();
    const sel = this.selectedMercaderista();
    return this.visitas().filter(v => {
      if (sel && v.id_mercaderista !== sel.id_mercaderista) return false;
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
    { key: 'gestion', label: 'Gestión', icon: 'photo_camera', ids: [1, 2], revisable: true },
    { key: 'exhibiciones', label: 'Exhibiciones', icon: 'view_carousel', ids: [4, 7], revisable: true },
    { key: 'pop', label: 'Material POP', icon: 'campaign', ids: [8, 10], revisable: true },
    { key: 'precio', label: 'Precio', icon: 'sell', ids: [3], revisable: true },
    { key: 'activacion', label: 'Activación / Desact.', icon: 'bolt', ids: [5, 6], revisable: false },
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
      error: (err) => {
        // Antes esto dejaba this.photos en [] sin ningún indicio de error --
        // indistinguible de una visita sin fotos, aunque los chips de arriba
        // (que salen de un endpoint distinto, el agregado de la lista) sí
        // mostraran totales > 0. Si esto vuelve a pasar, el snackbar dice
        // el motivo real en vez de "no hay fotos en este filtro".
        this.photos.set([]); this.photosLoading.set(false);
        this.snack.open(`No se pudieron cargar las fotos: ${err.error?.detail ?? err.message ?? 'error desconocido'}`, 'OK', { duration: 6000 });
      },
    });
  }
  closeReview(): void {
    this.reviewOpen.set(false);
    this.selectedVisita.set(null); this.photos.set([]); this.modalGrupos = [];
  }

  setGrupoSel(key: string): void { this.grupoSel = key; this.photoFilter = 'todas'; }
  // Cliente puro: en este panel solo ve fotos ya Aprobadas (comprobante de
  // visita), no tiene sentido ofrecerle Aprobar/Rechazar acá aunque el
  // backend técnicamente se lo permita sobre fotos de su propio cliente.
  isReviewable(f: any): boolean { return !this.isClientePuro() && ![5, 6].includes(f.id_tipo_foto); }

  /** Fila sintética que inserta el auto-cierre de las 7pm cuando el
   *  mercaderista no desactivó el PDV a mano -- no tiene foto real
   *  (file_path NULL), así que no debe renderizarse como <img>. Se detecta
   *  por Estado y también por url vacía, por si alguna quedó con otro
   *  Estado tras una revisión manual. */
  esAutoCierre(f: any): boolean {
    return this.estadoDe(f) === 'Auto-cierre' || (f?.id_tipo_foto === 6 && !f?.url);
  }

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
        this.router.navigate(['/chat'], {
          queryParams: {
            grupo_cliente: thread.id_cliente, tipo_grupo: thread.tipo_grupo,
            grupo_visita: thread.id_visita, titulo: thread.titulo,
          }
        });
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
    // Cliente puro: solo ve las fotos ya Aprobadas -- es una vista de
    // comprobante de visita, no el flujo de revisión interno. Ignora el
    // toggle de photoFilter por completo (ese toggle ni se muestra para
    // este rol, ver template).
    if (this.isClientePuro()) return ph.filter(f => this.isAprobada(f));
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
    const antes = ph.filter(f => this.ANTES_IDS.includes(f.id_tipo_foto)).sort(byId);
    const despues = ph.filter(f => this.DESPUES_IDS.includes(f.id_tipo_foto)).sort(byId);
    const n = Math.max(antes.length, despues.length);
    const pairs: { antes: any; despues: any }[] = [];

    if (this.isClientePuro()) {
      // Cliente puro: cada lado del par se muestra SOLO si está Aprobado --
      // si no existe todavía o existe pero sigue pendiente/rechazada, se
      // reemplaza por un marcador { _pendiente: true } para que la tarjeta
      // diga "Pendiente por revisión" en vez de mostrar la foto real (que
      // el cliente no debe ver antes de la aprobación) o el genérico
      // "Sin foto" (que no distingue "no existe" de "existe pero no
      // aprobada" -- desde la óptica del cliente es lo mismo: no está listo).
      for (let i = 0; i < n; i++) {
        const a = antes[i] || null, d = despues[i] || null;
        const aApr = a && this.isAprobada(a), dApr = d && this.isAprobada(d);
        if (!aApr && !dApr) continue; // nada aprobado en este par -- no se muestra
        pairs.push({ antes: aApr ? a : { _pendiente: true }, despues: dApr ? d : { _pendiente: true } });
      }
      return pairs;
    }

    // El filtro de estado se aplica DESPUÉS de emparejar, no antes. Filtrar
    // cada lista por separado (como estaba) rompía los pares: al elegir
    // "Aprobadas", un Antes aprobado cuyo Después seguía pendiente quedaba
    // emparejado contra el Después de OTRA pareja, o mostraba "Sin foto"
    // aunque la foto sí existiera -- de ahí los reportes de "solo salen
    // fotos de antes y no de después" en la pantalla de revisión.
    // Se conserva el par completo si CUALQUIERA de las dos matchea el filtro.
    for (let i = 0; i < n; i++) {
      const par = { antes: antes[i] || null, despues: despues[i] || null };
      const matchea = (par.antes && this.estadoMatch(par.antes)) || (par.despues && this.estadoMatch(par.despues));
      if (matchea) pairs.push(par);
    }
    return pairs;
  }

  openLightbox(url: string | null | undefined): void { if (url) this.lightboxUrl.set(url); }
  closeLightbox(): void { this.lightboxUrl.set(null); }
}
