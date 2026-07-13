import { Component, OnInit, signal, computed, EventEmitter, Output, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDialog, MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';
import { PhotoLightboxComponent } from '../../shared/photo-lightbox/photo-lightbox.component';

import { Router } from '@angular/router';

interface Region { region: string; }
interface Chain { cadena: string; }
interface Point { identificador: string; punto_de_interes: string; cadena: string; direccion: string; ciudad: string; }
interface PhotoItem { id_foto: number; id_tipo_foto: number; tipo_nombre: string; url: string; estado: string; fecha: string; }
interface Visit { id_visita: number; fecha: string; estado: string; mercaderista: string; total_fotos: number; fotos: PhotoItem[]; }
interface ExclusiveClient { id_cliente: number; cliente: string; id_tipo_cliente: number; }

const REGION_EMOJIS: Record<string, string> = {
  andes: '🏔️', capital: '🏛️', centro: '🌆', insular: '🏝️',
  occidente: '🌅', oriente: '🌄', llanos: '🌾', zulia: '🌴',
};
const REGION_COLORS: Record<string, string> = {
  andes: '#6366f1', capital: '#8b5cf6', centro: '#06b6d4',
  insular: '#f59e0b', occidente: '#f97316', oriente: '#ec4899',
  llanos: '#22c55e', zulia: '#14b8a6',
};

const TIPO_FOTO_CONFIG: Record<number, { icon: string; color: string; gradient: string }> = {
  1: { icon: 'edit_note', color: '#6366f1', gradient: 'linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%)' },
  2: { icon: 'edit_note', color: '#22c55e', gradient: 'linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)' },
  3: { icon: 'sell', color: '#f59e0b', gradient: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)' },
  4: { icon: 'grid_view', color: '#8b5cf6', gradient: 'linear-gradient(135deg, #ede9fe 0%, #ddd6fe 100%)' },
  8: { icon: 'inventory_2', color: '#ec4899', gradient: 'linear-gradient(135deg, #fce7f3 0%, #fbcfe8 100%)' },
  9: { icon: 'inventory_2', color: '#14b8a6', gradient: 'linear-gradient(135deg, #ccfbf1 0%, #99f6e4 100%)' },
};

type MotivoKey = 'resolucion' | 'orientacion' | 'planograma' | 'precio' | 'pop';

@Component({
  selector: 'app-photo-rejection-form',
  standalone: true,
  imports: [CommonModule, FormsModule, MatButtonModule, MatIconModule, MatFormFieldModule, MatInputModule],
  template: `
<div class="rj-form-panel">
  <!-- Header -->
  <div class="rj-header">
    <div class="rj-header-icon"><mat-icon>block</mat-icon></div>
    <div class="rj-header-text">
      <h2>Rechazar foto</h2>
      <p>Indica al menos un motivo o agrega un comentario.</p>
    </div>
    <button type="button" class="rj-close" (click)="cancel.emit()" aria-label="Cerrar">
      <mat-icon>close</mat-icon>
    </button>
  </div>

  <!-- Content -->
  <div class="rj-body">
    <div class="rj-section-title">
      <mat-icon>fact_check</mat-icon>
      <span>Motivo del rechazo</span>
      @if (countSelected() > 0) {
        <span class="rj-counter">{{ countSelected() }} seleccionado{{ countSelected() === 1 ? '' : 's' }}</span>
      }
    </div>

    <div class="rj-grid">
      @for (m of motivosList; track m.key) {
        <button type="button" class="rj-chip"
                [class.active]="motivos[m.key]"
                (click)="toggle(m.key)">
          <div class="rj-chip-check">
            <mat-icon>{{ motivos[m.key] ? 'check_circle' : 'radio_button_unchecked' }}</mat-icon>
          </div>
          <div class="rj-chip-text">
            <span class="rj-chip-icon">{{ m.icon }}</span>
            <span class="rj-chip-label">{{ m.label }}</span>
          </div>
        </button>
      }
    </div>

    <div class="rj-section-title" style="margin-top: 1.25rem;">
      <mat-icon>edit_note</mat-icon>
      <span>Comentario para el mercaderista</span>
      <span class="rj-optional">opcional</span>
    </div>

    <textarea class="rj-textarea"
              [(ngModel)]="comentario"
              rows="3"
              maxlength="500"
              placeholder="Describe el problema o da instrucciones específicas…"></textarea>
    <div class="rj-counter-text">{{ comentario.length }} / 500</div>
  </div>

  <!-- Actions -->
  <div class="rj-actions">
    <button mat-stroked-button (click)="cancel.emit()">Cancelar</button>
    <button type="button" class="rj-btn-confirm"
            [disabled]="!isValido()"
            (click)="confirmar()">
      <mat-icon>cancel</mat-icon>
      <span>Confirmar rechazo</span>
    </button>
  </div>
</div>
  `,
  styles: [`
    :host { display: block; color: inherit; height: 100%; }

    .rj-form-panel {
      width: 450px;
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
      height: 100%;
      background: #ffffff;
      color: #1e293b;
    }
    :host-context(.dark) .rj-form-panel { background: #0f172a; color: #f1f5f9; }

    @media (max-width: 768px) {
      .rj-form-panel { width: 100%; }
    }

    /* Header */
    .rj-header {
      display: flex; align-items: center; gap: 14px;
      padding: 18px 22px;
      background: linear-gradient(135deg, #e11d48 0%, #be123c 100%);
      color: #fff;
      flex-shrink: 0;
    }
    .rj-header-icon {
      width: 42px; height: 42px; border-radius: 12px;
      background: rgba(255,255,255,.18);
      display: inline-flex; align-items: center; justify-content: center;
      flex-shrink: 0;
    }
    .rj-header-icon mat-icon { font-size: 22px; width: 22px; height: 22px; }
    .rj-header-text { flex: 1; min-width: 0; }
    .rj-header-text h2 { margin: 0; font-size: 1.05rem; font-weight: 700; line-height: 1.2; }
    .rj-header-text p { margin: 2px 0 0; font-size: .8rem; opacity: .85; }
    .rj-close {
      width: 32px; height: 32px; border-radius: 50%; border: 0;
      background: rgba(0,0,0,.18); color: #fff; cursor: pointer;
      display: inline-flex; align-items: center; justify-content: center;
      transition: background .15s;
    }
    .rj-close:hover { background: rgba(0,0,0,.32); }
    .rj-close mat-icon { font-size: 18px; width: 18px; height: 18px; }

    /* Body */
    .rj-body { padding: 18px 22px 4px; flex: 1; overflow-y: auto; }

    .rj-section-title {
      display: flex; align-items: center; gap: 8px;
      font-size: .8rem; font-weight: 700;
      color: #64748b; text-transform: uppercase; letter-spacing: .04em;
      margin-bottom: 10px;
    }
    :host-context(.dark) .rj-section-title { color: #94a3b8; }
    .rj-section-title mat-icon { font-size: 18px; width: 18px; height: 18px; opacity: .8; }
    .rj-counter {
      margin-left: auto;
      background: #fee2e2; color: #b91c1c;
      padding: 2px 10px; border-radius: 999px;
      font-size: .7rem; font-weight: 700; text-transform: none; letter-spacing: 0;
    }
    :host-context(.dark) .rj-counter { background: rgba(239,68,68,.2); color: #fca5a5; }
    .rj-optional {
      margin-left: auto;
      background: #f1f5f9; color: #64748b;
      padding: 2px 10px; border-radius: 999px;
      font-size: .7rem; font-weight: 700; text-transform: none; letter-spacing: 0;
    }
    :host-context(.dark) .rj-optional { background: rgba(255,255,255,.08); color: #94a3b8; }

    /* Grid de chips */
    .rj-grid {
      display: grid; gap: 10px;
      grid-template-columns: 1fr;
    }
    .rj-chip {
      display: flex; align-items: center; gap: 10px;
      padding: 12px 14px;
      background: #f8fafc;
      border: 2px solid #e2e8f0;
      border-radius: 12px;
      color: #334155; font: inherit;
      cursor: pointer; text-align: left;
      transition: all .15s;
    }
    :host-context(.dark) .rj-chip {
      background: rgba(255,255,255,.04);
      border-color: rgba(255,255,255,.08);
      color: #cbd5e1;
    }
    .rj-chip:hover { border-color: #fda4af; background: #fff1f2; color: #be123c; }
    :host-context(.dark) .rj-chip:hover { background: rgba(244,63,94,.08); border-color: rgba(244,63,94,.4); color: #fda4af; }
    .rj-chip.active {
      border-color: #e11d48; background: linear-gradient(135deg, #fff1f2 0%, #ffe4e6 100%);
      color: #9f1239; font-weight: 700;
    }
    :host-context(.dark) .rj-chip.active {
      background: linear-gradient(135deg, rgba(225,29,72,.18) 0%, rgba(225,29,72,.10) 100%);
      border-color: #e11d48; color: #fecaca;
    }
    .rj-chip-check mat-icon { font-size: 22px; width: 22px; height: 22px; flex-shrink: 0; opacity: .55; }
    .rj-chip.active .rj-chip-check mat-icon { color: #e11d48; opacity: 1; }
    .rj-chip-text { flex: 1; display: flex; align-items: center; gap: 8px; min-width: 0; }
    .rj-chip-icon { font-size: 1.05rem; line-height: 1; }
    .rj-chip-label { font-size: .85rem; line-height: 1.2; white-space: normal; }

    /* Textarea */
    .rj-textarea {
      width: 100%; min-height: 80px; resize: vertical;
      padding: 12px 14px;
      background: #f8fafc; border: 2px solid #e2e8f0; border-radius: 12px;
      color: #1e293b; font: inherit; font-size: .9rem;
      outline: none;
      transition: border-color .15s, background .15s;
    }
    .rj-textarea:focus { border-color: #e11d48; background: #fff; }
    :host-context(.dark) .rj-textarea {
      background: rgba(255,255,255,.04); border-color: rgba(255,255,255,.08); color: #f1f5f9;
    }
    :host-context(.dark) .rj-textarea:focus { background: rgba(255,255,255,.06); }
    .rj-textarea::placeholder { color: #94a3b8; }
    .rj-counter-text {
      text-align: right; font-size: .7rem; color: #94a3b8;
      margin-top: 4px; font-weight: 600;
    }

    /* Footer / actions */
    .rj-actions {
      display: flex; justify-content: flex-end; gap: 10px;
      padding: 14px 22px 18px;
      background: #f8fafc;
      border-top: 1px solid #f1f5f9;
      flex-shrink: 0;
    }
    :host-context(.dark) .rj-actions {
      background: rgba(0,0,0,.18);
      border-top-color: rgba(255,255,255,.05);
    }
    .rj-btn-confirm {
      display: inline-flex; align-items: center; gap: 8px;
      padding: 8px 18px; border: 0; border-radius: 10px;
      background: linear-gradient(135deg, #e11d48, #be123c);
      color: #fff; font-weight: 700; font-size: .9rem; cursor: pointer;
      box-shadow: 0 4px 14px rgba(225,29,72,.35);
      transition: transform .12s, box-shadow .12s, opacity .12s;
    }
    .rj-btn-confirm:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 6px 18px rgba(225,29,72,.45); }
    .rj-btn-confirm:active:not(:disabled) { transform: translateY(0); }
    .rj-btn-confirm:disabled { opacity: .45; cursor: not-allowed; box-shadow: none; }
    .rj-btn-confirm mat-icon { font-size: 18px; width: 18px; height: 18px; }
  `]
})
export class PhotoRejectionFormComponent {
  @Input() foto!: any;
  @Output() cancel = new EventEmitter<void>();
  @Output() confirm = new EventEmitter<string>();

  motivos = {
    resolucion: false,
    orientacion: false,
    planograma: false,
    precio: false,
    pop: false
  } as Record<MotivoKey, boolean>;
  comentario = '';

  motivosList: { key: MotivoKey; label: string; icon: string }[] = [
    { key: 'resolucion',  label: 'Resolución',                   icon: '🔍' },
    { key: 'orientacion', label: 'Orientación de foto',          icon: '🔄' },
    { key: 'planograma',  label: 'Incumplimiento de planograma', icon: '📐' },
    { key: 'precio',      label: 'Falta información de precio',  icon: '🏷️' },
    { key: 'pop',         label: 'Falta material POP',           icon: '📦' },
  ];

  toggle(key: MotivoKey): void {
    this.motivos[key] = !this.motivos[key];
  }

  countSelected(): number {
    return Object.values(this.motivos).filter(Boolean).length;
  }

  isValido(): boolean {
    return this.countSelected() > 0 || this.comentario.trim().length > 0;
  }

  confirmar(): void {
    const seleccionados = [];
    if (this.motivos.resolucion) seleccionados.push('Resolución');
    if (this.motivos.orientacion) seleccionados.push('Orientación de Foto');
    if (this.motivos.planograma) seleccionados.push('Incumplimiento de Planograma');
    if (this.motivos.precio) seleccionados.push('Falta Información de Precio');
    if (this.motivos.pop) seleccionados.push('Falta Material POP');

    let stringMotivo = seleccionados.join(', ');
    if (this.comentario.trim()) {
      stringMotivo = stringMotivo ? `${stringMotivo} - ${this.comentario.trim()}` : this.comentario.trim();
    }
    
    this.confirm.emit(stringMotivo);
  }
}

@Component({
  selector: 'app-client-photos',
  standalone: true,
  imports: [
    CommonModule, FormsModule, MatCardModule, MatButtonModule, MatIconModule,
    MatProgressSpinnerModule, MatExpansionModule, MatFormFieldModule,
    MatInputModule, MatChipsModule, MatTooltipModule, MatDialogModule,
    PhotoLightboxComponent, PhotoRejectionFormComponent
  ],
  templateUrl: './client-photos.component.html',
  styleUrls: ['./client-photos.component.scss'],
})
export class ClientPhotosComponent implements OnInit {
  // State machine: 'select-client' | 'regions' | 'chains' | 'points' | 'photos'
  view = signal<'select-client' | 'regions' | 'chains' | 'points' | 'photos'>('regions');
  loading = signal(false);

  // Coordinador exclusivo
  isCoordinadorExclusivo = signal(false);
  exclusiveClients = signal<ExclusiveClient[]>([]);
  selectedExclusiveClient = signal<ExclusiveClient | null>(null);
  exclusiveClientSearch = signal('');
  filteredExclusiveClients = computed(() => {
    const term = this.exclusiveClientSearch().trim().toLowerCase();
    if (!term) return this.exclusiveClients();
    return this.exclusiveClients().filter(c =>
      (c.cliente || '').toLowerCase().includes(term)
    );
  });

  // Data
  regions = signal<Region[]>([]);
  chains = signal<Chain[]>([]);
  points = signal<Point[]>([]);
  visits = signal<Visit[]>([]);

  // Navigation context
  selectedRegion = signal<string>('');
  selectedChain = signal<string>('');
  selectedPoint = signal<Point | null>(null);

  // Search
  pointSearch = signal('');
  filteredPoints = computed(() => {
    const term = this.pointSearch().trim().toLowerCase();
    const chain = this.selectedChain().trim().toLowerCase();
    
    return this.points().filter(p => {
      const pChain = (p.cadena || '').trim().toLowerCase();
      const matchChain = !chain || pChain === chain;
      
      const pName = (p.punto_de_interes || '').toLowerCase();
      const matchTerm = !term || pName.includes(term) || pChain.includes(term);
      
      return matchChain && matchTerm;
    });
  });

  // Lightbox (delega en <app-photo-lightbox>)
  lightboxOpen = signal(false);
  lightboxPhotos = signal<PhotoItem[]>([]);
  lightboxIndex = signal(0);
  lightboxTitle = signal('');
  lightboxPhoto = computed<PhotoItem | null>(() => this.lightboxPhotos()[this.lightboxIndex()] ?? null);
  
  // Rejection sidebar state
  isRejecting = signal(false);

  // Dashboard modal
  dashboardOpen = signal(false);

  constructor(
    private api: ApiService,
    private auth: AuthService,
    private router: Router,
    private dialog: MatDialog,
  ) {}

  ngOnInit(): void {
    const u = this.auth.currentUser();
    if (u?.is_coordinador_exclusivo) {
      this.isCoordinadorExclusivo.set(true);
      this.view.set('select-client');
      this.loadExclusiveClients();
    } else {
      this.loadRegions();
    }
  }

  // ─── COORDINADOR EXCLUSIVO ───────────────────────────────────────
  private currentClienteId(): number | undefined {
    return this.selectedExclusiveClient()?.id_cliente;
  }

  loadExclusiveClients(): void {
    this.loading.set(true);
    this.api.getExclusiveClients().subscribe({
      next: data => { this.exclusiveClients.set(data); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  selectExclusiveClient(c: ExclusiveClient): void {
    this.selectedExclusiveClient.set(c);
    this.view.set('regions');
    // Resetear caches de navegación previa
    this.regions.set([]); this.chains.set([]); this.points.set([]); this.visits.set([]);
    this.selectedRegion.set(''); this.selectedChain.set(''); this.selectedPoint.set(null);
    this.loadRegions();
  }

  changeExclusiveClient(): void {
    this.selectedExclusiveClient.set(null);
    this.view.set('select-client');
  }

  // ─── DATA LOADING ─────────────────────────────────────────────────
  loadRegions(): void {
    this.loading.set(true);
    this.api.getClientRegions(this.currentClienteId()).subscribe({
      next: data => { this.regions.set(data); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  selectRegion(region: string): void {
    this.selectedRegion.set(region);
    this.selectedChain.set('');
    this.view.set('chains');
    this.loading.set(true);
    this.api.getClientChains(region, this.currentClienteId()).subscribe({
      next: data => { this.chains.set(data); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  selectChain(cadena: string): void {
    this.selectedChain.set(cadena);
    this.loadPoints();
  }

  loadPoints(): void {
    this.view.set('points');
    this.loading.set(true);
    this.api.getClientPoints(this.selectedRegion(), this.currentClienteId()).subscribe({
      next: data => { this.points.set(data); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  selectPoint(point: Point): void {
    this.selectedPoint.set(point);
    this.view.set('photos');
    this.loading.set(true);
    this.api.getClientPointVisits(point.identificador, this.currentClienteId()).subscribe({
      next: data => {
        data.forEach(v => {
          v.total_fotos = this.getAllTipos(v.fotos).reduce((acc, curr) => acc + curr.count, 0);
        });
        // El cliente solo necesita ver visitas con fotos — sin fotos no aporta nada.
        const conFotos = data.filter(v => v.total_fotos > 0);
        this.visits.set(conFotos);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  // ─── NAVIGATION ───────────────────────────────────────────────────
  goBack(): void {
    const v = this.view();
    if (v === 'photos') { this.loadPoints(); }
    else if (v === 'points') {
      // If we are filtering by chain, go back to chains. Otherwise go back to regions.
      this.view.set('chains');
    }
    else if (v === 'chains') { this.view.set('regions'); }
    else if (v === 'regions' && this.isCoordinadorExclusivo()) {
      this.changeExclusiveClient();
    }
  }

  getBreadcrumb(): string[] {
    const crumbs: string[] = ['Regiones'];
    const region = this.selectedRegion();
    const chain = this.selectedChain();
    const point = this.selectedPoint();

    if (region) crumbs.push(region);
    if (this.view() === 'points' || this.view() === 'photos') {
      crumbs.push(chain || 'Todos');
    }
    if (this.view() === 'photos' && point) {
      crumbs.push(point.punto_de_interes);
    }
    return crumbs;
  }

  // ─── HELPERS ──────────────────────────────────────────────────────
  getRegionEmoji(region: string): string {
    const normalized = region.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    for (const [key, emoji] of Object.entries(REGION_EMOJIS)) {
      if (normalized.includes(key)) return emoji;
    }
    return '📍';
  }

  getRegionColor(region: string): string {
    const normalized = region.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    for (const [key, color] of Object.entries(REGION_COLORS)) {
      if (normalized.includes(key)) return color;
    }
    return '#6366f1';
  }

  getTipoConfig(tipo: number): { icon: string; color: string; gradient: string } {
    return TIPO_FOTO_CONFIG[tipo] || { icon: 'photo', color: '#94a3b8', gradient: 'linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%)' };
  }

  groupFotosByTipo(fotos: PhotoItem[]): { tipo: number; nombre: string; fotos: PhotoItem[] }[] {
    const groups: Record<number, PhotoItem[]> = {};
    for (const f of fotos) {
      if (!groups[f.id_tipo_foto]) groups[f.id_tipo_foto] = [];
      groups[f.id_tipo_foto].push(f);
    }
    const TIPO_ORDER = [1, 2, 3, 4, 8, 9];
    return TIPO_ORDER
      .filter(t => groups[t])
      .map(t => ({ tipo: t, nombre: groups[t][0]?.tipo_nombre || 'Otro', fotos: groups[t] }));
  }

  getAllTipos(fotos: PhotoItem[]): { tipo: number; nombre: string; count: number; fotos: PhotoItem[] }[] {
    const ALL_TIPOS = [
      { tipo: 1, nombre: 'Gestión' },
      { tipo: 3, nombre: 'Precio' },
      { tipo: 4, nombre: 'Exhibiciones Adicionales' },
      { tipo: 8, nombre: 'Material POP Antes' },
      { tipo: 9, nombre: 'Material POP Después' },
    ];
    const grouped: Record<number, PhotoItem[]> = {};
    // Merge tipo 1 and 2 into "Gestión"
    for (const f of fotos) {
      const key = f.id_tipo_foto === 2 ? 1 : f.id_tipo_foto;
      if (!grouped[key]) grouped[key] = [];
      grouped[key].push(f);
    }
    return ALL_TIPOS.map(t => ({
      ...t,
      count: grouped[t.tipo]?.length || 0,
      fotos: grouped[t.tipo] || [],
    }));
  }

  // ─── LIGHTBOX ─────────────────────────────────────────────────────
  openLightbox(fotos: PhotoItem[], index: number, titulo: string = ''): void {
    if (!fotos || fotos.length === 0) return;
    this.lightboxPhotos.set(fotos);
    this.lightboxIndex.set(index);
    this.lightboxTitle.set(titulo);
    this.lightboxOpen.set(true);
  }

  closeLightbox(): void {
    this.lightboxOpen.set(false);
    this.lightboxPhotos.set([]);
    this.isRejecting.set(false);
  }

  onLightboxIndexChange(i: number): void {
    this.lightboxIndex.set(i);
    this.isRejecting.set(false);
  }

  goToChat(visitId: number): void {
    this.router.navigate(['/chat'], { queryParams: { visita: visitId } });
  }

  approvePhoto(foto: PhotoItem): void {
    this.api.approvePhotos([foto.id_foto]).subscribe({
      next: () => {
        foto.estado = 'Aprobada';
        this.closeLightbox();
      }
    });
  }

  startRejection(): void {
    this.isRejecting.set(true);
  }

  submitRejection(motivo: string, foto: PhotoItem): void {
    this.api.rejectPhoto(foto.id_foto, motivo).subscribe({
      next: () => {
        foto.estado = 'Rechazada';
        this.closeLightbox();
      }
    });
  }

  // ─── DASHBOARD ────────────────────────────────────────────────────
  toggleDashboard(): void {
    this.dashboardOpen.update(v => !v);
  }

  getPointsByChain(cadena: string): Point[] {
    return this.filteredPoints().filter(p => p.cadena === cadena);
  }
}

