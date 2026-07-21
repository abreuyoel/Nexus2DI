import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/services/auth.service';
import { AuditorOfflineQueueService, Chain } from './services/auditor-offline-queue.service';
import { ConfirmService } from '../../shared/components/confirm-dialog/confirm.service';

type Ruta = { id: number; nombre: string; total_puntos: number; esta_activa: boolean };
type Pdv = { id: string; nombre: string; prioridad: string; total_clientes: number; activado: boolean };
type Cli = { id: number; nombre: string; prioridad: string };
type Cat = { id: number; nombre: string };

@Component({
  selector: 'app-auditor-campo',
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule, MatSnackBarModule, MatProgressSpinnerModule],
  template: `
<div class="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white">
  <!-- HEADER + STEPPER -->
  <div class="bg-gradient-to-r from-white to-slate-50 dark:from-slate-900 dark:to-slate-800 border-b border-slate-200 dark:border-white/8 px-6 py-5">
    <div class="flex items-center gap-3">
      <div class="w-11 h-11 rounded-2xl bg-gradient-to-br from-violet-600 to-purple-700 flex items-center justify-center shadow-lg">
        <mat-icon class="text-white">fact_check</mat-icon>
      </div>
      <div class="flex-1 min-w-0">
        <h1 class="text-xl font-black tracking-tight leading-none">Auditoría de Campo</h1>
        <p class="text-slate-500 dark:text-slate-400 text-xs mt-0.5">{{ crumb() || ('CI ' + cedula) }}</p>
      </div>
      <div class="flex items-center gap-2 shrink-0">
        <span class="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-wider px-2 py-1 rounded-full"
              [ngClass]="isOnline() ? 'bg-emerald-50 dark:bg-emerald-950 text-emerald-600 dark:text-emerald-400' : 'bg-red-50 dark:bg-red-950 text-red-600 dark:text-red-400'">
          <span class="w-1.5 h-1.5 rounded-full" [ngClass]="isOnline() ? 'bg-emerald-600 dark:bg-emerald-400' : 'bg-red-600 dark:bg-red-400'"></span>
          {{ isOnline() ? 'En línea' : 'Sin conexión' }}
        </span>
        @if (pendingSync() > 0) {
          <button (click)="sincronizar()" class="flex items-center gap-1 text-[10px] font-black uppercase tracking-wider px-2 py-1 rounded-full bg-amber-50 dark:bg-amber-950 text-amber-600 dark:text-amber-400" [disabled]="!isOnline()">
            <mat-icon class="!text-sm">sync</mat-icon>{{ pendingSync() }} pendientes
          </button>
        }
      </div>
    </div>
    @if (syncErrors().length) {
      <div class="mt-3 bg-red-50/80 dark:bg-red-950/60 border border-red-200 dark:border-red-900 rounded-xl px-3 py-2 flex items-center justify-between gap-2">
        <span class="text-xs text-red-600 dark:text-red-300 font-semibold">{{ syncErrors().length }} sesión(es) no se pudieron sincronizar — los datos no se perdieron.</span>
        <button (click)="sincronizar()" class="text-[10px] font-black uppercase px-2 py-1 rounded-lg bg-red-200 dark:bg-red-900 text-red-700 dark:text-red-200">Reintentar</button>
      </div>
    }
    <div class="flex gap-2 mt-4">
      @for (s of steps; track s.n) {
        <div class="flex-1 text-center">
          <div class="w-8 h-8 mx-auto rounded-full flex items-center justify-center text-xs font-black border-2 transition-all"
               [ngClass]="step()===s.n ? 'bg-violet-600 border-violet-500 text-white' : step()>s.n ? 'bg-emerald-600 border-emerald-500 text-white' : 'bg-slate-100 dark:bg-slate-800 border-slate-300 dark:border-slate-700 text-slate-400 dark:text-slate-500'">
            @if (step()>s.n) { <mat-icon class="!text-base">check</mat-icon> } @else { {{ s.n }} }
          </div>
          <span class="text-[10px] font-bold uppercase tracking-wider mt-1 block"
                [ngClass]="step()>=s.n ? 'text-violet-600 dark:text-violet-300' : 'text-slate-400 dark:text-slate-600'">{{ s.label }}</span>
        </div>
      }
    </div>
  </div>

  <div class="px-6 py-6 max-w-3xl mx-auto pb-28">
    @if (loading()) {
      <div class="flex justify-center py-24"><mat-spinner diameter="40"></mat-spinner></div>
    } @else {

    <!-- STEP 1: RUTAS -->
    @if (step()===1) {
      <h2 class="text-lg font-black mb-1">Mis rutas</h2>
      <p class="text-slate-500 dark:text-slate-400 text-sm mb-4">Selecciona una ruta para iniciar la jornada</p>
      @for (r of rutas(); track r.id) {
        <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/8 rounded-2xl p-4 mb-3 flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-violet-100 dark:bg-violet-900 flex items-center justify-center"><mat-icon class="text-violet-600 dark:text-violet-400">route</mat-icon></div>
          <div class="flex-1 min-w-0">
            <p class="font-bold truncate">{{ r.nombre }}</p>
            <p class="text-xs text-slate-500 dark:text-slate-400">{{ r.total_puntos }} PDVs @if(r.esta_activa){<span class="text-emerald-600 dark:text-emerald-400 font-bold">· Activa</span>}</p>
          </div>
          <button (click)="activarRuta(r)" class="px-4 py-2 bg-violet-700 hover:bg-violet-600 rounded-xl text-sm font-bold text-white">{{ r.esta_activa ? 'Continuar' : 'Activar' }}</button>
          @if(!r.esta_activa){ <button (click)="noActivar(r)" class="px-3 py-2 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-xl text-sm font-bold text-slate-600 dark:text-slate-300">No activar</button> }
        </div>
      }
      @if(!rutas().length){ <p class="text-center text-slate-400 dark:text-slate-600 py-12">No tienes rutas asignadas.</p> }
    }

    <!-- STEP 2: PDVs -->
    @if (step()===2) {
      <h2 class="text-lg font-black mb-1">Puntos de venta</h2>
      <p class="text-slate-500 dark:text-slate-400 text-sm mb-4">Programados para hoy</p>
      @for (p of pdvs(); track p.id) {
        <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/8 rounded-2xl p-4 mb-3 flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl flex items-center justify-center" [ngClass]="p.activado?'bg-emerald-100 dark:bg-emerald-900':'bg-slate-100 dark:bg-slate-800'"><mat-icon [ngClass]="p.activado?'text-emerald-600 dark:text-emerald-400':'text-slate-500 dark:text-slate-400'">store</mat-icon></div>
          <div class="flex-1 min-w-0">
            <p class="font-bold truncate">{{ p.nombre }}</p>
            <p class="text-xs text-slate-500 dark:text-slate-400">{{ p.total_clientes }} clientes · <span [ngClass]="p.activado?'text-emerald-600 dark:text-emerald-400':'text-amber-600 dark:text-amber-400'">{{ p.activado?'Activado':'Pendiente' }}</span></p>
          </div>
          @if(p.activado){ <button (click)="abrirClientes(p)" class="px-4 py-2 bg-violet-100 dark:bg-violet-900 hover:bg-violet-200 dark:hover:bg-violet-800 rounded-xl text-sm font-bold text-violet-600 dark:text-violet-300">Clientes</button> }
          @else { <button (click)="activarPdv(p)" class="px-4 py-2 bg-amber-600 hover:bg-amber-500 rounded-xl text-sm font-bold text-white flex items-center gap-1"><mat-icon class="!text-base">photo_camera</mat-icon>Activar</button> }
        </div>
      }
      @if(!pdvs().length){ <p class="text-center text-slate-400 dark:text-slate-600 py-12">No hay PDVs programados para hoy.</p> }
    }

    <!-- STEP 3: CLIENTES + CATEGORIAS -->
    @if (step()===3 && !clienteSel()) {
      <h2 class="text-lg font-black mb-1">Clientes del PDV</h2>
      <p class="text-slate-500 dark:text-slate-400 text-sm mb-4">Selecciona el cliente a auditar</p>
      @for (c of clientes(); track c.id) {
        <button (click)="iniciarCliente(c)" class="w-full text-left bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 border border-slate-200 dark:border-white/8 rounded-2xl p-4 mb-3 flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-violet-100 dark:bg-violet-900 flex items-center justify-center"><mat-icon class="text-violet-600 dark:text-violet-400">person</mat-icon></div>
          <div class="flex-1"><p class="font-bold">{{ c.nombre }}</p><span class="text-xs px-2 py-0.5 bg-violet-100 dark:bg-violet-950 text-violet-600 dark:text-violet-300 rounded-full font-bold">{{ c.prioridad }}</span></div>
          <mat-icon class="text-slate-300 dark:text-slate-600">chevron_right</mat-icon>
        </button>
      }
      @if(!clientes().length){ <p class="text-center text-slate-400 dark:text-slate-600 py-12">Sin clientes para hoy.</p> }
    }
    @if (step()===3 && clienteSel() && !catSel()) {
      <h2 class="text-lg font-black mb-1">Categorías a auditar</h2>
      <p class="text-slate-500 dark:text-slate-400 text-sm mb-4">{{ clienteSel()?.nombre }}</p>
      @for (cat of categorias(); track cat.id) {
        <button (click)="abrirCategoria(cat)" class="w-full text-left bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 border border-slate-200 dark:border-white/8 rounded-2xl p-4 mb-3 flex items-center gap-3" [class.opacity-50]="catsHechas().includes(cat.id)">
          <div class="w-10 h-10 rounded-xl bg-violet-100 dark:bg-violet-900 flex items-center justify-center"><mat-icon class="text-violet-600 dark:text-violet-400">layers</mat-icon></div>
          <div class="flex-1"><p class="font-bold">{{ cat.nombre }}</p><p class="text-xs text-slate-400 dark:text-slate-500">{{ catsHechas().includes(cat.id)?'Auditada':'Toca para auditar' }}</p></div>
          <mat-icon class="text-slate-300 dark:text-slate-600">chevron_right</mat-icon>
        </button>
      }
      @if(!categorias().length){ <p class="text-center text-slate-400 dark:text-slate-600 py-12">Este cliente no tiene categorías configuradas.</p> }
    }

    <!-- STEP 4: CUESTIONARIO -->
    @if (step()===4 && catSel()) {
      <h2 class="text-lg font-black mb-1">{{ catSel()?.nombre }}</h2>
      <p class="text-slate-500 dark:text-slate-400 text-sm mb-4">Cuestionario de auditoría</p>

      <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/8 rounded-2xl overflow-hidden mb-3">
        <div class="px-4 py-2.5 bg-slate-100 dark:bg-slate-800 text-violet-600 dark:text-violet-400 text-xs font-black uppercase tracking-wider">Fotos de la categoría</div>
        <div class="p-4 flex items-center justify-between">
          <span class="text-sm text-slate-500 dark:text-slate-400">Puedes tomar varias</span>
          <div class="flex items-center gap-2">
            <span class="text-xs px-2 py-1 bg-violet-100 dark:bg-violet-950 text-violet-600 dark:text-violet-300 rounded-full font-bold">{{ fotos() }} fotos</span>
            <button (click)="cam('cat')" class="px-3 py-2 bg-violet-100 dark:bg-violet-900 hover:bg-violet-200 dark:hover:bg-violet-800 rounded-xl text-sm font-bold text-violet-600 dark:text-violet-300 flex items-center gap-1"><mat-icon class="!text-base">photo_camera</mat-icon>Tomar</button>
          </div>
        </div>
      </div>

      @for (sec of secciones; track sec.t) {
        <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/8 rounded-2xl overflow-hidden mb-3">
          <div class="px-4 py-2.5 bg-slate-100 dark:bg-slate-800 text-violet-600 dark:text-violet-400 text-xs font-black uppercase tracking-wider">{{ sec.t }}</div>
          <div class="p-4 space-y-1">
            @for (q of sec.qs; track q.k) {
              <div class="flex items-center justify-between gap-3 py-2.5 border-b border-slate-100 dark:border-white/5 last:border-0">
                <span class="text-sm font-semibold">{{ q.l }}</span>
                <div class="flex rounded-lg overflow-hidden border border-slate-300 dark:border-slate-700 shrink-0">
                  <button (click)="form[q.k]=1" [ngClass]="form[q.k]===1?'bg-emerald-600 text-white':'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400'" class="px-4 py-1.5 text-sm font-bold">Sí</button>
                  <button (click)="form[q.k]=0" [ngClass]="form[q.k]===0?'bg-red-600 text-white':'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400'" class="px-4 py-1.5 text-sm font-bold border-l border-slate-300 dark:border-slate-700">No</button>
                </div>
              </div>
              @if (q.k==='prox_vencer' && form['prox_vencer']===1) {
                <div class="pl-1 pb-2 grid grid-cols-2 gap-2">
                  <input [(ngModel)]="form['prox_vencer_cantidad']" type="number" placeholder="Cantidad" class="bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-sm outline-none text-slate-900 dark:text-white">
                  <input [(ngModel)]="form['prox_vencer_marca']" placeholder="Marca" class="bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-sm outline-none text-slate-900 dark:text-white">
                  <label class="text-[11px] text-slate-400 dark:text-slate-500 col-span-2 -mb-1">Fechas próximas a vencer</label>
                  <input [(ngModel)]="form['prox_vencer_fecha1']" type="date" class="bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-sm outline-none text-slate-900 dark:text-slate-200">
                  <input [(ngModel)]="form['prox_vencer_fecha2']" type="date" class="bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-sm outline-none text-slate-900 dark:text-slate-200">
                </div>
              }
              @if (q.k==='competencia_actividad' && form['competencia_actividad']===1) {
                <div class="pl-1 pb-2 space-y-2">
                  <label class="flex items-center gap-2 text-sm"><input type="checkbox" [(ngModel)]="form['competencia_material_pop']" class="w-4 h-4"> Hay material POP</label>
                  <label class="flex items-center gap-2 text-sm"><input type="checkbox" [(ngModel)]="form['competencia_impulsadora']" class="w-4 h-4"> Hay impulsadora</label>
                </div>
              }
              @if (q.k==='promo_nuestra' && form['promo_nuestra']===1) {
                <input [(ngModel)]="form['promo_nuestra_desc']" placeholder="¿Cuáles?" class="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-sm outline-none text-slate-900 dark:text-white mb-2">
              }
              @if (q.k==='promo_competencia' && form['promo_competencia']===1) {
                <input [(ngModel)]="form['promo_competencia_desc']" placeholder="Describe" class="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-sm outline-none text-slate-900 dark:text-white mb-2">
              }
              @if (q.k==='exhibicion_adicional' && form['exhibicion_adicional']===1) {
                <div class="pl-1 pb-2 flex flex-wrap gap-3">
                  @for (t of exhibTipos; track t) {
                    <label class="flex items-center gap-1.5 text-sm"><input type="checkbox" [checked]="exhibSel.has(t)" (change)="toggleExhib(t)" class="w-4 h-4"> {{ t }}</label>
                  }
                </div>
              }
            }
            @if (sec.t === 'Material POP del cliente') {
              <input [(ngModel)]="form['pop_otro']" placeholder="Otro material POP (opcional)" class="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-sm outline-none text-slate-900 dark:text-white mt-1">
            }
          </div>
        </div>
      }
      <div class="flex gap-2 mt-4">
        <button (click)="catSel.set(null)" class="flex-1 py-3 border border-slate-300 dark:border-slate-700 rounded-xl font-bold text-slate-500 dark:text-slate-400">Cancelar</button>
        <button (click)="guardarCategoria()" [disabled]="saving()" class="flex-1 py-3 bg-gradient-to-r from-violet-700 to-purple-700 rounded-xl font-black text-white flex items-center justify-center gap-2">
          @if(saving()){<mat-spinner diameter="18"></mat-spinner>}@else{<mat-icon class="!text-base">save</mat-icon>} Guardar
        </button>
      </div>
    }
    }
  </div>

  <!-- FOOTER ACCIONES -->
  @if (!loading() && footerBtns().length) {
    <div class="fixed bottom-0 left-0 right-0 bg-white/95 dark:bg-slate-900/95 backdrop-blur border-t border-slate-200 dark:border-white/8 px-6 py-3 flex gap-2 max-w-3xl mx-auto">
      @for (b of footerBtns(); track b.l) {
        <button (click)="b.fn()" class="flex-1 py-2.5 rounded-xl font-bold text-sm flex items-center justify-center gap-1.5" [ngClass]="b.cls">
          <mat-icon class="!text-base">{{ b.i }}</mat-icon>{{ b.l }}
        </button>
      }
    </div>
  }

  <!-- camera input + overlay -->
  <input #camInput type="file" accept="image/*" capture="environment" class="hidden" (change)="onCam($event)">
  @if (uploading()) {
    <div class="fixed inset-0 bg-black/60 z-50 flex items-center justify-center">
      <div class="bg-white dark:bg-slate-900 rounded-2xl px-8 py-6 text-center border border-slate-200 dark:border-white/10">
        <mat-spinner diameter="40" class="mx-auto"></mat-spinner>
        <p class="mt-3 font-bold">{{ uploadMsg() }}</p>
      </div>
    </div>
  }
</div>
  `,
})
export class AuditorCampoComponent implements OnInit {
  private http = inject(HttpClient);
  private auth = inject(AuthService);
  private snack = inject(MatSnackBar);
  private offline = inject(AuditorOfflineQueueService);
  private confirmDialog = inject(ConfirmService);
  private API = `${environment.apiUrl}/api/auditor-campo`;

