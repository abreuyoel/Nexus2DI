import { Component, Inject, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ApiService } from '../../core/services/api.service';

type ChatType = 'direct' | 'group_team' | 'group_region' | 'group_pdv';

interface RecipientUser { id_usuario: number; nombre: string; subtitulo?: string; }
interface RegionRecipient { region: string; mercaderistas_count: number; }
interface PdvRecipient { identificador: string; punto_de_interes: string; region?: string; mercaderistas_count: number; }
interface RecipientsResponse {
  analistas: RecipientUser[];
  mercaderistas: RecipientUser[];
  regiones: RegionRecipient[];
  pdvs: PdvRecipient[];
}

export interface NewChatDialogData {
  clienteId?: number;
}

@Component({
  selector: 'app-new-chat-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, MatDialogModule, MatButtonModule, MatIconModule, MatProgressSpinnerModule],
  template: `
<div class="nc-dialog">
  <!-- HEADER -->
  <div class="nc-header">
    <div class="nc-header-icon"><mat-icon>chat_bubble</mat-icon></div>
    <div>
      <h2 class="nc-title">Nuevo Chat</h2>
      <p class="nc-subtitle">
        Paso {{ step() }} de 3 — {{ stepLabel() }}
      </p>
    </div>
    <button class="nc-close" (click)="cancel()"><mat-icon>close</mat-icon></button>
  </div>

  <!-- STEPS DOTS -->
  <div class="nc-stepper">
    <span [class.active]="step() >= 1"></span>
    <span [class.active]="step() >= 2"></span>
    <span [class.active]="step() >= 3"></span>
  </div>

  <!-- BODY -->
  <div class="nc-body">
    @if (loading()) {
      <div class="nc-loading">
        <mat-spinner diameter="36"></mat-spinner>
        <p>Cargando opciones...</p>
      </div>
    }

    @if (!loading()) {
      <!-- STEP 1: TIPO -->
      @if (step() === 1) {
        <p class="nc-help">Elige el tipo de chat que quieres crear.</p>
        <div class="nc-type-grid">
          <button class="nc-type-card" [class.selected]="tipo() === 'direct'" (click)="selectTipo('direct')">
            <mat-icon>person</mat-icon>
            <span class="nc-type-name">Chat directo</span>
            <small>Con un analista o mercaderista</small>
          </button>
          <button class="nc-type-card" [class.selected]="tipo() === 'group_team'" (click)="selectTipo('group_team')">
            <mat-icon>groups</mat-icon>
            <span class="nc-type-name">Equipo completo</span>
            <small>Todos los analistas, mercs, supervisores</small>
          </button>
          <button class="nc-type-card" [class.selected]="tipo() === 'group_region'" (click)="selectTipo('group_region')">
            <mat-icon>map</mat-icon>
            <span class="nc-type-name">Por región</span>
            <small>Mercaderistas de una región</small>
          </button>
          <button class="nc-type-card" [class.selected]="tipo() === 'group_pdv'" (click)="selectTipo('group_pdv')">
            <mat-icon>store</mat-icon>
            <span class="nc-type-name">Por PDV</span>
            <small>Mercaderistas de un punto</small>
          </button>
        </div>
      }

      <!-- STEP 2: DESTINATARIO(S) -->
      @if (step() === 2) {
        <div class="nc-search">
          <mat-icon>search</mat-icon>
          <input type="text" placeholder="Buscar..."
                 [(ngModel)]="searchTerm">
        </div>

        @if (tipo() === 'direct') {
          <p class="nc-section-label">Analistas asignados</p>
          @for (u of filteredAnalistas(); track u.id_usuario) {
            <button class="nc-recipient" [class.selected]="destinatarioId() === u.id_usuario"
                    (click)="destinatarioId.set(u.id_usuario)">
              <mat-icon class="nc-recipient-icon nc-rec-analista">analytics</mat-icon>
              <div class="nc-recipient-info">
                <span class="nc-recipient-name">{{ u.nombre }}</span>
                <small>{{ u.subtitulo }}</small>
              </div>
              <mat-icon class="nc-check">{{ destinatarioId() === u.id_usuario ? 'check_circle' : 'radio_button_unchecked' }}</mat-icon>
            </button>
          }
          <p class="nc-section-label">Mercaderistas asignados</p>
          @for (u of filteredMercaderistas(); track u.id_usuario) {
            <button class="nc-recipient" [class.selected]="destinatarioId() === u.id_usuario"
                    (click)="destinatarioId.set(u.id_usuario)">
              <mat-icon class="nc-recipient-icon nc-rec-merc">person</mat-icon>
              <div class="nc-recipient-info">
                <span class="nc-recipient-name">{{ u.nombre }}</span>
                <small>{{ u.subtitulo }}</small>
              </div>
              <mat-icon class="nc-check">{{ destinatarioId() === u.id_usuario ? 'check_circle' : 'radio_button_unchecked' }}</mat-icon>
            </button>
          }
          @if (filteredAnalistas().length === 0 && filteredMercaderistas().length === 0) {
            <p class="nc-empty">No hay destinatarios disponibles.</p>
          }
        }

        @if (tipo() === 'group_team') {
          <div class="nc-info-box">
            <mat-icon>info</mat-icon>
            <div>
              <strong>Se incluirá:</strong>
              <ul>
                <li>{{ recipients()?.analistas?.length || 0 }} analista(s)</li>
                <li>{{ recipients()?.mercaderistas?.length || 0 }} mercaderista(s)</li>
                <li>Supervisores y coordinadores activos</li>
                <li>Todos los usuarios del cliente</li>
              </ul>
            </div>
          </div>
        }

        @if (tipo() === 'group_region') {
          @for (r of filteredRegiones(); track r.region) {
            <button class="nc-recipient" [class.selected]="region() === r.region"
                    (click)="region.set(r.region)">
              <mat-icon class="nc-recipient-icon nc-rec-region">map</mat-icon>
              <div class="nc-recipient-info">
                <span class="nc-recipient-name">{{ r.region }}</span>
                <small>{{ r.mercaderistas_count }} mercaderista(s)</small>
              </div>
              <mat-icon class="nc-check">{{ region() === r.region ? 'check_circle' : 'radio_button_unchecked' }}</mat-icon>
            </button>
          }
          @if (filteredRegiones().length === 0) {
            <p class="nc-empty">No hay regiones con mercaderistas asignados.</p>
          }
        }

        @if (tipo() === 'group_pdv') {
          @for (p of filteredPdvs(); track p.identificador) {
            <button class="nc-recipient" [class.selected]="puntoInteresId() === p.identificador"
                    (click)="puntoInteresId.set(p.identificador)">
              <mat-icon class="nc-recipient-icon nc-rec-pdv">store</mat-icon>
              <div class="nc-recipient-info">
                <span class="nc-recipient-name">{{ p.punto_de_interes }}</span>
                <small>{{ p.region || '—' }} · {{ p.mercaderistas_count }} mercaderista(s)</small>
              </div>
              <mat-icon class="nc-check">{{ puntoInteresId() === p.identificador ? 'check_circle' : 'radio_button_unchecked' }}</mat-icon>
            </button>
          }
          @if (filteredPdvs().length === 0) {
            <p class="nc-empty">No hay PDVs con mercaderistas asignados.</p>
          }
        }
      }

      <!-- STEP 3: PRIMER MENSAJE -->
      @if (step() === 3) {
        <p class="nc-help">
          Escribe el primer mensaje (opcional). Puedes crear el chat sin mensaje y enviarlo después.
        </p>
        <textarea class="nc-textarea" rows="5"
                  placeholder="Escribe tu primer mensaje (opcional)..."
                  [(ngModel)]="primerMensaje"></textarea>
      }
    }
  </div>

  <!-- FOOTER -->
  <div class="nc-footer">
    @if (step() > 1) {
      <button class="nc-btn nc-btn-secondary" (click)="prev()">
        <mat-icon>arrow_back</mat-icon> Atrás
      </button>
    }
    <span style="flex:1"></span>
    @if (step() < 3) {
      <button class="nc-btn nc-btn-primary" (click)="next()" [disabled]="!canAdvance()">
        Siguiente <mat-icon>arrow_forward</mat-icon>
      </button>
    } @else {
      <button class="nc-btn nc-btn-success" (click)="create()" [disabled]="creating()">
        @if (creating()) {
          <mat-spinner diameter="18"></mat-spinner>
        } @else {
          <mat-icon>send</mat-icon>
        }
        Crear chat
      </button>
    }
  </div>
</div>
  `,
  styles: [`
    :host { display: block; }
    .nc-dialog { display: flex; flex-direction: column; min-width: 520px; max-width: 600px; max-height: 80vh; background: #fff; }
    .nc-header { display: flex; align-items: center; gap: .75rem; padding: 1rem 1.25rem; border-bottom: 1px solid #e2e8f0; }
    .nc-header-icon { background: linear-gradient(135deg, #6366f1, #8b5cf6); color:#fff; width: 40px; height: 40px;
      border-radius: 10px; display:flex; align-items:center; justify-content:center; }
    .nc-title { font-size: 1.05rem; font-weight: 700; color:#1e293b; margin:0; }
    .nc-subtitle { font-size:.75rem; color:#64748b; margin:0; }
    .nc-close { margin-left: auto; background: transparent; border:none; cursor:pointer; color:#94a3b8;
      width:36px; height:36px; border-radius:8px; display:flex; align-items:center; justify-content:center; }
    .nc-close:hover { background:#f1f5f9; color:#475569; }

    .nc-stepper { display:flex; gap:6px; justify-content:center; padding: .5rem 0; background:#f8fafc; }
    .nc-stepper span { width: 32px; height: 4px; border-radius: 2px; background:#e2e8f0; transition: background .2s; }
    .nc-stepper span.active { background: #6366f1; }

    .nc-body { flex: 1; overflow-y: auto; padding: 1.25rem 1.5rem; min-height: 280px; }
    .nc-help { color:#475569; font-size:.85rem; margin-bottom: 1rem; }

    .nc-type-grid { display:grid; grid-template-columns: repeat(2, 1fr); gap: .75rem; }
    .nc-type-card {
      display:flex; flex-direction:column; align-items:center; gap:.35rem;
      padding: 1.25rem .75rem; background:#fff; border:2px solid #e2e8f0;
      border-radius:12px; cursor:pointer; text-align:center; transition: all .15s;
    }
    .nc-type-card:hover { border-color:#a5b4fc; transform: translateY(-2px); box-shadow: 0 4px 10px rgba(99,102,241,.1); }
    .nc-type-card.selected { border-color:#6366f1; background: linear-gradient(135deg, #eef2ff, #f5f3ff); }
    .nc-type-card mat-icon { font-size: 28px; width: 28px; height: 28px; color:#6366f1; }
    .nc-type-name { font-weight: 700; color:#1e293b; font-size: .92rem; }
    .nc-type-card small { color:#64748b; font-size:.72rem; }

    .nc-search {
      display:flex; align-items:center; gap:.5rem; background:#f8fafc; border:1px solid #e2e8f0;
      border-radius:10px; padding: .5rem .85rem; margin-bottom: .75rem;
    }
    .nc-search mat-icon { color:#64748b; }
    .nc-search input { flex:1; border:none; outline:none; background:transparent; color:#1e293b; font-size:.9rem; }

    .nc-section-label { font-size:.72rem; font-weight:700; color:#94a3b8; text-transform: uppercase; letter-spacing:.05em;
      margin: 1rem 0 .35rem; }

    .nc-recipient {
      display:flex; align-items:center; gap:.75rem; width:100%; padding: .65rem .85rem;
      background:#fff; border:1px solid #e2e8f0; border-radius:10px;
      margin-bottom: .35rem; cursor:pointer; text-align:left; transition: all .15s;
    }
    .nc-recipient:hover { border-color:#a5b4fc; background:#f8fafc; }
    .nc-recipient.selected { border-color:#6366f1; background: #eef2ff; }
    .nc-recipient-icon { padding: .35rem; border-radius:8px; color:#fff; }
    .nc-rec-analista { background:#3b82f6; }
    .nc-rec-merc { background:#10b981; }
    .nc-rec-region { background:#f59e0b; }
    .nc-rec-pdv { background:#8b5cf6; }
    .nc-recipient-info { flex:1; display:flex; flex-direction:column; min-width:0; }
    .nc-recipient-name { font-weight:600; color:#1e293b; font-size:.88rem; }
    .nc-recipient-info small { color:#64748b; font-size:.7rem; }
    .nc-check { color:#cbd5e1; }
    .nc-recipient.selected .nc-check { color:#6366f1; }

    .nc-info-box {
      display:flex; gap:.75rem; padding: 1rem; background:#eef2ff; border-left:4px solid #6366f1;
      border-radius:8px; color:#312e81;
    }
    .nc-info-box mat-icon { color:#6366f1; }
    .nc-info-box ul { margin: .25rem 0 0 0; padding-left: 1.25rem; font-size:.85rem; }

    .nc-textarea {
      width:100%; padding: .85rem; border:1px solid #e2e8f0; border-radius:10px; resize:vertical;
      font-family: inherit; font-size:.9rem; color:#1e293b; outline:none; min-height: 100px;
    }
    .nc-textarea:focus { border-color:#6366f1; box-shadow: 0 0 0 3px rgba(99,102,241,.15); }

    .nc-empty { color:#94a3b8; text-align:center; padding: 1.5rem; font-style:italic; font-size:.9rem; }
    .nc-loading { display:flex; flex-direction:column; align-items:center; gap:.5rem; padding: 2rem;
      p { color:#64748b; margin:0; font-size:.85rem; } }

    .nc-footer { display:flex; align-items:center; gap:.5rem; padding: .85rem 1.25rem;
      border-top: 1px solid #e2e8f0; background:#f8fafc; }
    .nc-btn {
      display:inline-flex; align-items:center; gap:.35rem; padding: .55rem 1rem; border-radius:8px;
      border:none; cursor:pointer; font-weight:600; font-size:.85rem; transition: all .15s;
    }
    .nc-btn:disabled { opacity:.5; cursor:not-allowed; }
    .nc-btn-primary { background:#6366f1; color:#fff; }
    .nc-btn-primary:hover:not(:disabled) { background:#4f46e5; }
    .nc-btn-success { background:#16a34a; color:#fff; }
    .nc-btn-success:hover:not(:disabled) { background:#15803d; }
    .nc-btn-secondary { background:#fff; color:#475569; border:1px solid #e2e8f0; }
    .nc-btn-secondary:hover { background:#f1f5f9; }

    @media (max-width: 600px) {
      .nc-dialog { min-width: 90vw; }
      .nc-type-grid { grid-template-columns: 1fr; }
    }
  `]
})
export class NewChatDialogComponent implements OnInit {
  // State
  step = signal<1 | 2 | 3>(1);
  loading = signal(false);
  creating = signal(false);

