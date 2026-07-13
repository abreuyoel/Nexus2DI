import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ConfirmService } from './confirm.service';

@Component({
  selector: 'app-confirm-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    @if (svc.request(); as r) {
      <div class="fixed inset-0 z-[1000] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4" (mousedown)="onBackdrop($event, r)">
        <div class="w-full max-w-sm rounded-2xl border border-white/10 bg-slate-900 shadow-2xl overflow-hidden" (mousedown)="$event.stopPropagation()">
          <div class="px-5 pt-5 pb-4">
            @if (r.title) {
              <h3 class="text-base font-semibold text-white mb-1.5">{{ r.title }}</h3>
            }
            <p class="text-sm text-slate-300 whitespace-pre-line leading-relaxed">{{ r.message }}</p>

            @if (r.items?.length) {
              <ul class="mt-3 max-h-56 overflow-y-auto space-y-1 rounded-lg bg-white/5 border border-white/8 p-2.5">
                @for (item of r.items; track $index) {
                  <li class="text-xs text-slate-300 border-b border-white/5 last:border-b-0 pb-1 last:pb-0">{{ item }}</li>
                }
              </ul>
            }

            @if (r.mode === 'prompt') {
              <textarea
                class="mt-3 w-full rounded-lg bg-white/5 border border-white/10 px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500/50 resize-none"
                rows="3"
                [placeholder]="r.inputPlaceholder || ''"
                [(ngModel)]="r.inputValue"
                #promptInput
              ></textarea>
            }
          </div>

          <div class="flex border-t border-white/8">
            @if (r.mode !== 'info') {
              <button
                type="button"
                class="flex-1 px-4 py-3 text-sm font-medium text-slate-300 hover:bg-white/5 transition"
                (click)="cancel(r)"
              >
                {{ r.cancelText || 'Cancelar' }}
              </button>
            }
            <button
              type="button"
              class="flex-1 px-4 py-3 text-sm font-semibold transition border-l border-white/8"
              [class]="r.danger ? 'text-red-400 hover:bg-red-500/10' : 'text-sky-400 hover:bg-sky-500/10'"
              (click)="confirm(r)"
            >
              {{ r.confirmText || (r.mode === 'info' ? 'Entendido' : 'Confirmar') }}
            </button>
          </div>
        </div>
      </div>
    }
  `,
})
export class ConfirmDialogComponent {
  svc = inject(ConfirmService);

  confirm(r: any) {
    if (r.mode === 'prompt') {
      const val = (r.inputValue || '').trim();
      if (r.inputRequired && !val) return;
      this.svc.respond(val);
    } else if (r.mode === 'info') {
      this.svc.respond(undefined);
    } else {
      this.svc.respond(true);
    }
  }

  cancel(r: any) {
    this.svc.respond(r.mode === 'prompt' ? null : false);
  }

  onBackdrop(ev: MouseEvent, r: any) {
    this.cancel(r);
  }
}
