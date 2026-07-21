from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text, bindparam
from typing import List, Optional
from datetime import date, timedelta
from app.db.session import get_db
from app.core.dependencies import get_current_user, require_analyst_or_admin
from app.models.user import Usuario
from app.models.visita import Visita
from app.models.foto import Foto, NotificacionRechazoFoto
from app.models.foto_razon import FotoRazonRechazo
from app.models.balance import Balance
from app.schemas.visita import VisitaCreate, VisitaUpdate, VisitaResponse, UpdateBalancesRequest, BalanceResponse
from app.schemas.foto import FotoResponse, ApprovePhotosRequest, RejectPhotoRequest, SavePhotoDecisionsRequest, RejectReason
from app.services.audit_service import log_action
from app.services.realtime import notify_event
from datetime import datetime

router = APIRouter(prefix="/api/visits", tags=["Visitas"])


@router.get("/", response_model=List[VisitaResponse])
def list_visits(
    ruta_id: Optional[int] = None,
    fecha: Optional[date] = None,
    estado: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    query = db.query(Visita)
    if ruta_id:
        query = query.filter(Visita.ruta_id == ruta_id)
    if fecha:
        query = query.filter(Visita.fecha == fecha)
    if estado:
        query = query.filter(Visita.estado == estado)
    return query.order_by(Visita.fecha.desc()).all()


@router.post("/", response_model=VisitaResponse, status_code=201)
def create_visit(
    data: VisitaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    visita = Visita(**data.model_dump())
    db.add(visita)
    db.commit()
    db.refresh(visita)
    return visita


@router.get("/pending", response_model=List[VisitaResponse])
def get_pending_visits(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_analyst_or_admin),
):
    today = date.today()
    return db.query(Visita).filter(
        Visita.fecha == today,
        Visita.estado.in_(["Pendiente", "En Progreso"]),
    ).options(joinedload(Visita.punto), joinedload(Visita.mercaderista)).all()


@router.get("/with-balances", response_model=List[VisitaResponse])
def get_visits_with_balances(
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
    cliente_id: Optional[int] = None,
    mercaderista_id: Optional[int] = None,
    punto_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_analyst_or_admin),
):
    query = db.query(Visita).join(Balance, Visita.id == Balance.visita_id).distinct()

    if current_user.is_analyst and current_user.id_perfil:
        # analistas_rutas -> RUTA_PROGRAMACION, no ANALISTAS_CLIENTE
        # (desactualizada) — mismo criterio que /review-list y centro_mando.
        managed_rows = db.execute(text("""
            SELECT DISTINCT rp.id_cliente
            FROM analistas_rutas ar
            JOIN RUTA_PROGRAMACION rp ON rp.id_ruta = ar.id_ruta
            WHERE ar.id_analista = :aid AND rp.activa = 1
        """), {"aid": current_user.id_perfil}).fetchall()
        managed_ids = [r[0] for r in managed_rows]
        query = query.filter(Balance.id_cliente.in_(managed_ids))

    if fecha_inicio:
        query = query.filter(Visita.fecha >= fecha_inicio)
    if fecha_fin:
        query = query.filter(Visita.fecha <= fecha_fin)
    if cliente_id:
        query = query.filter(Visita.id_cliente == cliente_id)
    if mercaderista_id:
        query = query.filter(Visita.mercaderista_id == mercaderista_id)
    if punto_id:
        query = query.filter(Visita.punto_id == punto_id)

    return query.options(
        joinedload(Visita.punto),
        joinedload(Visita.mercaderista),
        joinedload(Visita.cliente)
    ).order_by(Visita.fecha.desc()).all()


