import { Component, OnInit, OnDestroy, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MercSocketService } from '../../services/merc-socket.service';
import { MercUiService } from '../../services/merc-ui.service';
import { ApiService } from '../../../../core/services/api.service';
import { BrowserNotificationService } from '../../services/browser-notification.service';
import { GrupoDetalleComponent } from './components/grupo-detalle/grupo-detalle.component';
import { GrupoVisitaChatComponent } from './components/grupo-visita-chat/grupo-visita-chat.component';
import { interval, Subscription } from 'rxjs';
import { startWith, switchMap } from 'rxjs/operators';

@Component({
  selector: 'app-merc-chat',
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule, MatButtonModule, MatProgressSpinnerModule,
    GrupoDetalleComponent, GrupoVisitaChatComponent],
  template: `
    <div class="flex flex-col h-full bg-white dark:bg-slate-950">

      <!-- TABS -->
      <div class="flex border-b border-slate-100 dark:border-white/5 bg-white dark:bg-slate-900 shrink-0 overflow-x-auto">
        <button (click)="activeTab.set('equipo')"
                [class]="activeTab() === 'equipo' ? 'border-b-2 border-primary-500 text-primary-600 dark:text-primary-400' : 'text-slate-500'"
                class="flex items-center gap-1.5 px-3 py-3.5 text-[10px] font-black uppercase tracking-widest whitespace-nowrap transition-colors">
          <mat-icon class="!text-sm">chat</mat-icon>
          Visitas
          @if (unreadEquipo() > 0) {
            <span class="bg-emerald-500 text-white text-[8px] font-black w-4 h-4 rounded-full flex items-center justify-center">{{ unreadEquipo() }}</span>
          }
        </button>
        <button (click)="activeTab.set('grupo_operativo')"
                [class]="activeTab() === 'grupo_operativo' ? 'border-b-2 border-indigo-500 text-indigo-600 dark:text-indigo-400' : 'text-slate-500'"
                class="flex items-center gap-1.5 px-3 py-3.5 text-[10px] font-black uppercase tracking-widest whitespace-nowrap transition-colors">
          <mat-icon class="!text-sm">groups</mat-icon>
          G. Operativo
          @if (unreadGrupoOperativo() > 0) {
            <span class="bg-indigo-500 text-white text-[8px] font-black w-4 h-4 rounded-full flex items-center justify-center">{{ unreadGrupoOperativo() }}</span>
          }
        </button>
        <button (click)="activeTab.set('grupo_cliente')"
                [class]="activeTab() === 'grupo_cliente' ? 'border-b-2 border-purple-500 text-purple-600 dark:text-purple-400' : 'text-slate-500'"
                class="flex items-center gap-1.5 px-3 py-3.5 text-[10px] font-black uppercase tracking-widest whitespace-nowrap transition-colors">
          <mat-icon class="!text-sm">business</mat-icon>
          G. Cliente
          @if (unreadGrupoCliente() > 0) {
            <span class="bg-purple-500 text-white text-[8px] font-black w-4 h-4 rounded-full flex items-center justify-center">{{ unreadGrupoCliente() }}</span>
          }
        </button>
        <button (click)="activeTab.set('notificaciones')"
                [class]="activeTab() === 'notificaciones' ? 'border-b-2 border-primary-500 text-primary-600 dark:text-primary-400' : 'text-slate-500'"
                class="flex items-center gap-1.5 px-3 py-3.5 text-[10px] font-black uppercase tracking-widest whitespace-nowrap transition-colors">
          <mat-icon class="!text-sm">notifications</mat-icon>
          Alertas
          @if (unreadNotif() > 0) {
            <span class="bg-rose-500 text-white text-[8px] font-black w-4 h-4 rounded-full flex items-center justify-center">{{ unreadNotif() }}</span>
          }
        </button>
      </div>

      <!-- CONTENIDO DE TABS -->
      <div class="flex-grow overflow-hidden">
        @if (selectedGrupo() && (activeTab() === 'grupo_operativo' || activeTab() === 'grupo_cliente')) {
          @if (selectedThread()) {
            <app-grupo-visita-chat [threadData]="selectedThread()" (back)="closeThread()"></app-grupo-visita-chat>
          } @else {
            <app-grupo-detalle [grupoData]="selectedGrupo()"
                               (back)="closeGrupo()"
                               (openVisitThread)="openGroupThread($event)"></app-grupo-detalle>
          }
        } @else {
          <div class="flex-grow overflow-y-auto h-full">

            @if (loading()) {
              <div class="py-20 flex flex-col items-center gap-3">
                <mat-spinner diameter="32"></mat-spinner>
                <span class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Cargando mensajes...</span>
              </div>
            }

            <!-- TAB: VISITAS (Equipo Operativo) -->
            @if (!loading() && activeTab() === 'equipo') {
              @if (equipoConvs().length === 0) {
                <div class="py-20 text-center flex flex-col items-center gap-4 opacity-40">
                  <mat-icon class="!text-5xl text-slate-400">chat_bubble_outline</mat-icon>
                  <p class="text-xs font-bold text-slate-500">No tienes chats de visitas todavía</p>
                  <p class="text-[10px] text-slate-400 uppercase tracking-widest">Inicia una visita para chatear</p>
                </div>
              } @else {
                <div class="divide-y divide-slate-100 dark:divide-white/5">
                  @for (c of equipoConvs(); track c.id_visita) {
                    <div (click)="openChat(c)"
                         class="flex items-center gap-3 px-4 py-3.5 cursor-pointer hover:bg-slate-50 dark:hover:bg-white/5 transition-colors active:bg-slate-100 dark:active:bg-white/10">
                      <div class="relative shrink-0">
                        <div class="w-12 h-12 rounded-[1rem] flex items-center justify-center bg-primary-500/10">
                          <mat-icon class="text-primary-500 !text-xl">chat</mat-icon>
                        </div>
                        @if ((c.no_leidos ?? c.noLeidos ?? 0) > 0) {
                          <div class="absolute -top-1 -right-1 w-5 h-5 bg-emerald-500 text-white rounded-full border-2 border-white dark:border-slate-950 flex items-center justify-center text-[8px] font-black">
                            {{ c.no_leidos ?? c.noLeidos }}
                          </div>
                        }
                      </div>
                      <div class="flex-1 min-w-0">
                        <div class="flex items-center justify-between gap-2">
                          <h4 [class]="(c.no_leidos ?? c.noLeidos ?? 0) > 0 ? 'font-bold' : 'font-semibold'"
                              class="text-sm text-slate-800 dark:text-white truncate">
                            {{ c.titulo || c.pdv_nombre || 'Chat' }}
                          </h4>
                          <span class="text-[9px] font-bold shrink-0"
                                [class]="(c.no_leidos ?? c.noLeidos ?? 0) > 0 ? 'text-primary-500' : 'text-slate-400'">
                            {{ formatChatDate(c.fecha_ultimo ?? c.ultimo_at) }}
                          </span>
                        </div>
                        @if (c.subtitulo || c.cliente) {
                          <p class="text-[10px] text-slate-500 truncate">{{ c.subtitulo || c.cliente }}</p>
                        }
                        <p [class]="(c.no_leidos ?? c.noLeidos ?? 0) > 0 ? 'font-semibold text-slate-700 dark:text-slate-200' : 'text-slate-400'"
                           class="text-xs truncate mt-0.5">
                          {{ c.ultimo_mensaje ?? c.ultimo_msg ?? 'Sin mensajes aún' }}
                        </p>
                      </div>
                      <mat-icon class="text-slate-300 !text-base shrink-0">chevron_right</mat-icon>
                    </div>
                  }
                </div>
              }
            }

            <!-- TAB: GRUPO OPERATIVO -->
            @if (!loading() && activeTab() === 'grupo_operativo') {
              @if (gruposOperativo().length === 0) {
                <div class="py-20 text-center flex flex-col items-center gap-4 opacity-40">
                  <mat-icon class="!text-5xl text-slate-400">groups</mat-icon>
                  <p class="text-xs font-bold text-slate-500">No tienes grupos operativos</p>
                  <p class="text-[10px] text-slate-400 uppercase tracking-widest">Se te asignarán automáticamente</p>
                </div>
              } @else {
                <div class="divide-y divide-slate-100 dark:divide-white/5">
                  @for (g of gruposOperativo(); track g.id_grupo) {
                    <div (click)="openGrupo(g)"
                         class="flex items-center gap-3 px-4 py-3.5 cursor-pointer hover:bg-slate-50 dark:hover:bg-white/5 transition-colors active:bg-slate-100 dark:active:bg-white/10">
                      <div class="relative shrink-0">
                        <div class="w-12 h-12 rounded-[1rem] flex items-center justify-center bg-indigo-500/10">
                          <mat-icon class="text-indigo-500 !text-xl">groups</mat-icon>
                        </div>
                        @if ((g.no_leidos ?? 0) > 0) {
                          <div class="absolute -top-1 -right-1 w-5 h-5 bg-indigo-500 text-white rounded-full border-2 border-white dark:border-slate-950 flex items-center justify-center text-[8px] font-black">
                            {{ g.no_leidos }}
                          </div>
                        }
                      </div>
                      <div class="flex-1 min-w-0">
                        <div class="flex items-center justify-between gap-2">
                          <h4 [class]="(g.no_leidos ?? 0) > 0 ? 'font-bold' : 'font-semibold'"
                              class="text-sm text-slate-800 dark:text-white truncate">
                            {{ g.nombre || ('Grupo ' + g.id_grupo) }}
                          </h4>
                          <span class="text-[9px] font-bold shrink-0"
                                [class]="(g.no_leidos ?? 0) > 0 ? 'text-indigo-500' : 'text-slate-400'">
                            {{ formatChatDate(g.ultimo_mensaje_fecha) }}
                          </span>
                        </div>
                        <p [class]="(g.no_leidos ?? 0) > 0 ? 'font-semibold text-slate-700 dark:text-slate-200' : 'text-slate-400'"
                           class="text-xs truncate mt-0.5">
                          {{ g.ultimo_mensaje || 'Sin mensajes aún' }}
                        </p>
                      </div>
                      <mat-icon class="text-slate-300 !text-base shrink-0">chevron_right</mat-icon>
                    </div>
                  }
                </div>
              }
            }

            <!-- TAB: GRUPO CLIENTE -->
            @if (!loading() && activeTab() === 'grupo_cliente') {
              @if (gruposCliente().length === 0) {
                <div class="py-20 text-center flex flex-col items-center gap-4 opacity-40">
                  <mat-icon class="!text-5xl text-slate-400">business</mat-icon>
                  <p class="text-xs font-bold text-slate-500">No tienes grupos con clientes</p>
                  <p class="text-[10px] text-slate-400 uppercase tracking-widest">Se te asignarán automáticamente</p>
                </div>
              } @else {
                <div class="divide-y divide-slate-100 dark:divide-white/5">
                  @for (g of gruposCliente(); track g.id_grupo) {
                    <div (click)="openGrupo(g)"
                         class="flex items-center gap-3 px-4 py-3.5 cursor-pointer hover:bg-slate-50 dark:hover:bg-white/5 transition-colors active:bg-slate-100 dark:active:bg-white/10">
                      <div class="relative shrink-0">
                        <div class="w-12 h-12 rounded-[1rem] flex items-center justify-center bg-purple-500/10">
                          <mat-icon class="text-purple-500 !text-xl">business</mat-icon>
                        </div>
                        @if ((g.no_leidos ?? 0) > 0) {
                          <div class="absolute -top-1 -right-1 w-5 h-5 bg-purple-500 text-white rounded-full border-2 border-white dark:border-slate-950 flex items-center justify-center text-[8px] font-black">
                            {{ g.no_leidos }}
                          </div>
                        }
                      </div>
                      <div class="flex-1 min-w-0">
                        <div class="flex items-center justify-between gap-2">
                          <h4 [class]="(g.no_leidos ?? 0) > 0 ? 'font-bold' : 'font-semibold'"
                              class="text-sm text-slate-800 dark:text-white truncate">
                            {{ g.nombre || ('Grupo ' + g.id_grupo) }}
                          </h4>
                          <span class="text-[9px] font-bold shrink-0"
                                [class]="(g.no_leidos ?? 0) > 0 ? 'text-purple-500' : 'text-slate-400'">
                            {{ formatChatDate(g.ultimo_mensaje_fecha) }}
                          </span>
                        </div>
                        <p [class]="(g.no_leidos ?? 0) > 0 ? 'font-semibold text-slate-700 dark:text-slate-200' : 'text-slate-400'"
                           class="text-xs truncate mt-0.5">
                          {{ g.ultimo_mensaje || 'Sin mensajes aún' }}
                        </p>
                      </div>
                      <mat-icon class="text-slate-300 !text-base shrink-0">chevron_right</mat-icon>
                    </div>
                  }
                </div>
              }
            }

            <!-- TAB: NOTIFICACIONES (rechazos y alertas) -->
            @if (!loading() && activeTab() === 'notificaciones') {
              @if (notificaciones().length === 0) {
                <div class="py-20 text-center flex flex-col items-center gap-4 opacity-40">
                  <mat-icon class="!text-5xl text-slate-400">notifications_none</mat-icon>
                  <p class="text-xs font-bold text-slate-500">Sin notificaciones pendientes</p>
                  <p class="text-[10px] text-slate-400 uppercase tracking-widest">Todo en orden ✓</p>
                </div>
              } @else {
                <div class="divide-y divide-slate-100 dark:divide-white/5">
                  @for (n of notificaciones(); track $index) {
                    <div class="flex items-start gap-3 px-4 py-3.5"
                         [class]="n.leido ? 'opacity-60' : ''">
                      <div class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 mt-0.5"
                           [class]="n.tipo === 'rechazo' ? 'bg-rose-500/10' : 'bg-emerald-500/10'">
                        <mat-icon [class]="n.tipo === 'rechazo' ? 'text-rose-500' : 'text-emerald-500'" class="!text-xl">
                          {{ n.tipo === 'rechazo' ? 'block' : 'check_circle' }}
                        </mat-icon>
                      </div>
                      <div class="flex-1 min-w-0">
                        <p [class]="n.leido ? 'font-semibold' : 'font-bold'"
                           class="text-sm text-slate-800 dark:text-white leading-snug">
                          {{ n.tipo === 'rechazo' ? 'Foto rechazada' : 'Foto aprobada' }}
                        </p>
                        @if (n.pdv_nombre || n.cliente_nombre) {
                          <p class="text-[10px] text-slate-500 truncate">{{ n.pdv_nombre }} · {{ n.cliente_nombre }}</p>
                        }
                        @if (n.motivo) {
                          <p class="text-xs text-rose-500 italic mt-0.5">Motivo: {{ n.motivo }}</p>
                        }
                        <p class="text-[9px] text-slate-400 mt-1">{{ formatChatDate(n.fecha) }}</p>
                      </div>
                      @if (!n.leido) {
                        <div class="w-2 h-2 rounded-full bg-rose-500 mt-2 shrink-0"></div>
                      }
                    </div>
                  }
                </div>
              }
            }

          </div>
        }

      </div>
    </div>
  `,
  styles: [`:host { display: block; height: 100%; }`]
})
export class MercChatComponent implements OnInit, OnDestroy {
  private socket = inject(MercSocketService);
  private ui = inject(MercUiService);
  private api = inject(ApiService);
  private notif = inject(BrowserNotificationService);

