from typing import Optional, List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.entities import Usuario
from app.modules.clients.entities import Cliente
from app.modules.routes.entities import RutaProgramacion, AnalistaRuta
from app.modules.analysts.entities import AnalistaCliente
from app.modules.reporting.dto import ClienteCentroMandoResponse, ClienteCentroMandoItem

router = APIRouter()


@router.get("/clientes")
def listar_clientes(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    try:
        q = (
            db.query(Cliente.id, Cliente.nombre)
            .distinct()
            .join(RutaProgramacion, RutaProgramacion.id_cliente == Cliente.id)
            .filter(RutaProgramacion.activo == True, Cliente.nombre.isnot(None))
        )
        if current_user.is_analyst and current_user.id_perfil:
            analista_id = int(current_user.id_perfil)
            sub_rp = (
                db.query(RutaProgramacion.id_cliente)
                .join(AnalistaRuta, RutaProgramacion.ruta_id == AnalistaRuta.id_ruta)
                .filter(AnalistaRuta.id_analista == analista_id)
                .subquery()
            )
            sub_ac = (
                db.query(AnalistaCliente.id_cliente)
                .filter(AnalistaCliente.id_analista == analista_id)
                .subquery()
            )
            q = q.filter(Cliente.id.in_(sub_rp), Cliente.id.in_(sub_ac))

        rows = q.order_by(Cliente.nombre).all()
        return ClienteCentroMandoResponse(
            success=True,
            clientes=[ClienteCentroMandoItem(id_cliente=r[0], cliente=r[1]) for r in rows]
        )
    except Exception as e:
        return ClienteCentroMandoResponse(success=False, message=str(e), clientes=[])
