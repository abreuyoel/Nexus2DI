# Plan de Migración: APK EPRAN → Web (nexti_web_v2)

> **Objetivo:** Migrar TODA la funcionalidad de la APK Flutter (APK-EPRAM/epran_mercaderista)  
> a la versión web (nexti_web_v2), **excluyendo funciones offline** (SQLite, SyncService, etc.)
>
> **Fecha:** Agosto 2026  
> **APK Source:** `utilidades/APK-EPRAM/epran_mercaderista/lib/`  
> **Web Backend:** `backend/` (FastAPI + SQLAlchemy)  
> **Web Frontend:** `frontend/` (Angular 19+ Standalone + Tailwind CSS)  
> **DB:** SQL Server (itam_db) vía SQLAlchemy

---

## 🔍 Análisis Detallado del Estado Actual

### Arquitectura de la APK (Flutter + Provider + SQLite Offline-First)

La APK sigue un patrón **Offline-First** con tres capas claras:

| Capa | Archivos clave | Función |
|---|---|---|
| **Core Services** | `api_service`, `database_service`, `sync_service`, `socket_service`, `photo_service`, `location_service` | Infraestructura transversal |
| **Providers** | `gestion_provider`, `chat_provider`, `rutas_data_provider`, `auth_provider` | Estado global + lógica de negocio |
| **Screens** | 9 pantallas principales | UI y flujo de usuario |

En la web, los **Providers** se mapean a **Servicios Angular** + **Signals**, y **DatabaseService/SyncService** se reemplazan por llamadas directas a la API (con `OfflineQueueService` como respaldo mínimo).

---

### Lo que YA existe en el Backend (`/api/merc/`) — VERIFICADO

| Endpoint | Método | Estado | Observaciones |
|---|---|---|---|
| `/api/merc/me` | GET | ✅ | Perfil con rutas asignadas |
| `/api/merc/rutas` | GET | ✅ | Rutas del día con PDVs, clientes, estado visita |
| `/api/merc/pdv-activos` | GET | ✅ | PDVs con trabajo pendiente + clientes listos/pendientes |
| `/api/merc/visitas/iniciar` | POST | ✅ | Crea o devuelve visita existente del día |
| `/api/merc/visitas` | GET | ✅ | Historial con filtros fecha_inicio/fecha_fin |
| `/api/merc/visitas/{id}/fotos` | GET + POST | ✅ | GET: agrupadas por tipo (9 tipos). POST: upload con tipo_foto |
| `/api/merc/visitas/{id}/balances` | POST | ✅ | Guarda lista de productos con todos los campos |
| `/api/merc/visitas/{id}/finalizar` | POST | ✅ | Cierra ciclo de vida de visita |
| `/api/merc/visitas/{id}/productos` | GET | ✅ | Filtra por id_cliente opcional |
| `/api/merc/visitas/{id}/detalle` | GET | ✅ | Metadata + fotos con revisión + balances |
| `/api/merc/pdv/activar` | POST | ✅ | Activar PDV |
| `/api/merc/pdv/desactivar` | POST | ✅ | Desactivar PDV |
| `/api/merc/pdv/{id}/validar-cierre` | GET | ✅ | Validar cierre de PDV |
| `/api/merc/chat/inbox` | GET | ✅ | Conversaciones agrupadas por visita |
| `/api/merc/chat/visitas/{id}` | GET | ✅ | Mensajes de una visita |
| `/api/merc/chat/enviar` | POST | ✅ | Enviar mensaje + emitir WebSocket |
| `/api/merc/chat/notificaciones` | GET | ✅ | Rechazos, aprobaciones, visitas revisadas |
| `/api/merc/chat/grupos/mis-grupos` | GET | ✅ | Grupos del mercaderista con no-leídos |
| `/api/merc/chat/grupos/{id}/mensajes` | GET + POST | ✅ | Chat general del grupo |
| `/api/merc/chat/grupos/{id}/miembros` | GET | ✅ | Miembros del grupo |
| `/api/merc/chat/grupos/{id}/visitas-activas` | GET | ✅ | Visitas con hilo de chat en el grupo |
| `/api/merc/chat/grupos/{id}/visitas/{vid}` | GET + POST | ✅ | Hilo de chat de visita en grupo |
| `/api/merc/chat/grupos/{id}/marcar-leido` | POST | ✅ | Marcar lectura en grupo |
| `/api/merc/productos` | GET | ✅ | Catálogo completo agrupado por categorías |

### Lo que YA existe en el Frontend (Angular)

| Componente | Estado real | Qué falta |
|---|---|---|
| `LoginMercaderistaComponent` | ✅ Completo | Nada crítico |
| `MercaderistaComponent` | ⚠️ Shell funcional | Dashboard con cards de acceso rápido, badge notificaciones, botón sync, header con nombre |
| `MercRutaComponent` | ⚠️ Parcial (60%) | Agrupar por ruta, prioridades con colores, estado activación, ruta finalizada, puntos interés modal, WebSocket refresh |
| `MercVisitasComponent` | ⚠️ Parcial (50%) | Filtros fecha/cliente/PDV, combinación local+servidor, contadores pendientes, estados visuales, badge rechazos, WebSocket |
| `MercVisitPanelComponent` | ⚠️ Parcial (40%) | Solo estructura de tabs. Faltan: 9 tipos de foto, activación/desactivación, chat integrado, FIFO/Limpieza checks |
| `BalanceFormComponent` | ⚠️ Parcial (60%) | Falta: agrupación por categorías del cliente, búsqueda, cálculo automático Inv.Final, SKU competencia |
| `PhotoGridComponent` | ⚠️ Parcial (30%) | Solo muestra 3 tipos genéricos. Faltan los 9 tipos reales, vista previa, eliminación, badge obligatorio |
| `MercChatComponent` | 🔴 Mínimo (15%) | Solo estructura con search placeholder. Falta: 3 tabs (conversaciones/rechazos/notificaciones), inbox real, WebSocket |
| `MercPerfilComponent` | ✅ Completo | Datos personales + rutas asignadas |
| `OfflineQueueService` | ✅ Completo | Cola offline con IndexedDB |
| `MercSocketService` | ⚠️ Parcial | Solo maneja chat_message. Faltan: ai_alert, foto_status, visita_revisada, programacion_updated, productos_updated, grupo_lectura, grupo_visita_lectura |
| `MercUiService` | ✅ Completo | Estado UI compartido (activeVisit signal) |

