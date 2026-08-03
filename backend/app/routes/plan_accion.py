"""Plan de Acción -- Fase 2: lectura del último snapshot calculado por el
job en background (app/services/plan_accion_service.py). Fase 3: propuesta
de rutas BCK por cercanía (GET /clusters). Fase 4: POST /clusters/confirmar
crea la ruta de verdad y la asigna al mercaderista elegido por el admin."""
import logging
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db, SessionLocal
from app.core.dependencies import require_permission
from app.models.user import Usuario
from app.models.ruta import Ruta, RutaProgramacion
from app.models.mercaderista import MercaderistaRuta
from app.routes.rutas import _get_servicio_prefijo, _next_route_number
from app.services.plan_accion_service import recalcular_plan_accion, calcular_clusters, _execute_with_timeout

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/plan-accion", tags=["Plan de Acción"])

SERVICIO_BCK = "Backup"  # SERVICIOS.nombre -- ver sql/2026-08-02_servicio_bck.sql
DAY_MAP_ES = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"}


@router.get("/pendientes")
def listar_pendientes(
    id_ruta: Optional[int] = None,
    id_cliente: Optional[int] = None,
    tipo_pendiente: Optional[str] = Query(None, pattern="^(nunca_visitado|fotos_rechazadas)$"),
    prioridad_ruta: Optional[str] = None,
    score_min: Optional[float] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission('plan-accion', 'read')),
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
    current_user: Usuario = Depends(require_permission('plan-accion.recalcular', 'read')),
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
    current_user: Usuario = Depends(require_permission('plan-accion', 'read')),
):
    """Fase 3: agrupa por cercanía geográfica los pendientes con score >=
    score_min (críticos por defecto) y arma rutas del tamaño de una jornada
    -- cada elemento de "grupos" ya es una propuesta de ruta BCK ejecutable
    por un backup en un día, no una zona entera. Todavía es solo propuesta
    -- no crea rutas ni asigna mercaderista, eso es Fase 4."""
    grupos = calcular_clusters(db, score_min=score_min, radio_km=radio_km)
    return {
        "grupos": grupos,
        "total_grupos": len(grupos),
        "total_backups_sugeridos": len(grupos),
        "radio_km": radio_km,
        "score_min": score_min,
    }


class ConfirmarRutaItem(BaseModel):
    id_punto_interes: str
    id_cliente: int
    punto_de_interes: Optional[str] = None
    prioridad_ruta: Optional[str] = None


class ConfirmarRutaRequest(BaseModel):
    items: List[ConfirmarRutaItem]
    id_mercaderista: int


@router.post("/clusters/confirmar")
def confirmar_ruta_bck(
    data: ConfirmarRutaRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission('plan-accion.crear_ruta', 'read')),
):
    """Fase 4: toma una propuesta de ruta (los items de una tarjeta de
    /clusters, ya elegidos por el admin) y la vuelve real -- crea la ruta
    en RUTAS_NUEVAS (servicio "Backup"), sus puntos en RUTA_PROGRAMACION
    para el día de hoy, y la asigna al mercaderista elegido. No toca nada
    de Plan de Acción en sí -- el próximo recálculo ya va a ver esta visita
    reflejada normalmente en cuanto el backup suba las fotos."""
    if not data.items:
        raise HTTPException(status_code=400, detail="La propuesta no tiene PDVs")

    prefijo = _get_servicio_prefijo(db, SERVICIO_BCK)
    nombre = f"Ruta {prefijo}{_next_route_number(db, prefijo)}"
    ruta = Ruta(nombre=nombre, servicio=SERVICIO_BCK)
    db.add(ruta)
    db.flush()

    hoy = db.execute(text("SELECT CAST(GETDATE() AS DATE)")).scalar()
    dia = DAY_MAP_ES[hoy.weekday()]

    for item in data.items:
        db.add(RutaProgramacion(
            ruta_id=ruta.id,
            punto_id=item.id_punto_interes,
            id_cliente=item.id_cliente,
            dia=dia,
            prioridad=item.prioridad_ruta or "Media",
            activo=True,
            punto_interes_nombre=item.punto_de_interes,
        ))

    ya_asignado = db.query(MercaderistaRuta).filter(
        MercaderistaRuta.mercaderista_id == data.id_mercaderista,
        MercaderistaRuta.ruta_id == ruta.id,
    ).first()
    if not ya_asignado:
        db.add(MercaderistaRuta(mercaderista_id=data.id_mercaderista, ruta_id=ruta.id, tipo_ruta="Backup"))

    db.commit()
    logger.info(f"Ruta BCK creada: {nombre} (id={ruta.id}), {len(data.items)} PDV(s), mercaderista={data.id_mercaderista}")
    return {"ok": True, "id_ruta": ruta.id, "nombre_ruta": nombre, "dia": dia, "cantidad_pdvs": len(data.items)}
