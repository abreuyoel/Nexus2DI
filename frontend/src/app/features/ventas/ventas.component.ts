import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/services/auth.service';
import { VentasOfflineQueueService } from './services/ventas-offline-queue.service';
import { ConfirmService } from '../../shared/components/confirm-dialog/confirm.service';

type Pdv = { identificador: string; nombre: string; direccion: string; ciudad: string; localidad: string };
type Cli = { id_cliente: number; nombre: string };

@Component({
  selector: 'app-ventas',
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule, MatSnackBarModule, MatProgressSpinnerModule],
  template: `
<div class="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-800 dark:text-white">
  <!-- HEADER -->
  <div class="bg-white dark:bg-gradient-to-r dark:from-slate-900 dark:to-slate-800 border-b border-slate-200 dark:border-white/8 px-6 py-5">
    <div class="flex items-center gap-3">
      <div class="w-11 h-11 rounded-2xl bg-gradient-to-br from-emerald-600 to-teal-700 flex items-center justify-center shadow-lg">
        <mat-icon class="text-white">point_of_sale</mat-icon>
      </div>
      <div class="flex-1 min-w-0">
        <h1 class="text-xl font-black tracking-tight leading-none text-slate-800 dark:text-white">Ventas</h1>
        <p class="text-slate-500 dark:text-slate-400 text-xs mt-0.5">{{ crumb() || cedula }}</p>
      </div>
      <div class="flex items-center gap-2 shrink-0">
        <span class="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-wider px-2 py-1 rounded-full"
              [ngClass]="isOnline() ? 'bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-400' : 'bg-red-100 dark:bg-red-950 text-red-700 dark:text-red-400'">
          <span class="w-1.5 h-1.5 rounded-full" [ngClass]="isOnline() ? 'bg-emerald-500 dark:bg-emerald-400' : 'bg-red-500 dark:bg-red-400'"></span>
          {{ isOnline() ? 'En línea' : 'Sin conexión' }}
        </span>
        @if (pendingSync() > 0) {
          <button (click)="sincronizar()" class="flex items-center gap-1 text-[10px] font-black uppercase tracking-wider px-2 py-1 rounded-full bg-amber-100 dark:bg-amber-950 text-amber-700 dark:text-amber-400" [disabled]="!isOnline()">
            <mat-icon class="!text-sm">sync</mat-icon>{{ pendingSync() }} pendientes
          </button>
        }
      </div>
    </div>
    @if (syncError()) {
      <div class="mt-3 bg-red-50 dark:bg-red-950/60 border border-red-200 dark:border-red-900 rounded-xl px-3 py-2 flex items-center justify-between gap-2">
        <span class="text-xs text-red-700 dark:text-red-300 font-semibold">No se pudo sincronizar: {{ syncError() }}</span>
        <button (click)="sincronizar()" class="text-[10px] font-black uppercase px-2 py-1 rounded-lg bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-200">Reintentar</button>
      </div>
    }
  </div>

  <div class="px-6 py-6 max-w-3xl mx-auto pb-28">
    @if (loading()) {
      <div class="flex justify-center py-24"><mat-spinner diameter="40"></mat-spinner></div>
    } @else if (!jornadaActiva()) {

    <!-- SIN JORNADA -->
    <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/8 rounded-2xl p-8 text-center mt-8 shadow-sm">
      <mat-icon class="!text-5xl text-emerald-500 dark:text-emerald-400">place</mat-icon>
      <h2 class="text-lg font-black mt-3 mb-1 text-slate-800 dark:text-white">¿Listo para trabajar?</h2>
      <p class="text-slate-500 dark:text-slate-400 text-sm mb-6">Activa tu ruta para comenzar a registrar tus visitas y ventas del día.</p>
      <button (click)="activarJornada()" class="w-full py-3.5 bg-gradient-to-r from-emerald-600 to-teal-600 text-white rounded-xl font-black flex items-center justify-center gap-2">
        <mat-icon class="!text-base">power_settings_new</mat-icon> Activación de Ruta
      </button>
    </div>

    } @else {

    <!-- BARRA DE JORNADA -->
    <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/8 rounded-2xl p-4 mb-4 flex items-center justify-between gap-2 shadow-sm">
      <div class="text-xs text-slate-500 dark:text-slate-400">
        <span class="text-emerald-600 dark:text-emerald-400 font-bold"><mat-icon class="!text-sm align-middle">check_circle</mat-icon> Ruta activa</span><br>
        Iniciada: {{ fmtHora(jornadaActiva().fecha_inicio) }}
      </div>
      <div class="flex items-center gap-2">
        <span class="text-xs px-2 py-1 bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 rounded-full font-bold" title="Visitas registradas">{{ jornadaActiva().visitas || 0 }}</span>
        <button (click)="verVisitas()" class="w-9 h-9 flex items-center justify-center rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-white"><mat-icon class="!text-base">receipt_long</mat-icon></button>
        <button (click)="finalizarJornada()" class="px-3 py-2 bg-red-100 dark:bg-red-950 hover:bg-red-200 dark:hover:bg-red-900 text-red-700 dark:text-red-300 rounded-lg text-xs font-bold">Finalizar</button>
      </div>
    </div>

    <!-- STEP: PDVs -->
    @if (step() === 'pdvs') {
      <div class="flex items-center justify-between mb-3">
        <div>
          <h2 class="text-lg font-black text-slate-800 dark:text-white">Puntos de venta</h2>
          <p class="text-slate-500 dark:text-slate-400 text-sm">Selecciona el PDV que vas a visitar</p>
        </div>
        <button (click)="mostrarSolicitarPdv.set(!mostrarSolicitarPdv())" class="px-3 py-2 rounded-xl text-xs font-bold border border-emerald-600 dark:border-emerald-700 text-emerald-700 dark:text-emerald-400 flex items-center gap-1">
          <mat-icon class="!text-base">add_business</mat-icon> Solicitar PDV
        </button>
      </div>

      @if (mostrarSolicitarPdv()) {
        <div class="bg-white dark:bg-slate-900 border border-emerald-200 dark:border-emerald-900 rounded-2xl p-4 mb-4 space-y-2 shadow-sm">
          <h3 class="font-bold text-emerald-700 dark:text-emerald-400 text-sm mb-2">Solicitud de nuevo PDV</h3>
          <input [(ngModel)]="nuevoPdv.nombre" placeholder="Nombre del PDV *" class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-white rounded-lg px-3 py-2 text-sm outline-none">
          <input [(ngModel)]="nuevoPdv.rif" placeholder="RIF *" class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-white rounded-lg px-3 py-2 text-sm outline-none">
          <textarea [(ngModel)]="nuevoPdv.direccion" placeholder="Dirección completa *" rows="2" class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-white rounded-lg px-3 py-2 text-sm outline-none"></textarea>
          <label class="block text-xs text-slate-500 dark:text-slate-400">Foto de la tienda *</label>
          <input type="file" accept="image/*" capture="environment" (change)="onFotoTienda($event)" class="w-full text-xs text-slate-600 dark:text-slate-300">
          <label class="block text-xs text-slate-500 dark:text-slate-400">Foto del RIF *</label>
          <input type="file" accept="image/*" capture="environment" (change)="onFotoRif($event)" class="w-full text-xs text-slate-600 dark:text-slate-300">
          <div class="flex gap-2 pt-2">
            <button (click)="mostrarSolicitarPdv.set(false)" class="flex-1 py-2 border border-slate-300 dark:border-slate-700 rounded-lg text-sm font-bold text-slate-500 dark:text-slate-400">Cancelar</button>
            <button (click)="solicitarPdv()" [disabled]="enviandoSolicitud()" class="flex-1 py-2 bg-emerald-600 dark:bg-emerald-700 text-white rounded-lg text-sm font-bold">Enviar solicitud</button>
          </div>
        </div>
      }

      <input [(ngModel)]="searchPdv" placeholder="Buscar PDV por nombre, ciudad..."
        class="w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-white rounded-xl px-4 py-2.5 text-sm outline-none mb-3 focus:border-emerald-500">
      <p class="text-xs text-slate-500 dark:text-slate-500 mb-2">{{ filteredPdvs.length }} de {{ pdvs().length }} puntos de venta</p>
      <div class="max-h-[55vh] overflow-y-auto space-y-2">
        @for (p of filteredPdvs.slice(0, 100); track p.identificador) {
          <button (click)="seleccionarPdv(p)" class="w-full text-left bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 border border-slate-200 dark:border-white/8 rounded-xl p-3 flex items-center gap-3 shadow-sm">
            <mat-icon class="text-emerald-600 dark:text-emerald-400">storefront</mat-icon>
            <div class="flex-1 min-w-0">
              <p class="font-bold text-sm truncate text-slate-800 dark:text-white">{{ p.nombre || p.identificador }}</p>
              <p class="text-xs text-slate-500 dark:text-slate-400 truncate">{{ pdvSub(p) }}</p>
            </div>
            <mat-icon class="text-slate-400 dark:text-slate-600">chevron_right</mat-icon>
          </button>
        }
        @if (!filteredPdvs.length) { <p class="text-center text-slate-400 dark:text-slate-600 py-12">No se encontraron puntos de venta</p> }
      </div>
    }

    <!-- STEP: CLIENTES -->
    @if (step() === 'clientes') {
      <div class="flex items-center gap-2 mb-3">
        <button (click)="step.set('pdvs')" class="w-9 h-9 flex items-center justify-center rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-white"><mat-icon class="!text-base">arrow_back</mat-icon></button>
        <div>
          <h2 class="text-lg font-black text-slate-800 dark:text-white">Clientes</h2>
          <p class="text-slate-500 dark:text-slate-400 text-xs">PDV: {{ pdvSel()?.nombre || pdvSel()?.identificador }}</p>
        </div>
      </div>
      <input [(ngModel)]="searchCliente" placeholder="Buscar cliente..."
        class="w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-white rounded-xl px-4 py-2.5 text-sm outline-none mb-3 focus:border-emerald-500">
      <div class="max-h-[60vh] overflow-y-auto space-y-2">
        @for (c of filteredClientes; track c.id_cliente) {
          <button (click)="seleccionarCliente(c)" class="w-full text-left bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 border border-slate-200 dark:border-white/8 rounded-xl p-3 flex items-center gap-3 shadow-sm">
            <mat-icon class="text-emerald-600 dark:text-emerald-400">person</mat-icon>
            <p class="font-bold text-sm flex-1 text-slate-800 dark:text-white">{{ c.nombre }}</p>
            <mat-icon class="text-slate-400 dark:text-slate-600">chevron_right</mat-icon>
          </button>
        }
        @if (!filteredClientes.length) { <p class="text-center text-slate-400 dark:text-slate-600 py-12">No se encontraron clientes</p> }
      </div>
    }

    <!-- STEP: DECISION (panel inline, en vez de dialogos nativos) -->
    @if (step() === 'decision') {
      <div class="flex items-center gap-2 mb-4">
        <button (click)="step.set('clientes')" class="w-9 h-9 flex items-center justify-center rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-white"><mat-icon class="!text-base">arrow_back</mat-icon></button>
        <div>
          <h2 class="text-lg font-black text-slate-800 dark:text-white">{{ clienteSel()?.nombre }}</h2>
          <p class="text-slate-500 dark:text-slate-400 text-xs">{{ pdvSel()?.nombre }}</p>
        </div>
      </div>

      @if (vendio() === null) {
        <p class="text-center text-slate-700 dark:text-slate-300 font-semibold mb-4">¿Vendiste en este cliente?</p>
        <div class="flex gap-3">
          <button (click)="vendio.set(true)" class="flex-1 py-4 bg-emerald-600 dark:bg-emerald-700 hover:bg-emerald-700 dark:hover:bg-emerald-600 text-white rounded-xl font-black flex items-center justify-center gap-2">
            <mat-icon>check_circle</mat-icon> Sí, vendí
          </button>
          <button (click)="vendio.set(false)" class="flex-1 py-4 bg-red-700 dark:bg-red-800 hover:bg-red-800 dark:hover:bg-red-700 text-white rounded-xl font-black flex items-center justify-center gap-2">
            <mat-icon>cancel</mat-icon> No vendí
          </button>
        </div>
      } @else if (vendio() === true) {
        <label class="block text-xs font-bold text-slate-500 dark:text-slate-400 mb-1 uppercase">Monto de la venta</label>
        <input type="number" [(ngModel)]="monto" min="0" step="0.01" placeholder="0.00"
          class="w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-white rounded-xl px-4 py-3 text-lg outline-none mb-4 focus:border-emerald-500">
        <div class="flex gap-2">
          <button (click)="vendio.set(null)" class="flex-1 py-3 border border-slate-300 dark:border-slate-700 rounded-xl font-bold text-slate-500 dark:text-slate-400">Atrás</button>
          <button (click)="registrarVisita()" [disabled]="registrando()" class="flex-1 py-3 bg-emerald-600 dark:bg-emerald-700 text-white rounded-xl font-black">Registrar venta</button>
        </div>
      } @else {
        <label class="block text-xs font-bold text-slate-500 dark:text-slate-400 mb-1 uppercase">Motivo de la no venta</label>
        <textarea [(ngModel)]="razonNoVenta" rows="3" placeholder="Escribe la razón..."
          class="w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-white rounded-xl px-4 py-3 text-sm outline-none mb-4 focus:border-emerald-500"></textarea>
        <div class="flex gap-2">
          <button (click)="vendio.set(null)" class="flex-1 py-3 border border-slate-300 dark:border-slate-700 rounded-xl font-bold text-slate-500 dark:text-slate-400">Atrás</button>
          <button (click)="registrarVisita()" [disabled]="registrando()" class="flex-1 py-3 bg-red-700 dark:bg-red-700 text-white rounded-xl font-black">Registrar</button>
        </div>
      }
    }

    }
  </div>
</div>
  `,
})
export class VentasComponent implements OnInit {
  private http = inject(HttpClient);
  private auth = inject(AuthService);
  private snack = inject(MatSnackBar);
  private offline = inject(VentasOfflineQueueService);
  private confirmDialog = inject(ConfirmService);
  private API = `${environment.apiUrl}/api/vendedor`;

