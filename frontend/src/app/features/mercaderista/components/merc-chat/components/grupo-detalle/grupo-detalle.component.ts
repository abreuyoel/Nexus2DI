import { Component, Input, Output, EventEmitter, OnInit, OnDestroy, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { HttpClient } from '@angular/common/http';
import { interval, Subscription } from 'rxjs';
import { switchMap, startWith } from 'rxjs/operators';

interface GroupMessage {
  id_mensaje: number;
  id_grupo: number;
  id_usuario?: number;
  username?: string;
  mensaje: string;
  tipo_mensaje: string;
  fecha_envio?: string;
  foto_adjunta?: string;
  es_mio: boolean;
}

interface ActiveVisitThread {
  id_visita: number;
  fecha_visita?: string;
  mercaderista?: string;
  punto?: string;
  estado?: string;
  ultimo_mensaje?: string;
  fecha_ultimo?: string;
}

@Component({
  selector: 'app-grupo-detalle',
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule, MatButtonModule, MatProgressSpinnerModule, MatDialogModule],
  template: `
    <div class="flex flex-col h-full bg-white dark:bg-slate-950">

      <!-- Header -->
      <div class="shrink-0 px-4 py-3 flex items-center gap-3 border-b border-slate-100 dark:border-white/5 bg-slate-50 dark:bg-slate-900">
        <button (click)="back.emit()"
                class="w-9 h-9 rounded-xl bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-500 active:scale-95 transition-all">
          <mat-icon class="!text-lg">arrow_back</mat-icon>
        </button>
        <div class="flex-1 min-w-0">
          <h3 class="font-bold text-sm text-slate-800 dark:text-white truncate">{{ grupo()?.nombre || 'Grupo' }}</h3>
          <span class="text-[9px] font-black text-slate-400 uppercase tracking-widest">
            {{ grupo()?.tipo_grupo === 'operativo' ? 'Equipo Operativo' : 'Equipo + Cliente' }}
          </span>
        </div>
        <button (click)="toggleMiembros()"
                class="w-9 h-9 rounded-xl bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-500 active:scale-95 transition-all">
          <mat-icon class="!text-lg">people</mat-icon>
        </button>
      </div>

      <!-- Miembros Panel (collapsible) -->
      @if (showMiembros()) {
        <div class="shrink-0 bg-slate-50 dark:bg-slate-900 border-b border-slate-100 dark:border-white/5 px-4 py-3">
          <div class="flex items-center justify-between mb-2">
            <h4 class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Miembros ({{ miembros().length }})</h4>
            <button (click)="toggleMiembros()" class="text-slate-400">
              <mat-icon class="!text-sm">close</mat-icon>
            </button>
          </div>
          <div class="flex flex-wrap gap-1.5">
            @for (m of miembros(); track m.id_usuario) {
              <span class="text-[10px] font-semibold px-2 py-1 rounded-lg"
                    [class]="m.origen === 'mercaderista' ? 'bg-primary-500/10 text-primary-600' : 'bg-indigo-500/10 text-indigo-600'">
                {{ m.nombre || m.username }}
              </span>
            }
          </div>
        </div>
      }

      <!-- Visitas Activas (threads) -->
      @if (visitasActivas().length > 0) {
        <div class="shrink-0 bg-slate-50 dark:bg-slate-900 border-b border-slate-100 dark:border-white/5 px-4 py-2">
          <h4 class="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2">Hilos de Visita</h4>
          <div class="flex gap-2 overflow-x-auto pb-1">
            @for (v of visitasActivas(); track v.id_visita) {
              <button (click)="openThread(v)"
                      class="shrink-0 bg-white dark:bg-slate-800 border border-slate-200 dark:border-white/10 rounded-xl px-3 py-2 text-left hover:border-primary-400 transition-colors">
                <p class="text-[10px] font-bold text-slate-700 dark:text-slate-200 leading-tight truncate max-w-[120px]">{{ v.punto || 'PDV' }}</p>
                <p class="text-[8px] text-slate-400 uppercase truncate max-w-[120px]">{{ v.mercaderista || '' }}</p>
                @if (v.ultimo_mensaje) {
                  <p class="text-[9px] text-slate-500 truncate max-w-[120px] mt-0.5">"{{ v.ultimo_mensaje }}"</p>
                }
              </button>
            }
          </div>
        </div>
      }

      <!-- Messages -->
      <div #msgContainer class="flex-grow overflow-y-auto p-3 space-y-2 bg-slate-50/50 dark:bg-slate-950/50">
        @if (loading()) {
          <div class="py-16 flex flex-col items-center gap-3">
            <mat-spinner diameter="28"></mat-spinner>
            <span class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Cargando mensajes...</span>
          </div>
        } @else if (messages().length === 0) {
          <div class="py-16 text-center flex flex-col items-center gap-3 opacity-40">
            <mat-icon class="!text-4xl text-slate-400">forum</mat-icon>
            <p class="text-xs font-bold text-slate-500">Sin mensajes aún</p>
            <p class="text-[10px] text-slate-400">Sé el primero en escribir</p>
          </div>
        } @else {
          @for (m of messages(); track m.id_mensaje) {
            <div [class]="m.es_mio ? 'flex justify-end' : 'flex justify-start'">
              <div [class]="m.es_mio
                  ? 'bg-primary-600 text-white rounded-2xl rounded-br-md max-w-[80%]'
                  : 'bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 border border-slate-100 dark:border-white/5 rounded-2xl rounded-bl-md max-w-[80%]'"
                   class="px-3.5 py-2 shadow-sm">
                @if (!m.es_mio && m.username) {
                  <p class="text-[9px] font-black text-primary-500 uppercase tracking-wider mb-0.5">{{ m.username }}</p>
                }
                <p class="text-xs leading-relaxed whitespace-pre-wrap break-words">{{ m.mensaje }}</p>
                <p [class]="m.es_mio ? 'text-white/60' : 'text-slate-400'"
                   class="text-[8px] font-medium text-right mt-1">
                  {{ formatHora(m.fecha_envio) }}
                </p>
              </div>
            </div>
          }
        }
      </div>

      <!-- Input -->
      <div class="shrink-0 p-3 border-t border-slate-100 dark:border-white/5 bg-white dark:bg-slate-900 flex items-center gap-2">
        <input [(ngModel)]="newMessage" (keyup.enter)="enviar()"
               placeholder="Escribí un mensaje..."
               class="flex-1 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-white/10 rounded-2xl px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-primary-500 text-slate-800 dark:text-white">
        <button (click)="enviar()" [disabled]="!newMessage.trim() || sending()"
                class="w-11 h-11 shrink-0 rounded-2xl bg-primary-600 hover:bg-primary-500 disabled:opacity-40 text-white flex items-center justify-center transition-all active:scale-95">
          <mat-icon class="!text-lg">{{ sending() ? 'hourglass_empty' : 'send' }}</mat-icon>
        </button>
      </div>

    </div>
  `,
  styles: [`:host { display: block; height: 100%; }`]
})
export class GrupoDetalleComponent implements OnInit, OnDestroy {
  @Input() set grupoData(val: any) {
    this.grupo.set(val);
    this.showMiembros.set(false);
    this.messages.set([]);
    this.newMessage = '';
  }
  @Output() back = new EventEmitter<void>();
  @Output() openVisitThread = new EventEmitter<{ grupo: any; visita: any }>();