---

## 🗂️ Mapeo Completo APK → Web

```
APK Flutter                                     → Web Equivalent
─────────────────────────────────────────────────────────────────────
lib/main.dart                                   → frontend/src/main.ts + app.config.ts

lib/core/constants/app_config.dart              → frontend/src/environments/
lib/core/models/chat_models.dart                → Interfaces TypeScript en feature/mercaderista/models/
lib/core/theme/app_theme.dart                   → tailwind.config.js + estilos globales
lib/core/utils/dia_semana.dart                  → Util compartido (simple)

lib/core/services/api_service.dart              → frontend/src/app/core/services/api.service.ts
lib/core/services/socket_service.dart           → merc-socket.service.ts ⚠️ (faltan eventos)
lib/core/services/connectivity_service.dart     → ❌ OFFLINE (navigator.onLine nativo)
lib/core/services/database_service.dart         → ❌ OFFLINE (SQLite → API calls directas)
lib/core/services/ecc_service.dart              → ❌ OFFLINE (HTTPS)
lib/core/services/location_service.dart         → ❌ OFFLINE (navigator.geolocation)
lib/core/services/logger_service.dart           → ❌ OFFLINE (console.log)
lib/core/services/photo_service.dart            → ❌ OFFLINE (backend procesa)
lib/core/services/secure_storage_service.dart   → ❌ OFFLINE (localStorage + JWT)
lib/core/services/security_service.dart         → ❌ OFFLINE (no aplica web)
lib/core/services/sync_service.dart             → ❌ OFFLINE → OfflineQueueService (simplificado)

lib/presentation/auth/login_screen.dart         → login-mercaderista.component ✅
lib/presentation/auth/providers/auth_provider   → auth.service.ts ✅

lib/presentation/dashboard/dashboard_screen     → mercaderista.component ⚠️ (solo shell)

lib/presentation/gestion/mis_rutas_screen       → merc-ruta.component ⚠️ (60%)
lib/presentation/gestion/mis_visitas_screen     → merc-visitas.component ⚠️ (50%)
lib/presentation/gestion/visita_screen (2314L)  → merc-visit-panel.component ⚠️ (40%)
lib/presentation/gestion/visita_detalle_screen  → 🔴 NO EXISTE
lib/presentation/gestion/balance_screen         → balance-form.component ⚠️ (60%)
lib/presentation/gestion/pdv_activos_screen     → 🔴 NO EXISTE
lib/presentation/gestion/carga_fotos_menu       → 🔴 NO EXISTE (simplificar en dashboard)
lib/presentation/gestion/widgets/custom_camera  → ❌ OFFLINE (<input type="file">)
lib/presentation/gestion/widgets/puntos_interes → 🔴 NO EXISTE
lib/presentation/gestion/widgets/seleccionar_cliente → ✅ (integrado en merc-ruta)

lib/presentation/gestion/providers/gestion_provider → MercUiService + nuevos servicios
lib/presentation/gestion/providers/rutas_data_provider → Nuevo MercRutasService

lib/presentation/chat/chat_inbox_screen (3 tabs)→ merc-chat.component 🔴 (15%)
lib/presentation/chat/chat_room_screen          → 🔴 Integrado parcialmente en visit-panel
lib/presentation/chat/grupo_detalle_screen      → 🔴 NO EXISTE
lib/presentation/chat/grupo_visita_chat_screen  → 🔴 NO EXISTE
lib/presentation/chat/widgets/miembros_dialog   → 🔴 NO EXISTE
lib/presentation/chat/providers/chat_provider   → 🔴 NO EXISTE (nuevo MercChatService)

lib/presentation/sync/sync_status_screen        → 🔴 NO EXISTE (upload status)
```

---

## 📐 Diagrama de Flujo Operativo (Web)

```
┌──────────────────────────────────────────────────────────────────┐
│                        LOGIN (JWT)                               │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│  DASHBOARD                                                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │Ruta Fija │ │Ruta Var. │ │PDV Activos│ │Historial │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│  ┌──────────┐ ┌──────────┐                                      │
│  │  Chat    │ │Sync/Fotos│  + Badge notificaciones              │
│  └──────────┘ └──────────┘                                      │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│  RUTAS (tabs: Fija / Variable)                                   │
│  ┌──────────────────────────────────────────────┐               │
│  │ RUTA 1 - Norte                                │               │
│  │  ├─ 🟢 Super Líder Centro (Alta)              │               │
│  │  │   └─ Coca-Cola ✓  Pepsi ○                 │               │
│  │  ├─ 🔴 Éxito San Diego (Media)                │               │
│  │  └─ ⚪ Jumbo Norte (Baja)                     │               │
│  └──────────────────────────────────────────────┘               │
│  Seleccionar PDV → Seleccionar Cliente → INICIAR VISITA         │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│  VISITA (tabs: Fotos | Balance | Chat)                           │
│                                                                   │
│  ┌─ FOTOS ─────────────────────────────────────────────────┐    │
│  │  1. Gestión (Antes)      4. Exhibición Adicional (Antes)│    │
│  │  2. Gestión (Después)    5. ⭐ Activación (OBLIGATORIA) │    │
│  │  3. Precios              6. ⭐ Desactivación (OBLIG.)   │    │
│  │                           7. Exhibición Adicional (Desp.)│   │
│  │                           8. Material POP (Antes)       │    │
│  │                           9. Material POP (Después)     │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─ BALANCE ───────────────────────────────────────────────┐    │
│  │  Agrupado por categoría del cliente                       │    │
│  │  Campos: Inv.Inicial | Inv.Depósito | Inv.Final | Caras  │    │
│  │          Precio Bs | SKU Competencia | FEFO              │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─ ACTIVACIÓN PDV (si es primer cliente del punto) ────────┐   │
│  │  [ ] ¿FIFO correcto?   [ ] ¿Limpieza correcta?           │   │
│  │  📸 Foto de Activación (OBLIGATORIA)                      │   │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─ DESACTIVACIÓN PDV (si es último cliente pendiente) ─────┐   │
│  │  📸 Foto de Desactivación (OBLIGATORIA)                   │   │
│  │  Validación de cierre previa                              │   │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─ CHAT ───────────────────────────────────────────────────┐   │
│  │  Chat 1-a-1 con analista para esta visita                 │   │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                   │
│  [ FINALIZAR VISITA ]                                            │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│  HISTORIAL / DETALLE VISITA                                       │
│  • Visitas del servidor + locales pendientes                     │
│  • Fotos con badge: ✅ Aprobada ❌ Rechazada ⏳ Pendiente        │
│  • Motivo de rechazo expandible                                  │
│  • Balances guardados (solo lectura)                             │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Arquitectura del Sistema de Chat (3 Niveles)

La APK maneja **tres sistemas de chat independientes** que deben reflejarse en la web:

```
NIVEL 1: Chat 1-a-1 (Visita/Cliente)
  ├── Tabla: CHAT_MENSAJES (chat_mensajes)
  ├── Contexto: Una visita específica o un cliente
  ├── Participantes: Mercaderista ↔ Analista
  ├── WebSocket: chat_message, foto_status
  └── Lectura: leido_por, fecha_lectura (simple)

