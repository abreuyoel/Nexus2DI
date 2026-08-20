import { Component, Input, Output, EventEmitter, ElementRef, HostListener, OnInit, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

export interface ConsultorioExistente {
  nombre_clinica: string;
  direccion_especifica?: string;
  piso_consultorio?: string;
  valor_consulta_rango?: string;
  promedio_pacientes_semanal_rango?: string;
}

@Component({
  selector: 'app-consultorio-search-select',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="relative w-full">
      <label *ngIf="label" class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">
        {{ label }} <span *ngIf="required" class="text-red-500">*</span>
      </label>

      <!-- Select Input Box -->
      <div class="relative flex items-center">
        <span class="material-icons absolute left-3 text-slate-400 pointer-events-none select-none !text-lg">domain</span>
        <input
          type="text"
          [placeholder]="placeholder || 'Buscar o ingresar consultorio/clínica...'"
          [(ngModel)]="searchQuery"
          (focus)="onFocus()"
          (input)="onInput()"
          [disabled]="disabled"
          class="w-full bg-white dark:bg-slate-900 border border-gray-300 dark:border-slate-700 rounded-lg pl-9 pr-10 py-2.5 text-sm text-slate-800 dark:text-white focus:border-indigo-500 transition-colors outline-none disabled:opacity-60 disabled:bg-gray-100 dark:disabled:bg-slate-800/50"
        />
        <span class="material-icons absolute right-3 text-slate-400 pointer-events-none select-none">
          {{ isOpen ? 'arrow_drop_up' : 'arrow_drop_down' }}
        </span>
      </div>

      <!-- Dropdown Options List -->
      <div
        *ngIf="isOpen && !disabled"
        class="absolute z-50 w-full mt-1 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-lg shadow-2xl max-h-64 overflow-y-auto custom-scrollbar"
      >
        <!-- Filtered Options -->
        <div
          *ngFor="let opt of filteredOptions"
          (click)="selectOption(opt)"
          class="px-4 py-2.5 hover:bg-indigo-50 dark:hover:bg-indigo-950/40 cursor-pointer border-b border-gray-100 dark:border-slate-800/60 last:border-0 transition-colors"
        >
          <div class="font-bold text-sm text-slate-800 dark:text-white flex items-center gap-1.5">
            <span class="material-icons text-indigo-500 text-sm">local_hospital</span>
            {{ opt.nombre_clinica }}
          </div>
          <div *ngIf="opt.direccion_especifica || opt.piso_consultorio" class="text-xs text-slate-500 dark:text-slate-400 mt-0.5 pl-5 truncate">
            <span *ngIf="opt.piso_consultorio" class="font-semibold">{{ opt.piso_consultorio }} — </span>
            <span>{{ opt.direccion_especifica }}</span>
          </div>
        </div>

        <!-- Add New Button -->
        <div
          *ngIf="showAddNewOption"
          (click)="openAddModal()"
          class="px-4 py-2.5 text-sm font-bold text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-950/50 cursor-pointer border-t border-gray-100 dark:border-slate-800 flex items-center gap-1.5 transition-colors"
        >
          <span class="material-icons text-sm">add_circle_outline</span>
          Agregar nuevo consultorio "{{ searchQuery }}"
        </div>

        <!-- Empty State -->
        <div *ngIf="filteredOptions.length === 0 && !searchQuery" class="px-4 py-3 text-xs text-slate-400 text-center">
          No hay consultorios registrados. Escribe para ingresar uno nuevo.
        </div>
      </div>

      <!-- Confirmation Modal Overlay -->
      <div
        *ngIf="showModal"
        class="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-[99999] flex items-center justify-center p-4 animate-in fade-in duration-200"
      >
        <div
          class="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 shadow-2xl rounded-2xl p-6 max-w-md w-full text-slate-800 dark:text-white animate-in zoom-in-95 duration-200"
        >
          <!-- Modal Header -->
          <h3 class="text-xl font-bold mb-3 flex items-center gap-2 text-indigo-600 dark:text-indigo-400">
            <span class="material-icons">add_business</span> Agregar nuevo consultorio
          </h3>
          
          <p class="text-sm text-slate-600 dark:text-slate-300 mb-4">
            ¿Deseas registrar <span class="font-bold text-slate-800 dark:text-white">"{{ pendingValue }}"</span> en el catálogo de consultorios?
          </p>

          <!-- Autocomplete Suggestion Banner -->
          <div
            *ngIf="suggestion"
            class="mb-5 p-4 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900/60"
          >
            <div class="flex gap-2 text-amber-800 dark:text-amber-300 font-bold text-xs uppercase tracking-wider mb-1">
              <span class="material-icons text-sm">tips_and_updates</span> Sugerencia de formato
            </div>
            <p class="text-sm text-slate-700 dark:text-slate-200 mb-3">
              Detectamos que se escribe como:
              <span class="font-black text-indigo-600 dark:text-indigo-400 text-base">"{{ suggestion }}"</span>
            </p>
            <button
              type="button"
              (click)="confirmAdd(suggestion)"
              class="w-full bg-amber-500 hover:bg-amber-600 dark:bg-amber-600 dark:hover:bg-amber-700 text-white font-bold text-sm py-2.5 rounded-lg transition-colors flex items-center justify-center gap-1.5"
            >
              <span class="material-icons text-sm">done</span> Sí, guardar como "{{ suggestion }}"
            </button>
          </div>

          <!-- Buttons -->
          <div class="flex gap-3 justify-end">
            <button
              type="button"
              (click)="closeModal()"
              class="px-4 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-750 text-slate-600 dark:text-slate-300 font-semibold text-sm transition-colors"
            >
              Cancelar
            </button>
            <button
              type="button"
              (click)="confirmAdd(pendingValue)"
              class="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-sm transition-colors shadow-lg shadow-indigo-600/20"
            >
              Sí, guardar original
            </button>
          </div>
        </div>
      </div>
    </div>
  `
})
export class ConsultorioSearchSelectComponent implements OnInit, OnChanges {
  @Input() label: string = 'Nombre de la Clínica/Centro';
  @Input() options: ConsultorioExistente[] = [];
  @Input() placeholder: string = 'Buscar o ingresar consultorio/clínica...';
  @Input() value: string = '';
  @Input() disabled: boolean = false;
  @Input() required: boolean = true;

  @Output() valueChange = new EventEmitter<string>();
  @Output() selectConsultorio = new EventEmitter<ConsultorioExistente>();
  @Output() addNew = new EventEmitter<string>();

  searchQuery: string = '';
  isOpen: boolean = false;
  showModal: boolean = false;
  pendingValue: string = '';
  suggestion: string | null = null;

  constructor(private elementRef: ElementRef) {}

  ngOnInit() {
    this.searchQuery = this.value || '';
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes['value']) {
      this.searchQuery = this.value || '';
    }
  }

  @HostListener('document:click', ['$event'])
  onClickOutside(event: Event) {
    if (!this.elementRef.nativeElement.contains(event.target)) {
      this.isOpen = false;
    }
  }

  onFocus() {
    if (!this.disabled) {
      this.isOpen = true;
    }
  }

  onInput() {
    this.isOpen = true;
    this.value = this.searchQuery;
    this.valueChange.emit(this.searchQuery);
  }

  get filteredOptions(): ConsultorioExistente[] {
    if (!this.searchQuery) return this.options;
    const normQuery = this.normalize(this.searchQuery);
    return this.options.filter(opt =>
      this.normalize(opt.nombre_clinica).includes(normQuery) ||
      this.normalize(opt.direccion_especifica || '').includes(normQuery)
    );
  }

  get showAddNewOption(): boolean {
    if (!this.searchQuery.trim()) return false;
    const queryNorm = this.normalize(this.searchQuery.trim());
    return !this.options.some(opt => this.normalize(opt.nombre_clinica) === queryNorm);
  }

  selectOption(opt: ConsultorioExistente) {
    this.value = opt.nombre_clinica;
    this.searchQuery = opt.nombre_clinica;
    this.valueChange.emit(opt.nombre_clinica);
    this.selectConsultorio.emit(opt);
    this.isOpen = false;
  }

  openAddModal() {
    this.pendingValue = this.searchQuery.trim();
    if (!this.pendingValue) return;

    this.isOpen = false;
    this.suggestion = this.findSuggestion(this.pendingValue);
    this.showModal = true;
  }

  closeModal() {
    this.showModal = false;
  }

  confirmAdd(finalValue: string) {
    const formatted = finalValue.trim();
    if (formatted) {
      this.value = formatted;
      this.searchQuery = formatted;
      this.valueChange.emit(formatted);
      const newConsultorioObj: ConsultorioExistente = {
        nombre_clinica: formatted,
        direccion_especifica: '',
        piso_consultorio: '',
        valor_consulta_rango: '',
        promedio_pacientes_semanal_rango: ''
      };
      this.selectConsultorio.emit(newConsultorioObj);
      this.addNew.emit(formatted);
    }
    this.showModal = false;
  }

  private normalize(str: string): string {
    return (str || '')
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '');
  }

  private findSuggestion(input: string): string | null {
    const normInput = this.normalize(input);
    const matchingOption = this.options.find(opt => this.normalize(opt.nombre_clinica) === normInput);
    if (matchingOption && matchingOption.nombre_clinica !== input) {
      return matchingOption.nombre_clinica;
    }

    if (input === input.toLowerCase() && input.length > 2) {
      const titleCased = input
        .split(' ')
        .map(w => w ? w.charAt(0).toUpperCase() + w.slice(1) : '')
        .join(' ');
      if (titleCased !== input) {
        return titleCased;
      }
    }

    return null;
  }
}
