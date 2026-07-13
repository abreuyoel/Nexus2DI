import { Injectable, signal } from '@angular/core';

export type DialogMode = 'confirm' | 'prompt' | 'info';

export interface DialogRequest {
  mode: DialogMode;
  title?: string;
  message: string;
  items?: string[];
  confirmText?: string;
  cancelText?: string;
  danger?: boolean;
  inputValue?: string;
  inputPlaceholder?: string;
  inputRequired?: boolean;
  resolve: (value: any) => void;
}

/**
 * Reemplazo de confirm()/prompt()/alert() nativos del navegador con un diálogo
 * propio que respeta el tema oscuro de la app. Un solo <app-confirm-dialog>
 * montado en el shell atiende cualquier llamada, desde cualquier componente.
 */
@Injectable({ providedIn: 'root' })
export class ConfirmService {
  request = signal<DialogRequest | null>(null);

  confirm(message: string, opts: { title?: string; confirmText?: string; cancelText?: string; danger?: boolean } = {}): Promise<boolean> {
    return new Promise((resolve) => {
      this.request.set({ mode: 'confirm', message, resolve, ...opts });
    });
  }

  promptText(message: string, opts: { title?: string; placeholder?: string; required?: boolean; confirmText?: string; cancelText?: string } = {}): Promise<string | null> {
    return new Promise((resolve) => {
      this.request.set({
        mode: 'prompt', message, resolve, title: opts.title,
        inputValue: '', inputPlaceholder: opts.placeholder, inputRequired: opts.required,
        confirmText: opts.confirmText, cancelText: opts.cancelText,
      });
    });
  }

  info(message: string, opts: { title?: string; items?: string[]; confirmText?: string } = {}): Promise<void> {
    return new Promise((resolve) => {
      this.request.set({ mode: 'info', message, resolve, ...opts });
    });
  }

  respond(value: any) {
    const r = this.request();
    if (!r) return;
    this.request.set(null);
    r.resolve(value);
  }
}
