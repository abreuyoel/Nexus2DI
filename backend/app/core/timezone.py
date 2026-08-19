from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ruta import Ruta
from app.models.mercaderista import Mercaderista, MercaderistaRuta

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
    La hora del servidor corre en Venezuela (UTC-4).
    Si el mercaderista está en Panamá (UTC-5), se resta 1 hora.
    """
    now = datetime.now()
    if is_panama_mercaderista(db, mercaderista_id):
        return now - timedelta(hours=1)
    return now

def get_adjusted_today(db, mercaderista_id: int) -> date:
    """Devuelve la fecha actual (date) ajustada según el país de operación del mercaderista.
    Evita el salto de día prematuro cuando en Venezuela ya es el día siguiente pero en Panamá no.
    """
    return get_adjusted_now(db, mercaderista_id).date()
