from sqlalchemy import select, update, func
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Type
from app.db.session import get_db, get_async_db
from app.core.dependencies import get_current_user, require_analyst_or_admin, require_permission
from app.models.user import Usuario
from app.models.punto import PuntoInteres
from app.services.audit_service import log_action
from app.core.request_ip import get_client_ip
from app.models.ruta import Ruta
from app.models.catalogo import (
    TipoNegocio, SubtipoNegocio, Alcance, CanalVenta, DepartamentoGeo, Ciudad,
    Cuadrante, Servicio,
)
from app.schemas.catalogo import (
    CatalogoCreate, CatalogoUpdate, CatalogoResponse,
    CiudadCreate, CiudadUpdate, CiudadResponse,
    ServicioCreate, ServicioUpdate, ServicioResponse,
)

router = APIRouter(prefix="/api/catalogos", tags=["Catálogos"])


# Mapping: catalog_key → (usage_model, usage_column, sample_column)
# usage_model/usage_column = dónde se referencia el valor (para validar borrado/rename).
# sample_column = columna a mostrar como ejemplo de registros que lo usan.
# "servicios" NO va acá -- tiene endpoints dedicados (necesita el campo extra
# "prefijo" que el genérico no soporta), ver más abajo.
CATALOG_USAGE = {
    "tipo-negocio": (PuntoInteres, PuntoInteres.jerarquia_n2, PuntoInteres.id),
    "subtipo-negocio": (PuntoInteres, PuntoInteres.jerarquia_n2_2, PuntoInteres.id),
    "alcance": (PuntoInteres, PuntoInteres.nivel_de_alcance, PuntoInteres.id),
    "canal-venta": (PuntoInteres, PuntoInteres.cadena, PuntoInteres.id),
    "departamentos": (PuntoInteres, PuntoInteres.departamento, PuntoInteres.id),
    "cuadrantes": (Ruta, Ruta.cuadrante, Ruta.nombre),
}


async def _count_usage(db: AsyncSession, usage_model, usage_column, value: str) -> int:
    return (await db.execute(select(func.count()).select_from(usage_model).filter(usage_column == value))).scalar() or 0


async def _list_usage_ids(db: AsyncSession, usage_column, sample_column, value: str, limit: int = 5) -> list[str]:
    if sample_column == PuntoInteres.id:
        stmt = select(PuntoInteres.id, PuntoInteres.nombre).filter(usage_column == value).limit(limit)
        rows = (await db.execute(stmt)).all()
        result = []
        for r in rows:
            pdv_id, pdv_nombre = r[0], r[1]
            if pdv_nombre:
                result.append(f"{pdv_nombre} (ID: {pdv_id})")
            else:
                result.append(f"ID: {pdv_id}")
        return result
    else:
        rows = (await db.execute(select(sample_column).filter(usage_column == value).limit(limit))).scalars().all()
        return [str(r) for r in rows if r]


def _ciudad_to_response(c: Ciudad) -> dict:
    return {
        "id": c.id,
        "nombre": c.nombre,
        "activo": c.activo,
        "departamento_id": c.departamento_id,
        "departamento_nombre": c.departamento_geo.nombre if c.departamento_geo else None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Ciudades — registradas ANTES del genérico para que /ciudades/ no colisione
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/ciudades", response_model=List[CiudadResponse])
@router.get("/ciudades/", response_model=List[CiudadResponse])
async def list_ciudades(
    departamento_id: Optional[int] = None,
    departamento: Optional[str] = None,
    activo: Optional[bool] = None,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(get_current_user),
):
    q = select(Ciudad).join(DepartamentoGeo, Ciudad.departamento_id == DepartamentoGeo.id)
    if departamento_id is not None:
        q = q.filter(Ciudad.departamento_id == departamento_id)
    if departamento:
        q = q.filter(DepartamentoGeo.nombre == departamento)
    if activo is not None:
        q = q.filter(Ciudad.activo == activo)
    rows = (await db.execute(q.order_by(Ciudad.nombre))).scalars().all()
    return [_ciudad_to_response(c) for c in rows]


@router.post("/ciudades", response_model=CiudadResponse, status_code=201)
@router.post("/ciudades/", response_model=CiudadResponse, status_code=201)
async def create_ciudad(
    data: CiudadCreate,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_permission('points', 'write')),
):
    dep = (await db.execute(select(DepartamentoGeo).filter(DepartamentoGeo.id == data.departamento_id))).scalars().first()
    if not dep:
        raise HTTPException(status_code=404, detail="Departamento no existe")
    nombre = data.nombre.strip()
    exists = (await db.execute(select(Ciudad).filter(
        Ciudad.departamento_id == data.departamento_id,
        Ciudad.nombre == nombre,
    ))).scalars().first()
    if exists:
        raise HTTPException(status_code=409, detail=f"Ya existe '{nombre}' en {dep.nombre}")
    c = Ciudad(nombre=nombre, departamento_id=data.departamento_id, activo=data.activo)
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return _ciudad_to_response(c)


