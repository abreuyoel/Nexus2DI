"""Endpoint de Horas Trabajadas del Centro de Mando.

No existe check-in/check-out para mercaderistas (a diferencia de vendedor/
encuestador, que sí tienen tabla de jornada) -- ambas métricas se aproximan
con las fotos que cada mercaderista sube (FOTOS_TOTALES.fecha_registro), que
es el único rastro con timestamp que existe:

- Horas trabajadas: lapso entre la primera y la última foto de cada día,
  sumado sobre todos los días del rango.
- Tiempo de traslado: un mismo PDV puede tener más de un cliente (el
  mercaderista no "termina" el PDV hasta hacer gestión de todos), así que
  cambiar de cliente en el MISMO PDV no es traslado. Solo cuenta el lapso
  entre la ÚLTIMA foto en un PDV y la PRIMERA foto en un PDV DISTINTO dentro
  del mismo día.

Admin ve todos; analista solo los mercaderistas de SUS rutas
(analistas_rutas -> RUTA_PROGRAMACION -> MERCADERISTAS_RUTAS). Con cliente_id
(mismo filtro "Cliente" de arriba del dashboard) solo cuenta las fotos de
visitas de ESE cliente -- igual que resumen-dia/activaciones, para que las
pestañas queden consistentes entre sí.

Implementación: UNA sola query ORM (join FOTOS_TOTALES+VISITAS_MERCADERISTA+
MERCADERISTAS con los filtros, ordenada por mercaderista/día/hora) y toda la
agregación (horas + traslado) se resuelve en Python sobre esa única pasada.
No hay CTE reusada, así que no existe el problema de la versión SQL previa
(join recalculado dos veces) que terminó en 524 de Cloudflare (>100s) con el
volumen real de datos. La query lleva timeout explícito de 20s: si algo sale
mal (plan malo, bloqueo por un DDL corriendo en producción) falla rápido con
un error claro en vez de colgar la conexión -- y el thread del pool, con
--workers 1 -- hasta que el proxy corta solo.
"""
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import Date, cast, exists, func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import require_analyst_or_admin
from app.modules.auth.entities import Usuario
from app.modules.visits.entities import Visita, Foto
from app.modules.merchandisers.entities import Mercaderista, MercaderistaRuta
from app.modules.routes.entities import RutaProgramacion, AnalistaRuta

router = APIRouter()


