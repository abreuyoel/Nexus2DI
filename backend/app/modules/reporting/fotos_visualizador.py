from datetime import date as _date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.entities import Usuario
from app.modules.routes.entities import PuntoInteres, RutaProgramacion, Ruta
from app.modules.merchandisers.entities import Mercaderista
from app.modules.visits.entities import Visita, Foto
from app.modules.reporting.dto import FotosVisualizadorResponse, FotoVisualizadorItem
from app.shared.azure_service import azure_service

router = APIRouter()


@router.get("/fotos-visualizador")
def fotos_visualizador(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    cliente_id: Optional[int] = None,
    cadena: Optional[str] = None,
    region: Optional[str] = None,
    cuadrante: Optional[str] = None,
    punto_id: Optional[str] = None,
    mercaderista_id: Optional[int] = None,
    estado_foto: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    try:
        if current_user.is_client and not current_user.rol == 'admin':
            cliente_id = current_user.id_perfil

        fi = datetime.strptime(desde, '%Y-%m-%d').date() if desde else _date.today()
        ff = datetime.strptime(hasta, '%Y-%m-%d').date() if hasta else fi

        q = (
            db.query(
                Foto.id,
                Foto.visita_id,
                Foto.fecha_registro,
                Foto.blob_path,
                Foto.estado,
                Foto.id_tipo_foto,
                PuntoInteres.nombre.label("pdv_nombre"),
                PuntoInteres.cadena,
                PuntoInteres.departamento.label("region"),
                Mercaderista.nombre.label("mercaderista")
            )
            .join(Visita, Foto.visita_id == Visita.id)
            .outerjoin(PuntoInteres, PuntoInteres.id == Visita.punto_id)
            .outerjoin(Mercaderista, Mercaderista.id == Visita.mercaderista_id)
            .outerjoin(RutaProgramacion, (RutaProgramacion.punto_id == PuntoInteres.id) & (RutaProgramacion.id_cliente == Visita.id_cliente))
            .outerjoin(Ruta, Ruta.id == RutaProgramacion.ruta_id)
            .filter(Visita.fecha >= fi, Visita.fecha <= ff)
        )

        if cliente_id:
            q = q.filter(Visita.id_cliente == cliente_id)
        if cadena:
            q = q.filter(PuntoInteres.cadena == cadena)
        if region:
            q = q.filter(PuntoInteres.departamento == region)
        if cuadrante:
            q = q.filter(Ruta.cuadrante == cuadrante)
        if punto_id:
            q = q.filter(Visita.punto_id == punto_id)
        if mercaderista_id:
            q = q.filter(Visita.mercaderista_id == mercaderista_id)
        if estado_foto:
            q = q.filter(Foto.estado == estado_foto)

        total = q.count()
        rows = q.order_by(Foto.fecha_registro.desc(), Foto.id.desc()).offset(offset).limit(limit).all()

        fotos_list = []
        for r in rows:
            blob_path = r[3]
            url = None
            if blob_path:
                try:
                    url = azure_service.get_sas_url(blob_path)
                except Exception:
                    url = f"/api/merc/foto/{r[0]}"

            fotos_list.append(FotoVisualizadorItem(
                id_foto=r[0],
                visita_id=r[1],
                fecha=str(r[2]) if r[2] else None,
                blob_path=blob_path,
                url=url,
                estado=r[4],
                tipo_nombre=f"Tipo {r[5]}" if r[5] else "General",
                pdv_nombre=r[6],
                cadena=r[7],
                region=r[8],
                mercaderista=r[9]
            ))

        return FotosVisualizadorResponse(
            success=True,
            total=total,
            fotos=fotos_list
        )

    except Exception as e:
        return FotosVisualizadorResponse(success=False, total=0, fotos=[], message=str(e))