  cedula = this.auth.currentUser()?.username || '';

  loading = signal(true);
  jornadaActiva = signal<any>(null);
  step = signal<'pdvs' | 'clientes' | 'decision'>('pdvs');
  pdvs = signal<Pdv[]>([]);
  clientes = signal<Cli[]>([]);
  pdvSel = signal<Pdv | null>(null);
  clienteSel = signal<Cli | null>(null);
  vendio = signal<boolean | null>(null);
  monto = '';
  razonNoVenta = '';
  registrando = signal(false);

  searchPdv = '';
  searchCliente = '';

  mostrarSolicitarPdv = signal(false);
  nuevoPdv = { nombre: '', rif: '', direccion: '' };
  fotoTiendaData: string | null = null;
  fotoRifData: string | null = null;
  enviandoSolicitud = signal(false);

  isOnline = signal(navigator.onLine);
  pendingSync = signal(0);
  syncError = signal<string | null>(null);

  ngOnInit() {
    this.offline.isOnline$.subscribe(v => this.isOnline.set(v));
    this.offline.pendingCount$.subscribe(v => this.pendingSync.set(v));
    this.offline.syncError$.subscribe(e => this.syncError.set(e?.error || null));
    if (navigator.onLine) this.offline.syncAll();
    this.cargarJornada();
  }

