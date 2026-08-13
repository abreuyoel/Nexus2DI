import { Injectable } from '@angular/core';

/**
 * Servicio de Notificaciones del Navegador (Web Notifications API).
 * Solicita permiso una sola vez y dispara notificaciones nativas del OS
 * cuando llegan mensajes nuevos o alertas de fotos rechazadas.
 */
@Injectable({ providedIn: 'root' })
export class BrowserNotificationService {

  private _permissionGranted = false;

  /**
   * Solicita permiso de notificaciones al usuario.
   * Llama esto al iniciar el portal mercaderista.
   */
  async requestPermission(): Promise<void> {
    if (!('Notification' in window)) return;
    if (Notification.permission === 'granted') {
      this._permissionGranted = true;
      return;
    }
    if (Notification.permission === 'denied') return;
    const result = await Notification.requestPermission();
    this._permissionGranted = result === 'granted';
  }

  get isGranted(): boolean {
    return this._permissionGranted || Notification.permission === 'granted';
  }

  /**
   * Muestra una notificación nativa del navegador.
   * @param title Título de la notificación
   * @param body  Cuerpo del mensaje
   * @param opts  Opciones adicionales (icono, tag, etc.)
   */
  notify(title: string, body: string, opts: NotificationOptions & { force?: boolean } = {}): void {
    if (!this.isGranted) return;
    if (!('Notification' in window)) return;

    // Si la pestaña está activa/visible no mandamos notificación OS (ya la ve) a menos que se force
    if (document.visibilityState === 'visible' && !opts.force) return;

    const n = new Notification(title, {
      body,
      icon: '/favicon.ico',
      badge: '/favicon.ico',
      tag: opts.tag ?? 'merc-msg',   // tag agrupa: no spamea si ya hay una del mismo tipo
      renotify: true,                 // aunque el tag sea el mismo, vibra de nuevo
      ...opts,
    } as NotificationOptions);

    // Autoclose a los 6 segundos
    setTimeout(() => n.close(), 6000);

    // Al hacer click, foca la pestaña
    n.onclick = () => { window.focus(); n.close(); };
  }

  /**
   * Notificación de mensaje nuevo en chat.
   */
  notifyMensaje(pdvNombre: string, remitente: string, texto: string, force = false): void {
    this.notify(
      `💬 Nuevo mensaje — ${pdvNombre}`,
      `${remitente}: ${texto}`,
      { tag: `chat-${pdvNombre}`, force }
    );
  }

  /**
   * Notificación de foto rechazada.
   */
  notifyRechazo(pdvNombre: string, motivo?: string): void {
    this.notify(
      `❌ Foto rechazada — ${pdvNombre}`,
      motivo ? `Motivo: ${motivo}` : 'El analista rechazó una de tus fotos. Revisa la sección de Notificaciones.',
      { tag: `rechazo-${pdvNombre}` }
    );
  }

  /**
   * Notificación de foto aprobada.
   */
  notifyAprobacion(pdvNombre: string): void {
    this.notify(
      `✅ Foto aprobada — ${pdvNombre}`,
      'Una de tus fotos fue aprobada por el analista.',
      { tag: `aprobacion-${pdvNombre}` }
    );
  }

  /**
   * Notificación de sincronización exitosa.
   */
  notifySync(count: number): void {
    this.notify(
      '☁️ Gestiones sincronizadas',
      `${count} elemento(s) se enviaron exitosamente al servidor.`,
      { tag: 'sync-ok' }
    );
  }
}
