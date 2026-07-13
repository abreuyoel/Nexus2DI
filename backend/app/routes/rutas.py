from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Optional
from datetime import date, datetime
from app.db.session import get_db
from app.core.dependencies import get_current_user, require_analyst_or_admin, require_permission
from app.models.user import Usuario, UserPermission
from app.models.ruta import Ruta, RutaProgramacion, RutaCambioFuturo, RutaActivada, AnalistaRuta
from app.models.cliente import Cliente
from app.models.punto import PuntoInteres
from app.models.mercaderista import MercaderistaRuta
from app.schemas.ruta import (
    RutaCreate, RutaUpdate, RutaResponse,
    RutaProgramacionCreate, RutaProgramacionResponse,
    CambioFuturoResponse,
    AddPointToRouteRequest, ScheduleChangeRequest,
    BulkApplyRequest,
)

router = APIRouter(prefix="/api/routes", tags=["Rutas"])


def _next_route_number(db: Session, tipo: str) -> int:
    """Mayor sufijo numérico existente para 'Ruta {tipo}' + 1."""
    prefix = f"Ruta {tipo}"
    routes = db.query(Ruta.nombre).filter(Ruta.nombre.like(f"{prefix}%")).all()
    max_num = 0
    for (nombre,) in routes:
        if nombre:
            suffix = nombre[len(prefix):]
            if suffix.isdigit():
                max_num = max(max_num, int(suffix))
    return max_num + 1


