from datetime import date as _date, datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import Date, func

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.entities import Usuario
from app.modules.clients.entities import Cliente
from app.modules.routes.entities import Ruta, RutaProgramacion, RutaActivada
from app.modules.merchandisers.entities import Mercaderista, MercaderistaRuta
from app.modules.reporting.dto import DetalleMercaderistasResponse, DetalleMercaderistaItem
from app.modules.reporting.utils import _dia_es

router = APIRouter()


@router.get("/detalle-mercaderistas")
def detalle_mercaderistas(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    cliente_id: Optional[int] = None,
    estado_filtro: Optional[str] = Query('todos'),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    try:
        if current_user.is_client and not current_user.rol == 'admin':
            cliente_id = current_user.id_perfil

        d_desde = datetime.strptime(desde, '%Y-%m-%d').date() if desde else _date.today()
        d_hasta = datetime.strptime(hasta, '%Y-%m-%d').date() if hasta else d_desde
        if d_hasta < d_desde:
            d_hasta = d_desde

        day_counts = { 'Lunes':0, 'Martes':0, 'Miércoles':0, 'Jueves':0, 'Viernes':0, 'Sábado':0, 'Domingo':0 }
        curr = d_desde
        while curr <= d_hasta:
            day_counts[_dia_es(curr)] += 1
            curr += timedelta(days=1)
        days_in_range = [d for d, c in day_counts.items() if c > 0]

        cli_row = db.query(Cliente.id_tipo_cliente).filter(Cliente.id == cliente_id).first() if cliente_id else None
        cliente_tipo = cli_row[0] if cli_row else None

        # Asignados
        q_asig = (
            db.query(Mercaderista.id, Mercaderista.nombre, Mercaderista.cedula, Mercaderista.tipo)
            .distinct()
            .join(MercaderistaRuta, MercaderistaRuta.mercaderista_id == Mercaderista.id)
            .join(RutaProgramacion, RutaProgramacion.ruta_id == MercaderistaRuta.ruta_id)
            .outerjoin(Ruta, Ruta.id == RutaProgramacion.ruta_id)
            .filter(Mercaderista.activo == True, RutaProgramacion.activo == True)
        )
        if cliente_id:
            q_asig = q_asig.filter(RutaProgramacion.id_cliente == cliente_id)
            if cliente_tipo == 3:
                q_asig = q_asig.filter(Ruta.servicio == 'Exclusivo')

        asignados = q_asig.all()

        if not asignados:
            return DetalleMercaderistasResponse(success=True, total=0, mercaderistas=[])

        asignados_map = {
            r[0]: {
                "id_mercaderista": r[0],
                "nombre": r[1],
                "cedula": r[2],
                "tipo_campo": r[3] or "Mercaderista"
            }
            for r in asignados
        }

        # Planificados
        q_plan = (
            db.query(Mercaderista.id, RutaProgramacion.dia)
            .distinct()
            .join(MercaderistaRuta, MercaderistaRuta.mercaderista_id == Mercaderista.id)
            .join(RutaProgramacion, RutaProgramacion.ruta_id == MercaderistaRuta.ruta_id)
            .outerjoin(Ruta, Ruta.id == RutaProgramacion.ruta_id)
            .filter(Mercaderista.activo == True, RutaProgramacion.activo == True, RutaProgramacion.dia.in_(days_in_range))
        )
        if cliente_id:
            q_plan = q_plan.filter(RutaProgramacion.id_cliente == cliente_id)
            if cliente_tipo == 3:
                q_plan = q_plan.filter(Ruta.servicio == 'Exclusivo')

        plan_counts = {}
        for mid, dia in q_plan.all():
            plan_counts[mid] = plan_counts.get(mid, 0) + day_counts.get(dia, 0)

        # Activos
        q_act = (
            db.query(
                RutaActivada.id_mercaderista,
                func.cast(RutaActivada.fecha_hora_activacion, Date),
                func.count(RutaActivada.id),
                func.max(RutaActivada.fecha_hora_activacion)
            )
            .join(MercaderistaRuta, MercaderistaRuta.ruta_id == RutaActivada.ruta_id)
            .join(RutaProgramacion, RutaProgramacion.ruta_id == RutaActivada.ruta_id)
            .outerjoin(Ruta, Ruta.id == RutaProgramacion.ruta_id)
            .filter(
                func.cast(RutaActivada.fecha_hora_activacion, Date) >= d_desde,
                func.cast(RutaActivada.fecha_hora_activacion, Date) <= d_hasta,
                MercaderistaRuta.mercaderista_id == RutaActivada.id_mercaderista
            )
            .group_by(RutaActivada.id_mercaderista, func.cast(RutaActivada.fecha_hora_activacion, Date))
        )
        if cliente_id:
            q_act = q_act.filter(RutaProgramacion.id_cliente == cliente_id)
            if cliente_tipo == 3:
                q_act = q_act.filter(Ruta.servicio == 'Exclusivo')

        act_rows = q_act.all()
        act_counts = {}
        n_rutas_map = {}
        last_act_map = {}

        for mid, f_date, cnt, max_dt in act_rows:
            act_counts[mid] = act_counts.get(mid, 0) + 1
            n_rutas_map[mid] = n_rutas_map.get(mid, 0) + cnt
            if mid not in last_act_map or (max_dt and max_dt > last_act_map[mid]):
                last_act_map[mid] = max_dt

        # Clasificación de clientes
        ids = list(asignados_map.keys())
        clas_rows = (
            db.query(MercaderistaRuta.mercaderista_id, func.count(RutaProgramacion.id_cliente.distinct()))
            .join(RutaProgramacion, RutaProgramacion.ruta_id == MercaderistaRuta.ruta_id)
            .filter(MercaderistaRuta.mercaderista_id.in_(ids), RutaProgramacion.activo == True)
            .group_by(MercaderistaRuta.mercaderista_id)
            .all()
        )
        for mid, n in clas_rows:
            if cliente_tipo == 3:
                asignados_map[mid]["tipo_servicio"] = "Exclusivo"
            else:
                asignados_map[mid]["tipo_servicio"] = "Exclusivo" if n == 1 else "Tradex"
            asignados_map[mid]["n_clientes_asignados"] = int(n)

        resultado = []
        for mid, m in asignados_map.items():
            n_plan = plan_counts.get(mid, 0)
            n_act = act_counts.get(mid, 0)
            plan_bool = n_plan > 0
            act_bool = n_act > 0

            if act_bool:
                estado = "Presente"
            elif plan_bool:
                estado = "Ausente"
            else:
                estado = "No Planificado"

            if estado_filtro == 'presentes' and estado != 'Presente':
                continue
            if estado_filtro == 'ausentes' and estado != 'Ausente':
                continue
            if estado_filtro == 'planificados' and not plan_bool:
                continue

            last_dt = last_act_map.get(mid)
            dt_str = str(last_dt) if last_dt else None

            resultado.append(DetalleMercaderistaItem(
                id_mercaderista=mid,
                nombre=m["nombre"],
                cedula=m["cedula"],
                tipo_campo=m["tipo_campo"],
                tipo_servicio=m.get("tipo_servicio", "Exclusivo"),
                planificado_hoy=plan_bool,
                planificados_total=n_plan,
                activo_hoy=act_bool,
                activos_total=n_act,
                rutas_activadas=n_rutas_map.get(mid, 0),
                n_clientes_asignados=m.get("n_clientes_asignados", 1),
                ultima_activacion=dt_str,
                estado_asistencia=estado
            ))

        resultado.sort(key=lambda x: (
            0 if x.estado_asistencia == 'Presente' else (1 if x.estado_asistencia == 'Ausente' else 2),
            x.nombre
        ))

        return DetalleMercaderistasResponse(
            success=True,
            total=len(resultado),
            mercaderistas=resultado
        )

    except Exception as e:
        return DetalleMercaderistasResponse(success=False, total=0, mercaderistas=[], message=str(e))
