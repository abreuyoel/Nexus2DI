import { Component, OnInit, OnDestroy, signal, computed, ViewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormControl, FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatMenuModule } from '@angular/material/menu';
import { ActivatedRoute } from '@angular/router';
import { Subscription } from 'rxjs';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';
import { ApiService } from '../../core/services/api.service';
import { WebSocketService } from '../../core/services/websocket.service';
import { AuthService } from '../../core/services/auth.service';
import { ChatMensaje, ChatMensajeLector } from '../../core/models/visita.model';
import { NewChatDialogComponent } from './new-chat-dialog.component';

interface LecturaEvent {
  tipo: 'lectura';
  conversacion_id?: number;
  visita_id?: number;
  id_usuario: number;
  username?: string;
  mensajes_ids: number[];
  fecha_lectura?: string;
}

interface ExclusiveClient { id_cliente: number; cliente: string; id_tipo_cliente: number; }
interface InboxItem {
  kind: 'visit' | 'conversation';
  visita_id?: number;
  punto_nombre?: string;
  punto_id?: string;
  fecha_visita?: string;
  conversacion_id?: number;
  tipo?: string;
  titulo?: string;
  last_message?: string;
  last_message_date?: string;
  unread_count?: number;
}

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [
    CommonModule, ReactiveFormsModule, FormsModule,
    MatCardModule, MatFormFieldModule, MatInputModule, MatButtonModule, MatIconModule,
    MatListModule, MatProgressSpinnerModule, MatDialogModule, MatMenuModule,
  ],
  templateUrl: './chat.component.html',
  styleUrls: ['./chat.component.scss']
})
export class ChatComponent implements OnInit, OnDestroy {
  inbox = signal<InboxItem[]>([]);
  searchResults = signal<any[]>([]);
  messages = signal<ChatMensaje[]>([]);
  connected = signal(false);
  isSearching = signal(false);

  messageControl = new FormControl('');
  searchControl = new FormControl('');

  currentUserId = signal<number | null>(null);

  // Active chat: visita o conversación
  activeKind = signal<'visit' | 'conversation' | null>(null);
  activeId = signal<number | null>(null);
  activeTitle = signal<string>('');

  // Pestañas: Cliente (chats de visita) vs Equipo Operativo (conversaciones internas)
  activeChatTab = signal<'cliente' | 'equipo'>('cliente');
  clienteCount = computed(() => this.inbox().filter(i => i.kind === 'visit').length);
  equipoCount = computed(() => this.inbox().filter(i => i.kind === 'conversation').length);
  visibleInbox = computed(() => {
    const want = this.activeChatTab() === 'cliente' ? 'visit' : 'conversation';
    return this.inbox().filter(i => i.kind === want);
  });

  setChatTab(tab: 'cliente' | 'equipo'): void {
    this.activeChatTab.set(tab);
  }

  // Coordinador exclusivo
  isCoordinadorExclusivo = signal(false);
  exclusiveClients = signal<ExclusiveClient[]>([]);
  selectedExclusiveClient = signal<ExclusiveClient | null>(null);
  exclusiveClientSearch = signal('');
  filteredExclusiveClients = computed(() => {
    const term = this.exclusiveClientSearch().trim().toLowerCase();
    if (!term) return this.exclusiveClients();
    return this.exclusiveClients().filter(c => (c.cliente || '').toLowerCase().includes(term));
  });

  @ViewChild('scrollContainer') private scrollContainer!: ElementRef;

  private wsSubscription?: Subscription;
  private searchSubscription?: Subscription;

  constructor(
    private api: ApiService,
    private ws: WebSocketService,
    private auth: AuthService,
    private route: ActivatedRoute,
    private dialog: MatDialog,
  ) {
    this.currentUserId.set(this.auth.currentUser()?.id ?? null);
  }

