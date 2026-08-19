import { Component, Input, Output, EventEmitter, signal, computed, HostListener, ElementRef, inject, ViewChild, HostBinding } from '@angular/core';
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
    <mat-icon class="ss-trigger-icon">{{ icon }}</mat-icon>
    <span class="ss-trigger-text" [class.ss-placeholder]="!selectedLabel()">
      {{ selectedLabel() || placeholder }}
    </span>
    <mat-icon class="ss-trigger-chevron">{{ open() ? 'expand_less' : 'expand_more' }}</mat-icon>
  </button>

  @if (open()) {
    <div class="ss-panel" [class.ss-panel-right]="align === 'right'">
      <div class="ss-search">
        <mat-icon class="ss-search-icon">search</mat-icon>
        <input #searchInput
          [ngModel]="search()"
          (ngModelChange)="onSearchInput($event)"
          (keydown.escape)="close()"
          (keydown.enter)="onEnterKey($event)"
          [placeholder]="searchPlaceholder">
        @if (search()) {
          <button type="button" class="ss-clear-search" (click)="onSearchInput('')">
            <mat-icon>close</mat-icon>
          </button>
        }
      </div>

      <div class="ss-list">
        <button type="button" class="ss-item ss-item-all"
          [class.ss-active]="!value"
          (click)="pick('')">
          <mat-icon class="ss-item-icon">all_inclusive</mat-icon>
          <span>{{ allLabel }}</span>
        </button>

        @if (allowCustom && search().trim() && !hasExactMatch()) {
          <button type="button" class="ss-item ss-add-custom" (click)="pick(search().trim())">
            <mat-icon class="ss-item-icon">add_circle</mat-icon>
            <span class="ss-item-label font-bold">Añadir "{{ search().trim() }}"</span>
          </button>
        }

        @for (opt of filtered(); track opt.value) {
          <button type="button" class="ss-item"
            [class.ss-active]="opt.value === value"
            (click)="pick(opt.value)">
            <span class="ss-item-label">{{ opt.label }}</span>
            @if (opt.value === value) {
              <mat-icon class="ss-check">check</mat-icon>
            }
          </button>
        }

        @if (filtered().length === 0 && (!search().trim() || hasExactMatch())) {
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
    :host { display: block; position: relative; z-index: 1; }
    :host(.ss-open), :host:has(.ss-open), .ss-wrap.ss-open { z-index: 99999 !important; position: relative; }
    .ss-wrap { position: relative; width: 100%; }
    .ss-trigger {
      display: flex; align-items: center; gap: .5rem;
      width: 100%; padding: .55rem .75rem;
      background: #ffffff;
      border: 1px solid #cbd5e1;
      border-radius: .75rem;
      color: #0f172a; cursor: pointer;
      font: inherit; text-align: left;
      transition: border-color .15s, background .15s;
    }
    :host-context(.dark) .ss-trigger {
      background: rgba(255,255,255,.05);
      border: 1px solid rgba(255,255,255,.08);
      color: inherit;
    }
    .ss-trigger:hover { border-color: #7c3aed; }
    :host-context(.dark) .ss-trigger:hover { border-color: rgba(124,58,237,.5); }
    .ss-open .ss-trigger { border-color: #7c3aed; background: rgba(124,58,237,.04); }
    :host-context(.dark) .ss-open .ss-trigger { border-color: #7c3aed; background: rgba(124,58,237,.08); }
    .ss-trigger-icon { font-size: 1.1rem; width: 1.1rem; height: 1.1rem; opacity: .7; }
    .ss-trigger-text { flex: 1; font-size: .875rem; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .ss-placeholder { opacity: .5; font-weight: 400; }
    .ss-trigger-chevron { font-size: 1.1rem; width: 1.1rem; height: 1.1rem; opacity: .5; }

    .ss-panel {
      position: absolute; z-index: 99999; top: calc(100% + 4px); left: 0;
      min-width: 100%; width: max-content; max-width: min(380px, 90vw);
      background: #ffffff !important;
      border: 1px solid #cbd5e1;
      border-radius: .75rem;
      box-shadow: 0 20px 35px -5px rgba(0,0,0,0.25), 0 10px 15px -6px rgba(0,0,0,0.2);
      overflow: hidden;
      animation: ss-fade .12s ease-out;
      color: #0f172a;
      transition: background 0.3s, border-color 0.3s;
    }
    .ss-panel-right { left: auto; right: 0; }

    :host-context(.dark) .ss-panel {
      background: #0f172a !important;
      border-color: #334155;
      color: #f8fafc;
      box-shadow: 0 20px 40px rgba(0,0,0,0.7);
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
    .ss-item:hover { background: #f1f5f9; color: #6d28d9; }
    :host-context(.dark) .ss-item:hover { background: rgba(255,255,255,0.05); color: #a78bfa; }
    
    .ss-active { background: #f5f3ff; color: #6d28d9; font-weight: 600; }
    :host-context(.dark) .ss-active { background: rgba(124,58,237,0.15); color: #a78bfa; }

    .ss-item-icon { font-size: 1.1rem; width: 1.1rem; height: 1.1rem; opacity: .7; }
    .ss-item-label { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .ss-check { font-size: 1.1rem; width: 1.1rem; height: 1.1rem; color: #6d28d9; }
    :host-context(.dark) .ss-check { color: #a78bfa; }

    .ss-item-all { border-bottom: 1px solid #f1f5f9; border-radius: 0; margin-bottom: 4px; padding-bottom: .6rem; color: #64748b; }
    :host-context(.dark) .ss-item-all { border-bottom-color: rgba(255,255,255,0.05); color: #94a3b8; }
    .ss-item-all:hover { color: #6d28d9; }
    :host-context(.dark) .ss-item-all:hover { color: #a78bfa; }

    .ss-add-custom {
      border-bottom: 1px solid #e2e8f0;
      background: #f0fdf4;
      color: #16a34a;
      font-weight: 700;
      margin-bottom: 4px;
    }
    :host-context(.dark) .ss-add-custom {
      border-bottom-color: rgba(255,255,255,0.08);
      background: rgba(22,163,74,0.15);
      color: #4ade80;
    }
    .ss-add-custom:hover {
      background: #dcfce7;
      color: #15803d;
    }
    :host-context(.dark) .ss-add-custom:hover {
      background: rgba(22,163,74,0.25);
      color: #86efac;
    }

    .ss-empty {
      display: flex; flex-direction: column; align-items: center; gap: .5rem;
      padding: 2rem 1rem; color: #94a3b8; font-size: .875rem;
    }
    .ss-empty mat-icon { font-size: 1.75rem; width: 1.75rem; height: 1.75rem; opacity: .5; }
  `]
})
export class SearchableSelectComponent {
  @HostBinding('class.ss-open') get isHostOpen() { return this.open(); }

  private _options = signal<SelectOption[]>([]);
  private _value = signal<string>('');

  @Input() set options(val: SelectOption[]) {
    this._options.set(val || []);
  }
  get options(): SelectOption[] {
    return this._options();
  }

  @Input() set value(val: string) {
    this._value.set(val ?? '');
  }
  get value(): string {
    return this._value();
  }

  @Input() placeholder: string = 'Selecciona...';
  @Input() searchPlaceholder: string = 'Buscar...';
  @Input() allLabel: string = 'Todos';
  @Input() icon: string = 'list';
  @Input() align: 'left' | 'right' = 'left';
  @Input() disabled: boolean = false;
  @Input() allowCustom: boolean = false;

  @Output() valueChange = new EventEmitter<string>();
  @Output() searchChange = new EventEmitter<string>();

  open = signal(false);
  search = signal('');

  private host = inject(ElementRef<HTMLElement>);
  @ViewChild('searchInput') searchInput?: ElementRef<HTMLInputElement>;

  selectedLabel = computed(() => {
    const opts = this._options() || [];
    const val = (this._value() ?? '').toString();
    if (!val) return '';
    const opt = opts.find(o => o && String(o.value) === val);
    return opt ? (opt.label ?? '') : val;
  });

  filtered = computed(() => {
    const q = (this.search() ?? '').toString().trim().toLowerCase();
    const opts = this._options() || [];
    if (!q) return opts;
    return opts.filter(o => {
      if (!o) return false;
      const label = (o.label ?? '').toString().toLowerCase();
      const val = (o.value ?? '').toString().toLowerCase();
      return label.includes(q) || val.includes(q);
    });
  });

  hasExactMatch = computed(() => {
    const q = (this.search() ?? '').toString().trim().toLowerCase();
    if (!q) return true;
    const opts = this._options() || [];
    return opts.some(o => o && (o.label ?? '').toString().toLowerCase() === q);
  });

  onSearchInput(val: string): void {
    this.search.set(val);
    this.searchChange.emit(val);
  }

  onEnterKey(e: Event): void {
    e.preventDefault();
    const q = (this.search() ?? '').toString().trim();
    if (!q) return;
    const opts = this._options() || [];
    const exact = opts.find(o => o && (o.label ?? '').toString().toLowerCase() === q.toLowerCase());
    if (exact) {
      this.pick(exact.value);
    } else if (this.allowCustom) {
      this.pick(q);
    }
  }

  toggle(): void {
    if (this.disabled) return;
    this.open.update(v => !v);
    if (this.open()) {
      this.onSearchInput('');
      setTimeout(() => this.searchInput?.nativeElement?.focus(), 50);
    }
  }
  close(): void { this.open.set(false); }
  pick(v: string): void {
    this._value.set(v);
    this.valueChange.emit(v);
    this.close();
  }

  @HostListener('document:click', ['$event'])
  onDocClick(e: MouseEvent): void {
    if (this.open() && !this.host.nativeElement.contains(e.target as Node)) this.close();
  }
}
