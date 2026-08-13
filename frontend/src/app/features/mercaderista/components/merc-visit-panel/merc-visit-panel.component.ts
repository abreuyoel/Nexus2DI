import { Component, Input, signal, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ApiService } from '../../../../core/services/api.service';
import { OfflineQueueService } from '../../services/offline-queue.service';
import { MercUiService, ActiveVisit } from '../../services/merc-ui.service';
import { TipoCardComponent, FotoItem } from './components/tipo-card/tipo-card.component';
import { DobleCardComponent } from './components/doble-card/doble-card.component';
import { BalanceFormComponent } from './components/balance-form/balance-form.component';
import { ConfirmService } from '../../../../shared/components/confirm-dialog/confirm.service';
import { ConfirmDialogComponent } from '../../../../shared/components/confirm-dialog/confirm-dialog.component';

/**
 * Mapa de tipos para las DobleCard: código base → { titulo, icono, color, despuesObligatorio }
 * Las categorías se cargan dinámicamente desde los productos del cliente (APK: GestionProvider._loadCategorias).
 * Los códigos planos del backend (gestion_antes, gestion_despues, etc.) se agrupan aquí.
 */
const DOBLE_CONFIG: Record<string, { titulo: string; icono: string; color: string; despuesObligatorio: boolean }> = {
  gestion: { titulo: 'Gestión', icono: 'construction', color: '#f59e0b', despuesObligatorio: false },
  exhibiciones: { titulo: 'Exhibiciones Adicionales', icono: 'view_module', color: '#0277BD', despuesObligatorio: false },
  material_pop: { titulo: 'Material POP', icono: 'campaign', color: '#6A1B9A', despuesObligatorio: true },
};

/** Tipos simples (TipoCard): código → { titulo, icono, desc, color } */
const SIMPLE_CONFIG: Record<string, { titulo: string; icono: string; desc: string; color: string }> = {
  activacion: { titulo: 'Activación', icono: 'flash_on', desc: 'Selfie del mercaderista en el punto de venta.', color: '#f59e0b' },
  desactivacion: { titulo: 'Desactivación', icono: 'power_settings_new', desc: 'Foto de despedida al cerrar el PDV.', color: '#ef4444' },
  precios: { titulo: 'Precios', icono: 'sell', desc: 'Fotos de la etiqueta de precio en góndola.', color: '#3b82f6' },
};