@router.put("/ciudades/{ciudad_id}", response_model=CiudadResponse)
async def update_ciudad(
    ciudad_id: int,
    data: CiudadUpdate,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_permission('points', 'write')),
):
    c = (await db.execute(select(Ciudad).filter(Ciudad.id == ciudad_id))).scalars().first()
    if not c:
        raise HTTPException(status_code=404, detail="Ciudad no encontrada")

    old_nombre = c.nombre
    nuevo_nombre = data.nombre.strip() if data.nombre is not None else old_nombre
    nuevo_dep_id = data.departamento_id if data.departamento_id is not None else c.departamento_id

    if nuevo_dep_id != c.departamento_id:
        dep = (await db.execute(select(DepartamentoGeo).filter(DepartamentoGeo.id == nuevo_dep_id))).scalars().first()
        if not dep:
            raise HTTPException(status_code=404, detail="Departamento no existe")

    if nuevo_nombre != old_nombre or nuevo_dep_id != c.departamento_id:
        clash = (await db.execute(select(Ciudad).filter(
            Ciudad.departamento_id == nuevo_dep_id,
            Ciudad.nombre == nuevo_nombre,
            Ciudad.id != ciudad_id,
        ))).scalars().first()
        if clash:
            raise HTTPException(status_code=409, detail="Ya existe esa ciudad en el departamento")

    if nuevo_nombre != old_nombre:
        await db.execute(
            update(PuntoInteres).where(PuntoInteres.ciudad == old_nombre).values(ciudad=nuevo_nombre)
        )

    c.nombre = nuevo_nombre
    c.departamento_id = nuevo_dep_id
    if data.activo is not None:
        c.activo = data.activo

    await db.commit()
    await db.refresh(c)
    return _ciudad_to_response(c)


@router.delete("/ciudades/{ciudad_id}")
async def delete_ciudad(
    ciudad_id: int,
    force: bool = Query(False),
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_permission('points', 'delete')),
):
    c = (await db.execute(select(Ciudad).filter(Ciudad.id == ciudad_id))).scalars().first()
    if not c:
        raise HTTPException(status_code=404, detail="Ciudad no encontrada")

    usage = await _count_usage(db, PuntoInteres, PuntoInteres.ciudad, c.nombre)
    if usage > 0 and not force:
        sample = await _list_usage_ids(db, PuntoInteres.ciudad, PuntoInteres.id, c.nombre)
        raise HTTPException(
            status_code=409,
            detail={
                "message": f"No se puede eliminar '{c.nombre}' porque está siendo usada por {usage} punto(s) de venta. Inactive o elimine esos PDV primero, o use ?force=true.",
                "usage_count": usage,
                "sample_pdv_ids": sample,
            },
        )

    await db.delete(c)
    await db.commit()
    return {"message": "Eliminada", "usage_count": usage, "force": force}


# ─────────────────────────────────────────────────────────────────────────────
# Servicios — registrados ANTES del genérico (necesita el campo extra "prefijo",
# la sigla que arma el correlativo de nombre de ruta, ver routes/rutas.py)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/servicios", response_model=List[ServicioResponse])
@router.get("/servicios/", response_model=List[ServicioResponse])
async def list_servicios(
    activo: Optional[bool] = None,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(get_current_user),
):
    q = select(Servicio)
    if activo is not None:
        q = q.filter(Servicio.activo == activo)
    return (await db.execute(q.order_by(Servicio.nombre))).scalars().all()


