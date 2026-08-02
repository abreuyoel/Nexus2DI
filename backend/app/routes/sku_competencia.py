"""SKU vs SKU: por cliente, qué SKU propio se enfrenta contra qué SKU(s) de
la competencia. Fase 1 -- solo la pantalla de definición: NO cambia todavía
qué productos ve el mercaderista en la APK (GET /api/merc/productos sigue
mostrando toda la categoría del cliente hasta que se confirme ese paso)."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, aliased
from typing import List
from pydantic import BaseModel
from app.db.session import get_db
from app.core.dependencies import require_admin
from app.models.user import Usuario
from app.models.sku_competencia import SkuCompetencia
from app.models.producto import Producto, Marca

router = APIRouter(prefix="/api/sku-competencia", tags=["SKU vs SKU"])


@router.get("/mapeos")
def get_mapeos(id_cliente: int = Query(...), db: Session = Depends(get_db), _: Usuario = Depends(require_admin)):
    """Agrupado por SKU propio del cliente, con la lista de competidores
    que tiene definidos cada uno."""
    ProductoCliente = aliased(Producto)
    ProductoComp = aliased(Producto)
    MarcaCliente = aliased(Marca)
    MarcaComp = aliased(Marca)

    rows = (
        db.query(SkuCompetencia, ProductoCliente, MarcaCliente, ProductoComp, MarcaComp)
        .join(ProductoCliente, ProductoCliente.id_producto == SkuCompetencia.id_producto_cliente)
        .outerjoin(MarcaCliente, MarcaCliente.id_marca == ProductoCliente.id_marca)
        .join(ProductoComp, ProductoComp.id_producto == SkuCompetencia.id_producto_competencia)
        .outerjoin(MarcaComp, MarcaComp.id_marca == ProductoComp.id_marca)
        .filter(SkuCompetencia.id_cliente == id_cliente, SkuCompetencia.activo == True)
        .order_by(ProductoCliente.producto_gu, ProductoComp.producto_gu)
        .all()
    )

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
def create_mapeo(data: MapeoCreate, db: Session = Depends(get_db), _: Usuario = Depends(require_admin)):
    if data.id_producto_cliente == data.id_producto_competencia:
        raise HTTPException(400, "Un producto no puede ser su propia competencia")
    existe = db.query(SkuCompetencia).filter_by(
        id_cliente=data.id_cliente, id_producto_cliente=data.id_producto_cliente,
        id_producto_competencia=data.id_producto_competencia,
    ).first()
    if existe:
        if not existe.activo:
            existe.activo = True
            db.commit()
            return {"detail": "Reactivado"}
        return {"detail": "Ya estaba asignado"}
    db.add(SkuCompetencia(**data.model_dump()))
    db.commit()
    return {"detail": "Asignado"}


class MapeoMasivo(BaseModel):
    id_cliente: int
    id_producto_cliente: int
    competencia_ids: List[int]


@router.post("/mapeos/masivo")
def bulk_create_mapeo(data: MapeoMasivo, db: Session = Depends(get_db), _: Usuario = Depends(require_admin)):
    """Asigna varios competidores de una vez al mismo SKU propio -- salta
    los que ya están asignados en vez de fallar toda la operación."""
    ids = [i for i in data.competencia_ids if i != data.id_producto_cliente]
    ya = {
        r[0] for r in db.query(SkuCompetencia.id_producto_competencia)
        .filter(
            SkuCompetencia.id_cliente == data.id_cliente,
            SkuCompetencia.id_producto_cliente == data.id_producto_cliente,
            SkuCompetencia.id_producto_competencia.in_(ids),
            SkuCompetencia.activo == True,
        ).all()
    }
    nuevos = [
        SkuCompetencia(id_cliente=data.id_cliente, id_producto_cliente=data.id_producto_cliente, id_producto_competencia=i)
        for i in ids if i not in ya
    ]
    for n in nuevos:
        db.add(n)
    db.commit()
    return {"detail": f"{len(nuevos)} competidor(es) agregado(s).", "agregados": len(nuevos), "ya_existian": len(ya)}


@router.delete("/mapeos/{id_sku_competencia}")
def delete_mapeo(id_sku_competencia: int, db: Session = Depends(get_db), _: Usuario = Depends(require_admin)):
    row = db.query(SkuCompetencia).filter(SkuCompetencia.id == id_sku_competencia).first()
    if not row:
        raise HTTPException(404, "No encontrado")
    db.delete(row)
    db.commit()
    return {"detail": "Eliminado"}
