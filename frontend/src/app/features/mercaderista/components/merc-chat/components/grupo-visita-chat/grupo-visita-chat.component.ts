import { Component, Input, Output, EventEmitter, OnInit, OnDestroy, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { HttpClient } from '@angular/common/http';
import { interval, Subscription } from 'rxjs';
import { switchMap, startWith } from 'rxjs/operators';

interface ThreadMessage {
  id_mensaje: number;
  id_cliente: number;
  tipo_grupo: string;
  id_visita: number;
  id_usuario?: number;
  username?: string;
  mensaje: string;
  tipo_mensaje: string;
  fecha_envio?: string;
  foto_adjunta?: string;
  es_mio: boolean;
}

@Component({
  selector: 'app-grupo-visita-chat',
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule, MatButtonModule, MatProgressSpinnerModule],
  template: `
    <div class="flex flex-col h-full bg-white dark:bg-slate-950">

      <!-- Header -->
      <div class="shrink-0 px-4 py-3 flex items-center gap-3 border-b border-slate-100 dark:border-white/5 bg-slate-50 dark:bg-slate-900">
        <button (click)="back.emit()"
                class="w-9 h-9 rounded-xl bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-500 active:scale-95 transition-all">
          <mat-icon class="!text-lg">arrow_back</mat-icon>
        </button>
        <div class="flex-1 min-w-0">
          <h3 class="font-bold text-sm text-slate-800 dark:text-white truncate">
            {{ visita().punto || 'Visita' }}
          </h3>
          <span class="text-[9px] font-black text-slate-400 uppercase tracking-widest">
            {{ visita().mercaderista || '' }}
          </span>
        </div>
        <span class="text-[9px] font-bold px-2 py-0.5 rounded-full"
              [class]="visita().estado === 'completada' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-amber-500/10 text-amber-500'">
          {{ visita().estado || 'activa' }}
        </span>
      </div>

      <!-- Messages -->
      <div class="flex-grow overflow-y-auto p-3 space-y-2 bg-slate-50/50 dark:bg-slate-950/50">
        @if (loading()) {
          <div class="py-16 flex flex-col items-center gap-3">
            <mat-spinner diameter="28"></mat-spinner>
            <span class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Cargando mensajes...</span>
          </div>
        } @else if (messages().length === 0) {
          <div class="py-16 text-center flex flex-col items-center gap-3 opacity-40">
            <mat-icon class="!text-4xl text-slate-400">forum</mat-icon>
            <p class="text-xs font-bold text-slate-500">Sin mensajes aún en este hilo</p>
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
               placeholder="Escribí un mensaje en este hilo..."
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
export class GrupoVisitaChatComponent implements OnInit, OnDestroy {
  @Input() set threadData(val: { grupo: any; visita: any } | null) {
    this.grupo.set(val?.grupo ?? null);
    this.visita.set(val?.visita ?? null);
    this.messages.set([]);
    this.newMessage = '';
    if (val) this.loadMessages();
  }
  @Output() back = new EventEmitter<void>();

  grupo = signal<any>(null);
  visita = signal<any>(null);
  messages = signal<ThreadMessage[]>([]);
  loading = signal(true);
  sending = signal(false);
  newMessage = '';

  private http = inject(HttpClient);
  private pollSub?: Subscription;

  ngOnInit(): void { }

  ngOnDestroy(): void {
    this.pollSub?.unsubscribe();
  }

  private get idGrupo(): number {
    return this.grupo()?.id_grupo;
  }

  private get idVisita(): number {
    return this.visita()?.id_visita;
  }

  loadMessages(): void {
    this.loading.set(true);
    this.pollSub?.unsubscribe();
    this.pollSub = interval(8000).pipe(
      startWith(0),
      switchMap(() =>
        this.http.get<ThreadMessage[]>(`/api/merc/chat/grupos/${this.idGrupo}/visitas/${this.idVisita}`)
      )
    ).subscribe({
      next: (res) => {
        this.messages.set(res || []);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  enviar(): void {
    const texto = this.newMessage.trim();
    if (!texto || this.sending()) return;

    this.sending.set(true);
    this.http.post(`/api/merc/chat/grupos/${this.idGrupo}/visitas/${this.idVisita}`, { mensaje: texto }).subscribe({
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
