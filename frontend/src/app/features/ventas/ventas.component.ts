import { Component, OnInit, signal, inject, viewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterLink } from '@angular/router';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/services/auth.service';
import { VentasOfflineQueueService } from './services/ventas-offline-queue.service';
import { ConfirmService } from '../../shared/components/confirm-dialog/confirm.service';

type Pdv = { identificador: string; nombre: string; direccion: string; ciudad: string; localidad: string };
type Cli = { id_cliente: number; nombre: string };
type ProductoCatalogo = {
  id_catalogo: number; id_producto: number; nombre: string; categoria: string; marca: string;
  precio_unitario: number; unidades_por_caja: number | null; presentacion_venta: string;
  foto_url: string | null; codigo_barras: string | null; descuento_max_pct: number;
  stock_disponible: number | null;
};
type ItemCarrito = { id_producto: number; nombre: string; precio_unitario: number; cantidad: number; descuento_pct: number; stock_disponible: number | null };
type ProductoOcrPropuesto = {
  nombre_texto: string; cantidad: number;
  match: { id_producto: number; nombre: string; precio_unitario: number; similaridad: number } | null;
  incluido?: boolean;
};

@Component({
  selector: 'app-ventas',
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule, MatSnackBarModule, MatProgressSpinnerModule, MatTooltipModule, RouterLink],
  template: `
<div class="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-800 dark:text-white">
  <!-- HEADER -->
  <div class="bg-white dark:bg-gradient-to-r dark:from-slate-900 dark:to-slate-800 border-b border-slate-200 dark:border-white/8 px-6 py-5">
    <div class="flex items-center gap-3">
      <div class="w-11 h-11 rounded-2xl bg-gradient-to-br from-emerald-600 to-teal-700 flex items-center justify-center shadow-lg">
        <mat-icon class="text-white">point_of_sale</mat-icon>
      </div>
      <div class="flex-1 min-w-0">
        <h1 class="text-xl font-black tracking-tight leading-none text-slate-800 dark:text-white">Ventas</h1>
        <p class="text-slate-500 dark:text-slate-400 text-xs mt-0.5">{{ crumb() || cedula }}</p>
      </div>
      <div class="flex items-center gap-2 shrink-0">
        <a routerLink="/ventas-dashboard" class="w-9 h-9 flex items-center justify-center rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-white" title="Dashboard de ventas">
          <mat-icon class="!text-base">bar_chart</mat-icon>
        </a>
        <span class="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-wider px-2 py-1 rounded-full"
              [ngClass]="isOnline() ? 'bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-400' : 'bg-red-100 dark:bg-red-950 text-red-700 dark:text-red-400'">
          <span class="w-1.5 h-1.5 rounded-full" [ngClass]="isOnline() ? 'bg-emerald-500 dark:bg-emerald-400' : 'bg-red-500 dark:bg-red-400'"></span>
          {{ isOnline() ? 'En línea' : 'Sin conexión' }}
        </span>
        @if (pendingSync() > 0) {
          <button (click)="sincronizar()" class="flex items-center gap-1 text-[10px] font-black uppercase tracking-wider px-2 py-1 rounded-full bg-amber-100 dark:bg-amber-950 text-amber-700 dark:text-amber-400" [disabled]="!isOnline()">
            <mat-icon class="!text-sm">sync</mat-icon>{{ pendingSync() }} pendientes
          </button>
        }
      </div>
    </div>
    @if (syncError()) {
      <div class="mt-3 bg-red-50 dark:bg-red-950/60 border border-red-200 dark:border-red-900 rounded-xl px-3 py-2 flex items-center justify-between gap-2">
        <span class="text-xs text-red-700 dark:text-red-300 font-semibold">No se pudo sincronizar: {{ syncError() }}</span>
        <button (click)="sincronizar()" class="text-[10px] font-black uppercase px-2 py-1 rounded-lg bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-200">Reintentar</button>
      </div>
    }
  </div>

  <div class="px-6 py-6 max-w-3xl mx-auto pb-32">
    @if (loading()) {
      <div class="flex justify-center py-24"><mat-spinner diameter="40"></mat-spinner></div>
    } @else if (!jornadaActiva()) {

    <!-- SIN JORNADA -->
    <div class="relative overflow-hidden bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/8 rounded-2xl p-8 text-center mt-8 shadow-sm">
      <div class="absolute top-0 left-0 w-full h-0.5 bg-gradient-to-r from-emerald-500 to-teal-500"></div>
      <div class="w-16 h-16 mx-auto rounded-2xl bg-emerald-50 dark:bg-emerald-950/60 flex items-center justify-center mb-1">
        <mat-icon class="!text-4xl text-emerald-500 dark:text-emerald-400">place</mat-icon>
      </div>
      <h2 class="text-lg font-black mt-3 mb-1 text-slate-800 dark:text-white">¿Listo para trabajar?</h2>
      <p class="text-slate-500 dark:text-slate-400 text-sm mb-6">Activa tu ruta para comenzar a registrar tus visitas y pedidos del día.</p>
      <button (click)="activarJornada()" class="w-full py-3.5 bg-gradient-to-r from-emerald-600 to-teal-600 text-white rounded-xl font-black flex items-center justify-center gap-2">
        <mat-icon class="!text-base">power_settings_new</mat-icon> Activación de Ruta
      </button>
    </div>

    } @else {

    <!-- BARRA DE JORNADA -->
    <div class="relative overflow-hidden bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/8 rounded-2xl p-4 mb-4 flex items-center justify-between gap-2 shadow-sm">
      <div class="absolute top-0 left-0 w-full h-0.5 bg-gradient-to-r from-emerald-500 to-teal-500"></div>
      <div class="text-xs text-slate-500 dark:text-slate-400">
        <span class="text-emerald-600 dark:text-emerald-400 font-bold"><mat-icon class="!text-sm align-middle">check_circle</mat-icon> Ruta activa</span><br>
        Iniciada: {{ fmtHora(jornadaActiva().fecha_inicio) }}
      </div>
      <div class="flex items-center gap-2">
        <span class="text-xs px-2 py-1 bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 rounded-full font-bold" title="Visitas registradas">{{ jornadaActiva().visitas || 0 }}</span>
        <button (click)="verVisitas()" class="w-9 h-9 flex items-center justify-center rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-white transition-colors"><mat-icon class="!text-base">receipt_long</mat-icon></button>
        <button (click)="finalizarJornada()" class="px-3 py-2 bg-red-100 dark:bg-red-950 hover:bg-red-200 dark:hover:bg-red-900 text-red-700 dark:text-red-300 rounded-lg text-xs font-bold transition-colors">Finalizar</button>
      </div>
    </div>

    <!-- PROGRESO DEL FLUJO (PDV -> Cliente -> Decisión -> Catálogo/OCR -> Carrito) -->
    @if (pasoNumero() > 0) {
      <div class="flex items-center gap-2 mb-5" [matTooltip]="'Paso ' + pasoNumero() + ' de 5'">
        @for (n of [1,2,3,4,5]; track n) {
          <div class="flex-1 h-1 rounded-full transition-colors duration-300" [ngClass]="n <= pasoNumero() ? 'bg-emerald-500' : 'bg-slate-200 dark:bg-slate-800'"></div>
        }
      </div>
    }

    <!-- STEP: PDVs -->
    @if (step() === 'pdvs') {
      <div class="flex items-center justify-between mb-3">
        <div>
          <h2 class="text-lg font-black text-slate-800 dark:text-white">Puntos de venta</h2>
          <p class="text-slate-500 dark:text-slate-400 text-sm">Selecciona el PDV que vas a visitar</p>
        </div>
        <button (click)="mostrarSolicitarPdv.set(!mostrarSolicitarPdv())" class="px-3 py-2 rounded-xl text-xs font-bold border border-emerald-600 dark:border-emerald-700 text-emerald-700 dark:text-emerald-400 flex items-center gap-1">
          <mat-icon class="!text-base">add_business</mat-icon> Solicitar PDV
        </button>
      </div>

      @if (mostrarSolicitarPdv()) {
        <div class="bg-white dark:bg-slate-900 border border-emerald-200 dark:border-emerald-900 rounded-2xl p-4 mb-4 space-y-2 shadow-sm">
          <h3 class="font-bold text-emerald-700 dark:text-emerald-400 text-sm mb-2">Solicitud de nuevo PDV</h3>
          <input [(ngModel)]="nuevoPdv.nombre" placeholder="Nombre del PDV *" class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-white rounded-lg px-3 py-2 text-sm outline-none">
          <input [(ngModel)]="nuevoPdv.rif" placeholder="RIF *" class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-white rounded-lg px-3 py-2 text-sm outline-none">
          <textarea [(ngModel)]="nuevoPdv.direccion" placeholder="Dirección completa *" rows="2" class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-white rounded-lg px-3 py-2 text-sm outline-none"></textarea>
          <label class="block text-xs text-slate-500 dark:text-slate-400">Foto de la tienda *</label>
          <input type="file" accept="image/*" capture="environment" (change)="onFotoTienda($event)" class="w-full text-xs text-slate-600 dark:text-slate-300">
          <label class="block text-xs text-slate-500 dark:text-slate-400">Foto del RIF *</label>
          <input type="file" accept="image/*" capture="environment" (change)="onFotoRif($event)" class="w-full text-xs text-slate-600 dark:text-slate-300">
          <div class="flex gap-2 pt-2">
            <button (click)="mostrarSolicitarPdv.set(false)" class="flex-1 py-2 border border-slate-300 dark:border-slate-700 rounded-lg text-sm font-bold text-slate-500 dark:text-slate-400">Cancelar</button>
            <button (click)="solicitarPdv()" [disabled]="enviandoSolicitud()" class="flex-1 py-2 bg-emerald-600 dark:bg-emerald-700 text-white rounded-lg text-sm font-bold">Enviar solicitud</button>
          </div>
        </div>
      }

      <input [(ngModel)]="searchPdv" placeholder="Buscar PDV por nombre, ciudad..."
        class="w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-white rounded-xl px-4 py-2.5 text-sm outline-none mb-3 focus:border-emerald-500">
      <p class="text-xs text-slate-500 dark:text-slate-500 mb-2">{{ filteredPdvs.length }} de {{ pdvs().length }} puntos de venta</p>
      <div class="max-h-[55vh] overflow-y-auto space-y-2">
        @for (p of filteredPdvs.slice(0, 100); track p.identificador) {
          <button (click)="seleccionarPdv(p)" class="w-full text-left bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 border border-slate-200 dark:border-white/8 rounded-xl p-3 flex items-center gap-3 shadow-sm">
            <mat-icon class="text-emerald-600 dark:text-emerald-400">storefront</mat-icon>
            <div class="flex-1 min-w-0">
              <p class="font-bold text-sm truncate text-slate-800 dark:text-white">{{ p.nombre || p.identificador }}</p>
              <p class="text-xs text-slate-500 dark:text-slate-400 truncate">{{ pdvSub(p) }}</p>
            </div>
            <mat-icon class="text-slate-400 dark:text-slate-600">chevron_right</mat-icon>
          </button>
        }
        @if (!filteredPdvs.length) { <p class="text-center text-slate-400 dark:text-slate-600 py-12">No se encontraron puntos de venta</p> }
      </div>
    }

    <!-- STEP: CLIENTES -->
    @if (step() === 'clientes') {
      <div class="flex items-center gap-2 mb-3">
        <button (click)="step.set('pdvs')" class="w-9 h-9 flex items-center justify-center rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-white"><mat-icon class="!text-base">arrow_back</mat-icon></button>
        <div>
          <h2 class="text-lg font-black text-slate-800 dark:text-white">Clientes</h2>
          <p class="text-slate-500 dark:text-slate-400 text-xs">PDV: {{ pdvSel()?.nombre || pdvSel()?.identificador }}</p>
        </div>
      </div>
      <input [(ngModel)]="searchCliente" placeholder="Buscar cliente..."
        class="w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-white rounded-xl px-4 py-2.5 text-sm outline-none mb-3 focus:border-emerald-500">
      <div class="max-h-[60vh] overflow-y-auto space-y-2">
        @for (c of filteredClientes; track c.id_cliente) {
          <button (click)="seleccionarCliente(c)" class="w-full text-left bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 border border-slate-200 dark:border-white/8 rounded-xl p-3 flex items-center gap-3 shadow-sm">
            <mat-icon class="text-emerald-600 dark:text-emerald-400">person</mat-icon>
            <p class="font-bold text-sm flex-1 text-slate-800 dark:text-white">{{ c.nombre }}</p>
            <mat-icon class="text-slate-400 dark:text-slate-600">chevron_right</mat-icon>
          </button>
        }
        @if (!filteredClientes.length) { <p class="text-center text-slate-400 dark:text-slate-600 py-12">No se encontraron clientes</p> }
      </div>
    }

    <!-- STEP: DECISION -->
    @if (step() === 'decision') {
      <div class="flex items-center gap-2 mb-4">
        <button (click)="step.set('clientes')" class="w-9 h-9 flex items-center justify-center rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-white"><mat-icon class="!text-base">arrow_back</mat-icon></button>
        <div>
          <h2 class="text-lg font-black text-slate-800 dark:text-white">{{ clienteSel()?.nombre }}</h2>
          <p class="text-slate-500 dark:text-slate-400 text-xs">{{ pdvSel()?.nombre }}</p>
        </div>
      </div>

      @if (creditoCliente()?.bloqueado) {
        <div class="bg-red-50 dark:bg-red-950/60 border border-red-200 dark:border-red-900 rounded-xl px-4 py-3 mb-3 flex items-center gap-2">
          <mat-icon class="text-red-600 dark:text-red-400">block</mat-icon>
          <span class="text-sm text-red-700 dark:text-red-300 font-semibold flex-1">Cliente bloqueado por crédito ({{ creditoCliente()?.dias_mora }} días de mora) — no se pueden tomar pedidos.</span>
        </div>
        <button (click)="abrirPagoModal()" class="w-full mb-4 p-3 bg-white dark:bg-slate-900 border-2 border-amber-500 dark:border-amber-700 rounded-2xl text-left flex items-center gap-3 shadow-sm">
          <div class="w-10 h-10 rounded-xl bg-amber-100 dark:bg-amber-950 flex items-center justify-center"><mat-icon class="text-amber-600 dark:text-amber-400">payments</mat-icon></div>
          <p class="font-black text-sm text-slate-800 dark:text-white">Registrar cobro/abono</p>
        </button>
      } @else {
        <button (click)="abrirPagoModal()" class="w-full mb-4 p-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/8 rounded-2xl text-left flex items-center gap-3 shadow-sm">
          <div class="w-10 h-10 rounded-xl bg-amber-100 dark:bg-amber-950 flex items-center justify-center"><mat-icon class="text-amber-600 dark:text-amber-400">payments</mat-icon></div>
          <p class="font-bold text-sm text-slate-700 dark:text-slate-300">Registrar cobro/abono</p>
        </button>
      }

      <div class="grid gap-3">
        <button (click)="irACatalogo()" [disabled]="creditoCliente()?.bloqueado" class="p-5 bg-white dark:bg-slate-900 border-2 border-emerald-500 dark:border-emerald-700 rounded-2xl text-left flex items-center gap-4 shadow-sm disabled:opacity-40">
          <div class="w-12 h-12 rounded-xl bg-emerald-100 dark:bg-emerald-950 flex items-center justify-center"><mat-icon class="text-emerald-600 dark:text-emerald-400">shopping_cart</mat-icon></div>
          <div>
            <p class="font-black text-slate-800 dark:text-white">Tomar pedido</p>
            <p class="text-xs text-slate-500 dark:text-slate-400">Catálogo con precios y stock en vivo</p>
          </div>
        </button>
        <button (click)="abrirOcr()" [disabled]="creditoCliente()?.bloqueado || !isOnline()" class="p-5 bg-white dark:bg-slate-900 border-2 border-violet-500 dark:border-violet-700 rounded-2xl text-left flex items-center gap-4 shadow-sm disabled:opacity-40">
          <div class="w-12 h-12 rounded-xl bg-violet-100 dark:bg-violet-950 flex items-center justify-center"><mat-icon class="text-violet-600 dark:text-violet-400">document_scanner</mat-icon></div>
          <div>
            <p class="font-black text-slate-800 dark:text-white">Cargar nota de pedido (foto + IA)</p>
            <p class="text-xs text-slate-500 dark:text-slate-400">{{ isOnline() ? 'La IA lee la nota escrita a mano y arma el pedido' : 'Necesita conexión' }}</p>
          </div>
        </button>
        <button (click)="noHuboVenta()" class="p-4 bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/8 rounded-2xl text-left flex items-center gap-4 shadow-sm">
          <div class="w-10 h-10 rounded-xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center"><mat-icon class="text-slate-500 dark:text-slate-400">cancel</mat-icon></div>
          <p class="font-bold text-sm text-slate-700 dark:text-slate-300">No hubo venta en este cliente</p>
        </button>
      </div>
    }

    <!-- STEP: CATALOGO -->
    @if (step() === 'catalogo') {
      <div class="flex items-center gap-2 mb-3">
        <button (click)="step.set('decision')" class="w-9 h-9 flex items-center justify-center rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-white"><mat-icon class="!text-base">arrow_back</mat-icon></button>
        <div class="flex-1">
          <h2 class="text-lg font-black text-slate-800 dark:text-white">Catálogo</h2>
          <p class="text-slate-500 dark:text-slate-400 text-xs">{{ clienteSel()?.nombre }}</p>
        </div>
      </div>
      <div class="flex gap-2 mb-3">
        <input [(ngModel)]="searchCatalogo" placeholder="Buscar producto, marca, categoría..."
          class="flex-1 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-white rounded-xl px-4 py-2.5 text-sm outline-none focus:border-emerald-500">
        <button (click)="buscarCodigoBarras()" class="w-11 h-11 flex items-center justify-center rounded-xl bg-slate-800 dark:bg-slate-700 text-white shrink-0" title="Escanear código de barras">
          <mat-icon>qr_code_scanner</mat-icon>
        </button>
      </div>
      <div class="max-h-[55vh] overflow-y-auto space-y-2">
        @for (p of filteredCatalogo; track p.id_producto) {
          <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/8 rounded-xl p-3 flex items-center gap-3 shadow-sm">
            <div class="w-11 h-11 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center overflow-hidden shrink-0">
              @if (p.foto_url) { <img [src]="p.foto_url" class="w-full h-full object-cover"> } @else { <mat-icon class="text-slate-400">liquor</mat-icon> }
            </div>
            <div class="flex-1 min-w-0">
              <p class="font-bold text-sm truncate text-slate-800 dark:text-white">{{ p.nombre }}</p>
              <div class="flex items-center gap-1.5 flex-wrap mt-0.5">
                <span class="text-xs text-slate-500 dark:text-slate-400">{{ p.categoria }} · \${{ p.precio_unitario.toFixed(2) }}</span>
                @if (p.stock_disponible !== null) {
                  <span class="text-[10px] font-black px-1.5 py-0.5 rounded-full"
                    [ngClass]="p.stock_disponible > 0 ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400' : 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-400'">
                    {{ p.stock_disponible > 0 ? p.stock_disponible + ' disp.' : 'Sin stock' }}
                  </span>
                }
              </div>
            </div>
            <button (click)="agregarAlCarrito(p)" [disabled]="p.stock_disponible === 0" class="w-9 h-9 flex items-center justify-center rounded-full bg-emerald-600 dark:bg-emerald-700 text-white disabled:opacity-30 shrink-0">
              <mat-icon class="!text-base">add</mat-icon>
            </button>
          </div>
        }
        @if (!filteredCatalogo.length) { <p class="text-center text-slate-400 dark:text-slate-600 py-12">Sin productos en el catálogo de este cliente</p> }
      </div>
    }

    <!-- STEP: CARRITO -->
    @if (step() === 'carrito') {
      <div class="flex items-center gap-2 mb-4">
        <button (click)="step.set('catalogo')" class="w-9 h-9 flex items-center justify-center rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-white"><mat-icon class="!text-base">arrow_back</mat-icon></button>
        <h2 class="text-lg font-black text-slate-800 dark:text-white">Carrito</h2>
      </div>
      @if (!carrito().length) {
        <p class="text-center text-slate-400 dark:text-slate-600 py-12">Carrito vacío</p>
      } @else {
        <div class="space-y-2 mb-4">
          @for (item of carrito(); track item.id_producto; let i = $index) {
            <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/8 rounded-xl p-3 flex items-center gap-3 shadow-sm">
              <div class="flex-1 min-w-0">
                <p class="font-bold text-sm truncate text-slate-800 dark:text-white">{{ item.nombre }}</p>
                <p class="text-xs text-slate-500 dark:text-slate-400">\${{ item.precio_unitario.toFixed(2) }} c/u · Subtotal \${{ (item.precio_unitario * item.cantidad).toFixed(2) }}</p>
              </div>
              <div class="flex items-center gap-1 shrink-0">
                <button (click)="cambiarCantidad(i, -1)" class="w-7 h-7 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center"><mat-icon class="!text-sm">remove</mat-icon></button>
                <span class="w-6 text-center font-bold text-sm">{{ item.cantidad }}</span>
                <button (click)="cambiarCantidad(i, 1)" class="w-7 h-7 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center"><mat-icon class="!text-sm">add</mat-icon></button>
                <button (click)="quitarDelCarrito(i)" class="w-7 h-7 rounded-full bg-red-50 dark:bg-red-950 text-red-600 dark:text-red-400 flex items-center justify-center ml-1"><mat-icon class="!text-sm">delete</mat-icon></button>
              </div>
            </div>
          }
        </div>
        <textarea [(ngModel)]="notasPedido" rows="2" placeholder="Notas del pedido (opcional)"
          class="w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-white rounded-xl px-4 py-2.5 text-sm outline-none mb-4"></textarea>
        <div class="bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-900 rounded-xl p-4 flex items-center justify-between mb-4">
          <span class="font-bold text-slate-700 dark:text-slate-300">Total</span>
          <span class="text-2xl font-black text-emerald-700 dark:text-emerald-400">\${{ totalCarrito().toFixed(2) }}</span>
        </div>
        <button (click)="confirmarPedido()" [disabled]="creandoPedido()" class="w-full py-3.5 bg-gradient-to-r from-emerald-600 to-teal-600 text-white rounded-xl font-black flex items-center justify-center gap-2">
          @if (creandoPedido()) { <mat-spinner diameter="18" color="accent"></mat-spinner> } @else { <mat-icon class="!text-base">check_circle</mat-icon> }
          Confirmar pedido
        </button>
      }
    }

    <!-- STEP: OCR REVISION -->
    @if (step() === 'ocr-revision') {
      <div class="flex items-center gap-2 mb-4">
        <button (click)="step.set('decision')" class="w-9 h-9 flex items-center justify-center rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-white"><mat-icon class="!text-base">arrow_back</mat-icon></button>
        <div>
          <h2 class="text-lg font-black text-slate-800 dark:text-white">Revisar nota de pedido</h2>
          <p class="text-slate-500 dark:text-slate-400 text-xs">La IA propuso esto — revisa antes de confirmar</p>
        </div>
      </div>
      @if (ocrPropuesta()) {
        <div class="bg-violet-50 dark:bg-violet-950/40 border border-violet-200 dark:border-violet-900 rounded-xl p-3 mb-4 text-xs text-violet-700 dark:text-violet-300">
          <mat-icon class="!text-sm align-middle">info</mat-icon> Confianza de lectura: {{ (ocrPropuesta()!.confianza * 100).toFixed(0) }}%
          @if (ocrPropuesta()!.cliente_texto) { <br>Cliente detectado en la nota: "{{ ocrPropuesta()!.cliente_texto }}" }
        </div>
        <div class="space-y-2 mb-4">
          @for (p of ocrPropuesta()!.productos_propuestos; track p) {
            <div class="bg-white dark:bg-slate-900 border rounded-xl p-3 flex items-center gap-3 shadow-sm"
                 [ngClass]="p.match ? 'border-slate-200 dark:border-white/8' : 'border-amber-300 dark:border-amber-800'">
              <input type="checkbox" [checked]="p.incluido !== false" (change)="p.incluido = !(p.incluido !== false)" [disabled]="!p.match" class="w-5 h-5 shrink-0">
              <div class="flex-1 min-w-0">
                <p class="text-xs text-slate-400 dark:text-slate-500">Escrito: "{{ p.nombre_texto }}"</p>
                @if (p.match) {
                  <p class="font-bold text-sm text-slate-800 dark:text-white">{{ p.match.nombre }} <span class="text-xs font-normal text-slate-500">({{ (p.match.similaridad*100).toFixed(0) }}% match)</span></p>
                  <p class="text-xs text-emerald-600 dark:text-emerald-400">\${{ p.match.precio_unitario.toFixed(2) }}</p>
                } @else {
                  <p class="text-sm text-amber-700 dark:text-amber-400 font-semibold">No se encontró en el catálogo — agrégalo a mano si aplica</p>
                }
              </div>
              @if (p.match) {
                <div class="flex items-center gap-1 shrink-0">
                  <button (click)="p.cantidad = Math.max(1, p.cantidad - 1)" class="w-7 h-7 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center"><mat-icon class="!text-sm">remove</mat-icon></button>
                  <span class="w-6 text-center font-bold text-sm">{{ p.cantidad }}</span>
                  <button (click)="p.cantidad = p.cantidad + 1" class="w-7 h-7 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center"><mat-icon class="!text-sm">add</mat-icon></button>
                </div>
              }
            </div>
          }
        </div>
        <button (click)="confirmarNotaOcr()" [disabled]="creandoPedido()" class="w-full py-3.5 bg-gradient-to-r from-violet-600 to-purple-600 text-white rounded-xl font-black flex items-center justify-center gap-2">
          @if (creandoPedido()) { <mat-spinner diameter="18" color="accent"></mat-spinner> } @else { <mat-icon class="!text-base">check_circle</mat-icon> }
          Confirmar pedido desde la nota
        </button>
      }
    }

    }
  </div>

  <!-- carrito flotante -->
  @if (step() === 'catalogo' && carrito().length > 0) {
    <div class="fixed bottom-0 left-0 right-0 px-6 py-3">
      <button (click)="step.set('carrito')" class="w-full max-w-3xl mx-auto block py-3.5 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-xl font-black shadow-2xl flex items-center justify-center gap-2">
        <mat-icon class="!text-base">shopping_cart</mat-icon> Ver carrito ({{ carritoCount() }}) · \${{ totalCarrito().toFixed(2) }}
      </button>
    </div>
  }

  <!-- input oculto de camara para nota OCR -->
  <input #ocrInputEl type="file" accept="image/*" capture="environment" class="hidden" (change)="onFotoNotaPedido($event)">
  @if (subiendoOcr()) {
    <div class="fixed inset-0 bg-black/60 z-50 flex items-center justify-center">
      <div class="bg-white dark:bg-slate-900 rounded-2xl px-8 py-6 text-center border border-slate-200 dark:border-white/10">
        <mat-spinner diameter="40" class="mx-auto"></mat-spinner>
        <p class="mt-3 font-bold text-slate-800 dark:text-white">La IA está leyendo la nota…</p>
      </div>
    </div>
  }

  <!-- Picker de motivo de "no hubo venta" -->
  @if (showRazonModal()) {
    <div class="fixed inset-0 bg-black/60 z-50 flex items-end sm:items-center justify-center" (click)="showRazonModal.set(false)">
      <div class="bg-white dark:bg-slate-900 rounded-t-2xl sm:rounded-2xl w-full sm:w-96 p-4 border border-slate-200 dark:border-white/10" (click)="$event.stopPropagation()">
        <h3 class="font-black text-slate-800 dark:text-white mb-3">¿Por qué no hubo venta?</h3>
        <div class="space-y-2">
          @for (r of razonesNoVenta; track r) {
            <button (click)="elegirRazonNoVenta(r)" class="w-full text-left px-4 py-3 rounded-xl bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 font-semibold text-sm text-slate-700 dark:text-slate-200">{{ r }}</button>
          }
        </div>
        <button (click)="showRazonModal.set(false)" class="w-full mt-3 py-2 text-sm font-bold text-slate-500 dark:text-slate-400">Cancelar</button>
      </div>
    </div>
  }

  <!-- Registrar cobro/abono -->
  @if (showPagoModal()) {
    <div class="fixed inset-0 bg-black/60 z-50 flex items-end sm:items-center justify-center" (click)="showPagoModal.set(false)">
      <div class="bg-white dark:bg-slate-900 rounded-t-2xl sm:rounded-2xl w-full sm:w-96 p-4 border border-slate-200 dark:border-white/10" (click)="$event.stopPropagation()">
        <h3 class="font-black text-slate-800 dark:text-white mb-3">Registrar cobro/abono -- {{ clienteSel()?.nombre }}</h3>
        <label class="text-[10px] font-black text-slate-400 uppercase tracking-wider mb-1 block">Monto (USD)</label>
        <input type="number" [(ngModel)]="pagoMonto" min="0.01" step="0.01" placeholder="0.00"
          class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-white/10 focus:border-amber-500 text-slate-800 dark:text-white rounded-xl px-3 py-2.5 text-sm font-bold outline-none mb-3">
        <label class="text-[10px] font-black text-slate-400 uppercase tracking-wider mb-1 block">Método</label>
        <div class="grid grid-cols-3 gap-2 mb-3">
          @for (m of metodosPago; track m) {
            <button (click)="pagoMetodo = m" class="px-2 py-2 rounded-xl text-xs font-bold border transition-colors"
              [class.bg-amber-500]="pagoMetodo === m" [class.text-white]="pagoMetodo === m" [class.border-amber-500]="pagoMetodo === m"
              [class.bg-slate-50]="pagoMetodo !== m" [class.dark:bg-slate-800]="pagoMetodo !== m" [class.text-slate-600]="pagoMetodo !== m" [class.dark:text-slate-300]="pagoMetodo !== m" [class.border-slate-200]="pagoMetodo !== m" [class.dark:border-white/10]="pagoMetodo !== m">{{ m }}</button>
          }
        </div>
        <label class="text-[10px] font-black text-slate-400 uppercase tracking-wider mb-1 block">Referencia (opcional)</label>
        <input [(ngModel)]="pagoReferencia" placeholder="Nro. de comprobante..."
          class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-white/10 focus:border-amber-500 text-slate-800 dark:text-white rounded-xl px-3 py-2.5 text-sm outline-none mb-4">
        <div class="flex gap-2">
          <button (click)="showPagoModal.set(false)" class="flex-1 py-2.5 rounded-xl text-sm font-bold text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-white/10">Cancelar</button>
          <button (click)="registrarPago()" [disabled]="!pagoMonto || pagoMonto <= 0 || !pagoMetodo || registrandoPago()"
            class="flex-1 py-2.5 rounded-xl text-sm font-black text-white bg-amber-600 hover:bg-amber-500 disabled:opacity-40 flex items-center justify-center gap-1.5">
            @if (registrandoPago()) { <mat-spinner diameter="16" strokeWidth="3" class="!text-white"></mat-spinner> } @else { Registrar }
          </button>
        </div>
      </div>
    </div>
  }
</div>
  `,
})
export class VentasComponent implements OnInit {
  private http = inject(HttpClient);
  private auth = inject(AuthService);
  private snack = inject(MatSnackBar);
  private offline = inject(VentasOfflineQueueService);
  private confirmDialog = inject(ConfirmService);
  private API = `${environment.apiUrl}/api/vendedor`;
  Math = Math;

