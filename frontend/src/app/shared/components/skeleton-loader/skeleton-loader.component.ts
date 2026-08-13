import { Component, Input, computed } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
    selector: 'app-skeleton-loader',
    standalone: true,
    imports: [CommonModule],
    template: `
    <div class="animate-pulse space-y-4" [class.p-4]="!noPadding">
      @for (i of items; track i) {
        <div class="bg-white dark:bg-slate-900 border border-slate-100 dark:border-white/5 rounded-3xl p-5 shadow-sm space-y-3">
          <!-- Header -->
          <div class="flex items-start justify-between">
            <div class="space-y-2 flex-1">
              <div class="h-4 bg-slate-200 dark:bg-slate-800 rounded-lg" [style.width]="seededWidth(i, 60, 80)"></div>
              <div class="h-3 bg-slate-100 dark:bg-slate-800/50 rounded-lg" [style.width]="seededWidth(i, 35, 55)"></div>
            </div>
            <div class="h-5 w-20 bg-slate-200 dark:bg-slate-800 rounded-full"></div>
          </div>

          <!-- Content lines -->
          <div class="space-y-2">
            <div class="h-3 bg-slate-100 dark:bg-slate-800/50 rounded-lg" [style.width]="seededWidth(i + 1, 70, 95)"></div>
            <div class="h-3 bg-slate-100 dark:bg-slate-800/50 rounded-lg" [style.width]="seededWidth(i + 2, 45, 70)"></div>
          </div>

          <!-- Button row -->
          <div class="flex gap-2 pt-2">
            <div class="h-9 bg-slate-200 dark:bg-slate-800 rounded-xl flex-1"></div>
            <div class="h-9 bg-slate-200 dark:bg-slate-800 rounded-xl flex-1"></div>
            <div class="h-9 bg-slate-200 dark:bg-slate-800 rounded-xl flex-1"></div>
          </div>
        </div>
      }
    </div>
  `,
    styles: [`:host { display: block; }`]
})
export class SkeletonLoaderComponent {
    @Input() count: number = 3;
    @Input() noPadding: boolean = false;

    /** Deterministic item indices — prevents ExpressionChangedAfterItHasBeenCheckedError */
    get items(): number[] {
        return Array.from({ length: this.count }, (_, i) => i);
    }

    /**
     * Deterministic "seeded" percentage string based on index + offset.
     * Always returns the same value for the same inputs across renders.
     */
    seededWidth(seed: number, min: number, max: number): string {
        // Simple deterministic hash
        const range = max - min;
        const val = (seed * 13 + 7) % (range + 1);
        return (min + val) + '%';
    }
}
