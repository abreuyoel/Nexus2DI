"""
Endpoints de Rutas del Mercaderista.
GET  /api/merc/rutas          → Rutas del día con PDVs y clientes
POST /api/merc/ruta/activar   → Activar una ruta (persiste en RUTAS_ACTIVADAS)
GET  /api/merc/pdv-activos    → PDVs con trabajo pendiente hoy
GET  /api/merc/productos      → Catálogo de productos para balance
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import Usuario
from app.mercaderista.services.ruta_service import RutaService
from app.mercaderista.services.pdv_service import PdvService
from app.mercaderista.services.visita_service import VisitaService
from app.mercaderista.schemas import (
    MisRutasResponse, PdvActivoResponse, ProductosCatalogoResponse,
    ProgramacionResponse,
    ActivarRutaRequest, ActivarRutaResponse,
    FinalizarRutaRequest, FinalizarRutaResponse,
)

router = APIRouter(prefix="/api/merc", tags=["Mercaderista - Rutas"])


@router.get("/rutas", response_model=MisRutasResponse)
def get_mis_rutas(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Rutas del día del mercaderista autenticado.
    Devuelve rutas fijas y variables con sus PDVs y clientes programados para hoy.
    Incluye estado de visita por cada cliente.
    """
    service = RutaService(db)
    return service.get_mis_rutas(current_user)


@router.get("/pdv-activos", response_model=list[PdvActivoResponse])
def get_pdv_activos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    PDVs activos con trabajo pendiente hoy.
    Muestra clientes pendientes, listos y si falta desactivación.
    """
    service = PdvService(db)
    return service.get_pdv_activos(current_user)


@router.get("/productos", response_model=ProductosCatalogoResponse)
def get_productos_catalogo(
    id_cliente: Optional[int] = Query(None, description="Filtrar por categorías del cliente"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Catálogo completo de productos agrupados por categoría para el formulario
    de balance. Si se especifica id_cliente, filtra solo las categorías
    asignadas a ese cliente.
    Equivale a getProductos() de la APK (/api/mobile/productos).
    """
    service = VisitaService(db)
    return service.get_productos_catalogo(id_cliente)


@router.get("/programacion", response_model=ProgramacionResponse)
def get_programacion(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Programación completa del día para el mercaderista.
    Incluye rutas (fijas y variables) con PDVs y clientes, más el catálogo
    completo de productos. Equivale a getProgramacion() de la APK.
    """
    service = RutaService(db)
    return service.get_programacion_completa(current_user)


@router.get("/ruta/{id_ruta}/pdvs")
def get_pdvs_de_ruta(
    id_ruta: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Todos los PDVs (y clientes) de una ruta específica, sin filtro de día.
    Usado por el frontend cuando el mercaderista abre la ejecución de una ruta
    para ver todos sus puntos de venta.
    """
    service = RutaService(db)
    return service.get_pdvs_de_ruta(current_user, id_ruta)


@router.post("/ruta/activar", response_model=ActivarRutaResponse)
def activar_ruta(
    body: ActivarRutaRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Activa una ruta completa para el mercaderista.
    Persiste en RUTAS_ACTIVADAS para que la activación sobreviva a refrescos
    del navegador y cierres de sesión. Idempotente: si ya existe una activación
    para esa ruta hoy, retorna ya_activado=True.
    Equivale a g.activarRuta() de la APK.
    """
    service = PdvService(db)
    return service.activar_ruta(current_user, body.id_ruta)


@router.post("/ruta/finalizar", response_model=FinalizarRutaResponse)
def finalizar_ruta(
    body: FinalizarRutaRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Finaliza una ruta previamente activada. Marca el registro en RUTAS_ACTIVADAS
    como 'Finalizado' para que get_mis_rutas() no la devuelva como activada.
    Equivale a g.finalizarRuta() de la APK.
    """
    service = PdvService(db)
    return service.finalizar_ruta(current_user, body.id_ruta)