@router.post("/servicios", response_model=ServicioResponse, status_code=201)
@router.post("/servicios/", response_model=ServicioResponse, status_code=201)
async def create_servicio(
    data: ServicioCreate,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_permission('points', 'write')),
):
    nombre = data.nombre.strip()
    prefijo = data.prefijo.strip().upper()
    if (await db.execute(select(Servicio).filter(Servicio.nombre == nombre))).scalars().first():
        raise HTTPException(status_code=409, detail=f"Ya existe '{nombre}'")
    if (await db.execute(select(Servicio).filter(Servicio.prefijo == prefijo))).scalars().first():
        raise HTTPException(status_code=409, detail=f"El prefijo '{prefijo}' ya lo usa otro servicio -- las rutas se numerarían mezcladas")
    item = Servicio(nombre=nombre, prefijo=prefijo, activo=data.activo)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.put("/servicios/{item_id}", response_model=ServicioResponse)
async def update_servicio(
    item_id: int,
    data: ServicioUpdate,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_permission('points', 'write')),
):
    item = (await db.execute(select(Servicio).filter(Servicio.id == item_id))).scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="No encontrado")

    old_nombre = item.nombre
    nuevo_nombre = data.nombre.strip() if data.nombre is not None else old_nombre
    nuevo_prefijo = data.prefijo.strip().upper() if data.prefijo is not None else item.prefijo

    if nuevo_nombre != old_nombre:
        clash = (await db.execute(select(Servicio).filter(Servicio.nombre == nuevo_nombre, Servicio.id != item_id))).scalars().first()
        if clash:
            raise HTTPException(status_code=409, detail=f"Ya existe '{nuevo_nombre}'")

    if nuevo_prefijo != item.prefijo:
        clash = (await db.execute(select(Servicio).filter(Servicio.prefijo == nuevo_prefijo, Servicio.id != item_id))).scalars().first()
        if clash:
            raise HTTPException(status_code=409, detail=f"El prefijo '{nuevo_prefijo}' ya lo usa otro servicio")

    if nuevo_nombre != old_nombre:
        await db.execute(
            update(Ruta).where(Ruta.servicio == old_nombre).values(servicio=nuevo_nombre)
        )

    item.nombre = nuevo_nombre
    item.prefijo = nuevo_prefijo
    if data.activo is not None:
        item.activo = data.activo

    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/servicios/{item_id}")
async def delete_servicio(
    item_id: int,
    force: bool = Query(False),
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_permission('points', 'delete')),
):
    item = (await db.execute(select(Servicio).filter(Servicio.id == item_id))).scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="No encontrado")

    usage = await _count_usage(db, Ruta, Ruta.servicio, item.nombre)
    if usage > 0 and not force:
        sample = await _list_usage_ids(db, Ruta.servicio, Ruta.nombre, item.nombre)
        raise HTTPException(
            status_code=409,
            detail={
                "message": f"No se puede eliminar el servicio '{item.nombre}' porque está asignado a {usage} ruta(s). Reasigne o elimine esas rutas primero, o use ?force=true.",
                "usage_count": usage,
                "sample_route_names": sample,
            },
        )

    await db.delete(item)
    await db.commit()
    return {"message": "Eliminado", "usage_count": usage, "force": force}


# ─────────────────────────────────────────────────────────────────────────────
# Estados - registrados antes del genérico
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/estados", response_model=List[CatalogoResponse])
async def get_estados(db: AsyncSession = Depends(get_async_db), current_user: Usuario = Depends(get_current_user)):
    from app.models.catalogo import Estado
    estados = (await db.execute(select(Estado).order_by(Estado.nombre))).scalars().all()
    if not estados:
        departamentos = (await db.execute(select(DepartamentoGeo).filter(DepartamentoGeo.activo == True))).scalars().all()
        for dep in departamentos:
            nuevo = Estado(nombre=dep.nombre, activo=True)
            db.add(nuevo)
        await db.commit()
        estados = (await db.execute(select(Estado).order_by(Estado.nombre))).scalars().all()
        
    return estados


# ─────────────────────────────────────────────────────────────────────────────
# Catálogos genéricos: tipo-negocio, subtipo-negocio, alcance, canal-venta,
# departamentos. Usa columna correspondiente de PuntoInteres para validar uso.
# ─────────────────────────────────────────────────────────────────────────────

