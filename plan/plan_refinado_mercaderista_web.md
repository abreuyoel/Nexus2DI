# Plan Refinado: Migración APK Mercaderista → Web

> **Fecha:** Agosto 2026  
> **Objetivo:** Cerrar las 7 brechas reales entre la APK Flutter y la versión web Angular  
> **APK Source:** `utilidades/APK-EPRAM/epran_mercaderista/lib/`  
> **Web Backend:** `backend/` (FastAPI + SQLAlchemy) — **~95% completo**  
> **Web Frontend:** `frontend/` (Angular 19+ Standalone + Tailwind CSS)

---

## Diagnóstico: Lo que YA existe vs. lo que falta

### Backend: Prácticamente completo
Todos los endpoints críticos existen y están funcionales. Ver archivos:

| Endpoint | Archivo | Línea |
|---|---|---|
| `GET /api/merc/programacion` | [`backend/app/mercaderista/endpoints/rutas.py`](backend/app/mercaderista/endpoints/rutas.py) | 69 |
| `GET /api/merc/chat/notificaciones` | [`backend/app/mercaderista/endpoints/chat.py`](backend/app/mercaderista/endpoints/chat.py) | 72 |
| `GET /api/merc/chat/grupos/{id}/visitas-activas` | [`backend/app/mercaderista/endpoints/chat.py`](backend/app/mercaderista/endpoints/chat.py) | 137 |
| `GET/POST /api/merc/chat/grupos/{id}/visitas/{vid}` | [`backend/app/mercaderista/endpoints/chat.py`](backend/app/mercaderista/endpoints/chat.py) | 148 |
| `GET /api/merc/visitas/{id}/detalle` | [`backend/app/mercaderista/endpoints/visitas.py`](backend/app/mercaderista/endpoints/visitas.py) | 141 |

### Frontend: Estado real vs. lo que decía el plan original

| Componente | Plan original decía | Estado REAL |
|---|---|---|
| PhotoGridComponent | 30% | **~85%** — 9 tipos, colores, badges, preview, delete |
| BalanceFormComponent | 60% | **~85%** — Categorías, Inv.Final auto, FIFO, SKU competencia |
| MercVisitPanelComponent | 40% | **~70%** — Tabs, activación/desactivación, chat, finalizar |
| MercVisitasComponent | 50% | **~75%** — Filtros, locales+servidor, estados, reabrir |
| MercChatComponent | 15% | **~50%** — 3 tabs, poll 30s, notificaciones navegador |

---

## Las 7 Brechas Reales

### Brecha 1: Flujo "Realizar Ruta" DESORDENADO

**Problema:** El dashboard fuerza un paso intermedio "Carga de Fotos Menu" (`activeScreen === 'carga-fotos-menu'`) que no existe en la APK. La APK va directo: Dashboard → Seleccionar Ruta → Ver PDVs → Iniciar Visita.

**Archivo raíz:** [`frontend/src/app/features/mercaderista/mercaderista.component.html`](frontend/src/app/features/mercaderista/mercaderista.component.html)

**Cambios necesarios:**
- [ ] Eliminar pantalla intermedia `carga-fotos-menu` (líneas 160-203 del HTML)
- [ ] Botón "Ejecutar Ruta" del dashboard debe abrir directamente el componente `MercRutaComponent`
- [ ] Agregar tabs "Ruta Fija" / "Ruta Variable" dentro de `MercRutaComponent`
- [ ] Agrupar PDVs por ruta con colores de prioridad: Alta=rojo, Media=naranja, Baja=gris
- [ ] Indicador visual de "Ruta Finalizada" cuando todos los PDVs están visitados
- [ ] Botón "Sincronizar" en dashboard que llame `GET /api/merc/programacion`

**Archivos a modificar:**
- `frontend/src/app/features/mercaderista/mercaderista.component.ts` — quitar `carga-fotos-menu` del `activeScreen`
- `frontend/src/app/features/mercaderista/mercaderista.component.html` — eliminar bloque `carga-fotos-menu`, simplificar navegación
- `frontend/src/app/features/mercaderista/components/merc-ruta/merc-ruta.component.ts` — agregar tabs fija/variable, colores prioridad, indicador ruta finalizada

