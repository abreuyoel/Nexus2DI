# Guía de Setup de Desarrollo Local — Nexus2DI

Este documento contiene las instrucciones detalladas para levantar el entorno de desarrollo local para el proyecto **Nexus2DI**.

---

## 📋 Contexto y Arquitectura Local

El entorno local consta de un frontend en **Angular**, un backend en **FastAPI** y servicios auxiliares levantados localmente y a través de **Docker**.

```
Frontend Angular (localhost:4200)
    │  npm start (ng serve + proxy)
    ▼
Backend FastAPI (localhost:8000)   ← Corre localmente (fuera de Docker)
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