NIVEL 2: Chat de Grupo General
  ├── Tabla: CHAT_GRUPOS + CHAT_MENSAJES_GRUPO (chat_grupos_mensajes)
  ├── Tipos: "operativo" (Equipo) | "operativo_cliente" (Equipo+Cliente)
  ├── Participantes: Múltiples (analistas, mercaderistas, clientes)
  ├── WebSocket: grupo_lectura
  └── Lectura: CHAT_GRUPO_LECTURA + CHAT_GRUPO_MENSAJE_LECTURA (múltiples lectores)

NIVEL 3: Chat de Grupo-Visita (Hilo por visita activa)
  ├── Tabla: CHAT_MENSAJES_GRUPO_VISITA (chat_mensajes_grupo_visita)
  ├── Contexto: Una visita específica DENTRO de un grupo
  ├── Visible: Solo mientras la visita no esté "Revisado"
  ├── WebSocket: grupo_visita_lectura
  └── Lectura: CHAT_GRUPO_VISITA_LECTURA
```

---

# 📅 PLAN POR FASES (REESCRITO)

---

## 🟢 FASE 1: BACKEND — Endpoints Faltantes y Verificación

> **Prioridad:** CRÍTICA  
> **Duración:** 2-3 días  
> **Dependencias:** Ninguna — todo el frontend depende de esto

### 1.1 Endpoint: Programación Completa del Día

**Archivo APK:** `rutas_data_provider.dart → getProgramacion()`  
**Propósito:** Descargar TODA la data que el mercaderista necesita para operar (rutas, PDVs, clientes, productos) en una sola llamada. En la APK esto se cachea en SQLite; en la web se llama al iniciar el dashboard y se refresca vía WebSocket.

**Endpoint:** `GET /api/merc/programacion`

**Response:**
```json
{
  "fecha": "2026-08-10",
  "mercaderista": { "id": 1, "nombre": "Juan Pérez", "cedula": "V-12345678" },
  "rutas": [
    {
      "id_ruta": 1,
      "tipo": "fija",
      "nombre": "RUTA NORTE",
      "pdvs": [
        {
          "id_punto": "PT-001",
          "nombre": "Super Líder Centro",
          "cadena": "Líder",
          "direccion": "Av. Principal, Centro",
          "latitud": "10.4806",
          "longitud": "-66.9036",
          "prioridad": "Alta",
          "activado": false,
          "clientes": [
            {
              "id_cliente": 10,
              "nombre": "Coca-Cola",
              "visitado": false,
              "visita_id": null
            }
          ]
        }
      ]
    }
  ],
  "productos": [
    {
      "id_producto": 1,
      "sku": "CC-2L-001",
      "nombre": "Coca-Cola 2L",
      "fabricante": "Coca-Cola Company",
      "categoria_id": 5,
      "categoria_nombre": "Bebidas Carbonatadas",
      "precio_base_bs": 2.50,
      "precio_base_ds": 2.50
    }
  ]
}
```

**Tablas:** `MERCADERISTAS_RUTAS`, `RUTAS_NUEVAS`, `PUNTOS_INTERES`, `CLIENTES`, `CATEGORIAS_CLIENTES`, `PRODUCTS`

**Archivos:**
- `backend/app/mercaderista/endpoints/rutas.py` → agregar `GET /programacion`
- `backend/app/mercaderista/services/ruta_service.py` → agregar `get_programacion_completa()`

---

### 1.2 Endpoint: Notificaciones (Rechazos + Aprobaciones + Visitas Revisadas)

**Archivo APK:** `chat_provider.dart → fetchRechazos()`  
**Propósito:** La APK tiene un tab "Rechazos" y otro "Notificaciones" con fotos rechazadas por AI/analista, fotos aprobadas y visitas marcadas como revisadas.

**Endpoint:** `GET /api/merc/notificaciones`

**Response:**
```json
{
  "rechazos": [
    {
      "id_foto": 123,
      "id_visita": 456,
      "tipo_foto": "activacion",
      "url": "https://...",
      "motivo_rechazo": "Foto borrosa, no se aprecia el producto",
      "fecha_rechazo": "2026-08-10T10:00:00Z",
      "leido": false,
      "punto_nombre": "Super Líder Centro",
      "cliente_nombre": "Coca-Cola"
    }
  ],
  "aprobaciones": [
    {
      "id_foto": 124,
      "id_visita": 456,
      "tipo_foto": "precios",
      "fecha_aprobacion": "2026-08-10T09:30:00Z",
      "leido": false,
      "punto_nombre": "Super Líder Centro"
    }
  ],
  "visitas_revisadas": [
    {
      "id_visita": 456,
      "punto_nombre": "Super Líder Centro",
      "fecha_revision": "2026-08-10T11:00:00Z",
      "leido": false
    }
  ]
}
```

**Tablas:** `FOTOS` (campos `ia_revision`, `motivo_rechazo`, `fecha_revision`), `VISITAS` (campo `estado_revision`)

**Archivos:**
- `backend/app/mercaderista/endpoints/chat.py` → agregar `GET /notificaciones`
- `backend/app/mercaderista/services/chat_service.py` → agregar `get_notificaciones()`

**Endpoints auxiliares:**
- `POST /api/merc/notificaciones/rechazo/{id_foto}/leido` → marcar rechazo como leído
- `POST /api/merc/notificaciones/aprobacion/{id_foto}/leido` → marcar aprobación como leída
- `POST /api/merc/notificaciones/visita/{id_visita}/leido` → marcar visita revisada como leída

---

### 1.3 Endpoints: Grupos de Chat

**Archivos APK:** `grupo_detalle_screen.dart`, `grupo_visita_chat_screen.dart`, `chat_provider.dart`  
**Propósito:** Soportar los 3 niveles del sistema de chat (ver diagrama arriba).

**Endpoints necesarios:**

| Endpoint | Método | Propósito |
|---|---|---|
| `/api/merc/chat/grupos` | GET | Listar grupos del mercaderista |
| `/api/merc/chat/grupos/{id_grupo}/mensajes` | GET | Mensajes del chat general del grupo |
| `/api/merc/chat/grupos/{id_grupo}/enviar` | POST | Enviar mensaje al grupo |
| `/api/merc/chat/grupos/{id_grupo}/visitas-activas` | GET | Visitas no revisadas del grupo (hilos) |
| `/api/merc/chat/grupos/{id_grupo}/visitas/{id_visita}/mensajes` | GET | Mensajes del hilo de visita dentro del grupo |
| `/api/merc/chat/grupos/{id_grupo}/visitas/{id_visita}/enviar` | POST | Enviar mensaje al hilo de visita |
| `/api/merc/chat/grupos/{id_grupo}/miembros` | GET | Miembros del grupo |
| `/api/merc/chat/grupos/{id_grupo}/marcar-leido` | POST | Marcar lectura en grupo general |
| `/api/merc/chat/grupos/{id_grupo}/visitas/{id_visita}/marcar-leido` | POST | Marcar lectura en hilo de visita |

**Tablas:** `CHAT_GRUPOS`, `CHAT_GRUPO_MENSAJES` (`chat_grupos_mensajes`), `CHAT_MENSAJES_GRUPO_VISITA`, `CHAT_GRUPO_LECTURA`, `CHAT_GRUPO_MENSAJE_LECTURA`, `CHAT_GRUPO_VISITA_LECTURA`

**Archivos:**
- `backend/app/mercaderista/endpoints/chat.py` → agregar todos los endpoints de grupo
- `backend/app/mercaderista/services/chat_service.py` → agregar métodos de grupo
- `backend/app/services/chat_grupos_membresia.py` → verificar/reutilizar lógica existente

---

### 1.4 Endpoint: Detalle de Visita (Review)

**Archivo APK:** `visita_detalle_screen.dart → getDataVisita(id)`  
**Propósito:** Vista de solo lectura de una visita ya sincronizada con todas sus fotos (incluyendo estado de revisión AI) y balances.

**Endpoint:** `GET /api/merc/visitas/{id}/detalle`

**Response:**
```json
{
  "id_visita": 456,
  "fecha_inicio": "2026-08-10T08:00:00Z",
  "fecha_fin": "2026-08-10T08:45:00Z",
  "estado": "completado",
  "estado_revision": "revisado",
  "punto": { "id": "PT-001", "nombre": "Super Líder Centro" },
  "cliente": { "id": 10, "nombre": "Coca-Cola" },
  "mercaderista": { "id": 1, "nombre": "Juan Pérez" },
  "fotos": [
    {
      "id": 123,
      "tipo": "activacion",
      "url": "https://...",
      "thumbnail_url": "https://...",
      "estado_revision": "rechazado",
      "motivo_rechazo": "Foto borrosa",
      "fecha_subida": "2026-08-10T08:05:00Z"
    }
  ],
  "balances": [
    {
      "id_producto": 1,
      "sku": "CC-2L-001",
      "nombre": "Coca-Cola 2L",
      "inv_inicial": 50,
      "inv_deposito": 10,
      "inv_final": 40,
      "caras": 5,
      "precio_bs": 2.50,
      "precio_ds": 2.50,
      "fifo": "2026-12-01"
    }
  ]
}
```

**Archivos:**
- `backend/app/mercaderista/endpoints/visitas.py` → agregar `GET /visitas/{id}/detalle`
- `backend/app/mercaderista/services/visita_service.py` → agregar `get_detalle_visita()`

---

### 1.5 WebSocket: Completar Eventos

**Archivo APK:** `socket_service.dart`  
**Estado actual del backend:** `backend/app/websockets/manager.py` tiene `ConnectionManager` con broadcast. `backend/app/services/realtime.py` tiene `notify_event()`.

**Eventos que la APK escucha y el backend DEBE emitir:**

| Evento | Cuándo se emite | Prioridad |
|---|---|---|
| `chat_message` | Nuevo mensaje en chat 1-a-1 | ✅ Ya existe |
| `ai_alert` | AI aprueba/rechaza una foto automáticamente | 🔴 FALTA |
| `foto_status` | Analista aprueba/rechaza manualmente una foto | 🔴 FALTA |
| `visita_revisada` | Analista marca visita como "Revisado" | 🔴 FALTA |
| `programacion_updated` | Backend actualiza la programación del día | 🔴 FALTA |
| `productos_updated` | Backend actualiza el catálogo de productos | 🔴 FALTA |
| `grupo_lectura` | Alguien lee un mensaje en el grupo general | 🔴 FALTA |
| `grupo_visita_lectura` | Alguien lee un mensaje en el hilo de visita | 🔴 FALTA |

**Dónde emitir cada evento:**
- `ai_alert` → en el endpoint/webhook que recibe la revisión de AI (si existe)
- `foto_status` → en `backend/app/mercaderista/endpoints/visitas.py` al aprobar/rechazar foto
- `visita_revisada` → en el endpoint del analista que marca revisión
- `programacion_updated` → en el endpoint que modifica la programación
- `productos_updated` → en el endpoint que modifica el catálogo
- `grupo_lectura` / `grupo_visita_lectura` → en los endpoints de marcar-leido de grupo

**Archivos:**
- `backend/app/services/realtime.py` → verificar/agregar funciones helper por tipo de evento
- `backend/app/mercaderista/endpoints/visitas.py` → emitir `foto_status`
- `backend/app/mercaderista/endpoints/chat.py` → emitir `grupo_lectura`, `grupo_visita_lectura`

---

## 🟡 FASE 2: FRONTEND — Pantalla de Visita (LA MÁS CRÍTICA)

> **Prioridad:** MÁXIMA — es el 80% del trabajo del mercaderista  
> **Duración:** 5-6 días  
> **Dependencias:** Fase 1 completada (endpoints verificados)

### 2.1 PhotoGrid: Los 9 Tipos de Foto Reales

**Archivo APK:** `visita_screen.dart` (líneas 1-2004, especialmente `_buildFotoSections()`)  

La APK define **9 tipos de foto** con constantes `AppConfig.tiposFoto`. Cada tipo tiene:
- `codigo` (ej: `gestion_antes`)
- `label` (ej: `Gestión (Antes)`)
- `obligatorio` (solo `activacion` y `desactivacion` son obligatorios)
- `color` asociado

| # | Código | Label | Obligatorio | Color APK |
|---|---|---|---|---|
| 1 | `gestion_antes` | Gestión (Antes) | No | Azul |
| 2 | `gestion_despues` | Gestión (Después) | No | Verde |
| 3 | `precios` | Precios | No | Naranja |
| 4 | `exhibicion_antes` | Exhibición Adicional (Antes) | No | Púrpura |
| 5 | `activacion` | **Activación** | **SÍ** | Rojo |
| 6 | `desactivacion` | **Desactivación** | **SÍ** | Rojo |
| 7 | `exhibicion_despues` | Exhibición Adicional (Después) | No | Púrpura |
| 8 | `pop_antes` | Material POP (Antes) | No | Amarillo |
| 9 | `pop_despues` | Material POP (Después) | No | Amarillo |

**Tareas:**
- [ ] Reemplazar los 3 tipos genéricos actuales por los 9 reales
- [ ] Badge "(obligatorio)" en `activacion` y `desactivacion`
- [ ] Color del borde basado en tipo
- [ ] Upload vía `<input type="file" accept="image/*">` (no cámara nativa)
- [ ] Vista previa con thumbnail antes de confirmar
- [ ] Eliminación de fotos locales antes de subir
- [ ] Indicador visual de "falta foto obligatoria" si no se ha subido

**Archivos:**
- `frontend/src/app/features/mercaderista/components/merc-visit-panel/components/photo-grid/photo-grid.component.ts` → **reescritura mayor**

---

### 2.2 Flujo de Activación / Desactivación de PDV

**Archivo APK:** `visita_screen.dart` (cards de activación/desactivación) + `gestion_provider.dart` (lógica `_esUltimoCliente`, `_puntoActivadoHoy`, `_fifoOk`, `_limpiezaOk`)

**Reglas de negocio (críticas):**

1. **Activación:** Solo si es el PRIMER cliente del PDV en ser visitado hoy
   - Se requieren 2 checks locales (NO se persisten): "¿FIFO correcto?" y "¿Limpieza correcta?"
   - Foto de activación obligatoria
   - `POST /api/merc/pdv/activar`

2. **Desactivación:** Solo si es el ÚLTIMO cliente pendiente del PDV
   - Se requiere validación de cierre: `GET /api/merc/pdv/{id}/validar-cierre`
   - Foto de desactivación obligatoria
   - `POST /api/merc/pdv/desactivar`

3. **Motivo de no activación:** Si el mercaderista no puede activar, debe registrar un motivo

**Tareas:**
- [ ] Card de Activación con checks + foto + botón
- [ ] Card de Desactivación con validación + foto + botón
- [ ] Determinar `_esUltimoCliente` consultando el backend
- [ ] Determinar `_puntoActivadoHoy` consultando el backend
- [ ] Los checks FIFO/Limpieza son solo estado local del componente (no API)
- [ ] Modal de "Motivo de no activación" si aplica

---

### 2.3 Chat de Visita Integrado

**Archivo APK:** `chat_room_screen.dart` + integración en `visita_screen.dart`

**Tareas:**
- [ ] Lista de mensajes con burbujas (enviado vs recibido)
- [ ] Timestamps: "10:30 AM", "Ayer 3:15 PM", "12 Ago 2025"
- [ ] Envío con Enter (y botón)
- [ ] Auto-scroll al último mensaje
- [ ] WebSocket: recibir mensajes en tiempo real
- [ ] Indicador de mensajes no leídos

---

### 2.4 Finalización de Visita

**Archivo APK:** `gestion_provider.dart → finalizarVisita()`

**Tareas:**
- [ ] Botón "Finalizar Visita" con confirmación
- [ ] Validar que estén todas las fotos obligatorias
- [ ] Validar que se haya guardado al menos un balance
- [ ] `POST /api/merc/visitas/{id}/finalizar`
- [ ] Al finalizar, volver a la pantalla de rutas y refrescar

**Archivos a modificar:**
- `frontend/src/app/features/mercaderista/components/merc-visit-panel/merc-visit-panel.component.ts` → **reescritura mayor**
- `frontend/src/app/features/mercaderista/components/merc-visit-panel/merc-visit-panel.component.html` → nuevo template completo

---

## 🟡 FASE 2B: Balance Form (Completar)

### 2.5 BalanceForm: Agrupación por Categorías del Cliente

**Archivo APK:** `balance_screen.dart` (agrupación por `CATEGORIAS_CLIENTES`, no por `PRODUCTS`)

**Lógica crítica de la APK:**
- Los productos se agrupan por **categorías asignadas al cliente** (`CATEGORIAS_CLIENTES`), no por categorías del producto
- Cada categoría es una sección expandible
- Dentro de cada categoría, los productos pertenecen a esa categoría del cliente
- Búsqueda de productos con filtro local
- Los campos son: Inv.Inicial, Inv.Depósito, Inv.Final (= Inicial - Depósito, calculado automáticamente), Caras, Precio Bs, Precio Ds, FEFO (fecha), SKU Competencia

**Tareas:**
- [ ] Cargar categorías del cliente desde `GET /api/merc/visitas/{id}/productos`
- [ ] Agrupar productos por `categoria_id` con secciones expandibles
- [ ] Búsqueda inline que filtra todas las categorías
- [ ] Cálculo automático: `Inv.Final = Inv.Inicial - Inv.Depósito` (calculado, no editado manualmente)
- [ ] Campo FEFO como datepicker
- [ ] Campo SKU Competencia opcional
- [ ] Guardar balance: `POST /api/merc/visitas/{id}/balances`
- [ ] Indicador de "Balance guardado" por producto

**Archivos:**
- `frontend/src/app/features/mercaderista/components/merc-visit-panel/components/balance-form/balance-form.component.ts` → **reescritura mayor**

---

## 🟠 FASE 3: FRONTEND — Dashboard y Rutas

> **Prioridad:** ALTA  
> **Duración:** 3-4 días  
> **Dependencias:** Fase 1

### 3.1 Dashboard del Mercaderista

**Archivo APK:** `dashboard_screen.dart`

**Tareas:**
- [ ] Header con: nombre del mercaderista, fecha, día de la semana
- [ ] Indicador online/offline (WebSocket status)
- [ ] Botón "Sincronizar" (llama a `GET /api/merc/programacion`)
- [ ] Cards de acceso rápido (2 columnas en desktop, 1 en tablet):
  - "Realizar Ruta Fija" → abre `MercRutaComponent` con tab 'fija'
  - "Realizar Ruta Variable" → abre `MercRutaComponent` con tab 'variable'
  - "PDV Activos" → abre `PdvActivosComponent` (nuevo)
  - "Historial de Visitas" → abre `MercVisitasComponent`
  - "Chat / Notificaciones" → abre `MercChatComponent`
  - "Carga de Fotos" → abre `MercRutaComponent` (simplificado, igual que la APK)
- [ ] Badge de notificaciones pendientes (rechazos sin leer) en el ícono de Chat

**Archivos:**
- `frontend/src/app/features/mercaderista/mercaderista.component.html` → nuevo template
- `frontend/src/app/features/mercaderista/mercaderista.component.ts` → reescritura

---

### 3.2 Pantalla de Rutas (Completar)

**Archivo APK:** `mis_rutas_screen.dart`

**Tareas:**
- [ ] Agrupación de PDVs por `ruta_nombre` con header de ruta
- [ ] Visualización de prioridad con colores: Alta=Rojo, Media=Naranja, Baja=Gris
- [ ] Estado de activación: 🟢 Activado / ⚪ No Activado
- [ ] Indicador de "Ruta Finalizada" cuando todos los PDVs están visitados
- [ ] Modal de Puntos de Interés (si la ruta tiene puntos adicionales)
- [ ] Día de la semana calculado con `dia_semana.dart`
- [ ] Pull-to-refresh o botón de refrescar programación
- [ ] WebSocket: refrescar al recibir `programacion_updated`

**Nuevo componente:**
- `frontend/src/app/features/mercaderista/components/merc-ruta/puntos-interes-modal.component.ts`

**Archivos:**
- `frontend/src/app/features/mercaderista/components/merc-ruta/merc-ruta.component.ts` → reescritura

---

## 🟠 FASE 4: FRONTEND — Chat Completo

> **Prioridad:** ALTA  
> **Duración:** 4-5 días  
> **Dependencias:** Fase 1 (endpoints de grupo y notificaciones)

### 4.1 Servicio: MercChatService (NUEVO)

**Archivo APK:** `chat_provider.dart` (completo, ~500 líneas)

Este es el servicio central que reemplaza al `ChatProvider` de Flutter. Maneja:
- Bandeja de conversaciones (inbox)
- Caché de mensajes por sala
- Rechazos y notificaciones
- Visitas activas de grupo
- Miembros de grupo
- WebSocket subscriptions (chat_message, foto_status, visita_revisada, grupo_lectura, grupo_visita_lectura)
- Polling cada 30s como fallback si WebSocket falla

**Archivo a crear:**
- `frontend/src/app/features/mercaderista/services/merc-chat.service.ts`

---

### 4.2 Chat Inbox (3 Tabs)

**Archivo APK:** `chat_inbox_screen.dart` (3 tabs: Conversaciones, Rechazos, Notificaciones)

**Tareas:**

**Tab 1 - Conversaciones:**
- [ ] Lista de `ConversacionBandeja` desde `GET /api/merc/chat/inbox`
- [ ] Cada item muestra: título (PDV/Cliente), subtítulo (último mensaje), timestamp, badge no-leídos
- [ ] Tipos: `visita`, `cliente`, `grupo_operativo`, `grupo_cliente`
- [ ] Click en conversación 1-a-1 → abre ChatRoomScreen (dentro de visit-panel o standalone)
- [ ] Click en grupo → abre GrupoDetalleScreen
- [ ] Búsqueda/filtro por PDV o Cliente

**Tab 2 - Rechazos:**
- [ ] Lista de fotos rechazadas desde `GET /api/merc/notificaciones`
- [ ] Cada item: thumbnail, tipo de foto, motivo de rechazo, fecha, nombre del punto
- [ ] Badge "No leído" + marcar como leído al abrir
- [ ] Click → navega a VisitaDetalle para ver la foto y re-subir

**Tab 3 - Notificaciones:**
- [ ] Lista combinada de aprobaciones + visitas revisadas
- [ ] Cada item: icono (✅/📋), texto, fecha, punto
- [ ] Badge "No leído" + marcar como leído

**Archivos:**
- `frontend/src/app/features/mercaderista/components/merc-chat/merc-chat.component.ts` → **reescritura total**
- `frontend/src/app/features/mercaderista/components/merc-chat/merc-chat.component.html` → nuevo template

---

### 4.3 Chat Room (1-a-1)

**Archivo APK:** `chat_room_screen.dart`

**Tareas:**
- [ ] Burbujas de chat: enviado (derecha, azul) vs recibido (izquierda, gris)
- [ ] Timestamps formateados (misma lógica que la APK: "10:30 AM", "Ayer", "12 Ago")
- [ ] Recibo de lectura: "✓✓ Leído por Juan a las 3:15 PM"
- [ ] Input con botón enviar + Enter
- [ ] Auto-scroll al último mensaje
- [ ] WebSocket: recibir `chat_message` en tiempo real
- [ ] Polling cada 30s como fallback

**Archivos:**
- `frontend/src/app/features/mercaderista/components/merc-chat/chat-room/chat-room.component.ts` → **NUEVO**

---

### 4.4 Grupo Chat (Chat General + Hilos de Visita)

**Archivos APK:** `grupo_detalle_screen.dart`, `grupo_visita_chat_screen.dart`

**Tareas:**

**Pantalla de Grupo (GrupoDetalleComponent):**
- [ ] Header con nombre del grupo y botón de miembros
- [ ] Sección superior: Chat general del grupo
  - Mensajes con burbujas + autor + timestamp
  - Recibos de lectura múltiples (lista de quién leyó)
  - Input para enviar
- [ ] Sección inferior: Lista de "Visitas Activas"
  - Cada item: PDV, Cliente, última actividad
  - Click → abre GrupoVisitaChatComponent
  - Las visitas desaparecen cuando el analista las marca "Revisado"

**Pantalla de Hilo de Visita (GrupoVisitaChatComponent):**
- [ ] Chat independiente para una visita dentro del grupo
- [ ] Misma UI que Chat Room pero contexto de grupo
- [ ] WebSocket: `grupo_visita_lectura`

**Archivos a crear:**
- `frontend/src/app/features/mercaderista/components/merc-chat/grupo-detalle/grupo-detalle.component.ts`
- `frontend/src/app/features/mercaderista/components/merc-chat/grupo-visita-chat/grupo-visita-chat.component.ts`

---

### 4.5 Diálogo de Miembros

**Archivo APK:** `miembros_dialog.dart`

**Tareas:**
- [ ] Modal/panel con lista de miembros del grupo
- [ ] Avatar/icono por tipo: analista, mercaderista, cliente
- [ ] Estado online/offline (si está disponible)

**Archivo a crear:**
- `frontend/src/app/features/mercaderista/components/merc-chat/miembros-dialog/miembros-dialog.component.ts`

---

## 🔵 FASE 5: FRONTEND — Pantallas Secundarias

> **Prioridad:** MEDIA  
> **Duración:** 3-4 días  
> **Dependencias:** Fase 1 y 2

### 5.1 Visita Detalle (Review de Visita)

**Archivo APK:** `visita_detalle_screen.dart`

**Tareas:**
- [ ] Vista de solo lectura de una visita ya sincronizada
- [ ] Cabecera: PDV, Cliente, Fecha, Hora, Mercaderista, Estado
- [ ] Grid de fotos con badges:
  - ✅ Verde = Aprobada
  - ❌ Rojo = Rechazada (con motivo expandible)
  - ⏳ Gris = Pendiente de revisión
- [ ] Tabla de balances guardados (solo lectura)
- [ ] WebSocket: suscripción a `foto_status` para refrescar si una foto cambia de estado mientras se ve
- [ ] Navegación: desde Historial, desde Rechazos, desde Notificaciones

**Archivo a crear:**
- `frontend/src/app/features/mercaderista/components/merc-visita-detalle/merc-visita-detalle.component.ts`

---

### 5.2 PDV Activos

**Archivo APK:** `pdv_activos_screen.dart`

**Tareas:**
- [ ] Lista de PDVs con trabajo pendiente hoy
- [ ] Por cada PDV: nombre, ruta, clientes pendientes, clientes listos
- [ ] Indicador "Falta Desactivación" si todos los clientes están listos pero no se desactivó
- [ ] Botón "Ir a Visita" → navega al cliente pendiente
- [ ] Botón "Desactivar PDV" → acción directa de desactivación

**Archivo a crear:**
- `frontend/src/app/features/mercaderista/components/merc-pdv-activos/merc-pdv-activos.component.ts`

---

### 5.3 Historial de Visitas (Completar)

**Archivo APK:** `mis_visitas_screen.dart`

**Tareas:**
- [ ] Filtros: rango de fechas (datepicker), cliente, PDV
- [ ] Combinación: visitas del servidor (`GET /api/merc/visitas`) + visitas locales sin enviar (OfflineQueueService)
- [ ] Contadores: fotos pendientes por subir, balances pendientes
- [ ] Estados visuales con badges:
  - ⏳ Pendiente (tiene datos sin enviar)
  - ✅ Completado (todo enviado)
  - 🔍 Revisado (analista ya revisó)
- [ ] Badge de fotos rechazadas en cada visita
- [ ] Navegación a VisitaDetalle
- [ ] WebSocket: refrescar al recibir `visita_revisada`

**Archivos:**
- `frontend/src/app/features/mercaderista/components/merc-visitas/merc-visitas.component.ts` → reescritura

---

## 🟣 FASE 6: FRONTEND — Status, Perfil y Pulido

> **Prioridad:** BAJA  
> **Duración:** 2-3 días  
> **Dependencias:** Fases 1-5

### 6.1 Upload Status (Sync Status)

**Archivo APK:** `sync_status_screen.dart`

La APK muestra la cola de sync offline → server. En la web, el `OfflineQueueService` ya existe con IndexedDB.

**Tareas:**
- [ ] Lista de fotos pendientes de subir (cola del OfflineQueueService)
- [ ] Estado de cada item: pendiente, subiendo, completado, error
- [ ] Barra de progreso global
- [ ] Reintentar items fallidos
- [ ] Sincronización manual (forzar flush de la cola)

**Archivo a crear:**
- `frontend/src/app/features/mercaderista/components/merc-upload-status/merc-upload-status.component.ts`

---

### 6.2 Perfil (Completar)

**Archivo APK:** N/A (el perfil es parte del drawer/appbar)  
**Estado actual:** `merc-perfil.component.ts` existe con datos básicos.

**Tareas:**
- [ ] Verificar que muestre: nombre, cédula, email, teléfono
- [ ] Rutas asignadas con tipo y nombre
- [ ] Estadísticas básicas: visitas hoy, fotos hoy, PDVs pendientes

---

### 6.3 Pulido General

- [ ] **Tema oscuro/claro:** Consistente con la APK (usa `AppColors.surface`, `AppColors.accent`, etc.)
- [ ] **Estados de carga:** Skeleton screens para listas, spinners para acciones puntuales
- [ ] **Manejo de errores:** SnackBar/Toast con mensajes amigables
- [ ] **Confirmaciones:** Diálogos antes de eliminar foto, finalizar visita, desactivar PDV
- [ ] **Atajos de teclado:** Enter para enviar chat, Escape para cerrar modales
- [ ] **Responsive:** Funcional en tablet (768px+) y desktop (1280px+)
- [ ] **PWA:** Service worker para cachear assets (sin funcionalidad offline de negocio)
- [ ] **Badge de notificaciones:** En el ícono de Chat del shell principal

---

## ⚫ FASE 7: WebSocket — Verificación y Completitud

> **Prioridad:** ALTA (transversal a todas las fases)  
> **Duración:** 1-2 días

### 7.1 MercSocketService (Completar)

**Estado actual:** Solo maneja `chat_message`.  
**Archivo APK:** `socket_service.dart`

**Eventos a agregar al servicio Angular:**

| Evento | Stream | Acción |
|---|---|---|
| `ai_alert` | `aiAlert$` | SnackBar + badge notificaciones |
| `foto_status` | `fotoStatus$` | Refrescar photo-grid / detalle visita |
| `visita_revisada` | `visitaRevisada$` | Refrescar historial |
| `programacion_updated` | `programacionUpdated$` | Refrescar rutas |
| `productos_updated` | `productosUpdated$` | Refrescar catálogo de balance |
| `grupo_lectura` | `grupoLectura$` | Actualizar recibos de lectura en grupo |
| `grupo_visita_lectura` | `grupoVisitaLectura$` | Actualizar recibos en hilo de visita |

**Archivo:**
- `frontend/src/app/features/mercaderista/services/merc-socket.service.ts` → reescritura

---

## 📊 Resumen de Archivos a Crear/Modificar

### Backend (modificar)

| Archivo | Acción | Fase |
|---|---|---|
| `backend/app/mercaderista/endpoints/rutas.py` | Agregar `GET /programacion` | F1 |
| `backend/app/mercaderista/services/ruta_service.py` | Agregar `get_programacion_completa()` | F1 |
| `backend/app/mercaderista/endpoints/chat.py` | Agregar notificaciones + endpoints de grupo | F1 |
| `backend/app/mercaderista/services/chat_service.py` | Agregar `get_notificaciones()` + métodos grupo | F1 |
| `backend/app/mercaderista/endpoints/visitas.py` | Agregar `GET /visitas/{id}/detalle` + emitir `foto_status` | F1 |
| `backend/app/mercaderista/services/visita_service.py` | Agregar `get_detalle_visita()` | F1 |
| `backend/app/services/realtime.py` | Agregar helpers: `notify_ai_alert()`, `notify_foto_status()`, etc. | F1 |

### Frontend (crear)

| Archivo | Fase |
|---|---|
| `.../services/merc-chat.service.ts` | F4 |
| `.../components/merc-chat/chat-room/chat-room.component.ts` | F4 |
| `.../components/merc-chat/grupo-detalle/grupo-detalle.component.ts` | F4 |
| `.../components/merc-chat/grupo-visita-chat/grupo-visita-chat.component.ts` | F4 |
| `.../components/merc-chat/miembros-dialog/miembros-dialog.component.ts` | F4 |
| `.../components/merc-visita-detalle/merc-visita-detalle.component.ts` | F5 |
| `.../components/merc-pdv-activos/merc-pdv-activos.component.ts` | F5 |
| `.../components/merc-upload-status/merc-upload-status.component.ts` | F6 |
| `.../components/merc-ruta/puntos-interes-modal.component.ts` | F3 |

### Frontend (reescribir/modificar)

| Archivo | Acción | Fase |
|---|---|---|
| `.../mercaderista.component.ts` + `.html` | Dashboard con cards | F3 |
| `.../merc-ruta/merc-ruta.component.ts` | Agrupar por ruta, prioridades, WS | F3 |
| `.../merc-visit-panel/merc-visit-panel.component.ts` + `.html` | Fotos 9 tipos, activación, chat | F2 |
| `.../merc-visit-panel/.../photo-grid/photo-grid.component.ts` | 9 tipos reales | F2 |
| `.../merc-visit-panel/.../balance-form/balance-form.component.ts` | Categorías cliente, búsqueda | F2B |
| `.../merc-visitas/merc-visitas.component.ts` | Filtros, combinado local+server | F5 |
| `.../merc-chat/merc-chat.component.ts` + `.html` | 3 tabs inbox | F4 |
| `.../services/merc-socket.service.ts` | 8 eventos WS | F7 |

---

## 🎯 Orden de Ejecución

```
FASE 1 (Backend) — 2-3 días
  ├── 1.1 Programación del Día          ← EMPEZAR AQUÍ
  ├── 1.2 Notificaciones (Rechazos + Aprobaciones)
  ├── 1.3 Grupos de Chat (9 endpoints)
  ├── 1.4 Detalle de Visita
  └── 1.5 WebSocket (8 eventos)

