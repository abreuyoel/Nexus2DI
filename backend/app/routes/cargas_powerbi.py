from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.session import get_db
from app.core.dependencies import get_current_user, require_permission
from app.models.user import Usuario
from app.models.cliente import Cliente

router = APIRouter(prefix="/api/cargas-powerbi", tags=["Cargas de Power BI"])


class PowerBiCreate(BaseModel):
    id_cliente: int
    nombre: Optional[str] = "Power BI Principal"
    url_html: str
    tipo: Optional[str] = "powerbi"


class PowerBiUpdate(BaseModel):
    nombre: Optional[str] = None
    url_html: Optional[str] = None
    activo: Optional[bool] = None


class PowerBiItem(BaseModel):
    id_dashboard: int
    id_cliente: int
    cliente_nombre: Optional[str] = None
    nombre: Optional[str] = None
    url_html: str
    tipo: Optional[str] = "powerbi"
    fecha_creacion: Optional[datetime] = None
    activo: bool = True
    es_principal: bool = False


class ClientPowerBiSummary(BaseModel):
    id_cliente: int
    cliente: str
    total_powerbi: int
    powerbis: List[PowerBiItem]


@router.get("/summary", response_model=List[ClientPowerBiSummary])
def get_cargas_powerbi_summary(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("cargas-powerbi", "read", ("admin", "analyst", "coordinador_general"))),
):
    """Obtiene el resumen de todos los clientes con la lista de sus Power BIs cargados."""
    # 1. Obtener todos los clientes ordenados por nombre
    clientes = db.query(Cliente).order_by(Cliente.nombre).all()

    # 2. Obtener todos los registros de dashboard_client
    query = text("""
        SELECT id_dashboard, id_cliente, nombre, url_html, tipo, fecha_creacion, ISNULL(activo, 1) as activo, ISNULL(es_principal, 0) as es_principal
        FROM dashboard_client
        ORDER BY id_cliente, ISNULL(es_principal, 0) DESC, fecha_creacion DESC, id_dashboard DESC
    """)
    rows = db.execute(query).fetchall()

    # Agrupar por id_cliente
    powerbis_by_client = {}
    for r in rows:
        cid = r[1]
        item = PowerBiItem(
            id_dashboard=r[0],
            id_cliente=r[1],
            nombre=r[2] or "Power BI",
            url_html=r[3],
            tipo=r[4] or "powerbi",
            fecha_creacion=r[5],
            activo=bool(r[6]),
            es_principal=bool(r[7]),
        )
        if cid not in powerbis_by_client:
            powerbis_by_client[cid] = []
        powerbis_by_client[cid].append(item)

    # Construir respuesta final incluyendo el nombre del cliente
    result = []
    for c in clientes:
        p_list = powerbis_by_client.get(c.id, [])
        for p in p_list:
            p.cliente_nombre = c.nombre
        result.append(ClientPowerBiSummary(
            id_cliente=c.id,
            cliente=c.nombre,
            total_powerbi=len(p_list),
            powerbis=p_list
        ))

    return result


