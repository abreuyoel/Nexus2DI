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
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.models.user import Usuario

# Rutas que tienen más de un cliente (compartidas / tradex)
_RUTAS_COMPARTIDAS = """
    SELECT id_ruta FROM RUTA_PROGRAMACION
    WHERE activa = 1 AND id_cliente IS NOT NULL
    GROUP BY id_ruta HAVING COUNT(DISTINCT id_cliente) > 1
"""


def coordinator_client_ids(db: Session, user: Usuario) -> Optional[List[int]]:
    """Lista de id_cliente visibles. None = todos (sin filtro)."""
    if user.is_admin or user.is_coordinador_general:
        return None

    if user.is_coordinador_exclusivo:
        # Clientes que NO están en ninguna ruta compartida = exclusivos.
        rows = db.execute(text(f"""
            SELECT DISTINCT rp.id_cliente
            FROM RUTA_PROGRAMACION rp
            WHERE rp.activa = 1 AND rp.id_cliente IS NOT NULL
              AND rp.id_cliente NOT IN (
                    SELECT rp2.id_cliente FROM RUTA_PROGRAMACION rp2
                    WHERE rp2.activa = 1 AND rp2.id_cliente IS NOT NULL
                      AND rp2.id_ruta IN ({_RUTAS_COMPARTIDAS})
              )
        """)).fetchall()
        return [r[0] for r in rows]

    if user.is_coordinador_tradex:
        # Clientes en rutas compartidas = tradex.
        rows = db.execute(text(f"""
            SELECT DISTINCT rp.id_cliente
            FROM RUTA_PROGRAMACION rp
            WHERE rp.activa = 1 AND rp.id_cliente IS NOT NULL
              AND rp.id_ruta IN ({_RUTAS_COMPARTIDAS})
        """)).fetchall()
        return [r[0] for r in rows]

    # cliente normal (rol 1/9/12): solo su perfil
    return [user.id_perfil] if user.id_perfil else []


def client_route_ids(db: Session, user: Usuario) -> Optional[List[int]]:
    """Rutas asignadas a un usuario cliente en CLIENTES_RUTAS.

    None = sin restricción (el usuario no tiene ninguna fila en
    CLIENTES_RUTAS → ve TODAS las rutas de su cliente). Si tiene al menos
    una fila activa, solo ve esas rutas."""
    rows = db.execute(text("""
        SELECT id_ruta FROM CLIENTES_RUTAS WHERE id_usuario = :uid AND activo = 1
    """), {"uid": user.id}).fetchall()
    return [r[0] for r in rows] if rows else None
