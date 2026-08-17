from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import Usuario
from app.models.cliente import Cliente
from app.schemas.cliente import ClienteResponse

router = APIRouter(prefix="/api/clients", tags=["Clientes"])


@router.get("", response_model=List[ClienteResponse])
def list_clients(
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    return db.query(Cliente).order_by(Cliente.nombre).all()


@router.get("/{client_id}", response_model=ClienteResponse)
def get_client(client_id: int, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    cliente = db.query(Cliente).filter(Cliente.id == client_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente

from app.schemas.cliente import ClienteCreate, ClienteUpdate
from app.core.dependencies import require_admin
from fastapi import status

@router.post("", response_model=ClienteResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    data: ClienteCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    # El modelo Cliente solo mapea "nombre" (columna "cliente") -- ClienteBase
    # declara además "activo", que no existe en CLIENTES, así que
    # Cliente(**data.model_dump()) tiraba TypeError ("activo" es un keyword
    # arg inválido) y explotaba en 500 antes de llegar siquiera al INSERT.
    if not data.nombre or not data.nombre.strip():
        raise HTTPException(status_code=400, detail="El nombre del cliente es requerido")
    cliente = Cliente(nombre=data.nombre.strip())
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente

@router.put("/{client_id}", response_model=ClienteResponse)
def update_client(
    client_id: int,
    data: ClienteUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    cliente = db.query(Cliente).filter(Cliente.id == client_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    update_data = data.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(cliente, key, value)
    
    db.commit()
    db.refresh(cliente)
    return cliente

@router.delete("/{client_id}")
def delete_client(
    client_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    cliente = db.query(Cliente).filter(Cliente.id == client_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Simple check for active usage before deleting could be added here
    db.delete(cliente)
    db.commit()
    return {"detail": "Cliente eliminado"}

# =======================
# CATEGORIAS CLIENTES
# =======================
from app.models.cliente import CategoriaCliente
from app.models.producto import Categoria

@router.get("/categorias/{categoria_id}/clientes")
def get_clients_by_category(categoria_id: int, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    """IDs de clientes que ya tienen asignada esta categoría -- para el
    filtro "¿qué clientes tienen la categoría X?" en Categorías Cliente."""
    rows = db.query(CategoriaCliente.id_cliente).filter(CategoriaCliente.id_categoria == categoria_id).all()
    return [r[0] for r in rows]


class AsignacionMasiva(BaseModel):
    cliente_ids: List[int]


@router.post("/categorias/{categoria_id}/asignar-masivo")
def bulk_assign_category(categoria_id: int, payload: AsignacionMasiva, db: Session = Depends(get_db), _: Usuario = Depends(require_admin)):
    """Asigna la misma categoría a varios clientes de una sola vez -- salta
    los que ya la tienen en vez de fallar toda la operación por duplicados."""
    ya_tienen = {
        r[0] for r in db.query(CategoriaCliente.id_cliente)
        .filter(CategoriaCliente.id_categoria == categoria_id, CategoriaCliente.id_cliente.in_(payload.cliente_ids))
        .all()
    }
    nuevos = [CategoriaCliente(id_cliente=cid, id_categoria=categoria_id) for cid in payload.cliente_ids if cid not in ya_tienen]
    for n in nuevos:
        db.add(n)
    db.commit()
    return {"detail": f"{len(nuevos)} cliente(s) asignados.", "asignados": len(nuevos), "ya_tenian": len(ya_tienen)}


@router.get("/{client_id}/categorias", response_model=List[dict])
def get_client_categories(client_id: int, db: Session = Depends(get_db)):
    """Obtener todas las categorías asignadas a un cliente."""
    resultados = (
        db.query(CategoriaCliente, Categoria.nombre)
        .join(Categoria, CategoriaCliente.id_categoria == Categoria.id_categoria)
        .filter(CategoriaCliente.id_cliente == client_id)
        .all()
    )
    
    response = []
    for rel, cat_name in resultados:
        response.append({
            "id_cliente": rel.id_cliente,
            "id_categoria": rel.id_categoria,
            "categoria_nombre": cat_name
        })
    return response

from pydantic import BaseModel
class AsignacionCategoria(BaseModel):
    id_categoria: int

@router.post("/{client_id}/categorias")
def add_client_category(client_id: int, payload: AsignacionCategoria, db: Session = Depends(get_db), _: Usuario = Depends(require_admin)):
    """Asignar una categoría a un cliente."""
    existe = db.query(CategoriaCliente).filter_by(id_cliente=client_id, id_categoria=payload.id_categoria).first()
    if existe:
        raise HTTPException(status_code=400, detail="El cliente ya tiene esta categoría.")
    
    nuevo = CategoriaCliente(id_cliente=client_id, id_categoria=payload.id_categoria)
    db.add(nuevo)
    db.commit()
    return {"detail": "Categoría asignada al cliente."}

@router.delete("/{client_id}/categorias/{categoria_id}")
def remove_client_category(client_id: int, categoria_id: int, db: Session = Depends(get_db), _: Usuario = Depends(require_admin)):
    """Desasignar una categoría de un cliente."""
    rel = db.query(CategoriaCliente).filter_by(id_cliente=client_id, id_categoria=categoria_id).first()
    if not rel:
        raise HTTPException(status_code=404, detail="Asignación no encontrada.")
    
    db.delete(rel)
    db.commit()
    return {"detail": "Categoría desasignada del cliente."}
