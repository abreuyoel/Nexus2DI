"""Quiebre dinámico -- roadmap predictivo, N2. Ver app/services/quiebre_service.py
para el diseño completo (Capa 1: línea base por percentiles, Capa 2: señal
de riesgo + urgencia temporal)."""
import logging
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import text, select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.session import get_db, get_async_db, SessionLocal
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
async def recalcular_linea_base(
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
async def recalcular_alertas(
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
async def listar_alertas(
    riesgo: Optional[str] = None, urgente: Optional[bool] = None,
    id_cliente: Optional[int] = None, identificador_pdv: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(require_permission('plan-accion', 'read')),
):
    where = "WHERE 1=1"
    params: dict = {}
    if riesgo:
        where += " AND a.riesgo = :riesgo"; params["riesgo"] = riesgo
    if urgente is not None:
        where += " AND a.urgente = :urgente"; params["urgente"] = 1 if urgente else 0
    if id_cliente:
        where += " AND a.id_cliente = :id_cliente"; params["id_cliente"] = id_cliente
    if identificador_pdv:
        where += " AND a.identificador_pdv = :identificador_pdv"; params["identificador_pdv"] = identificador_pdv

    q = f"""
        SELECT a.id_alerta, a.identificador_pdv, pi.punto_de_interes, a.id_product, a.producto,
               a.id_cliente, c.cliente, a.caras_actual, a.caras_anterior, a.tendencia,
               a.riesgo, a.urgente, a.dias_hasta_proxima_visita, a.dias_para_llegar_a_cero, a.fecha_calculo
        FROM ALERTAS_QUIEBRE a
        LEFT JOIN PUNTOS_INTERES1 pi ON pi.identificador = a.identificador_pdv
        LEFT JOIN CLIENTES c ON c.id_cliente = a.id_cliente
        {where}
        ORDER BY a.urgente DESC, a.riesgo ASC, a.dias_para_llegar_a_cero ASC
    """
    rows = (await db.execute(text(q), params)).mappings().all()
    items = [dict(r) for r in rows]

    return {
        "total": len(items),
        "urgentes": sum(1 for i in items if i["urgente"]),
        "items": items,
    }


@router.get("/pronostico")
async def pronostico_quiebre(
    id_cliente: Optional[int] = None, horizonte_semanas: int = 6,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission('plan-accion', 'read')),
):
    """S1 -- Fase 2 de Quiebre. Pronostica, para las combinaciones SKU×PDV
    que N2 YA marcó en riesgo, cuántas semanas de historial real hay y --
    si alcanza el mínimo -- una proyección de `caras` a futuro con banda de
    error. Las combinaciones sin suficiente historial se listan igual, con
    suficiente_historial=false, nunca se omiten en silencio."""
    from app.services.quiebre_forecast_service import calcular_pronostico_quiebre
    try:
        return calcular_pronostico_quiebre(db, id_cliente=id_cliente, horizonte_semanas=horizonte_semanas)
    except Exception as e:
        logger.error(f"[S1] Error calculando pronóstico: {e}")
        raise HTTPException(status_code=500, detail="Error calculando el pronóstico de quiebre")


@router.get("/linea-base/info")
async def info_linea_base(db: AsyncSession = Depends(get_async_db), current_user=Depends(require_permission('plan-accion', 'read'))):
    row = (await db.execute(text("SELECT TOP 1 fecha_calculo FROM QUIEBRE_LINEA_BASE ORDER BY fecha_calculo DESC"))).fetchone()
    n_grupos = (await db.execute(text("SELECT COUNT(*) FROM QUIEBRE_LINEA_BASE"))).scalar() or 0
    return {"calculada": row is not None, "fecha_calculo": row[0].isoformat() if row and row[0] else None, "grupos": n_grupos}
