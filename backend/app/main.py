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
from fastapi.responses import JSONResponse, FileResponse, Response, RedirectResponse
from contextlib import asynccontextmanager
from app.core.config import settings
import app.db.all_models  # noqa: F401 — registers all SQLAlchemy models

# Import modular routers
from app.modules.auth.controller import router as auth_router
from app.modules.users.controller import router as users_router
from app.modules.merchandisers.controller import router as merchandisers_router
from app.modules.visits.controller import router as visits_router
from app.modules.routes.controller import router as rutas_router
from app.modules.routes.points_controller import router as points_router
from app.modules.supervisors.controller import router as supervisors_router
from app.modules.auditors.controller import router as auditors_router
from app.modules.reporting.controller import router as reporteria_router
from app.modules.chat.controller import router as chat_router
from app.modules.customer_service.controller import router as atencion_cliente_router
from app.modules.routes.mercaderista_rutas_controller import router as mercaderista_rutas_router
from app.modules.push.controller import router as push_router
from app.modules.visits.notifications_controller import router as notifications_router
from app.modules.clients.controller import router as clients_router
from app.modules.catalogues.controller import router as catalogos_router
from app.modules.analysts.controller import router as analysts_router
from app.modules.reporting.dashboard_controller import router as centro_mando_router
from app.modules.realtime.controller import router as realtime_router
from app.modules.clients.photos_controller import router as client_photos_router
from app.modules.clients.data_controller import router as client_data_router
from app.modules.merchandisers.portal_controller import router as mercaderista_portal_router
from app.modules.routes.segmentacion_controller import router as cliente_segmentacion_router
from app.modules.surveyors.controller import router as surveyors_router
from app.modules.sellers.controller import router as vendedor_router
from app.modules.frequencies.controller import router as frequencies_router
from app.modules.sessions.controller import router as sessions_router


from fastapi.responses import JSONResponse, FileResponse, Response, RedirectResponse, ORJSONResponse

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.shared.scheduler_service import start_scheduler, stop_scheduler
    from app.services.catalogos_init import ensure_catalog_tables
    import asyncio
    from app.shared.realtime import set_loop
    from app.db.session import engine

    # 1. Pre-calentamiento del pool asíncrono y no bloqueante
    async def _async_warmup():
        try:
            from sqlalchemy import text
            def _warm():
                conns = []
                for _ in range(min(5, settings.DB_POOL_SIZE)):
                    try:
                        conn = engine.connect()
                        conn.execute(text("SELECT 1"))
                        conns.append(conn)
                    except Exception:
                        pass
                for conn in conns:
                    conn.close()
            await asyncio.to_thread(_warm)
        except Exception:
            pass

    # 2. Inicialización de catálogos no bloqueante
    async def _async_init_catalogs():
        try:
            await asyncio.to_thread(ensure_catalog_tables)
        except Exception as e:
            logger.warning(f"Error inicializando catálogos: {e}")

    # Ejecutar tareas pesadas de inicio en background para recarga instantánea
    asyncio.create_task(_async_init_catalogs())
    asyncio.create_task(_async_warmup())

    set_loop(asyncio.get_running_loop())
    start_scheduler()

    yield

    # Apagado ultra-rápido sin bloqueos
    stop_scheduler()
    try:
        engine.dispose()
    except Exception:
        pass


from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.core.limiter import limiter

app = FastAPI(
    title="EPRAN API",
    description="Sistema de gestión de visitas y merchandising",
    version="2.0.0",
    default_response_class=ORJSONResponse,
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

_cors_origins = settings.ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

from fastapi.exceptions import ResponseValidationError

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

# Register modular routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(merchandisers_router)
app.include_router(visits_router)
app.include_router(rutas_router)
app.include_router(points_router)
app.include_router(supervisors_router)
app.include_router(auditors_router)
app.include_router(reporteria_router)
app.include_router(chat_router)
app.include_router(atencion_cliente_router)
app.include_router(mercaderista_rutas_router)
app.include_router(push_router)
app.include_router(notifications_router)
app.include_router(clients_router)
app.include_router(catalogos_router)
app.include_router(analysts_router)
app.include_router(centro_mando_router)
app.include_router(realtime_router)
app.include_router(client_photos_router)
app.include_router(client_data_router)
app.include_router(mercaderista_portal_router)
app.include_router(cliente_segmentacion_router)
app.include_router(surveyors_router)
app.include_router(vendedor_router)
app.include_router(frequencies_router)
app.include_router(sessions_router)

from app.modules.chat.chat_grupos_controller import router as chat_grupos_router
from app.modules.media.controller import router as media_router

app.include_router(chat_grupos_router)
app.include_router(media_router)



@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")



@app.get("/health")
def health_check():
    return {"status": "ok", "version": "2.0.0"}


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    favicon_path = "app/static/favicon.ico"
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path)
    return Response(status_code=204)