@router.get("/review-list")
def review_list(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    cliente_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Lista de visitas con conteo de fotos a revisar + desglose por tipo. Declarada
    ANTES de /{visit_id} para que la ruta estática no la capture el path param."""
    from app.services.visibility import coordinator_client_ids
    visible_ids = coordinator_client_ids(db, current_user) if current_user.is_client else None

    if not (desde and hasta):
        hoy = date.today()
        hasta = hoy.isoformat()
        desde = (hoy - timedelta(days=7)).isoformat()

    params = {"d": desde, "h": hasta}
    where = "WHERE CAST(v.fecha_visita AS DATE) BETWEEN :d AND :h"
    if cliente_id:
        where += " AND v.id_cliente = :cid"
        params["cid"] = cliente_id
    if visible_ids is not None:
        if not visible_ids:
            return []
        where += f" AND v.id_cliente IN ({','.join(str(int(i)) for i in visible_ids)})"
    analyst_join = ""
    if current_user.is_analyst and current_user.id_perfil:
        # analistas_rutas -> RUTA_PROGRAMACION es la fuente de verdad — antes
        # esto usaba ANALISTAS_CLIENTE (desactualizada) sola, sin cruce con
        # rutas: un analista con ruta asignada pero sin fila ahí veía 0
        # visitas para ese cliente pese a tener acceso real.
        analyst_join = """
            JOIN (
                SELECT DISTINCT rp.id_cliente
                FROM analistas_rutas ar
                JOIN RUTA_PROGRAMACION rp ON rp.id_ruta = ar.id_ruta
                WHERE ar.id_analista = :aid AND rp.activa = 1
            ) ac ON ac.id_cliente = v.id_cliente
        """
        params["aid"] = current_user.id_perfil

    q = text(f"""
        SELECT v.id_visita, c.cliente, c.id_cliente,
               p.punto_de_interes, p.identificador AS id_punto, ISNULL(p.ciudad,'') AS ciudad,
               ISNULL(rinfo.ruta,'Sin ruta') AS ruta, m.nombre AS mercaderista, v.fecha_visita,
               SUM(CASE WHEN f.id_tipo_foto NOT IN (5,6) AND f.id_foto IS NOT NULL THEN 1 ELSE 0 END) AS revisar,
               SUM(CASE WHEN f.id_tipo_foto NOT IN (5,6) AND f.Estado='Aprobada' THEN 1 ELSE 0 END) AS aprobadas,
               SUM(CASE WHEN f.id_tipo_foto NOT IN (5,6) AND f.Estado='Rechazada' THEN 1 ELSE 0 END) AS rechazadas,
               SUM(CASE WHEN f.id_tipo_foto IN (5,6) THEN 1 ELSE 0 END) AS activaciones,
               MAX(ISNULL(chat.n, 0)) AS chat_msgs,
               MAX(CASE WHEN v.revisada_por IS NOT NULL OR v.estado = 'Revisado' THEN 1 ELSE 0 END) AS revisada_flag,
               MAX(ISNULL(v.estado, 'Pendiente')) AS estado_visita
        FROM VISITAS_MERCADERISTA v
        JOIN CLIENTES c ON v.id_cliente = c.id_cliente
        JOIN PUNTOS_INTERES1 p ON v.identificador_punto_interes = p.identificador
        JOIN MERCADERISTAS m ON v.id_mercaderista = m.id_mercaderista
        {analyst_join}
        LEFT JOIN FOTOS_TOTALES f ON f.id_visita = v.id_visita
        LEFT JOIN (
            SELECT rp.id_punto_interes, MIN(rn.ruta) AS ruta
            FROM RUTA_PROGRAMACION rp JOIN RUTAS_NUEVAS rn ON rn.id_ruta = rp.id_ruta
            WHERE rp.activa = 1 GROUP BY rp.id_punto_interes
        ) rinfo ON rinfo.id_punto_interes = p.identificador
        LEFT JOIN (
            SELECT id_visita, COUNT(*) AS n FROM CHAT_MENSAJES_CLIENTE GROUP BY id_visita
        ) chat ON chat.id_visita = v.id_visita
        {where}
        GROUP BY v.id_visita, c.cliente, c.id_cliente, p.punto_de_interes, p.identificador,
                 p.ciudad, rinfo.ruta, m.nombre, v.fecha_visita
        HAVING SUM(CASE WHEN f.id_tipo_foto NOT IN (5,6) AND f.id_foto IS NOT NULL THEN 1 ELSE 0 END) > 0
        ORDER BY v.fecha_visita DESC
    """)
    rows = db.execute(q, params).fetchall()

    qb = text(f"""
        SELECT v.id_visita, f.id_tipo_foto,
               ISNULL(tf.tipo_foto, CONCAT('Tipo ', f.id_tipo_foto)) AS label,
               COUNT(*) AS total,
               SUM(CASE WHEN f.Estado='Aprobada' THEN 1 ELSE 0 END) AS aprobadas,
               SUM(CASE WHEN f.Estado='Rechazada' THEN 1 ELSE 0 END) AS rechazadas
        FROM VISITAS_MERCADERISTA v
        JOIN FOTOS_TOTALES f ON f.id_visita = v.id_visita
        LEFT JOIN TIPOS_FOTOS tf ON tf.id_tipo_foto = f.id_tipo_foto
        {analyst_join}
        {where}
        AND f.id_tipo_foto IS NOT NULL
        GROUP BY v.id_visita, f.id_tipo_foto, tf.tipo_foto
    """)
    tipos_map: dict = {}
    for r in db.execute(qb, params).fetchall():
        tid = int(r.id_tipo_foto)
        tipos_map.setdefault(r.id_visita, []).append({
            "id_tipo_foto": tid, "label": r.label,
            "total": int(r.total or 0), "aprobadas": int(r.aprobadas or 0),
            "rechazadas": int(r.rechazadas or 0), "revisable": tid not in (5, 6),
        })

    out = []
    for r in rows:
        rev = int(r.revisar or 0); apr = int(r.aprobadas or 0); rec = int(r.rechazadas or 0)
        out.append({
            "id_visita": r.id_visita, "cliente": r.cliente, "id_cliente": r.id_cliente,
            "punto_de_interes": r.punto_de_interes, "id_punto": r.id_punto, "ciudad": r.ciudad,
            "ruta": r.ruta, "mercaderista": r.mercaderista,
            "fecha": r.fecha_visita.isoformat() if r.fecha_visita else None,
            "fotos_revisar": rev, "aprobadas": apr, "rechazadas": rec,
            "sin_revisar": max(rev - apr - rec, 0), "activaciones": int(r.activaciones or 0),
            "revisada": bool(r.revisada_flag),
            "estado": "Revisado" if r.revisada_flag else (r.estado_visita or "Pendiente"),
            "completada": rev > 0 and (apr + rec) >= rev,
            "tiene_chat": int(r.chat_msgs or 0) > 0, "chat_msgs": int(r.chat_msgs or 0),
            "tipos": sorted(tipos_map.get(r.id_visita, []), key=lambda x: x["id_tipo_foto"]),
        })
    return out


async def _post_system_message_to_general_chat(db: Session, id_cliente: int, texto: str) -> None:
    """Envía un mensaje de sistema al chat general 'cliente' (y 'operativo' si lo prefieren) de un cliente."""
    if not id_cliente:
        return
    ahora = datetime.now()
    try:
        from app.websockets.manager import manager
        grupos = db.execute(text("SELECT id_grupo, tipo_grupo FROM CHAT_GRUPOS WHERE id_cliente = :cid AND activa = 1"), {"cid": id_cliente}).fetchall()
        for g_id, g_tipo in grupos:
            ins = db.execute(text("""
                INSERT INTO CHAT_GRUPO_MENSAJES
                    (id_grupo, id_usuario, username, mensaje, tipo_mensaje, fecha_envio, foto_adjunta)
                OUTPUT INSERTED.id_mensaje
                VALUES (:gid, NULL, 'Sistema', :mensaje, 'sistema', :fecha, NULL)
            """), {"gid": g_id, "mensaje": texto, "fecha": ahora}).fetchone()
            db.commit()
            await manager.broadcast_to_room(f"grupo_{g_id}", {
                "id_mensaje": ins[0], "id_grupo": g_id,
                "id_usuario": None, "username": "Sistema", "mensaje": texto, "tipo_mensaje": "sistema",
                "fecha_envio": str(ahora), "foto_adjunta": None, "leido_por": [],
            })
    except Exception as e:
        import logging
        logging.warning(f"Error _post_system_message_to_general_chat: {e}")
        db.rollback()


@router.post("/{visit_id}/mark-reviewed")
async def mark_reviewed(
    visit_id: int,
    revisada: bool = True,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_analyst_or_admin),
):
    visita = db.query(Visita).filter(Visita.id == visit_id).first()
    if not visita:
        raise HTTPException(status_code=404, detail="Visita no encontrada")
    visita.revisada_por = str(current_user.id) if revisada else None
    visita.fecha_revision = datetime.now() if revisada else None
    visita.estado = "Revisado" if revisada else "Pendiente"
    log_action(db, action="MARK_VISIT_REVIEWED", entity_type="Visita",
               user_id=current_user.id, username=current_user.username, rol=current_user.rol,
               entity_id=visita.id, changes={"revisada_por": visita.revisada_por})
    db.commit()
    notify_event("visit.reviewed", {"id_visita": visita.id, "revisada": revisada})
    if revisada and visita.id_cliente:
        await _post_system_message_to_general_chat(db, visita.id_cliente, f"✅ Visita #{visita.id} ({visita.punto_interes or 'Sin PDV'}) aprobada por el analista")
    return {"id_visita": visita.id, "revisada": revisada}


@router.get("/reject-reasons", response_model=List[RejectReason])
def get_reject_reasons(
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    rows = db.execute(text("SELECT id_razones_rechazos, razon FROM RAZONES_RECHAZOS ORDER BY razon")).fetchall()
    return [{"id": r.id_razones_rechazos, "razon": r.razon} for r in rows]


@router.get("/{visit_id}", response_model=VisitaResponse)
def get_visit(
    visit_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    visita = db.query(Visita).filter(Visita.id == visit_id).first()
    if not visita:
        raise HTTPException(status_code=404, detail="Visita no encontrada")
    return visita


@router.patch("/{visit_id}", response_model=VisitaResponse)
def update_visit(
    visit_id: int,
    data: VisitaUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    visita = db.query(Visita).filter(Visita.id == visit_id).first()
    if not visita:
        raise HTTPException(status_code=404, detail="Visita no encontrada")
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(visita, key, value)
    db.commit()
    db.refresh(visita)
    return visita


@router.get("/{visit_id}/photos", response_model=List[FotoResponse])
def get_visit_photos(
    visit_id: int,
    tipo: Optional[int] = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    query = db.query(Foto).filter(Foto.visita_id == visit_id)
    if tipo:
        query = query.filter(Foto.id_tipo_foto == tipo)
    fotos = query.all()

    foto_ids = [f.id for f in fotos]
    razones_map: dict = {}
    if foto_ids:
        q = text("""
            SELECT fr.id_foto, fr.id_razones_rechazos, r.razon, fr.rechazado_por, u.username
            FROM FOTOS_RAZONES_RECHAZOS fr
            JOIN RAZONES_RECHAZOS r ON r.id_razones_rechazos = fr.id_razones_rechazos
            LEFT JOIN USUARIOS u ON u.id_usuario = fr.rechazado_por
            WHERE fr.id_foto IN :ids
        """).bindparams(bindparam("ids", expanding=True))
        for row in db.execute(q, {"ids": foto_ids}).fetchall():
            d = razones_map.setdefault(row.id_foto, {"razones": [], "razones_ids": [], "rechazado_por": None, "rechazado_por_nombre": None})
            d["razones"].append(row.razon)
            d["razones_ids"].append(row.id_razones_rechazos)
            if row.rechazado_por and not d["rechazado_por"]:
                d["rechazado_por"] = row.rechazado_por
                d["rechazado_por_nombre"] = row.username
    for f in fotos:
        info = razones_map.get(f.id)
        f.razones = info["razones"] if info else None
        f.razones_ids = info["razones_ids"] if info else None
        f.rechazado_por = info["rechazado_por"] if info else None
        f.rechazado_por_nombre = info["rechazado_por_nombre"] if info else None
    return fotos


def _assert_can_manage_photos(db: Session, current_user: Usuario, foto_ids: list[int]) -> None:
    """Admin/Analyst pueden todo. Cliente solo puede gestionar fotos de sus visitas."""
    if current_user.rol in ("admin", "analyst"):
        return
    if not current_user.is_client:
        raise HTTPException(status_code=403, detail="Acceso denegado")
    if not current_user.id_perfil:
        raise HTTPException(status_code=403, detail="Usuario cliente sin id_perfil")

    # Validar que TODAS las fotos pertenezcan a visitas del cliente.
    rows = (
        db.query(Foto.id, Visita.id_cliente)
        .join(Visita, Foto.visita_id == Visita.id)
        .filter(Foto.id.in_(foto_ids))
        .all()
    )
    if len(rows) != len(set(foto_ids)):
        raise HTTPException(status_code=404, detail="Alguna foto no existe")
    for foto_id, cliente_id in rows:
        if cliente_id != current_user.id_perfil:
            raise HTTPException(status_code=403, detail="No puedes gestionar fotos de otro cliente")


@router.post("/approve-photos")
async def approve_photos(
    data: ApprovePhotosRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _assert_can_manage_photos(db, current_user, data.foto_ids)
    
    ids_str = ",".join(str(i) for i in data.foto_ids)
    conteo = db.execute(text(f"""
        SELECT v.id, v.id_cliente, COUNT(f.id), v.punto_interes
        FROM FOTOS_TOTALES f
        JOIN Visitas v ON v.id = f.id_visita
        WHERE f.id IN ({ids_str})
        GROUP BY v.id, v.id_cliente, v.punto_interes
    """)).fetchall()

    updated = db.query(Foto).filter(Foto.id.in_(data.foto_ids)).update(
        {"estado": "Aprobada"},
        synchronize_session=False,
    )
    log_action(db, action="APPROVE_PHOTOS", entity_type="Foto",
               user_id=current_user.id, username=current_user.username, rol=current_user.rol,
               changes={"foto_ids": data.foto_ids, "count": updated})
    db.commit()
    notify_event("photo.decided", {"foto_ids": data.foto_ids, "estado": "Aprobada"})
    
    for v_id, c_id, count, pdv in conteo:
        if c_id:
            await _post_system_message_to_general_chat(db, c_id, f"✅ {count} foto(s) aprobada(s) para la visita #{v_id} ({pdv or 'Sin PDV'})")
            
    return {"updated": updated, "message": "Fotos aprobadas"}


async def _post_rejection_to_chat(db: Session, visita: Optional[Visita], foto: Foto, motivo: str,
                                   current_user: Usuario) -> None:
    """Postea un mensaje de sistema con la foto rechazada SOLO en el
    sub-hilo de esa visita (CHAT_MENSAJES_GRUPO_VISITA, tipo_grupo='operativo')
    -- a diferencia de v1, que lo duplica también en el chat general del
    grupo. Decisión explícita: el chat general es para cosas generales del
    equipo, el aviso de una foto rechazada es sobre ESA visita puntual.
    Best-effort: no debe tumbar el rechazo de la foto (ya persistido antes
    de llamar esto)."""
    if not visita or not visita.id_cliente:
        return
    texto = f"Foto rechazada: {motivo}" if motivo else "Foto rechazada"
    ahora = datetime.now()

    try:
        from app.websockets.manager import manager

        ins = db.execute(text("""
            INSERT INTO CHAT_MENSAJES_GRUPO_VISITA
                (id_cliente, tipo_grupo, id_visita, id_usuario, username, mensaje, tipo_mensaje, fecha_envio, foto_adjunta)
            OUTPUT INSERTED.id_mensaje
            VALUES (:cid, 'operativo', :vid, NULL, 'Sistema', :mensaje, 'sistema', :fecha, :foto)
        """), {"cid": visita.id_cliente, "vid": visita.id, "mensaje": texto, "fecha": ahora, "foto": foto.blob_path}).fetchone()
        db.commit()
        from app.services.azure_service import azure_service
        _foto_proxy = azure_service.get_proxy_url(foto.blob_path) if foto.blob_path else None
        await manager.broadcast_to_room(f"grupo_visita_{visita.id_cliente}_operativo_{visita.id}", {
            "id_mensaje": ins[0], "id_cliente": visita.id_cliente, "tipo_grupo": "operativo", "id_visita": visita.id,
            "id_usuario": None, "username": "Sistema", "mensaje": texto, "tipo_mensaje": "sistema",
            "fecha_envio": str(ahora), "foto_adjunta": _foto_proxy, "leido_por": [],
        })
    except Exception:
        db.rollback()


@router.post("/reject-photo")
async def reject_photo(
    data: RejectPhotoRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _assert_can_manage_photos(db, current_user, [data.foto_id])
    foto = db.query(Foto).filter(Foto.id == data.foto_id).first()
    if not foto:
        raise HTTPException(status_code=404, detail="Foto no encontrada")
    foto.estado = "Rechazada"

    # Multi-razón: registra una fila por razón en FOTOS_RAZONES_RECHAZOS con quién rechazó.
    motivo = data.motivo or ""
    razones_nombres = []
    if data.razones_ids:
        db.query(FotoRazonRechazo).filter(FotoRazonRechazo.id_foto == foto.id).delete()
        q = text("SELECT id_razones_rechazos, razon FROM RAZONES_RECHAZOS WHERE id_razones_rechazos IN :ids").bindparams(bindparam("ids", expanding=True))
        name_by_id = {r.id_razones_rechazos: r.razon for r in db.execute(q, {"ids": data.razones_ids}).fetchall()}
        for rid in data.razones_ids:
            db.add(FotoRazonRechazo(id_foto=foto.id, id_razones_rechazos=rid, rechazado_por=current_user.id))
            if rid in name_by_id:
                razones_nombres.append(name_by_id[rid])
        if razones_nombres:
            motivo = ", ".join(razones_nombres)

    visita = db.query(Visita).filter(Visita.id == foto.visita_id).first()
    merc_cedula = None
    if visita:
        from app.models.mercaderista import Mercaderista
        merc = db.query(Mercaderista).filter(Mercaderista.id == visita.mercaderista_id).first()
        if merc:
            merc_cedula = merc.cedula

    # NotificacionRechazoFoto no tiene columna mercaderista_cedula (el modelo
    # real usa id_visita/id_cliente/nombre_cliente/punto_venta/rechazado_por)
    # — pasar ese kwarg tiraba TypeError antes de cualquier commit, así que
    # el rechazo entero fallaba sin persistir nada, ni siquiera foto.estado.
    ahora = datetime.now()
    notif = NotificacionRechazoFoto(
        foto_id=foto.id,
        id_visita=visita.id if visita else foto.visita_id,
        id_cliente=visita.cliente.id if visita and visita.cliente else None,
        nombre_cliente=visita.cliente.nombre if visita and visita.cliente else None,
        punto_venta=visita.punto.nombre if visita and visita.punto else None,
        rechazado_por=current_user.username,
        fecha_rechazo=ahora,
        fecha_notificacion=ahora,
        descripcion=motivo,
    )
    db.add(notif)
    log_action(db, action="REJECT_PHOTO", entity_type="Foto",
               user_id=current_user.id, username=current_user.username, rol=current_user.rol,
               entity_id=foto.id, entity_name=foto.blob_path,
               changes={"motivo": motivo, "mercaderista": merc_cedula})
    db.commit()

    if merc_cedula:
        try:
            from app.services.notification_service import notify_photo_rejected
            notify_photo_rejected(db, merc_cedula, foto.id, motivo)
        except Exception:
            pass

    await _post_rejection_to_chat(db, visita, foto, motivo, current_user)

    notify_event("photo.decided", {"foto_id": foto.id, "estado": "Rechazada", "visita_id": foto.visita_id})
    return {"message": "Foto rechazada", "foto_id": foto.id, "razones": razones_nombres}


@router.post("/save-decisions")
def save_photo_decisions(
    data: SavePhotoDecisionsRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_analyst_or_admin),
):
    for decision in data.decisions:
        foto_id = decision.get("foto_id")
        estado = decision.get("estado")
        foto = db.query(Foto).filter(Foto.id == foto_id).first()
        if foto and estado in ("Aprobada", "Rechazada"):
            foto.estado = estado
    db.commit()
    return {"message": "Decisiones guardadas"}





@router.get("/{visit_id}/balances", response_model=List[BalanceResponse])
def get_visit_balances(
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_analyst_or_admin),
):
    # Verificar que la visita pertenezca a un cliente manejado por el analista
    visita = db.query(Visita).filter(Visita.id == visit_id).first()
    if not visita:
        raise HTTPException(status_code=404, detail="Visita no encontrada")
    
    if current_user.is_analyst and current_user.id_perfil:
        is_managed = db.execute(text("""
            SELECT TOP 1 1
            FROM analistas_rutas ar
            JOIN RUTA_PROGRAMACION rp ON rp.id_ruta = ar.id_ruta
            WHERE ar.id_analista = :aid AND rp.activa = 1 AND rp.id_cliente = :cid
        """), {"aid": current_user.id_perfil, "cid": visita.id_cliente}).first()
        if not is_managed:
            raise HTTPException(status_code=403, detail="No tiene permiso para ver esta visita")

    # Registrar inicio de modificación
    db.query(Balance).filter(Balance.visita_id == visit_id).update(
        {"fecha_inicio_modificacion": datetime.now()},
        synchronize_session=False
    )
    db.commit()
    
    return db.query(Balance).filter(Balance.visita_id == visit_id).all()


@router.post("/update-balances")
def update_balances(
    data: UpdateBalancesRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_analyst_or_admin),
):
    for item in data.balances:
        db.query(Balance).filter(Balance.id == item.id_balance).update({
            "inv_inicial": item.inv_inicial,
            "inv_final": item.inv_final,
            "inv_deposito": item.inv_deposito,
            "caras": item.caras,
            "precio_bs": item.precio_bs,
            "precio_ds": item.precio_ds,
            "fecha_modificacion": datetime.now()
        }, synchronize_session=False)
    
    db.commit()
    notify_event("balance.updated", {"count": len(data.balances)})
    return {"message": "Balances actualizados correctamente"}
