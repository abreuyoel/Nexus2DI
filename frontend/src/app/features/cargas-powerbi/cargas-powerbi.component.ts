import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ApiService } from '../../core/services/api.service';

import { SearchableSelectComponent, SelectOption } from '../client-visits/searchable-select.component';

export interface PowerBiItem {
  id_dashboard: number;
  id_cliente: number;
  cliente_nombre?: string;
  nombre?: string;
  url_html: string;
  tipo?: string;
  fecha_creacion?: string;
  activo: boolean;
  es_principal?: boolean;
}

export interface ClientPowerBiSummary {
  id_cliente: number;
  cliente: string;
  total_powerbi: number;
  powerbis: PowerBiItem[];
}

@Component({
  selector: 'app-cargas-powerbi',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    SearchableSelectComponent,
  ],
  templateUrl: './cargas-powerbi.component.html',
  styleUrls: ['./cargas-powerbi.component.scss'],
})
export class CargasPowerbiComponent implements OnInit {
  Math = Math;
  loading = signal<boolean>(true);
  saving = signal<boolean>(false);

  // Datos
  clientsSummary = signal<ClientPowerBiSummary[]>([]);
  searchQuery = signal<string>('');
  filterStatus = signal<'all' | 'with' | 'without'>('all');

  // Modal / Selección de cliente
  selectedClient = signal<ClientPowerBiSummary | null>(null);
  
  // Viewer Modal (Ver Reporte)
  activeViewerReport = signal<PowerBiItem | null>(null);
  sanitizedViewerUrl = signal<SafeHtml | null>(null);

  // Form Modal (Crear / Editar)
  showFormModal = signal<boolean>(false);
  editingItem = signal<PowerBiItem | null>(null);
  
  // Form fields
  formClientId = signal<number | null>(null);
  formNombre = signal<string>('');
  formUrlHtml = signal<string>('');
  formLiveSanitized = signal<SafeHtml | null>(null);

  clientOptions = computed<SelectOption[]>(() =>
    this.clientsSummary().map((c) => ({
      value: String(c.id_cliente),
      label: c.cliente,
    }))
  );

  formClientIdStr = computed(() =>
    this.formClientId() ? String(this.formClientId()) : ''
  );

  onClientSelect(val: string): void {
    this.formClientId.set(val ? Number(val) : null);
  }

  // Paginación
  currentPage = signal<number>(1);
  pageSize = signal<number>(12);

  // Filtro computado de clientes
  filteredClients = computed(() => {
    const q = this.searchQuery().trim().toLowerCase();
    const status = this.filterStatus();
    let list = this.clientsSummary();

    if (status === 'with') {
      list = list.filter((c) => c.total_powerbi > 0);
    } else if (status === 'without') {
      list = list.filter((c) => c.total_powerbi === 0);
    }

    if (!q) return list;

    return list.filter((c) => c.cliente.toLowerCase().includes(q));
  });

  totalPages = computed(() => Math.ceil(this.filteredClients().length / this.pageSize()) || 1);

  paginatedClients = computed(() => {
    const page = this.currentPage();
    const size = this.pageSize();
    const start = (page - 1) * size;
    return this.filteredClients().slice(start, start + size);
  });

  setPage(page: number): void {
    if (page >= 1 && page <= this.totalPages()) {
      this.currentPage.set(page);
    }
  }

  changePageSize(size: number): void {
    this.pageSize.set(size);
    this.currentPage.set(1);
  }

  constructor(
    private api: ApiService,
    private sanitizer: DomSanitizer,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.loadData();
  }

  loadData(): void {
    this.loading.set(true);
    this.api.getPowerBiSummary().subscribe({
      next: (data) => {
        this.clientsSummary.set(data || []);
        this.loading.set(false);
        // Si hay un cliente seleccionado, actualizar su referencia
        if (this.selectedClient()) {
          const updated = data.find(c => c.id_cliente === this.selectedClient()?.id_cliente);
          if (updated) this.selectedClient.set(updated);
        }
      },
      error: (err) => {
        console.error('Error al cargar cargas de Power BI:', err);
        this.snackBar.open('Error al cargar la información de Power BI', 'Cerrar', { duration: 4000 });
        this.loading.set(false);
      },
    });
  }

  // --- ACCIONES DE CLIENTE Y REPORTES ---
  openClientDetail(client: ClientPowerBiSummary): void {
    this.selectedClient.set(client);
  }

  closeClientDetail(): void {
    this.selectedClient.set(null);
  }

  // Formateador de iframe para forzar 100% de alto y ancho en el visor
  formatIframeHtml(val: string): string {
    if (!val || !val.trim()) return '';
    let content = val.trim();
    if (content.startsWith('http://') || content.startsWith('https://')) {
      return `<iframe src="${content}" frameborder="0" allowFullScreen="true" style="width:100% !important; height:100% !important; min-height:80vh; border:0;" class="w-full h-full border-0 rounded-xl"></iframe>`;
    }
    if (content.includes('<iframe')) {
      content = content.replace(/\bwidth=["'][^"']*["']/gi, 'width="100%"');
      content = content.replace(/\bheight=["'][^"']*["']/gi, 'height="100%"');
      if (content.includes('style=')) {
        content = content.replace(/style=["']([^"']*)["']/gi, 'style="$1; width: 100% !important; height: 100% !important; min-height: 80vh;"');
      } else {
        content = content.replace(/<iframe/gi, '<iframe style="width: 100% !important; height: 100% !important; min-height: 80vh; border: 0;"');
      }
    }
    return content;
  }