---

### Brecha 2: Chat de Grupo INEXISTENTE

**Problema:** Los endpoints del backend para grupos de chat ya existen pero el frontend no tiene los componentes para mostrar:
- Chat general del grupo (mensajes con burbujas + autor + timestamp)
- Lista de visitas activas del grupo (hilos)
- Chat de hilo de visita dentro del grupo
- Miembros del grupo con roles

**Endpoints backend ya disponibles:**
- `GET /api/merc/chat/grupos/mis-grupos`
- `GET/POST /api/merc/chat/grupos/{id}/mensajes`
- `GET /api/merc/chat/grupos/{id}/miembros`
- `GET /api/merc/chat/grupos/{id}/visitas-activas`
- `GET/POST /api/merc/chat/grupos/{id}/visitas/{vid}`
- `POST /api/merc/chat/grupos/{id}/marcar-leido`

**Componentes a crear:**
- [ ] `GrupoDetalleComponent` — Chat general del grupo + lista de visitas activas con hilo
- [ ] `GrupoVisitaChatComponent` — Mensajes del hilo de visita dentro del grupo
- [ ] `MiembrosDialogComponent` — Modal/panel con lista de miembros, avatar por rol

**Archivos a crear:**
- `frontend/src/app/features/mercaderista/components/merc-chat/grupo-detalle/grupo-detalle.component.ts`
- `frontend/src/app/features/mercaderista/components/merc-chat/grupo-visita-chat/grupo-visita-chat.component.ts`
- `frontend/src/app/features/mercaderista/components/merc-chat/miembros-dialog/miembros-dialog.component.ts`

---

### Brecha 3: Visita Detalle (Review) INEXISTENTE

**Problema:** No hay vista de solo lectura para revisar una visita ya sincronizada con todas sus fotos y balances. El endpoint `GET /visitas/{id}/detalle` ya devuelve esta data.

**Cambios necesarios:**
- [ ] Grid de fotos con badges: ✅ Aprobada (verde), ❌ Rechazada (rojo, con motivo expandible), ⏳ Pendiente (gris)
- [ ] Cabecera: PDV, Cliente, Fecha, Hora, Mercaderista, Estado
- [ ] Tabla de balances guardados (solo lectura)
- [ ] Navegación: desde Historial, desde Rechazos, desde Notificaciones

**Archivo a crear:**
- `frontend/src/app/features/mercaderista/components/merc-visita-detalle/merc-visita-detalle.component.ts`

---

### Brecha 4: WebSocket — Solo POLLING

**Problema:** [`MercSocketService`](frontend/src/app/features/mercaderista/services/merc-socket.service.ts) usa `interval(8000)` polling en vez de WebSocket real. El backend ya tiene [`ConnectionManager` en `websockets/manager.py`](backend/app/websockets/manager.py) y [`realtime.py`](backend/app/services/realtime.py).

**8 eventos que la APK escucha y deben implementarse:**

| Evento | Cuándo se emite | Stream |
|---|---|---|
| `chat_message` | Nuevo mensaje en chat 1-a-1 | `chatMessage$` |
| `ai_alert` | AI aprueba/rechaza foto | `aiAlert$` |
| `foto_status` | Analista aprueba/rechaza foto | `fotoStatus$` |
| `visita_revisada` | Analista marca visita como Revisado | `visitaRevisada$` |
| `programacion_updated` | Backend actualiza programación | `programacionUpdated$` |
| `productos_updated` | Backend actualiza catálogo | `productosUpdated$` |
| `grupo_lectura` | Lectura en grupo general | `grupoLectura$` |
| `grupo_visita_lectura` | Lectura en hilo de visita | `grupoVisitaLectura$` |

**Archivo a modificar:**
- `frontend/src/app/features/mercaderista/services/merc-socket.service.ts` — reescribir con WebSocket nativo

---

### Brecha 5: PDV Activos — INLINE en dashboard

**Problema:** La vista de PDV Activos está hardcodeada como HTML inline en [`mercaderista.component.html` (líneas 246-285)](frontend/src/app/features/mercaderista/mercaderista.component.html).

