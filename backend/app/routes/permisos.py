"""Catálogo de módulos/submódulos permisables (tabla MODULOS).
Los permisos por usuario se gestionan en /api/users/{id}/permissions
(tabla usuario_permisos, module = MODULOS.clave)."""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import Usuario

router = APIRouter(prefix="/api", tags=["Permisos"])


@router.get("/modulos")
def list_modulos(db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    rows = db.execute(text("""
        SELECT id_modulo, clave, nombre, id_padre, tipo, ruta, icono, orden
        FROM MODULOS WHERE activo = 1 ORDER BY orden, id_modulo
    """)).fetchall()
    return [{"id": r[0], "clave": r[1], "nombre": r[2], "id_padre": r[3],
             "tipo": r[4], "ruta": r[5], "icono": r[6], "orden": r[7]} for r in rows]
