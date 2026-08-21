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
      <div class="fixed inset-0 z-[9999] flex items-center justify-center bg-slate-950/80 backdrop-blur-md p-4 animate-in fade-in duration-200" (mousedown)="onBackdrop($event, r)">
        <div class="w-full max-w-md rounded-3xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 shadow-2xl overflow-hidden flex flex-col scale-in-95 duration-200" (mousedown)="$event.stopPropagation()">
          
          <!-- Top Header with Glowing Badge Icon -->
          <div class="p-6 pb-2 flex items-start gap-4">
            <div [class]="r.danger ? 'bg-rose-500/10 text-rose-500 border-rose-500/20' : r.mode === 'info' ? 'bg-indigo-500/10 text-indigo-500 border-indigo-500/20' : 'bg-amber-500/10 text-amber-500 border-amber-500/20'"
              class="w-12 h-12 rounded-2xl border flex items-center justify-center shrink-0 shadow-sm">
              <span class="material-icons text-2xl">{{ r.danger ? 'warning' : r.mode === 'info' ? 'info' : 'help' }}</span>
            </div>

            <div class="space-y-1 flex-1">
              @if (r.title) {
                <h3 class="text-lg font-black tracking-tight text-slate-900 dark:text-white">
                  {{ r.title }}
                </h3>
              }
              <p class="text-xs font-semibold text-slate-600 dark:text-slate-300 leading-relaxed whitespace-pre-line">
                {{ r.message }}
              </p>
            </div>
          </div>

          <!-- Items list if provided -->
          @if (r.items?.length) {
            <div class="px-6 py-2">
              <div class="max-h-48 overflow-y-auto space-y-1 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-white/5 p-3">
                @for (item of r.items; track $index) {
                  <div class="text-xs font-medium text-slate-700 dark:text-slate-300 flex items-center gap-2">
                    <span class="material-icons text-sm text-slate-400">chevron_right</span>
                    <span>{{ item }}</span>
                  </div>
                }
              </div>
            </div>
          }

          <!-- Prompt input textarea if prompt mode -->
          @if (r.mode === 'prompt') {
            <div class="px-6 py-2">
              <textarea
                class="w-full rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 px-3 py-2.5 text-xs text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:border-indigo-500 resize-none font-medium"
                rows="3"
                [placeholder]="r.inputPlaceholder || ''"
                [(ngModel)]="r.inputValue"
              ></textarea>
            </div>
          }

          <!-- Action Buttons -->
          <div class="p-6 pt-4 flex items-center justify-end gap-3 bg-slate-50/50 dark:bg-slate-800/20 border-t border-slate-100 dark:border-white/5">
            @if (r.mode !== 'info') {
              <button
                type="button"
                class="px-5 py-2.5 text-xs font-bold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition-colors cursor-pointer"
                (click)="cancel(r)">
                {{ r.cancelText || 'Cancelar' }}
              </button>
            }

            <button
              type="button"
              [class]="r.danger
                ? 'bg-rose-600 hover:bg-rose-700 text-white shadow-lg shadow-rose-600/20'
                : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg shadow-indigo-600/20'"
              class="px-6 py-2.5 text-xs font-black rounded-xl transition-all flex items-center gap-2 cursor-pointer"
              (click)="confirm(r)">
              <span class="material-icons text-base">{{ r.danger ? 'delete' : 'check_circle' }}</span>
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
