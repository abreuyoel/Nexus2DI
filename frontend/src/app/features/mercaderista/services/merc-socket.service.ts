import { Injectable, OnDestroy } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Subject, Observable, interval } from 'rxjs';
import { takeUntil, switchMap, startWith } from 'rxjs/operators';

export interface ChatMessage {
  id_mensaje?: number;
  id_visita: number;
  sender_nombre: string;
  mensaje: string;
  created_at?: string;
  tipo_mensaje?: string;
}

@Injectable({ providedIn: 'root' })
export class MercSocketService implements OnDestroy {
  private _messages$ = new Subject<ChatMessage>();
  messages$ = this._messages$.asObservable();

  private _currentVisitId: number | null = null;
  private _destroy$ = new Subject<void>();
  private _stopPolling$ = new Subject<void>();
  private _lastMsgCount = 0;

  constructor(private http: HttpClient) {}

  /** Conectar al chat de una visita (poll cada 8s) */
  joinChat(visitaId: number): Observable<ChatMessage[]> {
    this._currentVisitId = visitaId;
    this._stopPolling$.next();

    // Polling simple — se puede mejorar con WS cuando el server lo soporte para móvil
    return interval(8000).pipe(
      startWith(0),
      takeUntil(this._stopPolling$),
      switchMap(() => this.http.get<ChatMessage[]>(`/api/chat/visit/${visitaId}/messages`)),
    );
  }

  leaveChat(): void {
    this._currentVisitId = null;
    this._stopPolling$.next();
  }

  sendMessage(visitaId: number, mensaje: string, senderNombre: string): Observable<any> {
    return this.http.post('/api/chat/send', {
      visita_id: visitaId,
      mensaje,
      sender_nombre: senderNombre,
    });
  }

  getInbox(): Observable<any[]> {
    return this.http.get<any[]>('/api/merc/chat/inbox');
  }

  ngOnDestroy(): void {
    this._destroy$.next();
    this._stopPolling$.next();
  }
}
