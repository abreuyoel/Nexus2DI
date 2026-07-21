from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from sqlalchemy import func, or_, String
from sqlalchemy.orm import Session

from app.db.session import get_db, SessionLocal
from app.core.dependencies import get_current_user
from app.modules.auth.entities import Usuario
from app.modules.chat.entities import ChatMensaje, ChatConversacion, ChatParticipante
from app.modules.analysts.entities import Analista, AnalistaCliente
from app.modules.merchandisers.entities import Mercaderista, MercaderistaRuta
from app.modules.routes.entities import Ruta, RutaProgramacion, PuntoInteres
from app.modules.visits.entities import Visita
from app.modules.chat.dto import (
    ChatMensajeCreate, ChatMensajeResponse,
    CrearConversacionRequest, ConversacionResponse,
    RecipientsResponse, RecipientUser, RegionRecipient, PdvRecipient,
    InboxItem, VisitSearchResult
)
from app.websockets.manager import manager
from app.websockets.guard import ws_guard
from app.shared.realtime import notify_event

router = APIRouter(prefix="/api/chat", tags=["Chat"])


# ════════════════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════════════════
def _resolve_cliente_id(user: Usuario, requested: Optional[int]) -> Optional[int]:
    if user.is_coordinador_exclusivo:
        return int(requested) if requested else None
    if user.is_client:
        return user.id_perfil
    if requested:
        return int(requested)
    return None


def _is_participant(db: Session, conversacion_id: int, user_id: int) -> bool:
    res = db.query(ChatParticipante.conversacion_id).filter(
        ChatParticipante.conversacion_id == conversacion_id,
        ChatParticipante.usuario_id == user_id
    ).first()
    return res is not None


def _can_access_conversation(db: Session, conv: ChatConversacion, user: Usuario) -> bool:
    if user.is_admin or user.is_coordinador_exclusivo:
        return True
    return _is_participant(db, conv.id, user.id)


