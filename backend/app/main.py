import logging
import os
import time
import collections
import threading

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
import app.db.all_models  # noqa: F401 — registers all SQLAlchemy models
from app.routes import auth, users, merchandisers, visits, rutas, points, supervisors, auditors, reporteria, chat, admin_sessions, atencion_cliente, mercaderista_rutas, push, notifications, clients, audit, catalogos, productos_catalogos, auditor_campo, cargas_powerbi


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.services.scheduler_service import start_scheduler, stop_scheduler
    from app.services.catalogos_init import ensure_catalog_tables
    from app.services.plan_accion_service import ensure_plan_accion_tables
    import asyncio
    from app.services.realtime import set_loop
    try:
        ensure_catalog_tables()
    except Exception as e:
        logger.exception(f"Fallo inicializando catálogos: {e}")

    # Plan de Acción: asegura la tabla PLAN_ACCION_PENDIENTES (idempotente) y,
    # si quedó vacía en un ambiente nuevo (epran-qa), dispara un recálculo en
    # background. Sin esto, GET /api/plan-accion/pendientes devuelve 500
    # 'Invalid object name' la primera vez que se abre el módulo.
    try:
        ensure_plan_accion_tables()
    except Exception as e:
        logger.exception(f"Fallo inicializando Plan de Acción: {e}")
        
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

    # Casi todos los endpoints son "def" sync (348 de 375) -- incluida
    # get_current_user, que corre en CADA request autenticado -- así que
    # todos pasan por el threadpool de AnyIO/Starlette. El límite por
    # defecto (~40 threads) se satura en hora pico con --workers 1, y ahí
    # se explica que hasta el login (que depende de la misma cola) se
    # ponga lento o no responda mientras endpoints pesados (resumen-dia,
    # export a Excel, compresión de fotos) ocupan esos threads. Subir el
    # límite no soluciona la contención de CPU/GIL de fondo, pero evita que
    # requests livianos (como login) queden en cola detrás de los pesados
    # simplemente por falta de threads disponibles.
    import anyio.to_thread
    anyio.to_thread.current_default_thread_limiter().total_tokens = 200

    # Fase A de la migración a Redis pub/sub: con --workers 1 / replicas 1
    # (todavía) esto no cambia el comportamiento observable -- cada proceso
    # se recibe su propio eco de Redis y lo descarta por PROCESS_ID. Valida
    # que el cableado no rompa nada antes de escalar workers/réplicas.
    from app.services.redis_pubsub import start_listener, stop_listener
    from app.websockets.manager import manager
    start_listener(manager)

    start_scheduler()
    yield
    stop_scheduler()
    await stop_listener()


from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.core.limiter import limiter
# Sin este import, settings.FRONTEND_URL (usado más abajo para CORS) tira
# NameError al arrancar -- crasheaba los 3 pods en CrashLoopBackOff en
# producción (confirmado 2026-08-18, "settings" nunca se había importado
# en este archivo).
from app.core.config import settings

app = FastAPI(
    title="EPRAN API",
    description="Sistema de gestión de visitas y merchandising",
    version="2.0.0",
    lifespan=lifespan,
)

# ─────────────────────────────────────────────────────────────────────────────
# Middleware de Timing — loguea cada request con su latencia en ms.
# Requests > 500ms → WARNING para fácil identificación en logs.
# Las stats se acumulan en memoria para el endpoint /api/debug/perf.
# ─────────────────────────────────────────────────────────────────────────────
_perf_lock = threading.Lock()
_perf_data: dict[str, collections.deque] = {}  # ruta → deque de latencias (ms)
_PERF_MAX_SAMPLES = 200  # últimas N mediciones por ruta