GENERIC_CATALOGS: dict[str, Type] = {
    "tipo-negocio": TipoNegocio,
    "subtipo-negocio": SubtipoNegocio,
    "alcance": Alcance,
    "canal-venta": CanalVenta,
    "departamentos": DepartamentoGeo,
    "cuadrantes": Cuadrante,
}


def _resolve_generic(catalog: str) -> Type:
    if catalog not in GENERIC_CATALOGS:
        raise HTTPException(status_code=404, detail=f"Catálogo '{catalog}' no existe")
    return GENERIC_CATALOGS[catalog]


@router.get("/{catalog}", response_model=List[CatalogoResponse])
@router.get("/{catalog}/", response_model=List[CatalogoResponse])
async def list_catalog(
    catalog: str,
    activo: Optional[bool] = None,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(get_current_user),
):
    Model = _resolve_generic(catalog)
    q = select(Model)
    if activo is not None:
        q = q.filter(Model.activo == activo)
    return (await db.execute(q.order_by(Model.nombre))).scalars().all()


@router.post("/{catalog}", response_model=CatalogoResponse, status_code=201)
@router.post("/{catalog}/", response_model=CatalogoResponse, status_code=201)
async def create_catalog_item(
    catalog: str,
    data: CatalogoCreate,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_permission('points', 'write')),
):
    Model = _resolve_generic(catalog)
    nombre = data.nombre.strip()
    if (await db.execute(select(Model).filter(Model.nombre == nombre))).scalars().first():
        raise HTTPException(status_code=409, detail=f"Ya existe '{nombre}'")
    item = Model(nombre=nombre, activo=data.activo)
    db.add(item)
    await db.flush()

    log_action(
        db,
        action="CREATE_CATALOG_ITEM",
        entity_type="PuntoInteres",
        user_id=current_user.id,
        username=current_user.username,
        rol=current_user.rol,
        ip_address=get_client_ip(request),
        entity_id=str(item.id),
        entity_name=f"Catálogo {catalog}: {nombre}",
        changes={"before": None, "after": {"id": item.id, "nombre": nombre, "catalog": catalog}},
    )

    await db.commit()
    await db.refresh(item)
    return item


@router.put("/{catalog}/{item_id}", response_model=CatalogoResponse)
async def update_catalog_item(
    catalog: str,
    item_id: int,
    data: CatalogoUpdate,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_permission('points', 'write')),
):
    Model = _resolve_generic(catalog)
    item = (await db.execute(select(Model).filter(Model.id == item_id))).scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="No encontrado")

    old_nombre = item.nombre
    before_dict = {"id": item.id, "nombre": old_nombre, "activo": item.activo, "catalog": catalog}

    if data.nombre is not None:
        nuevo = data.nombre.strip()
        if nuevo != old_nombre:
            if (await db.execute(select(Model).filter(Model.nombre == nuevo))).scalars().first():
                raise HTTPException(status_code=409, detail=f"Ya existe '{nuevo}'")
            usage_model, usage_column, _sample = CATALOG_USAGE[catalog]
            await db.execute(
                update(usage_model).where(usage_column == old_nombre).values({usage_column: nuevo})
            )
            item.nombre = nuevo

    if data.activo is not None:
        item.activo = data.activo

    after_dict = {"id": item.id, "nombre": item.nombre, "activo": item.activo, "catalog": catalog}
    log_action(
        db,
        action="UPDATE_CATALOG_ITEM",
        entity_type="PuntoInteres",
        user_id=current_user.id,
        username=current_user.username,
        rol=current_user.rol,
        ip_address=get_client_ip(request),
        entity_id=str(item_id),
        entity_name=f"Catálogo {catalog}: {item.nombre}",
        changes={"before": before_dict, "after": after_dict},
    )

    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/{catalog}/{item_id}")
