from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from typing import List, Optional
from datetime import date, datetime
from app.db.session import get_db, get_async_db
from app.core.dependencies import get_current_user, require_analyst_or_admin, require_permission
from app.services.realtime import notify_event
from app.models.user import Usuario, UserPermission
from app.models.ruta import Ruta, RutaProgramacion, RutaCambioFuturo, RutaActivada, AnalistaRuta
from app.models.catalogo import Servicio
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


async def _get_servicio_prefijo(db: AsyncSession, servicio_nombre: Optional[str]) -> str:
    """Prefijo de correlativo (ej. "E", "PR") configurado para ese servicio en
    el catálogo SERVICIOS -- reemplaza la whitelist hardcodeada E/A/T que
    tenía esta función antes, para poder agregar servicios nuevos (ej.
    Promovendedor -> "PR") sin tocar código."""
    if not servicio_nombre:
        raise HTTPException(status_code=400, detail="Servicio es requerido")
    serv = (await db.execute(select(Servicio).filter(Servicio.nombre == servicio_nombre))).scalars().first()
    if not serv:
        raise HTTPException(status_code=400, detail=f"El servicio '{servicio_nombre}' no existe en el catálogo")
    if not serv.prefijo:
        raise HTTPException(
            status_code=400,
            detail=f"El servicio '{servicio_nombre}' no tiene un prefijo configurado para numerar rutas -- configuralo en Gestión de Rutas → Servicios",
        )
    return serv.prefijo


async def _next_route_number(db: AsyncSession, prefijo: str) -> int:
    """Mayor sufijo numérico existente para 'Ruta {prefijo}' + 1."""
    prefix = f"Ruta {prefijo}"
    routes = (await db.execute(select(Ruta.nombre).filter(Ruta.nombre.like(f"{prefix}%")))).scalars().all()
    max_num = 0
    for (nombre,) in routes:
        if nombre:
            suffix = nombre[len(prefix):]
            if suffix.isdigit():
                max_num = max(max_num, int(suffix))
    return max_num + 1


@router.get("/next-number")
async def get_next_route_number(servicio: str, db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(get_current_user)):
    prefijo = await _get_servicio_prefijo(db, servicio)
    return {"next_number": await _next_route_number(db, prefijo), "prefijo": prefijo}


@router.get("/options")
async def get_route_options(db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(get_current_user)):
    servicios = (await db.execute(select(Ruta.servicio).distinct().filter(Ruta.servicio != None))).scalars().all()
    return {"servicios": [s[0] for s in servicios]}


