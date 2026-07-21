"""
Endpoint /resumen-dia del Centro de Mando.

Optimizado con:
  - ThreadPoolExecutor para paralelizar consultas independientes
  - Caché Redis con TTL de 45s (datos en tiempo real)
  - Cada hilo crea su propia sesión de BD para seguridad thread-safe
"""
import calendar as _calendar
from datetime import date as _date, datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, aliased
from sqlalchemy import Date, func, case, exists
from app.shared.redis_cache import make_cache_key, check_cache, set_cache, _MISS

from app.db.session import get_db, SessionLocal
from app.core.dependencies import get_current_user, require_analyst_or_admin
from app.modules.auth.entities import Usuario
from app.modules.clients.entities import Cliente
from app.modules.routes.entities import Ruta, RutaProgramacion, PuntoInteres, RutaActivada, AnalistaRuta
from app.modules.merchandisers.entities import Mercaderista, MercaderistaRuta
from app.modules.visits.entities import Visita, Foto, Activacion
from app.modules.reporting.utils import _dia_es, _clientes_de_analista

router = APIRouter()


# ──────────────────────────────────────────────────────────────
#  Helpers de hilos — cada uno crea su propia sesión via SessionLocal
# ──────────────────────────────────────────────────────────────

def _run_asignados(sf, cliente_id, is_analyst_scoped, analista_cliente_ids, cliente_tipo):
    """Hilo 1 — Mercaderistas asignados + clasificación por tipo de servicio."""
    db = sf()
    try:
        q_asig = (
            db.query(
                Mercaderista.id,
                Mercaderista.nombre,
                Mercaderista.cedula,
                func.coalesce(Mercaderista.tipo, 'Mercaderista').label("tipo_camp")
            )
            .distinct()
            .join(MercaderistaRuta, MercaderistaRuta.mercaderista_id == Mercaderista.id)
            .join(RutaProgramacion, RutaProgramacion.ruta_id == MercaderistaRuta.ruta_id)
            .join(Ruta, Ruta.id == RutaProgramacion.ruta_id)
            .filter(Mercaderista.activo == True, RutaProgramacion.activo == True)
        )
        if cliente_id:
            q_asig = q_asig.filter(RutaProgramacion.id_cliente == cliente_id)
            if cliente_tipo == 3:
                q_asig = q_asig.filter(Ruta.servicio == 'Exclusivo')
        elif is_analyst_scoped:
            q_asig = q_asig.filter(RutaProgramacion.id_cliente.in_(analista_cliente_ids))

        asignados = q_asig.all()
        asignados_map = {
            r[0]: {
                "id_mercaderista": r[0], "nombre": r[1],
                "cedula": r[2], "tipo_campo": r[3]
            }
            for r in asignados
        }

        # Clasificación Exclusivo / Tradex (depende de asignados_map)
        if asignados_map:
            ids = list(asignados_map.keys())
            clas_rows = (
                db.query(
                    MercaderistaRuta.mercaderista_id,
                    func.count(RutaProgramacion.id_cliente.distinct())
                )
                .join(RutaProgramacion, RutaProgramacion.ruta_id == MercaderistaRuta.ruta_id)
                .filter(
                    MercaderistaRuta.mercaderista_id.in_(ids),
                    RutaProgramacion.activo == True
                )
                .group_by(MercaderistaRuta.mercaderista_id)
                .all()
            )
            for mid, n in clas_rows:
                asig = asignados_map[mid]
                if cliente_tipo == 3:
                    asig["tipo_servicio"] = "Exclusivo"
                else:
                    asig["tipo_servicio"] = "Exclusivo" if n == 1 else "Tradex"
                asig["n_clientes_asignados"] = int(n)

        for m in asignados_map.values():
            if cliente_tipo == 3:
                m["tipo_servicio"] = "Exclusivo"
            else:
                m.setdefault("tipo_servicio", "Exclusivo")
            m.setdefault("n_clientes_asignados", 1)

        return asignados_map
    finally:
        db.close()


