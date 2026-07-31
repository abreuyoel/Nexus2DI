import { Component, Input, signal, inject, OnInit, OnDestroy, ElementRef, ViewChild, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTabsModule } from '@angular/material/tabs';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Subscription } from 'rxjs';
import { ApiService } from '../../../../core/services/api.service';
import { OfflineQueueService } from '../../services/offline-queue.service';
import { MercUiService, ActiveVisit } from '../../services/merc-ui.service';
import { PhotoGridComponent } from './components/photo-grid/photo-grid.component';
import { BalanceFormComponent } from './components/balance-form/balance-form.component';
import { MercSocketService, ChatMessage } from '../../services/merc-socket.service';

@Component({
  selector: 'app-merc-visit-panel',
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule, MatButtonModule, MatTabsModule, MatSnackBarModule, MatProgressSpinnerModule, PhotoGridComponent, BalanceFormComponent],
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

        <div class="flex items-center gap-2">
          @if (visit?.chainId) {
            <span class="text-[9px] font-black uppercase tracking-widest text-amber-500 bg-amber-500/10 px-2 py-1 rounded-full">Sin conexión</span>
          } @else {
            <div class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
            <span class="text-[10px] font-black uppercase tracking-widest text-emerald-500">Activa</span>
          }
        </div>
      </div>

      <!-- Content (Scrollable) -->
      <div class="flex-grow overflow-y-auto">
        <mat-tab-group mat-stretch-tabs="false" mat-align-tabs="start" class="merc-visit-tabs">

          <!-- FOTOS -->
          <mat-tab>
            <ng-template mat-tab-label>
              <div class="flex items-center gap-2">
                <mat-icon class="!text-sm">photo_camera</mat-icon>
                <span class="text-[10px] font-black uppercase tracking-widest">Fotos</span>
              </div>
            </ng-template>
            <div class="p-4">
              <app-photo-grid [visitaId]="visit?.id_visita!" [chainId]="visit?.chainId ?? null"></app-photo-grid>
            </div>
          </mat-tab>

          <!-- DATA (Balances) -->
          <mat-tab>
            <ng-template mat-tab-label>
              <div class="flex items-center gap-2">
                <mat-icon class="!text-sm">inventory_2</mat-icon>
                <span class="text-[10px] font-black uppercase tracking-widest">Data</span>
              </div>
            </ng-template>
            <div class="p-4">
              <app-balance-form [visitaId]="visit?.id_visita!" [idCliente]="visit?.id_cliente!" [chainId]="visit?.chainId ?? null"></app-balance-form>
            </div>
          </mat-tab>

          <!-- CHAT -->
          <mat-tab>
            <ng-template mat-tab-label>
              <div class="flex items-center gap-2">
                <mat-icon class="!text-sm">chat</mat-icon>
                <span class="text-[10px] font-black uppercase tracking-widest">Chat</span>
              </div>
            </ng-template>
            @if (visit?.chainId) {
              <div class="h-[60vh] flex flex-col items-center justify-center opacity-40 gap-4 px-8 text-center">
                <mat-icon class="!text-5xl">cloud_off</mat-icon>
                <p class="font-bold text-sm">El chat va a estar disponible cuando esta visita se sincronice (está guardada sin conexión).</p>
              </div>
            } @else {
              <div class="h-[60vh] flex flex-col">
                <div #msgList class="flex-grow overflow-y-auto p-4 space-y-3">
                  @if (chatLoading()) {
                    <div class="flex justify-center py-8"><mat-spinner diameter="28"></mat-spinner></div>
                  } @else if (messages().length === 0) {
                    <div class="h-full flex flex-col items-center justify-center opacity-30 gap-3">
                      <mat-icon class="!text-4xl">chat_bubble_outline</mat-icon>
                      <p class="text-xs font-bold">Sin mensajes todavía</p>
                    </div>
                  } @else {
                    @for (m of messages(); track m.id_mensaje) {
                      <div class="bg-slate-50 dark:bg-slate-900 rounded-2xl p-3 max-w-[85%]">
                        <div class="flex items-center gap-2 mb-1">
                          <span class="text-[10px] font-black text-primary-500 uppercase tracking-widest">{{ m.sender_nombre }}</span>
                          @if (m.created_at) { <span class="text-[9px] text-slate-400">{{ m.created_at | date:'short' }}</span> }
                        </div>
                        <p class="text-sm text-slate-700 dark:text-slate-200 break-words">{{ m.mensaje }}</p>
                      </div>
                    }
                  }
                </div>
                <div class="p-3 border-t border-slate-100 dark:border-white/5 flex items-center gap-2 shrink-0">
                  <input [(ngModel)]="newMessage" (keyup.enter)="enviarMensaje()" placeholder="Escribí un mensaje..."
                    class="flex-1 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-2xl px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-primary-500">
                  <button (click)="enviarMensaje()" [disabled]="!newMessage.trim() || sendingMsg()"
                    class="w-11 h-11 shrink-0 rounded-2xl bg-primary-600 hover:bg-primary-500 disabled:opacity-40 text-white flex items-center justify-center transition-all active:scale-95">
                    @if (sendingMsg()) { <mat-spinner diameter="18" color="accent"></mat-spinner> }
                    @else { <mat-icon>send</mat-icon> }
                  </button>
                </div>
              </div>
            }
          </mat-tab>

        </mat-tab-group>
      </div>

      <!-- Footer: ID + Finalizar Visita -->
      <div class="p-4 bg-slate-50 dark:bg-slate-900/50 border-t border-slate-100 dark:border-white/5 space-y-3 shrink-0">
         <p class="text-[9px] font-black text-slate-400 uppercase tracking-widest text-center">ID Visita: {{ visit?.id_visita }}</p>
         <button (click)="finalizar()" [disabled]="finalizando()"
                 class="w-full py-3.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-2xl font-black uppercase tracking-widest text-xs active:scale-95 transition-all flex items-center justify-center gap-2">
           @if (finalizando()) { <mat-spinner diameter="16" color="accent"></mat-spinner> }
           @else { <mat-icon class="!text-base">check_circle</mat-icon> }
           Finalizar Visita
         </button>
      </div>
    </div>
  `,
  styles: [`
    :host { display: block; }
    .merc-visit-tabs ::ng-deep {
      .mat-mdc-tab-header { background: white; .dark & { background: #0f172a; } }
      .mat-mdc-tab { height: 48px; min-width: 0; padding: 0 16px; }
    }
  `]
})
export class MercVisitPanelComponent implements OnInit, OnDestroy, AfterViewChecked {
  @Input() visit: ActiveVisit | null = null;
  @ViewChild('msgList') msgListEl?: ElementRef<HTMLDivElement>;

  private api = inject(ApiService);
  private offline = inject(OfflineQueueService);
  private ui = inject(MercUiService);
  private socket = inject(MercSocketService);
  private snack = inject(MatSnackBar);

  finalizando = signal(false);
  messages = signal<ChatMessage[]>([]);
  chatLoading = signal(false);
  newMessage = '';
  sendingMsg = signal(false);
  private chatSub?: Subscription;
  private lastMsgCount = 0;

  ngOnInit() {
    // El chat necesita un id_visita real del servidor -- si la visita se
    // activó offline y todavía no sincronizó (chainId), no hay nada que
    // consultar todavía (ver el bloque @if(visit?.chainId) del template).
    if (this.visit && !this.visit.chainId) {
      this.chatLoading.set(true);
      this.chatSub = this.socket.joinChat(this.visit.id_visita as number).subscribe({
        next: (msgs) => { this.messages.set(msgs); this.chatLoading.set(false); },
        error: () => this.chatLoading.set(false),
      });
    }
  }

  ngOnDestroy() {
    this.socket.leaveChat();
    this.chatSub?.unsubscribe();
  }

  ngAfterViewChecked() {
    if (this.messages().length !== this.lastMsgCount && this.msgListEl) {
      this.lastMsgCount = this.messages().length;
      const el = this.msgListEl.nativeElement;
      el.scrollTop = el.scrollHeight;
    }
  }

  enviarMensaje() {
    const texto = this.newMessage.trim();
    if (!texto || !this.visit || this.visit.chainId) return;
    this.sendingMsg.set(true);
    this.newMessage = '';
    // Eco optimista: el polling (cada 8s) recién va a traer este mensaje del
    // servidor en la próxima vuelta -- sin esto, el mercaderista lo ve
    // desaparecer y reaparecer varios segundos después.
    this.messages.update(list => [...list, {
      id_visita: this.visit!.id_visita as number, sender_nombre: 'Vos', mensaje: texto,
      created_at: new Date().toISOString(),
    }]);
    this.socket.sendMessage(this.visit.id_visita as number, texto, this.visit.cliente || '').subscribe({
      next: () => this.sendingMsg.set(false),
      error: () => { this.sendingMsg.set(false); this.snack.open('No se pudo enviar el mensaje', 'OK', { duration: 3000 }); },
    });
  }

  close() {
    this.ui.closeVisit();
  }

  async finalizar() {
    if (!this.visit || !confirm('¿Finalizar esta visita? No vas a poder cargar más fotos ni data después.')) return;
    this.finalizando.set(true);

    if (this.visit.chainId) {
      // Offline: encolar como paso de la cadena, con el placeholder -- se
      // resuelve al id real igual que el resto de los pasos.
      await this.offline.addChainStep(this.visit.chainId, {
        kind: 'finalizar', url: '/api/merc/finalizar-visita', isMultipart: false,
        jsonBody: { id_visita: this.visit.id_visita },
      });
      this.finalizando.set(false);
      this.snack.open('Visita finalizada localmente — se sincronizará al reconectar', 'OK', { duration: 3000 });
      this.ui.closeVisit();
      return;
    }

    this.api.finalizarMercVisita(this.visit.id_visita as number).subscribe({
      next: () => {
        this.finalizando.set(false);
        this.snack.open('Visita finalizada', 'OK', { duration: 2500 });
        this.ui.closeVisit();
      },
      error: () => {
        this.finalizando.set(false);
        this.snack.open('No se pudo finalizar la visita', 'OK', { duration: 3000 });
      },
    });
  }
}
