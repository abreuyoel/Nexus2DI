from datetime import date, timedelta, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.core.dependencies import get_current_user, require_analyst_or_admin
from app.modules.auth.entities import Usuario
from app.modules.visits.entities import (
    Visita, Foto, NotificacionRechazoFoto, FotoRazonRechazo, Balance, RazonRechazo, TipoFoto
)
from app.modules.analysts.entities import AnalistaCliente
from app.modules.routes.entities import PuntoInteres, Ruta, RutaProgramacion
from app.modules.clients.entities import Cliente
from app.modules.merchandisers.entities import Mercaderista
from app.modules.chat.entities import ChatMensaje
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

    f_desde = datetime.strptime(desde, '%Y-%m-%d').date() if isinstance(desde, str) else desde
    f_hasta = datetime.strptime(hasta, '%Y-%m-%d').date() if isinstance(hasta, str) else hasta

    sub_ruta = (
        db.query(
            RutaProgramacion.punto_id.label("id_punto_interes"),
            func.min(Ruta.nombre).label("ruta_nombre")
        )
        .join(Ruta, Ruta.id == RutaProgramacion.ruta_id)
        .filter(RutaProgramacion.activo == True)
        .group_by(RutaProgramacion.punto_id)
        .subquery()
    )

    sub_chat = (
        db.query(
            ChatMensaje.visita_id,
            func.count(ChatMensaje.id).label("chat_msgs")
        )
        .group_by(ChatMensaje.visita_id)
        .subquery()
    )

    query = (
        db.query(
            Visita.id,
            Cliente.nombre.label("cliente_nombre"),
            Cliente.id,
            PuntoInteres.nombre.label("punto_nombre"),
            PuntoInteres.id.label("punto_id"),
            PuntoInteres.ciudad,
            sub_ruta.c.ruta_nombre,
            Mercaderista.nombre.label("mercaderista_nombre"),
            Visita.fecha,
            func.sum(func.case((Foto.id_tipo_foto.notin_([5, 6]) & Foto.id.isnot(None), 1), else_=0)).label("revisar"),
            func.sum(func.case((Foto.id_tipo_foto.notin_([5, 6]) & (Foto.estado == "Aprobada"), 1), else_=0)).label("aprobadas"),
            func.sum(func.case((Foto.id_tipo_foto.notin_([5, 6]) & (Foto.estado == "Rechazada"), 1), else_=0)).label("rechazadas"),
            func.sum(func.case((Foto.id_tipo_foto.in_([5, 6]), 1), else_=0)).label("activaciones"),
            func.max(func.coalesce(sub_chat.c.chat_msgs, 0)).label("chat_msgs"),
            func.max(func.case((Visita.revisada_por.isnot(None) | (Visita.estado == "Revisado"), 1), else_=0)).label("revisada_flag"),
            func.max(func.coalesce(Visita.estado, "Pendiente")).label("estado_visita")
        )
        .join(Cliente, Visita.id_cliente == Cliente.id)
        .join(PuntoInteres, Visita.punto_id == PuntoInteres.id)
        .join(Mercaderista, Visita.mercaderista_id == Mercaderista.id)
        .outerjoin(Foto, Foto.visita_id == Visita.id)
        .outerjoin(sub_ruta, sub_ruta.c.id_punto_interes == PuntoInteres.id)
        .outerjoin(sub_chat, sub_chat.c.visita_id == Visita.id)
        .filter(Visita.fecha >= f_desde, Visita.fecha <= f_hasta)
    )

    if cliente_id:
        query = query.filter(Visita.id_cliente == cliente_id)
    if visible_ids is not None:
        if not visible_ids:
            return []
        query = query.filter(Visita.id_cliente.in_(visible_ids))

    if current_user.is_analyst and current_user.id_perfil:
        analista_id = int(current_user.id_perfil)
        sub_ac = (
            db.query(AnalistaCliente.id_cliente)
            .filter(AnalistaCliente.id_analista == analista_id)
            .subquery()
        )
        query = query.filter(Visita.id_cliente.in_(sub_ac))

    rows = (
        query.group_by(
            Visita.id, Cliente.nombre, Cliente.id, PuntoInteres.nombre, PuntoInteres.id,
            PuntoInteres.ciudad, sub_ruta.c.ruta_nombre, Mercaderista.nombre, Visita.fecha
        )
        .having(func.sum(func.case((Foto.id_tipo_foto.notin_([5, 6]) & Foto.id.isnot(None), 1), else_=0)) > 0)
        .order_by(Visita.fecha.desc())
        .all()
    )

    query_tipos = (
        db.query(
            Visita.id.label("visita_id"),
            Foto.id_tipo_foto,
            func.coalesce(TipoFoto.nombre, func.concat("Tipo ", Foto.id_tipo_foto)).label("label"),
            func.count(Foto.id).label("total"),
            func.sum(func.case((Foto.estado == "Aprobada", 1), else_=0)).label("aprobadas"),
            func.sum(func.case((Foto.estado == "Rechazada", 1), else_=0)).label("rechazadas")
        )
        .join(Foto, Foto.visita_id == Visita.id)
        .outerjoin(TipoFoto, TipoFoto.id == Foto.id_tipo_foto)
        .filter(Visita.fecha >= f_desde, Visita.fecha <= f_hasta, Foto.id_tipo_foto.isnot(None))
    )

    if cliente_id:
        query_tipos = query_tipos.filter(Visita.id_cliente == cliente_id)
    if visible_ids is not None:
        query_tipos = query_tipos.filter(Visita.id_cliente.in_(visible_ids))
    if current_user.is_analyst and current_user.id_perfil:
        analista_id = int(current_user.id_perfil)
        sub_ac = (
            db.query(AnalistaCliente.id_cliente)
            .filter(AnalistaCliente.id_analista == analista_id)
            .subquery()
        )
        query_tipos = query_tipos.filter(Visita.id_cliente.in_(sub_ac))

    rows_tipos = (
        query_tipos.group_by(Visita.id, Foto.id_tipo_foto, TipoFoto.nombre)
        .all()
    )

    tipos_map: dict = {}
    for r in rows_tipos:
        tid = int(r[1])
        tipos_map.setdefault(r[0], []).append({
            "id_tipo_foto": tid,
            "label": r[2],
            "total": int(r[3] or 0),
            "aprobadas": int(r[4] or 0),
            "rechazadas": int(r[5] or 0),
            "revisable": tid not in (5, 6),
        })

    out = []
    for r in rows:
        rev = int(r[9] or 0)
        apr = int(r[10] or 0)
        rec = int(r[11] or 0)
        out.append({
            "id_visita": r[0],
            "cliente": r[1],
            "id_cliente": r[2],
            "punto_de_interes": r[3],
            "id_punto": r[4],
            "ciudad": r[5] or "",
            "ruta": r[6] or "Sin ruta",
            "mercaderista": r[7],
            "fecha": r[8].isoformat() if r[8] else None,
            "fotos_revisar": rev,
            "aprobadas": apr,
            "rechazadas": rec,
            "sin_revisar": max(rev - apr - rec, 0),
            "activaciones": int(r[12] or 0),
            "revisada": bool(r[14]),
            "estado": "Revisado" if r[14] else (r[15] or "Pendiente"),
            "completada": rev > 0 and (apr + rec) >= rev,
            "tiene_chat": int(r[13] or 0) > 0,
            "chat_msgs": int(r[13] or 0),
            "tipos": sorted(tipos_map.get(r[0], []), key=lambda x: x["id_tipo_foto"]),
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
    rows = db.query(RazonRechazo).order_by(RazonRechazo.razon).all()
    return [RejectReason(id=r.id, razon=r.razon) for r in rows]


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
        rows = (
            db.query(
                FotoRazonRechazo.id_foto,
                RazonRechazo.id,
                RazonRechazo.razon,
                FotoRazonRechazo.rechazado_por,
                Usuario.username
            )
            .join(RazonRechazo, RazonRechazo.id == FotoRazonRechazo.id_razones_rechazos)
            .outerjoin(Usuario, Usuario.id == FotoRazonRechazo.rechazado_por)
            .filter(FotoRazonRechazo.id_foto.in_(foto_ids))
            .all()
        )
        for r_fid, r_id, r_razon, r_por, r_uname in rows:
            d = razones_map.setdefault(r_fid, {"razones": [], "razones_ids": [], "rechazado_por": None, "rechazado_por_nombre": None})
            d["razones"].append(r_razon)
            d["razones_ids"].append(r_id)
            if r_por and not d["rechazado_por"]:
                d["rechazado_por"] = r_por
                d["rechazado_por_nombre"] = r_uname

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
        name_by_id = {
            r.id: r.razon for r in db.query(RazonRechazo).filter(RazonRechazo.id.in_(data.razones_ids)).all()
        }
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
