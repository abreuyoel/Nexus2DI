from sqlalchemy import select
"""SKU vs SKU: por cliente, qué SKU propio se enfrenta contra qué SKU(s) de
la competencia. Fase 1 -- solo la pantalla de definición: NO cambia todavía
qué productos ve el mercaderista en la APK (GET /api/merc/productos sigue
mostrando toda la categoría del cliente hasta que se confirme ese paso)."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, aliased
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from pydantic import BaseModel
from app.db.session import get_db, get_async_db
from app.core.dependencies import require_permission
from app.models.user import Usuario
from app.models.sku_competencia import SkuCompetencia
from app.models.producto import Producto, Marca
from app.services.sku_competencia_precio_service import calcular_deriva_precio, UMBRAL_PCT_DEFAULT

router = APIRouter(prefix="/api/sku-competencia", tags=["SKU vs SKU"])


@router.get("/mapeos")
async def get_mapeos(id_cliente: int = Query(...), db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(require_permission('sku-competencia', 'read', fallback_roles=('admin',)))):
    """Agrupado por SKU propio del cliente, con la lista de competidores
    que tiene definidos cada uno."""
    ProductoCliente = aliased(Producto)
    ProductoComp = aliased(Producto)
    MarcaCliente = aliased(Marca)
    MarcaComp = aliased(Marca)

    rows = (await db.execute(
        select(SkuCompetencia, ProductoCliente, MarcaCliente, ProductoComp, MarcaComp)
        .join(ProductoCliente, ProductoCliente.id_producto == SkuCompetencia.id_producto_cliente)
        .outerjoin(MarcaCliente, MarcaCliente.id_marca == ProductoCliente.id_marca)
        .join(ProductoComp, ProductoComp.id_producto == SkuCompetencia.id_producto_competencia)
        .outerjoin(MarcaComp, MarcaComp.id_marca == ProductoComp.id_marca)
        .filter(SkuCompetencia.id_cliente == id_cliente, SkuCompetencia.activo == True)
        .order_by(ProductoCliente.producto_gu, ProductoComp.producto_gu)
    )).all()

    grouped: dict = {}
    for sc, pcli, mcli, pcomp, mcomp in rows:
        g = grouped.setdefault(pcli.id_producto, {
            "id_producto_cliente": pcli.id_producto, "producto_cliente": pcli.producto_gu,
            "marca_cliente": mcli.nombre if mcli else None, "competencia": [],
        })
        g["competencia"].append({
            "id_sku_competencia": sc.id, "id_producto": pcomp.id_producto,
            "producto": pcomp.producto_gu, "marca": mcomp.nombre if mcomp else None,
        })
    return list(grouped.values())


class MapeoCreate(BaseModel):
    id_cliente: int
    id_producto_cliente: int
    id_producto_competencia: int


@router.post("/mapeos")
async def create_mapeo(data: MapeoCreate, db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(require_permission('sku-competencia.crear', 'read', fallback_roles=('admin',)))):
    if data.id_producto_cliente == data.id_producto_competencia:
        raise HTTPException(400, "Un producto no puede ser su propia competencia")
    existe = (await db.execute(
        select(SkuCompetencia).filter_by(
            id_cliente=data.id_cliente, id_producto_cliente=data.id_producto_cliente,
            id_producto_competencia=data.id_producto_competencia,
        )
    )).scalars().first()
    if existe:
        if not existe.activo:
            existe.activo = True
            await db.commit()
            return {"detail": "Reactivado"}
        return {"detail": "Ya estaba asignado"}
    db.add(SkuCompetencia(**data.model_dump()))
    await db.commit()
    return {"detail": "Asignado"}


class MapeoMasivo(BaseModel):
    id_cliente: int
    id_producto_cliente: int
    competencia_ids: List[int]


@router.post("/mapeos/masivo")
async def bulk_create_mapeo(data: MapeoMasivo, db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(require_permission('sku-competencia.crear', 'read', fallback_roles=('admin',)))):
    """Asigna varios competidores de una vez al mismo SKU propio -- salta
    los que ya están asignados en vez de fallar toda la operación."""
    ids = [i for i in data.competencia_ids if i != data.id_producto_cliente]
    ya = {
        r for r in (await db.execute(
            select(SkuCompetencia.id_producto_competencia)
            .filter(
                SkuCompetencia.id_cliente == data.id_cliente,
                SkuCompetencia.id_producto_cliente == data.id_producto_cliente,
                SkuCompetencia.id_producto_competencia.in_(ids),
                SkuCompetencia.activo == True,
            )
        )).scalars().all()
    }
    nuevos = [
        SkuCompetencia(id_cliente=data.id_cliente, id_producto_cliente=data.id_producto_cliente, id_producto_competencia=i)
        for i in ids if i not in ya
    ]
    for n in nuevos:
        db.add(n)
    await db.commit()
    return {"detail": f"{len(nuevos)} competidor(es) agregado(s).", "agregados": len(nuevos), "ya_existian": len(ya)}


@router.get("/deriva-precio")
async def get_deriva_precio(
    id_cliente: int = Query(...),
    umbral_pct: float = Query(UMBRAL_PCT_DEFAULT, gt=0, le=100),
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_permission('sku-competencia', 'read', fallback_roles=('admin',))),
):
    """S3 del roadmap: por cada par SKU propio/competencia ya definido acá,
    suaviza el spread de precio (Holt amortiguado) y alerta cuando la
    tendencia proyectada apunta al umbral -- ver
    app/services/sku_competencia_precio_service.py para el detalle."""
    return calcular_deriva_precio(db, id_cliente, umbral_pct)


@router.delete("/mapeos/{id_sku_competencia}")
async def delete_mapeo(id_sku_competencia: int, db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(require_permission('sku-competencia.eliminar', 'read', fallback_roles=('admin',)))):
    row = (await db.execute(select(SkuCompetencia).filter(SkuCompetencia.id == id_sku_competencia))).scalars().first()
    if not row:
        raise HTTPException(404, "No encontrado")
    await db.delete(row)
    await db.commit()
    return {"detail": "Eliminado"}

