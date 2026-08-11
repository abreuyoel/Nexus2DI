import { Injectable, signal, computed, inject } from '@angular/core';
import { BrowserNotificationService } from './browser-notification.service';
import { ConfirmService } from '../../../shared/components/confirm-dialog/confirm.service';
import { ApiService } from '../../../core/services/api.service';

export interface ActiveVisit {
  // number cuando la visita ya tiene id real del servidor; string ("local_<uuid>")
  // mientras la activación quedó encolada offline y todavía no sincronizó.
  id_visita: number | string;
  pdv_nombre: string;
  id_punto?: string;
  id_cliente: number;
  cliente?: string;
  // Si la visita se abrió offline, el id de la cadena en OfflineQueueService
  // (ver offline-queue.service.ts) -- fotos/balance/finalizar deben encolarse
  // como pasos de esta cadena mientras no se resuelva a un id_visita real.
  chainId?: string | null;
}

/** Duración máxima de una visita en segundos (40 minutos). */
const MAX_VISITA_SECS = 40 * 60; // 2400

@Injectable({ providedIn: 'root' })
export class MercUiService {
  private notif = inject(BrowserNotificationService);
  private confirm = inject(ConfirmService);
  private api = inject(ApiService);

  activeVisit = signal<ActiveVisit | null>(null);
  detailVisitId = signal<number | null>(null);

  // ─── Timer de visita (40 min) ───
  timerSeconds = signal(MAX_VISITA_SECS);
  private timerInterval: ReturnType<typeof setInterval> | null = null;
  private notificationSent = false;
  private activeTimerId: string | null = null;

  /** Se muestra una sola vez por sesión al abrir la primera visita. */
  private disclaimerShown = false;

  timerExpired = computed(() => this.timerSeconds() <= 0);
  timerDisplay = computed(() => {
    const total = Math.max(0, this.timerSeconds());
    const min = Math.floor(total / 60).toString().padStart(2, '0');
    const sec = (total % 60).toString().padStart(2, '0');
    return `${min}:${sec}`;
  });

  constructor() {
    this.checkActiveTimerOnStartup();
  }

  private reportAudit(evento: string, detalle?: string) {
    const v = this.activeVisit();
    const id_visita_num = v && typeof v.id_visita === 'number' ? v.id_visita : undefined;
    const pointId = v?.id_punto || undefined;
    const seconds = this.timerSeconds();

    this.api.registrarAuditoriaTiempo({
      id_visita: id_visita_num,
      identificador_punto_interes: pointId,
      evento,
      detalle,
      tiempo_restante_segundos: seconds
    }).subscribe({
      error: () => { /* Silently fail to not block the UI */ }
    });
  }

