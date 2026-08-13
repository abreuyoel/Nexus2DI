"""
Endpoints de Chat del Mercaderista.
  GET  /api/merc/chat/inbox              → Bandeja de conversaciones
  GET  /api/merc/chat/visitas/{id}       → Mensajes de una visita
  POST /api/merc/chat/enviar             → Enviar mensaje
  GET  /api/merc/chat/notificaciones     → Rechazos, aprobaciones, visitas revisadas

  ── Grupos de Chat ─────────────────────────────────────────────────────
  GET  /api/merc/chat/grupos/mis-grupos                     → Grupos del mercaderista
  GET  /api/merc/chat/grupos/{id_grupo}/mensajes            → Mensajes del grupo
  POST /api/merc/chat/grupos/{id_grupo}/mensajes            → Enviar al grupo
  GET  /api/merc/chat/grupos/{id_grupo}/miembros            → Miembros del grupo
  GET  /api/merc/chat/grupos/{id_grupo}/visitas-activas     → Visitas con hilo
  GET  /api/merc/chat/grupos/{id_grupo}/visitas/{id_visita} → Mensajes hilo visita
  POST /api/merc/chat/grupos/{id_grupo}/visitas/{id_visita} → Enviar a hilo visita
  POST /api/merc/chat/grupos/{id_grupo}/marcar-leido        → Marcar leído grupo
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.entities import Usuario

from app.mercaderista.services.chat_service import ChatService
from app.mercaderista.schemas import (
    ChatInboxItem, ChatMensajeResponse, EnviarMensajeRequest,
    NotificacionesResponse,
    GrupoChatItem, MiembroGrupoItem, MensajeGrupoItem, EnviarMensajeGrupoRequest,
    VisitaGrupoChatItem, MensajeGrupoVisitaItem,
)

router = APIRouter(prefix="/api/merc/chat", tags=["Mercaderista - Chat"])


@router.get("/inbox", response_model=list[ChatInboxItem])
def get_inbox(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Bandeja de conversaciones del mercaderista (solo visitas con mensajes)."""
    service = ChatService(db)
    return service.get_inbox(current_user)


@router.get("/visitas/{visita_id}", response_model=list[ChatMensajeResponse])
def get_mensajes(
    visita_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Mensajes de chat de una visita específica."""
    service = ChatService(db)
    return service.get_mensajes(visita_id)


@router.post("/enviar", response_model=ChatMensajeResponse)
def enviar_mensaje(
    payload: EnviarMensajeRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Envía un mensaje de chat en el contexto de una visita."""
    service = ChatService(db)
    return service.enviar_mensaje(
        current_user, payload.visita_id, payload.mensaje, payload.sender_nombre
    )


@router.get("/notificaciones", response_model=NotificacionesResponse)
def get_notificaciones(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Notificaciones del mercaderista: fotos rechazadas (con motivo), fotos
    aprobadas y visitas marcadas como 'Revisado' por el analista.
    Equivale a fetchRechazos() + fetchEventos() de la APK.
    """
    service = ChatService(db)
    return service.get_notificaciones(current_user)


# ═══════════════════════════════════════════════════════════════════════════════
# GRUPOS DE CHAT (Equipo Operativo / Equipo + Cliente)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/grupos/mis-grupos", response_model=list[GrupoChatItem])
def get_mis_grupos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Grupos de chat (operativo / operativo_cliente) a los que pertenece el
    mercaderista, con conteo de no-leídos y preview del último mensaje."""
    service = ChatService(db)
    return service.get_mis_grupos(current_user)


@router.get("/grupos/{id_grupo}/mensajes", response_model=list[MensajeGrupoItem])
def get_mensajes_grupo(
    id_grupo: int,
    limit: int = Query(50, le=200),
    before_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Mensajes del chat general de un grupo."""
    service = ChatService(db)
    return service.get_mensajes_grupo(current_user, id_grupo, limit, before_id)


@router.post("/grupos/{id_grupo}/mensajes", response_model=MensajeGrupoItem, status_code=201)
def enviar_mensaje_grupo(
    id_grupo: int,
    payload: EnviarMensajeGrupoRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Envía un mensaje al chat general del grupo."""
    service = ChatService(db)
    return service.enviar_mensaje_grupo(current_user, id_grupo, payload.mensaje)


@router.get("/grupos/{id_grupo}/miembros", response_model=list[MiembroGrupoItem])
def get_miembros_grupo(
    id_grupo: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Miembros del grupo (resolución dinámica desde las tablas operativas)."""
    service = ChatService(db)
    return service.get_miembros_grupo(current_user, id_grupo)


@router.get("/grupos/{id_grupo}/visitas-activas", response_model=list[VisitaGrupoChatItem])
def get_visitas_activas_grupo(
    id_grupo: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Visitas que ya tienen un sub-hilo de chat iniciado en este grupo."""
    service = ChatService(db)
    return service.get_visitas_activas_grupo(current_user, id_grupo)


@router.get(
    "/grupos/{id_grupo}/visitas/{id_visita}",
    response_model=list[MensajeGrupoVisitaItem],
)
def get_mensajes_grupo_visita(
    id_grupo: int,
    id_visita: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Mensajes del sub-hilo de chat de una visita dentro del grupo."""
    service = ChatService(db)
    return service.get_mensajes_grupo_visita(current_user, id_grupo, id_visita)


@router.post(
    "/grupos/{id_grupo}/visitas/{id_visita}",
    response_model=MensajeGrupoVisitaItem,
    status_code=201,
)
def enviar_mensaje_grupo_visita(
    id_grupo: int,
    id_visita: int,
    payload: EnviarMensajeGrupoRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Envía un mensaje al sub-hilo de chat de una visita dentro del grupo."""
    service = ChatService(db)
    return service.enviar_mensaje_grupo_visita(current_user, id_grupo, id_visita, payload.mensaje)


@router.post("/grupos/{id_grupo}/marcar-leido")
def marcar_leido_grupo(
    id_grupo: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Marca el grupo como leído hasta su último mensaje."""
    service = ChatService(db)
    return service.marcar_leido_grupo(current_user, id_grupo)
