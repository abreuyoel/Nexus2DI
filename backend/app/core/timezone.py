from datetime import datetime, date
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ruta import Ruta
from app.models.mercaderista import Mercaderista, MercaderistaRuta

# IANA en vez de "restar 1 hora a mano": ninguno de los dos países usa
# horario de verano hoy, así que numéricamente da lo mismo -- pero con la
# zona real, si algún día cambia la regla (o se agrega un tercer país), el
# cálculo se sigue ajustando solo. Autodocumentado también: "America/Panama"
# dice qué es, "-1 hora" solo dice cuánto.
TZ_VENEZUELA = ZoneInfo("America/Caracas")
TZ_PANAMA = ZoneInfo("America/Panama")

def is_panama_mercaderista(db, mercaderista_id: int) -> bool:
    """Retorna True si el mercaderista opera en Panamá.
    Se determina si el cuadrante de alguna de sus rutas asignadas contiene 'Panam'.
    Soporta tanto Session síncrona como AsyncSession de SQLAlchemy.
    """
    if not mercaderista_id:
        return False
        
    # Si es AsyncSession, usamos su sync_session interna
    if isinstance(db, AsyncSession):
        sync_db = db.sync_session
    else:
        sync_db = db
        
    exists = (
        sync_db.query(MercaderistaRuta)
        .join(Ruta)
        .filter(
            MercaderistaRuta.mercaderista_id == mercaderista_id,
            Ruta.cuadrante.like("%Panam%")
        )
        .first()
    )
    return exists is not None

def get_adjusted_now(db, mercaderista_id: int) -> datetime:
    """Devuelve la fecha/hora actual (now) ajustada según el país de operación del mercaderista.

    Se calcula con zoneinfo real (America/Caracas o America/Panama), no una
    resta de horas a mano -- el servidor mismo puede estar en cualquier
    zona, esto no depende de su reloj local para el cálculo del offset,
    solo del instante UTC real. La columna de destino (FOTOS_TOTALES.
    fecha_registro, etc.) es DATETIME naive, así que se devuelve naive
    (tzinfo=None) representando la hora de pared del país correspondiente.
    """
    tz = TZ_PANAMA if is_panama_mercaderista(db, mercaderista_id) else TZ_VENEZUELA
    return datetime.now(tz).replace(tzinfo=None)

def get_adjusted_today(db, mercaderista_id: int) -> date:
    """Devuelve la fecha actual (date) ajustada según el país de operación del mercaderista.
    Evita el salto de día prematuro cuando en Venezuela ya es el día siguiente pero en Panamá no.
    """
    return get_adjusted_now(db, mercaderista_id).date()