  // Visualizar Power BI (Al tocar un reporte)
  viewReport(report: PowerBiItem): void {
    this.activeViewerReport.set(report);
    const htmlContent = this.formatIframeHtml(report.url_html);
    this.sanitizedViewerUrl.set(this.sanitizer.bypassSecurityTrustHtml(htmlContent));
  }

  closeViewer(): void {
    this.activeViewerReport.set(null);
    this.sanitizedViewerUrl.set(null);
  }

  // Establecer reporte como principal / activo por defecto para el cliente
  setAsPrincipal(item: PowerBiItem): void {
    this.api.put<PowerBiItem>(`/api/cargas-powerbi/${item.id_dashboard}/set-principal`, {}).subscribe({
      next: () => {
        this.snackBar.open(`Reporte "${item.nombre || 'Power BI'}" activado como principal`, 'OK', { duration: 3000 });
        this.loadData();
        // Actualizar item en el cliente seleccionado si el drawer está abierto
        if (this.selectedClient()) {
          const updated = this.selectedClient()!.powerbis.map(p => ({
            ...p,
            es_principal: p.id_dashboard === item.id_dashboard
          }));
          this.selectedClient.set({
            ...this.selectedClient()!,
            powerbis: updated
          });
        }
      },
      error: (err) => {
        console.error(err);
        this.snackBar.open('Error al establecer reporte como principal', 'Cerrar', { duration: 4000 });
      }
    });
  }

  // Modal de Formulario (Crear / Editar)
  openCreateModal(clientId?: number): void {
    this.editingItem.set(null);
    this.formClientId.set(clientId || (this.selectedClient()?.id_cliente || null));
    this.formNombre.set('Power BI');
    this.formUrlHtml.set('');
    this.formLiveSanitized.set(null);
    this.showFormModal.set(true);
  }

  openEditModal(item: PowerBiItem): void {
    this.editingItem.set(item);
    this.formClientId.set(item.id_cliente);
    this.formNombre.set(item.nombre || 'Power BI');
    this.formUrlHtml.set(item.url_html);
    this.updateLivePreview(item.url_html);
    this.showFormModal.set(true);
  }

  closeFormModal(): void {
    this.showFormModal.set(false);
    this.editingItem.set(null);
  }

  updateLivePreview(val: string): void {
    if (!val || !val.trim()) {
      this.formLiveSanitized.set(null);
      return;
    }
    const htmlContent = this.formatIframeHtml(val);
    this.formLiveSanitized.set(this.sanitizer.bypassSecurityTrustHtml(htmlContent));
  }

  savePowerBi(): void {
    const cid = this.formClientId();
    const url = this.formUrlHtml().trim();
    const nombre = this.formNombre().trim();

    if (!cid) {
      this.snackBar.open('Por favor selecciona un cliente', 'Entendido', { duration: 3000 });
      return;
    }
    if (!url) {
      this.snackBar.open('El código o URL de Power BI es requerido', 'Entendido', { duration: 3000 });
      return;
    }

    this.saving.set(true);

    if (this.editingItem()) {
      // Actualizar
      const id = this.editingItem()!.id_dashboard;
      this.api.updatePowerBi(id, { nombre, url_html: url }).subscribe({
        next: () => {
          this.snackBar.open('Power BI actualizado exitosamente', 'OK', { duration: 3000 });
          this.saving.set(false);
          this.closeFormModal();
          this.loadData();
        },
        error: (err) => {
          console.error(err);
          this.snackBar.open('Error al actualizar Power BI', 'Cerrar', { duration: 4000 });
          this.saving.set(false);
        },
      });
    } else {
      // Crear
      this.api.createPowerBi({ id_cliente: cid, nombre, url_html: url }).subscribe({
        next: () => {
          this.snackBar.open('Power BI cargado exitosamente', 'OK', { duration: 3000 });
          this.saving.set(false);
          this.closeFormModal();
          this.loadData();
        },
        error: (err) => {
          console.error(err);
          this.snackBar.open('Error al guardar Power BI', 'Cerrar', { duration: 4000 });
          this.saving.set(false);
        },
      });
    }
  }

  deletePowerBi(item: PowerBiItem, event: Event): void {
    event.stopPropagation();
    if (!confirm(`¿Estás seguro de eliminar "${item.nombre || 'este Power BI'}"?`)) {
      return;
    }

    this.api.deletePowerBi(item.id_dashboard).subscribe({
      next: () => {
        this.snackBar.open('Power BI eliminado', 'OK', { duration: 3000 });
        this.loadData();
      },
      error: (err) => {
        console.error(err);
        this.snackBar.open('Error al eliminar Power BI', 'Cerrar', { duration: 4000 });
      },
    });
  }
}
