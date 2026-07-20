from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from datetime import datetime

from app.db.session import get_db, SessionLocal
from app.core.dependencies import get_current_user
from app.models.user import Usuario
from app.models.chat import ChatMensaje, ChatConversacion, ChatParticipante, ChatMensajeLectura
from app.schemas.chat import (
    ChatMensajeCreate, ChatMensajeResponse, LectorInfo,
    CrearConversacionRequest, ConversacionResponse,
    RecipientsResponse, RegionRecipient, PdvRecipient,
    InboxItem,
)
from app.websockets.manager import manager

router = APIRouter(prefix="/api/chat", tags=["Chat"])


# ════════════════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════════════════
def _resolve_cliente_id(user: Usuario, requested: Optional[int]) -> int:
    """Igual que en client_photos: el coordinador exclusivo pasa cliente_id explícito."""
    if user.is_coordinador_exclusivo:
        if not requested:
            raise HTTPException(status_code=400, detail="cliente_id requerido para coordinador exclusivo")
        return int(requested)
    if user.is_client:
        if not user.id_perfil:
            raise HTTPException(status_code=400, detail="No tienes cliente asociado")
        return user.id_perfil
    # Staff (analista, supervisor, mercaderista, admin) puede usar el cliente_id provisto
    if requested:
        return int(requested)
    raise HTTPException(status_code=400, detail="cliente_id requerido")


def _is_participant(db: Session, conversacion_id: int, user_id: int) -> bool:
    row = db.execute(
        text("SELECT 1 FROM CHAT_PARTICIPANTES WHERE id_conversacion = :c AND id_usuario = :u"),
        {"c": conversacion_id, "u": user_id},
    ).fetchone()
    return row is not None


def _can_access_conversation(db: Session, conv: ChatConversacion, user: Usuario) -> bool:
    """Coordinador exclusivo y admin pueden ver cualquier conversación.
    El resto debe ser participante."""
    if user.is_admin or user.is_coordinador_exclusivo:
        return True
    return _is_participant(db, conv.id, user.id)


# ════════════════════════════════════════════════════════════════════════════
# RECIBOS DE LECTURA (estilo WhatsApp)
# ════════════════════════════════════════════════════════════════════════════
def _mark_leidos(db: Session, user: Usuario, conv_id: Optional[int] = None,
                  visita_id: Optional[int] = None) -> List[int]:
    """Inserta un recibo de lectura por cada mensaje ajeno de la conversación
    (o del chat de visita legacy) que este usuario todavía no había leído, y
    devuelve los id_mensaje recién marcados (para el broadcast por websocket).

    No es responsabilidad de esta función decidir si el usuario tiene acceso
    a la conversación/visita — eso ya se valida antes de llamarla.
    """
    if conv_id is not None:
        where = "m.id_conversacion = :ref"
        ref = conv_id
    else:
        where = "m.id_visita = :ref AND m.id_conversacion IS NULL"
        ref = visita_id

    pending = db.execute(text(f"""
        SELECT m.id_mensaje FROM CHAT_MENSAJES_CLIENTE m
        WHERE {where} AND m.id_usuario <> :uid
          AND NOT EXISTS (
              SELECT 1 FROM CHAT_MENSAJE_LECTURAS l
              WHERE l.id_mensaje = m.id_mensaje AND l.id_usuario = :uid
          )
    """), {"ref": ref, "uid": user.id}).fetchall()

    ids = [r[0] for r in pending]
    if not ids:
        return []

    ahora = datetime.now()
    for mid in ids:
        db.add(ChatMensajeLectura(mensaje_id=mid, usuario_id=user.id,
                                   username=user.username, fecha_lectura=ahora))
    db.commit()
    return ids