@router.get("/horas-trabajadas")
def horas_trabajadas(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    cliente_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_analyst_or_admin),
):
    """Horas trabajadas y tiempo de traslado por mercaderista en el rango,
    de mayor a menor por horas trabajadas."""
    try:
        hoy = date.today()
        if not desde:
            desde = hoy.isoformat()
        if not hasta:
            hasta = desde

        d_desde = date.fromisoformat(desde)
        d_hasta = date.fromisoformat(hasta)
        # Predicado sargable: comparar sobre la columna sin envolverla en
        # CAST(col AS DATE). SQL Server no puede usar un índice sobre una
        # columna dentro de una función, así que el CAST forzaba scan completo
        # en cada request de este endpoint.
        desde_dt = datetime.combine(d_desde, datetime.min.time())
        hasta_dt = datetime.combine(d_hasta, datetime.min.time()) + timedelta(days=1)

        q = (
            db.query(
                Visita.mercaderista_id,
                Mercaderista.nombre,
                Visita.punto_id,
                cast(Foto.fecha_registro, Date).label("dia"),
                Foto.fecha_registro,
                Visita.id,
            )
            .join(Visita, Visita.id == Foto.visita_id)
            .join(Mercaderista, Mercaderista.id == Visita.mercaderista_id)
            .filter(
                Foto.fecha_registro >= desde_dt,
                Foto.fecha_registro < hasta_dt,
            )
        )

        if cliente_id:
            q = q.filter(Visita.id_cliente == cliente_id)

        if current_user.is_analyst and current_user.id_perfil:
            analista_id = int(current_user.id_perfil)
            q = q.filter(
                exists()
                .where(MercaderistaRuta.mercaderista_id == Visita.mercaderista_id)
                .where(RutaProgramacion.ruta_id == MercaderistaRuta.ruta_id)
                .where(AnalistaRuta.id_ruta == RutaProgramacion.ruta_id)
                .where(AnalistaRuta.id_analista == analista_id)
                .where(RutaProgramacion.activo == True)
            )

        q = q.order_by(
            Visita.mercaderista_id,
            cast(Foto.fecha_registro, Date),
            Foto.fecha_registro,
        )

        # Timeout explícito a nivel de driver (pyodbc): si el plan sale mal o
        # un DDL bloquea la lectura en producción, la query falla rápido con
        # un error legible en vez de colgar la conexión hasta que Cloudflare
        # corta en 100s (524).
        #
        # Se pone en la CONEXIÓN (conn.timeout), no en el cursor: esta versión
        # de pyodbc no tiene Cursor.timeout ('pyodbc.Cursor' object has no
        # attribute 'timeout') -- eso rompía la llamada ANTES de ejecutar la
        # query. La conexión es del pool de SQLAlchemy y se reusa entre
        # requests, así que el timeout se restaura al valor previo al salir.
        raw_conn = db.connection().connection
        prev_timeout = 0
        try:
            prev_timeout = raw_conn.timeout
            raw_conn.timeout = 20
        except Exception:
            pass  # no se pudo aplicar -- seguir sin timeout en vez de romper la query
        try:
            rows = q.all()
        finally:
            try:
                raw_conn.timeout = prev_timeout
            except Exception:
                pass

        agg: dict = {}
        cur_mid = None
        cur_dia = None
        first_ts = None
        last_ts = None
        prev_pdv = None
        prev_ts = None
        day_visitas = set()

        def _finalize_day():
            nonlocal first_ts, last_ts, day_visitas
            a = agg[cur_mid]
            if first_ts is not None and last_ts is not None:
                minutos = max((last_ts - first_ts).total_seconds() / 60, 0)
                a["minutos"] += minutos
                a["dias"] += 1
            a["visitas"] += len(day_visitas)
            first_ts = None
            last_ts = None
            day_visitas = set()

        for mid, nombre, pdv, dia, ts, visita_id in rows:
            if ts is None:
                continue
            if mid != cur_mid or dia != cur_dia:
                if cur_mid is not None:
                    _finalize_day()
                cur_mid = mid
                cur_dia = dia
                prev_pdv = None
                prev_ts = None
                agg.setdefault(
                    mid,
                    {"id_mercaderista": mid, "mercaderista": nombre,
                     "minutos": 0.0, "dias": 0, "visitas": 0, "traslado_seg": 0.0},
                )

            a = agg[mid]
            # Traslado: lapso entre la última foto del PDV anterior y la
            # primera foto de un PDV distinto, dentro del mismo día (cambiar
            # de cliente en el mismo PDV no cuenta). NULL en SQL no suma.
            if prev_ts is not None and prev_pdv is not None and pdv is not None and prev_pdv != pdv:
                a["traslado_seg"] += max((ts - prev_ts).total_seconds(), 0)
            prev_pdv = pdv
            prev_ts = ts

            if first_ts is None:
                first_ts = ts
            last_ts = ts
            if visita_id is not None:
                day_visitas.add(visita_id)

        if cur_mid is not None:
            _finalize_day()

        out = []
        for a in agg.values():
            horas = round(a["minutos"] / 60, 1)
            dias = a["dias"]
            trasl_horas = round(a["traslado_seg"] / 3600, 1)
            out.append({
                "id_mercaderista": a["id_mercaderista"],
                "mercaderista": a["mercaderista"],
                "horas_trabajadas": horas,
                "horas_promedio_dia": round(horas / dias, 1) if dias else 0,
                "dias_trabajados": dias,
                "visitas": a["visitas"],
                "tiempo_traslado_horas": trasl_horas,
                "tiempo_traslado_promedio_dia_min": round(a["traslado_seg"] / 60 / dias, 1) if dias else 0,
            })
        out.sort(key=lambda x: x["horas_trabajadas"], reverse=True)
        return {"success": True, "desde": desde, "hasta": hasta, "mercaderistas": out}
    except Exception as e:
        return {"success": False, "message": str(e), "mercaderistas": []}
