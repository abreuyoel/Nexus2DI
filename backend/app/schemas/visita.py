from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from app.schemas.punto import PuntoResponse
from app.schemas.mercaderista import MercaderistaResponse
from app.schemas.cliente import ClienteResponse


class VisitaBase(BaseModel):
    mercaderista_id: Optional[int] = None
    punto_id: Optional[str] = None
    ruta_id: Optional[int] = None
    id_cliente: Optional[int] = None
    fecha: Optional[date] = None
    estado: Optional[str] = "Pendiente"
    tipo_visita: Optional[str] = None


class VisitaCreate(VisitaBase):
    pass


class VisitaUpdate(BaseModel):
    estado: Optional[str] = None
    tipo_visita: Optional[str] = None


class VisitaResponse(VisitaBase):
    id: int
    punto: Optional[PuntoResponse] = None
    mercaderista: Optional[MercaderistaResponse] = None
    cliente: Optional[ClienteResponse] = None

    class Config:
        from_attributes = True


class BalanceResponse(BaseModel):
    id: int
    id_cliente: Optional[int] = None
    fecha_balance: Optional[date] = None
    identificador_pdv: Optional[str] = None
    mercaderista: Optional[str] = None
    producto: Optional[str] = None
    categoria: Optional[str] = None
    fabricante: Optional[str] = None
    inv_inicial: Optional[float] = None
    inv_final: Optional[float] = None
    inv_deposito: Optional[float] = None
    caras: Optional[int] = None
    precio_bs: Optional[float] = None
    precio_ds: Optional[float] = None
    visita_id: Optional[int] = None
    # FIFO/FEFO -- fecha del primer vencimiento en el inventario del PDV,
    # capturada por el mercaderista en la APK (BALANCES_TOTALES.FEFO, columna
    # ya en mayúsculas en la tabla real -- de ahí el nombre del campo acá
    # también en mayúsculas: from_attributes mapea por nombre exacto de
    # atributo contra el modelo Balance, que usa "FEFO" igual). Pedido
    # explícito (21 ago 2026): que se vea en Auditoría de Data.
    FEFO: Optional[date] = None

    class Config:
        from_attributes = True


class UpdateBalanceItem(BaseModel):
    id_balance: int
    inv_inicial: Optional[float] = None
    inv_final: Optional[float] = None
    inv_deposito: Optional[float] = None
    caras: Optional[int] = None
    precio_bs: Optional[float] = None
    precio_ds: Optional[float] = None


class UpdateBalancesRequest(BaseModel):
    visita_id: int
    balances: List[UpdateBalanceItem]