@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    t0 = time.monotonic()
    response = await call_next(request)
    elapsed_ms = (time.monotonic() - t0) * 1000

    # Normalizar la ruta (quitar path params numéricos para agrupar correctamente)
    path = request.url.path
    method = request.method
    key = f"{method} {path}"

    with _perf_lock:
        if key not in _perf_data:
            _perf_data[key] = collections.deque(maxlen=_PERF_MAX_SAMPLES)
        _perf_data[key].append(elapsed_ms)

    if elapsed_ms > 2000:
        logger.warning(f"SLOW [{method}] {path} → {elapsed_ms:.0f}ms")
    elif elapsed_ms > 500:
        logger.info(f"SLOW [{method}] {path} → {elapsed_ms:.0f}ms")

    response.headers["X-Response-Time"] = f"{elapsed_ms:.1f}ms"
    return response

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
app.include_router(cargas_powerbi.router)
from app.routes import permisos
app.include_router(permisos.router)
from app.routes import analysts
app.include_router(analysts.router)
from app.routes import centro_mando
app.include_router(centro_mando.router)
from app.routes import centro_mando_auditoria
app.include_router(centro_mando_auditoria.router)
from app.routes import sku_competencia
app.include_router(sku_competencia.router)
from app.routes import plan_accion
app.include_router(plan_accion.router)
from app.routes import realtime as realtime_routes
app.include_router(realtime_routes.router)
from app.routes import supervisor_rutas
app.include_router(supervisor_rutas.router)
from app.routes import client_photos
app.include_router(client_photos.router)
from app.routes import client_data
app.include_router(client_data.router)
# Portal Mercaderista v2 — Arquitectura modular con ORM (reemplaza mercaderista_portal legacy)
from app.mercaderista.router import router as mercaderista_router
app.include_router(mercaderista_router)
from app.routes import cliente_segmentacion
app.include_router(cliente_segmentacion.router)
from app.routes import encuestador
app.include_router(encuestador.router)
from app.routes import cliente_encuestador
app.include_router(cliente_encuestador.router)
from app.routes import vendedor
app.include_router(vendedor.router)
from app.routes import ventas_pedidos
app.include_router(ventas_pedidos.router)
from app.routes import frecuencias_pdvs_cliente
app.include_router(frecuencias_pdvs_cliente.router)
from app.routes import horas_promedio_ejecucion
app.include_router(horas_promedio_ejecucion.router)
from app.routes import chat_grupos
app.include_router(chat_grupos.router)
from app.routes import admin_chat_grupos
app.include_router(admin_chat_grupos.router)
from app.routes import media as media_routes
app.include_router(media_routes.router)
from app.routes import supervisor_encuestadores
app.include_router(supervisor_encuestadores.router)
from app.routes import auditoria_usuarios
app.include_router(auditoria_usuarios.router)
from app.routes import quiebre
app.include_router(quiebre.router)
from app.routes import cobertura_encuestas
app.include_router(cobertura_encuestas.router)



@app.get("/health")
async def health_check():
    # async, no toca la DB: las rutas sync comparten un threadpool con las
    # queries pesadas (resumen-dia, etc.) -- si el health check también fuera
    # sync, un pico de tráfico podía dejarlo en cola detrás de esas queries,
    # el liveness probe expiraba (timeoutSeconds por default = 1s) y
    # Kubernetes reiniciaba el pod en plena carga, empeorando el problema.
    return {"status": "ok", "version": "2.0.0"}

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    # Intenta servir el favicon si existe, si no retorna 204
    favicon_path = "app/static/favicon.ico"
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path)
    return JSONResponse(status_code=204, content=None)


@app.get("/api/debug/perf", include_in_schema=False)
async def perf_stats(request: Request):
    """Estadísticas de latencia por endpoint (últimas 200 mediciones por ruta).
    Protegido por header X-Debug-Key con el SECRET_KEY del servidor.
    Solo accesible desde la red interna o con la clave correcta."""
    debug_key = request.headers.get("X-Debug-Key", "")
    if debug_key != settings.SECRET_KEY:
        return JSONResponse(status_code=403, content={"detail": "Forbidden"})

    import statistics
    result = []
    with _perf_lock:
        snapshot = {k: list(v) for k, v in _perf_data.items()}

    for route, latencies in snapshot.items():
        if not latencies:
            continue
        sorted_l = sorted(latencies)
        n = len(sorted_l)
        result.append({
            "route": route,
            "count": n,
            "avg_ms": round(statistics.mean(sorted_l), 1),
            "p50_ms": round(sorted_l[int(n * 0.50)], 1),
            "p95_ms": round(sorted_l[int(n * 0.95)], 1),
            "p99_ms": round(sorted_l[min(int(n * 0.99), n - 1)], 1),
            "max_ms": round(sorted_l[-1], 1),
        })

    result.sort(key=lambda x: x["p95_ms"], reverse=True)
    return {"routes": result, "total_routes_tracked": len(result)}


@app.get("/api/debug/auth-cache", include_in_schema=False)
async def auth_cache_stats(request: Request):
    """Estadísticas del cache de autenticación en memoria."""
    debug_key = request.headers.get("X-Debug-Key", "")
    if debug_key != settings.SECRET_KEY:
        return JSONResponse(status_code=403, content={"detail": "Forbidden"})

    from app.core.dependencies import get_cache_stats
    return get_cache_stats()