  loading = signal(true);
  activeTab = signal<'equipo' | 'grupo_operativo' | 'grupo_cliente' | 'notificaciones'>('equipo');

  equipoConvs = signal<any[]>([]);
  clienteConvs = signal<any[]>([]);
  notificaciones = signal<any[]>([]);

  grupos = signal<any[]>([]);
  selectedGrupo = signal<any>(null);
  selectedThread = signal<{ grupo: any; visita: any } | null>(null);

  gruposOperativo = () => this.grupos().filter(g => g.tipo_grupo === 'operativo');
  gruposCliente = () => this.grupos().filter(g => g.tipo_grupo === 'operativo_cliente');

  unreadEquipo = () => this.equipoConvs().reduce((s, c) => s + (c.no_leidos ?? c.noLeidos ?? 0), 0);
  unreadCliente = () => this.clienteConvs().reduce((s, c) => s + (c.no_leidos ?? c.noLeidos ?? 0), 0);
  unreadGrupoOperativo = () => this.grupos().filter(g => g.tipo_grupo === 'operativo').reduce((s, g) => s + (g.no_leidos ?? 0), 0);
  unreadGrupoCliente = () => this.grupos().filter(g => g.tipo_grupo === 'operativo_cliente').reduce((s, g) => s + (g.no_leidos ?? 0), 0);
  unreadNotif = () => this.notificaciones().filter(n => !n.leido).length;