@router.get("/next-number")
def get_next_route_number(tipo: str, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    tipo = tipo.upper()
    if tipo not in ["E", "A", "T"]:
        raise HTTPException(status_code=400, detail="Tipo inválido. Use E, A o T")
    return {"next_number": _next_route_number(db, tipo)}


@router.get("/options")
def get_route_options(db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    servicios = db.query(Ruta.servicio).distinct().filter(Ruta.servicio != None).all()
    return {"servicios": [s[0] for s in servicios]}


def _enrich_routes(db: Session, rutas: List[Ruta]) -> List[dict]:
    """Agrega por ruta: puntos_count, clientes (distintos), region y cliente exclusivo."""
    ruta_ids = [r.id for r in rutas]
    if not ruta_ids:
        return []

    counts = dict(
        db.query(RutaProgramacion.ruta_id, func.count(RutaProgramacion.id))
        .filter(RutaProgramacion.ruta_id.in_(ruta_ids), RutaProgramacion.activo == True)
        .group_by(RutaProgramacion.ruta_id)
        .all()
    )

    clientes_map: dict[int, set] = {}
    cliente_rows = (
        db.query(RutaProgramacion.ruta_id, Cliente.nombre)
        .join(Cliente, Cliente.id == RutaProgramacion.id_cliente)
        .filter(
            RutaProgramacion.ruta_id.in_(ruta_ids),
            RutaProgramacion.activo == True,
            Cliente.nombre.isnot(None),
        )
        .distinct()
        .all()
    )
    for rid, cname in cliente_rows:
        clientes_map.setdefault(rid, set()).add(cname)

    excl_ids = [r.id_cliente_exclusivo for r in rutas if r.id_cliente_exclusivo]
    excl_map = (
        dict(db.query(Cliente.id, Cliente.nombre).filter(Cliente.id.in_(excl_ids)).all())
        if excl_ids else {}
    )

    return [{
        "id": r.id,
        "nombre": r.nombre,
        "servicio": r.servicio,
        "coordinador_1": r.coordinador_1,
        "coordinador_2": r.coordinador_2,
        "supervisor": r.supervisor,
        "cuadrante": r.cuadrante,
        "id_cliente_exclusivo": r.id_cliente_exclusivo,
        "activa": True,
        "region": r.cuadrante,
        "puntos_count": counts.get(r.id, 0),
        "clientes": sorted(clientes_map.get(r.id, set())),
        "cliente_exclusivo_nombre": excl_map.get(r.id_cliente_exclusivo),
    } for r in rutas]


@router.get("/", response_model=List[RutaResponse])
def list_routes(
    activa: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    query = db.query(Ruta)

    # Granular Visibility Logic
    if not current_user.is_admin:
        # Check if they have 'can_see_all' permission for routes
        perm = next((p for p in current_user.permisos if p.module == 'rutas'), None)
        can_see_all = perm.can_see_all if perm else False

        if not can_see_all and current_user.is_analyst:
            # Only see routes where they are assigned in analistas_rutas
            query = query.join(Ruta.analistas).filter(AnalistaRuta.id_analista == current_user.id_perfil)

    rutas = query.order_by(Ruta.nombre).all()
    return _enrich_routes(db, rutas)


@router.post("/", response_model=RutaResponse, status_code=201)
def create_route(
    data: RutaCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_permission('routes', 'write')),
):
    tipo = data.tipo.upper()
    if tipo not in ["E", "A", "T"]:
        raise HTTPException(status_code=400, detail="Tipo inválido. Use E, A o T")
    if tipo == "E" and not data.id_cliente_exclusivo:
        raise HTTPException(status_code=400, detail="Cliente exclusivo es requerido para rutas tipo E (Exclusiva)")

    route_name = f"Ruta {tipo}{_next_route_number(db, tipo)}"

    db_data = data.model_dump(exclude={"tipo"})
    db_data["nombre"] = route_name
    # El cliente exclusivo sólo aplica a rutas tipo E
    if tipo != "E":
        db_data["id_cliente_exclusivo"] = None

    ruta = Ruta(**db_data)
    db.add(ruta)
    db.commit()
    db.refresh(ruta)
    return _enrich_routes(db, [ruta])[0]


@router.get("/activated/today")
def get_activated_routes_today(
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    activadas = db.query(RutaActivada).all()
    return [{"ruta_id": a.ruta_id, "mercaderista_id": a.mercaderista_id} for a in activadas]


@router.get("/{route_id}", response_model=RutaResponse)
def get_route(route_id: int, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    ruta = db.query(Ruta).filter(Ruta.id == route_id).first()
    if not ruta:
        raise HTTPException(status_code=404, detail="Ruta no encontrada")
    return ruta


@router.patch("/{route_id}", response_model=RutaResponse)
def update_route(
    route_id: int,
    data: RutaUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_permission('routes', 'write')),
):
    ruta = db.query(Ruta).filter(Ruta.id == route_id).first()
    if not ruta:
        raise HTTPException(status_code=404, detail="Ruta no encontrada")
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(ruta, key, value)
    db.commit()
    db.refresh(ruta)
    return _enrich_routes(db, [ruta])[0]


@router.delete("/{route_id}", status_code=204)
def delete_route(
    route_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_permission('routes', 'delete')),
):
    ruta = db.query(Ruta).filter(Ruta.id == route_id).first()
    if not ruta:
        raise HTTPException(status_code=404, detail="Ruta no encontrada")
    # Eliminar dependencias sin cascade configurado (asignaciones/activaciones)
    db.query(MercaderistaRuta).filter(MercaderistaRuta.ruta_id == route_id).delete(synchronize_session=False)
    db.query(AnalistaRuta).filter(AnalistaRuta.id_ruta == route_id).delete(synchronize_session=False)
    db.query(RutaActivada).filter(RutaActivada.ruta_id == route_id).delete(synchronize_session=False)
    # programaciones y cambios_futuros caen por cascade en la relación
    db.delete(ruta)
    db.commit()
    return None


@router.post("/{route_id}/duplicate", response_model=RutaResponse, status_code=201)
def duplicate_route(
    route_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_permission('routes', 'write')),
):
    orig = db.query(Ruta).filter(Ruta.id == route_id).first()
    if not orig:
        raise HTTPException(status_code=404, detail="Ruta no encontrada")

    # Derivar el tipo (letra tras "Ruta ") para numerar igual que el original
    tipo = "T"
    if orig.nombre and orig.nombre.startswith("Ruta ") and len(orig.nombre) > 5:
        cand = orig.nombre[5]
        if cand in ("E", "A", "T"):
            tipo = cand
    new_name = f"Ruta {tipo}{_next_route_number(db, tipo)}"

    nueva = Ruta(
        nombre=new_name,
        servicio=orig.servicio,
        coordinador_1=orig.coordinador_1,
        coordinador_2=orig.coordinador_2,
        supervisor=orig.supervisor,
        cuadrante=orig.cuadrante,
        id_cliente_exclusivo=orig.id_cliente_exclusivo,
    )
    db.add(nueva)
    db.flush()  # asignar nueva.id

    for p in orig.programaciones:
        db.add(RutaProgramacion(
            ruta_id=nueva.id,
            punto_id=p.punto_id,
            id_cliente=p.id_cliente,
            dia=p.dia,
            prioridad=p.prioridad,
            activo=p.activo,
            punto_interes_nombre=p.punto_interes_nombre,
        ))

    db.commit()
    db.refresh(nueva)
    return _enrich_routes(db, [nueva])[0]


@router.get("/{route_id}/points", response_model=List[RutaProgramacionResponse])
def get_route_points(
    route_id: int,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    q = db.query(RutaProgramacion).options(
        joinedload(RutaProgramacion.punto),
        joinedload(RutaProgramacion.cliente)
    ).filter(RutaProgramacion.ruta_id == route_id)
    if not include_inactive:
        q = q.filter(RutaProgramacion.activo == True)
    return q.all()


@router.post("/{route_id}/add-point", response_model=RutaProgramacionResponse, status_code=201)
def add_point_to_route(
    route_id: int,
    data: AddPointToRouteRequest,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_permission('routes', 'write')),
):
    existing = db.query(RutaProgramacion).filter(
        RutaProgramacion.ruta_id == route_id,
        RutaProgramacion.punto_id == data.punto_id,
        RutaProgramacion.id_cliente == data.client_id,
    ).first()
    
    if existing:
        existing.activo = True
        existing.dia = data.dia
        existing.prioridad = data.priority
        db.commit()
        db.refresh(existing)
        return existing
        
    prog = RutaProgramacion(
        ruta_id=route_id,
        punto_id=data.punto_id,
        id_cliente=data.client_id,
        dia=data.dia,
        prioridad=data.priority,
        activo=True
    )
    db.add(prog)
    db.commit()
    db.refresh(prog)
    return prog


@router.post("/{route_id}/schedule-change", response_model=CambioFuturoResponse, status_code=201)
def schedule_route_change(
    route_id: int,
    data: ScheduleChangeRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission('routes', 'write')),
):
    ruta = db.query(Ruta).filter(Ruta.id == route_id).first()
    cambio = RutaCambioFuturo(
        ruta_id=route_id,
        ruta_nombre=ruta.nombre if ruta else None,
        id_programacion=data.id_programacion,
        id_punto_interes=data.id_punto_interes,
        punto_interes_nombre=data.punto_interes_nombre,
        id_cliente=data.id_cliente,
        cliente_nombre=data.cliente_nombre,
        dia=data.dia,
        prioridad=data.prioridad,
        tipo_cambio=data.tipo_cambio,
        fecha_ejecucion=data.fecha_ejecucion,
        observaciones=data.observaciones,
        creado_por=current_user.username,
        estado="PENDIENTE",
    )
    db.add(cambio)
    db.commit()
    db.refresh(cambio)
    return cambio


