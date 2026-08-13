"""
Endpoints de Visitas del Mercaderista.
  POST   /api/merc/visitas/iniciar       → Iniciar visita
  GET    /api/merc/visitas               → Historial de visitas
  GET    /api/merc/visitas/{id}/fotos     → Fotos de una visita
  POST   /api/merc/visitas/{id}/fotos     → Subir foto
  POST   /api/merc/visitas/{id}/balances  → Guardar balances
  POST   /api/merc/visitas/{id}/finalizar → Finalizar visita
  GET    /api/merc/visitas/{id}/productos → Productos para balance
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import Usuario
from app.mercaderista.services.visita_service import VisitaService
from app.mercaderista.schemas import (
    IniciarVisitaRequest, IniciarVisitaResponse,
    VisitaHistorialItem, FotosVisitaResponse,
    BalanceRequest, BalanceResponse,
    FinalizarVisitaRequest, FinalizarVisitaResponse,
    ProductoParaBalance,
    VisitaDetalleResponse,
    AuditoriaTiempoRequest, AuditoriaTiempoResponse,
    ReabrirVisitaRequest,
)

router = APIRouter(prefix="/api/merc/visitas", tags=["Mercaderista - Visitas"])


# ── Iniciar Visita ───────────────────────────────────────────────────────────

@router.post("/iniciar", response_model=IniciarVisitaResponse)
def iniciar_visita(
    payload: IniciarVisitaRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Crea una nueva visita o devuelve una existente del día."""
    service = VisitaService(db)
    return service.iniciar_visita(current_user, payload.id_punto, payload.id_cliente)


# ── Historial ────────────────────────────────────────────────────────────────

@router.get("", response_model=List[VisitaHistorialItem])
def list_visitas(
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Historial de visitas del mercaderista autenticado."""
    service = VisitaService(db)
    return service.get_mis_visitas(current_user, fecha_inicio, fecha_fin)


# ── Fotos ────────────────────────────────────────────────────────────────────

@router.get("/{visita_id}/fotos", response_model=FotosVisitaResponse)
def get_fotos_visita(
    visita_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Fotos de una visita agrupadas por tipo."""
    service = VisitaService(db)
    return service.get_fotos_visita(visita_id)


@router.post("/{visita_id}/fotos")
async def upload_foto(
    visita_id: int,
    tipo_foto: str = Form(...),
    file: UploadFile = File(...),
    lat: Optional[float] = Form(None),
    lon: Optional[float] = Form(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Sube una foto para una visita."""
    service = VisitaService(db)
    file_bytes = await file.read()
    return service.upload_foto(
        current_user, visita_id, tipo_foto,
        file_bytes, file.filename or "foto.jpg", lat, lon,
    )


@router.delete("/fotos/{foto_id}")
def delete_foto(
    foto_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Elimina una foto individual de una visita (solo el propio mercaderista)."""
    service = VisitaService(db)
    service.delete_foto(current_user, foto_id)
    return {"ok": True}


# ── Balances ─────────────────────────────────────────────────────────────────

@router.post("/{visita_id}/balances", response_model=BalanceResponse)
def save_balances(
    visita_id: int,
    payload: BalanceRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Guarda los balances de productos de una visita."""
    service = VisitaService(db)
    productos = [p.model_dump() for p in payload.productos]
    return service.save_balances(
        current_user, visita_id, payload.id_cliente, payload.id_pdv, productos
    )


# ── Finalizar ────────────────────────────────────────────────────────────────

@router.post("/{visita_id}/finalizar", response_model=FinalizarVisitaResponse)
def finalizar_visita(
    visita_id: int,
    payload: FinalizarVisitaRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Cierra el ciclo de vida de una visita."""
    # Validar que el visita_id del payload coincide con el de la URL
    if payload.id_visita != visita_id:
        raise HTTPException(status_code=400, detail="id_visita no coincide")
    service = VisitaService(db)
    return service.finalizar_visita(current_user, visita_id)


# ── Productos para Balance ───────────────────────────────────────────────────

@router.get("/{visita_id}/productos", response_model=List[ProductoParaBalance])
def get_productos_balance(
    visita_id: int,
    id_cliente: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Productos disponibles para el formulario de balance de una visita."""
    service = VisitaService(db)
    return service.get_productos_balance(id_cliente)


# ── Detalle Completo de Visita ────────────────────────────────────────────────

@router.get("/{visita_id}/detalle", response_model=VisitaDetalleResponse)
def get_visita_detalle(
    visita_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Detalle completo de una visita: metadata, fotos con estado de revisión
    (incluye motivo de rechazo si aplica), y balances.
    Equivale a getDataVisita() de la APK.
    """
    service = VisitaService(db)
    return service.get_visita_detalle(current_user, visita_id)


# ── Auditoría de Temporizador ──────────────────────────────────────────────────

@router.post("/auditoria-tiempo", response_model=AuditoriaTiempoResponse)
def registrar_auditoria_tiempo(
    payload: AuditoriaTiempoRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Registra una auditoría de tiempo para una visita o punto de interés."""
    service = VisitaService(db)
    return service.registrar_auditoria_tiempo(current_user, payload)


# ── Reabrir Visita ────────────────────────────────────────────────────────────

@router.post("/{visita_id}/reabrir")
def reabrir_visita(
    visita_id: int,
    body: ReabrirVisitaRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Reabre una visita finalizada. Solo reabre el PDV, no la ruta."""
    service = VisitaService(db)
    return service.reabrir_visita(current_user, visita_id, body.motivo)
