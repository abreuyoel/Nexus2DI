import {
  Component,
  Input,
  Output,
  EventEmitter,
  signal,
  computed,
  ChangeDetectionStrategy,
  HostListener,
  ViewChild,
  ElementRef,
  OnChanges,
  SimpleChanges,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

export interface SearchableOption<T = any> {
  value: T;
  label: string;
  secondary?: string;
  disabled?: boolean;
  icon?: string;
}

@Component({
  selector: 'app-searchable-select',
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule, MatProgressSpinnerModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './searchable-select.component.scss',
  template: `
    <div class="searchable-select" [class.is-open]="isOpen()" [class.dark-mode]="darkMode">
      @if (label) {
        <label class="select-label">{{ label }}</label>
      }

      <div class="select-trigger" (click)="toggleOpen()" [class.has-value]="hasValue()">
        <div class="selected-value" [class.placeholder]="!hasValue()">
          @if (multiple) {
            @if (selectedOptions().length > 0) {
              <div class="chips-container">
                @for (opt of displayChips(); track opt.value) {
                  <span class="chip">{{ opt.label }}</span>
                }
                @if (selectedOptions().length > 2) {
                  <span class="chip-remainder">+{{ selectedOptions().length - 2 }}</span>
                }
              </div>
            } @else {
              <span class="placeholder-text">{{ placeholder }}</span>
            }
          } @else {
            @if (selectedOption(); as opt) {
              @if (opt.icon) {
                <mat-icon class="option-icon">{{ opt.icon }}</mat-icon>
              }
              <div class="option-content">
                <span class="option-label">{{ opt.label }}</span>
                @if (opt.secondary) {
                  <span class="option-secondary">{{ opt.secondary }}</span>
                }
              </div>
            } @else {
              <span class="placeholder-text">{{ placeholder }}</span>
            }
          }
        </div>
        <div class="trigger-actions">
          @if (clearable && hasValue()) {
            <button
              type="button"
              class="clear-btn"
              (click)="clearSelection($event)"
              tabindex="-1"
              aria-label="Limpiar selección"
            >
              <mat-icon>close</mat-icon>
            </button>
          }
          <mat-icon class="arrow-icon">{{ isOpen() ? 'expand_less' : 'expand_more' }}</mat-icon>
        </div>
      </div>

      @if (isOpen()) {
        <div class="select-dropdown" (click)="$event.stopPropagation()">
          <div class="search-box">
            <mat-icon class="search-icon">search</mat-icon>
            <input
              #searchInput
              type="text"
              [placeholder]="searchPlaceholder"
              [ngModel]="searchQuery()"
              (ngModelChange)="onSearch($event)"
              (keydown)="onKeydown($event)"
              autocomplete="off"
              spellcheck="false"
            />
          </div>

          <div class="options-list">
            @if (loading) {
              <div class="loading-state">
                <mat-spinner diameter="24"></mat-spinner>
                <span>Cargando...</span>
              </div>
            } @else if (filteredOptions().length === 0) {
              <div class="empty-state">
                <mat-icon>search_off</mat-icon>
                @if (searchQuery()) {
                  <span>Sin resultados para "<strong>{{ searchQuery() }}</strong>"</span>
                } @else {
                  <span>No hay opciones disponibles</span>
                }
              </div>
            } @else {
              <div class="options-container">
                @for (opt of filteredOptions(); track opt.value; let i = $index) {
                  <div
                    class="option-item"
                    [class.highlighted]="i === highlightedIndex()"
                    [class.selected]="isSelected(opt.value)"
                    [class.disabled]="opt.disabled"
                    (click)="selectOption(opt)"
                    (mouseenter)="highlightedIndex.set(i)"
                    role="option"
                    [attr.aria-selected]="isSelected(opt.value)"
                  >
                    @if (opt.icon) {
                      <mat-icon class="option-icon">{{ opt.icon }}</mat-icon>
                    }
                    <div class="option-content">
                      <span class="option-label">{{ opt.label }}</span>
                      @if (opt.secondary) {
                        <span class="option-secondary">{{ opt.secondary }}</span>
                      }
                    </div>
                    @if (multiple) {
                      <mat-icon class="checkbox-icon" [class.checked]="isSelected(opt.value)">
                        {{ isSelected(opt.value) ? 'check_box' : 'check_box_outline_blank' }}
                      </mat-icon>
                    } @else {
                      @if (opt.value === value) {
                        <mat-icon class="check-icon">check</mat-icon>
                      }
                    }
                  </div>
                }
              </div>
              @if (filteredOptions().length < options.length) {
                <div class="options-footer">
                  Mostrando {{ filteredOptions().length }} de {{ options.length }}
                </div>
              }
            }
          </div>
        </div>
      }
    </div>
  `,
})
export class SearchableSelectComponent implements OnChanges {
  @Input() options: SearchableOption[] = [];
  @Input() placeholder = 'Seleccionar...';
  @Input() searchPlaceholder = 'Buscar...';
  @Input() value: any = null;
  @Input() clearable = false;
  @Input() loading = false;
  @Input() label = '';
  @Input() minCharsFilter = 0;
  @Input() darkMode = false;
  @Input() multiple = false;

  @Output() valueChange = new EventEmitter<any>();
  @Output() opened = new EventEmitter<void>();
  @Output() closed = new EventEmitter<void>();

  // ── Internal state ─────────────────────────────────────────────
  isOpen = signal(false);
  searchQuery = signal('');
  highlightedIndex = signal(0);
  private optionsVersion = signal(0);
  private valueVersion = signal(0);

  private debounceTimer: ReturnType<typeof setTimeout> | null = null;

  // ── ViewChild for search input ──────────────────────────────────
  @ViewChild('searchInput', { static: false })
  set searchInputRef(el: ElementRef<HTMLInputElement> | undefined) {
    if (el) {
      setTimeout(() => el.nativeElement.focus());
    }
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['options']) this.optionsVersion.update(version => version + 1);
    if (changes['value']) this.valueVersion.update(version => version + 1);
  }

  // ── Computed ────────────────────────────────────────────────────
  /** Single selected option for non-multiple mode */
  selectedOption = computed(() => {
    this.optionsVersion();
    this.valueVersion();
    return this.options.find(o => o.value === this.value) ?? null;
  });

  /** All selected options for multiple mode */
  selectedOptions = computed(() => {
    this.optionsVersion();
    this.valueVersion();
    if (!this.multiple) return [];
    const arr = Array.isArray(this.value) ? this.value : [];
    return this.options.filter(o => arr.includes(o.value));
  });

  /** Whether the component has a value selected (for clear button) */
  hasValue = computed(() => {
    if (this.multiple) {
      return Array.isArray(this.value) && this.value.length > 0;
    }
    return this.value != null && this.value !== '';
  });

  /** First 2 chips to display in the trigger when multiple */
  displayChips = computed(() => {
    return this.selectedOptions().slice(0, 2);
  });

  filteredOptions = computed(() => {
    this.optionsVersion();
    const query = this.searchQuery().toLowerCase().trim();
    if (!query || query.length < this.minCharsFilter) {
      return this.options;
    }
    return this.options.filter(
      o =>
        o.label.toLowerCase().includes(query) ||
        (o.secondary && o.secondary.toLowerCase().includes(query))
    );
  });

  // ── TrackBy ─────────────────────────────────────────────────────
  trackByFn(_index: number, option: SearchableOption): any {
    return option.value;
  }

  // ── Open / Close ────────────────────────────────────────────────
  toggleOpen(): void {
    if (this.isOpen()) {
      this.close();
    } else {
      this.open();
    }
  }

  open(): void {
    this.isOpen.set(true);
    this.searchQuery.set('');
    this.highlightedIndex.set(0);
    this.opened.emit();
  }

  close(): void {
    this.isOpen.set(false);
    this.searchQuery.set('');
    this.debounceTimer = null;
    this.closed.emit();
  }

  // ── Search with debounce ────────────────────────────────────────
  onSearch(query: string): void {
    if (this.debounceTimer) clearTimeout(this.debounceTimer);
    this.debounceTimer = setTimeout(() => {
      this.searchQuery.set(query);
      this.highlightedIndex.set(0);
    }, 150);
  }

  // ── Selection ───────────────────────────────────────────────────
  isSelected(value: any): boolean {
    if (this.multiple) {
      const arr = Array.isArray(this.value) ? this.value : [];
      return arr.includes(value);
    }
    return this.value === value;
  }

  selectOption(option: SearchableOption): void {
    if (option.disabled) return;

    if (this.multiple) {
      const current = Array.isArray(this.value) ? [...this.value] : [];
      const idx = current.indexOf(option.value);
      if (idx >= 0) {
        current.splice(idx, 1);
      } else {
        current.push(option.value);
      }
      this.value = current;
      this.valueChange.emit(current);
      // Keep dropdown open for multiple selection
    } else {
      this.value = option.value;
      this.valueChange.emit(option.value);
      this.close();
    }
  }

  clearSelection(event: MouseEvent): void {
    event.stopPropagation();
    if (this.multiple) {
      this.value = [];
      this.valueChange.emit([]);
    } else {
      this.value = null;
      this.valueChange.emit(null);
    }
    this.searchQuery.set('');
    this.close();
  }

  // ── Keyboard navigation ─────────────────────────────────────────
  onKeydown(event: KeyboardEvent): void {
    const opts = this.filteredOptions();

    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault();
        this.highlightedIndex.update(i => Math.min(i + 1, opts.length - 1));
        this.scrollToHighlighted();
        break;
      case 'ArrowUp':
        event.preventDefault();
        this.highlightedIndex.update(i => Math.max(i - 1, 0));
        this.scrollToHighlighted();
        break;
      case 'Enter':
        event.preventDefault();
        if (opts[this.highlightedIndex()]) {
          this.selectOption(opts[this.highlightedIndex()]);
        }
        break;
      case 'Escape':
        event.preventDefault();
        this.close();
        break;
    }
  }

  // ── Click outside ───────────────────────────────────────────────
  @HostListener('document:click', ['$event'])
  onClickOutside(event: MouseEvent): void {
    const target = event.target as HTMLElement;
    if (this.isOpen() && !target.closest('.searchable-select')) {
      this.close();
    }
  }

  // ── Scroll highlighted option into view ─────────────────────────
  private scrollToHighlighted(): void {
    requestAnimationFrame(() => {
      const container = document.querySelector('.searchable-select.is-open .options-container');
      if (!container) return;
      const highlighted = container.querySelector('.option-item.highlighted');
      if (highlighted) {
        highlighted.scrollIntoView({ block: 'nearest' });
      }
    });
  }
}
