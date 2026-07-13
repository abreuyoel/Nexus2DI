import { Component, Input, Output, EventEmitter, signal, computed, HostListener, ElementRef, inject, input, model } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';

export interface SelectOption {
  value: string;
  label: string;
}

@Component({
  selector: 'app-searchable-select',
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule],
  template: `
<div class="ss-wrap" [class.ss-open]="open()">
  <button type="button" class="ss-trigger" (click)="toggle()">
    <mat-icon class="ss-trigger-icon">{{ icon() }}</mat-icon>
    <span class="ss-trigger-text" [class.ss-placeholder]="!selectedLabel()">
      {{ selectedLabel() || placeholder() }}
    </span>
    <mat-icon class="ss-trigger-chevron">{{ open() ? 'expand_less' : 'expand_more' }}</mat-icon>
  </button>

  @if (open()) {
    <div class="ss-panel">
      <div class="ss-search">
        <mat-icon class="ss-search-icon">search</mat-icon>
        <input #searchInput
          [ngModel]="search()"
          (ngModelChange)="search.set($event)"
          (keydown.escape)="close()"
          [placeholder]="searchPlaceholder()"
          autofocus>
        @if (search()) {
          <button type="button" class="ss-clear-search" (click)="search.set('')">
            <mat-icon>close</mat-icon>
          </button>
        }
      </div>

      <div class="ss-list">
        <button type="button" class="ss-item ss-item-all"
          [class.ss-active]="!value()"
          (click)="pick('')">
          <mat-icon class="ss-item-icon">all_inclusive</mat-icon>
          <span>{{ allLabel() }}</span>
        </button>

        @for (opt of filtered(); track opt.value) {
          <button type="button" class="ss-item"
            [class.ss-active]="opt.value === value()"
            (click)="pick(opt.value)">
            <span class="ss-item-label">{{ opt.label }}</span>
            @if (opt.value === value()) {
              <mat-icon class="ss-check">check</mat-icon>
            }
          </button>
        }

        @if (filtered().length === 0) {
          <div class="ss-empty">
            <mat-icon>search_off</mat-icon>
            <span>Sin coincidencias</span>
          </div>
        }
      </div>
    </div>
  }
</div>
  `,
  styles: [`
    .ss-wrap { position: relative; width: 100%; }
    .ss-trigger {
      display: flex; align-items: center; gap: .5rem;
      width: 100%; padding: .55rem .75rem;
      background: rgba(255,255,255,.05);
      border: 1px solid rgba(255,255,255,.08);
      border-radius: .75rem;
      color: inherit; cursor: pointer;
      font: inherit; text-align: left;
      transition: border-color .15s, background .15s;
    }
    .ss-trigger:hover { border-color: rgba(124,58,237,.5); }
    .ss-open .ss-trigger { border-color: #7c3aed; background: rgba(124,58,237,.08); }
    .ss-trigger-icon { font-size: 1.1rem; width: 1.1rem; height: 1.1rem; opacity: .7; }
    .ss-trigger-text { flex: 1; font-size: .875rem; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .ss-placeholder { opacity: .5; font-weight: 400; }
    .ss-trigger-chevron { font-size: 1.1rem; width: 1.1rem; height: 1.1rem; opacity: .5; }

    .ss-panel {
      position: absolute; z-index: 1000; top: calc(100% + 4px); left: 0; right: 0;
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: .75rem;
      box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.1);
      overflow: hidden;
      animation: ss-fade .12s ease-out;
      color: #1e293b;
      transition: background 0.3s, border-color 0.3s;
    }

    :host-context(.dark) .ss-panel {
      background: #1f2937;
      border-color: rgba(255,255,255,0.1);
      color: #f1f5f9;
      box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }

    @keyframes ss-fade {
      from { opacity: 0; transform: translateY(-4px); }
      to   { opacity: 1; transform: none; }
    }

    .ss-search {
      display: flex; align-items: center; gap: .5rem;
      padding: .6rem .75rem;
      background: #f8fafc;
      border-bottom: 1px solid #f1f5f9;
    }
    :host-context(.dark) .ss-search { background: rgba(0,0,0,0.2); border-bottom-color: rgba(255,255,255,0.05); }

    .ss-search-icon { color: #64748b; font-size: 1.1rem; width: 1.1rem; height: 1.1rem; }
    .ss-search input {
      flex: 1; background: transparent; border: 0; outline: 0;
      color: #1e293b; font: inherit; font-size: .875rem;
    }
    :host-context(.dark) .ss-search input { color: #fff; }
    .ss-search input::placeholder { color: #94a3b8; }

    .ss-clear-search {
      background: transparent; border: 0; cursor: pointer; padding: 2px;
      color: #64748b; display: inline-flex;
    }
    .ss-clear-search:hover { color: #1e293b; }
    :host-context(.dark) .ss-clear-search:hover { color: #fff; }
    .ss-clear-search mat-icon { font-size: 1rem; width: 1rem; height: 1rem; }

    .ss-list { max-height: 280px; overflow-y: auto; padding: .35rem; }
    .ss-list::-webkit-scrollbar { width: 5px; }
    .ss-list::-webkit-scrollbar-thumb { background: #e2e8f0; border-radius: 10px; }
    :host-context(.dark) .ss-list::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); }

    .ss-item {
      display: flex; align-items: center; gap: .6rem;
      width: 100%; padding: .55rem .75rem;
      background: transparent; border: 0; cursor: pointer;
      color: #334155; font: inherit; text-align: left; border-radius: .5rem;
      font-size: .875rem; transition: all .15s;
    }
    :host-context(.dark) .ss-item { color: #cbd5e1; }
    .ss-item:hover { background: #f1f5f9; color: #7c3aed; }
    :host-context(.dark) .ss-item:hover { background: rgba(255,255,255,0.05); color: #a78bfa; }
    
    .ss-active { background: #f5f3ff; color: #7c3aed; font-weight: 600; }
    :host-context(.dark) .ss-active { background: rgba(124,58,237,0.15); color: #a78bfa; }

    .ss-item-icon { font-size: 1.1rem; width: 1.1rem; height: 1.1rem; opacity: .7; }
    .ss-item-label { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .ss-check { font-size: 1.1rem; width: 1.1rem; height: 1.1rem; color: #7c3aed; }
    :host-context(.dark) .ss-check { color: #a78bfa; }

    .ss-item-all { border-bottom: 1px solid #f1f5f9; border-radius: 0; margin-bottom: 4px; padding-bottom: .6rem; color: #64748b; }
    :host-context(.dark) .ss-item-all { border-bottom-color: rgba(255,255,255,0.05); color: #94a3b8; }
    .ss-item-all:hover { color: #7c3aed; }
    :host-context(.dark) .ss-item-all:hover { color: #a78bfa; }

    .ss-empty {
      display: flex; flex-direction: column; align-items: center; gap: .5rem;
      padding: 2rem 1rem; color: #94a3b8; font-size: .875rem;
    }
    .ss-empty mat-icon { font-size: 1.75rem; width: 1.75rem; height: 1.75rem; opacity: .5; }
  `]
})
export class SearchableSelectComponent {
  options = input<SelectOption[]>([]);
  value = model<string>('');
  placeholder = input<string>('Selecciona...');
  searchPlaceholder = input<string>('Buscar...');
  allLabel = input<string>('Todos');
  icon = input<string>('list');
  @Output() valueChange = new EventEmitter<string>();

  open = signal(false);
  search = signal('');

  private host = inject(ElementRef<HTMLElement>);

  selectedLabel = computed(() => {
    const opt = this.options().find(o => o.value === this.value());
    return opt ? opt.label : '';
  });

  filtered = computed(() => {
    const q = this.search().trim().toLowerCase();
    const opts = this.options();
    if (!q) return opts;
    return opts.filter(o => o.label.toLowerCase().includes(q) || o.value.toLowerCase().includes(q));
  });

  toggle(): void {
    this.open.update(v => !v);
    if (this.open()) this.search.set('');
  }
  close(): void { this.open.set(false); }
  pick(v: string): void {
    this.value.set(v);
    this.valueChange.emit(v);
    this.close();
  }

  @HostListener('document:click', ['$event'])
  onDocClick(e: MouseEvent): void {
    if (this.open() && !this.host.nativeElement.contains(e.target as Node)) this.close();
  }
}
