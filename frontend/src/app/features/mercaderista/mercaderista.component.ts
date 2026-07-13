import { Component, OnInit, Input, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTabsModule } from '@angular/material/tabs';
import { MatIconModule } from '@angular/material/icon';
import { MatBadgeModule } from '@angular/material/badge';
import { MatButtonModule } from '@angular/material/button';
import { MercRutaComponent } from './components/merc-ruta/merc-ruta.component';
import { MercVisitasComponent } from './components/merc-visitas/merc-visitas.component';
import { MercChatComponent } from './components/merc-chat/merc-chat.component';
import { MercPerfilComponent } from './components/merc-perfil/merc-perfil.component';
import { MercVisitPanelComponent } from './components/merc-visit-panel/merc-visit-panel.component';
import { OfflineQueueService } from './services/offline-queue.service';
import { MercUiService } from './services/merc-ui.service';

@Component({
  selector: 'app-mercaderista',
  standalone: true,
  imports: [
    CommonModule, MatTabsModule, MatIconModule, MatBadgeModule, MatButtonModule,
    MercRutaComponent, MercVisitasComponent, MercChatComponent, MercPerfilComponent, MercVisitPanelComponent
  ],
  templateUrl: './mercaderista.component.html',
  styleUrls: ['./mercaderista.component.scss']
})
export class MercaderistaComponent implements OnInit {
  @Input() titulo = 'Portal Mercaderista';

  isOnline = signal(navigator.onLine);
  pendingPhotos = signal(0);
  today = new Date().toLocaleDateString('es-VE', { weekday: 'long', day: 'numeric', month: 'long' });

  ui = inject(MercUiService);
  constructor(private offline: OfflineQueueService) {}

  ngOnInit(): void {
    this.offline.isOnline$.subscribe(v => this.isOnline.set(v));
    this.offline.pendingCount$.subscribe(v => this.pendingPhotos.set(v));
  }
}