  // Form
  tipo = signal<ChatType | null>(null);
  destinatarioId = signal<number | null>(null);
  region = signal<string | null>(null);
  puntoInteresId = signal<string | null>(null);
  primerMensaje = '';
  searchTerm = '';

  // Recipients data
  recipients = signal<RecipientsResponse | null>(null);

  // Filtered lists
  filteredAnalistas = computed(() => {
    const term = this.searchTerm.toLowerCase().trim();
    const list = this.recipients()?.analistas || [];
    return term ? list.filter(a => a.nombre.toLowerCase().includes(term)) : list;
  });
  filteredMercaderistas = computed(() => {
    const term = this.searchTerm.toLowerCase().trim();
    const list = this.recipients()?.mercaderistas || [];
    return term ? list.filter(m => m.nombre.toLowerCase().includes(term)) : list;
  });
  filteredRegiones = computed(() => {
    const term = this.searchTerm.toLowerCase().trim();
    const list = this.recipients()?.regiones || [];
    return term ? list.filter(r => r.region.toLowerCase().includes(term)) : list;
  });
  filteredPdvs = computed(() => {
    const term = this.searchTerm.toLowerCase().trim();
    const list = this.recipients()?.pdvs || [];
    return term ? list.filter(p => p.punto_de_interes.toLowerCase().includes(term)) : list;
  });

