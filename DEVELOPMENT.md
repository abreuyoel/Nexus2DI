# Guía de Setup de Desarrollo Local — Nexus2DI

Este documento contiene las instrucciones detalladas para levantar el entorno de desarrollo local para el proyecto **Nexus2DI**.

---

## 📋 Contexto y Arquitectura Local

El entorno local consta de un frontend en **Angular**, un backend en **FastAPI** estructurado de forma modular y servicios auxiliares levantados localmente y a través de **Docker**.

```
Frontend Angular (localhost:4200)
    │  npm start (ng serve + proxy)
    ▼
Backend FastAPI (localhost:8000)   ← Corre localmente (fuera de Docker)
    │  ├── Arquitectura Modular (app/modules/<domain>/)
    │  ├── Query Builder ORM (SQLAlchemy) & DTOs (Pydantic v2)
    │  └── WebSocketGuard (Auth, CORS & Token Bucket Rate Limiter)
    │
    ├── SQL Server (localhost:1433) ← Instalación local en Windows con Windows Auth
    ├── Redis (localhost:6379)      ← Contenedor Docker
    └── Azurite Blob (localhost:10000) ← Contenedor Docker (Emulador de Azure Storage)
```

---

## 🛠️ Requisitos Previos

1. **Docker / Docker Desktop** (para Redis y Azurite).
2. **Python 3.12** (se requiere específicamente Python 3.12; versiones como Python 3.14 carecen de wheels precompiladas para dependencias clave como pandas, scikit-learn o pydantic-core).
3. **Node.js** (versión compatible con Angular 17) y **npm**.
4. **SQL Server local** con *Windows Authentication* habilitado y el puerto `1433` expuesto.

---

## 🚀 Paso a Paso del Setup

### 1. Levantar Servicios en Docker (Redis + Azurite)
Desde la raíz del repositorio, ejecuta:
```powershell
docker compose -f docker-compose.dev.yml up -d
```
Esto levantará:
- **Redis** (`localhost:6379`)
- **Azurite Blob Storage** (`localhost:10000`)

---

### 2. Crear la Base de Datos Local
Usa `sqlcmd` para crear la base de datos `epran-dev` si aún no existe. 

> [!TIP]
> Si `sqlcmd` no está en tu PATH, generalmente se ubica en:
> `C:\Program Files\Microsoft SQL Server\Client SDK\ODBC\180\Tools\Binn\SQLCMD.EXE`

**Comando de PowerShell/cmd:**
```cmd
"C:\Program Files\Microsoft SQL Server\Client SDK\ODBC\180\Tools\Binn\SQLCMD.EXE" -S localhost -E -C -Q "IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = N'epran-dev') BEGIN CREATE DATABASE [epran-dev] COLLATE Latin1_General_CI_AS; END"
```
* `-E`: Utiliza Windows Authentication (sin usuario/contraseña).
* `-C`: Confía en el certificado del servidor (requerido para conexiones ODBC Driver 18).

---

### 3. Configuración del Backend (Python 3.12)

#### Crear Entorno Virtual e Instalar Dependencias
Desde la raíz del proyecto, limpia cualquier entorno virtual antiguo y crea uno con Python 3.12:
```powershell
# Eliminar entorno anterior si existe
Remove-Item -Recurse -Force backend\.venv

# Crear entorno con Python 3.12
py -3.12 -m venv backend\.venv

# Activar el entorno
backend\.venv\Scripts\activate

# Instalar dependencias con preferencia por paquetes binarios
pip install -r backend\requirements.txt --prefer-binary
```

