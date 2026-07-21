from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.entities import Usuario
from app.modules.routes.entities import PuntoInteres, RutaProgramacion, Ruta
from app.modules.reporting.dto import FiltrosOpcionesResponse, PuntoFilterItem

router = APIRouter()


@router.get("/filtros-opciones")
def filtros_opciones(
    cliente_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    try:
        if current_user.is_client and not current_user.rol == 'admin':
            cliente_id = current_user.id_perfil

        base_q = (
            db.query(PuntoInteres.cadena, PuntoInteres.departamento, Ruta.cuadrante, PuntoInteres.id, PuntoInteres.nombre)
            .distinct()
            .join(RutaProgramacion, RutaProgramacion.punto_id == PuntoInteres.id)
            .outerjoin(Ruta, Ruta.id == RutaProgramacion.ruta_id)
            .filter(RutaProgramacion.activo == True)
        )
        if cliente_id:
            base_q = base_q.filter(RutaProgramacion.id_cliente == cliente_id)

        rows = base_q.all()

        cadenas = sorted({r[0] for r in rows if r[0]})
        regiones = sorted({r[1] for r in rows if r[1]})
        cuadrantes = sorted({r[2] for r in rows if r[2]})

        seen_pts = set()
        puntos = []
        for r in rows:
            if r[3] and r[3] not in seen_pts:
                seen_pts.add(r[3])
                puntos.append(PuntoFilterItem(id=r[3], nombre=r[4] or ""))

        puntos.sort(key=lambda x: x.nombre)

        return FiltrosOpcionesResponse(
            success=True,
            cadenas=cadenas,
            regiones=regiones,
            cuadrantes=cuadrantes,
            puntos=puntos
        )
    except Exception as e:
        return FiltrosOpcionesResponse(success=False, message=str(e))