def _attach_leido_por(db: Session, mensajes: List[ChatMensaje]) -> List[ChatMensajeResponse]:
    """Construye ChatMensajeResponse a mano para cada mensaje, con su lista
    de lectores (leido_por) — no es un campo mapeado en el ORM, así que no
    se puede depender de la conversión automática de response_model."""
    ids = [m.id for m in mensajes]
    lecturas_map: dict[int, list[LectorInfo]] = {}
    if ids:
        ph = ",".join(str(int(i)) for i in ids)
        rows = db.execute(text(f"""
            SELECT id_mensaje, id_usuario, username, fecha_lectura
            FROM CHAT_MENSAJE_LECTURAS WHERE id_mensaje IN ({ph})
            ORDER BY fecha_lectura
        """)).fetchall()
        for r in rows:
            lecturas_map.setdefault(r[0], []).append(
                LectorInfo(id_usuario=r[1], username=r[2], fecha_lectura=r[3])
            )

    from app.services.azure_service import azure_service

    return [
        ChatMensajeResponse(
            id=m.id, visita_id=m.visita_id, cliente_id=m.cliente_id,
            conversacion_id=m.conversacion_id, sender_type=m.sender_type,
            sender_id=m.sender_id, sender_nombre=m.sender_nombre, mensaje=m.mensaje,
            leido=m.leido, created_at=m.created_at,
            leido_por=lecturas_map.get(m.id, []),
            foto_adjunta=azure_service.get_sas_url(m.foto_adjunta) if m.foto_adjunta else None,
        )
        for m in mensajes
    ]


