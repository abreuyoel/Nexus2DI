from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, delete as sa_delete
from typing import List
from pydantic import BaseModel
from app.db.session import get_async_db
from app.core.dependencies import get_current_user, require_analyst_or_admin
from app.models.user import Usuario
from app.models.mercaderista import Mercaderista, MercaderistaRuta
from app.models.ruta import Ruta
from collections import defaultdict

router = APIRouter(prefix="/api/mercaderista-rutas", tags=["Mercaderista Rutas"])


class RouteAssignment(BaseModel):
    ruta_id: int
    tipo_ruta: str = "Variable"


@router.get("")
@router.get("/")
async def list_mercaderistas_con_rutas(
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(get_current_user),
):
    try:
        users_vendedores = (await db.execute(select(Usuario).filter(Usuario.id_rol == 9, Usuario.activo == True))).scalars().all()
        synced = False
        for u in users_vendedores:
            cid = int(u.cedula) if u.cedula and str(u.cedula).isdigit() else (9000000 + u.id)
            existing = (await db.execute(select(Mercaderista).filter(Mercaderista.cedula == cid))).scalars().first()
            if not existing:
                db.add(Mercaderista(
                    nombre=u.username,
                    cedula=cid,
                    email=u.email,
                    tipo="Vendedor",
                    activo=True
                ))
                synced = True
        if synced:
            await db.commit()
    except Exception:
        await db.rollback()

    # Contar rutas por mercaderista
    rutas_counts_rows = (await db.execute(
        select(
            MercaderistaRuta.mercaderista_id.label("mercaderista_id"),
            func.count(MercaderistaRuta.id).label("rutas_count"),
        ).group_by(MercaderistaRuta.mercaderista_id)
    )).all()
    rutas_count_map = {row.mercaderista_id: row.rutas_count for row in rutas_counts_rows}

    mercs = (await db.execute(
        select(Mercaderista)
        .filter(Mercaderista.activo == True)
        .order_by(Mercaderista.nombre)
    )).scalars().all()

    # Nombres de ruta por mercaderista -- para poder buscar "quién tiene la
    # ruta X" desde el mismo cuadro de búsqueda del frontend, sin un N+1 de
    # una consulta por tarjeta.
    nombres_por_merc: dict[int, list[str]] = defaultdict(list)
    for mercaderista_id, ruta_nombre in (await db.execute(
        select(MercaderistaRuta.mercaderista_id, Ruta.nombre)
        .join(Ruta, Ruta.id == MercaderistaRuta.ruta_id)
    )).all():
        if ruta_nombre:
            nombres_por_merc[mercaderista_id].append(ruta_nombre)

    result = []
    for m in mercs:
        result.append({
            "id": m.id,
            "cedula": m.cedula,
            "nombre": m.nombre_completo,
            "email": m.email,
            "telefono": m.telefono,
            "tipo": m.tipo,
            "activo": m.activo,
            "rutas_count": rutas_count_map.get(m.id, 0),
            "rutas_nombres": nombres_por_merc.get(m.id, []),
        })
    return result


@router.get("/mercaderista/{mercaderista_id}/routes")
async def get_mercaderista_routes(
    mercaderista_id: int,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(get_current_user),
):
    mr_list = (await db.execute(
        select(MercaderistaRuta).filter(MercaderistaRuta.mercaderista_id == mercaderista_id)
    )).scalars().all()
    result = []
    for mr in mr_list:
        ruta = (await db.execute(select(Ruta).filter(Ruta.id == mr.ruta_id))).scalars().first()
        if ruta:
            result.append({
                "id": ruta.id,
                "nombre": ruta.nombre,
                "servicio": ruta.servicio,
                "activa": ruta.activa,
                "tipo_ruta": mr.tipo_ruta or "Variable",
            })
    return result


@router.post("/mercaderista/{mercaderista_id}/sync-routes")
async def sync_routes(
    mercaderista_id: int,
    assignments: List[RouteAssignment],
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_analyst_or_admin),
):
    merc = (await db.execute(select(Mercaderista).filter(Mercaderista.id == mercaderista_id))).scalars().first()
    if not merc:
        raise HTTPException(status_code=404, detail="Mercaderista no encontrado")

    await db.execute(sa_delete(MercaderistaRuta).where(MercaderistaRuta.mercaderista_id == mercaderista_id))

    for a in assignments:
        ruta = (await db.execute(select(Ruta).filter(Ruta.id == a.ruta_id))).scalars().first()
        if ruta:
            mr = MercaderistaRuta(
                mercaderista_id=mercaderista_id,
                ruta_id=a.ruta_id,
                tipo_ruta=a.tipo_ruta,
            )
            db.add(mr)

    await db.commit()
    return {"message": "Rutas sincronizadas correctamente"}


@router.post("/assign")
async def assign_route_to_mercaderista(
    mercaderista_id: int,
    ruta_id: int,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_analyst_or_admin),
):
    merc = (await db.execute(select(Mercaderista).filter(Mercaderista.id == mercaderista_id))).scalars().first()
    if not merc:
        raise HTTPException(status_code=404, detail="Mercaderista no encontrado")
    ruta = (await db.execute(select(Ruta).filter(Ruta.id == ruta_id))).scalars().first()
    if not ruta:
        raise HTTPException(status_code=404, detail="Ruta no encontrada")
    existing = (await db.execute(
        select(MercaderistaRuta).filter(
            MercaderistaRuta.mercaderista_id == mercaderista_id,
            MercaderistaRuta.ruta_id == ruta_id,
        )
    )).scalars().first()
    if existing:
        return {"message": "Asignación ya existe"}
    mr = MercaderistaRuta(mercaderista_id=mercaderista_id, ruta_id=ruta_id)
    db.add(mr)
    await db.commit()
    return {"message": "Ruta asignada exitosamente"}
