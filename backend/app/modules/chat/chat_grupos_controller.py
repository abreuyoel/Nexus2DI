from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_, not_
from typing import List, Optional
from datetime import datetime

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.entities import Usuario
from app.modules.chat.entities import (
    ChatGrupo, ChatGrupoMensaje, ChatGrupoLectura, ChatGrupoMensajeLectura,
    ChatMensajeGrupoVisita, ChatGrupoVisitaLectura
)
from app.modules.visits.entities import Visita
from app.modules.merchandisers.entities import Mercaderista
from app.modules.routes.entities import PuntoInteres, RutaProgramacion

from app.modules.chat.dto import (
    GrupoResponse, MiembroGrupoResponse, MensajeGrupoResponse,
    EnviarMensajeGrupoRequest, VisitaConChatResponse, MensajeGrupoVisitaResponse,
    InfoGrupoClienteResponse, LectorGrupoInfo, VisitaThreadRequest, VisitaThreadResponse,
)
from app.services.chat_grupos_membresia import (
    get_grupos_de_usuario, get_miembros_grupo, usuario_es_miembro,
    asegurar_grupos_cliente, TIPOS_VALIDOS,
)
from app.shared.visibility import client_route_ids

from app.websockets.manager import manager

router = APIRouter(prefix="/api/chat/grupos", tags=["Chat Grupos"])


def _validar_tipo(tipo_grupo: str) -> None:
    if tipo_grupo not in TIPOS_VALIDOS:
        raise HTTPException(status_code=400, detail=f"tipo_grupo inválido: {tipo_grupo}")


def _foto_url(blob_path: Optional[str]) -> Optional[str]:
    if not blob_path:
        return None
    from app.shared.azure_service import azure_service

    return azure_service.get_proxy_url(blob_path)


def _grupo_info(db: Session, id_grupo: int) -> Optional[ChatGrupo]:
    return db.query(ChatGrupo).filter(ChatGrupo.id == id_grupo).first()


def _autorizado_grupo(db: Session, current_user: Usuario, id_grupo: int) -> bool:
    return any(g["id_grupo"] == id_grupo for g in get_grupos_de_usuario(db, current_user.id))


def _rutas_permitidas_cliente(db: Session, current_user: Usuario) -> Optional[list]:
    if current_user.rol != "client":
        return None
    return client_route_ids(db, current_user)


def _visita_permitida_para_cliente(db: Session, current_user: Usuario, id_cliente: int, id_visita: int) -> bool:
    rutas = _rutas_permitidas_cliente(db, current_user)
    if rutas is None:
        return True
    if not rutas:
        return False

    v = db.query(Visita).filter(Visita.id == id_visita, Visita.id_cliente == id_cliente).first()
    if not v or not v.punto_id:
        return False

    rp = db.query(RutaProgramacion.id).filter(
        RutaProgramacion.punto_id == v.punto_id,
        RutaProgramacion.id_cliente == v.id_cliente,
        RutaProgramacion.ruta_id.in_(rutas)
    ).first()
    return rp is not None


