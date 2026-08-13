"""
Endpoints de PDV (Activación / Desactivación).
  POST /api/merc/pdv/activar              → Activar PDV
  POST /api/merc/pdv/desactivar           → Desactivar PDV
  GET  /api/merc/pdv/{id}/validar-cierre  → Validar cierre (NUEVO)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import Usuario
from app.mercaderista.services.pdv_service import PdvService
from app.mercaderista.schemas import (
    ActivarPdvRequest, ActivarPdvResponse,
    DesactivarPdvRequest, DesactivarPdvResponse,
    ValidarCierrePdvResponse,
)

router = APIRouter(prefix="/api/merc/pdv", tags=["Mercaderista - PDV"])


@router.post("/activar", response_model=ActivarPdvResponse)
def activar_pdv(
    payload: ActivarPdvRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Registra la activación de un PDV al iniciar la jornada en ese punto.
    Solo se activa una vez por día por mercaderista.
    """
    service = PdvService(db)
    return service.activar_pdv(current_user, payload.id_punto, payload.id_ruta)


@router.post("/desactivar", response_model=DesactivarPdvResponse)
def desactivar_pdv(
    payload: DesactivarPdvRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Desactiva un PDV al finalizar todos los clientes del punto.
    El frontend DEBE llamar a validar-cierre antes de este endpoint.
    """
    service = PdvService(db)
    return service.desactivar_pdv(current_user, payload.id_punto)


@router.get("/{id_punto}/validar-cierre", response_model=ValidarCierrePdvResponse)
def validar_cierre_pdv(
    id_punto: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    🔴 NUEVO: Valida que todos los clientes programados en un PDV para hoy
    estén visitados antes de permitir la desactivación.

    La APK valida esto del lado del cliente (SQLite local). En la web,
    este endpoint reemplaza esa validación.

    Retorna:
    - puede_cerrar: bool
    - total_clientes: cuántos clientes hay programados hoy
    - clientes_visitados: cuántos ya tienen visita
    - clientes_pendientes: nombres de los que faltan
    - mensaje: resumen legible
    """
    service = PdvService(db)
    return service.validar_cierre_pdv(current_user, id_punto)