  private pollSub?: Subscription;
  private gruposPollSub?: Subscription;

  ngOnInit(): void {
    this.loadInbox();
    this.loadGrupos();
    // Poll inbox cada 30 segundos
    this.pollSub = interval(30000).pipe(startWith(0), switchMap(() => this.socket.getInbox())).subscribe({
      next: (res: any) => {
        this.socket.checkInboxForNotifications(res);
        this.processInbox(res);
      },
      error: () => { }
    });
    // Poll grupos cada 30 segundos
    this.gruposPollSub = interval(30000).pipe(startWith(0), switchMap(() => this.api.getMercMisGrupos())).subscribe({
      next: (res: any[]) => this.grupos.set(res || []),
      error: () => { }
    });
  }

  ngOnDestroy(): void {
    this.pollSub?.unsubscribe();
    this.gruposPollSub?.unsubscribe();
  }

  loadInbox(): void {
    this.loading.set(true);
    this.socket.getInbox().subscribe({
      next: (res: any) => {
        this.processInbox(res);
        this.loading.set(false);
      },
      error: () => this.loading.set(false)
    });
  }

  loadGrupos(): void {
    this.api.getMercMisGrupos().subscribe({
      next: (res: any[]) => this.grupos.set(res || []),
      error: () => { }
    });
  }

