import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { RouterLink } from '@angular/router';
import { BaseChartDirective } from 'ng2-charts';
import { ChartData, ChartOptions } from 'chart.js';
import { environment } from '../../../environments/environment';

type DashboardData = {
  periodo: { desde: string; hasta: string };
  resumen: { pedidos: number; total_vendido: number; ticket_promedio: number };
  por_vendedor: { vendedor: string; pedidos: number; total: number }[];
  por_dia: { dia: string; total: number; pedidos: number }[];
  top_productos: { producto: string; unidades: number; total: number }[];
  por_estado: { estado: string; cantidad: number }[];
  top_clientes: { cliente: string; pedidos: number; total: number }[];
};

@Component({
  selector: 'app-ventas-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule, MatProgressSpinnerModule, RouterLink, BaseChartDirective],
  template: `
<div class="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-800 dark:text-white">
  <div class="bg-white dark:bg-gradient-to-r dark:from-slate-900 dark:to-slate-800 border-b border-slate-200 dark:border-white/8 px-6 py-5">
    <div class="flex items-center gap-3 max-w-6xl mx-auto">
      <a routerLink="/ventas" class="w-9 h-9 flex items-center justify-center rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700"><mat-icon class="!text-base">arrow_back</mat-icon></a>
      <div class="w-11 h-11 rounded-2xl bg-gradient-to-br from-emerald-600 to-teal-700 flex items-center justify-center shadow-lg">
        <mat-icon class="text-white">bar_chart</mat-icon>
      </div>
      <div class="flex-1">
        <h1 class="text-xl font-black tracking-tight leading-none">Dashboard de Ventas</h1>
        <p class="text-slate-500 dark:text-slate-400 text-xs mt-0.5">{{ data()?.periodo?.desde }} → {{ data()?.periodo?.hasta }}</p>
      </div>
      <a routerLink="/pedidos-ventas" class="px-3 py-2 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-xs font-bold flex items-center gap-1">
        <mat-icon class="!text-base">receipt_long</mat-icon> Pedidos
      </a>
      <div class="flex items-center gap-2">
        <input type="date" [(ngModel)]="desde" (change)="cargar()" class="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-2 py-1.5 text-xs">
        <span class="text-slate-400 text-xs">a</span>
        <input type="date" [(ngModel)]="hasta" (change)="cargar()" class="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-2 py-1.5 text-xs">
      </div>
    </div>
  </div>

  <div class="px-6 py-6 max-w-6xl mx-auto">
    @if (loading()) {
      <div class="flex justify-center py-24"><mat-spinner diameter="40"></mat-spinner></div>
    } @else if (data()) {

    <!-- RESUMEN -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
      <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/8 rounded-2xl p-5 shadow-sm">
        <p class="text-xs text-slate-500 dark:text-slate-400 font-bold uppercase">Pedidos</p>
        <p class="text-3xl font-black text-slate-800 dark:text-white mt-1">{{ data()!.resumen.pedidos }}</p>
      </div>
      <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/8 rounded-2xl p-5 shadow-sm">
        <p class="text-xs text-slate-500 dark:text-slate-400 font-bold uppercase">Total vendido</p>
        <p class="text-3xl font-black text-emerald-600 dark:text-emerald-400 mt-1">\${{ data()!.resumen.total_vendido.toFixed(2) }}</p>
      </div>
      <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/8 rounded-2xl p-5 shadow-sm">
        <p class="text-xs text-slate-500 dark:text-slate-400 font-bold uppercase">Ticket promedio</p>
        <p class="text-3xl font-black text-slate-800 dark:text-white mt-1">\${{ data()!.resumen.ticket_promedio.toFixed(2) }}</p>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
      <!-- VENTAS POR DIA -->
      <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/8 rounded-2xl p-5 shadow-sm">
        <h3 class="font-black text-sm mb-3 text-slate-800 dark:text-white">Ventas por día</h3>
        @if (porDiaChart.labels?.length) {
          <div style="position:relative; height:220px; width:100%">
            <canvas baseChart [data]="porDiaChart" [options]="lineOptions" type="line"></canvas>
          </div>
        } @else { <p class="text-center text-slate-400 py-12 text-sm">Sin datos en el período</p> }
      </div>

      <!-- PEDIDOS POR ESTADO -->
      <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/8 rounded-2xl p-5 shadow-sm">
        <h3 class="font-black text-sm mb-3 text-slate-800 dark:text-white">Pedidos por estado</h3>
        @if (porEstadoChart.labels?.length) {
          <div style="position:relative; height:220px; width:100%">
            <canvas baseChart [data]="porEstadoChart" [options]="doughnutOptions" type="doughnut"></canvas>
          </div>
        } @else { <p class="text-center text-slate-400 py-12 text-sm">Sin datos en el período</p> }
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
      <!-- RANKING VENDEDORES -->
      <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/8 rounded-2xl overflow-hidden shadow-sm">
        <div class="px-5 py-3 bg-slate-50 dark:bg-slate-800 flex items-center gap-2">
          <mat-icon class="!text-base text-amber-500">emoji_events</mat-icon>
          <h3 class="font-black text-sm text-slate-800 dark:text-white">Ranking de vendedores</h3>
        </div>
        <div class="divide-y divide-slate-100 dark:divide-white/5">
          @for (v of data()!.por_vendedor; track v.vendedor; let i = $index) {
            <div class="px-5 py-3 flex items-center gap-3">
              <span class="w-6 h-6 rounded-full flex items-center justify-center text-xs font-black shrink-0"
                    [ngClass]="i===0 ? 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-400' : 'bg-slate-100 dark:bg-slate-800 text-slate-500'">{{ i+1 }}</span>
              <span class="flex-1 text-sm font-semibold truncate">{{ v.vendedor }}</span>
              <span class="text-xs text-slate-400">{{ v.pedidos }} ped.</span>
              <span class="font-black text-emerald-600 dark:text-emerald-400 text-sm">\${{ v.total.toFixed(0) }}</span>
            </div>
          }
          @if (!data()!.por_vendedor.length) { <p class="text-center text-slate-400 py-8 text-sm">Sin datos</p> }
        </div>
      </div>

      <!-- TOP PRODUCTOS -->
      <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/8 rounded-2xl overflow-hidden shadow-sm">
        <div class="px-5 py-3 bg-slate-50 dark:bg-slate-800">
          <h3 class="font-black text-sm text-slate-800 dark:text-white">Productos más vendidos</h3>
        </div>
        <div class="divide-y divide-slate-100 dark:divide-white/5">
          @for (p of data()!.top_productos; track p.producto) {
            <div class="px-5 py-3 flex items-center gap-3">
              <span class="flex-1 text-sm font-semibold truncate">{{ p.producto }}</span>
              <span class="text-xs text-slate-400">{{ p.unidades }} u.</span>
              <span class="font-black text-slate-700 dark:text-slate-200 text-sm">\${{ p.total.toFixed(0) }}</span>
            </div>
          }
          @if (!data()!.top_productos.length) { <p class="text-center text-slate-400 py-8 text-sm">Sin datos</p> }
        </div>
      </div>
    </div>

    <!-- TOP CLIENTES -->
    <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/8 rounded-2xl overflow-hidden shadow-sm">
      <div class="px-5 py-3 bg-slate-50 dark:bg-slate-800">
        <h3 class="font-black text-sm text-slate-800 dark:text-white">Clientes con más pedidos</h3>
      </div>
      <div class="divide-y divide-slate-100 dark:divide-white/5">
        @for (c of data()!.top_clientes; track c.cliente) {
          <div class="px-5 py-3 flex items-center gap-3">
            <mat-icon class="!text-base text-slate-400">storefront</mat-icon>
            <span class="flex-1 text-sm font-semibold truncate">{{ c.cliente }}</span>
            <span class="text-xs text-slate-400">{{ c.pedidos }} ped.</span>
            <span class="font-black text-emerald-600 dark:text-emerald-400 text-sm">\${{ c.total.toFixed(0) }}</span>
          </div>
        }
        @if (!data()!.top_clientes.length) { <p class="text-center text-slate-400 py-8 text-sm">Sin datos</p> }
      </div>
    </div>

    }
  </div>
</div>
  `,
})
export class VentasDashboardComponent implements OnInit {
  private http = inject(HttpClient);
  private API = `${environment.apiUrl}/api/vendedor`;

