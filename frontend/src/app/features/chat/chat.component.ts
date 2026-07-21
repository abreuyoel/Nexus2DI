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
import { GroupMembersDialogComponent } from './group-members-dialog.component';
import { PhotoLightboxComponent, LightboxPhoto } from '../../shared/photo-lightbox/photo-lightbox.component';
import { AuthImgDirective } from '../../shared/directives/auth-img.directive';

type TipoGrupo = 'operativo' | 'operativo_cliente';

interface LecturaEvent {
  tipo: 'lectura';
  conversacion_id?: number;
  visita_id?: number;
  id_grupo?: number;
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

interface Grupo {
  id_grupo: number;
  id_cliente: number;
  tipo_grupo: TipoGrupo;
  nombre?: string;
  no_leidos: number;
  ultimo_mensaje?: string;
  ultimo_mensaje_fecha?: string;
}

interface VisitaConChat {
  id_visita: number;
  fecha_visita?: string;
  mercaderista?: string;
  punto?: string;
  estado?: string;
  ultimo_mensaje?: string;
  fecha_ultimo?: string;
}

interface GrupoVisitaKey { id_cliente: number; tipo_grupo: TipoGrupo; id_visita: number; }

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [
    CommonModule, ReactiveFormsModule, FormsModule,
    MatCardModule, MatFormFieldModule, MatInputModule, MatButtonModule, MatIconModule,
    MatListModule, MatProgressSpinnerModule, MatDialogModule, MatMenuModule,
    PhotoLightboxComponent, AuthImgDirective,
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

  // Chat activo: visita (legacy) / conversación ad-hoc (region/pdv) /
  // grupo (equipo operativo, chat general) / grupo_visita (su sub-hilo)
  activeKind = signal<'visit' | 'conversation' | 'grupo' | 'grupo_visita' | null>(null);
  activeId = signal<number | null>(null);
  activeGrupoVisita = signal<GrupoVisitaKey | null>(null);
  activeTitle = signal<string>('');

  // Pestañas: Cliente (chats de visita + grupos "Equipo + Cliente") vs
  // Equipo Operativo (SOLO grupos 'operativo' puros, sin cliente + ad-hoc).
  // Los grupos 'operativo_cliente' incluyen usuarios del cliente -- por eso
  // viven en la pestaña Cliente, no en Equipo Operativo.
  activeChatTab = signal<'cliente' | 'equipo'>('cliente');
  gruposOperativo = computed(() => this.grupos().filter(g => g.tipo_grupo === 'operativo'));
  gruposCliente = computed(() => this.grupos().filter(g => g.tipo_grupo === 'operativo_cliente'));
  clienteCount = computed(() => this.inbox().filter(i => i.kind === 'visit').length + this.gruposCliente().length);
  adHocConversations = computed(() => this.inbox().filter(i => i.kind === 'conversation'));
  equipoCount = computed(() => this.gruposOperativo().length + this.adHocConversations().length);
  visibleInbox = computed(() => this.inbox().filter(i => i.kind === 'visit'));

  // Grupos de equipo operativo (mis-grupos) + sus visitas con sub-hilo
  grupos = signal<Grupo[]>([]);
  expandedGrupoId = signal<number | null>(null);
  visitasPorGrupo = signal<Record<number, VisitaConChat[]>>({});
  loadingVisitasGrupo = signal<number | null>(null);
  // Visitas Revisadas quedan colapsadas aparte, para no saturar la lista de
  // pendientes -- el chat de la visita se sigue viendo, solo que no está a
  // la vista por defecto una vez que el analista la marcó Revisada.
  expandedArchivadasGrupoId = signal<number | null>(null);

  setChatTab(tab: 'cliente' | 'equipo'): void {
    this.activeChatTab.set(tab);
    if (tab === 'equipo' && this.grupos().length === 0) this.loadGrupos();
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
    public auth: AuthService,
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
      this.loadGrupos();
    }

    this.route.queryParams.subscribe(params => {
      const visitaId = params['visita'] ? parseInt(params['visita'], 10) : null;
      if (visitaId) {
        this.selectChat('visit', visitaId);
        return;
      }
      const idCliente = params['grupo_cliente'] ? parseInt(params['grupo_cliente'], 10) : null;
      const tipoGrupo = params['tipo_grupo'] as TipoGrupo | undefined;
      const idVisitaGrupo = params['grupo_visita'] ? parseInt(params['grupo_visita'], 10) : null;
      if (idCliente && tipoGrupo && idVisitaGrupo) {
        this.activeChatTab.set('equipo');
        this.selectGrupoVisitaByKey({ id_cliente: idCliente, tipo_grupo: tipoGrupo, id_visita: idVisitaGrupo },
          params['titulo'] || undefined);
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
    this.loadGrupos();
  }

  changeExclusiveClient(): void {
    this.selectedExclusiveClient.set(null);
    this.inbox.set([]);
    this.grupos.set([]);
    this.activeKind.set(null);
    this.activeId.set(null);
    this.activeGrupoVisita.set(null);
    this.wsSubscription?.unsubscribe();
    this.ws.disconnectAll();
  }

  // ─── INBOX (tab Cliente) ──────────────────────────────────────────
  loadInbox(): void {
    const clienteId = this.selectedExclusiveClient()?.id_cliente;
    this.api.getChatInbox(clienteId).subscribe({
      next: (data) => this.inbox.set(data),
    });
  }

  // ─── GRUPOS DE EQUIPO OPERATIVO (tab Equipo) ──────────────────────
  loadGrupos(): void {
    this.api.getMisGrupos().subscribe({
      next: (data) => this.grupos.set(data),
    });
  }

  toggleGrupoVisitas(g: Grupo, ev: Event): void {
    ev.stopPropagation();
    if (this.expandedGrupoId() === g.id_grupo) {
      this.expandedGrupoId.set(null);
      return;
    }
    this.expandedGrupoId.set(g.id_grupo);
    if (!this.visitasPorGrupo()[g.id_grupo]) {
      this.loadingVisitasGrupo.set(g.id_grupo);
      this.api.getVisitasConChat(g.id_cliente, g.tipo_grupo).subscribe({
        next: (visitas) => {
          this.visitasPorGrupo.update(m => ({ ...m, [g.id_grupo]: visitas }));
          this.loadingVisitasGrupo.set(null);
        },
        error: () => this.loadingVisitasGrupo.set(null),
      });
    }
  }

  visitasDe(g: Grupo): VisitaConChat[] {
    return this.visitasPorGrupo()[g.id_grupo] || [];
  }

  visitasActivasDe(g: Grupo): VisitaConChat[] {
    return this.visitasDe(g).filter(v => v.estado !== 'Revisado');
  }

  visitasArchivadasDe(g: Grupo): VisitaConChat[] {
    return this.visitasDe(g).filter(v => v.estado === 'Revisado');
  }

  toggleArchivadas(g: Grupo, ev: Event): void {
    ev.stopPropagation();
    this.expandedArchivadasGrupoId.set(this.expandedArchivadasGrupoId() === g.id_grupo ? null : g.id_grupo);
  }

  get activeList(): InboxItem[] | any[] {
    return this.searchControl.value ? this.searchResults() : this.visibleInbox();
  }

  isItemActive(item: InboxItem): boolean {
    if (item.kind === 'visit') return this.activeKind() === 'visit' && this.activeId() === item.visita_id;
    if (item.kind === 'conversation') return this.activeKind() === 'conversation' && this.activeId() === item.conversacion_id;
    return false;
  }

  isGrupoActive(g: Grupo): boolean {
    return this.activeKind() === 'grupo' && this.activeId() === g.id_grupo;
  }

  isGrupoVisitaActive(g: Grupo, v: VisitaConChat): boolean {
    const gv = this.activeGrupoVisita();
    return this.activeKind() === 'grupo_visita' && !!gv
      && gv.id_cliente === g.id_cliente && gv.tipo_grupo === g.tipo_grupo && gv.id_visita === v.id_visita;
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

  private resetActiveChat(): void {
    this.wsSubscription?.unsubscribe();
    this.ws.disconnectAll();
    this.messages.set([]);
    this.connected.set(false);
    if (this.searchControl.value) {
      this.searchControl.setValue('', { emitEvent: false });
      this.searchResults.set([]);
      this.loadInbox();
    }
  }

  selectChat(kind: 'visit' | 'conversation', id: number, title?: string): void {
    if (this.activeKind() === kind && this.activeId() === id) return;

    this.activeKind.set(kind);
    this.activeId.set(id);
    this.activeGrupoVisita.set(null);
    this.activeTitle.set(title || (kind === 'visit' ? `Visita #${id}` : `Chat #${id}`));
    this.resetActiveChat();

    const history$ = kind === 'visit'
      ? this.api.getMessagesByVisit(id)
      : this.api.getConversationMessages(id);

    history$.subscribe({
      next: history => {
        this.messages.set(history);
        setTimeout(() => this.scrollToBottom(), 50);
      }
    });

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

  // ─── CHAT DE GRUPO (equipo operativo) ─────────────────────────────
  private mapGrupoMensaje(m: any): ChatMensaje {
    return {
      id: m.id_mensaje,
      sender_id: m.id_usuario,
      sender_nombre: m.username,
      sender_type: m.tipo_mensaje === 'sistema' ? 'sistema' : 'usuario',
      mensaje: m.mensaje,
      leido: true,
      created_at: m.fecha_envio,
      foto_adjunta: m.foto_adjunta,
      leido_por: m.leido_por || [],
    };
  }

  selectGrupo(g: Grupo): void {
    if (this.activeKind() === 'grupo' && this.activeId() === g.id_grupo) return;

    this.activeKind.set('grupo');
    this.activeId.set(g.id_grupo);
    this.activeGrupoVisita.set(null);
    this.activeTitle.set(g.nombre || (g.tipo_grupo === 'operativo' ? 'Equipo operativo' : 'Equipo + Cliente'));
    this.resetActiveChat();

    this.api.getMensajesGrupo(g.id_grupo).subscribe({
      next: history => {
        this.messages.set(history.map(h => this.mapGrupoMensaje(h)));
        setTimeout(() => this.scrollToBottom(), 50);
      }
    });
    this.api.marcarLeidoGrupo(g.id_grupo).subscribe({ next: () => this.loadGrupos() });

    this.wsSubscription = this.ws.connectToChatGrupos(`grupo_${g.id_grupo}`).subscribe({
      next: (msg) => {
        if (msg?.tipo === 'lectura') {
          this.applyReadReceipt(msg);
          return;
        }
        this.messages.update((ms) => [...ms, this.mapGrupoMensaje(msg)]);
        this.connected.set(true);
        setTimeout(() => this.scrollToBottom(), 50);
        this.loadGrupos();
      },
      error: () => this.connected.set(false),
    });
  }

  private selectGrupoVisitaByKey(key: GrupoVisitaKey, title?: string): void {
    const g: Grupo = this.grupos().find(x => x.id_cliente === key.id_cliente && x.tipo_grupo === key.tipo_grupo)
      || { id_grupo: 0, id_cliente: key.id_cliente, tipo_grupo: key.tipo_grupo, no_leidos: 0 };
    const v: VisitaConChat = { id_visita: key.id_visita, punto: title };
    this.selectGrupoVisita(g, v);
  }

  selectGrupoVisita(g: Grupo, v: VisitaConChat): void {
    const key: GrupoVisitaKey = { id_cliente: g.id_cliente, tipo_grupo: g.tipo_grupo, id_visita: v.id_visita };
    if (this.isGrupoVisitaActive(g, v)) return;

    this.activeKind.set('grupo_visita');
    this.activeId.set(null);
    this.activeGrupoVisita.set(key);
    this.activeTitle.set(v.punto || `Visita #${v.id_visita}`);
    this.resetActiveChat();

    this.api.getMensajesGrupoVisita(key.id_cliente, key.tipo_grupo, key.id_visita).subscribe({
      next: history => {
        this.messages.set(history.map(h => this.mapGrupoMensaje(h)));
        setTimeout(() => this.scrollToBottom(), 50);
      }
    });
    this.api.marcarLeidoGrupoVisita(key.id_cliente, key.tipo_grupo, key.id_visita).subscribe();

    const room = `grupo_visita_${key.id_cliente}_${key.tipo_grupo}_${key.id_visita}`;
    this.wsSubscription = this.ws.connectToChatGrupos(room).subscribe({
      next: (msg) => {
        if (msg?.tipo === 'lectura') {
          this.applyReadReceipt(msg);
          return;
        }
        this.messages.update((ms) => [...ms, this.mapGrupoMensaje(msg)]);
        this.connected.set(true);
        setTimeout(() => this.scrollToBottom(), 50);
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

  // ─── LIGHTBOX de fotos adjuntas (antes abría en pestaña nueva) ────
  lightboxOpen = signal(false);
  lightboxPhotos = signal<LightboxPhoto[]>([]);

  openFotoLightbox(url?: string): void {
    if (!url) return;
    this.lightboxPhotos.set([{ url }]);
    this.lightboxOpen.set(true);
  }

  sendMessage(): void {
    const text = this.messageControl.value?.trim();
    if (!text) return;

    const kind = this.activeKind();
    const user = this.auth.currentUser();

    if (kind === 'visit' || kind === 'conversation') {
      const id = this.activeId();
      if (id === null) return;
      if (kind === 'visit') {
        this.ws.sendToChat(id.toString(), {
          visita_id: id,
          mensaje: text,
          sender_type: user?.is_client ? 'cliente' : 'usuario',
          sender_id: user?.id,
          sender_nombre: user?.username,
        });
      } else {
        this.ws.sendToChat(`conv_${id}`, {
          conversacion_id: id,
          mensaje: text,
          sender_type: user?.is_client ? 'cliente' : 'usuario',
          sender_id: user?.id,
          sender_nombre: user?.username,
        });
      }
    } else if (kind === 'grupo') {
      const id = this.activeId();
      if (id === null) return;
      this.api.enviarMensajeGrupo(id, text).subscribe();
    } else if (kind === 'grupo_visita') {
      const gv = this.activeGrupoVisita();
      if (!gv) return;
      this.api.enviarMensajeGrupoVisita(gv.id_cliente, gv.tipo_grupo, gv.id_visita, text).subscribe();
    } else {
      return;
    }
    this.messageControl.reset();
  }

  // ─── NUEVO CHAT (grupos ad-hoc de mercaderistas: region/pdv) ──────
  openNewChatDialog(): void {
    const clienteId = this.selectedExclusiveClient()?.id_cliente;
    const ref = this.dialog.open(NewChatDialogComponent, {
      data: { clienteId },
      autoFocus: false,
      panelClass: 'nc-dialog-panel',
    });
    ref.afterClosed().subscribe(conv => {
      if (conv?.id) {
        this.activeChatTab.set('equipo');
        this.loadInbox();
        this.selectChat('conversation', conv.id, conv.titulo);
      }
    });
  }

  // ─── MIEMBROS DEL GRUPO ──────────────────────────────────────────
  openMembersDialog(): void {
    const idGrupo = this.activeId();
    if (this.activeKind() !== 'grupo' || idGrupo === null) return;
    this.dialog.open(GroupMembersDialogComponent, {
      data: { idGrupo },
      width: '400px',
      autoFocus: false,
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

  // Helpers de UI (conversaciones ad-hoc region/pdv del tab Equipo)
  iconForItem(item: InboxItem): string {
    if (item.kind === 'visit') return 'store';
    switch (item.tipo) {
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
    const map: Record<string, string> = { group_region: 'Región', group_pdv: 'PDV' };
    return map[item.tipo || ''] || 'Chat';
  }

  nombreGrupo(g: Grupo): string {
    return g.nombre || (g.tipo_grupo === 'operativo' ? 'Equipo operativo' : 'Equipo + Cliente');
  }

  // Helpers del header del chat activo (varían según activeKind)
  activeIcon(): string {
    switch (this.activeKind()) {
      case 'visit': return 'store';
      case 'grupo': return 'groups';
      case 'grupo_visita': return 'store';
      default: return 'forum';
    }
  }

  activeSubtitle(): string {
    const kind = this.activeKind();
    if (kind === 'visit') return `Visita #${this.activeId()}`;
    if (kind === 'grupo_visita') {
      const gv = this.activeGrupoVisita();
      return gv ? `Visita #${gv.id_visita} · ${gv.tipo_grupo === 'operativo_cliente' ? 'Equipo+Cliente' : 'Solo equipo'}` : '';
    }
    if (kind === 'grupo') return 'Chat general';
    return `Chat #${this.activeId()}`;
  }
}