  private processInbox(res: any): void {
    if (!res) return;
    if (Array.isArray(res)) {
      this.equipoConvs.set(res);
      this.clienteConvs.set([]);
      this.notificaciones.set([]);
    } else {
      this.equipoConvs.set(res.equipo_operativo ?? res.conversaciones_equipo ?? res.conversaciones ?? []);
      this.clienteConvs.set(res.equipo_cliente ?? res.conversaciones_cliente ?? []);
      this.notificaciones.set([
        ...(res.rechazos ?? []).map((r: any) => ({ ...r, tipo: 'rechazo' })),
        ...(res.aprobaciones ?? []).map((a: any) => ({ ...a, tipo: 'aprobacion' })),
        ...(res.notificaciones ?? []),
      ].sort((a, b) => new Date(b.fecha ?? 0).getTime() - new Date(a.fecha ?? 0).getTime()));
    }
    this.loading.set(false);
  }

  openChat(c: any): void {
    this.ui.openVisit({
      id_visita: c.id_visita,
      pdv_nombre: c.titulo ?? c.pdv_nombre,
      id_cliente: c.id_cliente,
      cliente: c.subtitulo ?? c.cliente
    });
  }

  openGrupo(g: any): void {
    this.selectedGrupo.set(g);
    // Marcar como leído al abrir
    this.api.marcarLeidoGrupo(g.id_grupo).subscribe({ error: () => { } });
  }

  closeGrupo(): void {
    this.selectedGrupo.set(null);
    this.selectedThread.set(null);
  }

  openGroupThread(event: { grupo: any; visita: any }): void {
    this.selectedThread.set({ grupo: event.grupo, visita: event.visita });
  }

  closeThread(): void {
    this.selectedThread.set(null);
  }

  formatChatDate(raw: string | null | undefined): string {
    if (!raw) return '';
    try {
      const dt = new Date(raw);
      const now = new Date();
      const isToday = dt.toDateString() === now.toDateString();
      const yesterday = new Date(now);
      yesterday.setDate(now.getDate() - 1);
      const isYesterday = dt.toDateString() === yesterday.toDateString();

      if (isToday) return dt.toLocaleTimeString('es-VE', { hour: '2-digit', minute: '2-digit' });
      if (isYesterday) return 'Ayer';
      return dt.toLocaleDateString('es-VE', { day: '2-digit', month: '2-digit', year: '2-digit' });
    } catch { return ''; }
  }
}
