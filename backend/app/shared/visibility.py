"""Resuelve qué clientes puede ver un usuario coordinador.

Definición por CARDINALIDAD de ruta (no por nombre):
- Una ruta es EXCLUSIVA si tiene exactamente 1 cliente.
- Un cliente es EXCLUSIVO si NO comparte ninguna ruta con otro cliente
  (es decir, no aparece en ninguna ruta con más de 1 cliente).
- Un cliente es TRADEX si aparece en al menos una ruta con >1 cliente.

Roles:
- Coordinador General (rol 11) / admin → todos los clientes (None = sin filtro).
- Coordinador Exclusivo (rol 3) → solo clientes exclusivos.
- Coordinador Tradex (rol 4) → solo clientes tradex (compartidos).
- Cliente normal → su propio id_perfil.
"""
from typing import Optional, List
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.modules.auth.entities import Usuario
from app.modules.routes.entities import RutaProgramacion
from app.modules.clients.entities import ClienteRuta


def coordinator_client_ids(db: Session, user: Usuario) -> Optional[List[int]]:
    """Lista de id_cliente visibles. None = todos (sin filtro)."""
    if user.is_admin or user.is_coordinador_general:
        return None

    rutas_compartidas_sub = (
        db.query(RutaProgramacion.ruta_id)
        .filter(RutaProgramacion.activo == True, RutaProgramacion.id_cliente.isnot(None))
        .group_by(RutaProgramacion.ruta_id)
        .having(func.count(RutaProgramacion.id_cliente.distinct()) > 1)
        .subquery()
    )

    if user.is_coordinador_exclusivo:
        clientes_compartidos_sub = (
            db.query(RutaProgramacion.id_cliente)
            .filter(
                RutaProgramacion.activo == True,
                RutaProgramacion.id_cliente.isnot(None),
                RutaProgramacion.ruta_id.in_(rutas_compartidas_sub)
            )
            .subquery()
        )

        rows = (
            db.query(RutaProgramacion.id_cliente.distinct())
            .filter(
                RutaProgramacion.activo == True,
                RutaProgramacion.id_cliente.isnot(None),
                RutaProgramacion.id_cliente.notin_(clientes_compartidos_sub)
            )
            .all()
        )
        return [r[0] for r in rows]

    if user.is_coordinador_tradex:
        rows = (
            db.query(RutaProgramacion.id_cliente.distinct())
            .filter(
                RutaProgramacion.activo == True,
                RutaProgramacion.id_cliente.isnot(None),
                RutaProgramacion.ruta_id.in_(rutas_compartidas_sub)
            )
            .all()
        )
        return [r[0] for r in rows]

    return [user.id_perfil] if user.id_perfil else []


def client_route_ids(db: Session, user: Usuario) -> Optional[List[int]]:
    """Rutas asignadas a un usuario cliente en CLIENTES_RUTAS."""
    rows = (
        db.query(ClienteRuta.id_ruta)
        .filter(ClienteRuta.id_usuario == user.id, ClienteRuta.activo == True)
        .all()
    )
    return [r[0] for r in rows] if rows else None