async def _enrich_routes(db: AsyncSession, rutas: List[Ruta]) -> List[dict]:
    """Agrega por ruta: puntos_count, clientes (distintos), region y cliente exclusivo."""
    ruta_ids = [r.id for r in rutas]
    if not ruta_ids:
        return []

    counts = dict(
        (await db.execute(
            select(RutaProgramacion.ruta_id, func.count(RutaProgramacion.id))
            .filter(RutaProgramacion.ruta_id.in_(ruta_ids), RutaProgramacion.activo == True)
            .group_by(RutaProgramacion.ruta_id)
        )).all()
    )

    pair_rows = (
        (await db.execute(
            select(RutaProgramacion.ruta_id, RutaProgramacion.id_cliente)
            .filter(
                RutaProgramacion.ruta_id.in_(ruta_ids),
                RutaProgramacion.activo == True,
                RutaProgramacion.id_cliente.isnot(None),
            )
            .distinct()
        )).all()
    )

    unique_cids = list({cid for _, cid in pair_rows if cid is not None})
    client_map = (
        dict((await db.execute(select(Cliente.id, Cliente.nombre).filter(Cliente.id.in_(unique_cids)))).all())
        if unique_cids else {}
    )

    clientes_map: dict[int, set] = {}
    for rid, cid in pair_rows:
        cname = client_map.get(cid)
        if cname:
            clientes_map.setdefault(rid, set()).add(cname)

    excl_ids = [r.id_cliente_exclusivo for r in rutas if r.id_cliente_exclusivo]
    excl_map = (
        dict((await db.execute(select(Cliente.id, Cliente.nombre).filter(Cliente.id.in_(excl_ids)))).all())
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


@router.get("", response_model=List[RutaResponse])
@router.get("/", response_model=List[RutaResponse])
async def list_routes(
    activa: Optional[bool] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(get_current_user),
):
    query = select(Ruta)

    # Granular Visibility Logic
    if not current_user.is_admin:
        # Check if they have 'can_see_all' permission for routes
        perm = next((p for p in current_user.permisos if p.module == 'rutas'), None)
        can_see_all = perm.can_see_all if perm else False

        if not can_see_all and current_user.is_analyst:
            # Only see routes where they are assigned in analistas_rutas
            query = query.join(Ruta.analistas).filter(AnalistaRuta.id_analista == current_user.id_perfil)

    rutas = (await db.execute(query.order_by(Ruta.nombre))).scalars().all()
    return await _enrich_routes(db, rutas)


@router.get("/my-routes", response_model=List[RutaResponse])
async def my_routes(
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Retorna las rutas asignadas al usuario logueado según su rol (analista / supervisor / admin)."""
    if current_user.is_admin:
        rutas = (await db.execute(select(Ruta).order_by(Ruta.nombre))).scalars().all()
        return await _enrich_routes(db, rutas)

    if current_user.is_analyst and current_user.id_perfil:
        rutas = (
            await db.execute(
                select(Ruta)
                .join(Ruta.analistas)
                .filter(AnalistaRuta.id_analista == current_user.id_perfil)
                .order_by(Ruta.nombre)
            )
        ).scalars().all()
        return await _enrich_routes(db, rutas)

    return []


@router.post("", response_model=RutaResponse, status_code=201)
@router.post("/", response_model=RutaResponse, status_code=201)
async def create_route(
    data: RutaCreate,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_permission('routes', 'write')),
):
    prefijo = await _get_servicio_prefijo(db, data.servicio)
    if data.servicio == "Exclusivo" and not data.id_cliente_exclusivo:
        raise HTTPException(status_code=400, detail="Cliente exclusivo es requerido para rutas de servicio Exclusivo")

    route_name = f"Ruta {prefijo}{await _next_route_number(db, prefijo)}"

    db_data = data.model_dump()
    db_data["nombre"] = route_name
    # id_analista no es columna de RUTAS_NUEVAS -- vive en la tabla
    # intermedia analistas_rutas (modelo AnalistaRuta). Pasarlo directo a
    # Ruta(**db_data) rompía con 500 la creación de CUALQUIER ruta, tuviera
    # o no analista asignado (el constructor de SQLAlchemy rechaza kwargs
    # que no son columnas mapeadas).
    id_analista = db_data.pop("id_analista", None)
    # El cliente exclusivo sólo aplica al servicio Exclusivo
    if data.servicio != "Exclusivo":
        db_data["id_cliente_exclusivo"] = None

    ruta = Ruta(**db_data)
    db.add(ruta)
    db.flush()
    if id_analista is not None:
        db.add(AnalistaRuta(id_analista=id_analista, id_ruta=ruta.id))
    await db.commit()
    await db.refresh(ruta)
    notify_event("route.created", {"id": ruta.id, "nombre": ruta.nombre})
    return (await _enrich_routes(db, [ruta]))[0]


@router.get("/activated/today")
async def get_activated_routes_today(
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(get_current_user),
):
    activadas = (await db.execute(select(RutaActivada))).scalars().all()
    return [{"ruta_id": a.ruta_id, "mercaderista_id": a.mercaderista_id} for a in activadas]


@router.get("/{route_id}", response_model=RutaResponse)
async def get_route(route_id: int, db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(get_current_user)):
    ruta = (await db.execute(select(Ruta).filter(Ruta.id == route_id))).scalars().first()
    if not ruta:
        raise HTTPException(status_code=404, detail="Ruta no encontrada")
    return ruta


@router.patch("/{route_id}", response_model=RutaResponse)
async def update_route(
    route_id: int,
    data: RutaUpdate,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_permission('routes', 'write')),
):
    ruta = (await db.execute(select(Ruta).filter(Ruta.id == route_id))).scalars().first()
    if not ruta:
        raise HTTPException(status_code=404, detail="Ruta no encontrada")
    updates = data.model_dump(exclude_none=True)
    # Igual que en create_route: id_analista no es columna de Ruta, así que
    # setattr(ruta, "id_analista", ...) no rompía pero tampoco guardaba nada
    # -- se maneja aparte contra la tabla intermedia analistas_rutas.
    id_analista = updates.pop("id_analista", None)
    for key, value in updates.items():
        setattr(ruta, key, value)
    if id_analista is not None:
        existente = (await db.execute(select(AnalistaRuta).filter(AnalistaRuta.id_ruta == route_id))).scalars().first()
        if not existente:
            db.add(AnalistaRuta(id_analista=id_analista, id_ruta=route_id))
        elif existente.id_analista != id_analista:
            db.delete(existente)
            db.flush()
            db.add(AnalistaRuta(id_analista=id_analista, id_ruta=route_id))
    await db.commit()
    await db.refresh(ruta)
    notify_event("route.updated", {"id": ruta.id, "nombre": ruta.nombre})
    return (await _enrich_routes(db, [ruta]))[0]


@router.delete("/{route_id}", status_code=204)
async def delete_route(
    route_id: int,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_permission('routes', 'delete')),
):
    ruta = (await db.execute(select(Ruta).filter(Ruta.id == route_id))).scalars().first()
    if not ruta:
        raise HTTPException(status_code=404, detail="Ruta no encontrada")
    # Eliminar dependencias sin cascade configurado (asignaciones/activaciones)
    await db.execute(delete(MercaderistaRuta).where(MercaderistaRuta.ruta_id == route_id))
    await db.execute(delete(AnalistaRuta).where(AnalistaRuta.id_ruta == route_id))
    await db.execute(delete(RutaActivada).where(RutaActivada.ruta_id == route_id))
    # programaciones y cambios_futuros caen por cascade en la relación
    db.delete(ruta)
    await db.commit()
    notify_event("route.deleted", {"id": route_id})
    return None


@router.post("/{route_id}/duplicate", response_model=RutaResponse, status_code=201)
async def duplicate_route(
    route_id: int,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_permission('routes', 'write')),
):
    orig = (await db.execute(select(Ruta).filter(Ruta.id == route_id))).scalars().first()
    if not orig:
        raise HTTPException(status_code=404, detail="Ruta no encontrada")

    # Mismo prefijo que el servicio de la ruta original (antes se intentaba
    # adivinar parseando la letra tras "Ruta " del nombre, que no siempre
    # coincidía con el servicio real de la ruta).
    prefijo = await _get_servicio_prefijo(db, orig.servicio)
    new_name = f"Ruta {prefijo}{await _next_route_number(db, prefijo)}"

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

    await db.commit()
    await db.refresh(nueva)
    notify_event("route.created", {"id": nueva.id, "nombre": nueva.nombre})
    return (await _enrich_routes(db, [nueva]))[0]


@router.get("/{route_id}/points", response_model=List[RutaProgramacionResponse])
async def get_route_points(
    route_id: int,
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(get_current_user),
):
    q = select(RutaProgramacion).options(
        joinedload(RutaProgramacion.punto),
        joinedload(RutaProgramacion.cliente)
    ).filter(RutaProgramacion.ruta_id == route_id)
    if not include_inactive:
        q = q.filter(RutaProgramacion.activo == True)
    return (await db.execute(q)).scalars().all()


@router.post("/{route_id}/add-point", response_model=RutaProgramacionResponse, status_code=201)
async def add_point_to_route(
    route_id: int,
    data: AddPointToRouteRequest,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_permission('routes', 'write')),
):
    existing = (await db.execute(select(RutaProgramacion).filter(
        RutaProgramacion.ruta_id == route_id,
        RutaProgramacion.punto_id == data.punto_id,
        RutaProgramacion.id_cliente == data.client_id,
    ))).scalars().first()
    
    if existing:
        existing.activo = True
        existing.dia = data.dia
        existing.prioridad = data.priority
        await db.commit()
        await db.refresh(existing)
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
    await db.commit()
    await db.refresh(prog)
    return prog


@router.post("/{route_id}/schedule-change", response_model=CambioFuturoResponse, status_code=201)
async def schedule_route_change(
    route_id: int,
    data: ScheduleChangeRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_permission('routes', 'write')),
):
    ruta = (await db.execute(select(Ruta).filter(Ruta.id == route_id))).scalars().first()
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
    await db.commit()
    await db.refresh(cambio)
    return cambio


@router.get("/{route_id}/future-changes", response_model=List[CambioFuturoResponse])
async def get_future_changes(
    route_id: int,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(get_current_user),
):
    return (await db.execute(
        select(RutaCambioFuturo)
        .filter(RutaCambioFuturo.ruta_id == route_id)
        .order_by(RutaCambioFuturo.fecha_ejecucion.asc())
    )).scalars().all()


@router.delete("/points/{programacion_id}", status_code=204)
async def remove_point_from_route(
    programacion_id: int,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_permission('routes', 'delete')),
):
    prog = (await db.execute(select(RutaProgramacion).filter(RutaProgramacion.id == programacion_id))).scalars().first()
    if not prog:
        raise HTTPException(status_code=404, detail="Programación no encontrada")
    db.delete(prog)
    await db.commit()
    return None


@router.patch("/points/{programacion_id}/active")
async def set_point_active(
    programacion_id: int,
    activa: bool = Query(...),
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_permission('routes', 'write')),
):
    """Inactivar/activar un PDV de la ruta para ese día (RUTA_PROGRAMACION.activa)."""
    prog = (await db.execute(select(RutaProgramacion).filter(RutaProgramacion.id == programacion_id))).scalars().first()
    if not prog:
        raise HTTPException(status_code=404, detail="Programación no encontrada")
    prog.activo = activa
    await db.commit()
    return {"id": programacion_id, "activa": activa}


@router.post("/{route_id}/bulk-apply")
async def bulk_apply(
    route_id: int,
    data: BulkApplyRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_permission('routes', 'write')),
):
    """Aplica inserts + updates + deletes de programaciones en una sola operación
    (núcleo del Editor Masivo). Espejo de v1 bulk-apply."""
    ruta = (await db.execute(select(Ruta).filter(Ruta.id == route_id))).scalars().first()
    if not ruta:
        raise HTTPException(status_code=404, detail="Ruta no encontrada")

    if not data.inserts and not data.updates and not data.deletes:
        raise HTTPException(status_code=400, detail="No hay cambios para aplicar")

    inserted = updated = deleted = 0
    skipped: list = []

    # DELETES
    for d in data.deletes:
        await db.execute(
            delete(RutaProgramacion).where(
                RutaProgramacion.id == d.programacion_id,
                RutaProgramacion.ruta_id == route_id,
            )
        )
        deleted += 1

    # UPDATES
    for u in data.updates:
        prog = (await db.execute(select(RutaProgramacion).filter(
            RutaProgramacion.id == u.programacion_id,
            RutaProgramacion.ruta_id == route_id,
        ))).scalars().first()
        if prog:
            prog.dia = u.dia
            prog.prioridad = u.prioridad
            updated += 1

    # INSERTS (dedupe por ruta+punto+cliente+día)
    usuario = current_user.username
    for ins in data.inserts:
        exists = (await db.execute(select(RutaProgramacion).filter(
            RutaProgramacion.ruta_id == route_id,
            RutaProgramacion.punto_id == ins.point_id,
            RutaProgramacion.id_cliente == ins.client_id,
            RutaProgramacion.dia == ins.dia,
        ))).scalars().first()
        if exists:
            skipped.append({"point_id": ins.point_id, "dia": ins.dia, "reason": "Ya existe"})
            continue
        pname = (await db.execute(select(PuntoInteres.nombre).filter(PuntoInteres.id == ins.point_id))).scalar()
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

    await db.commit()
    return {
        "success": True,
        "inserted": inserted,
        "updated": updated,
        "deleted": deleted,
        "skipped": skipped,
        "message": f"{inserted} agregado(s), {updated} actualizado(s), {deleted} eliminado(s), {len(skipped)} omitido(s)",
    }