#### Configurar Variables de Entorno (`.env`)
Crea el archivo [backend/.env](file:///d:/proyects/Nexus2DI/backend/.env) en formato **ASCII puro** (sin tildes ni caracteres especiales en los comentarios para evitar fallos de decodificación en Windows).

Contenido base:
```ini
SECRET_KEY=TU_SECRET_KEY_GENERADA
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
DB_DRIVER=ODBC Driver 18 for SQL Server
DB_SERVER=localhost
DB_NAME=epran-dev
DB_TRUSTED_CONNECTION=true
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
REDIS_HOST=localhost
REDIS_PORT=6379
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OcqFlqUwJPLlmEtlCDXJ1OcqFlqUwJPLlmEtlCDXJ1OcqFlqUwJPLlmEtlCDXJ1OcqFlqUwJPLlmEtlCDXJ1OcqFlqUwJPLlmEtlCDXJ1==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;QueueEndpoint=http://127.0.0.1:10001/devstoreaccount1;TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;
AZURE_CONTAINER_NAME=epran
AZURE_ACCOUNT_NAME=devstoreaccount1
VAPID_PRIVATE_KEY=
VAPID_PUBLIC_KEY=
VAPID_EMAIL=mailto:admin@epran.com
SCHEDULER_INTERVAL_MINUTES=60
SCHEDULER_TIMEZONE=America/Caracas
ENVIRONMENT=development
FRONTEND_URL=http://localhost:4200
CORS_ORIGINS=http://localhost:4200,http://127.0.0.1:4200,http://localhost,http://127.0.0.1
```
> [!NOTE]
> Puedes generar una nueva `SECRET_KEY` desde la terminal con:
> `python -c "import secrets; print(secrets.token_hex(64))"`

---

### 4. Inicializar Base de Datos (Alembic y Seed)

#### Correr Migraciones
Genera y aplica las tablas iniciales a la base de datos local:
```powershell
# Crear carpeta de versiones si no existe
New-Item -ItemType Directory -Path "backend\alembic\versions"

# Generar esquema inicial de Alembic
alembic revision --autogenerate -m "initial_schema"

# Aplicar las migraciones
alembic upgrade head
```

#### Insertar Roles y Admin por Defecto (Seed)
Crea un archivo temporal `backend/seed_admin.py` con el siguiente código:
```python
import sys
sys.path.insert(0, '.')

from app.db.session import SessionLocal
from app.core.security import get_password_hash
from sqlalchemy import text

db = SessionLocal()

# Roles requeridos en la base de datos
roles = [
    (1,'client'),(2,'analyst'),(3,'coordinador_exclusivo'),
    (4,'coordinador_tradex'),(5,'mercaderista'),(6,'supervisor'),
    (7,'auditor'),(8,'admin'),(9,'vendedor'),(10,'atc'),
    (11,'coordinador_general'),(12,'encuestador'),
    (13,'cliente_encuestador'),(14,'auditor_campo'),
]

for rid, nombre in roles:
    exists = db.execute(text('SELECT 1 FROM ROLES WHERE id_rol=:id'), {'id': rid}).fetchone()
    if not exists:
        db.execute(text('INSERT INTO ROLES (id_rol, nombre) VALUES (:id, :nombre)'), {'id': rid, 'nombre': nombre})
print('Roles insertados.')

# Crear usuario admin inicial
existe = db.execute(text("SELECT 1 FROM USUARIOS WHERE username='admin'")).fetchone()
if not existe:
    hashed = get_password_hash('Admin1234!')
    db.execute(text('''
        INSERT INTO USUARIOS (username, password_hash, email, id_rol, activo)
        VALUES (:u, :p, :e, :r, 1)
    '''), {'u': 'admin', 'p': hashed, 'e': 'admin@epran.com', 'r': 8})
    print('Usuario admin creado exitosamente. Password: Admin1234!')
else:
    print('El usuario admin ya existe.')

db.commit()
db.close()
```
Ejecútalo desde el directorio `backend` con el entorno virtual activado:
```powershell
python seed_admin.py
```
* **Credenciales por defecto:**
  * Usuario: `admin`
  * Contraseña: `Admin1234!`

---

### 5. Configurar y Levantar el Frontend (Angular)

> [!WARNING]
> Si intentas ejecutar `npm start` y obtienes el error `Could not find the 'angular-devkit/build-angular:dev-server' builder`, significa que no has instalado los paquetes de node locales. Debes correr primero `npm install`.

```powershell
cd frontend

# Instalar los paquetes locales la primera vez
npm install

# Iniciar el servidor local de desarrollo
npm start
```

---

## 🏗️ Arquitectura y Seguridad del Backend

### 1. Estructura Modular por Dominio (`app/modules/`)
El backend organiza sus funcionalidades por módulos independientes dentro de `app/modules/<domain>/`:
- `controller.py`: Manejadores de endpoints HTTP/WebSocket tipados.
- `dto.py`: Modelos Pydantic v2 para validación de entrada y esquemas de respuesta.
- `entities.py`: Modelos ORM de SQLAlchemy para mapeo de tablas.

### 2. Estándar de Consultas de Base de Datos
- Se utiliza exclusivamente **SQLAlchemy ORM Query Builder**.
- Todas las sentencias SQL nativas (`db.execute(text(...))`) en controladores han sido eliminadas.

### 3. Seguridad en WebSockets y CORS
- **WebSocketGuard (`app/websockets/guard.py`)**: Valida la cabecera `Origin` en conexiones WebSocket y autentica mediante tokens JWT (`?token=...`, `Authorization: Bearer` o `Sec-WebSocket-Protocol`).
- **Token Bucket Rate Limiter**: Controla la frecuencia de mensajes por conexión WebSocket (`capacity=20.0`, `refill_rate=5.0 tokens/seg`).
- **Control de CORS**: Se gestiona mediante `FRONTEND_URL` y `CORS_ORIGINS` en el archivo `.env`, aplicándose tanto a endpoints REST como a WebSockets a través de `settings.ALLOWED_ORIGINS`.

---

## 🔌 Direcciones de Acceso

| Componente | URL |
|---|---|
| **Aplicación Frontend** | [http://localhost:4200](http://localhost:4200) |
| **API FastAPI Backend** | [http://localhost:8000](http://localhost:8000) |
| **API Swagger Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) |
| **Redis** | `localhost:6379` |
| **Azurite Blob Store** | `http://localhost:10000/devstoreaccount1` |

---

## 🔍 Solución de Problemas Frecuentes

* **Error `UnicodeDecodeError: 'cp1252' codec can't decode...` al iniciar uvicorn**: El archivo `.env` tiene caracteres UTF-8 invisibles (como tildes o eñes en comentarios). Guarda el archivo `.env` usando codificación **ASCII** estricta.
* **Error de conexión `SAWarning: Unrecognized server version info...`**: Es un warning inocuo de SQLAlchemy al conectarse a SQL Server 2022. No afecta la funcionalidad del sistema.
* **Error `Could not find the 'angular-devkit/build-angular...'`**: Corre `npm install` dentro de la carpeta `frontend` antes de `npm start`.
}


ES NECESARIO INDEXAR ESTAS COLUMNAS EN LA BD PRODUCCION 


-- ============================================================
-- Índices de rendimiento para consultas de Centro de Mando
-- Generado desde: alembic/versions/1c8d4f3e7b2a_add_performance_indexes.py
-- Ejecutar directamente en SQL Server Management Studio (SSMS)
-- ============================================================

-- ── VISITAS_MERCADERISTA ──────────────────────────────────
-- WHERE fecha_visita BETWEEN ... ORDER BY fecha_visita DESC
-- JOIN con CLIENTES, PUNTOS_INTERES1, MERCADERISTAS
CREATE INDEX ix_visitas_fecha ON VISITAS_MERCADERISTA (fecha_visita DESC)
    INCLUDE (id_visita, id_mercaderista, identificador_punto_interes, id_cliente);

CREATE INDEX ix_visitas_id_mercaderista ON VISITAS_MERCADERISTA (id_mercaderista);
CREATE INDEX ix_visitas_id_cliente ON VISITAS_MERCADERISTA (id_cliente);
CREATE INDEX ix_visitas_identificador_punto ON VISITAS_MERCADERISTA (identificador_punto_interes);

-- ── FOTOS_TOTALES ─────────────────────────────────────────
-- Subconsultas con ROW_NUMBER() OVER(PARTITION BY id_visita ORDER BY fecha_registro DESC)
-- WHERE id_tipo_foto IN (5, 6)
CREATE INDEX ix_fotos_visita_tipo_fecha ON FOTOS_TOTALES (id_visita, id_tipo_foto, fecha_registro DESC)
    INCLUDE (id_foto, file_path, Estado);

CREATE INDEX ix_fotos_id_tipo_foto ON FOTOS_TOTALES (id_tipo_foto);

-- ── RUTA_PROGRAMACION ─────────────────────────────────────
-- Subquery ruta_pre: WHERE activa = 1 GROUP BY id_punto_interes
-- Pending query: WHERE activa = 1 AND dia IN (...)
CREATE INDEX ix_ruta_prog_punto_activo ON RUTA_PROGRAMACION (id_punto_interes, activa)
    INCLUDE (id_ruta, prioridad);

CREATE INDEX ix_ruta_prog_dia_activo ON RUTA_PROGRAMACION (dia, activa)
    INCLUDE (id_ruta, id_punto_interes, id_cliente, prioridad);

-- ── CHAT_MENSAJES_CLIENTE ─────────────────────────────────
-- Subquery chat_pre: WHERE id_visita = X GROUP BY id_visita
CREATE INDEX ix_chat_msgs_visita ON CHAT_MENSAJES_CLIENTE (id_visita)
    INCLUDE (visto, tipo_mensaje);

-- ── MERCADERISTAS ─────────────────────────────────────────
-- Pending query: WHERE activo = 1
CREATE INDEX ix_mercaderistas_activo ON MERCADERISTAS (activo)
    INCLUDE (id_mercaderista, nombre);

