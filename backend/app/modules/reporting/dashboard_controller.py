import calendar as _calendar
from datetime import date as _date, datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, aliased
from sqlalchemy import func

from app.db.session import get_db
from app.core.dependencies import get_current_user, require_analyst_or_admin
from app.modules.auth.entities import Usuario
from app.modules.clients.entities import Cliente
from app.modules.routes.entities import Ruta, RutaProgramacion, PuntoInteres, RutaActivada, AnalistaRuta
from app.modules.merchandisers.entities import Mercaderista, MercaderistaRuta
from app.modules.visits.entities import Visita, Foto
from app.modules.analysts.entities import AnalistaCliente
from app.modules.reporting.dto import (
    ClienteCentroMandoResponse, ClienteCentroMandoItem,
    ResumenDiaResponse, ResumenDiaFiltrosAplicados, ResumenDiaKpis,
    DetalleMercaderistasResponse, DetalleMercaderistaItem,
    FiltrosOpcionesResponse, PuntoFilterItem,
    FotosVisualizadorResponse, FotoVisualizadorItem
)
from app.shared.azure_service import azure_service

router = APIRouter(prefix="/api/centro-mando", tags=["Centro de Mando"])

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


@router.get("/clientes", response_model=ClienteCentroMandoResponse)
def listar_clientes(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    try:
        q = (
            db.query(Cliente.id, Cliente.nombre)
            .distinct()
            .join(RutaProgramacion, RutaProgramacion.id_cliente == Cliente.id)
            .filter(RutaProgramacion.activo == True, Cliente.nombre.isnot(None))
        )
        if current_user.is_analyst and current_user.id_perfil:
            analista_id = int(current_user.id_perfil)
            sub_rp = (
                db.query(RutaProgramacion.id_cliente)
                .join(AnalistaRuta, RutaProgramacion.ruta_id == AnalistaRuta.id_ruta)
                .filter(AnalistaRuta.id_analista == analista_id)
                .subquery()
            )
            sub_ac = (
                db.query(AnalistaCliente.id_cliente)
                .filter(AnalistaCliente.id_analista == analista_id)
                .subquery()
            )
            q = q.filter(Cliente.id.in_(sub_rp), Cliente.id.in_(sub_ac))

        rows = q.order_by(Cliente.nombre).all()
        return ClienteCentroMandoResponse(
            success=True,
            clientes=[ClienteCentroMandoItem(id_cliente=r[0], cliente=r[1]) for r in rows]
        )
    except Exception as e:
        return ClienteCentroMandoResponse(success=False, message=str(e), clientes=[])


@router.get("/resumen-dia", response_model=ResumenDiaResponse)
def resumen_dia(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    cliente_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    try:
        if current_user.is_client and not current_user.rol == 'admin':
            cliente_id = current_user.id_perfil

        try:
            d_desde = datetime.strptime(desde, '%Y-%m-%d').date() if desde else _date.today()
            d_hasta = datetime.strptime(hasta, '%Y-%m-%d').date() if hasta else d_desde
        except ValueError:
            raise HTTPException(status_code=400, detail="Fecha inválida")
            
        if d_hasta < d_desde:
            d_hasta = d_desde

        day_counts = { 'Lunes':0, 'Martes':0, 'Miércoles':0, 'Jueves':0, 'Viernes':0, 'Sábado':0, 'Domingo':0 }
        curr = d_desde
        while curr <= d_hasta:
            day_counts[_dia_es(curr)] += 1
            curr += timedelta(days=1)
            
        days_in_range = [d for d, c in day_counts.items() if c > 0]
        if not days_in_range:
            days_in_range = ['Lunes']

        cliente_tipo = None
        cliente_nombre = "Todos los clientes"
        if cliente_id:
            cli = db.query(Cliente.nombre, Cliente.id_tipo_cliente).filter(Cliente.id == cliente_id).first()
            if cli:
                cliente_nombre = cli[0] or f"Cliente {cliente_id}"
                cliente_tipo = cli[1]
            else:
                cliente_nombre = f"Cliente {cliente_id}"

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
        asignados_map = {
            r[0]: {
                "id_mercaderista": r[0],
                "nombre": r[1],
                "cedula": r[2],
                "tipo_campo": r[3] or "Mercaderista"
            }
            for r in asignados
        }

        # Planificados hoy
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

        plan_hoy = q_plan.all()
        plan_counts = {}
        for mid, dia in plan_hoy:
            plan_counts[mid] = plan_counts.get(mid, 0) + day_counts.get(dia, 0)

        total_planificados = sum(plan_counts.values())

        # Activos hoy
        q_act = (
            db.query(RutaActivada.id_mercaderista, func.cast(RutaActivada.fecha_hora_activacion, _date))
            .distinct()
            .join(MercaderistaRuta, MercaderistaRuta.ruta_id == RutaActivada.ruta_id)
            .join(RutaProgramacion, RutaProgramacion.ruta_id == RutaActivada.ruta_id)
            .outerjoin(Ruta, Ruta.id == RutaProgramacion.ruta_id)
            .filter(
                func.cast(RutaActivada.fecha_hora_activacion, _date) >= d_desde,
                func.cast(RutaActivada.fecha_hora_activacion, _date) <= d_hasta,
                MercaderistaRuta.mercaderista_id == RutaActivada.id_mercaderista
            )
        )
        if cliente_id:
            q_act = q_act.filter(RutaProgramacion.id_cliente == cliente_id)
            if cliente_tipo == 3:
                q_act = q_act.filter(Ruta.servicio == 'Exclusivo')

        activos_rows = q_act.all()
        act_counts = {}
        for mid, f_date in activos_rows:
            act_counts[mid] = act_counts.get(mid, 0) + 1

        total_activos = sum(act_counts.values())

        # Clasificación de clientes asignados
        if asignados_map:
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

        for m in asignados_map.values():
            if cliente_tipo == 3:
                m["tipo_servicio"] = "Exclusivo"
            else:
                m.setdefault("tipo_servicio", "Exclusivo")
            m.setdefault("n_clientes_asignados", 1)

        total_asig = len(asignados_map)
        cob_pct = round((total_planificados / total_asig * 100), 1) if total_asig > 0 else 0.0
        ejec_pct = round((total_activos / total_planificados * 100), 1) if total_planificados > 0 else 0.0
        pend = max(0, total_planificados - total_activos)

        return ResumenDiaResponse(
            success=True,
            cliente_nombre=cliente_nombre,
            filtros=ResumenDiaFiltrosAplicados(
                desde=str(d_desde),
                hasta=str(d_hasta),
                cliente_id=cliente_id,
                dias_evaluados=days_in_range
            ),
            kpis=ResumenDiaKpis(
                total_asignados=total_asig,
                total_planificados=total_planificados,
                cobertura_planificada_pct=cob_pct,
                total_activos=total_activos,
                ejecucion_activa_pct=ejec_pct,
                pendientes=pend
            )
        )

    except Exception as e:
        return ResumenDiaResponse(
            success=False,
            cliente_nombre="Error",
            filtros=ResumenDiaFiltrosAplicados(desde="", hasta="", cliente_id=cliente_id, dias_evaluados=[]),
            kpis=ResumenDiaKpis(total_asignados=0, total_planificados=0, cobertura_planificada_pct=0.0, total_activos=0, ejecucion_activa_pct=0.0, pendientes=0),
            message=str(e)
        )


@router.get("/detalle-mercaderistas", response_model=DetalleMercaderistasResponse)
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
                func.cast(RutaActivada.fecha_hora_activacion, _date),
                func.count(RutaActivada.id),
                func.max(RutaActivada.fecha_hora_activacion)
            )
            .join(MercaderistaRuta, MercaderistaRuta.ruta_id == RutaActivada.ruta_id)
            .join(RutaProgramacion, RutaProgramacion.ruta_id == RutaActivada.ruta_id)
            .outerjoin(Ruta, Ruta.id == RutaProgramacion.ruta_id)
            .filter(
                func.cast(RutaActivada.fecha_hora_activacion, _date) >= d_desde,
                func.cast(RutaActivada.fecha_hora_activacion, _date) <= d_hasta,
                MercaderistaRuta.mercaderista_id == RutaActivada.id_mercaderista
            )
            .group_by(RutaActivada.id_mercaderista, func.cast(RutaActivada.fecha_hora_activacion, _date))
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


@router.get("/filtros-opciones", response_model=FiltrosOpcionesResponse)
def filtros_opciones(
    cliente_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    try:
        if current_user.is_client and not current_user.rol == 'admin':
            cliente_id = current_user.id_perfil

        base_q = (
            db.query(PuntoInteres.cadena, PuntoInteres.departamento, Ruta.cuadrante, PuntoInteres.id, PuntoInteres.nombre)
            .distinct()
            .join(RutaProgramacion, RutaProgramacion.punto_id == PuntoInteres.id)
            .outerjoin(Ruta, Ruta.id == RutaProgramacion.ruta_id)
            .filter(RutaProgramacion.activo == True)
        )
        if cliente_id:
            base_q = base_q.filter(RutaProgramacion.id_cliente == cliente_id)

        rows = base_q.all()

        cadenas = sorted({r[0] for r in rows if r[0]})
        regiones = sorted({r[1] for r in rows if r[1]})
        cuadrantes = sorted({r[2] for r in rows if r[2]})

        seen_pts = set()
        puntos = []
        for r in rows:
            if r[3] and r[3] not in seen_pts:
                seen_pts.add(r[3])
                puntos.append(PuntoFilterItem(id=r[3], nombre=r[4] or ""))

        puntos.sort(key=lambda x: x.nombre)

        return FiltrosOpcionesResponse(
            success=True,
            cadenas=cadenas,
            regiones=regiones,
            cuadrantes=cuadrantes,
            puntos=puntos
        )
    except Exception as e:
        return FiltrosOpcionesResponse(success=False, message=str(e))


@router.get("/fotos-visualizador", response_model=FotosVisualizadorResponse)
def fotos_visualizador(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    cliente_id: Optional[int] = None,
    cadena: Optional[str] = None,
    region: Optional[str] = None,
    cuadrante: Optional[str] = None,
    punto_id: Optional[str] = None,
    mercaderista_id: Optional[int] = None,
    estado_foto: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    try:
        if current_user.is_client and not current_user.rol == 'admin':
            cliente_id = current_user.id_perfil

        fi = datetime.strptime(desde, '%Y-%m-%d').date() if desde else _date.today()
        ff = datetime.strptime(hasta, '%Y-%m-%d').date() if hasta else fi

        q = (
            db.query(
                Foto.id,
                Foto.visita_id,
                Foto.fecha_registro,
                Foto.blob_path,
                Foto.estado,
                Foto.id_tipo_foto,
                PuntoInteres.nombre.label("pdv_nombre"),
                PuntoInteres.cadena,
                PuntoInteres.departamento.label("region"),
                Mercaderista.nombre.label("mercaderista")
            )
            .join(Visita, Foto.visita_id == Visita.id)
            .outerjoin(PuntoInteres, PuntoInteres.id == Visita.punto_id)
            .outerjoin(Mercaderista, Mercaderista.id == Visita.mercaderista_id)
            .outerjoin(RutaProgramacion, (RutaProgramacion.punto_id == PuntoInteres.id) & (RutaProgramacion.id_cliente == Visita.id_cliente))
            .outerjoin(Ruta, Ruta.id == RutaProgramacion.ruta_id)
            .filter(Visita.fecha >= fi, Visita.fecha <= ff)
        )

        if cliente_id:
            q = q.filter(Visita.id_cliente == cliente_id)
        if cadena:
            q = q.filter(PuntoInteres.cadena == cadena)
        if region:
            q = q.filter(PuntoInteres.departamento == region)
        if cuadrante:
            q = q.filter(Ruta.cuadrante == cuadrante)
        if punto_id:
            q = q.filter(Visita.punto_id == punto_id)
        if mercaderista_id:
            q = q.filter(Visita.mercaderista_id == mercaderista_id)
        if estado_foto:
            q = q.filter(Foto.estado == estado_foto)

        total = q.count()
        rows = q.order_by(Foto.fecha_registro.desc(), Foto.id.desc()).offset(offset).limit(limit).all()

        fotos_list = []
        for r in rows:
            blob_path = r[3]
            url = None
            if blob_path:
                try:
                    url = azure_service.get_sas_url(blob_path)
                except Exception:
                    url = f"/api/merc/foto/{r[0]}"

            fotos_list.append(FotoVisualizadorItem(
                id_foto=r[0],
                visita_id=r[1],
                fecha=str(r[2]) if r[2] else None,
                blob_path=blob_path,
                url=url,
                estado=r[4],
                tipo_nombre=f"Tipo {r[5]}" if r[5] else "General",
                pdv_nombre=r[6],
                cadena=r[7],
                region=r[8],
                mercaderista=r[9]
            ))

        return FotosVisualizadorResponse(
            success=True,
            total=total,
            fotos=fotos_list
        )

    except Exception as e:
        return FotosVisualizadorResponse(success=False, total=0, fotos=[], message=str(e))