  isOnline = signal(navigator.onLine);
  pendingSync = signal(0);
  syncErrors = signal<Chain[]>([]);
  /** Cadena activa de la sesión de auditoría en curso mientras no hay id_visita real. */
  private activeChainId: string | null = null;
  // Si el usuario logueado es mercaderista, su username es la cédula (numérica).
  // Si es admin/analista abriendo el módulo para probar, usamos una cédula de
  // AUDITOR DEMO (88880001) para ver el flujo con datos reales.
  cedula = (() => {
    const un = this.auth.currentUser()?.username || '';
    return /^\d{5,}$/.test(un) ? un : '88880001';
  })();

  steps = [{ n: 1, label: 'Ruta' }, { n: 2, label: 'PDV' }, { n: 3, label: 'Cliente' }, { n: 4, label: 'Auditoría' }];
  exhibTipos = ['Cabezal', 'Torre', 'Isla', 'Cross', 'Checkout'];
  exhibSel = new Set<string>();
  secciones = [
    {
      t: 'Cumplimiento en el anaquel', qs: [
        { k: 'aplico_planograma', l: '¿Aplicó planograma?' }, { k: 'lineamiento_marca', l: 'Lineamiento de marca' },
        { k: 'precio_correcto', l: 'Precio colocado correcto' }, { k: 'limpieza_correcta', l: 'Limpieza correcta' },
        { k: 'participacion_correcta', l: 'Participación según objetivos' }, { k: 'fifo_correcto', l: 'Aplicación correcta de FIFO' }]
    },
    {
      t: 'Vencimiento y competencia', qs: [
        { k: 'prox_vencer', l: '¿Productos próximos a vencer?' }, { k: 'competencia_actividad', l: '¿Actividad de la competencia?' }]
    },
    {
      t: 'Material POP del cliente', qs: [
        { k: 'pop_hablador', l: 'Hablador' }, { k: 'pop_rompetrafico', l: 'Rompetráfico' }]
    },
    {
      t: 'Promociones', qs: [
        { k: 'promo_nuestra', l: '¿Promociones nuestras?' }, { k: 'promo_competencia', l: '¿Promociones de la competencia?' }]
    },
    { t: 'Exhibición adicional', qs: [{ k: 'exhibicion_adicional', l: '¿Existe exhibición adicional?' }] },
  ];