  cedula = this.auth.currentUser()?.username || '';

  loading = signal(true);
  jornadaActiva = signal<any>(null);
  step = signal<'pdvs' | 'clientes' | 'decision' | 'catalogo' | 'carrito' | 'ocr-revision'>('pdvs');
  pdvs = signal<Pdv[]>([]);
  clientes = signal<Cli[]>([]);
  pdvSel = signal<Pdv | null>(null);
  clienteSel = signal<Cli | null>(null);
  creditoCliente = signal<{ bloqueado: boolean; dias_mora: number } | null>(null);
  registrando = signal(false);

  // Motivo de "no hubo venta" -- fuente de verdad en el backend
  // (RAZONES_NO_VENTA, vendedor.py); duplicado acá porque es una lista
  // chica y estable, no vale la pena un round-trip solo para esto.
  readonly razonesNoVenta = ['Precio', 'Competencia', 'Sin stock', 'Cerrado', 'Otro'];
  showRazonModal = signal(false);

  // Registrar pago/abono
  readonly metodosPago = ['Transferencia', 'Efectivo', 'Zelle', 'Pago Móvil', 'Otro'];
  showPagoModal = signal(false);
  registrandoPago = signal(false);
  pagoMonto: number | null = null;
  pagoMetodo = '';
  pagoReferencia = '';