@Component({
  selector: 'app-merc-visit-panel',
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule, MatButtonModule, MatSnackBarModule, MatProgressSpinnerModule, TipoCardComponent, DobleCardComponent, BalanceFormComponent, ConfirmDialogComponent],
  template: `
    <div class="fixed inset-0 z-[100] bg-white dark:bg-slate-950 flex flex-col animate-in slide-in-from-right-full duration-300">

      <!-- Header -->
      <div class="bg-white dark:bg-slate-900 border-b border-slate-100 dark:border-white/5 px-6 py-4 flex items-center justify-between shadow-sm shrink-0">
        <div class="flex items-center gap-3">
          <button (click)="close()" class="w-10 h-10 rounded-xl bg-slate-50 dark:bg-white/5 flex items-center justify-center text-slate-500">
            <mat-icon>arrow_back</mat-icon>
          </button>
          <div class="flex flex-col min-w-0">
            <span class="text-[9px] font-black text-primary-500 uppercase tracking-widest truncate">{{ visit?.cliente }}</span>
            <h3 class="font-bold text-slate-800 dark:text-white truncate tracking-tight text-sm">{{ visit?.pdv_nombre }}</h3>
          </div>
        </div>

        <!-- Timer de visita (40 min) -->
        <div class="flex items-center gap-2">
          @if (ui.timerExpired()) {
            <div class="flex items-center gap-2 bg-red-500/10 border border-red-500/20 rounded-xl px-3 py-1.5">
              <mat-icon class="!text-base text-red-500">timer_off</mat-icon>
              <span class="text-[11px] font-black uppercase tracking-widest text-red-500">{{ ui.timerDisplay() }}</span>
              <span class="text-[9px] font-bold text-red-400 uppercase tracking-wider">Excedido</span>
            </div>
          } @else if (ui.timerSeconds() <= 240) {
            <!-- Últimos 4 min: advertencia -->
            <div class="flex items-center gap-2 bg-amber-500/10 border border-amber-500/20 rounded-xl px-3 py-1.5">
              <mat-icon class="!text-base text-amber-500">timer</mat-icon>
              <span class="text-[11px] font-black uppercase tracking-widest text-amber-500">{{ ui.timerDisplay() }}</span>
            </div>
          } @else {
            <!-- Normal -->
            <div class="flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/20 rounded-xl px-3 py-1.5">
              <mat-icon class="!text-base text-emerald-500">timer</mat-icon>
              <span class="text-[11px] font-black uppercase tracking-widest text-emerald-500">{{ ui.timerDisplay() }}</span>
            </div>
          }
        </div>
      </div>

      <!-- Content (Scrollable) -->
      <div class="flex-grow overflow-y-auto p-4 space-y-4 custom-scrollbar">

        <!-- 1. Activación (TipoCard) — APK: _TipoCard activacion -->
        <app-tipo-card
          [titulo]="simpleConf('activacion').titulo"
          [icono]="simpleConf('activacion').icono"
          [desc]="simpleConf('activacion').desc"
          [color]="simpleConf('activacion').color"
          [fotos]="fotosActivacion()"
          tipoFoto="activacion"
          [visitaId]="visit?.id_visita!"
          [chainId]="visit?.chainId ?? null"
          (fotoSubida)="onFotoSubida()"
          (onDelete)="handleDeleteFoto($event)">
        </app-tipo-card>

        <!-- 2. Precios (TipoCard) — APK: _TipoCard precios, requiere categoría -->
        <app-tipo-card
          [titulo]="simpleConf('precios').titulo"
          [icono]="simpleConf('precios').icono"
          [desc]="simpleConf('precios').desc"
          [color]="simpleConf('precios').color"
          [fotos]="fotosPrecios()"
          tipoFoto="precios"
          [visitaId]="visit?.id_visita!"
          [chainId]="visit?.chainId ?? null"
          [categorias]="categoriasCliente()"
          [loadingCategorias]="categoriasLoading()"
          (fotoSubida)="onFotoSubida()"
          (onDelete)="handleDeleteFoto($event)">
        </app-tipo-card>

        <!-- 3. Auditoría de Inventario y Balance (inline) — APK: Card + BalanceScreen -->
        <div class="bg-white dark:bg-slate-900 border border-slate-100 dark:border-white/5 rounded-3xl shadow-sm overflow-hidden">
          <div class="p-4 flex items-center gap-3 border-b border-slate-50 dark:border-white/5">
            <div class="shrink-0 w-9 h-9 rounded-lg bg-emerald-500/10 flex items-center justify-center">
              <mat-icon class="!text-lg text-emerald-600">inventory_2</mat-icon>
            </div>
            <div>
              <span class="text-[13px] font-bold text-slate-700 dark:text-slate-100">Auditoría de Inventario y Balance</span>
              <p class="text-[11px] text-slate-400 dark:text-slate-500 mt-0.5">Registro de stock en góndola y bodega.</p>
            </div>
          </div>
          <div class="p-0">
            <app-balance-form
              [visitaId]="visit?.id_visita!"
              [idCliente]="visit?.id_cliente!"
              [chainId]="visit?.chainId ?? null"
              (balanceGuardado)="ui.resetTimer('Balance guardado')">
            </app-balance-form>
          </div>
        </div>

        <!-- 4. Gestión (DobleCard) — APK: _DobleCard gestion -->
        @if (dobleConf('gestion'); as dc) {
          <app-doble-card
            [titulo]="dc.titulo"
            [icono]="dc.icono"
            [color]="dc.color"
            tipo="gestion"
            [fotos]="fotosGestion()"
            [categorias]="categoriasCliente()"
            [loadingCategorias]="categoriasLoading()"
            [visitaId]="visit?.id_visita!"
            [chainId]="visit?.chainId ?? null"
            [despuesObligatorio]="dc.despuesObligatorio"
            (fotoSubida)="onFotoSubida()"
            (onDelete)="handleDeleteFoto($event)">
          </app-doble-card>
        }

        <!-- 5. Exhibiciones Adicionales (DobleCard) — APK: _DobleCard exhibiciones -->
        @if (dobleConf('exhibiciones'); as dc) {
          <app-doble-card
            [titulo]="dc.titulo"
            [icono]="dc.icono"
            [color]="dc.color"
            tipo="exhibiciones"
            [fotos]="fotosExhibicion()"
            [categorias]="categoriasCliente()"
            [loadingCategorias]="categoriasLoading()"
            [visitaId]="visit?.id_visita!"
            [chainId]="visit?.chainId ?? null"
            [despuesObligatorio]="dc.despuesObligatorio"
            (fotoSubida)="onFotoSubida()"
            (onDelete)="handleDeleteFoto($event)">
          </app-doble-card>
        }

        <!-- 6. Material POP (DobleCard) — APK: _DobleCard material_pop -->
        @if (dobleConf('material_pop'); as dc) {
          <app-doble-card
            [titulo]="dc.titulo"
            [icono]="dc.icono"
            [color]="dc.color"
            tipo="material_pop"
            [fotos]="fotosPOP()"
            [categorias]="categoriasCliente()"
            [loadingCategorias]="categoriasLoading()"
            [visitaId]="visit?.id_visita!"
            [chainId]="visit?.chainId ?? null"
            [despuesObligatorio]="dc.despuesObligatorio"
            (fotoSubida)="onFotoSubida()"
            (onDelete)="handleDeleteFoto($event)">
          </app-doble-card>
        }

        <!-- 7. Desactivación (TipoCard) — APK: _TipoCard desactivacion -->
        <app-tipo-card
          [titulo]="simpleConf('desactivacion').titulo"
          [icono]="simpleConf('desactivacion').icono"
          [desc]="simpleConf('desactivacion').desc"
          [color]="simpleConf('desactivacion').color"
          [fotos]="fotosDesactivacion()"
          tipoFoto="desactivacion"
          [visitaId]="visit?.id_visita!"
          [chainId]="visit?.chainId ?? null"
          (fotoSubida)="onFotoSubida()"
          (onDelete)="handleDeleteFoto($event)">
        </app-tipo-card>



      </div>

      <!-- Footer: Checks + Resume + Finalizar -->
      <div class="p-4 bg-slate-50 dark:bg-slate-900/50 border-t border-slate-100 dark:border-white/5 space-y-3 shrink-0">
        <!-- Resumen de fotos (APK: total en botón finalizar) -->
        <div class="flex items-center justify-center gap-3 text-[10px] font-medium text-slate-500 dark:text-slate-400">
          <div class="flex items-center gap-1">
            <span class="w-2 h-2 rounded-full bg-amber-500"></span>
            <span>Activación: {{ fotosActivacion().length }}</span>
          </div>
          <div class="flex items-center gap-1">
            <span class="w-2 h-2 rounded-full bg-blue-500"></span>
            <span>Precios: {{ fotosPrecios().length }}</span>
          </div>
          <div class="flex items-center gap-1">
            <span class="w-2 h-2 rounded-full bg-amber-500"></span>
            <span>Gestión: {{ fotosGestion().length }}</span>
          </div>
          <div class="flex items-center gap-1">
            <span class="w-2 h-2 rounded-full bg-blue-700"></span>
            <span>Exhibición: {{ fotosExhibicion().length }}</span>
          </div>
          <div class="flex items-center gap-1">
            <span class="w-2 h-2 rounded-full bg-purple-700"></span>
            <span>POP: {{ fotosPOP().length }}</span>
          </div>
        </div>

        <!-- Checks FIFO y Limpieza (APK: validaciones antes de finalizar) -->
        <div class="flex items-center justify-center gap-6">
          <label class="flex items-center gap-2 cursor-pointer select-none">
            <input type="checkbox" [checked]="fifoOk()" (change)="fifoOk.set(!fifoOk())"
              class="w-5 h-5 rounded-lg border-2 border-slate-300 dark:border-slate-600 text-emerald-600 focus:ring-emerald-500 cursor-pointer">
            <span class="text-xs font-bold text-slate-600 dark:text-slate-300">¿FIFO correcto?</span>
          </label>

          <label class="flex items-center gap-2 cursor-pointer select-none">
            <input type="checkbox" [checked]="limpiezaOk()" (change)="limpiezaOk.set(!limpiezaOk())"
              class="w-5 h-5 rounded-lg border-2 border-slate-300 dark:border-slate-600 text-emerald-600 focus:ring-emerald-500 cursor-pointer">
            <span class="text-xs font-bold text-slate-600 dark:text-slate-300">¿Limpieza del anaquel?</span>
          </label>
        </div>

        <p class="text-[9px] font-black text-slate-400 uppercase tracking-widest text-center">ID Visita: {{ visit?.id_visita }}</p>

        <button (click)="finalizar()" [disabled]="finalizando()"
                class="w-full py-3.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-2xl font-black uppercase tracking-widest text-xs active:scale-95 transition-all flex items-center justify-center gap-2">
          @if (finalizando()) { <mat-spinner diameter="16" color="accent"></mat-spinner> }
          @else { <mat-icon class="!text-base">check_circle</mat-icon> }
          Guardar y Finalizar Visita
        </button>
      </div>
    </div>
  `,
  styles: [`
    :host { display: block; }
  `]
})
export class MercVisitPanelComponent implements OnInit {
  @Input() visit: ActiveVisit | null = null;