  step = signal(1);
  loading = signal(false);
  saving = signal(false);
  uploading = signal(false);
  uploadMsg = signal('Subiendo foto…');
  rutas = signal<Ruta[]>([]);
  pdvs = signal<Pdv[]>([]);
  clientes = signal<Cli[]>([]);
  categorias = signal<Cat[]>([]);
  catsHechas = signal<number[]>([]);
  rutaSel = signal<Ruta | null>(null);
  pdvSel = signal<Pdv | null>(null);
  clienteSel = signal<Cli | null>(null);
  catSel = signal<Cat | null>(null);
  /** Número real una vez sincronizado, o placeholder `local_<uuid>` mientras la sesión está offline. */
  idVisita = signal<number | string | null>(null);
  fotos = signal(0);
  form: any = {};
  private camMode: 'pdv-on' | 'pdv-off' | 'cat' = 'cat';

  ngOnInit() {
    this.loadRutas();
    this.offline.isOnline$.subscribe(v => this.isOnline.set(v));
    this.offline.pendingCount$.subscribe(v => this.pendingSync.set(v));
    this.offline.failedChains$.subscribe(chains => this.syncErrors.set(chains));
    this.offline.chainResolved$.subscribe(({ chainId, realVisitaId }) => {
      if (this.activeChainId === chainId) {
        this.activeChainId = null;
        this.idVisita.set(realVisitaId);
      }
    });
    if (navigator.onLine) this.offline.syncAll();
  }