async def delete_catalog_item(
    catalog: str,
    item_id: int,
    request: Request,
    force: bool = Query(False, description="Si true, elimina aunque hayan PDV referenciados"),
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_permission('points', 'delete')),
):
    Model = _resolve_generic(catalog)
    item = (await db.execute(select(Model).filter(Model.id == item_id))).scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="No encontrado")

    usage_model, usage_column, sample_column = CATALOG_USAGE[catalog]
    usage = await _count_usage(db, usage_model, usage_column, item.nombre)
    if usage > 0 and not force:
        sample = await _list_usage_ids(db, usage_column, sample_column, item.nombre)
        unidad = "ruta(s)" if usage_model is Ruta else "punto(s) de venta"
        raise HTTPException(
            status_code=409,
            detail={
                "message": f"No se puede eliminar '{item.nombre}' porque está siendo usado por {usage} {unidad}. Reasigne o elimine esos registros primero, o use ?force=true para eliminar de todos modos (quedarán sin este valor).",
                "usage_count": usage,
                "sample_pdv_ids": sample,
            },
        )

    affected_pdv_ids = []
    if usage_model is PuntoInteres and item.nombre:
        try:
            rows = (await db.execute(select(PuntoInteres.id).filter(usage_column == item.nombre))).scalars().all()
            affected_pdv_ids = [str(r) for r in rows if r]
        except Exception:
            affected_pdv_ids = []

    if force:
        from sqlalchemy import text
        try:
            if catalog == "tipo-negocio":
                await db.execute(text("DELETE FROM HORAS_PROMEDIO_EJECUCION WHERE id_tipo_negocio = :iid"), {"iid": item_id})
                await db.execute(text("UPDATE PUNTOS_INTERES1 SET jerarquia_n2 = NULL WHERE jerarquia_n2 = :name"), {"name": item.nombre})
            elif catalog == "subtipo-negocio":
                await db.execute(text("UPDATE PUNTOS_INTERES1 SET jerarquia_n2_2 = NULL WHERE jerarquia_n2_2 = :name"), {"name": item.nombre})
            elif catalog == "alcance":
                await db.execute(text("UPDATE PUNTOS_INTERES1 SET nivel_de_alcance = NULL WHERE nivel_de_alcance = :name"), {"name": item.nombre})
            elif catalog == "canal-venta":
                await db.execute(text("UPDATE PUNTOS_INTERES1 SET cadena = NULL WHERE cadena = :name"), {"name": item.nombre})
            elif catalog == "departamentos":
                await db.execute(text("UPDATE PUNTOS_INTERES1 SET departamento = NULL WHERE departamento = :name"), {"name": item.nombre})
        except Exception:
            pass

    item_nombre = item.nombre
    before_state = {
        "id": item_id,
        "nombre": item_nombre,
        "catalog": catalog,
        "activo": item.activo,
        "affected_pdv_ids": affected_pdv_ids
    }

    try:
        await db.delete(item)
        log_action(
            db,
            action="DELETE_CATALOG_ITEM",
            entity_type="PuntoInteres",
            user_id=current_user.id,
            username=current_user.username,
            rol=current_user.rol,
            ip_address=get_client_ip(request),
            entity_id=str(item_id),
            entity_name=f"Catálogo {catalog}: {item_nombre}",
            changes={"before": before_state, "after": None},
            status="APPROVED" if force else "OK"
        )
        await db.commit()
        return {"message": "Eliminado exitosamente", "usage_count": usage, "force": force}
    except Exception as ex:
        import logging
        logging.getLogger("app.routes.catalogos").warning(f"Hard delete para '{item_nombre}' (id={item_id}) bloqueado por restricciones SQL Server, aplicando inactivación (soft-delete): {ex}")
        await db.rollback()
        item = (await db.execute(select(Model).filter(Model.id == item_id))).scalars().first()
        if item and hasattr(item, "activo"):
            item.activo = False
            log_action(
                db,
                action="DELETE_CATALOG_ITEM",
                entity_type="PuntoInteres",
                user_id=current_user.id,
                username=current_user.username,
                rol=current_user.rol,
                ip_address=get_client_ip(request),
                entity_id=str(item_id),
                entity_name=f"Catálogo {catalog}: {item_nombre}",
                changes={"before": before_state, "after": {"id": item_id, "nombre": item_nombre, "catalog": catalog, "activo": False}},
                status="DEACTIVATED"
            )
            await db.commit()
            return {"message": "Ítem desactivado correctamente (vinculado a registros del sistema)", "usage_count": usage, "force": force}
        else:
            raise HTTPException(
                status_code=400,
                detail="Este catálogo está vinculado a registros históricos en la base de datos. Se ha marcado como inactivo."
            )
