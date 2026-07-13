import { Injectable, NgZone, signal } from '@angular/core';
import { Subject } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface RealtimeEvent { tipo: string; data: any; }

/**
 * Canal global de eventos en tiempo real (/api/ws/events).
 * Los componentes se suscriben a `events$` y refrescan sus datos según `tipo`.
 */
@Injectable({ providedIn: 'root' })
export class RealtimeService {
  private ws?: WebSocket;
  private reconnectTimer?: any;
  private manualClose = false;
  private readonly _events = new Subject<RealtimeEvent>();
  readonly events$ = this._events.asObservable();
  readonly connected = signal(false);

  constructor(private zone: NgZone) {}

  connect(): void {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) return;
    this.manualClose = false;
    const base = environment.wsUrl || `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}`;
    const url = `${base}/api/ws/events`;
    try {
      this.ws = new WebSocket(url);
      this.ws.onopen = () => this.zone.run(() => this.connected.set(true));
      this.ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (msg && msg.tipo) this.zone.run(() => this._events.next(msg));
        } catch { /* ignora frames no-JSON */ }
      };
      this.ws.onclose = () => {
        this.zone.run(() => this.connected.set(false));
        if (!this.manualClose) this.scheduleReconnect();
      };
      this.ws.onerror = () => { try { this.ws?.close(); } catch { /* noop */ } };
    } catch {
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect(): void {
    clearTimeout(this.reconnectTimer);
    this.reconnectTimer = setTimeout(() => this.connect(), 4000);
  }

  disconnect(): void {
    this.manualClose = true;
    clearTimeout(this.reconnectTimer);
    try { this.ws?.close(); } catch { /* noop */ }
    this.ws = undefined;
  }
}
