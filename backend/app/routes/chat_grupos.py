"""
API de los GRUPOS DE CHAT por cliente (equipo operativo / equipo + cliente)
y su sub-hilo por visita — mirror de AppWeb v1 (Astroweb:
app/routes/chat_grupos.py + socket_chat_grupo.py + socket_chat_grupo_visita.py)
sobre las MISMAS tablas (CHAT_GRUPOS, CHAT_GRUPO_MENSAJES,
CHAT_MENSAJES_GRUPO_VISITA, + lecturas) que ya usan v1 y la APK del
mercaderista (epran_backend) — así los tres clientes ven el mismo chat.

Envío de mensajes: REST simple (INSERT + broadcast), no se replica el
protocolo de comandos Socket.IO de v1. Salas del broadcast con el mismo
naming que v1 (`grupo_{id}`, `grupo_visita_{cliente}_{tipo}_{visita}`) por
si en el futuro se quiere puentear de verdad con la APK/v1 — no es parte de
este trabajo, pero no cuesta nada mantener el mismo esquema de nombres.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from datetime import datetime

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import Usuario
from app.schemas.chat_grupos import (
    GrupoResponse, MiembroGrupoResponse, MensajeGrupoResponse,
    EnviarMensajeGrupoRequest, VisitaConChatResponse, MensajeGrupoVisitaResponse,
    InfoGrupoClienteResponse, LectorGrupoInfo, VisitaThreadRequest, VisitaThreadResponse,
)
from app.services.chat_grupos_membresia import (
    get_grupos_de_usuario, get_miembros_grupo, usuario_es_miembro,
    asegurar_grupos_cliente, TIPOS_VALIDOS,
)
from app.services.visibility import client_route_ids
from app.websockets.manager import manager

router = APIRouter(prefix="/api/chat/grupos", tags=["Chat Grupos"])


def _validar_tipo(tipo_grupo: str) -> None:
    if tipo_grupo not in TIPOS_VALIDOS:
        raise HTTPException(status_code=400, detail=f"tipo_grupo inválido: {tipo_grupo}")


def _foto_url(blob_path: Optional[str]) -> Optional[str]:
    """Devuelve la URL del proxy interno en lugar de una SAS URL directa.
    El endpoint /api/media/foto hace el fetch al blob storage server-side,
    eliminando los problemas de CSP/ngsw-worker en el browser."""
    if not blob_path:
        return None
    import urllib.parse
    return f"/api/media/foto?path={urllib.parse.quote(blob_path, safe='')}"



def _grupo_info(db: Session, id_grupo: int):
    return db.execute(text("""
        SELECT id_grupo, id_cliente, tipo_grupo, nombre, activa
        FROM CHAT_GRUPOS WHERE id_grupo = :id
    """), {"id": id_grupo}).fetchone()


def _autorizado_grupo(db: Session, current_user: Usuario, id_grupo: int) -> bool:
    return any(g["id_grupo"] == id_grupo for g in get_grupos_de_usuario(db, current_user.id))


def _rutas_permitidas_cliente(db: Session, current_user: Usuario) -> Optional[list]:
    """None = sin restricción (ve todas las rutas de su cliente). Lista =
    solo esas rutas. Mismo criterio que client_photos.py: exclusivo del rol
    'client' puro (id_rol=1) — coordinadores/admin ya son miembros de TODOS
    los grupos vía ROLES_COORDINADOR y no se restringen acá."""
    if current_user.rol != "client":
        return None
    return client_route_ids(db, current_user)


def _visita_permitida_para_cliente(db: Session, current_user: Usuario, id_cliente: int, id_visita: int) -> bool:
    """Para un cliente con CLIENTES_RUTAS restringido: ¿esta visita cae en
    una de sus rutas asignadas? Mismo patrón EXISTS que
    client_photos.py::get_client_visits (id_punto_interes + id_cliente).
    Coordinadores/admin y clientes sin restricción (None) siempre pasan."""
    rutas = _rutas_permitidas_cliente(db, current_user)
    if rutas is None:
        return True
    ids_csv = ",".join(str(int(i)) for i in rutas) if rutas else "-1"
    row = db.execute(text(f"""
        SELECT 1 FROM VISITAS_MERCADERISTA v
        WHERE v.id_visita = :vid AND v.id_cliente = :cid
          AND EXISTS (
              SELECT 1 FROM RUTA_PROGRAMACION rp_f
              WHERE rp_f.id_punto_interes = v.identificador_punto_interes
                AND rp_f.id_cliente = v.id_cliente
                AND rp_f.id_ruta IN ({ids_csv})
          )
    """), {"vid": id_visita, "cid": id_cliente}).fetchone()
    return row is not None


# ════════════════════════════════════════════════════════════════════════════
# MIS GRUPOS
# ════════════════════════════════════════════════════════════════════════════
@router.get("/mis-grupos", response_model=List[GrupoResponse])
def mis_grupos(db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    """Grupos a los que pertenece el usuario, con conteo de no-leídos y preview."""
    grupos = get_grupos_de_usuario(db, current_user.id)
    if not grupos:
        return []

    ids = [g["id_grupo"] for g in grupos]
    ph = ",".join(str(int(i)) for i in ids)

    unread_rows = db.execute(text(f"""
        SELECT m.id_grupo, COUNT(*)
        FROM CHAT_GRUPO_MENSAJES m
        LEFT JOIN CHAT_GRUPO_LECTURAS l
               ON l.id_grupo = m.id_grupo AND l.id_usuario = :uid
        WHERE m.id_grupo IN ({ph})
          AND m.id_usuario <> :uid
          AND m.id_mensaje > ISNULL(l.last_read_id_mensaje, 0)
        GROUP BY m.id_grupo
    """), {"uid": current_user.id}).fetchall()
    unread = {r[0]: int(r[1]) for r in unread_rows}

    last_rows = db.execute(text(f"""
        SELECT x.id_grupo, x.mensaje, x.fecha_envio
        FROM (
            SELECT m.id_grupo, m.mensaje, m.fecha_envio,
                   ROW_NUMBER() OVER (PARTITION BY m.id_grupo ORDER BY m.id_mensaje DESC) AS rn
            FROM CHAT_GRUPO_MENSAJES m
            WHERE m.id_grupo IN ({ph})
              AND NOT (
                  m.tipo_mensaje = 'sistema'
                  AND (
                      m.mensaje LIKE N'%Foto Rechazada%'
                      OR m.mensaje LIKE N'%Foto rechazada%'
                      OR m.mensaje LIKE N'%🚫%'
                  )
              )
        ) x
        WHERE x.rn = 1
    """)).fetchall()
    last = {r[0]: {"mensaje": r[1], "fecha": r[2]} for r in last_rows}

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

    cond = " AND m.id_mensaje < :before_id" if before_id else ""
    params = {"limit": limit, "id_grupo": id_grupo}
    if before_id:
        params["before_id"] = before_id

    rows = db.execute(text(f"""
        SELECT TOP (:limit) m.id_mensaje, m.id_grupo, m.id_usuario, m.username,
                             m.mensaje, m.tipo_mensaje, m.fecha_envio, m.foto_adjunta
        FROM CHAT_GRUPO_MENSAJES m
        WHERE m.id_grupo = :id_grupo{cond}
          AND NOT (
              m.tipo_mensaje = 'sistema'
              AND (
                  m.mensaje LIKE N'%Foto Rechazada%'
                  OR m.mensaje LIKE N'%Foto rechazada%'
                  OR m.mensaje LIKE N'%🚫%'
              )
          )
        ORDER BY m.id_mensaje DESC
    """), params).fetchall()

    mensajes = [{
        "id_mensaje": r[0], "id_grupo": r[1], "id_usuario": r[2], "username": r[3],
        "mensaje": r[4], "tipo_mensaje": r[5], "fecha_envio": r[6],
        "foto_adjunta": _foto_url(r[7]), "es_mio": r[2] == current_user.id, "leido_por": [],
    } for r in rows]

    if mensajes:
        ids = [m["id_mensaje"] for m in mensajes]
        ph = ",".join(str(int(i)) for i in ids)
        lect_rows = db.execute(text(f"""
            SELECT id_mensaje, id_usuario, username, fecha_lectura
            FROM CHAT_GRUPO_MENSAJE_LECTURAS
            WHERE id_mensaje IN ({ph})
            ORDER BY fecha_lectura ASC
        """)).fetchall()
        por_mensaje: dict[int, list] = {}
        for r in lect_rows:
            por_mensaje.setdefault(r[0], []).append(
                LectorGrupoInfo(id_usuario=r[1], username=r[2], fecha_lectura=r[3])
            )
        for m in mensajes:
            m["leido_por"] = por_mensaje.get(m["id_mensaje"], [])

    mensajes.reverse()  # cronológico ascendente para la UI
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
    row = db.execute(text("""
        INSERT INTO CHAT_GRUPO_MENSAJES (id_grupo, id_usuario, username, mensaje, tipo_mensaje, fecha_envio)
        OUTPUT INSERTED.id_mensaje
        VALUES (:id_grupo, :uid, :username, :mensaje, 'usuario', :fecha)
    """), {"id_grupo": id_grupo, "uid": current_user.id, "username": current_user.username,
           "mensaje": texto, "fecha": ahora}).fetchone()
    db.commit()
    id_mensaje = row[0]

    payload = {
        "id_mensaje": id_mensaje, "id_grupo": id_grupo, "id_usuario": current_user.id,
        "username": current_user.username, "mensaje": texto, "tipo_mensaje": "usuario",
        "fecha_envio": str(ahora), "foto_adjunta": None, "leido_por": [],
    }
    try:
        await manager.broadcast_to_room(f"grupo_{id_grupo}", payload)
    except Exception:
        pass

    return MensajeGrupoResponse(
        id_mensaje=id_mensaje, id_grupo=id_grupo, id_usuario=current_user.id,
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
    miembros = get_miembros_grupo(db, info[1], info[2])
    return [MiembroGrupoResponse(**m) for m in miembros]


@router.post("/{id_grupo}/marcar-leido")
async def marcar_leido_grupo(id_grupo: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    """Marca el grupo como leído hasta su último mensaje (puntero, badge de
    no-leídos) y registra el recibo de lectura por mensaje (tick doble)."""
    if not _autorizado_grupo(db, current_user, id_grupo):
        raise HTTPException(status_code=403, detail="No autorizado")

    last = db.execute(text("""
        SELECT ISNULL(MAX(id_mensaje), 0) FROM CHAT_GRUPO_MENSAJES WHERE id_grupo = :id
    """), {"id": id_grupo}).scalar()
    last_id = int(last or 0)

    db.execute(text("""
        MERGE CHAT_GRUPO_LECTURAS AS t
        USING (SELECT :id_grupo AS id_grupo, :uid AS id_usuario) AS s
           ON t.id_grupo = s.id_grupo AND t.id_usuario = s.id_usuario
        WHEN MATCHED THEN
            UPDATE SET last_read_id_mensaje = :last_id, fecha_actualizacion = GETDATE()
        WHEN NOT MATCHED THEN
            INSERT (id_grupo, id_usuario, last_read_id_mensaje, fecha_actualizacion)
            VALUES (:id_grupo, :uid, :last_id, GETDATE());
    """), {"id_grupo": id_grupo, "uid": current_user.id, "last_id": last_id})

    nuevos = db.execute(text("""
        INSERT INTO CHAT_GRUPO_MENSAJE_LECTURAS (id_mensaje, id_usuario, username, fecha_lectura)
        OUTPUT INSERTED.id_mensaje, INSERTED.fecha_lectura
        SELECT m.id_mensaje, :uid, :username, GETDATE()
        FROM CHAT_GRUPO_MENSAJES m
        WHERE m.id_grupo = :id_grupo AND m.id_usuario <> :uid AND m.id_usuario IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM CHAT_GRUPO_MENSAJE_LECTURAS l
              WHERE l.id_mensaje = m.id_mensaje AND l.id_usuario = :uid
          )
    """), {"id_grupo": id_grupo, "uid": current_user.id, "username": current_user.username}).fetchall()
    db.commit()

    if nuevos:
        try:
            await manager.broadcast_to_room(f"grupo_{id_grupo}", {
                "tipo": "lectura", "id_grupo": id_grupo, "id_usuario": current_user.id,
                "username": current_user.username,
                "mensajes_ids": [int(r[0]) for r in nuevos],
                "fecha_lectura": str(nuevos[0][1]) if nuevos[0][1] else None,
            })
        except Exception:
            pass

    return {"last_read_id_mensaje": last_id, "marcados": len(nuevos)}


# ════════════════════════════════════════════════════════════════════════════
# SUB-HILO DE CHAT POR VISITA
# ════════════════════════════════════════════════════════════════════════════
@router.get("/visitas-chat/{id_cliente}/{tipo_grupo}", response_model=List[VisitaConChatResponse])
def visitas_con_chat(id_cliente: int, tipo_grupo: str, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    """Visitas de este cliente que YA tienen un sub-hilo de chat iniciado."""
    _validar_tipo(tipo_grupo)
    if not usuario_es_miembro(db, current_user.id, id_cliente, tipo_grupo):
        raise HTTPException(status_code=403, detail="No autorizado")

    rutas = _rutas_permitidas_cliente(db, current_user)
    ruta_filter_sql = ""
    if rutas is not None:
        ids_csv = ",".join(str(int(i)) for i in rutas) if rutas else "-1"
        ruta_filter_sql = f"""
          AND EXISTS (
              SELECT 1 FROM RUTA_PROGRAMACION rp_f
              WHERE rp_f.id_punto_interes = v.identificador_punto_interes
                AND rp_f.id_cliente = v.id_cliente
                AND rp_f.id_ruta IN ({ids_csv})
          )
        """

    rows = db.execute(text(f"""
        SELECT v.id_visita, v.fecha_visita, m.nombre AS mercaderista, p.punto_de_interes,
               v.estado, x.ultimo_mensaje, x.fecha_ultimo
        FROM (
            SELECT DISTINCT id_visita FROM CHAT_MENSAJES_GRUPO_VISITA
            WHERE id_cliente = :cid AND tipo_grupo = :tipo
        ) gv
        JOIN VISITAS_MERCADERISTA v ON v.id_visita = gv.id_visita
        LEFT JOIN MERCADERISTAS m ON m.id_mercaderista = v.id_mercaderista
        LEFT JOIN PUNTOS_INTERES1 p ON p.identificador = v.identificador_punto_interes
        CROSS APPLY (
            SELECT TOP 1 mensaje AS ultimo_mensaje, fecha_envio AS fecha_ultimo
            FROM CHAT_MENSAJES_GRUPO_VISITA
            WHERE id_visita = v.id_visita AND id_cliente = :cid AND tipo_grupo = :tipo
            ORDER BY fecha_envio DESC
        ) x
        WHERE 1=1 {ruta_filter_sql}
        ORDER BY x.fecha_ultimo DESC
    """), {"cid": id_cliente, "tipo": tipo_grupo}).fetchall()

    return [
        VisitaConChatResponse(
            id_visita=r[0], fecha_visita=str(r[1]) if r[1] else None,
            mercaderista=r[2], punto=r[3], estado=r[4], ultimo_mensaje=r[5], fecha_ultimo=r[6],
        )
        for r in rows
    ]


@router.get("/visita-mensajes/{id_cliente}/{tipo_grupo}/{id_visita}", response_model=List[MensajeGrupoVisitaResponse])
def mensajes_grupo_visita(id_cliente: int, tipo_grupo: str, id_visita: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    _validar_tipo(tipo_grupo)
    if not usuario_es_miembro(db, current_user.id, id_cliente, tipo_grupo):
        raise HTTPException(status_code=403, detail="No autorizado")
    if not _visita_permitida_para_cliente(db, current_user, id_cliente, id_visita):
        raise HTTPException(status_code=403, detail="No autorizado para esta visita")

    rows = db.execute(text("""
        SELECT id_mensaje, id_usuario, username, mensaje, tipo_mensaje, fecha_envio, foto_adjunta
        FROM CHAT_MENSAJES_GRUPO_VISITA
        WHERE id_cliente = :cid AND tipo_grupo = :tipo AND id_visita = :vid
        ORDER BY fecha_envio ASC
    """), {"cid": id_cliente, "tipo": tipo_grupo, "vid": id_visita}).fetchall()

    mensajes = [{
        "id_mensaje": r[0], "id_cliente": id_cliente, "tipo_grupo": tipo_grupo, "id_visita": id_visita,
        "id_usuario": r[1], "username": r[2], "mensaje": r[3], "tipo_mensaje": r[4],
        "fecha_envio": r[5], "foto_adjunta": _foto_url(r[6]),
        "es_mio": r[1] == current_user.id, "leido_por": [],
    } for r in rows]

    if mensajes:
        ids = [m["id_mensaje"] for m in mensajes]
        ph = ",".join(str(int(i)) for i in ids)
        lect_rows = db.execute(text(f"""
            SELECT id_mensaje, id_usuario, username, fecha_lectura
            FROM CHAT_GRUPO_VISITA_LECTURAS
            WHERE id_mensaje IN ({ph})
            ORDER BY fecha_lectura ASC
        """)).fetchall()
        por_mensaje: dict[int, list] = {}
        for r in lect_rows:
            por_mensaje.setdefault(r[0], []).append(
                LectorGrupoInfo(id_usuario=r[1], username=r[2], fecha_lectura=r[3])
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
    row = db.execute(text("""
        INSERT INTO CHAT_MENSAJES_GRUPO_VISITA
            (id_cliente, tipo_grupo, id_visita, id_usuario, username, mensaje, tipo_mensaje, fecha_envio)
        OUTPUT INSERTED.id_mensaje
        VALUES (:cid, :tipo, :vid, :uid, :username, :mensaje, 'usuario', :fecha)
    """), {"cid": id_cliente, "tipo": tipo_grupo, "vid": id_visita, "uid": current_user.id,
           "username": current_user.username, "mensaje": texto, "fecha": ahora}).fetchone()
    db.commit()
    id_mensaje = row[0]

    payload = {
        "id_mensaje": id_mensaje, "id_cliente": id_cliente, "tipo_grupo": tipo_grupo, "id_visita": id_visita,
        "id_usuario": current_user.id, "username": current_user.username, "mensaje": texto,
        "tipo_mensaje": "usuario", "fecha_envio": str(ahora), "foto_adjunta": None, "leido_por": [],
    }
    try:
        await manager.broadcast_to_room(f"grupo_visita_{id_cliente}_{tipo_grupo}_{id_visita}", payload)
    except Exception:
        pass

    return MensajeGrupoVisitaResponse(
        id_mensaje=id_mensaje, id_cliente=id_cliente, tipo_grupo=tipo_grupo, id_visita=id_visita,
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

    nuevos = db.execute(text("""
        INSERT INTO CHAT_GRUPO_VISITA_LECTURAS (id_mensaje, id_usuario, username, fecha_lectura)
        OUTPUT INSERTED.id_mensaje, INSERTED.fecha_lectura
        SELECT m.id_mensaje, :uid, :username, GETDATE()
        FROM CHAT_MENSAJES_GRUPO_VISITA m
        WHERE m.id_cliente = :cid AND m.tipo_grupo = :tipo AND m.id_visita = :vid
          AND m.id_usuario <> :uid AND m.id_usuario IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM CHAT_GRUPO_VISITA_LECTURAS l
              WHERE l.id_mensaje = m.id_mensaje AND l.id_usuario = :uid
          )
    """), {"cid": id_cliente, "tipo": tipo_grupo, "vid": id_visita,
           "uid": current_user.id, "username": current_user.username}).fetchall()
    db.commit()

    if nuevos:
        try:
            await manager.broadcast_to_room(f"grupo_visita_{id_cliente}_{tipo_grupo}_{id_visita}", {
                "tipo": "lectura", "id_cliente": id_cliente, "tipo_grupo": tipo_grupo, "id_visita": id_visita,
                "id_usuario": current_user.id, "username": current_user.username,
                "mensajes_ids": [int(r[0]) for r in nuevos],
                "fecha_lectura": str(nuevos[0][1]) if nuevos[0][1] else None,
            })
        except Exception:
            pass

    return {"marcados": len(nuevos)}


# ════════════════════════════════════════════════════════════════════════════
# INFO DE GRUPO POR CLIENTE (auto-provisiona) — usado por el botón de chat
# de equipo fuera del chat en sí (Centro de Mando / revisión de visitas).
# ════════════════════════════════════════════════════════════════════════════
@router.get("/info-cliente/{id_cliente}/{tipo_grupo}", response_model=InfoGrupoClienteResponse)
def info_grupo_cliente(id_cliente: int, tipo_grupo: str, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    _validar_tipo(tipo_grupo)
    if not usuario_es_miembro(db, current_user.id, id_cliente, tipo_grupo):
        raise HTTPException(status_code=403, detail="No autorizado")

    asegurar_grupos_cliente(db, id_cliente)  # idempotente: crea el grupo si falta

    row = db.execute(text("""
        SELECT id_grupo, nombre FROM CHAT_GRUPOS WHERE id_cliente = :cid AND tipo_grupo = :tipo AND activa = 1
    """), {"cid": id_cliente, "tipo": tipo_grupo}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")

    return InfoGrupoClienteResponse(id_grupo=row[0], id_cliente=id_cliente, tipo_grupo=tipo_grupo, nombre=row[1])


@router.post("/visita-thread", response_model=VisitaThreadResponse, status_code=201)
def get_or_create_visita_thread(
    body: VisitaThreadRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Punto de entrada del botón de chat de una visita en Centro de Mando /
    revision-visitas: resuelve el id_cliente de la visita y auto-provisiona
    su grupo — el llamador solo necesita saber visita_id + tipo_grupo, igual
    que el viejo POST /api/chat/visit-thread (ahora eliminado)."""
    _validar_tipo(body.tipo_grupo)

    row = db.execute(text("""
        SELECT v.id_cliente, p.punto_de_interes
        FROM VISITAS_MERCADERISTA v
        LEFT JOIN PUNTOS_INTERES1 p ON v.identificador_punto_interes = p.identificador
        WHERE v.id_visita = :vid
    """), {"vid": body.visita_id}).fetchone()
    if not row or not row[0]:
        raise HTTPException(status_code=404, detail="Visita no encontrada")
    id_cliente, punto_nombre = int(row[0]), row[1]

    if not usuario_es_miembro(db, current_user.id, id_cliente, body.tipo_grupo):
        raise HTTPException(status_code=403, detail="No autorizado")

    asegurar_grupos_cliente(db, id_cliente)
    grupo_row = db.execute(text("""
        SELECT id_grupo FROM CHAT_GRUPOS WHERE id_cliente = :cid AND tipo_grupo = :tipo AND activa = 1
    """), {"cid": id_cliente, "tipo": body.tipo_grupo}).fetchone()
    if not grupo_row:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")

    return VisitaThreadResponse(
        id_grupo=grupo_row[0], id_cliente=id_cliente, tipo_grupo=body.tipo_grupo,
        id_visita=body.visita_id, titulo=punto_nombre or f"Visita #{body.visita_id}",
    )


# ════════════════════════════════════════════════════════════════════════════
# WEBSOCKET — solo para recibir los broadcasts (mensaje nuevo / recibo de
# lectura) emitidos por los endpoints REST de arriba. No hay protocolo de
# comandos por este socket (a diferencia de app/routes/chat.py::websocket_chat):
# el envío es siempre por REST. `room` debe ser exactamente el mismo nombre
# usado en manager.broadcast_to_room(...): `grupo_{id_grupo}` o
# `grupo_visita_{id_cliente}_{tipo_grupo}_{id_visita}`.
# ════════════════════════════════════════════════════════════════════════════
@router.websocket("/ws/{room}")
async def websocket_chat_grupos(websocket: WebSocket, room: str):
    await manager.connect(websocket, room)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, room)