  private api = inject(ApiService);
  private offline = inject(OfflineQueueService);
  ui = inject(MercUiService);
  private snack = inject(MatSnackBar);
  private confirmSvc = inject(ConfirmService);

  finalizando = signal(false);

  // Checks de validación (FIFO y Limpieza)
  fifoOk = signal(false);
  limpiezaOk = signal(false);

  /** Categorías dinámicas cargadas desde los productos del cliente (APK: GestionProvider._loadCategorias). */
  categoriasCliente = signal<string[]>([]);
  /** Indica si las categorías aún se están cargando del backend. */
  categoriasLoading = signal(true);

  // ─── Señales de fotos por tipo (APK: GestionProvider) ───
  fotosActivacion = signal<FotoItem[]>([]);
  fotosPrecios = signal<FotoItem[]>([]);
  fotosDesactivacion = signal<FotoItem[]>([]);
  fotosGestion = signal<FotoItem[]>([]);
  fotosExhibicion = signal<FotoItem[]>([]);
  fotosPOP = signal<FotoItem[]>([]);

  // ─── Helpers de configuración ───
  simpleConf(codigo: string) { return SIMPLE_CONFIG[codigo] || { titulo: codigo, icono: 'photo_camera', desc: '', color: '#6b7280' }; }
  dobleConf(codigo: string) { return DOBLE_CONFIG[codigo] || null; }