  private checkActiveTimerOnStartup() {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith('merc_timer_exp_')) {
        const saved = localStorage.getItem(key);
        if (saved) {
          const expTime = parseInt(saved, 10);
          const now = Date.now();
          const remaining = Math.max(0, Math.floor((expTime - now) / 1000));
          this.timerSeconds.set(remaining);
          const timerId = key.replace('merc_timer_exp_', '');
          this.iniciarTimer(false, timerId);
          break;
        }
      }
    }
  }

  private getDisclaimerShown(): boolean {
    if (this.disclaimerShown) return true;
    const val = localStorage.getItem('merc_disclaimer_shown');
    if (val === 'true') {
      this.disclaimerShown = true;
      return true;
    }
    return false;
  }

  private setDisclaimerShown() {
    this.disclaimerShown = true;
    localStorage.setItem('merc_disclaimer_shown', 'true');
  }

  /** Abre el panel de visita. La primera vez muestra un disclaimer con las reglas del timer. */
  async openVisit(visit: ActiveVisit) {
    if (!this.getDisclaimerShown()) {
      this.setDisclaimerShown();
      await this.confirm.info(
        '⏱️ Disponés de 40 minutos para completar la visita (fotos y auditoría).\n\nEl contador se reinicia cada vez que subís una foto o guardás datos de balance.\n\nSi el tiempo se agota, deberás reconectar el dispositivo a internet para validar tu actividad.\n\n⚠️ No podés tomar las fotos y cargarlas después desde otro lugar.',
        { title: '⏰ Reglas del Temporizador', confirmText: 'Entendido' }
      );
    }
    this.activeVisit.set(visit);

    const targetId = String(visit.id_punto || visit.id_visita);
    if (this.activeTimerId === targetId) {
      // Ya está corriendo en segundo plano, no reiniciar nada
      this.reportAudit('OPEN_VISITA', 'Panel de visita abierto (ya estaba corriendo en segundo plano).');
      return;
    }

    // Si había otro corriendo, detenerlo
    this.detenerTimer();

    const key = 'merc_timer_exp_' + targetId;
    const saved = localStorage.getItem(key);
    if (saved) {
      const expTime = parseInt(saved, 10);
      const now = Date.now();
      const remaining = Math.max(0, Math.floor((expTime - now) / 1000));
      this.timerSeconds.set(remaining);
      this.iniciarTimer(false, targetId);
      this.reportAudit('RESUME_VISITA', `Visita reanudada. Restaban ${remaining}s.`);
    } else {
      const expTime = Date.now() + MAX_VISITA_SECS * 1000;
      localStorage.setItem(key, expTime.toString());
      this.timerSeconds.set(MAX_VISITA_SECS);
      this.iniciarTimer(true, targetId);
      this.reportAudit('INICIO_VISITA', 'Nueva visita iniciada.');
    }
  }

  closeVisit(finalized = false) {
    if (finalized && this.activeTimerId) {
      this.reportAudit('FINALIZAR_VISITA', 'Visita completada y finalizada.');
      const key = 'merc_timer_exp_' + this.activeTimerId;
      localStorage.removeItem(key);
      this.detenerTimer();
    } else {
      this.reportAudit('CERRAR_PANEL', 'Cerró el panel de visita sin finalizar (pausa de fondo).');
    }
    this.activeVisit.set(null);
  }

  openDetailVisit(idVisita: number) {
    this.detailVisitId.set(idVisita);
  }

  closeDetailVisit() {
    this.detailVisitId.set(null);
  }

  /** Reemplaza el id_visita placeholder por el real cuando la cadena sincroniza. */
  resolveVisita(chainId: string, realVisitaId: number) {
    const v = this.activeVisit();
    if (v && v.chainId === chainId) {
      const oldTarget = String(v.id_punto || v.id_visita);
      const newTarget = String(v.id_punto || realVisitaId);
      if (oldTarget !== newTarget) {
        const oldKey = 'merc_timer_exp_' + oldTarget;
        const newKey = 'merc_timer_exp_' + newTarget;
        const val = localStorage.getItem(oldKey);
        if (val) {
          localStorage.setItem(newKey, val);
          localStorage.removeItem(oldKey);
        }
        if (this.activeTimerId === oldTarget) {
          this.activeTimerId = newTarget;
        }
      }
      this.activeVisit.set({ ...v, id_visita: realVisitaId, chainId: null });
      this.reportAudit('RESOLVE_VISITA', `Visita offline sincronizada con ID real: ${realVisitaId}.`);
    }
  }

  // ─── Timer ──────────────────────────────────────────────────────────────

  /** Inicia el contador regresivo de 40 min. */
  private iniciarTimer(reset = true, timerId?: string) {
    this.detenerTimer();
    if (timerId) {
      this.activeTimerId = timerId;
    }
    const targetId = this.activeTimerId;
    if (reset && targetId) {
      this.timerSeconds.set(MAX_VISITA_SECS);
      const key = 'merc_timer_exp_' + targetId;
      const expTime = Date.now() + MAX_VISITA_SECS * 1000;
      localStorage.setItem(key, expTime.toString());
    }
    this.notificationSent = false;
    this.timerInterval = setInterval(() => {
      this.timerSeconds.update(s => {
        const next = s - 1;
        // Al llegar a 0, disparar notificación del navegador (solo una vez)
        if (next <= 0 && !this.notificationSent) {
          this.notificationSent = true;
          this.reportAudit('TIEMPO_AGOTADO', 'Se agotaron los 40 minutos.');
          this.notif.notify(
            '⏰ Tiempo excedido',
            'Se agotaron los 40 minutos para completar la visita. Reconectá el dispositivo para validar tu actividad.',
            { tag: 'timer-expired', force: true }
          );
        }
        return next;
      });
    }, 1000);
  }

  /** Reinicia el contador a 40 min (llamar tras cada foto/balance/actividad). */
  resetTimer(detalle = 'Actividad') {
    if (this.activeTimerId) {
      const key = 'merc_timer_exp_' + this.activeTimerId;
      const expTime = Date.now() + MAX_VISITA_SECS * 1000;
      localStorage.setItem(key, expTime.toString());
    }
    const previousSeconds = this.timerSeconds();
    this.timerSeconds.set(MAX_VISITA_SECS);
    this.notificationSent = false;
    this.reportAudit('REINICIO_TIEMPO', `${detalle}. Tiempo restante previo: ${previousSeconds}s.`);
  }

  /** Detiene completamente el timer (al cerrar visita). */
  private detenerTimer() {
    if (this.timerInterval !== null) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
    this.activeTimerId = null;
  }
}