@router.get("/{route_id}/future-changes", response_model=List[CambioFuturoResponse])
def get_future_changes(
    route_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    return db.query(RutaCambioFuturo).filter(
        RutaCambioFuturo.ruta_id == route_id,
    ).order_by(RutaCambioFuturo.fecha_ejecucion.asc()).all()


@router.delete("/points/{programacion_id}", status_code=204)
def remove_point_from_route(
    programacion_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_permission('routes', 'delete')),
):
    prog = db.query(RutaProgramacion).filter(RutaProgramacion.id == programacion_id).first()
    if not prog:
        raise HTTPException(status_code=404, detail="Programación no encontrada")
    db.delete(prog)
    db.commit()
    return None


@router.patch("/points/{programacion_id}/active")
def set_point_active(
    programacion_id: int,
    activa: bool = Query(...),
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_permission('routes', 'write')),
):
    """Inactivar/activar un PDV de la ruta para ese día (RUTA_PROGRAMACION.activa)."""
    prog = db.query(RutaProgramacion).filter(RutaProgramacion.id == programacion_id).first()
    if not prog:
        raise HTTPException(status_code=404, detail="Programación no encontrada")
    prog.activo = activa
    db.commit()
    return {"id": programacion_id, "activa": activa}


@router.post("/{route_id}/bulk-apply")
def bulk_apply(
    route_id: int,
    data: BulkApplyRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission('routes', 'write')),
):
    """Aplica inserts + updates + deletes de programaciones en una sola operación
    (núcleo del Editor Masivo). Espejo de v1 bulk-apply."""
    ruta = db.query(Ruta).filter(Ruta.id == route_id).first()
    if not ruta:
        raise HTTPException(status_code=404, detail="Ruta no encontrada")

    if not data.inserts and not data.updates and not data.deletes:
        raise HTTPException(status_code=400, detail="No hay cambios para aplicar")

    inserted = updated = deleted = 0
    skipped: list = []

    # DELETES
    for d in data.deletes:
        db.query(RutaProgramacion).filter(
            RutaProgramacion.id == d.programacion_id,
            RutaProgramacion.ruta_id == route_id,
        ).delete(synchronize_session=False)
        deleted += 1

    # UPDATES
    for u in data.updates:
        prog = db.query(RutaProgramacion).filter(
            RutaProgramacion.id == u.programacion_id,
            RutaProgramacion.ruta_id == route_id,
        ).first()
        if prog:
            prog.dia = u.dia
            prog.prioridad = u.prioridad
            updated += 1

    # INSERTS (dedupe por ruta+punto+cliente+día)
    usuario = current_user.username
    for ins in data.inserts:
        exists = db.query(RutaProgramacion).filter(
            RutaProgramacion.ruta_id == route_id,
            RutaProgramacion.punto_id == ins.point_id,
            RutaProgramacion.id_cliente == ins.client_id,
            RutaProgramacion.dia == ins.dia,
        ).first()
        if exists:
            skipped.append({"point_id": ins.point_id, "dia": ins.dia, "reason": "Ya existe"})
            continue
        pname = db.query(PuntoInteres.nombre).filter(PuntoInteres.id == ins.point_id).scalar()
        db.add(RutaProgramacion(
            ruta_id=route_id,
            punto_id=ins.point_id,
            id_cliente=ins.client_id,
            dia=ins.dia,
            prioridad=ins.prioridad,
            activo=True,
            punto_interes_nombre=pname,
        ))
        inserted += 1

    db.commit()
    return {
        "success": True,
        "inserted": inserted,
        "updated": updated,
        "deleted": deleted,
        "skipped": skipped,
        "message": f"{inserted} agregado(s), {updated} actualizado(s), {deleted} eliminado(s), {len(skipped)} omitido(s)",
    }
