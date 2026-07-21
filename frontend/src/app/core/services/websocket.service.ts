import { Injectable } from '@angular/core';
import { Observable, Subject, timer } from 'rxjs';
import { webSocket, WebSocketSubject } from 'rxjs/webSocket';
import { retryWhen, delayWhen } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class WebSocketService {
  private sockets: Map<string, WebSocketSubject<any>> = new Map();

  connectToChat(room: string): Observable<any> {
    return this.getOrCreate(`${environment.wsUrl}/api/chat/ws/${room}`);
  }

  // Grupos de "equipo operativo" (chat_grupos.py) — sockets de solo-lectura,
  // el envío siempre es por REST (ver ApiService.enviarMensajeGrupo/...).
  connectToChatGrupos(room: string): Observable<any> {
    return this.getOrCreate(`${environment.wsUrl}/api/chat/grupos/ws/${room}`);
  }

  connectToNotifications(userId: number): Observable<any> {
    return this.getOrCreate(`${environment.wsUrl}/api/notifications/ws/${userId}`);
  }

  sendToChat(room: string, message: any): void {
    const url = `${environment.wsUrl}/api/chat/ws/${room}`;
    this.sockets.get(url)?.next(message);
  }

  disconnect(url: string): void {
    const socket = this.sockets.get(url);
    if (socket) {
      socket.complete();
      this.sockets.delete(url);
    }
  }

  disconnectAll(): void {
    this.sockets.forEach((s) => s.complete());
    this.sockets.clear();
  }

  private getOrCreate(url: string): Observable<any> {
    if (!this.sockets.has(url)) {
      const socket = webSocket(url);
      this.sockets.set(url, socket);
    }
    return this.sockets.get(url)!.pipe(
      retryWhen((errors) => errors.pipe(delayWhen(() => timer(3000))))
    );
  }
}
