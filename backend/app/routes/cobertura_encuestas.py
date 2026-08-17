"""Curva de cobertura de encuestas médicas -- roadmap predictivo, S4. Ver
app/services/cobertura_encuestas_service.py para el diseño completo (ajuste
logístico sobre el acumulado semanal de médicos registrados, por estado)."""
import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db, SessionLocal
from app.models.user import Usuario as User
from app.routes.cliente_encuestador import check_rol_cliente_encuestador

logger = logging.getLogger("app")

router = APIRouter(prefix="/api/cobertura-encuestas", tags=["Cobertura Encuestas"])


def _recalcular_background():
    from app.services.cobertura_encuestas_service import calcular_cobertura
    db = SessionLocal()
    try:
        r = calcular_cobertura(db)
        logger.info(f"[CoberturaEncuestas] Recalculada: {r}")
    except Exception as e:
        db.rollback()
        logger.error(f"[CoberturaEncuestas] Error calculando cobertura: {e}")
    finally:
        db.close()


@router.post("/recalcular")
def recalcular(
    background_tasks: BackgroundTasks, sincrono: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Barato de recalcular (todo el histórico de médicos hoy son unos
    cientos de filas) -- pero se deja admin-only de todos modos, mismo
    criterio que el resto de los recálculos manuales de este roadmap."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo un administrador puede recalcular esto.")
    if sincrono:
        from app.services.cobertura_encuestas_service import calcular_cobertura
        try:
            return {"ok": True, "resultado": calcular_cobertura(db)}
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
    background_tasks.add_task(_recalcular_background)
    return {"ok": True, "started": True}


@router.get("/curva")
def obtener_curva(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_rol_cliente_encuestador(current_user, db)
    conn = db.connection().connection
    cursor = conn.cursor()
    cursor.execute("""
        SELECT estado, n_semanas_historial, n_medicos_total, curva_valida,
               asintota_l, tasa_crecimiento_k, semana_punto_medio_x0, r2,
               semana_inicio, serie_json, proyeccion_json, fecha_calculo
        FROM COBERTURA_ENCUESTAS_CURVA
        ORDER BY estado
    """)
    zonas = []
    for row in cursor.fetchall():
        (estado, n_semanas, n_medicos, curva_valida, L, k, x0, r2,
         semana_inicio, serie_json, proyeccion_json, fecha_calculo) = row
        zonas.append({
            "estado": estado,
            "n_semanas_historial": n_semanas,
            "n_medicos_total": n_medicos,
            "curva_valida": bool(curva_valida),
            "asintota_l": L, "tasa_crecimiento_k": k, "semana_punto_medio_x0": x0, "r2": r2,
            "semana_inicio": semana_inicio.isoformat() if semana_inicio else None,
            "serie": json.loads(serie_json) if serie_json else [],
            "proyeccion": json.loads(proyeccion_json) if proyeccion_json else None,
            "fecha_calculo": fecha_calculo.isoformat() if fecha_calculo else None,
        })
    return {"zonas": zonas, "calculada": len(zonas) > 0}