@router.get("/client/{client_id}", response_model=List[PowerBiItem])
def get_client_powerbis(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Obtiene la lista de Power BIs activos para un cliente específico."""
    cliente = db.query(Cliente).filter(Cliente.id == client_id).first()
    cliente_nombre = cliente.nombre if cliente else "Cliente"

    query = text("""
        SELECT id_dashboard, id_cliente, nombre, url_html, tipo, fecha_creacion, ISNULL(activo, 1) as activo, ISNULL(es_principal, 0) as es_principal
        FROM dashboard_client
        WHERE id_cliente = :client_id AND ISNULL(activo, 1) = 1
        ORDER BY ISNULL(es_principal, 0) DESC, fecha_creacion DESC, id_dashboard DESC
    """)
    rows = db.execute(query, {"client_id": client_id}).fetchall()

    return [
        PowerBiItem(
            id_dashboard=r[0],
            id_cliente=r[1],
            cliente_nombre=cliente_nombre,
            nombre=r[2] or "Power BI",
            url_html=r[3],
            tipo=r[4] or "powerbi",
            fecha_creacion=r[5],
            activo=bool(r[6]),
            es_principal=bool(r[7]),
        )
        for r in rows
    ]


@router.post("", response_model=PowerBiItem, status_code=status.HTTP_201_CREATED)
def create_cargas_powerbi(
    payload: PowerBiCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("cargas-powerbi", "write", ("admin", "analyst"))),
):
    """Crea una nueva carga de Power BI asignada a un cliente."""
    if not payload.url_html or not payload.url_html.strip():
        raise HTTPException(status_code=400, detail="El código iframe o URL de Power BI es obligatorio")

    cliente = db.query(Cliente).filter(Cliente.id == payload.id_cliente).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="El cliente especificado no existe")

    nombre = payload.nombre.strip() if payload.nombre and payload.nombre.strip() else "Power BI"

    query = text("""
        INSERT INTO dashboard_client (id_cliente, nombre, url_html, tipo, fecha_creacion, activo)
        OUTPUT INSERTED.id_dashboard, INSERTED.id_cliente, INSERTED.nombre, INSERTED.url_html, INSERTED.tipo, INSERTED.fecha_creacion, INSERTED.activo
        VALUES (:id_cliente, :nombre, :url_html, :tipo, GETDATE(), 1)
    """)
    row = db.execute(query, {
        "id_cliente": payload.id_cliente,
        "nombre": nombre,
        "url_html": payload.url_html.strip(),
        "tipo": payload.tipo or "powerbi"
    }).fetchone()
    db.commit()

    return PowerBiItem(
        id_dashboard=row[0],
        id_cliente=row[1],
        cliente_nombre=cliente.nombre,
        nombre=row[2],
        url_html=row[3],
        tipo=row[4],
        fecha_creacion=row[5],
        activo=bool(row[6]),
    )


@router.put("/{id_dashboard}", response_model=PowerBiItem)
def update_cargas_powerbi(
    id_dashboard: int,
    payload: PowerBiUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("cargas-powerbi", "write", ("admin", "analyst"))),
):
    """Actualiza los datos de un Power BI cargado."""
    check_query = text("SELECT id_dashboard, id_cliente FROM dashboard_client WHERE id_dashboard = :id")
    existing = db.execute(check_query, {"id": id_dashboard}).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Carga de Power BI no encontrada")

    updates = []
    params = {"id": id_dashboard}

    if payload.nombre is not None:
        updates.append("nombre = :nombre")
        params["nombre"] = payload.nombre.strip()

    if payload.url_html is not None:
        updates.append("url_html = :url_html")
        params["url_html"] = payload.url_html.strip()

    if payload.activo is not None:
        updates.append("activo = :activo")
        params["activo"] = 1 if payload.activo else 0

    if updates:
        sql = f"UPDATE dashboard_client SET {', '.join(updates)} WHERE id_dashboard = :id"
        db.execute(text(sql), params)
        db.commit()

    # Devolver el item actualizado
    query = text("""
        SELECT d.id_dashboard, d.id_cliente, d.nombre, d.url_html, d.tipo, d.fecha_creacion, d.activo, c.cliente
        FROM dashboard_client d
        LEFT JOIN CLIENTES c ON c.id_cliente = d.id_cliente
        WHERE d.id_dashboard = :id
    """)
    row = db.execute(query, {"id": id_dashboard}).fetchone()

    return PowerBiItem(
        id_dashboard=row[0],
        id_cliente=row[1],
        cliente_nombre=row[7] or "Cliente",
        nombre=row[2],
        url_html=row[3],
        tipo=row[4],
        fecha_creacion=row[5],
        activo=bool(row[6]),
    )


@router.delete("/{id_dashboard}")
def delete_cargas_powerbi(
    id_dashboard: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("cargas-powerbi", "delete", ("admin", "analyst"))),
):
    """Elimina un Power BI asignado."""
    check_query = text("SELECT id_dashboard FROM dashboard_client WHERE id_dashboard = :id")
    existing = db.execute(check_query, {"id": id_dashboard}).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Carga de Power BI no encontrada")

    db.execute(text("DELETE FROM dashboard_client WHERE id_dashboard = :id"), {"id": id_dashboard})
    db.commit()
    return {"detail": "Power BI eliminado exitosamente"}


@router.put("/{id_dashboard}/set-principal", response_model=PowerBiItem)
def set_principal_powerbi(
    id_dashboard: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("cargas-powerbi", "write", ("admin", "analyst"))),
):
    """Establece un Power BI como el principal/activo por defecto de su cliente."""
    check_query = text("SELECT id_dashboard, id_cliente FROM dashboard_client WHERE id_dashboard = :id")
    existing = db.execute(check_query, {"id": id_dashboard}).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Carga de Power BI no encontrada")

    client_id = existing[1]

    # Desmarcar todos los demás reportes del mismo cliente
    db.execute(text("UPDATE dashboard_client SET es_principal = 0 WHERE id_cliente = :cid"), {"cid": client_id})

    # Marcar este reporte como principal
    db.execute(text("UPDATE dashboard_client SET es_principal = 1 WHERE id_dashboard = :id"), {"id": id_dashboard})
    db.commit()

    # Devolver item actualizado
    query = text("""
        SELECT d.id_dashboard, d.id_cliente, d.nombre, d.url_html, d.tipo, d.fecha_creacion, ISNULL(d.activo, 1) as activo, c.cliente, ISNULL(d.es_principal, 0) as es_principal
        FROM dashboard_client d
        LEFT JOIN CLIENTES c ON c.id_cliente = d.id_cliente
        WHERE d.id_dashboard = :id
    """)
    row = db.execute(query, {"id": id_dashboard}).fetchone()

    return PowerBiItem(
        id_dashboard=row[0],
        id_cliente=row[1],
        cliente_nombre=row[7] or "Cliente",
        nombre=row[2],
        url_html=row[3],
        tipo=row[4],
        fecha_creacion=row[5],
        activo=bool(row[6]),
        es_principal=bool(row[8]),
    )