def _run_planificados(sf, cliente_id, is_analyst_scoped, analista_cliente_ids,
                      cliente_tipo, days_in_range, day_counts):
    """Hilo 2 — Mercaderistas planificados (plan_counts)."""
    db = sf()
    try:
        q_plan = (
            db.query(Mercaderista.id, RutaProgramacion.dia)
            .distinct()
            .join(MercaderistaRuta, MercaderistaRuta.mercaderista_id == Mercaderista.id)
            .join(RutaProgramacion, RutaProgramacion.ruta_id == MercaderistaRuta.ruta_id)
            .join(Ruta, Ruta.id == RutaProgramacion.ruta_id)
            .filter(
                Mercaderista.activo == True,
                RutaProgramacion.activo == True,
                RutaProgramacion.dia.in_(days_in_range)
            )
        )
        if cliente_id:
            q_plan = q_plan.filter(RutaProgramacion.id_cliente == cliente_id)
            if cliente_tipo == 3:
                q_plan = q_plan.filter(Ruta.servicio == 'Exclusivo')
        elif is_analyst_scoped:
            q_plan = q_plan.filter(RutaProgramacion.id_cliente.in_(analista_cliente_ids))

        plan_hoy = q_plan.all()
        plan_counts: Dict[int, int] = {}
        for mid, dia in plan_hoy:
            plan_counts[mid] = plan_counts.get(mid, 0) + day_counts.get(dia, 0)
        return plan_counts
    finally:
        db.close()


def _run_activos_y_rutas_activadas(sf, cliente_id, is_analyst_scoped, analista_cliente_ids,
                                    cliente_tipo, d_desde, d_hasta):
    """Hilo 3 — Mercaderistas que activaron + filas RutaActivada."""
    db = sf()
    try:
        # Mercaderistas activos
        q_act = (
            db.query(
                RutaActivada.mercaderista_id,
                func.cast(RutaActivada.fecha_hora_activacion, Date)
            )
            .distinct()
            .join(MercaderistaRuta, MercaderistaRuta.ruta_id == RutaActivada.ruta_id)
            .join(RutaProgramacion, RutaProgramacion.ruta_id == RutaActivada.ruta_id)
            .join(Ruta, Ruta.id == RutaProgramacion.ruta_id)
            .filter(
                func.cast(RutaActivada.fecha_hora_activacion, Date) >= d_desde,
                func.cast(RutaActivada.fecha_hora_activacion, Date) <= d_hasta,
                MercaderistaRuta.mercaderista_id == RutaActivada.mercaderista_id
            )
        )
        if cliente_id:
            q_act = q_act.filter(RutaProgramacion.id_cliente == cliente_id)
            if cliente_tipo == 3:
                q_act = q_act.filter(Ruta.servicio == 'Exclusivo')
        elif is_analyst_scoped:
            q_act = q_act.filter(RutaProgramacion.id_cliente.in_(analista_cliente_ids))

        activos_rows = q_act.all()
        act_counts: Dict[int, int] = {}
        for mid, _fecha in activos_rows:
            if mid is not None:
                act_counts[mid] = act_counts.get(mid, 0) + 1

        # RutaActivada rows (needed for ruta_merc_pairs)
        ra_rows = (
            db.query(
                RutaActivada.ruta_id,
                RutaActivada.mercaderista_id,
                RutaActivada.estado,
                func.cast(RutaActivada.fecha_hora_activacion, Date)
            )
            .filter(
                func.cast(RutaActivada.fecha_hora_activacion, Date) >= d_desde,
                func.cast(RutaActivada.fecha_hora_activacion, Date) <= d_hasta
            )
            .all()
        )

        return act_counts, ra_rows
    finally:
        db.close()


