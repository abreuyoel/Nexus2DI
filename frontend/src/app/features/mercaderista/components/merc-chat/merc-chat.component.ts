import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatBadgeModule } from '@angular/material/badge';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MercSocketService } from '../../services/merc-socket.service';
import { MercUiService } from '../../services/merc-ui.service';

@Component({
  selector: 'app-merc-chat',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatButtonModule, MatBadgeModule, MatProgressSpinnerModule],
  template: `
    <div class="flex flex-col h-full bg-white dark:bg-slate-950">
      
      <!-- Chat Header -->
      <div class="p-6 pb-2">
        <h2 class="text-2xl font-black text-slate-800 dark:text-white tracking-tight italic uppercase">Mensajería</h2>
        <p class="text-xs text-slate-500 dark:text-slate-400">Conversaciones con analistas y clientes</p>
      </div>

      <!-- Search / Filters (Placeholder) -->
      <div class="px-6 py-4">
        <div class="relative">
          <mat-icon class="absolute left-3 top-1/2 -translate-y-1/2 !text-slate-400">search</mat-icon>
          <input type="text" placeholder="Buscar por PDV o Cliente..." 
                 class="w-full bg-slate-50 dark:bg-slate-900 border border-slate-100 dark:border-white/5 rounded-2xl pl-10 pr-4 py-2.5 text-xs font-bold outline-none focus:ring-2 focus:ring-primary-500 transition-all">
        </div>
      </div>

      <!-- Inbox List -->
      <div class="flex-grow overflow-y-auto px-4 pb-10">
        @if (loading()) {
          <div class="py-20 flex flex-col items-center gap-3">
            <mat-spinner diameter="32"></mat-spinner>
            <span class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Sincronizando mensajes...</span>
          </div>
        } @else if (conversations().length === 0) {
          <div class="py-20 text-center flex flex-col items-center gap-4 opacity-40 grayscale">
            <div class="w-20 h-20 rounded-full bg-slate-100 dark:bg-white/5 flex items-center justify-center">
              <mat-icon class="!text-4xl text-slate-400">chat_bubble_outline</mat-icon>
            </div>
            <div class="space-y-1">
              <p class="font-bold text-slate-600 dark:text-slate-400">Sin conversaciones activas</p>
              <p class="text-[10px] uppercase tracking-widest text-slate-400">Inicia una visita para chatear</p>
            </div>
          </div>
        } @else {
          <div class="space-y-2">
            @for (c of conversations(); track c.id_visita) {
              <div (click)="openChat(c)" class="group flex items-center gap-4 p-4 rounded-3xl hover:bg-slate-50 dark:hover:bg-white/5 transition-all cursor-pointer active:scale-95 border border-transparent hover:border-slate-100 dark:hover:border-white/5">
                <!-- Avatar / Icon -->
                <div class="relative">
                  <div class="w-14 h-14 rounded-[1.25rem] bg-gradient-to-br from-primary-500 to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-primary-500/20">
                    <mat-icon class="!text-2xl">chat</mat-icon>
                  </div>
                  @if (c.no_leidos > 0) {
                    <div class="absolute -top-1 -right-1 w-6 h-6 bg-rose-500 text-white rounded-full border-4 border-white dark:border-slate-950 flex items-center justify-center text-[9px] font-black">
                      {{ c.no_leidos }}
                    </div>
                  }
                </div>

                <!-- Content -->
                <div class="flex-grow min-w-0">
                  <div class="flex items-center justify-between mb-0.5">
                    <h4 class="font-bold text-slate-800 dark:text-white truncate tracking-tight">{{ c.pdv_nombre }}</h4>
                    <span class="text-[9px] font-bold text-slate-400">{{ c.ultimo_at | date:'HH:mm' }}</span>
                  </div>
                  <div class="flex flex-col">
                    <span class="text-[9px] font-black text-primary-500 uppercase tracking-widest mb-0.5">{{ c.cliente }}</span>
                    <p class="text-xs text-slate-500 dark:text-slate-400 line-clamp-1 italic">{{ c.ultimo_msg || 'Sin mensajes aún' }}</p>
                  </div>
                </div>

                <!-- Indicator -->
                <mat-icon class="text-slate-200 group-hover:text-primary-500 transition-colors !text-lg">chevron_right</mat-icon>
              </div>
            }
          </div>
        }
      </div>
    </div>
  `,
  styles: [`:host { display: block; height: 100%; }`]
})
export class MercChatComponent implements OnInit {
  private socket = inject(MercSocketService);
  private ui = inject(MercUiService);
  
  loading = signal(true);
  conversations = signal<any[]>([]);

  ngOnInit(): void {
    this.loadInbox();
  }

  loadInbox(): void {
    this.loading.set(true);
    this.socket.getInbox().subscribe({
      next: (res) => {
        this.conversations.set(res);
        this.loading.set(false);
      },
      error: () => this.loading.set(false)
    });
  }

  openChat(c: any): void {
    this.ui.openVisit({
      id_visita: c.id_visita,
      pdv_nombre: c.pdv_nombre,
      id_cliente: c.id_cliente,
      cliente: c.cliente
    });
  }
}
