"""
Endpoint de Perfil del Mercaderista.
GET /api/merc/me → Datos del mercaderista autenticado + rutas asignadas.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import Usuario
from app.mercaderista.services.ruta_service import RutaService
from app.mercaderista.schemas import MercaderistaProfile

router = APIRouter(prefix="/api/merc", tags=["Mercaderista - Perfil"])


@router.get("/me", response_model=MercaderistaProfile)
def get_profile(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Perfil del mercaderista autenticado.
    Incluye datos personales y lista de rutas asignadas.
    """
    service = RutaService(db)
    merc = service._get_mercaderista(current_user)
    rutas = service.get_rutas_asignadas(merc.id)

    return MercaderistaProfile(
        id=merc.id,
        nombre=merc.nombre,
        cedula=str(merc.cedula),
        email=merc.email,
        telefono=merc.telefono,
        rutas=[
            {"id_ruta": r["id_ruta"], "tipo": r["tipo"], "nombre": r["nombre"]}
            for r in rutas
        ],
    )
