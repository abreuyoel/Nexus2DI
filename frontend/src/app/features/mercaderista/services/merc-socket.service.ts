import { Injectable, OnDestroy, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Subject, Observable, interval, Subscription } from 'rxjs';
import { takeUntil, startWith, switchMap } from 'rxjs/operators';
import { BrowserNotificationService } from './browser-notification.service';
import { AuthService } from '../../../core/services/auth.service';

export interface ChatMessage {
  id_mensaje?: number;
  id_visita: number;
  sender_nombre: string;
  mensaje: string;
  created_at?: string;
  tipo_mensaje?: string;
  sender_id?: number;
}

export interface WsEvent {
  tipo: string;
  data: any;
}

type WsStatus = 'disconnected' | 'connecting' | 'connected';

@Injectable({ providedIn: 'root' })
export class MercSocketService implements OnDestroy {
  private http = inject(HttpClient);
  private notif = inject(BrowserNotificationService);
  private auth = inject(AuthService);

  // ── Observables ──────────────────────────────────────────────
  private _chatMessages$ = new Subject<ChatMessage>();
  chatMessages$ = this._chatMessages$.asObservable();

  private _event$ = new Subject<WsEvent>();
  event$ = this._event$.asObservable();

  private _groupMessages$ = new Subject<any>();
  groupMessages$ = this._groupMessages$.asObservable();

  // ── Estado de conexiones ─────────────────────────────────────
  connectionStatus = signal<WsStatus>('disconnected');

  // ── Conexiones activas ───────────────────────────────────────
  private chatWs: WebSocket | null = null;
  private eventsWs: WebSocket | null = null;
  private groupWs: WebSocket | null = null;
  private chatReconnectTimer: any;
  private eventsReconnectTimer: any;
  private groupReconnectTimer: any;

  private _currentChatRoom: string | null = null;
  private _currentGroupRoom: string | null = null;
  private _destroy$ = new Subject<void>();
  private _stopPolling$ = new Subject<void>();

  // Polling fallback — usado mientras no hay WS o como complemento
  private _currentVisitId: number | null = null;
  private _pollSub?: Subscription;

  // Snapshot del inbox anterior para detectar novedades en el poll global
  private _prevInboxSnapshot: Map<string, number> = new Map();
  private _prevRechazos = 0;

  // ── Helpers URL ───────────────────────────────────────────────
  private get wsBase(): string {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = location.host;
    return `${protocol}//${host}`;
  }

  // ═══════════════════════════════════════════════════════════════
  // Chat 1-a-1 por visita
  // ═══════════════════════════════════════════════════════════════

  /** Conectar al chat de una visita vía WebSocket + fallback polling */
  joinChat(visitaId: number): Observable<ChatMessage[]> {
    this._currentVisitId = visitaId;
    this._stopPolling$.next();
    this.disconnectChat();

    const room = String(visitaId);
    this._currentChatRoom = room;
    this.connectChatWS(`/api/chat/ws/${room}`);

    // Polling como fallback (cada 60s, solo cuando WS está desconectado)
    const polling$ = interval(60000).pipe(
      startWith(0),
      takeUntil(this._stopPolling$),
      switchMap(() => this.http.get<ChatMessage[]>(`/api/merc/chat/visitas/${visitaId}`)),
    );

    this._pollSub = polling$.subscribe({
      next: (msgs) => {
        // Solo emitimos por polling si no tenemos WS activo
        if (this.chatWs?.readyState !== WebSocket.OPEN) {
          msgs?.forEach(m => this._chatMessages$.next(m));
        }
      },
      error: () => { },
    });

    return polling$;
  }

  leaveChat(): void {
    this._currentVisitId = null;
    this._currentChatRoom = null;
    this._stopPolling$.next();
    this._pollSub?.unsubscribe();
    this.disconnectChat();
  }

  sendMessage(visitaId: number, mensaje: string, senderNombre: string): Observable<any> {
    // Enviar por REST — el backend hace broadcast al room chat_{visitaId}
    return this.http.post('/api/chat/send', {
      visita_id: visitaId,
      mensaje,
      sender_nombre: senderNombre,
    });
  }

