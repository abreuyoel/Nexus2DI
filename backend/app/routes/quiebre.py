"""Quiebre dinámico -- roadmap predictivo, N2. Ver app/services/quiebre_service.py
para el diseño completo (Capa 1: línea base por percentiles, Capa 2: señal
de riesgo + urgencia temporal)."""
import logging
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db, SessionLocal
from app.core.dependencies import require_permission

logger = logging.getLogger("app")

router = APIRouter(prefix="/api/quiebre", tags=["Quiebre Dinámico"])


def _recalcular_linea_base_background():
    from app.services.quiebre_service import calcular_linea_base
    db = SessionLocal()
    try:
        r = calcular_linea_base(db)
        logger.info(f"[Quiebre] Línea base recalculada: {r}")
    except Exception as e:
        db.rollback()
        logger.error(f"[Quiebre] Error calculando línea base: {e}")
    finally:
        db.close()


def _recalcular_alertas_background():
    from app.services.quiebre_service import calcular_alertas
    db = SessionLocal()
    try:
        r = calcular_alertas(db)
        logger.info(f"[Quiebre] Alertas recalculadas: {r}")
    except Exception as e:
        db.rollback()
        logger.error(f"[Quiebre] Error calculando alertas: {e}")
    finally:
        db.close()


@router.post("/linea-base/recalcular")
def recalcular_linea_base(
    background_tasks: BackgroundTasks, sincrono: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission('plan-accion.recalcular', 'read')),
):
    """Capa 1 -- corrida nocturna, en background por default. sincrono=true
    devuelve el resultado real en la respuesta (cuántos grupos, con cuántos
    balances)."""
    if sincrono:
        from app.services.quiebre_service import calcular_linea_base
        try:
            return {"ok": True, "resultado": calcular_linea_base(db)}
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
    background_tasks.add_task(_recalcular_linea_base_background)
    return {"ok": True, "started": True}


@router.post("/alertas/recalcular")
def recalcular_alertas(
    background_tasks: BackgroundTasks, sincrono: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission('plan-accion.recalcular', 'read')),
):
    """Capa 2 -- necesita que ya haya corrido /linea-base/recalcular al
    menos una vez (si no hay línea base para un grupo, esas filas quedan
    sin p10/p25 y no disparan riesgo, solo "Normal")."""
    if sincrono:
        from app.services.quiebre_service import calcular_alertas
        return {"ok": True, "resultado": calcular_alertas(db)}
    background_tasks.add_task(_recalcular_alertas_background)
    return {"ok": True, "started": True}


@router.get("/alertas")
def listar_alertas(
    riesgo: Optional[str] = None, urgente: Optional[bool] = None,
    id_cliente: Optional[int] = None, identificador_pdv: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission('plan-accion', 'read')),
):
    where = "WHERE 1=1"
    params: list = []
    if riesgo:
        where += " AND riesgo = ?"; params.append(riesgo)
    if urgente is not None:
        where += " AND urgente = ?"; params.append(1 if urgente else 0)
    if id_cliente:
        where += " AND id_cliente = ?"; params.append(id_cliente)
    if identificador_pdv:
        where += " AND identificador_pdv = ?"; params.append(identificador_pdv)

    conn = db.connection().connection
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT a.id_alerta, a.identificador_pdv, pi.punto_de_interes, a.id_product, a.producto,
               a.id_cliente, c.cliente, a.caras_actual, a.caras_anterior, a.tendencia,
               a.riesgo, a.urgente, a.dias_hasta_proxima_visita, a.dias_para_llegar_a_cero, a.fecha_calculo
        FROM ALERTAS_QUIEBRE a
        LEFT JOIN PUNTOS_INTERES1 pi ON pi.identificador = a.identificador_pdv
        LEFT JOIN CLIENTES c ON c.id_cliente = a.id_cliente
        {where}
        ORDER BY a.urgente DESC, a.riesgo ASC, a.dias_para_llegar_a_cero ASC
    """, params)
    cols = [d[0] for d in cursor.description]
    items = [dict(zip(cols, row)) for row in cursor.fetchall()]

    return {
        "total": len(items),
        "urgentes": sum(1 for i in items if i["urgente"]),
        "items": items,
    }


@router.get("/linea-base/info")
def info_linea_base(db: Session = Depends(get_db), current_user=Depends(require_permission('plan-accion', 'read'))):
    conn = db.connection().connection
    cursor = conn.cursor()
    cursor.execute("SELECT TOP 1 fecha_calculo FROM QUIEBRE_LINEA_BASE ORDER BY fecha_calculo DESC")
    row = cursor.fetchone()
    cursor.execute("SELECT COUNT(*) FROM QUIEBRE_LINEA_BASE")
    n_grupos = cursor.fetchone()[0]
    return {"calculada": row is not None, "fecha_calculo": row[0].isoformat() if row else None, "grupos": n_grupos}