  sincronizar() { this.offline.syncAll(); }

  crumb() {
    return [this.pdvSel()?.nombre, this.clienteSel()?.nombre].filter(Boolean).join('  ›  ');
  }

  fmtHora(iso: string): string {
    if (!iso) return '—';
    try { return new Date(iso).toLocaleString('es-VE', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }); }
    catch { return iso; }
  }

  err(e: any) { this.snack.open(e?.error?.detail || e?.error?.message || 'Error', 'OK', { duration: 4000 }); }

  private get<T>(u: string) { return this.http.get<T>(`${this.API}${u}`); }
  private post<T>(u: string, b: any) { return this.http.post<T>(`${this.API}${u}`, b); }

  private cachedGet<T>(url: string, cacheKey: string, onData: (v: T) => void, onDone?: () => void) {
    this.get<T>(url).subscribe({
      next: v => { onData(v); this.offline.cacheWrite(cacheKey, v); onDone?.(); },
      error: async () => {
        const cached = await this.offline.cacheRead(cacheKey);
        if (cached) { onData(cached); this.snack.open('Sin conexión — mostrando datos guardados', 'OK', { duration: 3000 }); }
        onDone?.();
      }
    });
  }

  cargarJornada() {
    this.loading.set(true);
    this.cachedGet<any>('/jornada-activa', 'jornada-activa', res => {
      this.jornadaActiva.set(res.activa ? res : null);
      if (res.activa) { this.cargarPdvs(); this.cargarClientes(); }
    }, () => this.loading.set(false));
  }

  activarJornada() {
    if (!navigator.onLine) {
      this.offline.enqueue({ url: `${this.API}/activar-jornada`, jsonBody: {}, label: 'Activar jornada' });
      const optimista = { success: true, activa: true, fecha_inicio: new Date().toISOString(), visitas: 0 };
      this.jornadaActiva.set(optimista);
      this.offline.cacheWrite('jornada-activa', optimista);
      this.cargarPdvs(); this.cargarClientes();
      return;
    }
    this.post<any>('/activar-jornada', {}).subscribe({
      next: res => { this.jornadaActiva.set({ ...res, activa: true, visitas: 0 }); this.cargarPdvs(); this.cargarClientes(); },
      error: e => this.err(e),
    });
  }

  async finalizarJornada() {
    const ok = await this.confirmDialog.confirm('¿Terminar la jornada de hoy?', { title: 'Finalizar jornada', confirmText: 'Sí, terminar', danger: true });
    if (!ok) return;
    if (!navigator.onLine) {
      this.offline.enqueue({ url: `${this.API}/finalizar-jornada`, jsonBody: {}, label: 'Finalizar jornada' });
      this.jornadaActiva.set(null);
      this.offline.cacheWrite('jornada-activa', { success: true, activa: false });
      this.snack.open('Jornada finalizada localmente — se sincronizará al reconectar', 'OK', { duration: 3000 });
      return;
    }
    this.post('/finalizar-jornada', {}).subscribe({
      next: () => { this.jornadaActiva.set(null); this.snack.open('Jornada finalizada', 'OK', { duration: 2500 }); },
      error: e => this.err(e),
    });
  }

  cargarPdvs() {
    this.cachedGet<Pdv[]>('/pdvs', 'pdvs', p => this.pdvs.set(p || []), () => this.loading.set(false));
  }
  cargarClientes() {
    this.cachedGet<Cli[]>('/clientes', 'clientes', c => this.clientes.set(c || []));
  }

  pdvSub(p: Pdv): string {
    return [p.ciudad, p.localidad].filter(x => !!x).join(' · ') || p.direccion || '';
  }

  get filteredPdvs(): Pdv[] {
    const f = this.searchPdv.trim().toLowerCase();
    if (!f) return this.pdvs();
    return this.pdvs().filter(p =>
      (p.nombre || '').toLowerCase().includes(f) || (p.identificador || '').toLowerCase().includes(f) ||
      (p.ciudad || '').toLowerCase().includes(f) || (p.localidad || '').toLowerCase().includes(f) ||
      (p.direccion || '').toLowerCase().includes(f));
  }
  get filteredClientes(): Cli[] {
    const f = this.searchCliente.trim().toLowerCase();
    if (!f) return this.clientes();
    return this.clientes().filter(c => (c.nombre || '').toLowerCase().includes(f));
  }

  seleccionarPdv(p: Pdv) {
    this.pdvSel.set(p); this.searchCliente = ''; this.step.set('clientes');
  }
  seleccionarCliente(c: Cli) {
    this.clienteSel.set(c); this.vendio.set(null); this.monto = ''; this.razonNoVenta = ''; this.step.set('decision');
  }

  registrarVisita() {
    const pdv = this.pdvSel(), cli = this.clienteSel();
    if (!pdv || !cli) return;
    const payload: any = { id_punto_interes: pdv.identificador, id_cliente: cli.id_cliente, vendio: this.vendio() };
    if (this.vendio()) {
      const m = parseFloat(this.monto);
      if (!m || m <= 0) { this.snack.open('Ingresa un monto válido mayor que cero', 'OK', { duration: 2500 }); return; }
      payload.monto = m;
    } else {
      if (!this.razonNoVenta.trim()) { this.snack.open('La razón de la no venta es obligatoria', 'OK', { duration: 2500 }); return; }
      payload.razon_no_venta = this.razonNoVenta.trim();
    }
    this.registrando.set(true);
    if (!navigator.onLine) {
      this.offline.enqueue({ url: `${this.API}/registrar-visita`, jsonBody: payload, label: `Visita ${cli.nombre}` });
      const j = this.jornadaActiva();
      if (j) { j.visitas = (j.visitas || 0) + 1; this.jornadaActiva.set({ ...j }); this.offline.cacheWrite('jornada-activa', j); }
      this.registrando.set(false);
      this.snack.open(payload.vendio ? 'Venta guardada localmente' : 'No-venta guardada localmente', 'OK', { duration: 2500 });
      this.step.set('clientes');
      return;
    }
    this.post<any>('/registrar-visita', payload).subscribe({
      next: res => {
        this.registrando.set(false);
        const j = this.jornadaActiva(); if (j) this.jornadaActiva.set({ ...j, visitas: res.visitas });
        this.snack.open(payload.vendio ? '¡Venta registrada!' : 'No venta registrada', 'OK', { duration: 2000 });
        this.step.set('clientes');
      },
      error: e => { this.registrando.set(false); this.err(e); },
    });
  }

  verVisitas() {
    this.cachedGet<any>('/visitas-hoy', 'visitas-hoy', res => {
      const visitas = res?.visitas || [];
      if (!visitas.length) { this.snack.open('Aún no has registrado visitas en esta jornada', 'OK', { duration: 2500 }); return; }
      const items = visitas.map((v: any) => `${v.cliente || 'Cliente'}: ${v.vendio ? 'Vendió $' + (v.monto?.toFixed?.(2) ?? v.monto) : 'No vendió — ' + (v.razon_no_venta || '')}`);
      this.confirmDialog.info(`${visitas.length} visita(s) registradas en esta jornada`, { title: 'Visitas de la jornada', items });
    });
  }

  private fileToCompressedDataURL(file: File, maxDim = 1000, quality = 0.6): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
          let w = img.width, h = img.height;
          if (w > h && w > maxDim) { h = Math.round(h * maxDim / w); w = maxDim; }
          else if (h >= w && h > maxDim) { w = Math.round(w * maxDim / h); h = maxDim; }
          const canvas = document.createElement('canvas');
          canvas.width = w; canvas.height = h;
          canvas.getContext('2d')!.drawImage(img, 0, 0, w, h);
          resolve(canvas.toDataURL('image/jpeg', quality));
        };
        img.onerror = reject;
        img.src = e.target!.result as string;
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  onFotoTienda(ev: Event) {
    const file = (ev.target as HTMLInputElement).files?.[0];
    if (!file) return;
    this.fileToCompressedDataURL(file).then(d => this.fotoTiendaData = d);
  }
  onFotoRif(ev: Event) {
    const file = (ev.target as HTMLInputElement).files?.[0];
    if (!file) return;
    this.fileToCompressedDataURL(file).then(d => this.fotoRifData = d);
  }

  solicitarPdv() {
    const { nombre, rif, direccion } = this.nuevoPdv;
    if (!nombre.trim() || !rif.trim() || !direccion.trim() || !this.fotoTiendaData || !this.fotoRifData) {
      this.snack.open('Completa nombre, RIF, dirección y ambas fotos', 'OK', { duration: 3000 });
      return;
    }
    const payload = {
      punto_de_interes: nombre.trim(), rif: rif.trim(), direccion: direccion.trim(),
      foto_tienda: this.fotoTiendaData, foto_rif: this.fotoRifData,
      latitud: null as number | null, longitud: null as number | null,
    };
    const send = () => {
      this.enviandoSolicitud.set(true);
      if (!navigator.onLine) {
        this.offline.enqueue({ url: `${this.API}/solicitar-pdv`, jsonBody: payload, label: `Solicitud PDV ${nombre}` });
        this.enviandoSolicitud.set(false);
        this.mostrarSolicitarPdv.set(false);
        this.nuevoPdv = { nombre: '', rif: '', direccion: '' };
        this.fotoTiendaData = null; this.fotoRifData = null;
        this.snack.open('Solicitud guardada localmente — se enviará a ATC al reconectar', 'OK', { duration: 3000 });
        return;
      }
      this.post<any>('/solicitar-pdv', payload).subscribe({
        next: res => {
          this.enviandoSolicitud.set(false);
          this.mostrarSolicitarPdv.set(false);
          this.nuevoPdv = { nombre: '', rif: '', direccion: '' };
          this.fotoTiendaData = null; this.fotoRifData = null;
          this.snack.open(res.message || 'Solicitud enviada', 'OK', { duration: 3000 });
        },
        error: e => { this.enviandoSolicitud.set(false); this.err(e); },
      });
    };
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        pos => { payload.latitud = pos.coords.latitude; payload.longitud = pos.coords.longitude; send(); },
        () => send(), { enableHighAccuracy: true, timeout: 5000 });
    } else send();
  }
}
