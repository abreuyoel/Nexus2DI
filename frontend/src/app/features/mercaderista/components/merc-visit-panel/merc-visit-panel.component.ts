import { Component, Input, signal, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTabsModule } from '@angular/material/tabs';
import { MercUiService, ActiveVisit } from '../../services/merc-ui.service';
import { PhotoGridComponent } from './components/photo-grid/photo-grid.component';
import { BalanceFormComponent } from './components/balance-form/balance-form.component';
import { MercSocketService } from '../../services/merc-socket.service';

@Component({
  selector: 'app-merc-visit-panel',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatButtonModule, MatTabsModule, PhotoGridComponent, BalanceFormComponent],
  template: `
    <div class="fixed inset-0 z-[100] bg-white dark:bg-slate-950 flex flex-col animate-in slide-in-from-right-full duration-300">
      
      <!-- Header -->
      <div class="bg-white dark:bg-slate-900 border-b border-slate-100 dark:border-white/5 px-6 py-4 flex items-center justify-between shadow-sm shrink-0">
        <div class="flex items-center gap-3">
          <button (click)="close()" class="w-10 h-10 rounded-xl bg-slate-50 dark:bg-white/5 flex items-center justify-center text-slate-500">
            <mat-icon>arrow_back</mat-icon>
          </button>
          <div class="flex flex-col min-w-0">
            <span class="text-[9px] font-black text-primary-500 uppercase tracking-widest truncate">{{ visit?.cliente }}</span>
            <h3 class="font-bold text-slate-800 dark:text-white truncate tracking-tight text-sm">{{ visit?.pdv_nombre }}</h3>
          </div>
        </div>
        
        <div class="flex items-center gap-2">
          <div class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
          <span class="text-[10px] font-black uppercase tracking-widest text-emerald-500">Activa</span>
        </div>
      </div>

      <!-- Content (Scrollable) -->
      <div class="flex-grow overflow-y-auto">
        <mat-tab-group mat-stretch-tabs="false" mat-align-tabs="start" class="merc-visit-tabs">
          
          <!-- FOTOS -->
          <mat-tab>
            <ng-template mat-tab-label>
              <div class="flex items-center gap-2">
                <mat-icon class="!text-sm">photo_camera</mat-icon>
                <span class="text-[10px] font-black uppercase tracking-widest">Fotos</span>
              </div>
            </ng-template>
            <div class="p-4">
              <app-photo-grid [visitaId]="visit?.id_visita!"></app-photo-grid>
            </div>
          </mat-tab>

          <!-- DATA (Balances) -->
          <mat-tab>
            <ng-template mat-tab-label>
              <div class="flex items-center gap-2">
                <mat-icon class="!text-sm">inventory_2</mat-icon>
                <span class="text-[10px] font-black uppercase tracking-widest">Data</span>
              </div>
            </ng-template>
            <div class="p-4">
              <app-balance-form [visitaId]="visit?.id_visita!" [idCliente]="visit?.id_cliente!"></app-balance-form>
            </div>
          </mat-tab>

          <!-- CHAT -->
          <mat-tab>
            <ng-template mat-tab-label>
              <div class="flex items-center gap-2">
                <mat-icon class="!text-sm">chat</mat-icon>
                <span class="text-[10px] font-black uppercase tracking-widest">Chat</span>
              </div>
            </ng-template>
            <div class="p-4 h-[60vh]">
               <div class="h-full flex flex-col items-center justify-center opacity-30 gap-4">
                 <mat-icon class="!text-5xl">chat</mat-icon>
                 <p class="font-bold">Chat de la visita activa</p>
               </div>
            </div>
          </mat-tab>

        </mat-tab-group>
      </div>

      <!-- Footer Info -->
      <div class="p-4 bg-slate-50 dark:bg-slate-900/50 border-t border-slate-100 dark:border-white/5 text-center">
         <p class="text-[9px] font-black text-slate-400 uppercase tracking-widest">ID Visita: {{ visit?.id_visita }}</p>
      </div>
    </div>
  `,
  styles: [`
    :host { display: block; }
    .merc-visit-tabs ::ng-deep {
      .mat-mdc-tab-header { background: white; .dark & { background: #0f172a; } }
      .mat-mdc-tab { height: 48px; min-width: 0; padding: 0 16px; }
    }
  `]
})
export class MercVisitPanelComponent implements OnInit {
  @Input() visit: ActiveVisit | null = null;
  
  private ui = inject(MercUiService);
  private socket = inject(MercSocketService);

  ngOnInit() {
    if (this.visit) {
      // this.socket.joinChat(this.visit.id_visita);
    }
  }

  close() {
    this.ui.closeVisit();
  }
}