**Cambios necesarios:**
- [ ] Extraer a componente separado `MercPdvActivosComponent`
- [ ] Agregar acciones: "Ir a Visita" (navega al cliente pendiente), "Desactivar PDV" (acción directa)

**Archivo a crear:**
- `frontend/src/app/features/mercaderista/components/merc-pdv-activos/merc-pdv-activos.component.ts`

---

### Brecha 6: Puntos de Interés — SIN MODAL

**Problema:** La APK muestra puntos de interés asociados a cada ruta. No existe en la web.

**Cambios necesarios:**
- [ ] Modal que muestre puntos de interés de una ruta (nombre, dirección, coordenadas)
- [ ] Accesible desde la vista de ruta

**Archivo a crear:**
- `frontend/src/app/features/mercaderista/components/merc-ruta/puntos-interes-modal.component.ts`

---

### Brecha 7: Pulido General y Badges

**Problema:** Faltan detalles de UX que la APK tiene.

**Cambios necesarios:**
- [ ] Badge de notificaciones pendientes en el shell principal (ícono de chat)
- [ ] Indicador visual de "Ruta Finalizada" (todos los PDVs visitados)
- [ ] Confirmaciones antes de: eliminar foto, finalizar visita, desactivar PDV
- [ ] Estados de carga: skeleton screens para listas
- [ ] Responsive: funcional en tablet (768px+) y desktop (1280px+)

**Archivos a modificar:**
- `frontend/src/app/layout/shell/shell.component.ts` — badge notificaciones
- Varios componentes — skeletons, confirmaciones

---

## Orden de Ejecución

```
FASE 1: Reordenar Flujo "Realizar Ruta"
  ├── Eliminar pantalla intermedia "Carga Fotos Menu"
  ├── Dashboard → directo a selección de ruta con tabs fija/variable
  ├── PDVs agrupados por ruta con colores de prioridad
  └── Indicador "Ruta Finalizada"

FASE 2: Chat de Grupo (3 componentes nuevos)
  ├── GrupoDetalleComponent (chat general + lista visitas activas)
  ├── GrupoVisitaChatComponent (hilo de visita en grupo)
  └── MiembrosDialogComponent (lista de miembros)

FASE 3: Visita Detalle (Review)
  └── MercVisitaDetalleComponent (fotos badgeadas + balances solo lectura)

FASE 4: WebSocket Real
  └── Reescribir MercSocketService con WebSocket nativo (8 eventos)

FASE 5: PDV Activos como componente
  └── MercPdvActivosComponent con acciones

FASE 6: Puntos de Interés modal
  └── PuntosInteresModalComponent

FASE 7: Pulido y Badges
  ├── Badge notificaciones en shell
  ├── Indicador ruta finalizada
  ├── Confirmaciones
  └── Responsive
```

---

## Resumen de Archivos

### A CREAR (6 archivos)

| Archivo | Fase |
|---|---|
| `.../merc-chat/grupo-detalle/grupo-detalle.component.ts` | F2 |
| `.../merc-chat/grupo-visita-chat/grupo-visita-chat.component.ts` | F2 |
| `.../merc-chat/miembros-dialog/miembros-dialog.component.ts` | F2 |
| `.../merc-visita-detalle/merc-visita-detalle.component.ts` | F3 |
| `.../merc-pdv-activos/merc-pdv-activos.component.ts` | F5 |
| `.../merc-ruta/puntos-interes-modal.component.ts` | F6 |

### A MODIFICAR (5 archivos)

| Archivo | Cambio | Fase |
|---|---|---|
| `.../mercaderista.component.ts` | Eliminar carga-fotos-menu, simplificar screen router | F1 |
| `.../mercaderista.component.html` | Eliminar bloque carga-fotos-menu, navegación directa | F1 |
| `.../merc-ruta/merc-ruta.component.ts` | Tabs fija/variable, colores prioridad, ruta finalizada | F1 |
| `.../services/merc-socket.service.ts` | WebSocket nativo (8 eventos) | F4 |
| `.../layout/shell/shell.component.ts` | Badge notificaciones | F7 |