  sincronizar() { this.offline.syncAll(); }

  crumb() {
    return [this.rutaSel()?.nombre, this.pdvSel()?.nombre, this.clienteSel()?.nombre, this.catSel()?.nombre].filter(Boolean).join('  ›  ');
  }
  footerBtns(): any[] {
    if (this.step() === 2) return [
      { l: 'Rutas', i: 'arrow_back', cls: 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300', fn: () => this.loadRutas() },
      { l: 'Terminar jornada', i: 'flag', cls: 'bg-red-50 dark:bg-red-950 text-red-600 dark:text-red-300', fn: () => this.desactivarRuta() }];
    if (this.step() === 3 && !this.clienteSel()) return [
      { l: 'PDVs', i: 'arrow_back', cls: 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300', fn: () => this.loadPdvs() },
      { l: 'Desactivar PDV', i: 'photo_camera', cls: 'bg-red-50 dark:bg-red-950 text-red-600 dark:text-red-300', fn: () => this.cam('pdv-off') }];
    if (this.step() === 3 && this.clienteSel()) return [
      { l: 'Clientes', i: 'arrow_back', cls: 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300', fn: () => this.abrirClientes(this.pdvSel()!) },
      { l: 'Terminar cliente', i: 'check', cls: 'bg-emerald-50 dark:bg-emerald-900 text-emerald-600 dark:text-emerald-300', fn: () => this.finalizarCliente() }];
    return [];
  }

  private get<T>(u: string) { return this.http.get<T>(`${this.API}${u}`); }
  private post<T>(u: string, b: any) { return this.http.post<T>(`${this.API}${u}`, b); }
  err(e: any) { this.snack.open(e?.error?.detail || e?.error?.message || 'Error', 'OK', { duration: 4000 }); }

  /** Lee con red y cachea; si falla (offline) sirve la última copia cacheada en vez de dejar la pantalla vacía. */
  private cachedGet<T>(url: string, cacheKey: string, onData: (v: T) => void) {
    this.get<T>(url).subscribe({
      next: v => { onData(v); this.loading.set(false); this.offline.cacheWrite(cacheKey, v); },
      error: async e => {
        const cached = await this.offline.cacheRead(cacheKey);
        if (cached) { onData(cached); this.loading.set(false); this.snack.open('Sin conexión — mostrando datos guardados', 'OK', { duration: 3000 }); }
        else { this.loading.set(false); this.err(e); }
      }
    });
  }

  loadRutas() {
    this.step.set(1); this.rutaSel.set(null); this.pdvSel.set(null); this.clienteSel.set(null); this.catSel.set(null);
    this.loading.set(true);
    this.cachedGet<Ruta[]>(`/rutas/${this.cedula}`, `rutas:${this.cedula}`, r => this.rutas.set(r));
  }
  activarRuta(r: Ruta) {
    this.rutaSel.set(r);
    const body = { id_ruta: r.id, cedula: this.cedula };
    if (!navigator.onLine) {
      this.offline.enqueueFlat({ url: `${this.API}/activar-ruta`, isMultipart: false, jsonBody: body, label: `Activar ruta ${r.nombre}` });
      this.snack.open('Ruta activada localmente — se sincronizará al reconectar', 'OK', { duration: 3000 });
      this.loadPdvs();
      return;
    }
    this.post('/activar-ruta', body).subscribe({ next: () => this.loadPdvs(), error: e => this.err(e) });
  }
  async noActivar(r: Ruta) {
    const razon = await this.confirmDialog.promptText('Motivo por el que NO activas esta ruta hoy:', { title: 'No activar ruta', placeholder: 'Escribe el motivo…', required: true, confirmText: 'Registrar' });
    if (!razon?.trim()) return;
    const body = { id_ruta: r.id, cedula: this.cedula, razon: razon.trim() };
    if (!navigator.onLine) {
      this.offline.enqueueFlat({ url: `${this.API}/no-activar-ruta`, isMultipart: false, jsonBody: body, label: `No activar ruta ${r.nombre}` });
      this.snack.open('Registrado localmente — se sincronizará al reconectar', 'OK', { duration: 3000 });
      return;
    }
    this.post('/no-activar-ruta', body).subscribe({ next: () => this.snack.open('Registrado', 'OK', { duration: 2500 }), error: e => this.err(e) });
  }
  loadPdvs() {
    this.step.set(2); this.clienteSel.set(null); this.catSel.set(null); this.loading.set(true);
    this.cachedGet<Pdv[]>(`/ruta-puntos/${this.rutaSel()!.id}?cedula=${this.cedula}`, `pdvs:${this.rutaSel()!.id}`, p => this.pdvs.set(p));
  }
  abrirClientes(p: Pdv) {
    this.pdvSel.set(p); this.step.set(3); this.clienteSel.set(null); this.catSel.set(null); this.loading.set(true);
    this.cachedGet<Cli[]>(`/pdv-clientes/${p.id}/${this.rutaSel()!.id}`, `clientes:${p.id}:${this.rutaSel()!.id}`, c => this.clientes.set(c));
  }
  iniciarCliente(c: Cli) {
    const body = { cliente_id: c.id, point_id: this.pdvSel()!.id, cedula: this.cedula };
    if (!navigator.onLine) {
      this.offline.openChain({
        clienteId: c.id, pointId: this.pdvSel()!.id, rutaId: this.rutaSel()!.id, cedula: this.cedula,
        clienteNombre: c.nombre, iniciarUrl: `${this.API}/iniciar-auditoria-cliente`, iniciarBody: body,
      }).then(({ chainId, placeholderVisitaId }) => {
        this.activeChainId = chainId;
        this.clienteSel.set(c); this.idVisita.set(placeholderVisitaId); this.catsHechas.set([]);
        this.loadCategorias();
        this.snack.open('Trabajando sin conexión — se sincronizará al reconectar', 'OK', { duration: 3000 });
      });
      return;
    }
    this.post<any>('/iniciar-auditoria-cliente', body).subscribe({
      next: r => { this.clienteSel.set(c); this.idVisita.set(r.id_visita); this.catsHechas.set([]); this.loadCategorias(); }, error: e => this.err(e)
    });
  }
  loadCategorias() {
    this.catSel.set(null); this.loading.set(true);
    this.cachedGet<Cat[]>(`/cliente-categorias/${this.clienteSel()!.id}`, `categorias:${this.clienteSel()!.id}`, c => this.categorias.set(c));
  }
  abrirCategoria(cat: Cat) {
    this.catSel.set(cat); this.step.set(4); this.form = {}; this.exhibSel.clear(); this.fotos.set(0);
  }
  toggleExhib(t: string) { this.exhibSel.has(t) ? this.exhibSel.delete(t) : this.exhibSel.add(t); }
  guardarCategoria() {
    this.saving.set(true);
    const payload = {
      ...this.form, id_visita: this.idVisita(), id_categoria: this.catSel()!.id,
      exhibicion_tipos: [...this.exhibSel].join(', ') || null
    };
    if (this.activeChainId) {
      this.offline.addChainStep(this.activeChainId, { kind: 'guardarCategoria', url: `${this.API}/guardar-auditoria-categoria`, isMultipart: false, jsonBody: payload }).then(() => {
        this.saving.set(false); this.snack.open('Categoría guardada (pendiente de sincronizar)', 'OK', { duration: 2500 });
        this.catsHechas.update(a => [...a, this.catSel()!.id]); this.step.set(3); this.catSel.set(null);
      });
      return;
    }
    this.post('/guardar-auditoria-categoria', payload).subscribe({
      next: () => {
        this.saving.set(false); this.snack.open('Categoría guardada', 'OK', { duration: 2500 });
        this.catsHechas.update(a => [...a, this.catSel()!.id]); this.step.set(3); this.catSel.set(null);
      },
      error: e => { this.saving.set(false); this.err(e); }
    });
  }
  async finalizarCliente() {
    const ok = await this.confirmDialog.confirm('¿Terminar la auditoría de este cliente?', { title: 'Finalizar cliente', confirmText: 'Sí, terminar' });
    if (!ok) return;
    const body = { id_visita: this.idVisita() };
    if (this.activeChainId) {
      this.offline.addChainStep(this.activeChainId, { kind: 'finalizarCliente', url: `${this.API}/finalizar-auditoria-cliente`, isMultipart: false, jsonBody: body }).then(() => {
        this.activeChainId = null;
        this.snack.open('Cliente finalizado (pendiente de sincronizar)', 'OK', { duration: 2500 });
        this.abrirClientes(this.pdvSel()!);
      });
      return;
    }
    this.post('/finalizar-auditoria-cliente', body).subscribe({ next: () => { this.snack.open('Cliente finalizado', 'OK', { duration: 2500 }); this.abrirClientes(this.pdvSel()!); }, error: e => this.err(e) });
  }
  activarPdv(p: Pdv) { this.pdvSel.set(p); this.cam('pdv-on'); }
  async desactivarRuta() {
    const ok = await this.confirmDialog.confirm('¿Terminar la jornada de esta ruta?', { title: 'Finalizar jornada', confirmText: 'Sí, terminar', danger: true });
    if (!ok) return;
    const body = { id_ruta: this.rutaSel()!.id, cedula: this.cedula };
    if (!navigator.onLine) {
      this.offline.enqueueFlat({ url: `${this.API}/desactivar-ruta`, isMultipart: false, jsonBody: body, label: `Terminar jornada ${this.rutaSel()?.nombre}` });
      this.snack.open('Jornada terminada localmente — se sincronizará al reconectar', 'OK', { duration: 3000 });
      this.loadRutas();
      return;
    }
    this.post('/desactivar-ruta', body).subscribe({ next: () => { this.snack.open('Jornada terminada', 'OK', { duration: 2500 }); this.loadRutas(); }, error: e => this.err(e) });
  }

  // ── Cámara ──
  private camEl?: HTMLInputElement;
  cam(mode: 'pdv-on' | 'pdv-off' | 'cat') {
    this.camMode = mode;
    this.camEl ??= document.querySelector('input[type=file]') as HTMLInputElement;
    this.camEl?.click();
  }
  onCam(ev: Event) {
    const file = (ev.target as HTMLInputElement).files?.[0];
    (ev.target as HTMLInputElement).value = '';
    if (!file) return;
    const send = (lat?: number, lon?: number) => {
      this.uploadMsg.set('Subiendo foto…'); this.uploading.set(true);
      const fields: Record<string, string> = { cedula: this.cedula };
      if (lat != null) fields['lat'] = String(lat);
      if (lon != null) fields['lon'] = String(lon);
      let url = '';
      if (this.camMode === 'cat') {
        url = '/subir-foto-categoria';
        fields['id_visita'] = String(this.idVisita());
        fields['id_categoria'] = String(this.catSel()!.id);
        fields['categoria_nombre'] = this.catSel()!.nombre;
        fields['point_id'] = this.pdvSel()?.id || '';

        if (this.activeChainId) {
          this.offline.addChainStep(this.activeChainId, {
            kind: 'subirFotoCategoria', url: `${this.API}${url}`, isMultipart: true,
            formFields: fields, fileBlob: file, fileName: file.name,
          }).then(() => { this.uploading.set(false); this.fotos.update(n => n + 1); });
          return;
        }
      } else {
        url = this.camMode === 'pdv-on' ? '/activar-pdv' : '/desactivar-pdv';
        fields['point_id'] = this.pdvSel()!.id;

        if (!navigator.onLine) {
          const label = this.camMode === 'pdv-on' ? `Activar PDV ${this.pdvSel()?.nombre}` : `Desactivar PDV ${this.pdvSel()?.nombre}`;
          this.offline.enqueueFlat({ url: `${this.API}${url}`, isMultipart: true, formFields: fields, fileBlob: file, fileName: file.name, label });
          this.uploading.set(false);
          if (this.camMode === 'pdv-on') this.abrirClientes(this.pdvSel()!);
          else { this.snack.open('PDV desactivado localmente — se sincronizará al reconectar', 'OK', { duration: 3000 }); this.loadPdvs(); }
          return;
        }
      }
      const fd = new FormData();
      for (const [k, v] of Object.entries(fields)) fd.append(k, v);
      fd.append('file', file);
      this.http.post<any>(`${this.API}${url}`, fd).subscribe({
        next: () => {
          this.uploading.set(false);
          if (this.camMode === 'cat') this.fotos.update(n => n + 1);
          else if (this.camMode === 'pdv-on') this.abrirClientes(this.pdvSel()!);
          else { this.snack.open('PDV desactivado', 'OK', { duration: 2500 }); this.loadPdvs(); }
        },
        error: e => { this.uploading.set(false); this.err(e); }
      });
    };
    if (navigator.geolocation) navigator.geolocation.getCurrentPosition(p => send(p.coords.latitude, p.coords.longitude), () => send(), { enableHighAccuracy: true, timeout: 8000 });
    else send();
  }
}