  stepLabel = computed(() => {
    switch (this.step()) {
      case 1: return 'Selecciona el tipo';
      case 2: return 'Elige destinatario';
      case 3: return 'Mensaje inicial';
    }
    return '';
  });

  constructor(
    private api: ApiService,
    private dialogRef: MatDialogRef<NewChatDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: NewChatDialogData,
  ) {}

  ngOnInit(): void {
    this.loading.set(true);
    this.api.getChatRecipients(this.data.clienteId).subscribe({
      next: r => { this.recipients.set(r); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  selectTipo(t: ChatType): void {
    this.tipo.set(t);
    // Limpiar selecciones de otros tipos
    this.destinatarioId.set(null);
    this.region.set(null);
    this.puntoInteresId.set(null);
  }

  canAdvance(): boolean {
    if (this.step() === 1) return !!this.tipo();
    if (this.step() === 2) {
      const t = this.tipo();
      if (t === 'direct') return !!this.destinatarioId();
      if (t === 'group_team') return true;
      if (t === 'group_region') return !!this.region();
      if (t === 'group_pdv') return !!this.puntoInteresId();
    }
    return true;
  }

  next(): void {
    if (!this.canAdvance()) return;
    if (this.step() < 3) this.step.update(s => (s + 1) as 1 | 2 | 3);
  }

  prev(): void {
    if (this.step() > 1) this.step.update(s => (s - 1) as 1 | 2 | 3);
    this.searchTerm = '';
  }

  cancel(): void {
    this.dialogRef.close(null);
  }

  create(): void {
    const tipo = this.tipo();
    if (!tipo) return;
    this.creating.set(true);
    const body: any = { tipo };
    if (this.data.clienteId) body.cliente_id = this.data.clienteId;
    if (tipo === 'direct') body.destinatario_id = this.destinatarioId();
    if (tipo === 'group_region') body.region = this.region();
    if (tipo === 'group_pdv') body.punto_interes_id = this.puntoInteresId();
    if (this.primerMensaje.trim()) body.primer_mensaje = this.primerMensaje.trim();

    this.api.createConversation(body).subscribe({
      next: conv => {
        this.creating.set(false);
        this.dialogRef.close(conv);
      },
      error: err => {
        this.creating.set(false);
        const detail = err?.error?.detail || 'No se pudo crear la conversación.';
        alert(detail);
      }
    });
  }
}