  /** Mapea los códigos planos del backend (gestion_antes, gestion_despues, etc.) a sub y pair_id para las DobleCard. */
  private parseFlatCode(codigo: string): { sub: string; pair_id: string | undefined } | null {
    const match = codigo.match(/^(gestion|exhibicion|pop)_(antes|despues)$/);
    if (match) {
      return { sub: match[2], pair_id: undefined };
    }
    const mixtoMatch = codigo.match(/^(gestion|exhibicion|pop)_mixto$/);
    if (mixtoMatch) {
      return { sub: 'mixto', pair_id: undefined };
    }
    return null;
  }

  /** Agrupa códigos planos del backend en el array de fotos del tipo correcto. */
  private distribuirFotos(tipos: { codigo: string; fotos: any[] }[]) {
    const activacion: FotoItem[] = [];
    const precios: FotoItem[] = [];
    const desactivacion: FotoItem[] = [];
    const gestion: FotoItem[] = [];
    const exhibicion: FotoItem[] = [];
    const pop: FotoItem[] = [];

    for (const t of tipos) {
      const parsed = this.parseFlatCode(t.codigo);
      const mapped: FotoItem[] = t.fotos.map((f: any) => ({
        id_foto: f.id_foto,
        url: f.url || '',
        estado: f.estado || 'Subida',
        tipo_foto: t.codigo,
        comentario: f.comentario || undefined,
        pair_id: f.pair_id || (parsed?.pair_id || undefined),
        sub: parsed?.sub || undefined,
      }));

      if (t.codigo === 'activacion') {
        activacion.push(...mapped);
      } else if (t.codigo === 'precios') {
        precios.push(...mapped);
      } else if (t.codigo === 'desactivacion') {
        desactivacion.push(...mapped);
      } else if (t.codigo.startsWith('gestion')) {
        gestion.push(...mapped);
      } else if (t.codigo.startsWith('exhibicion') || t.codigo.startsWith('exhibici')) {
        exhibicion.push(...mapped);
      } else if (t.codigo.startsWith('pop') || t.codigo.startsWith('material_pop')) {
        pop.push(...mapped);
      }
    }

    this.fotosActivacion.set(activacion);
    this.fotosPrecios.set(precios);
    this.fotosDesactivacion.set(desactivacion);
    this.fotosGestion.set(gestion);
    this.fotosExhibicion.set(exhibicion);
    this.fotosPOP.set(pop);
  }

