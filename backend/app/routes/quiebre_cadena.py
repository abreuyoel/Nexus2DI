"""Quiebre por Cadena -- ver app/services/quiebre_cadena_service.py para el
diseño completo y por qué es un módulo/permiso separado de N2 (quiebre.py).

Fase 1 (acordada 2026-08-19): vista agregada, sin atribución de marca,
acceso admin/analista -- para armar el material de venta hacia las cadenas.
Un rol "cadena" con acceso directo (scoped a SU cadena) es un paso
posterior, condicionado a tener el ok de los clientes-marca relevantes.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import require_permission
from app.services.quiebre_cadena_service import calcular_quiebre_por_cadena, DIAS_VENTANA_DEFAULT

router = APIRouter(prefix="/api/quiebre-cadena", tags=["Quiebre por Cadena"])


@router.get("")
def get_quiebre_por_cadena(
    dias_ventana: int = Query(DIAS_VENTANA_DEFAULT, ge=7, le=90),
    db: Session = Depends(get_db),
    _=Depends(require_permission("quiebre-cadena", "read", fallback_roles=("admin", "analyst"))),
):
    return calcular_quiebre_por_cadena(db, dias_ventana)
