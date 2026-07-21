from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text, bindparam
from typing import List, Optional
from datetime import date, timedelta, datetime
from app.db.session import get_db
from app.core.dependencies import get_current_user, require_analyst_or_admin
from app.modules.auth.entities import Usuario
from app.modules.visits.entities import Visita, Foto, NotificacionRechazoFoto, FotoRazonRechazo
from app.modules.visits.entities import Balance
from app.modules.analysts.entities import AnalistaCliente
from app.modules.visits.dto import (
    VisitaCreate, VisitaUpdate, VisitaResponse, UpdateBalancesRequest, BalanceResponse,
    FotoResponse, ApprovePhotosRequest, RejectPhotoRequest, SavePhotoDecisionsRequest, RejectReason
)
from app.shared.audit_service import log_action
from app.shared.realtime import notify_event

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
        managed_clients = db.query(AnalistaCliente.id_cliente).filter(
            AnalistaCliente.id_analista == current_user.id_perfil
        ).all()
        managed_ids = [c[0] for c in managed_clients]
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
    from app.shared.visibility import coordinator_client_ids
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
        analyst_join = "JOIN ANALISTAS_CLIENTE ac ON ac.id_cliente = v.id_cliente AND ac.id_analista = :aid"
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


@router.post("/{visit_id}/mark-reviewed")
def mark_reviewed(
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
    if current_user.rol in ("admin", "analyst"):
        return
    if not current_user.is_client:
        raise HTTPException(status_code=403, detail="Acceso denegado")
    if not current_user.id_perfil:
        raise HTTPException(status_code=403, detail="Usuario cliente sin id_perfil")

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
def approve_photos(
    data: ApprovePhotosRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _assert_can_manage_photos(db, current_user, data.foto_ids)
    updated = db.query(Foto).filter(Foto.id.in_(data.foto_ids)).update(
        {"estado": "Aprobada"},
        synchronize_session=False,
    )
    log_action(db, action="APPROVE_PHOTOS", entity_type="Foto",
               user_id=current_user.id, username=current_user.username, rol=current_user.rol,
               changes={"foto_ids": data.foto_ids, "count": updated})
    db.commit()
    notify_event("photo.decided", {"foto_ids": data.foto_ids, "estado": "Aprobada"})
    return {"updated": updated, "message": "Fotos aprobadas"}


@router.post("/reject-photo")
def reject_photo(
    data: RejectPhotoRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _assert_can_manage_photos(db, current_user, [data.foto_id])
    foto = db.query(Foto).filter(Foto.id == data.foto_id).first()
    if not foto:
        raise HTTPException(status_code=404, detail="Foto no encontrada")
    foto.estado = "Rechazada"

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
        from app.modules.merchandisers.entities import Mercaderista
        merc = db.query(Mercaderista).filter(Mercaderista.id == visita.mercaderista_id).first()
        if merc:
            merc_cedula = merc.cedula

    notif = NotificacionRechazoFoto(
        foto_id=foto.id,
        id_foto_rechazada=foto.id,
        id_visita=foto.visita_id,
        id_cliente=visita.id_cliente if visita else None,
        nombre_cliente=visita.cliente.nombre if (visita and visita.cliente) else None,
        punto_venta=visita.punto.punto_de_interes if (visita and visita.punto) else None,
        rechazado_por=current_user.username,
        fecha_rechazo=datetime.now(),
        fecha_notificacion=datetime.now(),
        leida=False,
        descripcion=motivo,
        mercaderista_cedula=merc_cedula,
    )
    db.add(notif)
    log_action(db, action="REJECT_PHOTO", entity_type="Foto",
               user_id=current_user.id, username=current_user.username, rol=current_user.rol,
               entity_id=foto.id, entity_name=foto.blob_path,
               changes={"motivo": motivo, "mercaderista": merc_cedula})
    db.commit()

    if merc_cedula:
        try:
            from app.shared.notification_service import notify_photo_rejected
            notify_photo_rejected(db, merc_cedula, foto.id, motivo)
        except Exception:
            pass

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
    visita = db.query(Visita).filter(Visita.id == visit_id).first()
    if not visita:
        raise HTTPException(status_code=404, detail="Visita no encontrada")
    
    if current_user.is_analyst and current_user.id_perfil:
        is_managed = db.query(AnalistaCliente).filter(
            AnalistaCliente.id_analista == current_user.id_perfil,
            AnalistaCliente.id_cliente == visita.id_cliente
        ).first()
        if not is_managed:
            raise HTTPException(status_code=403, detail="No tiene permiso para ver esta visita")

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