  searchPdv = '';
  searchCliente = '';
  searchCatalogo = '';

  catalogo = signal<ProductoCatalogo[]>([]);
  carrito = signal<ItemCarrito[]>([]);
  notasPedido = '';
  creandoPedido = signal(false);

  ocrPropuesta = signal<{ id_nota_ocr: number; cliente_texto: string | null; confianza: number; productos_propuestos: ProductoOcrPropuesto[] } | null>(null);
  subiendoOcr = signal(false);

  mostrarSolicitarPdv = signal(false);
  nuevoPdv = { nombre: '', rif: '', direccion: '' };
  fotoTiendaData: string | null = null;
  fotoRifData: string | null = null;
  enviandoSolicitud = signal(false);

  isOnline = signal(navigator.onLine);
  pendingSync = signal(0);
  syncError = signal<string | null>(null);

  ngOnInit() {
    this.offline.isOnline$.subscribe(v => this.isOnline.set(v));
    this.offline.pendingCount$.subscribe(v => this.pendingSync.set(v));
    this.offline.syncError$.subscribe(e => this.syncError.set(e?.error || null));
    if (navigator.onLine) this.offline.syncAll();
    this.cargarJornada();
  }

  sincronizar() { this.offline.syncAll(); }

  crumb() {
    return [this.pdvSel()?.nombre, this.clienteSel()?.nombre].filter(Boolean).join('  ›  ');
  }