FASE 2 (Frontend — Visita) — 5-6 días
  ├── 2.1 PhotoGrid (9 tipos)           ← LO MÁS GRANDE Y CRÍTICO
  ├── 2.2 Activación/Desactivación PDV
  ├── 2.3 Chat de Visita integrado
  ├── 2.4 Finalización de Visita
  └── 2B Balance Form (categorías)

FASE 3 (Frontend — Dashboard + Rutas) — 3-4 días
  ├── 3.1 Dashboard con cards
  └── 3.2 Rutas (completar)

FASE 4 (Frontend — Chat Completo) — 4-5 días
  ├── 4.1 MercChatService
  ├── 4.2 Chat Inbox (3 tabs)
  ├── 4.3 Chat Room (1-a-1)
  ├── 4.4 Grupo Chat + Hilos
  └── 4.5 Miembros Dialog

FASE 5 (Frontend — Secundario) — 3-4 días
  ├── 5.1 Visita Detalle (Review)
  ├── 5.2 PDV Activos
  └── 5.3 Historial de Visitas

FASE 6 (Frontend — Status + Pulido) — 2-3 días
  ├── 6.1 Upload Status
  ├── 6.2 Perfil
  └── 6.3 Pulido General

FASE 7 (WebSocket) — 1-2 días
  └── 7.1 MercSocketService completo
```

**Tiempo total estimado:** 20-27 días

---

## 🚫 Lo que NO se migra

| Componente APK | Razón |
|---|---|
| `DatabaseService` (SQLite + SQLCipher) | La web usa API calls directas |
| `SyncService` (cola offline→online) | Reemplazado por `OfflineQueueService` simplificado |
| `ConnectivityService` | `navigator.onLine` nativo del browser |
| `SecureStorageService` | `localStorage` + JWT en cookies |
| `SecurityService` (anti-root, kill-switch) | No aplica a web |
| `LocationService` (GPS nativo + fake detection) | `navigator.geolocation` (sin watermarking) |
| `PhotoService` (watermarking, compresión C++) | El backend procesa las imágenes |
| `ECCService` (encripción de datos locales) | HTTPS ya encripta el tráfico |
| `Workmanager` (background sync) | No aplica a web |
| `CustomCameraScreen` | `<input type="file" accept="image/*">` |
| `LoggerService` | `console.log/warn/error` nativo |

---

> **Nota para sesiones futuras:** Si necesitas recordar el contexto, lee primero  
> `utilidades/APK-EPRAM/epran_mercaderista/FLUJO_OPERATIVO.md` para entender el flujo  
> completo del mercaderista, y luego vuelve a este plan.