  grupo = signal<any>(null);
  messages = signal<GroupMessage[]>([]);
  miembros = signal<any[]>([]);
  visitasActivas = signal<ActiveVisitThread[]>([]);
  loading = signal(true);
  sending = signal(false);
  showMiembros = signal(false);
  newMessage = '';

  private http = inject(HttpClient);
  private pollSub?: Subscription;
  private miembrosPollSub?: Subscription;

  ngOnInit(): void {
    this.loadMessages();
    this.loadVisitasActivas();
  }

  ngOnDestroy(): void {
    this.pollSub?.unsubscribe();
    this.miembrosPollSub?.unsubscribe();
  }

  private get idGrupo(): number {
    return this.grupo()?.id_grupo;
  }

  loadMessages(): void {
    this.loading.set(true);
    this.pollSub?.unsubscribe();
    this.pollSub = interval(8000).pipe(
      startWith(0),
      switchMap(() => this.http.get<GroupMessage[]>(`/api/merc/chat/grupos/${this.idGrupo}/mensajes`))
    ).subscribe({
      next: (res) => {
        this.messages.set(res || []);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  loadVisitasActivas(): void {
    this.http.get<ActiveVisitThread[]>(`/api/merc/chat/grupos/${this.idGrupo}/visitas-activas`).subscribe({
      next: (res) => this.visitasActivas.set(res || []),
      error: () => { },
    });
  }

  toggleMiembros(): void {
    if (this.showMiembros()) {
      this.showMiembros.set(false);
    } else {
      this.showMiembros.set(true);
      this.loadMiembros();
    }
  }

  loadMiembros(): void {
    this.http.get<any[]>(`/api/merc/chat/grupos/${this.idGrupo}/miembros`).subscribe({
      next: (res) => this.miembros.set(res || []),
      error: () => { },
    });
  }

  openThread(visita: ActiveVisitThread): void {
    this.openVisitThread.emit({ grupo: this.grupo(), visita });
  }

  enviar(): void {
    const texto = this.newMessage.trim();
    if (!texto || this.sending()) return;

    this.sending.set(true);
    this.http.post(`/api/merc/chat/grupos/${this.idGrupo}/mensajes`, { mensaje: texto }).subscribe({
      next: () => {
        this.newMessage = '';
        this.sending.set(false);
      },
      error: () => this.sending.set(false),
    });
  }

  formatHora(raw?: string): string {
    if (!raw) return '';
    try {
      return new Date(raw).toLocaleTimeString('es-VE', { hour: '2-digit', minute: '2-digit' });
    } catch { return ''; }
  }
}