  /** Carga fotos desde API o cadena offline. */
  reloadFotos() {
    if (!this.visit) return;

    if (this.visit.chainId) {
      // Offline: buscar pasos de foto en la cadena
      this.offline.getChain(this.visit.chainId).then(chain => {
        if (!chain) return;
        const activacion: FotoItem[] = [];
        const precios: FotoItem[] = [];
        const desactivacion: FotoItem[] = [];
        const gestion: FotoItem[] = [];
        const exhibicion: FotoItem[] = [];
        const pop: FotoItem[] = [];

        for (let i = 0; i < chain.steps.length; i++) {
          const s = chain.steps[i];
          if (s.kind !== 'foto' || !s.formFields) continue;
          const tf = s.formFields['tipo_foto'] || '';
          const sub = s.formFields['sub'] || undefined;
          const pairId = s.formFields['pair_id'] || undefined;

          const item: FotoItem = {
            id_foto: `pending_${i}`,
            url: s.fileBlob ? URL.createObjectURL(s.fileBlob) : '',
            estado: 'Pendiente',
            tipo_foto: tf,
            pair_id: pairId,
            sub: sub,
          };

          if (tf === 'activacion') activacion.push(item);
          else if (tf === 'precios') precios.push(item);
          else if (tf === 'desactivacion') desactivacion.push(item);
          else if (tf.startsWith('gestion')) gestion.push(item);
          else if (tf.startsWith('exhibicion')) exhibicion.push(item);
          else if (tf.startsWith('pop') || tf.startsWith('material_pop')) pop.push(item);
        }

        this.fotosActivacion.set(activacion);
        this.fotosPrecios.set(precios);
        this.fotosDesactivacion.set(desactivacion);
        this.fotosGestion.set(gestion);
        this.fotosExhibicion.set(exhibicion);
        this.fotosPOP.set(pop);
      });
      return;
    }

    // Online: llamar API
    this.api.getFotosVisita(this.visit.id_visita as number).subscribe({
      next: (res: any) => {
        this.distribuirFotos(res.tipos || []);
      },
      error: () => { },
    });
  }

  /** Delete handler delegado al API/offline. */
  async handleDeleteFoto(foto: FotoItem) {
    const confirmed = await this.confirmSvc.confirm(
      '¿Eliminar esta foto? Esta acción no se puede deshacer.',
      { title: 'Eliminar Foto', confirmText: 'Eliminar', cancelText: 'Cancelar', danger: true }
    );
    if (!confirmed) return;

    // Si es pendiente (offline), eliminar paso de la cadena
    if (this.visit?.chainId && typeof foto.id_foto === 'string' && foto.id_foto.startsWith('pending_')) {
      const idx = parseInt(foto.id_foto.replace('pending_', ''), 10);
      if (!isNaN(idx)) {
        try {
          await this.offline.deleteChainStep(this.visit.chainId, idx);
          this.reloadFotos();
          this.snack.open('Foto eliminada localmente', 'OK', { duration: 2000 });
        } catch { /* ignore */ }
      }
      return;
    }

    // Online: usar API delete
    this.api.delete(`/api/merc/visitas/fotos/${foto.id_foto}`).subscribe({
      next: () => { this.reloadFotos(); this.snack.open('Foto eliminada', 'OK', { duration: 2000 }); },
      error: () => this.snack.open('No se pudo eliminar la foto', 'OK', { duration: 3000 }),
    });
  }

  // ─── Validación Antes/Después (APK: esAntesDespuesValid) ───

  esAntesDespuesValid(): boolean {
    const tipos = [
      { name: 'Gestión', fotos: this.fotosGestion() },
      { name: 'Exhibiciones', fotos: this.fotosExhibicion() },
      { name: 'Material POP', fotos: this.fotosPOP() },
    ];

    for (const t of tipos) {
      const antes = t.fotos.filter(f => f.sub === 'antes').length;
      const despues = t.fotos.filter(f => f.sub === 'despues').length;
      if (antes !== despues) {
        this.snack.open(`${t.name}: la cantidad de Antes (${antes}) debe ser igual a Después (${despues}).`, 'OK', { duration: 4000 });
        return false;
      }
    }

    // Material POP requiere al menos 1 después (obligatorio)
    const popDespues = this.fotosPOP().filter(f => f.sub === 'despues').length;
    if (popDespues === 0) {
      this.snack.open('Material POP: debés subir al menos una foto de Después.', 'OK', { duration: 4000 });
      return false;
    }

    return true;
  }