  // ═══════════════════════════════════════════════════════════════
  // WebSocket de eventos de dominio (foto_status, visita_revisada, etc.)
  // ═══════════════════════════════════════════════════════════════

  connectToEvents(): void {
    if (this.eventsWs?.readyState === WebSocket.OPEN) return;
    this.disconnectEvents();

    this.eventsWs = new WebSocket(`${this.wsBase}/api/ws/events`);

    this.eventsWs.onopen = () => {
      this.connectionStatus.set('connected');
    };

    this.eventsWs.onmessage = (ev) => {
      try {
        const msg: WsEvent = JSON.parse(ev.data);
        this._event$.next(msg);
        this.handleDomainEvent(msg);
      } catch { }
    };

    this.eventsWs.onclose = () => {
      this.eventsWs = null;
      this.scheduleEventsReconnect();
    };

    this.eventsWs.onerror = () => {
      this.eventsWs?.close();
    };
  }

  disconnectEvents(): void {
    clearTimeout(this.eventsReconnectTimer);
    if (this.eventsWs) {
      this.eventsWs.onclose = null;
      this.eventsWs.close();
      this.eventsWs = null;
    }
  }

  // ═══════════════════════════════════════════════════════════════
  // WebSocket de grupos (solo lectura)
  // ═══════════════════════════════════════════════════════════════