  /** Posición del paso actual en el flujo PDV → Cliente → Decisión →
   *  Catálogo/OCR → Carrito, para la barra de progreso. 0 = no mostrarla
   *  (ocr-revision cuelga de "decisión", cuenta como el mismo paso 4). */
  private readonly PASOS: Record<string, number> = {
    pdvs: 1, clientes: 2, decision: 3, catalogo: 4, 'ocr-revision': 4, carrito: 5,
  };
  pasoNumero(): number { return this.PASOS[this.step()] || 0; }

  fmtHora(iso: string): string {
    if (!iso) return '—';
    try { return new Date(iso).toLocaleString('es-VE', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }); }
    catch { return iso; }
  }

  err(e: any) { this.snack.open(e?.error?.detail || e?.error?.message || 'Error', 'OK', { duration: 4000 }); }

  private get<T>(u: string) { return this.http.get<T>(`${this.API}${u}`); }
  private post<T>(u: string, b: any) { return this.http.post<T>(`${this.API}${u}`, b); }

  private cachedGet<T>(url: string, cacheKey: string, onData: (v: T) => void, onDone?: () => void) {
    this.get<T>(url).subscribe({
      next: v => { onData(v); this.offline.cacheWrite(cacheKey, v); onDone?.(); },
      error: async () => {
        const cached = await this.offline.cacheRead(cacheKey);
        if (cached) { onData(cached); this.snack.open('Sin conexión — mostrando datos guardados', 'OK', { duration: 3000 }); }
        onDone?.();
      }
    });
  }

  cargarJornada() {
    this.loading.set(true);
    this.cachedGet<any>('/jornada-activa', 'jornada-activa', res => {
      this.jornadaActiva.set(res.activa ? res : null);
      if (res.activa) { this.cargarPdvs(); this.cargarClientes(); }
    }, () => this.loading.set(false));
  }

  activarJornada() {
    if (!navigator.onLine) {
      this.offline.enqueue({ url: `${this.API}/activar-jornada`, jsonBody: {}, label: 'Activar jornada' });
      const optimista = { success: true, activa: true, fecha_inicio: new Date().toISOString(), visitas: 0 };
      this.jornadaActiva.set(optimista);
      this.offline.cacheWrite('jornada-activa', optimista);
      this.cargarPdvs(); this.cargarClientes();
      return;
    }
    this.post<any>('/activar-jornada', {}).subscribe({
      next: res => { this.jornadaActiva.set({ ...res, activa: true, visitas: 0 }); this.cargarPdvs(); this.cargarClientes(); },
      error: e => this.err(e),
    });
  }

  async finalizarJornada() {
    const ok = await this.confirmDialog.confirm('¿Terminar la jornada de hoy?', { title: 'Finalizar jornada', confirmText: 'Sí, terminar', danger: true });
    if (!ok) return;
    if (!navigator.onLine) {
      this.offline.enqueue({ url: `${this.API}/finalizar-jornada`, jsonBody: {}, label: 'Finalizar jornada' });
      this.jornadaActiva.set(null);
      this.offline.cacheWrite('jornada-activa', { success: true, activa: false });
      this.snack.open('Jornada finalizada localmente — se sincronizará al reconectar', 'OK', { duration: 3000 });
      return;
    }
    this.post('/finalizar-jornada', {}).subscribe({
      next: () => { this.jornadaActiva.set(null); this.snack.open('Jornada finalizada', 'OK', { duration: 2500 }); },
      error: e => this.err(e),
    });
  }

  cargarPdvs() {
    this.cachedGet<Pdv[]>('/pdvs', 'pdvs', p => this.pdvs.set(p || []), () => this.loading.set(false));
  }
  cargarClientes() {
    this.cachedGet<Cli[]>('/clientes', 'clientes', c => this.clientes.set(c || []));
  }

  pdvSub(p: Pdv): string {
    return [p.ciudad, p.localidad].filter(x => !!x).join(' · ') || p.direccion || '';
  }

  get filteredPdvs(): Pdv[] {
    const f = this.searchPdv.trim().toLowerCase();
    if (!f) return this.pdvs();
    return this.pdvs().filter(p =>
      (p.nombre || '').toLowerCase().includes(f) || (p.identificador || '').toLowerCase().includes(f) ||
      (p.ciudad || '').toLowerCase().includes(f) || (p.localidad || '').toLowerCase().includes(f) ||
      (p.direccion || '').toLowerCase().includes(f));
  }
  get filteredClientes(): Cli[] {
    const f = this.searchCliente.trim().toLowerCase();
    if (!f) return this.clientes();
    return this.clientes().filter(c => (c.nombre || '').toLowerCase().includes(f));
  }
  get filteredCatalogo(): ProductoCatalogo[] {
    const f = this.searchCatalogo.trim().toLowerCase();
    const base = this.catalogo();
    if (!f) return base;
    return base.filter(p =>
      (p.nombre || '').toLowerCase().includes(f) || (p.categoria || '').toLowerCase().includes(f) || (p.marca || '').toLowerCase().includes(f));
  }

  seleccionarPdv(p: Pdv) {
    this.pdvSel.set(p); this.searchCliente = ''; this.step.set('clientes');
  }
  seleccionarCliente(c: Cli) {
    this.clienteSel.set(c); this.carrito.set([]); this.notasPedido = ''; this.step.set('decision');
    this.get<any>(`/credito/${c.id_cliente}`).subscribe({
      next: r => this.creditoCliente.set({ bloqueado: r.bloqueado, dias_mora: r.dias_mora }),
      error: () => this.creditoCliente.set(null),
    });
  }

  // ── CATÁLOGO / CARRITO ──────────────────────────────────────────
  irACatalogo() {
    this.step.set('catalogo'); this.searchCatalogo = '';
    this.cachedGet<ProductoCatalogo[]>(`/catalogo?id_cliente=${this.clienteSel()!.id_cliente}`, `catalogo:${this.clienteSel()!.id_cliente}`, c => this.catalogo.set(c || []));
  }

  agregarAlCarrito(p: ProductoCatalogo) {
    const items = [...this.carrito()];
    const existente = items.find(i => i.id_producto === p.id_producto);
    if (existente) { existente.cantidad++; }
    else { items.push({ id_producto: p.id_producto, nombre: p.nombre, precio_unitario: p.precio_unitario, cantidad: 1, descuento_pct: 0, stock_disponible: p.stock_disponible }); }
    this.carrito.set(items);
    this.snack.open(`${p.nombre} agregado`, '', { duration: 1200 });
  }
  cambiarCantidad(i: number, delta: number) {
    const items = [...this.carrito()];
    items[i].cantidad = Math.max(1, items[i].cantidad + delta);
    this.carrito.set(items);
  }
  quitarDelCarrito(i: number) {
    const items = [...this.carrito()]; items.splice(i, 1); this.carrito.set(items);
  }
  carritoCount(): number { return this.carrito().reduce((n, i) => n + i.cantidad, 0); }
  totalCarrito(): number { return this.carrito().reduce((t, i) => t + i.precio_unitario * i.cantidad, 0); }

  buscarCodigoBarras() {
    const codigo = prompt('Código de barras (o escanea con el lector si tu dispositivo lo soporta):');
    if (!codigo?.trim()) return;
    this.get<any>(`/catalogo/buscar-codigo-barras?codigo=${encodeURIComponent(codigo.trim())}&id_cliente=${this.clienteSel()!.id_cliente}`).subscribe({
      next: r => this.agregarAlCarrito({ id_producto: r.id_producto, nombre: r.nombre, precio_unitario: r.precio_unitario } as ProductoCatalogo),
      error: () => this.snack.open('Sin resultados para ese código de barras', 'OK', { duration: 2500 }),
    });
  }

  confirmarPedido() {
    const cli = this.clienteSel();
    if (!cli || !this.carrito().length) return;
    const payload = {
      id_cliente: cli.id_cliente,
      identificador_punto_interes: this.pdvSel()?.identificador,
      lineas: this.carrito().map(i => ({ id_producto: i.id_producto, cantidad: i.cantidad, descuento_pct: i.descuento_pct })),
      notas: this.notasPedido.trim() || null,
    };
    this.creandoPedido.set(true);
    if (!navigator.onLine) {
      this.offline.enqueue({ url: `${this.API}/pedidos`, jsonBody: payload, label: `Pedido ${cli.nombre}` });
      this.creandoPedido.set(false);
      this.carrito.set([]); this.notasPedido = '';
      this.snack.open('Pedido guardado localmente — se sincronizará al reconectar', 'OK', { duration: 3000 });
      this.step.set('clientes');
      return;
    }
    this.post<any>('/pedidos', payload).subscribe({
      next: res => {
        this.creandoPedido.set(false);
        this.carrito.set([]); this.notasPedido = '';
        this.snack.open(`¡Pedido ${res.pedido.numero_pedido} registrado! Total $${res.pedido.total.toFixed(2)}`, 'OK', { duration: 3500 });
        this.step.set('clientes');
      },
      error: e => { this.creandoPedido.set(false); this.err(e); },
    });
  }

  // ── OCR + IA ─────────────────────────────────────────────────────
  ocrInputEl = viewChild<ElementRef<HTMLInputElement>>('ocrInputEl');
  abrirOcr() {
    this.ocrInputEl()?.nativeElement.click();
  }
  onFotoNotaPedido(ev: Event) {
    const file = (ev.target as HTMLInputElement).files?.[0];
    (ev.target as HTMLInputElement).value = '';
    if (!file || !this.clienteSel()) return;
    const fd = new FormData();
    fd.append('id_cliente', String(this.clienteSel()!.id_cliente));
    fd.append('file', file);
    this.subiendoOcr.set(true);
    this.http.post<any>(`${this.API}/pedidos/ocr`, fd).subscribe({
      next: res => {
        this.subiendoOcr.set(false);
        const propuestos: ProductoOcrPropuesto[] = (res.productos_propuestos || []).map((p: any) => ({ ...p, incluido: true }));
        this.ocrPropuesta.set({ id_nota_ocr: res.id_nota_ocr, cliente_texto: res.cliente_texto, confianza: res.confianza || 0, productos_propuestos: propuestos });
        this.step.set('ocr-revision');
      },
      error: e => { this.subiendoOcr.set(false); this.err(e); },
    });
  }

  confirmarNotaOcr() {
    const prop = this.ocrPropuesta();
    const cli = this.clienteSel();
    if (!prop || !cli) return;
    const lineas = prop.productos_propuestos
      .filter(p => p.match && p.incluido !== false)
      .map(p => ({ id_producto: p.match!.id_producto, cantidad: p.cantidad, descuento_pct: 0 }));
    if (!lineas.length) { this.snack.open('No hay productos con match para confirmar', 'OK', { duration: 3000 }); return; }
    const payload = {
      id_cliente: cli.id_cliente,
      identificador_punto_interes: this.pdvSel()?.identificador,
      lineas, notas: 'Cargado desde nota de pedido (IA)',
    };
    this.creandoPedido.set(true);
    this.post<any>(`/pedidos/ocr/${prop.id_nota_ocr}/confirmar`, payload).subscribe({
      next: res => {
        this.creandoPedido.set(false);
        this.ocrPropuesta.set(null);
        this.snack.open(`¡Pedido ${res.pedido.numero_pedido} registrado desde la nota! Total $${res.pedido.total.toFixed(2)}`, 'OK', { duration: 3500 });
        this.step.set('clientes');
      },
      error: e => { this.creandoPedido.set(false); this.err(e); },
    });
  }

  // ── NO HUBO VENTA (visita sin pedido -- se mantiene el registro histórico) ──
  // Antes esto era un promptText libre -- imposible de reportar ("no compró"
  // tenía 30 variantes escritas a mano). Ahora abre el picker de categorías;
  // "Otro" sigue usando el prompt libre para el detalle.
  noHuboVenta() {
    if (!this.pdvSel() || !this.clienteSel()) return;
    this.showRazonModal.set(true);
  }

  async elegirRazonNoVenta(categoria: string) {
    this.showRazonModal.set(false);
    let detalle = '';
    if (categoria === 'Otro') {
      const texto = await this.confirmDialog.promptText('Detalle:', { title: 'Otro motivo', placeholder: 'Escribe el motivo…', required: true, confirmText: 'Registrar' });
      if (!texto?.trim()) return;
      detalle = texto.trim();
    }
    await this.enviarNoHuboVenta(categoria, detalle);
  }

  private async enviarNoHuboVenta(categoria: string, detalle: string) {
    const pdv = this.pdvSel(), cli = this.clienteSel();
    if (!pdv || !cli) return;
    const payload = { id_punto_interes: pdv.identificador, id_cliente: cli.id_cliente, vendio: false, razon_categoria: categoria, razon_no_venta: detalle };
    this.registrando.set(true);
    if (!navigator.onLine) {
      this.offline.enqueue({ url: `${this.API}/registrar-visita`, jsonBody: payload, label: `No venta ${cli.nombre}` });
      const j = this.jornadaActiva();
      if (j) { j.visitas = (j.visitas || 0) + 1; this.jornadaActiva.set({ ...j }); this.offline.cacheWrite('jornada-activa', j); }
      this.registrando.set(false);
      this.snack.open('Registrado localmente', 'OK', { duration: 2500 });
      this.step.set('clientes');
      return;
    }
    this.post<any>('/registrar-visita', payload).subscribe({
      next: res => {
        this.registrando.set(false);
        const j = this.jornadaActiva(); if (j) this.jornadaActiva.set({ ...j, visitas: res.visitas });
        this.snack.open('No venta registrada', 'OK', { duration: 2000 });
        this.step.set('clientes');
      },
      error: e => { this.registrando.set(false); this.err(e); },
    });
  }

  // ── Registrar pago/abono (requiere señal -- el cobro es un movimiento de
  // cuenta real, no algo que tenga sentido dejar en la cola offline como
  // los pedidos) ──
  abrirPagoModal() {
    this.pagoMonto = null; this.pagoMetodo = ''; this.pagoReferencia = '';
    this.showPagoModal.set(true);
  }

  registrarPago() {
    const cli = this.clienteSel();
    if (!cli || !this.pagoMonto || this.pagoMonto <= 0 || !this.pagoMetodo) return;
    this.registrandoPago.set(true);
    this.post<any>(`/credito/${cli.id_cliente}/pago`, {
      monto: this.pagoMonto, metodo_pago: this.pagoMetodo, referencia: this.pagoReferencia.trim() || null,
    }).subscribe({
      next: res => {
        this.registrandoPago.set(false);
        this.showPagoModal.set(false);
        this.snack.open(`Pago registrado. Saldo: $${res.saldo_despues.toFixed(2)}`, 'OK', { duration: 3000 });
        const c = this.creditoCliente();
        if (c) this.creditoCliente.set({ ...c, dias_mora: res.saldo_despues <= 0 ? 0 : c.dias_mora });
      },
      error: e => { this.registrandoPago.set(false); this.err(e); },
    });
  }

  verVisitas() {
    this.cachedGet<any>('/visitas-hoy', 'visitas-hoy', res => {
      const visitas = res?.visitas || [];
      if (!visitas.length) { this.snack.open('Aún no has registrado visitas en esta jornada', 'OK', { duration: 2500 }); return; }
      const items = visitas.map((v: any) => `${v.cliente || 'Cliente'}: ${v.vendio ? 'Vendió $' + (v.monto?.toFixed?.(2) ?? v.monto) : 'No vendió — ' + (v.razon_no_venta || '')}`);
      this.confirmDialog.info(`${visitas.length} visita(s) registradas en esta jornada`, { title: 'Visitas de la jornada', items });
    });
  }

  private fileToCompressedDataURL(file: File, maxDim = 1000, quality = 0.6): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
          let w = img.width, h = img.height;
          if (w > h && w > maxDim) { h = Math.round(h * maxDim / w); w = maxDim; }
          else if (h >= w && h > maxDim) { w = Math.round(w * maxDim / h); h = maxDim; }
          const canvas = document.createElement('canvas');
          canvas.width = w; canvas.height = h;
          canvas.getContext('2d')!.drawImage(img, 0, 0, w, h);
          resolve(canvas.toDataURL('image/jpeg', quality));
        };
        img.onerror = reject;
        img.src = e.target!.result as string;
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  onFotoTienda(ev: Event) {
    const file = (ev.target as HTMLInputElement).files?.[0];
    if (!file) return;
    this.fileToCompressedDataURL(file).then(d => this.fotoTiendaData = d);
  }
  onFotoRif(ev: Event) {
    const file = (ev.target as HTMLInputElement).files?.[0];
    if (!file) return;
    this.fileToCompressedDataURL(file).then(d => this.fotoRifData = d);
  }

  solicitarPdv() {
    const { nombre, rif, direccion } = this.nuevoPdv;
    if (!nombre.trim() || !rif.trim() || !direccion.trim() || !this.fotoTiendaData || !this.fotoRifData) {
      this.snack.open('Completa nombre, RIF, dirección y ambas fotos', 'OK', { duration: 3000 });
      return;
    }
    const payload = {
      punto_de_interes: nombre.trim(), rif: rif.trim(), direccion: direccion.trim(),
      foto_tienda: this.fotoTiendaData, foto_rif: this.fotoRifData,
      latitud: null as number | null, longitud: null as number | null,
    };
    const send = () => {
      this.enviandoSolicitud.set(true);
      if (!navigator.onLine) {
        this.offline.enqueue({ url: `${this.API}/solicitar-pdv`, jsonBody: payload, label: `Solicitud PDV ${nombre}` });
        this.enviandoSolicitud.set(false);
        this.mostrarSolicitarPdv.set(false);
        this.nuevoPdv = { nombre: '', rif: '', direccion: '' };
        this.fotoTiendaData = null; this.fotoRifData = null;
        this.snack.open('Solicitud guardada localmente — se enviará a ATC al reconectar', 'OK', { duration: 3000 });
        return;
      }
      this.post<any>('/solicitar-pdv', payload).subscribe({
        next: res => {
          this.enviandoSolicitud.set(false);
          this.mostrarSolicitarPdv.set(false);
          this.nuevoPdv = { nombre: '', rif: '', direccion: '' };
          this.fotoTiendaData = null; this.fotoRifData = null;
          this.snack.open(res.message || 'Solicitud enviada', 'OK', { duration: 3000 });
        },
        error: e => { this.enviandoSolicitud.set(false); this.err(e); },
      });
    };
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        pos => { payload.latitud = pos.coords.latitude; payload.longitud = pos.coords.longitude; send(); },
        () => send(), { enableHighAccuracy: true, timeout: 5000 });
    } else send();
  }
}
