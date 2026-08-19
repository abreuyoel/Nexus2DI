from sqlalchemy import select
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel
from app.db.session import get_db, get_async_db
from app.core.dependencies import get_current_user
from app.models.user import Usuario
from app.models.cliente import Cliente
from app.schemas.cliente import ClienteResponse

router = APIRouter(prefix="/api/clients", tags=["Clientes"])


@router.get("", response_model=List[ClienteResponse])
@router.get("/", response_model=List[ClienteResponse])
async def list_clients(
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(get_current_user),
):
    return (await db.execute(select(Cliente).order_by(Cliente.nombre))).scalars().all()


@router.get("/{client_id}", response_model=ClienteResponse)
async def get_client(client_id: int, db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(get_current_user)):
    cliente = (await db.execute(select(Cliente).filter(Cliente.id == client_id))).scalars().first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente

from app.schemas.cliente import ClienteCreate, ClienteUpdate
from app.core.dependencies import require_admin
from fastapi import status

@router.post("", response_model=ClienteResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ClienteResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    data: ClienteCreate,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_admin),
):
    # El modelo Cliente solo mapea "nombre" (columna "cliente") -- ClienteBase
    # declara además "activo", que no existe en CLIENTES, así que
    # Cliente(**data.model_dump()) tiraba TypeError ("activo" es un keyword
    # arg inválido) y explotaba en 500 antes de llegar siquiera al INSERT.
    if not data.nombre or not data.nombre.strip():
        raise HTTPException(status_code=400, detail="El nombre del cliente es requerido")
    cliente = Cliente(
        nombre=data.nombre.strip(),
        id_categoria=data.id_categoria or 1,
    )
    db.add(cliente)
    await db.commit()
    await db.refresh(cliente)
    return cliente

@router.put("/{client_id}", response_model=ClienteResponse)
async def update_client(
    client_id: int,
    data: ClienteUpdate,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_admin),
):
    cliente = (await db.execute(select(Cliente).filter(Cliente.id == client_id))).scalars().first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    update_data = data.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(cliente, key, value)
    
    await db.commit()
    await db.refresh(cliente)
    return cliente

@router.delete("/{client_id}")
async def delete_client(
    client_id: int,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_admin),
):
    cliente = (await db.execute(select(Cliente).filter(Cliente.id == client_id))).scalars().first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Simple check for active usage before deleting could be added here
    await db.delete(cliente)
    await db.commit()
    return {"detail": "Cliente eliminado"}

# =======================
# CATEGORIAS CLIENTES
# =======================
from app.models.cliente import CategoriaCliente
from app.models.producto import Categoria

@router.get("/categorias/{categoria_id}/clientes")
async def get_clients_by_category(categoria_id: int, db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(get_current_user)):
    """IDs de clientes que ya tienen asignada esta categoría -- para el
    filtro "¿qué clientes tienen la categoría X?" en Categorías Cliente."""
    rows = (await db.execute(select(CategoriaCliente.id_cliente).filter(CategoriaCliente.id_categoria == categoria_id))).scalars().all()
    return [r[0] for r in rows]


class AsignacionMasiva(BaseModel):
    cliente_ids: List[int]


@router.post("/categorias/{categoria_id}/asignar-masivo")
async def bulk_assign_category(categoria_id: int, payload: AsignacionMasiva, db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(require_admin)):
    """Asigna la misma categoría a varios clientes de una sola vez -- salta
    los que ya la tienen en vez de fallar toda la operación por duplicados."""
    ya_tienen = {
        r for r in (await db.execute(
            select(CategoriaCliente.id_cliente)
            .filter(CategoriaCliente.id_categoria == categoria_id, CategoriaCliente.id_cliente.in_(payload.cliente_ids))
        )).scalars().all()
    }
    nuevos = [CategoriaCliente(id_cliente=cid, id_categoria=categoria_id) for cid in payload.cliente_ids if cid not in ya_tienen]
    for n in nuevos:
        db.add(n)
    await db.commit()
    return {"detail": f"{len(nuevos)} cliente(s) asignados.", "asignados": len(nuevos), "ya_tenian": len(ya_tienen)}


@router.get("/{client_id}/categorias", response_model=List[dict])
async def get_client_categories(client_id: int, db: AsyncSession = Depends(get_async_db)):
    """Obtener todas las categorías asignadas a un cliente."""
    resultados = (await db.execute(
        select(CategoriaCliente, Categoria.nombre.label("cat_nombre"))
        .join(Categoria, CategoriaCliente.id_categoria == Categoria.id_categoria)
        .filter(CategoriaCliente.id_cliente == client_id)
    )).all()
    
    response = []
    for row in resultados:
        rel = row.CategoriaCliente
        response.append({
            "id_cliente": rel.id_cliente,
            "id_categoria": rel.id_categoria,
            "categoria_nombre": row.cat_nombre
        })
    return response

from pydantic import BaseModel
class AsignacionCategoria(BaseModel):
    id_categoria: int

@router.post("/{client_id}/categorias")
async def add_client_category(client_id: int, payload: AsignacionCategoria, db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(require_admin)):
    """Asignar una categoría a un cliente."""
    existe = (await db.execute(select(CategoriaCliente).filter_by(id_cliente=client_id, id_categoria=payload.id_categoria))).scalars().first()
    if existe:
        raise HTTPException(status_code=400, detail="El cliente ya tiene esta categoría.")
    
    nuevo = CategoriaCliente(id_cliente=client_id, id_categoria=payload.id_categoria)
    db.add(nuevo)
    await db.commit()
    return {"detail": "Categoría asignada al cliente."}

@router.delete("/{client_id}/categorias/{categoria_id}")
async def remove_client_category(client_id: int, categoria_id: int, db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(require_admin)):
    """Desasignar una categoría de un cliente."""
    rel = (await db.execute(select(CategoriaCliente).filter_by(id_cliente=client_id, id_categoria=categoria_id))).scalars().first()
    if not rel:
        raise HTTPException(status_code=404, detail="Asignación no encontrada.")
    
    db.delete(rel)
    await db.commit()
    return {"detail": "Categoría desasignada del cliente."}