# ════════════════════════════════════════════════════════════════════════════
# DESTINATARIOS DISPONIBLES
# ════════════════════════════════════════════════════════════════════════════
@router.get("/recipients", response_model=RecipientsResponse)
def get_recipients(
    cliente_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Devuelve los destinatarios disponibles para crear grupos ad-hoc de
    mercaderistas (region/pdv) — el chat de equipo/visita ya no se crea
    desde acá, se auto-provisiona vía app/routes/chat_grupos.py."""
    cid = _resolve_cliente_id(current_user, cliente_id)

    # Regiones con mercaderistas activos
    regiones = db.execute(text("""
        SELECT rn.cuadrante AS region, COUNT(DISTINCT mr.id_mercaderista) AS cnt
        FROM RUTAS_NUEVAS rn
        JOIN RUTA_PROGRAMACION rp ON rp.id_ruta = rn.id_ruta
        JOIN MERCADERISTAS_RUTAS mr ON mr.id_ruta = rn.id_ruta
        WHERE rp.id_cliente = :cid
          AND rn.cuadrante IS NOT NULL AND rn.cuadrante <> ''
        GROUP BY rn.cuadrante
        ORDER BY rn.cuadrante
    """), {"cid": cid}).fetchall()

    # PDVs con mercaderistas
    pdvs = db.execute(text("""
        SELECT pin.identificador,
               pin.punto_de_interes,
               rn.cuadrante AS region,
               COUNT(DISTINCT mr.id_mercaderista) AS cnt
        FROM PUNTOS_INTERES1 pin
        JOIN RUTA_PROGRAMACION rp ON rp.id_punto_interes = pin.identificador
        JOIN RUTAS_NUEVAS rn ON rp.id_ruta = rn.id_ruta
        JOIN MERCADERISTAS_RUTAS mr ON mr.id_ruta = rn.id_ruta
        WHERE rp.id_cliente = :cid
        GROUP BY pin.identificador, pin.punto_de_interes, rn.cuadrante
        ORDER BY pin.punto_de_interes
    """), {"cid": cid}).fetchall()

    return RecipientsResponse(
        regiones=[RegionRecipient(region=r[0], mercaderistas_count=r[1]) for r in regiones],
        pdvs=[
            PdvRecipient(identificador=r[0], punto_de_interes=r[1],
                         region=r[2], mercaderistas_count=r[3])
            for r in pdvs
        ],
    )


# ════════════════════════════════════════════════════════════════════════════
# CREAR / LISTAR CONVERSACIONES (grupos region/pdv — equipo/visita están en
# chat_grupos.py)
# ════════════════════════════════════════════════════════════════════════════
def _get_region_user_ids(db: Session, cid: int, region: str) -> set[int]:
    """Mercaderistas de cierta región del cliente."""
    rows = db.execute(text("""
        SELECT DISTINCT u.id_usuario
        FROM RUTA_PROGRAMACION rp
        JOIN RUTAS_NUEVAS rn ON rp.id_ruta = rn.id_ruta
        JOIN MERCADERISTAS_RUTAS mr ON mr.id_ruta = rn.id_ruta
        JOIN USUARIOS u ON u.id_perfil = mr.id_mercaderista AND u.id_rol = 5
        WHERE rp.id_cliente = :cid AND rn.cuadrante = :region
          AND ISNULL(u.activo, 1) = 1
    """), {"cid": cid, "region": region}).fetchall()
    return {r[0] for r in rows}


def _get_pdv_user_ids(db: Session, cid: int, pdv_id: str) -> set[int]:
    """Mercaderistas asignados a un PDV del cliente."""
    rows = db.execute(text("""
        SELECT DISTINCT u.id_usuario
        FROM RUTA_PROGRAMACION rp
        JOIN MERCADERISTAS_RUTAS mr ON mr.id_ruta = rp.id_ruta
        JOIN USUARIOS u ON u.id_perfil = mr.id_mercaderista AND u.id_rol = 5
        WHERE rp.id_cliente = :cid AND rp.id_punto_interes = :pdv
          AND ISNULL(u.activo, 1) = 1
    """), {"cid": cid, "pdv": pdv_id}).fetchall()
    return {r[0] for r in rows}


@router.post("/conversations", response_model=ConversacionResponse, status_code=201)
def create_conversation(
    body: CrearConversacionRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    cid = _resolve_cliente_id(current_user, body.cliente_id)

    # Construir el set de participantes según tipo
    participantes: set[int] = {current_user.id}

    if body.tipo == "group_region":
        if not body.region:
            raise HTTPException(status_code=400, detail="region requerida")
        participantes |= _get_region_user_ids(db, cid, body.region)
        titulo = body.titulo or f"Mercaderistas · {body.region}"

    elif body.tipo == "group_pdv":
        if not body.punto_interes_id:
            raise HTTPException(status_code=400, detail="punto_interes_id requerido")
        participantes |= _get_pdv_user_ids(db, cid, body.punto_interes_id)
        # Lookup nombre del PDV
        row = db.execute(text("""
            SELECT punto_de_interes FROM PUNTOS_INTERES1 WHERE identificador = :p
        """), {"p": body.punto_interes_id}).fetchone()
        pdv_name = row[0] if row else body.punto_interes_id
        titulo = body.titulo or f"Mercaderistas · {pdv_name}"

    else:
        raise HTTPException(status_code=400, detail=f"Tipo de conversación inválido: {body.tipo}")

    if len(participantes) < 2:
        raise HTTPException(status_code=400, detail="No hay destinatarios para esta conversación")

    # Crear conversación + participantes
    conv = ChatConversacion(
        cliente_id=cid,
        tipo=body.tipo,
        titulo=titulo[:200] if titulo else None,
        region=body.region,
        punto_interes_id=body.punto_interes_id,
        creado_por=current_user.id,
        fecha_creacion=datetime.now(),
    )
    db.add(conv)
    db.flush()  # para tener conv.id

    for uid in participantes:
        db.add(ChatParticipante(conversacion_id=conv.id, usuario_id=uid, fecha_union=datetime.now()))

    # Primer mensaje opcional
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
    """Listar las conversaciones del usuario actual.

    - Coordinador exclusivo: todas las conversaciones del cliente_id que pase.
    - Resto: solo aquellas donde es participante.
    """
    if current_user.is_coordinador_exclusivo:
        if not cliente_id:
            raise HTTPException(status_code=400, detail="cliente_id requerido")
        query = """
            SELECT c.id_conversacion, c.id_cliente, c.tipo, c.titulo, c.region,
                   c.id_punto_interes, c.creado_por, c.fecha_creacion,
                   (SELECT COUNT(*) FROM CHAT_PARTICIPANTES WHERE id_conversacion = c.id_conversacion) AS cnt,
                   (SELECT TOP 1 mensaje FROM CHAT_MENSAJES_CLIENTE
                       WHERE id_conversacion = c.id_conversacion ORDER BY fecha_envio DESC) AS last_msg,
                   (SELECT TOP 1 fecha_envio FROM CHAT_MENSAJES_CLIENTE
                       WHERE id_conversacion = c.id_conversacion ORDER BY fecha_envio DESC) AS last_msg_date,
                   0 AS no_leidos
            FROM CHAT_CONVERSACIONES c
            WHERE c.id_cliente = :cid
            ORDER BY ISNULL(
                (SELECT TOP 1 fecha_envio FROM CHAT_MENSAJES_CLIENTE
                    WHERE id_conversacion = c.id_conversacion ORDER BY fecha_envio DESC),
                c.fecha_creacion
            ) DESC
        """
        rows = db.execute(text(query), {"cid": cliente_id}).fetchall()
    else:
        query = """
            SELECT c.id_conversacion, c.id_cliente, c.tipo, c.titulo, c.region,
                   c.id_punto_interes, c.creado_por, c.fecha_creacion,
                   (SELECT COUNT(*) FROM CHAT_PARTICIPANTES WHERE id_conversacion = c.id_conversacion) AS cnt,
                   (SELECT TOP 1 mensaje FROM CHAT_MENSAJES_CLIENTE
                       WHERE id_conversacion = c.id_conversacion ORDER BY fecha_envio DESC) AS last_msg,
                   (SELECT TOP 1 fecha_envio FROM CHAT_MENSAJES_CLIENTE
                       WHERE id_conversacion = c.id_conversacion ORDER BY fecha_envio DESC) AS last_msg_date,
                   (SELECT COUNT(*) FROM CHAT_MENSAJES_CLIENTE m
                       WHERE m.id_conversacion = c.id_conversacion
                         AND m.id_usuario <> :uid
                         AND ISNULL(m.visto, 0) = 0) AS no_leidos
            FROM CHAT_CONVERSACIONES c
            JOIN CHAT_PARTICIPANTES p ON p.id_conversacion = c.id_conversacion
            WHERE p.id_usuario = :uid
            ORDER BY ISNULL(
                (SELECT TOP 1 fecha_envio FROM CHAT_MENSAJES_CLIENTE
                    WHERE id_conversacion = c.id_conversacion ORDER BY fecha_envio DESC),
                c.fecha_creacion
            ) DESC
        """
        rows = db.execute(text(query), {"uid": current_user.id}).fetchall()

    return [
        ConversacionResponse(
            id=r[0], cliente_id=r[1], tipo=r[2], titulo=r[3], region=r[4],
            punto_interes_id=r[5], creado_por=r[6], fecha_creacion=r[7],
            participantes_count=r[8], ultimo_mensaje=r[9], ultimo_mensaje_fecha=r[10],
            no_leidos=int(r[11] or 0),
        )
        for r in rows
    ]


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

    cnt = db.execute(text("""
        SELECT COUNT(*) FROM CHAT_PARTICIPANTES WHERE id_conversacion = :c
    """), {"c": conv_id}).scalar()

    return ConversacionResponse(
        id=conv.id, cliente_id=conv.cliente_id, tipo=conv.tipo, titulo=conv.titulo,
        region=conv.region, punto_interes_id=conv.punto_interes_id, visita_id=conv.visita_id,
        creado_por=conv.creado_por, fecha_creacion=conv.fecha_creacion,
        participantes_count=int(cnt or 0),
    )


@router.get("/conversations/{conv_id}/messages", response_model=List[ChatMensajeResponse])
async def get_conversation_messages(
    conv_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    conv = db.query(ChatConversacion).filter(ChatConversacion.id == conv_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    if not _can_access_conversation(db, conv, current_user):
        raise HTTPException(status_code=403, detail="No tienes acceso")

    # Marcar como leídos los mensajes ajenos (badge de no-leídos del inbox)
    db.execute(text("""
        UPDATE CHAT_MENSAJES_CLIENTE
        SET visto = 1
        WHERE id_conversacion = :c AND id_usuario <> :u AND ISNULL(visto, 0) = 0
    """), {"c": conv_id, "u": current_user.id})
    db.commit()

    # Recibos de lectura por mensaje (tick doble) + avisar por websocket
    leidos_ids = _mark_leidos(db, current_user, conv_id=conv_id)
    if leidos_ids:
        try:
            await manager.broadcast_to_room(f"chat_conv_{conv_id}", {
                "tipo": "lectura",
                "conversacion_id": conv_id,
                "id_usuario": current_user.id,
                "username": current_user.username,
                "mensajes_ids": leidos_ids,
                "fecha_lectura": str(datetime.now()),
            })
        except Exception:
            pass

    mensajes = db.query(ChatMensaje).filter(
        ChatMensaje.conversacion_id == conv_id
    ).order_by(ChatMensaje.created_at).all()
    return _attach_leido_por(db, mensajes)


@router.post("/conversations/{conv_id}/mark-read")
async def mark_conversation_read(
    conv_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Marca como leídos (recibo por mensaje) los mensajes ajenos pendientes
    de esta conversación. `get_conversation_messages` ya hace esto al abrir
    el chat — este endpoint existe para que el frontend pueda marcarlo leído
    explícitamente sin recargar el historial completo."""
    conv = db.query(ChatConversacion).filter(ChatConversacion.id == conv_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    if not _can_access_conversation(db, conv, current_user):
        raise HTTPException(status_code=403, detail="No tienes acceso")

    leidos_ids = _mark_leidos(db, current_user, conv_id=conv_id)
    if leidos_ids:
        try:
            await manager.broadcast_to_room(f"chat_conv_{conv_id}", {
                "tipo": "lectura",
                "conversacion_id": conv_id,
                "id_usuario": current_user.id,
                "username": current_user.username,
                "mensajes_ids": leidos_ids,
                "fecha_lectura": str(datetime.now()),
            })
        except Exception:
            pass
    return {"marcados": len(leidos_ids)}


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

    # Broadcast WebSocket
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
    """Inbox unificado: chats por visita + conversaciones nuevas.

    Coordinador exclusivo: requiere cliente_id (ve todo del cliente).
    Cliente normal: usa su id_perfil; ve sus visitas + las conversaciones donde participa.
    Staff: ve solo conversaciones donde participa.
    """
    cid: Optional[int] = None
    if current_user.is_coordinador_exclusivo:
        if not cliente_id:
            raise HTTPException(status_code=400, detail="cliente_id requerido")
        cid = int(cliente_id)
    elif current_user.is_client:
        cid = current_user.id_perfil

    inbox: list[InboxItem] = []

    # ── Chats por visita (modelo viejo) ──────────────────────────────────
    if cid is not None:
        visit_query = """
            SELECT cm.id_visita,
                   MAX(cm.fecha_envio) AS last_date,
                   (SELECT TOP 1 mensaje FROM CHAT_MENSAJES_CLIENTE
                      WHERE id_visita = cm.id_visita AND id_conversacion IS NULL
                      ORDER BY fecha_envio DESC) AS last_msg,
                   p.punto_de_interes AS punto_nombre,
                   p.identificador AS punto_id,
                   v.fecha_visita,
                   (SELECT COUNT(*) FROM CHAT_MENSAJES_CLIENTE m
                      WHERE m.id_visita = cm.id_visita AND m.id_conversacion IS NULL
                        AND m.id_usuario <> :uid AND ISNULL(m.visto, 0) = 0) AS no_leidos
            FROM CHAT_MENSAJES_CLIENTE cm
            JOIN VISITAS_MERCADERISTA v ON cm.id_visita = v.id_visita
            LEFT JOIN PUNTOS_INTERES1 p ON v.identificador_punto_interes = p.identificador
            WHERE cm.id_cliente = :cid AND cm.id_conversacion IS NULL
            GROUP BY cm.id_visita, p.punto_de_interes, p.identificador, v.fecha_visita
            ORDER BY last_date DESC
        """
        rows = db.execute(text(visit_query), {"cid": cid, "uid": current_user.id}).fetchall()
        for r in rows:
            inbox.append(InboxItem(
                kind="visit",
                visita_id=r[0],
                punto_nombre=r[3] or "Punto Desconocido",
                punto_id=r[4],
                fecha_visita=str(r[5]) if r[5] else None,
                last_message=r[2],
                last_message_date=str(r[1]) if r[1] else None,
                unread_count=int(r[6] or 0),
            ))

    # ── Conversaciones ────────────────────────────────────────────────────
    if current_user.is_coordinador_exclusivo:
        conv_rows = db.execute(text("""
            SELECT c.id_conversacion, c.tipo, c.titulo, c.id_visita,
                   (SELECT TOP 1 mensaje FROM CHAT_MENSAJES_CLIENTE
                      WHERE id_conversacion = c.id_conversacion ORDER BY fecha_envio DESC) AS last_msg,
                   (SELECT TOP 1 fecha_envio FROM CHAT_MENSAJES_CLIENTE
                      WHERE id_conversacion = c.id_conversacion ORDER BY fecha_envio DESC) AS last_date,
                   0 AS no_leidos
            FROM CHAT_CONVERSACIONES c
            WHERE c.id_cliente = :cid
            ORDER BY ISNULL(
                (SELECT TOP 1 fecha_envio FROM CHAT_MENSAJES_CLIENTE
                    WHERE id_conversacion = c.id_conversacion ORDER BY fecha_envio DESC),
                c.fecha_creacion
            ) DESC
        """), {"cid": cid}).fetchall()
    else:
        conv_rows = db.execute(text("""
            SELECT c.id_conversacion, c.tipo, c.titulo, c.id_visita,
                   (SELECT TOP 1 mensaje FROM CHAT_MENSAJES_CLIENTE
                      WHERE id_conversacion = c.id_conversacion ORDER BY fecha_envio DESC) AS last_msg,
                   (SELECT TOP 1 fecha_envio FROM CHAT_MENSAJES_CLIENTE
                      WHERE id_conversacion = c.id_conversacion ORDER BY fecha_envio DESC) AS last_date,
                   (SELECT COUNT(*) FROM CHAT_MENSAJES_CLIENTE m
                      WHERE m.id_conversacion = c.id_conversacion
                        AND m.id_usuario <> :uid AND ISNULL(m.visto, 0) = 0) AS no_leidos
            FROM CHAT_CONVERSACIONES c
            JOIN CHAT_PARTICIPANTES p ON p.id_conversacion = c.id_conversacion
            WHERE p.id_usuario = :uid
            ORDER BY ISNULL(
                (SELECT TOP 1 fecha_envio FROM CHAT_MENSAJES_CLIENTE
                    WHERE id_conversacion = c.id_conversacion ORDER BY fecha_envio DESC),
                c.fecha_creacion
            ) DESC
        """), {"uid": current_user.id}).fetchall()

    for r in conv_rows:
        inbox.append(InboxItem(
            kind="conversation",
            conversacion_id=r[0],
            tipo=r[1],
            titulo=r[2] or "(Sin título)",
            visita_id=r[3],
            last_message=r[4],
            last_message_date=str(r[5]) if r[5] else None,
            unread_count=int(r[6] or 0),
        ))

    # Orden global por último mensaje (los None van al final)
    def _sort_key(item: InboxItem):
        return item.last_message_date or "0000-00-00"
    inbox.sort(key=_sort_key, reverse=True)
    return inbox


# ════════════════════════════════════════════════════════════════════════════
# CHAT POR VISITA — endpoints originales (compatibilidad)
# ════════════════════════════════════════════════════════════════════════════
@router.get("/search-visits")
def search_chat_visits(
    q: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    cliente_id = current_user.id_perfil if current_user.is_client else None

    query_str = """
        SELECT TOP 50
            v.id_visita,
            p.punto_de_interes as punto_nombre,
            p.identificador as punto_id,
            p.jerarquia_nivel_2 as cadena,
            p.jerarquia_nivel_2_2 as region,
            v.fecha_visita,
            m.nombre as mercaderista_nombre
        FROM VISITAS_MERCADERISTA v
        LEFT JOIN PUNTOS_INTERES1 p ON v.identificador_punto_interes = p.identificador
        LEFT JOIN MERCADERISTAS m ON v.id_mercaderista = m.id_mercaderista
        WHERE 1=1
    """
    params = {}
    if cliente_id:
        query_str += " AND v.id_cliente = :cliente_id"
        params["cliente_id"] = cliente_id

    if q:
        query_str += """ AND (
            CAST(v.id_visita AS VARCHAR) LIKE :q OR
            p.punto_de_interes LIKE :q OR
            p.jerarquia_nivel_2 LIKE :q OR
            p.jerarquia_nivel_2_2 LIKE :q OR
            m.nombre LIKE :q
        )"""
        params["q"] = f"%{q}%"

    query_str += " ORDER BY v.fecha_visita DESC"
    rows = db.execute(text(query_str), params).fetchall()

    results = []
    for row in rows:
        results.append({
            "visita_id": row.id_visita,
            "punto_nombre": row.punto_nombre or "Punto Desconocido",
            "punto_id": row.punto_id,
            "cadena": row.cadena,
            "region": row.region,
            "mercaderista_nombre": row.mercaderista_nombre,
            "fecha_visita": str(row.fecha_visita) if row.fecha_visita else None,
            "last_message": "Nueva Conversación",
            "last_message_date": str(row.fecha_visita) if row.fecha_visita else None,
            "unread_count": 0
        })
    return results


@router.get("/visit/{visita_id}/messages", response_model=List[ChatMensajeResponse])
async def get_messages_by_visit(
    visita_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    mensajes = db.query(ChatMensaje).filter(
        ChatMensaje.visita_id == visita_id, ChatMensaje.conversacion_id.is_(None)
    ).order_by(ChatMensaje.created_at).all()

    for msg in mensajes:
        if msg.sender_nombre and msg.sender_nombre.isdigit():
            from app.models.mercaderista import Mercaderista
            merc = db.query(Mercaderista).filter(Mercaderista.cedula == msg.sender_nombre).first()
            if merc and merc.nombre:
                msg.sender_nombre = merc.nombre

    # Marcar como leídos los mensajes ajenos (badge de no-leídos del inbox
    # de chats de visita — antes este endpoint no lo hacía, a diferencia de
    # get_conversation_messages, dejando el contador de no-leídos "pegado").
    db.execute(text("""
        UPDATE CHAT_MENSAJES_CLIENTE
        SET visto = 1
        WHERE id_visita = :v AND id_conversacion IS NULL
          AND id_usuario <> :u AND ISNULL(visto, 0) = 0
    """), {"v": visita_id, "u": current_user.id})
    db.commit()

    # Recibos de lectura por mensaje (tick doble) + avisar por websocket
    leidos_ids = _mark_leidos(db, current_user, visita_id=visita_id)
    if leidos_ids:
        try:
            await manager.broadcast_to_room(f"chat_{visita_id}", {
                "tipo": "lectura",
                "visita_id": visita_id,
                "id_usuario": current_user.id,
                "username": current_user.username,
                "mensajes_ids": leidos_ids,
                "fecha_lectura": str(datetime.now()),
            })
        except Exception:
            pass

    return _attach_leido_por(db, mensajes)


@router.post("/visit/{visita_id}/mark-read")
async def mark_visit_read(
    visita_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Equivalente a mark_conversation_read pero para el chat de visita
    legacy (id_visita, sin id_conversacion)."""
    leidos_ids = _mark_leidos(db, current_user, visita_id=visita_id)
    if leidos_ids:
        try:
            await manager.broadcast_to_room(f"chat_{visita_id}", {
                "tipo": "lectura",
                "visita_id": visita_id,
                "id_usuario": current_user.id,
                "username": current_user.username,
                "mensajes_ids": leidos_ids,
                "fecha_lectura": str(datetime.now()),
            })
        except Exception:
            pass
    return {"marcados": len(leidos_ids)}


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
    from app.services.realtime import notify_event
    notify_event("chat.message", {"visita_id": mensaje.visita_id, "id": mensaje.id})
    return mensaje


# ════════════════════════════════════════════════════════════════════════════
# WEBSOCKETS
# ════════════════════════════════════════════════════════════════════════════
@router.websocket("/ws/{room}")
async def websocket_chat(websocket: WebSocket, room: str):
    """WebSocket genérico. La 'room' puede ser:
       - '<visita_id>' (chat por visita)
       - 'conv_<id_conversacion>' (chat de conversación nueva)
    """
    await manager.connect(websocket, f"chat_{room}")
    try:
        while True:
            data = await websocket.receive_json()
            db = SessionLocal()
            try:
                conversacion_id = data.get("conversacion_id")
                mensaje = ChatMensaje(
                    visita_id=data.get("visita_id"),
                    cliente_id=data.get("cliente_id"),
                    conversacion_id=conversacion_id,
                    sender_type=data.get("sender_type", "usuario"),
                    sender_id=data.get("sender_id"),
                    sender_nombre=data.get("sender_nombre"),
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
                    "leido_por": [],
                })
            finally:
                db.close()
    except WebSocketDisconnect:
        manager.disconnect(websocket, f"chat_{room}")