  loading = signal(true);
  data = signal<DashboardData | null>(null);

  desde = this._isoHace(30);
  hasta = this._isoHoy();

  porDiaChart: ChartData<'line'> = { labels: [], datasets: [] };
  porEstadoChart: ChartData<'doughnut'> = { labels: [], datasets: [] };

  lineOptions: ChartOptions<'line'> = { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } };
  doughnutOptions: ChartOptions<'doughnut'> = { responsive: true, maintainAspectRatio: false };

  ngOnInit() { this.cargar(); }

  private _isoHoy(): string { return new Date().toISOString().slice(0, 10); }
  private _isoHace(dias: number): string { const d = new Date(); d.setDate(d.getDate() - dias); return d.toISOString().slice(0, 10); }

  cargar() {
    this.loading.set(true);
    this.http.get<DashboardData>(`${this.API}/dashboard`, { params: { desde: this.desde, hasta: this.hasta } }).subscribe({
      next: d => {
        this.data.set(d);
        this.porDiaChart = {
          labels: d.por_dia.map(x => x.dia.slice(5)),
          datasets: [{ data: d.por_dia.map(x => x.total), label: 'Ventas', borderColor: '#059669', backgroundColor: 'rgba(5,150,105,0.15)', fill: true, tension: 0.3 }],
        };
        this.porEstadoChart = {
          labels: d.por_estado.map(x => x.estado),
          datasets: [{ data: d.por_estado.map(x => x.cantidad), backgroundColor: ['#94a3b8', '#3b82f6', '#10b981', '#ef4444', '#8b5cf6', '#f59e0b', '#14b8a6'] }],
        };
        this.loading.set(false);
      },
      error: () => { this.loading.set(false); },
    });
  }
}