  /** Conectarse a un room de grupo: `grupo_{id}` o `grupo_visita_{cliente}_{tipo}_{visita}` */
  connectToGroupRoom(room: string): void {
    if (this.groupWs && this._currentGroupRoom === room && this.groupWs.readyState === WebSocket.OPEN) return;
    this.disconnectGroup();

    this._currentGroupRoom = room;
    this.groupWs = new WebSocket(`${this.wsBase}/api/chat/grupos/ws/${room}`);

    this.groupWs.onopen = () => { };

    this.groupWs.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        this._groupMessages$.next(msg);
      } catch { }
    };

    this.groupWs.onclose = () => {
      this.groupWs = null;
      this.scheduleGroupReconnect();
    };

    this.groupWs.onerror = () => {
      this.groupWs?.close();
    };
  }

  disconnectGroup(): void {
    clearTimeout(this.groupReconnectTimer);
    if (this.groupWs) {
      this.groupWs.onclose = null;
      this.groupWs.close();
      this.groupWs = null;
    }
    this._currentGroupRoom = null;
  }

  // ═══════════════════════════════════════════════════════════════
  // Polling: Inbox (para MercChatComponent — pestaña Visitas y notificaciones)
  // ═══════════════════════════════════════════════════════════════

  getInbox(): Observable<any> {
    return this.http.get<any>('/api/merc/chat/inbox');
  }

  checkInboxForNotifications(inboxRes: any): void {
    if (!inboxRes) return;

    const convs: any[] = Array.isArray(inboxRes)
      ? inboxRes
      : [
        ...(inboxRes.equipo_operativo ?? inboxRes.conversaciones_equipo ?? inboxRes.conversaciones ?? []),
        ...(inboxRes.equipo_cliente ?? inboxRes.conversaciones_cliente ?? []),
      ];

    for (const c of convs) {
      const key = String(c.id_visita ?? c.id_conversacion ?? c.titulo ?? '');
      const prevUnread = this._prevInboxSnapshot.get(key) ?? 0;
      const currUnread = c.no_leidos ?? c.noLeidos ?? 0;

      if (currUnread > prevUnread) {
        const pdv = c.titulo ?? c.pdv_nombre ?? 'Visita';
        const remitente = c.ultimo_remitente ?? '';
        const texto = c.ultimo_mensaje ?? c.ultimo_msg ?? 'Nuevo mensaje recibido';
        this.notif.notifyMensaje(pdv, remitente, texto);
      }
      this._prevInboxSnapshot.set(key, currUnread);
    }

    const rechazos: any[] = inboxRes.rechazos ?? [];
    const newRechazos = rechazos.filter((r: any) => !r.leido).length;
    if (newRechazos > this._prevRechazos) {
      const nuevos = rechazos.filter((r: any) => !r.leido).slice(0, 3);
      for (const r of nuevos) {
        this.notif.notifyRechazo(r.pdv_nombre ?? r.punto_nombre ?? 'PDV', r.motivo);
      }
    }
    this._prevRechazos = newRechazos;

    const aprobaciones: any[] = inboxRes.aprobaciones ?? [];
    for (const a of aprobaciones.filter((x: any) => !x.leido).slice(0, 3)) {
      this.notif.notifyAprobacion(a.pdv_nombre ?? a.punto_nombre ?? 'PDV');
    }
  }

  // ═══════════════════════════════════════════════════════════════
  // Internals
  // ═══════════════════════════════════════════════════════════════

  private connectChatWS(path: string): void {
    this.chatWs = new WebSocket(`${this.wsBase}${path}`);

    this.chatWs.onopen = () => {
      this.connectionStatus.set('connected');
    };

    this.chatWs.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        // El servidor envía { id, visita_id, sender_nombre, mensaje, created_at, ... }
        this._chatMessages$.next({
          id_mensaje: msg.id,
          id_visita: msg.visita_id,
          sender_nombre: msg.sender_nombre,
          mensaje: msg.mensaje,
          created_at: msg.created_at,
          tipo_mensaje: msg.tipo_mensaje,
          sender_id: msg.sender_id,
        });
      } catch { }
    };

    this.chatWs.onclose = () => {
      this.chatWs = null;
      this.scheduleChatReconnect();
    };

    this.chatWs.onerror = () => {
      this.chatWs?.close();
    };
  }

  private disconnectChat(): void {
    clearTimeout(this.chatReconnectTimer);
    if (this.chatWs) {
      this.chatWs.onclose = null;
      this.chatWs.close();
      this.chatWs = null;
    }
  }

  private scheduleChatReconnect(): void {
    if (!this._currentChatRoom) return;
    clearTimeout(this.chatReconnectTimer);
    this.chatReconnectTimer = setTimeout(() => {
      if (this._currentChatRoom) {
        this.connectChatWS(`/api/chat/ws/${this._currentChatRoom}`);
      }
    }, 3000);
  }

  private scheduleEventsReconnect(): void {
    clearTimeout(this.eventsReconnectTimer);
    this.eventsReconnectTimer = setTimeout(() => this.connectToEvents(), 5000);
  }

  private scheduleGroupReconnect(): void {
    if (!this._currentGroupRoom) return;
    clearTimeout(this.groupReconnectTimer);
    this.groupReconnectTimer = setTimeout(() => {
      if (this._currentGroupRoom) {
        this.connectToGroupRoom(this._currentGroupRoom);
      }
    }, 3000);
  }

  private handleDomainEvent(event: WsEvent): void {
    switch (event.tipo) {
      case 'foto_status': {
        const { id_foto, id_visita, estado, motivo, tipo_foto } = event.data;
        if (estado === 'rechazado') {
          this.notif.notifyRechazo(
            `Visita #${id_visita}`,
            motivo || 'Sin motivo especificado'
          );
        } else if (estado === 'aprobado') {
          this.notif.notifyAprobacion(`Visita #${id_visita}`);
        }
        break;
      }
      case 'visita_revisada': {
        const { id_visita } = event.data;
        this.notif.notifyAprobacion(`Visita #${id_visita} revisada`);
        break;
      }
      case 'programacion_updated':
      case 'productos_updated':
        // Los componentes que consuman event$ pueden reaccionar
        break;
    }
  }

  ngOnDestroy(): void {
    this._destroy$.next();
    this._stopPolling$.next();
    this._pollSub?.unsubscribe();
    this.disconnectChat();
    this.disconnectEvents();
    this.disconnectGroup();
  }
}
