from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from typing import List, Optional
from datetime import datetime, date
from pydantic import BaseModel
from app.db.session import get_db
from app.core.dependencies import get_current_user, require_analyst_or_admin
from app.modules.auth.entities import Usuario
from app.modules.supervisors.entities import Supervisor, SupervisorRuta, SupervisorCliente
from app.modules.visits.entities import Foto, NotificacionRechazoFoto, Visita
from app.modules.routes.entities import Ruta, RutaProgramacion
from app.modules.clients.entities import Cliente
from app.modules.merchandisers.entities import Mercaderista
from app.modules.visits.dto import FotoResponse, RejectedPhotosPaginatedResponse, NotificacionRechazoResponse
from app.shared.photo_service import process_and_upload_photo
from app.shared.audit_service import log_action
from app.shared.redis_cache import make_cache_key, get_cached_or_compute

router = APIRouter(tags=["Supervisores"])


class IdListRequest(BaseModel):
    ids: List[int] = []


class SupervisorCreate(BaseModel):
    nombre: str


class SupervisorUpdate(BaseModel):
    nombre: str


# ─── Rutas del Supervisor (Reemplazo / Notificaciones) ──────────────────────

@router.get("/api/supervisor/rejected-photos/filters")
def get_rejected_photos_filters(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Retorna listas de valores distintos para los filtros (cacheado 5 min)."""
    if current_user.rol not in ("supervisor", "admin", "analyst"):
        raise HTTPException(status_code=403, detail="Acceso denegado")

    cache_key = make_cache_key("rejected_photos_filters")
    return get_cached_or_compute(cache_key, 300, lambda: _compute_filters(db))


def _compute_filters(db: Session) -> dict:
    """Consulta real a la BD para obtener opciones de filtros."""
    mercs = (
        db.query(Mercaderista.nombre, Mercaderista.cedula)
        .join(Visita, Visita.mercaderista_id == Mercaderista.id)
        .join(Foto, Foto.visita_id == Visita.id)
        .filter(Foto.estado == "Rechazada", Mercaderista.nombre.isnot(None))
        .distinct()
        .order_by(Mercaderista.nombre)
        .all()
    )

    # Quienes han rechazado (actualmente NULL en BD, pero dejamos la query)
    revisados = (
        db.query(Foto.revisada_por)
        .filter(Foto.estado == "Rechazada", Foto.revisada_por.isnot(None), Foto.revisada_por != "")
        .distinct()
        .all()
    )
    ultimos = (
        db.query(Foto.ultimo_rechazo_por_paso1)
        .filter(Foto.estado == "Rechazada", Foto.ultimo_rechazo_por_paso1.isnot(None), Foto.ultimo_rechazo_por_paso1 != "")
        .distinct()
        .all()
    )
    rechazadores = sorted(set(
        [r[0] for r in revisados if r[0]] + [r[0] for r in ultimos if r[0]]
    ))

    return {
        "mercaderistas": [
            {"value": m.nombre, "label": f"{m.nombre} — C.I. {m.cedula}"}
            for m in mercs
        ],
        "rechazados_por": [
            {"value": r, "label": r}
            for r in rechazadores
        ],
    }


@router.get("/api/supervisor/rejected-photos", response_model=RejectedPhotosPaginatedResponse)
def get_rejected_photos(
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(20, ge=1, le=100, description="Ítems por página"),
    fecha_desde: Optional[str] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    mercaderista: Optional[str] = Query(None, description="Nombre del mercaderista"),
    rechazado_por: Optional[str] = Query(None, description="Quién rechazó"),
    cedula: Optional[str] = Query(None, description="Cédula del mercaderista"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol not in ("supervisor", "admin", "analyst"):
        raise HTTPException(status_code=403, detail="Acceso denegado")

    base_query = (
        db.query(Foto)
        .options(joinedload(Foto.visita).joinedload(Visita.mercaderista))
        .filter(Foto.estado == "Rechazada")
    )

    # ── Filtros dinámicos ──────────────────────────────────────────
    if fecha_desde:
        try:
            fd = datetime.strptime(fecha_desde, "%Y-%m-%d")
            base_query = base_query.filter(Foto.fecha_registro >= fd)
        except ValueError:
            pass
    if fecha_hasta:
        try:
            fh = datetime.strptime(fecha_hasta, "%Y-%m-%d")
            base_query = base_query.filter(Foto.fecha_registro <= fh)
        except ValueError:
            pass
    if mercaderista:
        base_query = base_query.filter(Visita.mercaderista.has(Mercaderista.nombre.ilike(f"%{mercaderista}%")))
    if cedula:
        base_query = base_query.filter(Visita.mercaderista.has(Mercaderista.cedula.ilike(f"%{cedula}%")))
    if rechazado_por:
        base_query = base_query.filter(
            or_(
                Foto.revisada_por.ilike(f"%{rechazado_por}%"),
                Foto.ultimo_rechazo_por_paso1.ilike(f"%{rechazado_por}%"),
            )
        )

    # ── Total (para paginación) ─────────────────────────────────────
    total = base_query.count()
    total_pages = max(1, (total + per_page - 1) // per_page)

    # ── Página actual ──────────────────────────────────────────────
    fotos = (
        base_query
        .order_by(Foto.fecha_registro.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    # ── Mapear a DTO ───────────────────────────────────────────────
    items = []
    for f in fotos:
        visita = f.visita
        merc = visita.mercaderista if visita else None
        items.append(
            FotoResponse(
                id=f.id,
                visita_id=f.visita_id,
                id_tipo_foto=f.id_tipo_foto,
                blob_path=f.blob_path,
                estado=f.estado,
                latitud=f.latitud,
                longitud=f.longitud,
                exif_timestamp=f.exif_timestamp,
                camera_model=f.camera_model,
                fecha_registro=f.fecha_registro,
                motivo_rechazo=f.motivo_rechazo,
                revisada_por=f.revisada_por,
                fecha_revision=f.fecha_revision,
                comentario=f.comentario,
                ultimo_rechazo_por=f.ultimo_rechazo_por_paso1,
                ultima_fecha_rechazo=f.ultima_fecha_rechazo_paso1,
                mercaderista_nombre=merc.nombre if merc else None,
                mercaderista_cedula=str(merc.cedula) if merc else None,
                fecha_visita=visita.fecha if visita else None,
            )
        )

    return RejectedPhotosPaginatedResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


@router.post("/api/supervisor/replace-photo")
async def replace_rejected_photo(
    foto_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol not in ("supervisor", "admin", "mercaderista"):
        raise HTTPException(status_code=403, detail="Acceso denegado")

    foto = db.query(Foto).filter(Foto.id == foto_id).first()
    if not foto:
        raise HTTPException(status_code=404, detail="Foto no encontrada")

    file_bytes = await file.read()
    result = process_and_upload_photo(file_bytes, file.content_type or "image/jpeg")

    old_path = foto.blob_path
    foto.blob_path = result.get("blob_path")
    foto.estado = "pendiente"
    foto.latitud = result.get("latitud")
    foto.longitud = result.get("longitud")
    foto.exif_timestamp = result.get("timestamp")
    foto.camera_model = result.get("camera_model")

    log_action(db, action="REPLACE_PHOTO", entity_type="Foto",
               user_id=current_user.id, username=current_user.username, rol=current_user.rol,
               entity_id=foto.id,
               changes={"old_path": old_path, "new_path": foto.blob_path})
    db.commit()
    return {"message": "Foto reemplazada exitosamente", "foto_id": foto.id, "blob_path": foto.blob_path}


@router.get("/api/supervisor/notifications", response_model=List[NotificacionRechazoResponse])
def get_notifications(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return db.query(NotificacionRechazoFoto).filter(
        NotificacionRechazoFoto.leida == False
    ).order_by(NotificacionRechazoFoto.fecha_notificacion.desc()).limit(50).all()


# ─── Rutas de Gestión del Supervisor (Asignaciones) ────────────────────────

@router.post("/api/supervisores", status_code=201)
def create_supervisor(
    data: SupervisorCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_analyst_or_admin),
):
    nombre = (data.nombre or "").strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre es requerido")
    s = Supervisor(nombre=nombre)
    db.add(s)
    db.commit()
    db.refresh(s)
    return {"id": s.id, "nombre": s.nombre, "rutas_count": 0, "clientes_count": 0}


@router.put("/api/supervisores/{supervisor_id}")
def update_supervisor(
    supervisor_id: int,
    data: SupervisorUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_analyst_or_admin),
):
    s = db.query(Supervisor).filter(Supervisor.id == supervisor_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Supervisor no encontrado")
    nombre = (data.nombre or "").strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre es requerido")
    s.nombre = nombre
    db.commit()
    return {"id": s.id, "nombre": s.nombre}


@router.delete("/api/supervisores/{supervisor_id}", status_code=204)
def delete_supervisor(
    supervisor_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_analyst_or_admin),
):
    s = db.query(Supervisor).filter(Supervisor.id == supervisor_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Supervisor no encontrado")
    db.query(SupervisorRuta).filter(SupervisorRuta.id_supervisor == supervisor_id).delete(synchronize_session=False)
    db.query(SupervisorCliente).filter(SupervisorCliente.id_supervisor == supervisor_id).delete(synchronize_session=False)
    db.delete(s)
    db.commit()
    return None


@router.get("/api/supervisores/with-assignments")
def list_supervisors_with_assignments(
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    sups = db.query(Supervisor).order_by(Supervisor.nombre).all()
    rutas_counts = dict(
        db.query(SupervisorRuta.id_supervisor, func.count(SupervisorRuta.id_ruta))
        .group_by(SupervisorRuta.id_supervisor).all()
    )
    cli_counts = dict(
        db.query(SupervisorCliente.id_supervisor, func.count(SupervisorCliente.id_cliente))
        .group_by(SupervisorCliente.id_supervisor).all()
    )
    return [{
        "id": s.id,
        "nombre": s.nombre,
        "rutas_count": rutas_counts.get(s.id, 0),
        "clientes_count": cli_counts.get(s.id, 0),
    } for s in sups]


@router.get("/api/supervisores/{supervisor_id}/routes")
def get_supervisor_routes(
    supervisor_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    rows = (
        db.query(Ruta)
        .join(SupervisorRuta, SupervisorRuta.id_ruta == Ruta.id)
        .filter(SupervisorRuta.id_supervisor == supervisor_id)
        .order_by(Ruta.nombre).all()
    )
    return [{"id": r.id, "nombre": r.nombre, "servicio": r.servicio, "cuadrante": r.cuadrante} for r in rows]


@router.post("/api/supervisores/{supervisor_id}/sync-routes")
def sync_supervisor_routes(
    supervisor_id: int,
    data: IdListRequest,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_analyst_or_admin),
):
    if not db.query(Supervisor).filter(Supervisor.id == supervisor_id).first():
        raise HTTPException(status_code=404, detail="Supervisor no encontrado")
    db.query(SupervisorRuta).filter(SupervisorRuta.id_supervisor == supervisor_id).delete(synchronize_session=False)
    for rid in set(data.ids):
        db.add(SupervisorRuta(id_supervisor=supervisor_id, id_ruta=rid))
    db.commit()
    return {"message": "Rutas del supervisor sincronizadas", "count": len(set(data.ids))}


@router.get("/api/supervisores/{supervisor_id}/clients")
def get_supervisor_clients(
    supervisor_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    rows = (
        db.query(Cliente)
        .join(SupervisorCliente, SupervisorCliente.id_cliente == Cliente.id)
        .filter(SupervisorCliente.id_supervisor == supervisor_id)
        .order_by(Cliente.nombre).all()
    )
    return [{"id": c.id, "nombre": c.nombre} for c in rows]


@router.get("/api/supervisores/{supervisor_id}/route-clients")
def get_supervisor_route_clients(
    supervisor_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    """Clientes distintos presentes en las rutas asignadas al supervisor."""
    rows = (
        db.query(Cliente.id, Cliente.nombre)
        .join(RutaProgramacion, RutaProgramacion.id_cliente == Cliente.id)
        .join(SupervisorRuta, SupervisorRuta.id_ruta == RutaProgramacion.ruta_id)
        .filter(
            SupervisorRuta.id_supervisor == supervisor_id,
            RutaProgramacion.activo == True,
            Cliente.nombre.isnot(None),
        )
        .distinct().order_by(Cliente.nombre).all()
    )
    return [{"id": cid, "nombre": cn} for cid, cn in rows]


@router.post("/api/supervisores/{supervisor_id}/sync-clients")
def sync_supervisor_clients(
    supervisor_id: int,
    data: IdListRequest,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_analyst_or_admin),
):
    if not db.query(Supervisor).filter(Supervisor.id == supervisor_id).first():
        raise HTTPException(status_code=404, detail="Supervisor no encontrado")
    db.query(SupervisorCliente).filter(SupervisorCliente.id_supervisor == supervisor_id).delete(synchronize_session=False)
    for cid in set(data.ids):
        db.add(SupervisorCliente(id_supervisor=supervisor_id, id_cliente=cid))
    db.commit()
    return {"message": "Clientes del supervisor sincronizados", "count": len(set(data.ids))}