# ════════════════════════════════════════════════════════════════════════════
# DESTINATARIOS DISPONIBLES
# ════════════════════════════════════════════════════════════════════════════
@router.get("/recipients", response_model=RecipientsResponse)
def get_recipients(
    cliente_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    cid = _resolve_cliente_id(current_user, cliente_id)

    analistas_q = (
        db.query(
            Usuario.id,
            func.coalesce(Analista.nombre, Usuario.username).label("nombre"),
            Usuario.username
        )
        .distinct()
        .join(Analista, Usuario.id_perfil == Analista.id)
        .join(AnalistaCliente, AnalistaCliente.id_analista == Analista.id)
        .filter(
            Usuario.id_rol == 2,
            func.coalesce(Usuario.activo, True) == True
        )
    )
    if cid is not None:
        analistas_q = analistas_q.filter(AnalistaCliente.id_cliente == cid)
    analistas = analistas_q.order_by(func.coalesce(Analista.nombre, Usuario.username)).all()

    mercs_q = (
        db.query(
            Usuario.id,
            Mercaderista.nombre,
            Mercaderista.cedula
        )
        .distinct()
        .join(Mercaderista, Usuario.id_perfil == Mercaderista.id)
        .join(MercaderistaRuta, MercaderistaRuta.mercaderista_id == Mercaderista.id)
        .join(RutaProgramacion, RutaProgramacion.ruta_id == MercaderistaRuta.ruta_id)
        .filter(
            Usuario.id_rol == 5,
            func.coalesce(Mercaderista.activo, True) == True,
            func.coalesce(Usuario.activo, True) == True
        )
    )
    if cid is not None:
        mercs_q = mercs_q.filter(RutaProgramacion.id_cliente == cid)
    mercs = mercs_q.order_by(Mercaderista.nombre).all()

    regiones_q = (
        db.query(
            Ruta.cuadrante.label("region"),
            func.count(func.distinct(MercaderistaRuta.mercaderista_id)).label("cnt")
        )
        .join(RutaProgramacion, RutaProgramacion.ruta_id == Ruta.id)
        .join(MercaderistaRuta, MercaderistaRuta.ruta_id == Ruta.id)
        .filter(
            Ruta.cuadrante.isnot(None),
            Ruta.cuadrante != ""
        )
    )
    if cid is not None:
        regiones_q = regiones_q.filter(RutaProgramacion.id_cliente == cid)
    regiones = regiones_q.group_by(Ruta.cuadrante).order_by(Ruta.cuadrante).all()

    pdvs_q = (
        db.query(
            PuntoInteres.id.label("identificador"),
            PuntoInteres.nombre.label("punto_de_interes"),
            Ruta.cuadrante.label("region"),
            func.count(func.distinct(MercaderistaRuta.mercaderista_id)).label("cnt")
        )
        .join(RutaProgramacion, RutaProgramacion.punto_id == PuntoInteres.id)
        .join(Ruta, RutaProgramacion.ruta_id == Ruta.id)
        .join(MercaderistaRuta, MercaderistaRuta.ruta_id == Ruta.id)
    )
    if cid is not None:
        pdvs_q = pdvs_q.filter(RutaProgramacion.id_cliente == cid)
    pdvs = pdvs_q.group_by(PuntoInteres.id, PuntoInteres.nombre, Ruta.cuadrante).order_by(PuntoInteres.nombre).all()


    return RecipientsResponse(
        analistas=[
            RecipientUser(id_usuario=r[0], nombre=r[1] or "Analista", subtitulo="Analista")
            for r in analistas
        ],
        mercaderistas=[
            RecipientUser(id_usuario=r[0], nombre=r[1] or "Mercaderista",
                          subtitulo=f"Mercaderista · CI {r[2]}")
            for r in mercs
        ],
        regiones=[RegionRecipient(region=r[0], mercaderistas_count=r[1]) for r in regiones],
        pdvs=[
            PdvRecipient(identificador=r[0], punto_de_interes=r[1] or "",
                          region=r[2], mercaderistas_count=r[3])
            for r in pdvs
        ],
    )


# ════════════════════════════════════════════════════════════════════════════
# CREAR / LISTAR CONVERSACIONES
# ════════════════════════════════════════════════════════════════════════════
def _get_team_user_ids(db: Session, cid: Optional[int]) -> set[int]:
    analistas_q = (
        db.query(Usuario.id)
        .join(Analista, Usuario.id_perfil == Analista.id)
        .join(AnalistaCliente, AnalistaCliente.id_analista == Analista.id)
        .filter(
            Usuario.id_rol == 2,
            func.coalesce(Usuario.activo, True) == True
        )
    )
    if cid is not None:
        analistas_q = analistas_q.filter(AnalistaCliente.id_cliente == cid)
    analista_uids = analistas_q.all()

    merc_q = (
        db.query(Usuario.id)
        .join(MercaderistaRuta, Usuario.id_perfil == MercaderistaRuta.mercaderista_id)
        .join(RutaProgramacion, RutaProgramacion.ruta_id == MercaderistaRuta.ruta_id)
        .filter(
            Usuario.id_rol == 5,
            func.coalesce(Usuario.activo, True) == True
        )
    )
    if cid is not None:
        merc_q = merc_q.filter(RutaProgramacion.id_cliente == cid)
    merc_uids = merc_q.all()

    super_uids = (
        db.query(Usuario.id)
        .filter(
            Usuario.id_rol == 3,
            func.coalesce(Usuario.activo, True) == True
        ).all()
    )

    client_q = (
        db.query(Usuario.id)
        .filter(
            Usuario.id_rol.in_([1, 4, 9, 11, 12]),
            func.coalesce(Usuario.activo, True) == True
        )
    )
    if cid is not None:
        client_q = client_q.filter(Usuario.id_perfil == cid)
    client_uids = client_q.all()

    return {u[0] for u in analista_uids} | {u[0] for u in merc_uids} | {u[0] for u in super_uids} | {u[0] for u in client_uids}


def _get_region_user_ids(db: Session, cid: Optional[int], region: str) -> set[int]:
    query = (
        db.query(Usuario.id)
        .distinct()
        .join(MercaderistaRuta, Usuario.id_perfil == MercaderistaRuta.mercaderista_id)
        .join(Ruta, MercaderistaRuta.ruta_id == Ruta.id)
        .filter(
            Ruta.cuadrante == region,
            Usuario.id_rol == 5,
            func.coalesce(Usuario.activo, True) == True
        )
    )
    if cid is not None:
        query = query.join(RutaProgramacion, RutaProgramacion.ruta_id == Ruta.id).filter(RutaProgramacion.id_cliente == cid)
    rows = query.all()
    return {r[0] for r in rows}


def _get_pdv_user_ids(db: Session, cid: Optional[int], pdv_id: str) -> set[int]:
    query = (
        db.query(Usuario.id)
        .distinct()
        .join(MercaderistaRuta, Usuario.id_perfil == MercaderistaRuta.mercaderista_id)
        .join(RutaProgramacion, RutaProgramacion.ruta_id == MercaderistaRuta.ruta_id)
        .filter(
            RutaProgramacion.punto_id == pdv_id,
            Usuario.id_rol == 5,
            func.coalesce(Usuario.activo, True) == True
        )
    )
    if cid is not None:
        query = query.filter(RutaProgramacion.id_cliente == cid)
    rows = query.all()
    return {r[0] for r in rows}


def _build_direct_title(db: Session, user_a: int, user_b: int) -> str:
    rows = db.query(Usuario.id, Usuario.username).filter(Usuario.id.in_([user_a, user_b])).all()
    names = {r[0]: r[1] for r in rows}
    return f"{names.get(user_a, '?')} ↔ {names.get(user_b, '?')}"


@router.post("/conversations", response_model=ConversacionResponse, status_code=201)
def create_conversation(
    body: CrearConversacionRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    cid = _resolve_cliente_id(current_user, body.cliente_id)

    participantes: set[int] = {current_user.id}

    if body.tipo == "direct":
        if not body.destinatario_id:
            raise HTTPException(status_code=400, detail="destinatario_id requerido para chat directo")
        if body.destinatario_id == current_user.id:
            raise HTTPException(status_code=400, detail="No puedes iniciar un chat contigo mismo")
        participantes.add(body.destinatario_id)
        titulo = body.titulo or _build_direct_title(db, current_user.id, body.destinatario_id)

    elif body.tipo == "group_team":
        participantes |= _get_team_user_ids(db, cid)
        titulo = body.titulo or "Equipo completo"

    elif body.tipo == "group_region":
        if not body.region:
            raise HTTPException(status_code=400, detail="region requerida")
        participantes |= _get_region_user_ids(db, cid, body.region)
        titulo = body.titulo or f"Mercaderistas · {body.region}"
        if not cid:
            row_reg = (
                db.query(RutaProgramacion.id_cliente)
                .join(Ruta, RutaProgramacion.ruta_id == Ruta.id)
                .filter(Ruta.cuadrante == body.region, RutaProgramacion.id_cliente.isnot(None))
                .first()
            )
            if row_reg:
                cid = row_reg[0]

    elif body.tipo == "group_pdv":
        if not body.punto_interes_id:
            raise HTTPException(status_code=400, detail="punto_interes_id requerido")
        participantes |= _get_pdv_user_ids(db, cid, body.punto_interes_id)
        row = db.query(PuntoInteres.nombre).filter(PuntoInteres.id == body.punto_interes_id).first()
        pdv_name = row[0] if row and row[0] else body.punto_interes_id
        titulo = body.titulo or f"Mercaderistas · {pdv_name}"
        if not cid:
            row_pdv = (
                db.query(RutaProgramacion.id_cliente)
                .filter(RutaProgramacion.punto_id == body.punto_interes_id, RutaProgramacion.id_cliente.isnot(None))
                .first()
            )
            if row_pdv:
                cid = row_pdv[0]

    else:
        raise HTTPException(status_code=400, detail=f"Tipo de conversación inválido: {body.tipo}")

    if len(participantes) < 2:
        raise HTTPException(status_code=400, detail="No hay destinatarios para esta conversación")

    conv = ChatConversacion(
        cliente_id=cid or 0,
        tipo=body.tipo,
        titulo=titulo[:200] if titulo else None,
        region=body.region,
        punto_interes_id=body.punto_interes_id,
        creado_por=current_user.id,
        fecha_creacion=datetime.now(),
    )

    db.add(conv)
    db.flush()

    for uid in participantes:
        db.add(ChatParticipante(conversacion_id=conv.id, usuario_id=uid, fecha_union=datetime.now()))

    if body.primer_mensaje:
        mensaje = ChatMensaje(
            conversacion_id=conv.id,
            cliente_id=cid,
            sender_id=current_user.id,
            sender_nombre=current_user.username,
            sender_type="cliente" if current_user.is_client else "usuario",
            mensaje=body.primer_mensaje,
            created_at=datetime.now(),
        )
        db.add(mensaje)

    db.commit()
    db.refresh(conv)

    return ConversacionResponse(
        id=conv.id,
        cliente_id=conv.cliente_id,
        tipo=conv.tipo,
        titulo=conv.titulo,
        region=conv.region,
        punto_interes_id=conv.punto_interes_id,
        creado_por=conv.creado_por,
        fecha_creacion=conv.fecha_creacion,
        participantes_count=len(participantes),
    )


# ════════════════════════════════════════════════════════════════════════════
# LISTAR / VER CONVERSACIONES
# ════════════════════════════════════════════════════════════════════════════
@router.get("/conversations", response_model=List[ConversacionResponse])
def list_conversations(
    cliente_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    query = db.query(ChatConversacion)
    if current_user.is_coordinador_exclusivo:
        if not cliente_id:
            raise HTTPException(status_code=400, detail="cliente_id requerido")
        query = query.filter(ChatConversacion.cliente_id == cliente_id)
    else:
        query = query.join(ChatParticipante, ChatConversacion.id == ChatParticipante.conversacion_id)\
                     .filter(ChatParticipante.usuario_id == current_user.id)

    convs = query.all()
    res = []
    for conv in convs:
        cnt = db.query(func.count(ChatParticipante.usuario_id)).filter(ChatParticipante.conversacion_id == conv.id).scalar() or 0
        last_msg_obj = db.query(ChatMensaje).filter(ChatMensaje.conversacion_id == conv.id).order_by(ChatMensaje.created_at.desc()).first()
        no_leidos = 0
        if not current_user.is_coordinador_exclusivo:
            no_leidos = db.query(func.count(ChatMensaje.id)).filter(
                ChatMensaje.conversacion_id == conv.id,
                ChatMensaje.sender_id != current_user.id,
                func.coalesce(ChatMensaje.leido, False) == False
            ).scalar() or 0

        res.append(ConversacionResponse(
            id=conv.id,
            cliente_id=conv.cliente_id,
            tipo=conv.tipo,
            titulo=conv.titulo,
            region=conv.region,
            punto_interes_id=conv.punto_interes_id,
            creado_por=conv.creado_por,
            fecha_creacion=conv.fecha_creacion,
            participantes_count=int(cnt),
            ultimo_mensaje=last_msg_obj.mensaje if last_msg_obj else None,
            ultimo_mensaje_fecha=last_msg_obj.created_at if last_msg_obj else None,
            no_leidos=int(no_leidos),
        ))

    res.sort(key=lambda c: c.ultimo_mensaje_fecha or c.fecha_creacion or datetime.min, reverse=True)
    return res


@router.get("/conversations/{conv_id}", response_model=ConversacionResponse)
def get_conversation(
    conv_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    conv = db.query(ChatConversacion).filter(ChatConversacion.id == conv_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    if not _can_access_conversation(db, conv, current_user):
        raise HTTPException(status_code=403, detail="No tienes acceso a esta conversación")

    cnt = db.query(func.count(ChatParticipante.usuario_id)).filter(ChatParticipante.conversacion_id == conv_id).scalar() or 0

    return ConversacionResponse(
        id=conv.id, cliente_id=conv.cliente_id, tipo=conv.tipo, titulo=conv.titulo,
        region=conv.region, punto_interes_id=conv.punto_interes_id,
        creado_por=conv.creado_por, fecha_creacion=conv.fecha_creacion,
        participantes_count=int(cnt),
    )


@router.get("/conversations/{conv_id}/messages", response_model=List[ChatMensajeResponse])
def get_conversation_messages(
    conv_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    conv = db.query(ChatConversacion).filter(ChatConversacion.id == conv_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    if not _can_access_conversation(db, conv, current_user):
        raise HTTPException(status_code=403, detail="No tienes acceso")

    unread = db.query(ChatMensaje).filter(
        ChatMensaje.conversacion_id == conv_id,
        ChatMensaje.sender_id != current_user.id,
        func.coalesce(ChatMensaje.leido, False) == False
    ).all()
    for m in unread:
        m.leido = True
    if unread:
        db.commit()

    mensajes = db.query(ChatMensaje).filter(
        ChatMensaje.conversacion_id == conv_id
    ).order_by(ChatMensaje.created_at).all()
    return mensajes


@router.post("/conversations/{conv_id}/messages", response_model=ChatMensajeResponse, status_code=201)
async def send_conversation_message(
    conv_id: int,
    data: ChatMensajeCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    conv = db.query(ChatConversacion).filter(ChatConversacion.id == conv_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    if not _can_access_conversation(db, conv, current_user):
        raise HTTPException(status_code=403, detail="No tienes acceso")

    mensaje = ChatMensaje(
        conversacion_id=conv_id,
        cliente_id=conv.cliente_id,
        sender_id=current_user.id,
        sender_nombre=current_user.username,
        sender_type="cliente" if current_user.is_client else "usuario",
        mensaje=data.mensaje,
        created_at=datetime.now(),
    )
    db.add(mensaje)
    db.commit()
    db.refresh(mensaje)

    try:
        await manager.broadcast_to_room(f"conv_{conv_id}", {
            "id": mensaje.id,
            "conversacion_id": conv_id,
            "sender_id": mensaje.sender_id,
            "sender_nombre": mensaje.sender_nombre,
            "sender_type": mensaje.sender_type,
            "mensaje": mensaje.mensaje,
            "created_at": str(mensaje.created_at),
        })
    except Exception:
        pass

    return mensaje


# ════════════════════════════════════════════════════════════════════════════
# INBOX UNIFICADO (visitas + conversaciones)
# ════════════════════════════════════════════════════════════════════════════
@router.get("/inbox", response_model=List[InboxItem])
def get_chat_inbox(
    cliente_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    cid: Optional[int] = None
    if current_user.is_coordinador_exclusivo:
        if not cliente_id:
            raise HTTPException(status_code=400, detail="cliente_id requerido")
        cid = int(cliente_id)
    elif current_user.is_client:
        cid = current_user.id_perfil

    inbox: list[InboxItem] = []

    if cid is not None:
        visita_ids = (
            db.query(ChatMensaje.visita_id)
            .distinct()
            .filter(
                ChatMensaje.cliente_id == cid,
                ChatMensaje.conversacion_id.is_(None),
                ChatMensaje.visita_id.isnot(None)
            )
            .all()
        )
        v_ids = [v[0] for v in visita_ids if v[0] is not None]

        for vid in v_ids:
            last_msg = (
                db.query(ChatMensaje)
                .filter(ChatMensaje.visita_id == vid, ChatMensaje.conversacion_id.is_(None))
                .order_by(ChatMensaje.created_at.desc())
                .first()
            )
            visita = db.query(Visita).get(vid)
            punto = db.query(PuntoInteres).get(visita.punto_id) if visita and visita.punto_id else None
            no_leidos = db.query(func.count(ChatMensaje.id)).filter(
                ChatMensaje.visita_id == vid,
                ChatMensaje.conversacion_id.is_(None),
                ChatMensaje.sender_id != current_user.id,
                func.coalesce(ChatMensaje.leido, False) == False
            ).scalar() or 0

            inbox.append(InboxItem(
                kind="visit",
                visita_id=vid,
                punto_nombre=punto.nombre if punto else "Punto Desconocido",
                punto_id=punto.id if punto else None,
                fecha_visita=str(visita.fecha) if (visita and visita.fecha) else None,
                last_message=last_msg.mensaje if last_msg else None,
                last_message_date=str(last_msg.created_at) if (last_msg and last_msg.created_at) else None,
                unread_count=int(no_leidos)
            ))

    conv_query = db.query(ChatConversacion)
    if current_user.is_coordinador_exclusivo:
        conv_query = conv_query.filter(ChatConversacion.cliente_id == cid)
    else:
        conv_query = conv_query.join(ChatParticipante, ChatConversacion.id == ChatParticipante.conversacion_id)\
                               .filter(ChatParticipante.usuario_id == current_user.id)

    conv_list = conv_query.all()

    for c in conv_list:
        last_msg = (
            db.query(ChatMensaje)
            .filter(ChatMensaje.conversacion_id == c.id)
            .order_by(ChatMensaje.created_at.desc())
            .first()
        )
        no_leidos = 0
        if not current_user.is_coordinador_exclusivo:
            no_leidos = db.query(func.count(ChatMensaje.id)).filter(
                ChatMensaje.conversacion_id == c.id,
                ChatMensaje.sender_id != current_user.id,
                func.coalesce(ChatMensaje.leido, False) == False
            ).scalar() or 0

        inbox.append(InboxItem(
            kind="conversation",
            conversacion_id=c.id,
            tipo=c.tipo,
            titulo=c.titulo or "(Sin título)",
            last_message=last_msg.mensaje if last_msg else None,
            last_message_date=str(last_msg.created_at) if (last_msg and last_msg.created_at) else None,
            unread_count=int(no_leidos)
        ))

    inbox.sort(key=lambda i: i.last_message_date or "0000-00-00", reverse=True)
    return inbox


# ════════════════════════════════════════════════════════════════════════════
# CHAT POR VISITA — endpoints originales (compatibilidad)
# ════════════════════════════════════════════════════════════════════════════
@router.get("/search-visits", response_model=List[VisitSearchResult])
def search_chat_visits(
    q: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    cliente_id = current_user.id_perfil if current_user.is_client else None

    query = (
        db.query(
            Visita.id.label("visita_id"),
            PuntoInteres.nombre.label("punto_nombre"),
            PuntoInteres.id.label("punto_id"),
            PuntoInteres.cadena.label("cadena"),
            PuntoInteres.departamento.label("region"),
            Visita.fecha.label("fecha_visita"),
            Mercaderista.nombre.label("mercaderista_nombre")
        )
        .outerjoin(PuntoInteres, Visita.punto_id == PuntoInteres.id)
        .outerjoin(Mercaderista, Visita.mercaderista_id == Mercaderista.id)
    )

    if cliente_id:
        query = query.filter(Visita.id_cliente == cliente_id)

    if q:
        search_pattern = f"%{q}%"
        query = query.filter(
            or_(
                func.cast(Visita.id, String).like(search_pattern),
                PuntoInteres.nombre.like(search_pattern),
                PuntoInteres.cadena.like(search_pattern),
                PuntoInteres.departamento.like(search_pattern),
                Mercaderista.nombre.like(search_pattern)
            )
        )

    rows = query.order_by(Visita.fecha.desc()).limit(50).all()

    results = []
    for row in rows:
        results.append(VisitSearchResult(
            visita_id=row[0],
            punto_nombre=row[1] or "Punto Desconocido",
            punto_id=row[2],
            cadena=row[3],
            region=row[4],
            mercaderista_nombre=row[6],
            fecha_visita=str(row[5]) if row[5] else None,
            last_message="Nueva Conversación",
            last_message_date=str(row[5]) if row[5] else None,
            unread_count=0
        ))
    return results


@router.get("/visit/{visita_id}/messages", response_model=List[ChatMensajeResponse])
def get_messages_by_visit(
    visita_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    mensajes = db.query(ChatMensaje).filter(
        ChatMensaje.visita_id == visita_id
    ).order_by(ChatMensaje.created_at).all()

    for msg in mensajes:
        if msg.sender_nombre and msg.sender_nombre.isdigit():
            merc = db.query(Mercaderista).filter(Mercaderista.cedula == msg.sender_nombre).first()
            if merc and merc.nombre:
                msg.sender_nombre = merc.nombre

    return mensajes


@router.post("/send", response_model=ChatMensajeResponse, status_code=201)
def send_message(
    data: ChatMensajeCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    cliente_id = current_user.id_perfil if current_user.is_client else None
    if not cliente_id and data.cliente_id:
        cliente_id = data.cliente_id

    mensaje = ChatMensaje(
        visita_id=data.visita_id,
        cliente_id=cliente_id,
        sender_type="cliente" if current_user.is_client else "usuario",
        sender_id=current_user.id,
        sender_nombre=current_user.username,
        mensaje=data.mensaje,
        created_at=datetime.now()
    )
    db.add(mensaje)
    db.commit()
    db.refresh(mensaje)
    notify_event("chat.message", {"visita_id": mensaje.visita_id, "id": mensaje.id})
    return mensaje


# ════════════════════════════════════════════════════════════════════════════
# WEBSOCKETS
# ════════════════════════════════════════════════════════════════════════════
@router.websocket("/ws/{room}")
async def websocket_chat(websocket: WebSocket, room: str):
    user = await manager.connect_guarded(websocket, f"chat_{room}", require_auth=True)
    if not user:
        return
    try:
        while True:
            data = await websocket.receive_json()
            if not ws_guard.check_rate_limit(websocket):
                await websocket.send_json({"error": "Rate limit exceeded. Please slow down."})
                continue

            db = SessionLocal()
            try:
                conversacion_id = data.get("conversacion_id")
                mensaje = ChatMensaje(
                    visita_id=data.get("visita_id"),
                    cliente_id=data.get("cliente_id"),
                    conversacion_id=conversacion_id,
                    sender_type=data.get("sender_type", "usuario"),
                    sender_id=user.id,
                    sender_nombre=user.username,
                    mensaje=data["mensaje"],
                    created_at=datetime.now()
                )
                db.add(mensaje)
                db.commit()
                db.refresh(mensaje)
                await manager.broadcast_to_room(f"chat_{room}", {
                    "id": mensaje.id,
                    "conversacion_id": mensaje.conversacion_id,
                    "visita_id": mensaje.visita_id,
                    "sender_id": mensaje.sender_id,
                    "sender_nombre": mensaje.sender_nombre,
                    "mensaje": mensaje.mensaje,
                    "created_at": str(mensaje.created_at),
                    "sender_type": mensaje.sender_type,
                })
            finally:
                db.close()
    except WebSocketDisconnect:
        manager.disconnect(websocket, f"chat_{room}")