  ngOnInit(): void {
    const u = this.auth.currentUser();
    if (u?.is_coordinador_exclusivo) {
      this.isCoordinadorExclusivo.set(true);
      this.loadExclusiveClients();
    } else {
      this.loadInbox();
    }

    this.route.queryParams.subscribe(params => {
      const visitaId = params['visita'] ? parseInt(params['visita'], 10) : null;
      if (visitaId) {
        this.selectChat('visit', visitaId);
        return;
      }
      const convId = params['conversacion'] ? parseInt(params['conversacion'], 10) : null;
      if (convId) {
        this.activeChatTab.set('equipo');
        this.selectChat('conversation', convId, params['titulo'] || undefined);
      }
    });

    this.searchSubscription = this.searchControl.valueChanges.pipe(
      debounceTime(300),
      distinctUntilChanged()
    ).subscribe(query => {
      if (query && query.trim().length >= 2) {
        this.isSearching.set(true);
        this.api.searchChatVisits(query.trim()).subscribe({
          next: (results) => {
            this.searchResults.set(results);
            this.isSearching.set(false);
          },
          error: () => this.isSearching.set(false)
        });
      } else {
        this.searchResults.set([]);
      }
    });
  }

  // ─── COORDINADOR EXCLUSIVO ───────────────────────────────────────
  loadExclusiveClients(): void {
    this.api.getExclusiveClients().subscribe({
      next: data => this.exclusiveClients.set(data),
    });
  }

  selectExclusiveClient(c: ExclusiveClient): void {
    this.selectedExclusiveClient.set(c);
    this.loadInbox();
  }

  changeExclusiveClient(): void {
    this.selectedExclusiveClient.set(null);
    this.inbox.set([]);
    this.activeKind.set(null);
    this.activeId.set(null);
    this.wsSubscription?.unsubscribe();
    this.ws.disconnectAll();
  }

  // ─── INBOX ────────────────────────────────────────────────────────
  loadInbox(): void {
    const clienteId = this.selectedExclusiveClient()?.id_cliente;
    this.api.getChatInbox(clienteId).subscribe({
      next: (data) => this.inbox.set(data),
    });
  }

  get activeList(): InboxItem[] | any[] {
    return this.searchControl.value ? this.searchResults() : this.inbox();
  }

  isItemActive(item: InboxItem): boolean {
    if (item.kind === 'visit') return this.activeKind() === 'visit' && this.activeId() === item.visita_id;
    if (item.kind === 'conversation') return this.activeKind() === 'conversation' && this.activeId() === item.conversacion_id;
    return false;
  }

  selectInboxItem(item: InboxItem): void {
    if (item.kind === 'visit' && item.visita_id) {
      this.selectChat('visit', item.visita_id, item.punto_nombre);
    } else if (item.kind === 'conversation' && item.conversacion_id) {
      this.selectChat('conversation', item.conversacion_id, item.titulo);
    }
  }

  // Visita seleccionada desde search results (mantenemos compat)
  selectVisitFromSearch(visitaId: number, puntoNombre?: string): void {
    this.selectChat('visit', visitaId, puntoNombre);
  }

  selectChat(kind: 'visit' | 'conversation', id: number, title?: string): void {
    if (this.activeKind() === kind && this.activeId() === id) return;

    this.activeKind.set(kind);
    this.activeId.set(id);
    this.activeTitle.set(title || (kind === 'visit' ? `Visita #${id}` : `Chat #${id}`));

    // Limpiar búsqueda si estaba activa
    if (this.searchControl.value) {
      this.searchControl.setValue('', { emitEvent: false });
      this.searchResults.set([]);
      this.loadInbox();
    }

    this.wsSubscription?.unsubscribe();
    this.ws.disconnectAll();
    this.messages.set([]);

    // Cargar historial
    const history$ = kind === 'visit'
      ? this.api.getMessagesByVisit(id)
      : this.api.getConversationMessages(id);

    history$.subscribe({
      next: history => {
        this.messages.set(history);
        setTimeout(() => this.scrollToBottom(), 50);
      }
    });

    // Conectar WebSocket
    const room = kind === 'visit' ? id.toString() : `conv_${id}`;
    this.wsSubscription = this.ws.connectToChat(room).subscribe({
      next: (msg) => {
        if (msg?.tipo === 'lectura') {
          this.applyReadReceipt(msg);
          return;
        }
        this.messages.update((ms) => [...ms, msg]);
        this.connected.set(true);
        setTimeout(() => this.scrollToBottom(), 50);
        if (!this.searchControl.value) this.loadInbox();
      },
      error: () => this.connected.set(false),
    });
  }