def _run_rutas_pois_visitas(sf, cliente_id, is_analyst_scoped, analista_cliente_ids,
                             cliente_tipo, days_in_range, d_desde, d_hasta):
    """Hilo 4 — Rutas planificadas + POIs planificados + Visitas con fotos."""
    db = sf()
    try:
        # ── Rutas planificadas ──
        q_rutas_plan = (
            db.query(
                RutaProgramacion.ruta_id, Ruta.nombre,
                MercaderistaRuta.mercaderista_id, Mercaderista.nombre,
                RutaProgramacion.dia
            )
            .distinct()
            .join(Ruta, Ruta.id == RutaProgramacion.ruta_id)
            .join(MercaderistaRuta, MercaderistaRuta.ruta_id == RutaProgramacion.ruta_id)
            .join(Mercaderista, Mercaderista.id == MercaderistaRuta.mercaderista_id)
            .filter(
                RutaProgramacion.activo == True,
                Mercaderista.activo == True,
                RutaProgramacion.dia.in_(days_in_range)
            )
        )
        if cliente_id:
            q_rutas_plan = q_rutas_plan.filter(RutaProgramacion.id_cliente == cliente_id)
            if cliente_tipo == 3:
                q_rutas_plan = q_rutas_plan.filter(Ruta.servicio == 'Exclusivo')
        elif is_analyst_scoped:
            q_rutas_plan = q_rutas_plan.filter(RutaProgramacion.id_cliente.in_(analista_cliente_ids))
        rutas_plan_rows = q_rutas_plan.all()

        # ── POIs planificados ──
        q_pois_plan = (
            db.query(
                RutaProgramacion.punto_id, MercaderistaRuta.mercaderista_id,
                PuntoInteres.nombre, RutaProgramacion.ruta_id, Ruta.nombre,
                RutaProgramacion.dia, PuntoInteres.departamento,
                RutaProgramacion.prioridad
            )
            .distinct()
            .join(MercaderistaRuta, MercaderistaRuta.ruta_id == RutaProgramacion.ruta_id)
            .join(Ruta, Ruta.id == RutaProgramacion.ruta_id)
            .join(PuntoInteres, PuntoInteres.id == RutaProgramacion.punto_id)
            .join(Mercaderista, Mercaderista.id == MercaderistaRuta.mercaderista_id)
            .filter(
                RutaProgramacion.activo == True,
                Mercaderista.activo == True,
                RutaProgramacion.dia.in_(days_in_range)
            )
        )
        if cliente_id:
            q_pois_plan = q_pois_plan.filter(RutaProgramacion.id_cliente == cliente_id)
            if cliente_tipo == 3:
                q_pois_plan = q_pois_plan.filter(Ruta.servicio == 'Exclusivo')
        elif is_analyst_scoped:
            q_pois_plan = q_pois_plan.filter(RutaProgramacion.id_cliente.in_(analista_cliente_ids))
        pois_plan_rows = q_pois_plan.all()

        # ── Visitas con fotos (act/des) ──
        q_ev = (
            db.query(
                Visita.punto_id, Visita.mercaderista_id, Visita.id_cliente, Visita.fecha,
                func.max(case(((Foto.id_tipo_foto == 5) & (Foto.estado == 'Aprobada'), 1), else_=0)),
                func.max(case(((Foto.id_tipo_foto == 6) & (Foto.estado == 'Aprobada'), 1), else_=0))
            )
            .outerjoin(Foto, Foto.visita_id == Visita.id)
            .filter(Visita.fecha >= d_desde, Visita.fecha <= d_hasta)
        )
        if cliente_id:
            q_ev = q_ev.filter(Visita.id_cliente == cliente_id)
        elif is_analyst_scoped:
            q_ev = q_ev.filter(Visita.id_cliente.in_(analista_cliente_ids))
        q_ev = q_ev.group_by(Visita.punto_id, Visita.mercaderista_id, Visita.id_cliente, Visita.fecha)
        ev_rows = q_ev.all()

        return rutas_plan_rows, pois_plan_rows, ev_rows
    finally:
        db.close()


