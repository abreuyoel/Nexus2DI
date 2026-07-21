from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel
from app.db.session import get_db
from app.core.dependencies import get_current_user, require_analyst_or_admin
from app.modules.auth.entities import Usuario
from app.modules.supervisors.entities import Supervisor, SupervisorRuta, SupervisorCliente
from app.modules.visits.entities import Foto, NotificacionRechazoFoto
from app.modules.routes.entities import Ruta, RutaProgramacion
from app.modules.clients.entities import Cliente
from app.modules.visits.dto import FotoResponse, NotificacionRechazoResponse
from app.shared.photo_service import process_and_upload_photo
from app.shared.audit_service import log_action

router = APIRouter(tags=["Supervisores"])


class IdListRequest(BaseModel):
    ids: List[int] = []


class SupervisorCreate(BaseModel):
    nombre: str


class SupervisorUpdate(BaseModel):
    nombre: str


# ─── Rutas del Supervisor (Reemplazo / Notificaciones) ──────────────────────

@router.get("/api/supervisor/rejected-photos", response_model=List[FotoResponse])
def get_rejected_photos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol not in ("supervisor", "admin", "analyst"):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    return db.query(Foto).filter(Foto.estado == "Rechazada").order_by(Foto.fecha_registro.desc()).all()


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
