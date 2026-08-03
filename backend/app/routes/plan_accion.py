"""Plan de Acción -- Fase 2: lectura del último snapshot calculado por el
job en background (app/services/plan_accion_service.py) y disparo manual
del recálculo. Todavía no genera rutas BCK ni asigna backups -- eso es
Fase 3/4."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional

from app.db.session import get_db
from app.core.dependencies import require_analyst_or_admin
from app.models.user import Usuario
from app.services.plan_accion_service import recalcular_plan_accion

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
    params: dict = {}
    if id_ruta:
        where += " AND id_ruta = :id_ruta"
        params["id_ruta"] = id_ruta
    if id_cliente:
        where += " AND id_cliente = :id_cliente"
        params["id_cliente"] = id_cliente
    if tipo_pendiente:
        where += " AND tipo_pendiente = :tipo_pendiente"
        params["tipo_pendiente"] = tipo_pendiente
    if prioridad_ruta:
        where += " AND prioridad_ruta = :prioridad_ruta"
        params["prioridad_ruta"] = prioridad_ruta
    if score_min is not None:
        where += " AND score >= :score_min"
        params["score_min"] = score_min

    rows = db.execute(text(f"""
        SELECT id_pendiente, id_ruta, ruta_nombre, id_punto_interes, punto_de_interes,
               departamento, ciudad, id_cliente, cliente_nombre, prioridad_ruta,
               frecuencia_semanal, periodo, tipo_pendiente, visitas_requeridas,
               visitas_hechas, visitas_faltantes, dias_disponibles, urgencia, score,
               fecha_calculo
        FROM PLAN_ACCION_PENDIENTES
        {where}
        ORDER BY score DESC
    """), params).fetchall()

    items = [dict(r._mapping) for r in rows]

    fecha_calculo = items[0]["fecha_calculo"] if items else None
    total_criticos = sum(1 for i in items if (i["score"] or 0) >= 1)

    return {
        "items": items,
        "total": len(items),
        "total_criticos": total_criticos,
        "fecha_calculo": fecha_calculo,
    }


@router.post("/recalcular")
def recalcular(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_analyst_or_admin),
):
    n = recalcular_plan_accion(db)
    return {"ok": True, "pendientes": n}