def _run_tradex(sf, cliente_id, is_analyst_scoped, analista_cliente_ids,
                days_in_range, d_desde, d_hasta, tradex_ids):
    """Hilo 5 — Consultas Tradex (plan + visitas full)."""
    if not tradex_ids:
        return [], [], {}
    db = sf()
    try:
        # Plan tradex
        q_tradex = (
            db.query(
                RutaProgramacion.punto_id, MercaderistaRuta.mercaderista_id,
                RutaProgramacion.id_cliente, RutaProgramacion.dia
            )
            .join(MercaderistaRuta, MercaderistaRuta.ruta_id == RutaProgramacion.ruta_id)
            .filter(
                RutaProgramacion.activo == True,
                RutaProgramacion.dia.in_(days_in_range),
                MercaderistaRuta.mercaderista_id.in_(tradex_ids)
            )
        )
        if is_analyst_scoped:
            q_tradex = q_tradex.filter(RutaProgramacion.id_cliente.in_(analista_cliente_ids))
        tradex_rows = q_tradex.all()

        # Visitas full tradex
        q_ev_full = (
            db.query(
                Visita.punto_id, Visita.mercaderista_id, Visita.id_cliente, Visita.fecha,
                func.max(case(((Foto.id_tipo_foto == 5) & (Foto.estado == 'Aprobada'), 1), else_=0)),
                func.max(case(((Foto.id_tipo_foto == 6) & (Foto.estado == 'Aprobada'), 1), else_=0))
            )
            .outerjoin(Foto, Foto.visita_id == Visita.id)
            .filter(Visita.fecha >= d_desde, Visita.fecha <= d_hasta)
            .group_by(Visita.punto_id, Visita.mercaderista_id, Visita.id_cliente, Visita.fecha)
        )
        ev_full = q_ev_full.all()

        # Post-process tradex
        ev_full_map = {
            (r[0], r[1], r[2], r[3]): {"act": bool(r[4]), "des": bool(r[5])}
            for r in ev_full
        }
        ev_full_agg: Dict[Tuple[int, int, int], Dict[str, int]] = {}
        for (id_p, id_m, id_c, _fd), st in ev_full_map.items():
            d = ev_full_agg.setdefault((id_p, id_m, id_c), {"act": 0, "com": 0})
            if st["act"]:
                d["act"] += 1
            if st["act"] and st["des"]:
                d["com"] += 1

        # Agrupar por (id_punto, id_merc, id_cliente)
        t_plan: Dict[Tuple[int, int, int], int] = {}
        for id_punto, id_merc, id_cli, dia in tradex_rows:
            key = (id_punto, id_merc, id_cli)
            t_plan[key] = t_plan.get(key, 0) + 1  # day_count is 1 per day in range

        return tradex_rows, ev_full, {
            "t_plan": t_plan,
            "ev_full_agg": ev_full_agg,
        }
    finally:
        db.close()


# ──────────────────────────────────────────────────────────────
#  Endpoint principal
# ──────────────────────────────────────────────────────────────

