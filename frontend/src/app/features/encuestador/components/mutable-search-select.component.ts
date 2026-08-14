import { Component, Input, Output, EventEmitter, ElementRef, HostListener, OnInit, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

const ACCENT_DICT: Record<string, string> = {
  // Especialidades
  'pediatria': 'Pediatría',
  'ginecologia': 'Ginecología',
  'cardiologia': 'Cardiología',
  'traumatologia': 'Traumatología',
  'oftalmologia': 'Oftalmología',
  'urologia': 'Urología',
  'gastroenterologia': 'Gastroenterología',
  'neumonologia': 'Neumonología',
  'neumologia': 'Neumología',
  'dermatologia': 'Dermatología',
  'psiquiatria': 'Psiquiatría',
  'otorrinolaringologia': 'Otorrinolaringología',
  'medicina interna': 'Medicina Interna',
  'medicina general': 'Medicina General',
  'cirugia': 'Cirugía',
  'anestesiologia': 'Anestesiología',
  'nefrologia': 'Nefrología',
  'neurologia': 'Neurología',
  'oncologia': 'Oncología',
  'fisiatria': 'Fisiatría',
  'obstetricia': 'Obstetricia',
  'odontologia': 'Odontología',
  'endocrinologia': 'Endocrinología',
  'reumatologia': 'Reumatología',
  'hematologia': 'Hematología',
  'infectologia': 'Infectología',
  'psicologo': 'Psicólogo',
  'psicologia': 'Psicología',

  // Sub-especialidades
  'cardiologia pediatrica': 'Cardiología Pediátrica',
  'cirugia cardiovascular': 'Cirugía Cardiovascular',
  'cirugia pediatrica': 'Cirugía Pediátrica',
  'cirugia plastica': 'Cirugía Plástica y Reconstructiva',
  'cirugia oncológica': 'Cirugía Oncológica',
  'ecografia': 'Ecografía Integral',
  'ecografia integral': 'Ecografía Integral',
  'electrofisiologia': 'Electrofisiología',
  'endocrinologia pediatrica': 'Endocrinología Pediátrica',
  'gastroenterologia pediatrica': 'Gastroenterología Pediátrica',
  'ginecologia infanto juvenil': 'Ginecología Infanto-Juvenil',
  'hematologia pediatrica': 'Hematología Pediátrica',
  'infectologia pediatrica': 'Infectología Pediátrica',
  'mastologia': 'Mastología',
  'medicina critica': 'Medicina Crítica y Cuidado Intensivo',
  'nefrologia pediatrica': 'Nefrología Pediátrica',
  'neonatologia': 'Neonatología',
  'neumonologia pediatrica': 'Neumonología Pediátrica',
  'neurocirugia': 'Neurocirugía',
  'neurologia pediatrica': 'Neurología Pediátrica',
  'nutricion clinica': 'Nutrición Clínica',
  'odontopediatria': 'Odontopediatría',
  'oftalmologia pediatrica': 'Oftalmología Pediátrica',
  'oncologia medica': 'Oncología Médica',
  'ortodoncia': 'Ortodoncia',
  'periodoncia': 'Periodoncia',
  'perinatologia': 'Perinatología',
  'psiquiatria infantil': 'Psiquiatría Infantil',
  'radiologia': 'Radiología e Imagenología',
  'reproduccion humana': 'Reproducción Humana',
  'reumatologia pediatrica': 'Reumatología Pediátrica',

  // Universidades (siglas y nombres)
  'ucv': 'Universidad Central de Venezuela (UCV)',
  'ula': 'Universidad de Los Andes (ULA)',
  'luz': 'Universidad del Zulia (LUZ)',
  'uc': 'Universidad de Carabobo (UC)',
  'udo': 'Universidad de Oriente (UDO)',
  'ucla': 'Universidad Centroccidental Lisandro Alvarado (UCLA)',
  'unefm': 'Universidad Nacional Experimental Francisco de Miranda (UNEFM)',
  'unerg': 'Universidad Nacional Experimental Rómulo Gallegos (UNERG)',
  'ucab': 'Universidad Católica Andrés Bello (UCAB)',
  'usm': 'Universidad Santa María (USM)',
  'elam': 'Escuela Latinoamericana de Medicina (ELAM)',
  'unellez': 'Universidad Nacional Experimental de los Llanos Ezequiel Zamora (UNELLEZ)',
  'unet': 'Universidad del Táchira (UNET)',
  'urbe': 'Universidad Rafael Belloso Chacín (URBE)',
  'unimet': 'Universidad Metropolitana (UNIMET)',
  'universidad central de venezuela': 'Universidad Central de Venezuela (UCV)',
  'universidad de los andes': 'Universidad de Los Andes (ULA)',
  'universidad del zulia': 'Universidad del Zulia (LUZ)',
  'universidad de carabobo': 'Universidad de Carabobo (UC)',
  'universidad de oriente': 'Universidad de Oriente (UDO)',
  'universidad catolica andres bello': 'Universidad Católica Andrés Bello (UCAB)',
  'universidad santa maria': 'Universidad Santa María (USM)',

  // Estados
  'anzoategui': 'Anzoátegui',
  'apure': 'Apure',
  'aragua': 'Aragua',
  'barinas': 'Barinas',
  'bolivar': 'Bolívar',
  'carabobo': 'Carabobo',
  'cojedes': 'Cojedes',
  'delta amacuro': 'Delta Amacuro',
  'falcon': 'Falcón',
  'guarico': 'Guárico',
  'lara': 'Lara',
  'merida': 'Mérida',
  'miranda': 'Miranda',
  'monagas': 'Monagas',
  'nueva esparta': 'Nueva Esparta',
  'portuguesa': 'Portuguesa',
  'sucre': 'Sucre',
  'tachira': 'Táchira',
  'trujillo': 'Trujillo',
  'vargas': 'Vargas',
  'yaracuy': 'Yaracuy',
  'zulia': 'Zulia',
  'distrito capital': 'Distrito Capital',
  'dependencias federales': 'Dependencias Federales',

  // Ciudades
  'caracas': 'Caracas',
  'maracaibo': 'Maracaibo',
  'valencia': 'Valencia',
  'barquisimeto': 'Barquisimeto',
  'maracay': 'Maracay',
  'ciudad guayana': 'Ciudad Guayana',
  'barcelona': 'Barcelona',
  'maturin': 'Maturín',
  'tucupita': 'Tucupita',
  'san cristobal': 'San Cristóbal',
  'san felipe': 'San Felipe',
  'san fernando de apure': 'San Fernando de Apure',
  'san juan de los morros': 'San Juan de los Morros',
  'la guaira': 'La Guaira',
  'los teques': 'Los Teques',
  'guanare': 'Guanare',
  'san carlos': 'San Carlos',
  'el tigre': 'El Tigre',
  'cabimas': 'Cabimas',
  'ciudad ojeda': 'Ciudad Ojeda',
  'puerto la cruz': 'Puerto La Cruz',
  'guarenas': 'Guarenas',
  'guatire': 'Guatire',
  'carupano': 'Carúpano',
  'coro': 'Coro',
  'punto fijo': 'Punto Fijo'
};

@Component({
  selector: 'app-mutable-search-select',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="relative w-full">
      <label *ngIf="label" class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">
        {{ label }} <span class="text-red-500">*</span>
      </label>
      
      <!-- Select Input Box -->
      <div class="relative flex items-center">
        <input
          type="text"
          [placeholder]="placeholder || 'Seleccione...'"
          [(ngModel)]="searchQuery"
          (focus)="onFocus()"
          (input)="onInput()"
          [disabled]="disabled"
          class="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg pl-3 pr-10 py-2.5 text-sm text-slate-800 dark:text-white focus:border-indigo-500 transition-colors outline-none disabled:opacity-60 disabled:bg-gray-100 dark:disabled:bg-slate-800/50"
        />
        <span class="material-icons absolute right-3 text-slate-400 pointer-events-none select-none">
          {{ isOpen ? 'arrow_drop_up' : 'arrow_drop_down' }}
        </span>
      </div>

      <!-- Dropdown Options List -->
      <div
        *ngIf="isOpen && !disabled"
        class="absolute z-50 w-full mt-1 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-lg shadow-2xl max-h-60 overflow-y-auto custom-scrollbar"
      >
        <!-- Filtered Options -->
        <div
          *ngFor="let opt of filteredOptions"
          (click)="selectOption(opt)"
          class="px-4 py-2 text-sm text-slate-700 dark:text-slate-200 hover:bg-indigo-50 dark:hover:bg-indigo-950/40 hover:text-indigo-600 dark:hover:text-indigo-400 cursor-pointer font-medium transition-colors"
        >
          {{ opt }}
        </div>

        <!-- Add New Button -->
        <div
          *ngIf="showAddNewOption"
          (click)="openAddModal()"
          class="px-4 py-2.5 text-sm font-bold text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-950/50 cursor-pointer border-t border-gray-100 dark:border-slate-800 flex items-center gap-1.5 transition-colors"
        >
          <span class="material-icons text-sm">add_circle_outline</span>
          Agregar nuevo "{{ searchQuery }}"
        </div>

        <!-- Empty State -->
        <div *ngIf="filteredOptions.length === 0 && !searchQuery" class="px-4 py-3 text-xs text-slate-400 text-center">
          No hay opciones disponibles. Escribe para agregar una nueva.
        </div>
      </div>

      <!-- confirmation Modal Overlay -->
      <div
        *ngIf="showModal"
        class="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-[99999] flex items-center justify-center p-4 animate-in fade-in duration-200"
      >
        <div
          class="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 shadow-2xl rounded-2xl p-6 max-w-md w-full text-slate-800 dark:text-white animate-in zoom-in-95 duration-200"
        >
          <!-- Modal Header -->
          <h3 class="text-xl font-bold mb-3 flex items-center gap-2 text-indigo-600 dark:text-indigo-400">
            <span class="material-icons">add_box</span> Agregar nuevo elemento
          </h3>
          
          <p class="text-sm text-slate-600 dark:text-slate-300 mb-4">
            ¿Deseas agregar <span class="font-bold text-slate-800 dark:text-white">"{{ pendingValue }}"</span> al catálogo de <span class="font-semibold text-indigo-500 capitalize">{{ tipo }}</span>?
          </p>

          <!-- Autocomplete Suggestion Banner -->
          <div
            *ngIf="suggestion"
            class="mb-5 p-4 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900/60"
          >
            <div class="flex gap-2 text-amber-800 dark:text-amber-300 font-bold text-xs uppercase tracking-wider mb-1">
              <span class="material-icons text-sm">tips_and_updates</span> Sugerencia de Acentuación
            </div>
            <p class="text-sm text-slate-700 dark:text-slate-200 mb-3">
              Detectamos que se escribe con tildes/mayúsculas correctas como:
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
export class MutableSearchSelectComponent implements OnInit, OnChanges {
  @Input() label: string = '';
  @Input() options: string[] = [];
  @Input() placeholder: string = '';
  @Input() value: string = '';
  @Input() disabled: boolean = false;
  @Input() tipo: 'especialidad' | 'subespecialidad' | 'universidad' | 'estado' | 'ciudad' = 'especialidad';

  @Output() valueChange = new EventEmitter<string>();
  @Output() addNew = new EventEmitter<{ tipo: 'especialidad' | 'subespecialidad' | 'universidad' | 'estado' | 'ciudad', value: string }>();

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
      // Resetear si no se seleccionó ninguna opción válida
      if (this.searchQuery !== this.value) {
        this.searchQuery = this.value || '';
      }
    }
  }

  onFocus() {
    if (!this.disabled) {
      this.isOpen = true;
    }
  }

  onInput() {
    this.isOpen = true;
    if (!this.searchQuery) {
      this.value = '';
      this.valueChange.emit('');
    }
  }

  get filteredOptions(): string[] {
    if (!this.searchQuery) return this.options;
    const normQuery = this.normalize(this.searchQuery);
    return this.options.filter(opt => this.normalize(opt).includes(normQuery));
  }

  get showAddNewOption(): boolean {
    if (!this.searchQuery) return false;
    const queryNorm = this.normalize(this.searchQuery);
    return !this.options.some(opt => this.normalize(opt) === queryNorm);
  }

  selectOption(opt: string) {
    this.value = opt;
    this.searchQuery = opt;
    this.valueChange.emit(opt);
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
    this.searchQuery = this.value || '';
  }

  confirmAdd(finalValue: string) {
    const formatted = finalValue.trim();
    if (formatted) {
      this.value = formatted;
      this.searchQuery = formatted;
      this.valueChange.emit(formatted);
      this.addNew.emit({ tipo: this.tipo, value: formatted });
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

    if (ACCENT_DICT[normInput]) {
      return ACCENT_DICT[normInput];
    }

    const matchingOption = this.options.find(opt => this.normalize(opt) === normInput);
    if (matchingOption && matchingOption !== input) {
      return matchingOption;
    }

    // Sugerencia de formato Capitalizado si fue escrito todo en minúsculas
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
