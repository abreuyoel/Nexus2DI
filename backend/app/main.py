import logging
import os

# Configuración de logging (DEBE IR ANTES DE IMPORTAR RUTAS)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("app")

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from contextlib import asynccontextmanager
from app.core.config import settings
import app.db.all_models  # noqa: F401 — registers all SQLAlchemy models
from app.routes import auth, users, merchandisers, visits, rutas, points, supervisors, auditors, reporteria, chat, admin_sessions, atencion_cliente, mercaderista_rutas, push, notifications, clients, audit, catalogos, productos_catalogos, auditor_campo


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.services.scheduler_service import start_scheduler, stop_scheduler
    from app.services.catalogos_init import ensure_catalog_tables
    import asyncio
    from app.services.realtime import set_loop
    try:
        ensure_catalog_tables()
    except Exception as e:
        logger.exception(f"Fallo inicializando catálogos: {e}")
        
    # Pre-calentamiento del pool de conexiones (Punto B5 del Informe Optimización)
    try:
        from app.db.session import engine
        from sqlalchemy import text
        logger.info("Iniciando pre-calentamiento del pool de base de datos...")
        def _warm_pool():
            conns = []
            for _ in range(settings.DB_POOL_SIZE):
                try:
                    conn = engine.connect()
                    conn.execute(text("SELECT 1"))
                    conns.append(conn)
                except Exception:
                    pass
            for conn in conns:
                conn.close()
        await asyncio.to_thread(_warm_pool)
        logger.info(f"[DB] Pool pre-calentado: {settings.DB_POOL_SIZE} conexiones idle")
    except Exception as e:
        logger.warning(f"Error pre-calentando pool: {e}")

    set_loop(asyncio.get_running_loop())  # para difundir eventos en tiempo real
    start_scheduler()
    yield
    stop_scheduler()


from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.core.limiter import limiter

app = FastAPI(
    title="EPRAN API",
    description="Sistema de gestión de visitas y merchandising",
    version="2.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print(f"!!! VALIDATION ERROR: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )

# En producción solo se confía en FRONTEND_URL (el frontend real, servido bajo
# el mismo origen que hace proxy a esta API) — los orígenes de localhost solo
# se agregan fuera de producción, para no ampliar innecesariamente la lista
# de orígenes con allow_credentials=True en el dominio público.
_cors_origins = [settings.FRONTEND_URL]
if settings.ENVIRONMENT != "production":
    _cors_origins += [
        "http://localhost:4200",
        "http://127.0.0.1:4200",
        "http://localhost:4200/",
        "http://127.0.0.1:4200/",
        "http://localhost",
        "http://127.0.0.1",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

from fastapi.exceptions import RequestValidationError, ResponseValidationError

@app.exception_handler(ResponseValidationError)
async def validation_exception_handler(request: Request, exc: ResponseValidationError):
    print(f"RESPONSE VALIDATION ERROR: {exc.errors()}", flush=True)
    return JSONResponse(status_code=500, content={"detail": "Response validation error", "errors": exc.errors()})

@app.exception_handler(Exception)

async def global_exception_handler(request: Request, exc: Exception):
    import sys
    import traceback
    try:
        print(f"CRASH DETECTED in {request.url.path}: {exc}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        logger.error(f"Error no manejado en {request.url.path}: {str(exc)}", exc_info=True)
    except Exception as e:
        print(f"Error in exception handler: {e}", file=sys.stderr)
        
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Error interno del servidor",
            "message": str(exc)
        }
    )

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(merchandisers.router)
app.include_router(visits.router)
app.include_router(rutas.router)
app.include_router(points.router)
app.include_router(supervisors.router)
app.include_router(auditors.router)
app.include_router(reporteria.router)
app.include_router(chat.router)
app.include_router(admin_sessions.router)
app.include_router(atencion_cliente.router)
app.include_router(mercaderista_rutas.router)
app.include_router(push.router)
app.include_router(notifications.router)
app.include_router(clients.router)
app.include_router(audit.router)
app.include_router(catalogos.router)
app.include_router(productos_catalogos.router)
app.include_router(auditor_campo.router)
from app.routes import permisos
app.include_router(permisos.router)
from app.routes import analysts
app.include_router(analysts.router)
from app.routes import centro_mando
app.include_router(centro_mando.router)
from app.routes import realtime as realtime_routes
app.include_router(realtime_routes.router)
from app.routes import supervisor_rutas
app.include_router(supervisor_rutas.router)
from app.routes import client_photos
app.include_router(client_photos.router)
from app.routes import client_data
app.include_router(client_data.router)
from app.routes import mercaderista_portal
app.include_router(mercaderista_portal.router)
from app.routes import cliente_segmentacion
app.include_router(cliente_segmentacion.router)
from app.routes import encuestador
app.include_router(encuestador.router)
from app.routes import cliente_encuestador
app.include_router(cliente_encuestador.router)
from app.routes import vendedor
app.include_router(vendedor.router)
from app.routes import frecuencias_pdvs_cliente
app.include_router(frecuencias_pdvs_cliente.router)
from app.routes import horas_promedio_ejecucion
app.include_router(horas_promedio_ejecucion.router)
from app.routes import chat_grupos
app.include_router(chat_grupos.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "version": "2.0.0"}

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    # Intenta servir el favicon si existe, si no retorna 204
    favicon_path = "app/static/favicon.ico"
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path)
    return JSONResponse(status_code=204, content=None)