@router.get("/resumen-dia")
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

        analista_cliente_ids: List[int] = []
        if current_user.is_analyst and current_user.id_perfil:
            analista_id = int(current_user.id_perfil)
            analista_cliente_ids = _clientes_de_analista(db, analista_id)
            if cliente_id and cliente_id not in analista_cliente_ids:
                raise HTTPException(status_code=403, detail="No autorizado para este cliente")
        is_analyst_scoped = current_user.is_analyst and current_user.id_perfil and not cliente_id
        if is_analyst_scoped and not analista_cliente_ids:
            return {
                "success": True, "cliente_id": None, "cliente_nombre": "Sin clientes asignados",
                "desde": _date.today().isoformat(), "hasta": _date.today().isoformat(),
                "mercaderistas": {"total_asignados": 0, "planificados_hoy": 0, "activos_hoy": 0,
                                   "faltantes_hoy": 0, "exclusivos": 0, "tradex": 0,
                                   "detalle": [], "faltantes": [], "activos": []},
                "rutas": {"planificadas": 0, "activas": 0, "completadas": 0, "detalle": []},
                "puntos_interes": {"planificados": 0, "activos": 0, "completados": 0, "detalle": []},
                "clientes_tradex": {"planificados": 0, "activos": 0, "completados": 0, "aplica": False},
            }

        try:
            d_desde = datetime.strptime(desde, '%Y-%m-%d').date() if desde else _date.today()
            d_hasta = datetime.strptime(hasta, '%Y-%m-%d').date() if hasta else d_desde
        except ValueError:
            raise HTTPException(status_code=400, detail="Fecha inválida")

        if d_hasta < d_desde:
            d_hasta = d_desde

        cache_key = make_cache_key(
            "resumen_dia", desde, hasta, cliente_id,
            current_user.id, is_analyst_scoped,
            tuple(sorted(analista_cliente_ids))
        )
        cached_data = check_cache(cache_key)
        if type(cached_data) is not type(_MISS):
            return cached_data

        # ── Calcular days_in_range ──
        day_counts = {'Lunes': 0, 'Martes': 0, 'Miércoles': 0, 'Jueves': 0,
                      'Viernes': 0, 'Sábado': 0, 'Domingo': 0}
        curr = d_desde
        while curr <= d_hasta:
            day_counts[_dia_es(curr)] += 1
            curr += timedelta(days=1)

        days_in_range = [d for d, c in day_counts.items() if c > 0]
        if not days_in_range:
            days_in_range = ['Lunes']

        # ── Cliente info (rápido, en main thread) ──
        cliente_tipo = None
        cliente_nombre = "Todos los clientes"
        if cliente_id:
            cli = db.query(Cliente.nombre, Cliente.id_tipo_cliente).filter(Cliente.id == cliente_id).first()
            if cli:
                cliente_nombre = cli[0] or f"Cliente {cliente_id}"
                cliente_tipo = cli[1]
            else:
                cliente_nombre = f"Cliente {cliente_id}"

        # ══════════════════════════════════════════════════════
        #  EJECUCIÓN PARALELA (hasta 5 hilos simultáneos)
        # ══════════════════════════════════════════════════════
        with ThreadPoolExecutor(max_workers=5) as ex:
            f_asig = ex.submit(
                _run_asignados, SessionLocal, cliente_id, is_analyst_scoped,
                analista_cliente_ids, cliente_tipo
            )
            f_plan = ex.submit(
                _run_planificados, SessionLocal, cliente_id, is_analyst_scoped,
                analista_cliente_ids, cliente_tipo, days_in_range, day_counts
            )
            f_act = ex.submit(
                _run_activos_y_rutas_activadas, SessionLocal, cliente_id,
                is_analyst_scoped, analista_cliente_ids, cliente_tipo,
                d_desde, d_hasta
            )
            f_rpv = ex.submit(
                _run_rutas_pois_visitas, SessionLocal, cliente_id,
                is_analyst_scoped, analista_cliente_ids, cliente_tipo,
                days_in_range, d_desde, d_hasta
            )

            # Recolectar resultados
            asignados_map = f_asig.result()
            plan_counts = f_plan.result()
            act_counts, ra_rows = f_act.result()
            rutas_plan_rows, pois_plan_rows, ev_rows = f_rpv.result()

        # ──────────────────────────────────────────────────────
        #  POST-PROCESAMIENTO (main thread, solo Python)
        # ──────────────────────────────────────────────────────

        # Calcular totales planificados
        total_planificados = sum(plan_counts.values())

        # ── Construir ruta_merc_pairs ──
        ruta_merc_pairs = {}
        for rid, ruta_nombre, mid, nombre_merc, dia in rutas_plan_rows:
            k = (rid, mid)
            if k not in ruta_merc_pairs:
                ruta_merc_pairs[k] = {
                    "id_ruta": rid, "ruta": ruta_nombre,
                    "id_mercaderista": mid, "nombre_mercaderista": nombre_merc,
                    "estado": "Planificada",
                    "planificadas": 0, "activas": 0, "completadas": 0,
                    "pois_plan": 0, "pois_act": 0, "pois_com": 0,
                    "clientes_plan": 0, "clientes_act": 0, "clientes_com": 0
                }
            ruta_merc_pairs[k]["planificadas"] += day_counts.get(dia, 0)

        for rid, mid, estado, _fd in ra_rows:
            k = (rid, mid)
            if k in ruta_merc_pairs:
                if estado == 'Finalizado':
                    ruta_merc_pairs[k]["completadas"] += 1
                    ruta_merc_pairs[k]["activas"] += 1
                elif estado == 'En Progreso':
                    ruta_merc_pairs[k]["activas"] += 1

        rutas_planificadas = sum(x["planificadas"] for x in ruta_merc_pairs.values())
        rutas_activas = sum(x["activas"] for x in ruta_merc_pairs.values())
        rutas_completadas = sum(x["completadas"] for x in ruta_merc_pairs.values())

        # ── Construir estado_visita ──
        estado_visita = {
            (r[0], r[1], r[2], r[3]): {"act": bool(r[4]), "des": bool(r[5])}
            for r in ev_rows
        }

        ev_agg: Dict[Tuple[int, int], Dict[str, int]] = {}
        for (id_punto, id_merc, _cli, _fd), st in estado_visita.items():
            d = ev_agg.setdefault((id_punto, id_merc), {"act": 0, "com": 0})
            if st["act"]:
                d["act"] += 1
            if st["act"] and st["des"]:
                d["com"] += 1

        ev_agg_cli: Dict[Tuple[int, int, int], Dict[str, int]] = {}
        for (id_punto, id_merc, id_cli, _fd), st in estado_visita.items():
            d = ev_agg_cli.setdefault((id_punto, id_merc, id_cli), {"act": 0, "com": 0})
            if st["act"]:
                d["act"] += 1
            if st["act"] and st["des"]:
                d["com"] += 1

        # ── Construir pois_status ──
        pois_status = {}
        for id_punto, id_merc, nombre_punto, id_ruta, ruta_nombre, dia, depto, prio in pois_plan_rows:
            key = (id_punto, id_merc)
            if key not in pois_status:
                pois_status[key] = {
                    "id_punto": id_punto, "punto_de_interes": nombre_punto,
                    "id_mercaderista": id_merc, "id_ruta": id_ruta, "ruta": ruta_nombre,
                    "mercaderista": asignados_map.get(id_merc, {}).get("nombre", "Desconocido"),
                    "departamento": depto, "prioridad": prio,
                    "plan": 0, "act": 0, "com": 0,
                    "clientes_plan": 0, "clientes_act": 0, "clientes_com": 0
                }
            pois_status[key]["plan"] += day_counts.get(dia, 0)
            pois_status[key]["clientes_plan"] += day_counts.get(dia, 0)

        for key, ent in pois_status.items():
            if cliente_id is not None:
                ev_c = ev_agg_cli.get((key[0], key[1], cliente_id))
                if ev_c:
                    ent["act"] = ev_c["act"]
                    ent["com"] = ev_c["com"]
                    ent["clientes_act"] = ev_c["act"]
                    ent["clientes_com"] = ev_c["com"]
            else:
                ag = ev_agg.get(key)
                if ag:
                    ent["act"] = ag["act"]
                    ent["com"] = ag["com"]
                    ent["clientes_act"] = ag["act"]
                    ent["clientes_com"] = ag["com"]

            pair = ruta_merc_pairs.get((ent["id_ruta"], ent["id_mercaderista"]))
            if pair is not None:
                pair["pois_plan"] += ent["plan"]
                pair["pois_act"] += ent["act"]
                pair["pois_com"] += ent["com"]
                pair["clientes_plan"] += ent["clientes_plan"]
                pair["clientes_act"] += ent["clientes_act"]
                pair["clientes_com"] += ent["clientes_com"]

        pois_planificados = sum(v["plan"] for v in pois_status.values())
        pois_activos = sum(v["act"] for v in pois_status.values())
        pois_completados = sum(v["com"] for v in pois_status.values())

        # ── Tradex (necesita asignados_map ya resuelto) ──
        tradex_ids = [mid for mid, m in asignados_map.items()
                      if m.get("tipo_servicio") == "Tradex"]
        tradex_data = _run_tradex(
            SessionLocal, cliente_id, is_analyst_scoped, analista_cliente_ids,
            days_in_range, d_desde, d_hasta, tradex_ids
        )
        _tradex_rows, _ev_full, tradex_agg = tradex_data

        clientes_plan = clientes_act = clientes_com = 0
        if tradex_agg:
            t_plan = tradex_agg.get("t_plan", {})
            ev_full_agg = tradex_agg.get("ev_full_agg", {})
            clientes_plan = sum(t_plan.values())
            for key, plan_cnt in t_plan.items():
                ev = ev_full_agg.get(key)
                if ev:
                    clientes_act += ev["act"]
                    clientes_com += ev["com"]

        # ── Detalle mercaderistas ──
        merc_pois: Dict[int, Dict[str, int]] = {}
        for (_id_punto, id_merc), ent in pois_status.items():
            d = merc_pois.setdefault(id_merc, {"pois_plan": 0, "pois_act": 0, "pois_com": 0})
            d["pois_plan"] += ent["plan"]
            d["pois_act"] += ent["act"]
            d["pois_com"] += ent["com"]

        merc_rutas: Dict[int, Dict] = {}
        for (_id_ruta, id_merc), ent in ruta_merc_pairs.items():
            d = merc_rutas.setdefault(id_merc, {
                "rutas_plan": 0, "rutas_act": 0, "rutas_com": 0, "rutas_nombres": []
            })
            d["rutas_plan"] += ent["planificadas"]
            d["rutas_act"] += ent["activas"]
            d["rutas_com"] += ent["completadas"]
            if ent["ruta"] not in d["rutas_nombres"]:
                d["rutas_nombres"].append(ent["ruta"])

        mercaderistas_detalle = []
        faltantes = []
        activos = []

        for mid, m in asignados_map.items():
            p_cnt = plan_counts.get(mid, 0)
            a_cnt = act_counts.get(mid, 0)
            faltas = max(0, p_cnt - a_cnt)

            mp = merc_pois.get(mid, {"pois_plan": 0, "pois_act": 0, "pois_com": 0})
            mr = merc_rutas.get(mid, {"rutas_plan": 0, "rutas_act": 0, "rutas_com": 0, "rutas_nombres": []})

            estado = ("No planificado" if p_cnt == 0 else
                      ("Faltante" if faltas > 0 else "Activo"))

            det = {
                **m,
                "planificado_hoy": p_cnt > 0,
                "planificados": p_cnt,
                "activos": a_cnt,
                "faltas": faltas,
                "estado": estado,
                "rutas_planificadas": mr["rutas_plan"],
                "rutas_activas": mr["rutas_act"],
                "rutas_completadas": mr["rutas_com"],
                "rutas_nombres": mr["rutas_nombres"],
                "pois_planificados": mp["pois_plan"],
                "pois_activos": mp["pois_act"],
                "pois_completados": mp["pois_com"],
            }
            mercaderistas_detalle.append(det)
            if faltas > 0:
                faltantes.append(det)
            if a_cnt > 0:
                activos.append(det)

        prio = {"Faltante": 0, "Activo": 1, "No planificado": 2}
        mercaderistas_detalle.sort(key=lambda x: (prio.get(x["estado"], 99), x["nombre"] or ""))

        total_faltantes = sum(
            max(0, plan_counts.get(m, 0) - act_counts.get(m, 0))
            for m in plan_counts.keys()
        )

        _result = {
            "success": True,
            "cliente_id": cliente_id,
            "cliente_nombre": cliente_nombre,
            "desde": d_desde.isoformat(),
            "hasta": d_hasta.isoformat(),
            "mercaderistas": {
                "total_asignados": len(asignados_map),
                "planificados_hoy": total_planificados,
                "activos_hoy": sum(act_counts.values()),
                "faltantes_hoy": total_faltantes,
                "exclusivos": sum(1 for m in asignados_map.values()
                                  if m["tipo_servicio"] == "Exclusivo"),
                "tradex": sum(1 for m in asignados_map.values()
                              if m["tipo_servicio"] == "Tradex"),
                "detalle": mercaderistas_detalle,
                "faltantes": faltantes,
                "activos": activos,
            },
            "rutas": {
                "planificadas": rutas_planificadas,
                "activas": rutas_activas,
                "completadas": rutas_completadas,
                "detalle": list(ruta_merc_pairs.values()),
            },
            "puntos_interes": {
                "planificados": pois_planificados,
                "activos": pois_activos,
                "completados": pois_completados,
                "detalle": list(pois_status.values()),
            },
            "clientes_tradex": {
                "planificados": clientes_plan,
                "activos": clientes_act,
                "completados": clientes_com,
                "aplica": bool(tradex_ids),
            },
        }

        set_cache(cache_key, 45, _result)
        return _result

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
