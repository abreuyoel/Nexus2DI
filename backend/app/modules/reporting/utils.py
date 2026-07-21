import calendar as _calendar
from datetime import date as _date, datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from app.modules.routes.entities import RutaProgramacion, AnalistaRuta


DIAS_ES = {
    'Monday':    'Lunes',
    'Tuesday':   'Martes',
    'Wednesday': 'Miércoles',
    'Thursday':  'Jueves',
    'Friday':    'Viernes',
    'Saturday':  'Sábado',
    'Sunday':    'Domingo',
}


def _dia_es(fecha: _date) -> str:
    return DIAS_ES[fecha.strftime('%A')]


def _clientes_de_analista(db: Session, analista_id: int) -> List[int]:
    if not analista_id:
        return []
    rows = (
        db.query(RutaProgramacion.id_cliente)
        .distinct()
        .join(AnalistaRuta, RutaProgramacion.ruta_id == AnalistaRuta.id_ruta)
        .filter(AnalistaRuta.id_analista == analista_id, RutaProgramacion.activo == True)
        .all()
    )
    return [r[0] for r in rows if r[0] is not None]
