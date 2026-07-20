from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class LectorGrupoInfo(BaseModel):
    id_usuario: int
    username: Optional[str] = None
    fecha_lectura: Optional[datetime] = None


class GrupoResponse(BaseModel):
    id_grupo: int
    id_cliente: int
    tipo_grupo: str
    nombre: Optional[str] = None
    no_leidos: int = 0
    ultimo_mensaje: Optional[str] = None
    ultimo_mensaje_fecha: Optional[datetime] = None

    class Config:
        from_attributes = True


class MiembroGrupoResponse(BaseModel):
    id_usuario: int
    username: Optional[str] = None
    origen: str


class MensajeGrupoResponse(BaseModel):
    id_mensaje: int
    id_grupo: int
    id_usuario: Optional[int] = None
    username: Optional[str] = None
    mensaje: str
    tipo_mensaje: str
    fecha_envio: Optional[datetime] = None
    foto_adjunta: Optional[str] = None
    es_mio: bool = False
    leido_por: List[LectorGrupoInfo] = []


class EnviarMensajeGrupoRequest(BaseModel):
    mensaje: str


class VisitaThreadRequest(BaseModel):
    visita_id: int
    tipo_grupo: str


class VisitaThreadResponse(BaseModel):
    id_grupo: int
    id_cliente: int
    tipo_grupo: str
    id_visita: int
    titulo: Optional[str] = None


class VisitaConChatResponse(BaseModel):
    id_visita: int
    fecha_visita: Optional[str] = None
    mercaderista: Optional[str] = None
    punto: Optional[str] = None
    ultimo_mensaje: Optional[str] = None
    fecha_ultimo: Optional[datetime] = None


class MensajeGrupoVisitaResponse(BaseModel):
    id_mensaje: int
    id_cliente: int
    tipo_grupo: str
    id_visita: int
    id_usuario: Optional[int] = None
    username: Optional[str] = None
    mensaje: str
    tipo_mensaje: str
    fecha_envio: Optional[datetime] = None
    foto_adjunta: Optional[str] = None
    es_mio: bool = False
    leido_por: List[LectorGrupoInfo] = []


class InfoGrupoClienteResponse(BaseModel):
    id_grupo: int
    id_cliente: int
    tipo_grupo: str
    nombre: Optional[str] = None