  // ─── Ciclo de vida ───

  /** Carga categorías dinámicas desde los productos del cliente (APK: _loadCategorias). */
  private loadCategoriasCliente() {
    if (!this.visit?.id_cliente) {
      this.categoriasLoading.set(false);
      return;
    }

    // Si estamos offline, no podemos cargar categorías del servidor
    if (this.visit.chainId) {
      // En modo offline, cargar desde los pasos de foto pendientes o usar empty
      this.offline.getChain(this.visit.chainId).then(chain => {
        if (!chain) { this.categoriasLoading.set(false); return; }
        const cats = new Set<string>();
        for (const s of chain.steps) {
          if (s.kind === 'foto' && s.formFields?.['categoria']) {
            cats.add(s.formFields['categoria']);
          }
        }
        if (cats.size > 0) {
          this.categoriasCliente.set(Array.from(cats).sort());
        }
        this.categoriasLoading.set(false);
      });
      return;
    }

    this.api.getMercProductosCliente(this.visit.id_cliente as number).subscribe({
      next: (res: { categorias: any[]; total_productos: number }) => {
        const cats = new Set<string>();
        for (const cat of res.categorias || []) {
          if (cat.productos) {
            for (const p of cat.productos) {
              if (p.categoria) cats.add(p.categoria);
            }
          }
        }
        this.categoriasCliente.set(Array.from(cats).sort());
        this.categoriasLoading.set(false);
      },
      error: () => {
        this.categoriasLoading.set(false);
      }
    });
  }

  ngOnInit() {
    this.reloadFotos();
    this.loadCategoriasCliente();
  }

  close() {
    this.ui.closeVisit();
  }

  onFotoSubida() {
    this.ui.resetTimer('Foto subida');
    this.reloadFotos();
  }

  async finalizar() {
    if (!this.visit) return;

    // Validación Antes/Después (APK: esAntesDespuesValid)
    if (!this.esAntesDespuesValid()) {
      return;
    }

    // Validación FIFO
    if (!this.fifoOk()) {
      this.snack.open('Debés confirmar que el FIFO es correcto antes de finalizar.', 'OK', { duration: 4000 });
      return;
    }

    // Validación Limpieza
    if (!this.limpiezaOk()) {
      this.snack.open('Debés confirmar la limpieza del anaquel antes de finalizar.', 'OK', { duration: 4000 });
      return;
    }

    const confirmed = await this.confirmSvc.confirm(
      '¿Finalizar esta visita? No vas a poder cargar más fotos ni data después.',
      { title: 'Finalizar Visita', confirmText: 'Finalizar', cancelText: 'Cancelar', danger: true }
    );
    if (!confirmed) return;
    this.finalizando.set(true);

    let hasBalances = false;
    if (this.visit.chainId) {
      const chain = await this.offline.getChain(this.visit.chainId);
      hasBalances = !!(chain && chain.steps.some(s => s.kind === 'balances' && s.jsonBody?.productos?.length > 0));
    } else {
      try {
        const res = await this.api.get<any>(`/api/merc/visitas/${this.visit.id_visita}/detalle`).toPromise();
        hasBalances = !!(res && res.balances && res.balances.length > 0);
      } catch (e) {
        hasBalances = false;
      }
    }

    if (!hasBalances) {
      this.snack.open('Debés cargar al menos un balance de producto antes de finalizar la visita.', 'OK', { duration: 4000 });
      this.finalizando.set(false);
      return;
    }

    if (this.visit.chainId) {
      await this.offline.addChainStep(this.visit.chainId, {
        kind: 'finalizar', url: `/api/merc/visitas/${this.visit.id_visita}/finalizar`, isMultipart: false,
        jsonBody: { id_visita: this.visit.id_visita }
      });
      this.finalizando.set(false);
      this.snack.open('Visita finalizada localmente — se sincronizará al reconectar', 'OK', { duration: 3000 });
      this.ui.closeVisit(true);
      return;
    }

    this.api.finalizarMercVisita(this.visit.id_visita as number).subscribe({
      next: () => {
        this.finalizando.set(false);
        this.snack.open('Visita finalizada', 'OK', { duration: 2500 });
        this.ui.closeVisit(true);
      },
      error: () => {
        this.finalizando.set(false);
        this.snack.open('No se pudo finalizar la visita', 'OK', { duration: 3000 });
      },
    });
  }
}