# ════════════════════════════════════════════════════════════════════════════
# MIS GRUPOS
# ════════════════════════════════════════════════════════════════════════════
@router.get("/mis-grupos", response_model=List[GrupoResponse])
def mis_grupos(db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    grupos = get_grupos_de_usuario(db, current_user.id)
    if not grupos:
        return []

    ids = [g["id_grupo"] for g in grupos]

    # No leídos
    unread_query = (
        db.query(ChatGrupoMensaje.grupo_id, func.count(ChatGrupoMensaje.id))
        .outerjoin(
            ChatGrupoLectura,
            and_(
                ChatGrupoLectura.grupo_id == ChatGrupoMensaje.grupo_id,
                ChatGrupoLectura.usuario_id == current_user.id
            )
        )
        .filter(
            ChatGrupoMensaje.grupo_id.in_(ids),
            ChatGrupoMensaje.sender_id != current_user.id,
            ChatGrupoMensaje.id > func.coalesce(ChatGrupoLectura.last_read_id_mensaje, 0)
        )
        .group_by(ChatGrupoMensaje.grupo_id)
        .all()
    )
    unread = {r[0]: int(r[1]) for r in unread_query}

    # Último mensaje por grupo
    last = {}
    for gid in ids:
        msg = (
            db.query(ChatGrupoMensaje)
            .filter(
                ChatGrupoMensaje.grupo_id == gid,
                not_(
                    and_(
                        ChatGrupoMensaje.tipo_mensaje == 'sistema',
                        or_(
                            ChatGrupoMensaje.mensaje.like('%Foto Rechazada%'),
                            ChatGrupoMensaje.mensaje.like('%Foto rechazada%'),
                            ChatGrupoMensaje.mensaje.like('%🚫%')
                        )
                    )
                )
            )
            .order_by(desc(ChatGrupoMensaje.id))
            .first()
        )
        if msg:
            last[gid] = {"mensaje": msg.mensaje, "fecha": msg.created_at}

    result = [
        GrupoResponse(
            id_grupo=g["id_grupo"], id_cliente=g["id_cliente"], tipo_grupo=g["tipo_grupo"],
            nombre=g["nombre"], no_leidos=unread.get(g["id_grupo"], 0),
            ultimo_mensaje=last.get(g["id_grupo"], {}).get("mensaje"),
            ultimo_mensaje_fecha=last.get(g["id_grupo"], {}).get("fecha"),
        )
        for g in grupos
    ]
    result.sort(key=lambda g: (-g.no_leidos, g.nombre or ""))
    return result


# ════════════════════════════════════════════════════════════════════════════
# CHAT GENERAL DEL GRUPO
# ════════════════════════════════════════════════════════════════════════════
@router.get("/{id_grupo}/mensajes", response_model=List[MensajeGrupoResponse])
def mensajes_grupo(
    id_grupo: int,
    limit: int = Query(50, le=200),
    before_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if not _autorizado_grupo(db, current_user, id_grupo):
        raise HTTPException(status_code=403, detail="No autorizado")

    query = db.query(ChatGrupoMensaje).filter(
        ChatGrupoMensaje.grupo_id == id_grupo,
        not_(
            and_(
                ChatGrupoMensaje.tipo_mensaje == 'sistema',
                or_(
                    ChatGrupoMensaje.mensaje.like('%Foto Rechazada%'),
                    ChatGrupoMensaje.mensaje.like('%Foto rechazada%'),
                    ChatGrupoMensaje.mensaje.like('%🚫%')
                )
            )
        )
    )

    if before_id:
        query = query.filter(ChatGrupoMensaje.id < before_id)

    rows = query.order_by(desc(ChatGrupoMensaje.id)).limit(limit).all()

    mensajes = [{
        "id_mensaje": r.id, "id_grupo": r.grupo_id, "id_usuario": r.sender_id, "username": r.sender_nombre,
        "mensaje": r.mensaje, "tipo_mensaje": r.tipo_mensaje, "fecha_envio": r.created_at,
        "foto_adjunta": _foto_url(r.foto_adjunta), "es_mio": r.sender_id == current_user.id, "leido_por": [],
    } for r in rows]

    if mensajes:
        ids = [m["id_mensaje"] for m in mensajes]
        lect_rows = (
            db.query(ChatGrupoMensajeLectura)
            .filter(ChatGrupoMensajeLectura.mensaje_id.in_(ids))
            .order_by(ChatGrupoMensajeLectura.fecha_lectura.asc())
            .all()
        )
        por_mensaje: dict[int, list] = {}
        for r in lect_rows:
            por_mensaje.setdefault(r.mensaje_id, []).append(
                LectorGrupoInfo(id_usuario=r.usuario_id, username=r.username, fecha_lectura=r.fecha_lectura)
            )
        for m in mensajes:
            m["leido_por"] = por_mensaje.get(m["id_mensaje"], [])

    mensajes.reverse()
    return mensajes


@router.post("/{id_grupo}/mensajes", response_model=MensajeGrupoResponse, status_code=201)
async def enviar_mensaje_grupo(
    id_grupo: int,
    data: EnviarMensajeGrupoRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if not _autorizado_grupo(db, current_user, id_grupo):
        raise HTTPException(status_code=403, detail="No autorizado")

    texto = (data.mensaje or "").strip()
    if not texto:
        raise HTTPException(status_code=400, detail="Mensaje vacío")

    ahora = datetime.now()
    nuevo_msg = ChatGrupoMensaje(
        grupo_id=id_grupo,
        sender_id=current_user.id,
        sender_nombre=current_user.username,
        mensaje=texto,
        tipo_mensaje="usuario",
        created_at=ahora
    )
    db.add(nuevo_msg)
    db.commit()
    db.refresh(nuevo_msg)

    payload = {
        "id_mensaje": nuevo_msg.id, "id_grupo": id_grupo, "id_usuario": current_user.id,
        "username": current_user.username, "mensaje": texto, "tipo_mensaje": "usuario",
        "fecha_envio": str(ahora), "foto_adjunta": None, "leido_por": [],
    }
    try:
        await manager.broadcast_to_room(f"grupo_{id_grupo}", payload)
    except Exception:
        pass

    return MensajeGrupoResponse(
        id_mensaje=nuevo_msg.id, id_grupo=id_grupo, id_usuario=current_user.id,
        username=current_user.username, mensaje=texto, tipo_mensaje="usuario",
        fecha_envio=ahora, foto_adjunta=None, es_mio=True, leido_por=[],
    )


@router.get("/{id_grupo}/miembros", response_model=List[MiembroGrupoResponse])
def miembros_grupo(id_grupo: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    if not _autorizado_grupo(db, current_user, id_grupo):
        raise HTTPException(status_code=403, detail="No autorizado")
    info = _grupo_info(db, id_grupo)
    if not info:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    miembros = get_miembros_grupo(db, info.cliente_id, info.tipo_grupo)
    return [MiembroGrupoResponse(**m) for m in miembros]


@router.post("/{id_grupo}/marcar-leido")
async def marcar_leido_grupo(id_grupo: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    if not _autorizado_grupo(db, current_user, id_grupo):
        raise HTTPException(status_code=403, detail="No autorizado")

    max_id = db.query(func.coalesce(func.max(ChatGrupoMensaje.id), 0)).filter(ChatGrupoMensaje.grupo_id == id_grupo).scalar() or 0

    lectura = db.query(ChatGrupoLectura).filter(
        ChatGrupoLectura.grupo_id == id_grupo,
        ChatGrupoLectura.usuario_id == current_user.id
    ).first()

    if lectura:
        lectura.last_read_id_mensaje = max_id
        lectura.fecha_actualizacion = datetime.now()
    else:
        db.add(ChatGrupoLectura(
            grupo_id=id_grupo,
            usuario_id=current_user.id,
            last_read_id_mensaje=max_id,
            fecha_actualizacion=datetime.now()
        ))

    # Lecturas por mensaje
    pendientes = db.query(ChatGrupoMensaje).filter(
        ChatGrupoMensaje.grupo_id == id_grupo,
        ChatGrupoMensaje.sender_id != current_user.id,
        ChatGrupoMensaje.sender_id.isnot(None),
        not_(
            db.query(ChatGrupoMensajeLectura.mensaje_id)
            .filter(
                ChatGrupoMensajeLectura.mensaje_id == ChatGrupoMensaje.id,
                ChatGrupoMensajeLectura.usuario_id == current_user.id
            ).exists()
        )
    ).all()

    nuevos_ids = []
    ahora = datetime.now()
    for m in pendientes:
        db.add(ChatGrupoMensajeLectura(
            mensaje_id=m.id,
            usuario_id=current_user.id,
            username=current_user.username,
            fecha_lectura=ahora
        ))
        nuevos_ids.append(m.id)

    db.commit()

    if nuevos_ids:
        try:
            await manager.broadcast_to_room(f"grupo_{id_grupo}", {
                "tipo": "lectura", "id_grupo": id_grupo, "id_usuario": current_user.id,
                "username": current_user.username,
                "mensajes_ids": nuevos_ids,
                "fecha_lectura": str(ahora),
            })
        except Exception:
            pass

    return {"last_read_id_mensaje": max_id, "marcados": len(nuevos_ids)}


# ════════════════════════════════════════════════════════════════════════════
# SUB-HILO DE CHAT POR VISITA
# ════════════════════════════════════════════════════════════════════════════
@router.get("/visitas-chat/{id_cliente}/{tipo_grupo}", response_model=List[VisitaConChatResponse])
def visitas_con_chat(id_cliente: int, tipo_grupo: str, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    _validar_tipo(tipo_grupo)
    if not usuario_es_miembro(db, current_user.id, id_cliente, tipo_grupo):
        raise HTTPException(status_code=403, detail="No autorizado")

    visitas_ids = (
        db.query(ChatMensajeGrupoVisita.visita_id)
        .distinct()
        .filter(
            ChatMensajeGrupoVisita.cliente_id == id_cliente,
            ChatMensajeGrupoVisita.tipo_grupo == tipo_grupo
        )
        .all()
    )
    v_ids = [v[0] for v in visitas_ids]
    if not v_ids:
        return []

    rutas = _rutas_permitidas_cliente(db, current_user)

    query = (
        db.query(
            Visita.id,
            Visita.fecha,
            Mercaderista.nombre.label("mercaderista"),
            PuntoInteres.nombre.label("punto"),
            Visita.estado
        )
        .outerjoin(Mercaderista, Mercaderista.id == Visita.mercaderista_id)
        .outerjoin(PuntoInteres, PuntoInteres.id == Visita.punto_id)
        .filter(Visita.id.in_(v_ids))
    )

    if rutas is not None:
        if not rutas:
            return []
        query = query.filter(
            db.query(RutaProgramacion.id).filter(
                RutaProgramacion.punto_id == Visita.punto_id,
                RutaProgramacion.id_cliente == Visita.id_cliente,
                RutaProgramacion.ruta_id.in_(rutas)
            ).exists()
        )

    rows = query.all()
    res = []
    for r in rows:
        last_msg = (
            db.query(ChatMensajeGrupoVisita)
            .filter(
                ChatMensajeGrupoVisita.visita_id == r.id,
                ChatMensajeGrupoVisita.cliente_id == id_cliente,
                ChatMensajeGrupoVisita.tipo_grupo == tipo_grupo
            )
            .order_by(desc(ChatMensajeGrupoVisita.created_at))
            .first()
        )
        res.append(VisitaConChatResponse(
            id_visita=r.id,
            fecha_visita=str(r.fecha) if r.fecha else None,
            mercaderista=r.mercaderista,
            punto=r.punto,
            estado=r.estado,
            ultimo_mensaje=last_msg.mensaje if last_msg else None,
            fecha_ultimo=last_msg.created_at if last_msg else None,
        ))

    res.sort(key=lambda x: x.fecha_ultimo or datetime.min, reverse=True)
    return res


@router.get("/visita-mensajes/{id_cliente}/{tipo_grupo}/{id_visita}", response_model=List[MensajeGrupoVisitaResponse])
def mensajes_grupo_visita(id_cliente: int, tipo_grupo: str, id_visita: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    _validar_tipo(tipo_grupo)
    if not usuario_es_miembro(db, current_user.id, id_cliente, tipo_grupo):
        raise HTTPException(status_code=403, detail="No autorizado")
    if not _visita_permitida_para_cliente(db, current_user, id_cliente, id_visita):
        raise HTTPException(status_code=403, detail="No autorizado para esta visita")

    rows = (
        db.query(ChatMensajeGrupoVisita)
        .filter(
            ChatMensajeGrupoVisita.cliente_id == id_cliente,
            ChatMensajeGrupoVisita.tipo_grupo == tipo_grupo,
            ChatMensajeGrupoVisita.visita_id == id_visita
        )
        .order_by(ChatMensajeGrupoVisita.created_at.asc())
        .all()
    )

    mensajes = [{
        "id_mensaje": r.id, "id_cliente": id_cliente, "tipo_grupo": tipo_grupo, "id_visita": id_visita,
        "id_usuario": r.sender_id, "username": r.sender_nombre, "mensaje": r.mensaje, "tipo_mensaje": r.tipo_mensaje,
        "fecha_envio": r.created_at, "foto_adjunta": _foto_url(r.foto_adjunta),
        "es_mio": r.sender_id == current_user.id, "leido_por": [],
    } for r in rows]

    if mensajes:
        ids = [m["id_mensaje"] for m in mensajes]
        lect_rows = (
            db.query(ChatGrupoVisitaLectura)
            .filter(ChatGrupoVisitaLectura.mensaje_id.in_(ids))
            .order_by(ChatGrupoVisitaLectura.fecha_lectura.asc())
            .all()
        )
        por_mensaje: dict[int, list] = {}
        for r in lect_rows:
            por_mensaje.setdefault(r.mensaje_id, []).append(
                LectorGrupoInfo(id_usuario=r.usuario_id, username=r.username, fecha_lectura=r.fecha_lectura)
            )
        for m in mensajes:
            m["leido_por"] = por_mensaje.get(m["id_mensaje"], [])

    return mensajes


@router.post("/visita-mensajes/{id_cliente}/{tipo_grupo}/{id_visita}", response_model=MensajeGrupoVisitaResponse, status_code=201)
async def enviar_mensaje_grupo_visita(
    id_cliente: int, tipo_grupo: str, id_visita: int,
    data: EnviarMensajeGrupoRequest,
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user),
):
    _validar_tipo(tipo_grupo)
    if not usuario_es_miembro(db, current_user.id, id_cliente, tipo_grupo):
        raise HTTPException(status_code=403, detail="No autorizado")
    if not _visita_permitida_para_cliente(db, current_user, id_cliente, id_visita):
        raise HTTPException(status_code=403, detail="No autorizado para esta visita")

    texto = (data.mensaje or "").strip()
    if not texto:
        raise HTTPException(status_code=400, detail="Mensaje vacío")

    ahora = datetime.now()
    nuevo_msg = ChatMensajeGrupoVisita(
        cliente_id=id_cliente,
        tipo_grupo=tipo_grupo,
        visita_id=id_visita,
        sender_id=current_user.id,
        sender_nombre=current_user.username,
        mensaje=texto,
        tipo_mensaje="usuario",
        created_at=ahora
    )
    db.add(nuevo_msg)
    db.commit()
    db.refresh(nuevo_msg)

    payload = {
        "id_mensaje": nuevo_msg.id, "id_cliente": id_cliente, "tipo_grupo": tipo_grupo, "id_visita": id_visita,
        "id_usuario": current_user.id, "username": current_user.username, "mensaje": texto,
        "tipo_mensaje": "usuario", "fecha_envio": str(ahora), "foto_adjunta": None, "leido_por": [],
    }
    try:
        await manager.broadcast_to_room(f"grupo_visita_{id_cliente}_{tipo_grupo}_{id_visita}", payload)
    except Exception:
        pass

    return MensajeGrupoVisitaResponse(
        id_mensaje=nuevo_msg.id, id_cliente=id_cliente, tipo_grupo=tipo_grupo, id_visita=id_visita,
        id_usuario=current_user.id, username=current_user.username, mensaje=texto,
        tipo_mensaje="usuario", fecha_envio=ahora, foto_adjunta=None, es_mio=True, leido_por=[],
    )


@router.post("/visita-marcar-leido/{id_cliente}/{tipo_grupo}/{id_visita}")
async def marcar_leido_grupo_visita(id_cliente: int, tipo_grupo: str, id_visita: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    _validar_tipo(tipo_grupo)
    if not usuario_es_miembro(db, current_user.id, id_cliente, tipo_grupo):
        raise HTTPException(status_code=403, detail="No autorizado")
    if not _visita_permitida_para_cliente(db, current_user, id_cliente, id_visita):
        raise HTTPException(status_code=403, detail="No autorizado para esta visita")

    pendientes = db.query(ChatMensajeGrupoVisita).filter(
        ChatMensajeGrupoVisita.cliente_id == id_cliente,
        ChatMensajeGrupoVisita.tipo_grupo == tipo_grupo,
        ChatMensajeGrupoVisita.visita_id == id_visita,
        ChatMensajeGrupoVisita.sender_id != current_user.id,
        ChatMensajeGrupoVisita.sender_id.isnot(None),
        not_(
            db.query(ChatGrupoVisitaLectura.mensaje_id)
            .filter(
                ChatGrupoVisitaLectura.mensaje_id == ChatMensajeGrupoVisita.id,
                ChatGrupoVisitaLectura.usuario_id == current_user.id
            ).exists()
        )
    ).all()

    nuevos_ids = []
    ahora = datetime.now()
    for m in pendientes:
        db.add(ChatGrupoVisitaLectura(
            mensaje_id=m.id,
            usuario_id=current_user.id,
            username=current_user.username,
            fecha_lectura=ahora
        ))
        nuevos_ids.append(m.id)

    db.commit()

    if nuevos_ids:
        try:
            await manager.broadcast_to_room(f"grupo_visita_{id_cliente}_{tipo_grupo}_{id_visita}", {
                "tipo": "lectura", "id_cliente": id_cliente, "tipo_grupo": tipo_grupo, "id_visita": id_visita,
                "id_usuario": current_user.id, "username": current_user.username,
                "mensajes_ids": nuevos_ids,
                "fecha_lectura": str(ahora),
            })
        except Exception:
            pass

    return {"marcados": len(nuevos_ids)}


@router.get("/info-cliente/{id_cliente}/{tipo_grupo}", response_model=InfoGrupoClienteResponse)
def info_grupo_cliente(id_cliente: int, tipo_grupo: str, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    _validar_tipo(tipo_grupo)
    if not usuario_es_miembro(db, current_user.id, id_cliente, tipo_grupo):
        raise HTTPException(status_code=403, detail="No autorizado")

    asegurar_grupos_cliente(db, id_cliente)

    row = db.query(ChatGrupo).filter(
        ChatGrupo.cliente_id == id_cliente,
        ChatGrupo.tipo_grupo == tipo_grupo,
        ChatGrupo.activa == True
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")

    return InfoGrupoClienteResponse(id_grupo=row.id, id_cliente=id_cliente, tipo_grupo=tipo_grupo, nombre=row.nombre)


@router.post("/visita-thread", response_model=VisitaThreadResponse, status_code=201)
def get_or_create_visita_thread(
    body: VisitaThreadRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _validar_tipo(body.tipo_grupo)

    v = db.query(Visita).filter(Visita.id == body.visita_id).first()
    if not v or not v.id_cliente:
        raise HTTPException(status_code=404, detail="Visita no encontrada")
    id_cliente = v.id_cliente
    punto_nombre = v.punto.nombre if v.punto else None

    if not usuario_es_miembro(db, current_user.id, id_cliente, body.tipo_grupo):
        raise HTTPException(status_code=403, detail="No autorizado")

    asegurar_grupos_cliente(db, id_cliente)
    grupo = db.query(ChatGrupo).filter(
        ChatGrupo.cliente_id == id_cliente,
        ChatGrupo.tipo_grupo == body.tipo_grupo,
        ChatGrupo.activa == True
    ).first()
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")

    return VisitaThreadResponse(
        id_grupo=grupo.id, id_cliente=id_cliente, tipo_grupo=body.tipo_grupo,
        id_visita=body.visita_id, titulo=punto_nombre or f"Visita #{body.visita_id}",
    )


@router.websocket("/ws/{room}")
async def websocket_chat_grupos(websocket: WebSocket, room: str):
    await manager.connect(websocket, room)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, room)