  // ─── RECIBOS DE LECTURA (tick doble estilo WhatsApp) ──────────────
  private applyReadReceipt(evt: LecturaEvent): void {
    const ids = new Set(evt.mensajes_ids || []);
    if (ids.size === 0) return;
    this.messages.update((ms) => ms.map((m) => {
      if (!ids.has(m.id)) return m;
      const yaListado = (m.leido_por || []).some((l) => l.id_usuario === evt.id_usuario);
      if (yaListado) return m;
      const lector: ChatMensajeLector = {
        id_usuario: evt.id_usuario,
        username: evt.username,
        fecha_lectura: evt.fecha_lectura,
      };
      return { ...m, leido_por: [...(m.leido_por || []), lector] };
    }));
  }

  isOwnMessage(msg: ChatMensaje): boolean {
    return msg.sender_id === this.currentUserId();
  }

  readersOf(msg: ChatMensaje): ChatMensajeLector[] {
    return msg.leido_por || [];
  }

  isReadByOthers(msg: ChatMensaje): boolean {
    return this.readersOf(msg).length > 0;
  }

  sendMessage(): void {
    const text = this.messageControl.value?.trim();
    if (!text || this.activeId() === null) return;

    const user = this.auth.currentUser();
    const kind = this.activeKind();
    const id = this.activeId()!;

    if (kind === 'visit') {
      this.ws.sendToChat(id.toString(), {
        visita_id: id,
        mensaje: text,
        sender_type: user?.is_client ? 'cliente' : 'usuario',
        sender_id: user?.id,
        sender_nombre: user?.username,
      });
    } else if (kind === 'conversation') {
      this.ws.sendToChat(`conv_${id}`, {
        conversacion_id: id,
        mensaje: text,
        sender_type: user?.is_client ? 'cliente' : 'usuario',
        sender_id: user?.id,
        sender_nombre: user?.username,
      });
    }
    this.messageControl.reset();
  }

  // ─── NUEVO CHAT ───────────────────────────────────────────────────
  openNewChatDialog(): void {
    const clienteId = this.selectedExclusiveClient()?.id_cliente;
    const ref = this.dialog.open(NewChatDialogComponent, {
      data: { clienteId },
      autoFocus: false,
      panelClass: 'nc-dialog-panel',
    });
    ref.afterClosed().subscribe(conv => {
      if (conv?.id) {
        this.loadInbox();
        this.selectChat('conversation', conv.id, conv.titulo);
      }
    });
  }

  ngOnDestroy(): void {
    this.wsSubscription?.unsubscribe();
    this.searchSubscription?.unsubscribe();
    this.ws.disconnectAll();
  }

  private scrollToBottom(): void {
    try {
      this.scrollContainer.nativeElement.scrollTop = this.scrollContainer.nativeElement.scrollHeight;
    } catch {}
  }

  // Helpers de UI
  isVisitThread(item: InboxItem): boolean {
    return item.tipo === 'visit_team' || item.tipo === 'visit_team_client';
  }

  iconForItem(item: InboxItem): string {
    if (item.kind === 'visit') return 'store';
    if (this.isVisitThread(item)) return item.tipo === 'visit_team_client' ? 'diversity_3' : 'groups';
    switch (item.tipo) {
      case 'direct': return 'person';
      case 'group_team': return 'groups';
      case 'group_region': return 'map';
      case 'group_pdv': return 'storefront';
      default: return 'forum';
    }
  }

  labelForItem(item: InboxItem): string {
    if (item.kind === 'visit') return item.punto_nombre || 'Visita';
    return item.titulo || '(Sin título)';
  }

  sublabelForItem(item: InboxItem): string {
    if (item.kind === 'visit') return `V-${item.visita_id}`;
    if (this.isVisitThread(item)) {
      const suf = item.tipo === 'visit_team_client' ? 'Equipo+Cliente' : 'Solo equipo';
      return item.visita_id ? `V-${item.visita_id} · ${suf}` : suf;
    }
    const map: Record<string, string> = {
      direct: 'Directo', group_team: 'Equipo', group_region: 'Región', group_pdv: 'PDV',
    };
    return map[item.tipo || ''] || 'Chat';
  }
}
