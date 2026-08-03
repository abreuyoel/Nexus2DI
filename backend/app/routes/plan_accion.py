"""Plan de Acción -- Fase 2: lectura del último snapshot calculado por el
job en background (app/services/plan_accion_service.py) y disparo manual
del recálculo. Todavía no genera rutas BCK ni asigna backups -- eso es
Fase 3/4."""
import logging
from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db, SessionLocal
from app.core.dependencies import require_analyst_or_admin
from app.models.user import Usuario
from app.services.plan_accion_service import recalcular_plan_accion, calcular_clusters, _execute_with_timeout

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/plan-accion", tags=["Plan de Acción"])


@router.get("/pendientes")
def listar_pendientes(
    id_ruta: Optional[int] = None,
    id_cliente: Optional[int] = None,
    tipo_pendiente: Optional[str] = Query(None, pattern="^(nunca_visitado|fotos_rechazadas)$"),
    prioridad_ruta: Optional[str] = None,
    score_min: Optional[float] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_analyst_or_admin),
):
    where = "WHERE 1=1"
    params: list = []
    if id_ruta:
        where += " AND id_ruta = ?"
        params.append(id_ruta)
    if id_cliente:
        where += " AND id_cliente = ?"
        params.append(id_cliente)
    if tipo_pendiente:
        where += " AND tipo_pendiente = ?"
        params.append(tipo_pendiente)
    if prioridad_ruta:
        where += " AND prioridad_ruta = ?"
        params.append(prioridad_ruta)
    if score_min is not None:
        where += " AND score >= ?"
        params.append(score_min)

    # Timeout defensivo: esta tabla es chica y no debería tardar, pero si
    # alguna vez queda bloqueada detrás de un recalculo en curso, mejor
    # fallar rápido en vez de colgar la pantalla indefinidamente.
    rows = _execute_with_timeout(db, f"""
        SELECT id_pendiente, id_ruta, ruta_nombre, id_punto_interes, punto_de_interes,
               departamento, ciudad, id_cliente, cliente_nombre, prioridad_ruta,
               frecuencia_semanal, periodo, tipo_pendiente, visitas_requeridas,
               visitas_hechas, visitas_faltantes, dias_disponibles, urgencia, score,
               fecha_calculo
        FROM PLAN_ACCION_PENDIENTES
        {where}
        ORDER BY score DESC
    """, tuple(params), timeout=15)

    cols = ["id_pendiente", "id_ruta", "ruta_nombre", "id_punto_interes", "punto_de_interes",
            "departamento", "ciudad", "id_cliente", "cliente_nombre", "prioridad_ruta",
            "frecuencia_semanal", "periodo", "tipo_pendiente", "visitas_requeridas",
            "visitas_hechas", "visitas_faltantes", "dias_disponibles", "urgencia", "score",
            "fecha_calculo"]
    items = [dict(zip(cols, row)) for row in rows]

    fecha_calculo = items[0]["fecha_calculo"] if items else None
    total_criticos = sum(1 for i in items if (i["score"] or 0) >= 1)

    return {
        "items": items,
        "total": len(items),
        "total_criticos": total_criticos,
        "fecha_calculo": fecha_calculo,
    }


def _recalcular_background():
    db = SessionLocal()
    try:
        n = recalcular_plan_accion(db)
        logger.info(f"Plan de Acción recalculado manualmente: {n} pendiente(s)")
    except Exception as e:
        db.rollback()
        logger.error(f"Error recalculando Plan de Acción (manual): {e}")
    finally:
        db.close()


@router.post("/recalcular")
def recalcular(
    background_tasks: BackgroundTasks,
    current_user: Usuario = Depends(require_analyst_or_admin),
):
    # Corre en background (sesión propia, no la del request) -- la query de
    # arriba puede tardar y con --workers 1 no queremos que el thread del
    # request se quede esperando hasta el timeout de Cloudflare (524),
    # bloqueando de paso al resto de la app.
    background_tasks.add_task(_recalcular_background)
    return {"ok": True, "started": True}


@router.get("/clusters")
def listar_clusters(
    score_min: float = 1.0,
    radio_km: float = 5.0,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_analyst_or_admin),
):
    """Fase 3: agrupa por cercanía geográfica los pendientes con score >=
    score_min (críticos por defecto). Todavía es solo propuesta -- no crea
    rutas BCK ni asigna mercaderista, eso es Fase 4."""
    grupos = calcular_clusters(db, score_min=score_min, radio_km=radio_km)
    return {
        "grupos": grupos,
        "total_grupos": len(grupos),
        "radio_km": radio_km,
        "score_min": score_min,
    }
