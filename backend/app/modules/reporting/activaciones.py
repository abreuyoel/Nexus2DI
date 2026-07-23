"""Endpoint de activaciones del Centro de Mando.

Optimizado con:
  - ThreadPoolExecutor para paralelizar consultas independientes
  - TTL adaptativo de caché (histórico ⇢ 1h, tiempo real ⇢ 45s)
  - Caché compartida entre usuarios (clave sin current_user.id)
"""
import calendar as _calendar
from datetime import date as _date, datetime, timedelta
from typing import Optional, List, Dict, Any
from collections import defaultdict as _dd
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, aliased
from sqlalchemy import Date, func, case, exists, literal_column, cast, String

from app.db.session import get_db, SessionLocal
from app.core.dependencies import get_current_user, require_analyst_or_admin
from app.modules.auth.entities import Usuario
from app.modules.clients.entities import Cliente
from app.modules.routes.entities import Ruta, RutaProgramacion, PuntoInteres, RutaActivada, AnalistaRuta
from app.modules.merchandisers.entities import Mercaderista, MercaderistaRuta
from app.modules.visits.entities import Visita, Foto, Activacion
from app.modules.analysts.entities import AnalistaCliente, Analista
from app.modules.chat.entities import ChatMensaje
from app.shared.azure_service import azure_service
from app.modules.reporting.utils import _dia_es, _clientes_de_analista
from app.shared.redis_cache import make_cache_key, check_cache, set_cache, _MISS

router = APIRouter()


# ──────────────────────────────────────────────
#  Thread‑safe query helpers (cada una crea su
#  propia sesión para ser usada en ThreadPool)
# ──────────────────────────────────────────────

def _run_main_query(sf, query_cols, act_alias, des_alias, ruta_pre_alias, chat_pre_alias,
                    d_desde, d_hasta, cliente_id, is_analyst, analista_id):
    """Hilo 1 — Consulta principal de visitas con activación/desactivación."""
    db = sf()
    try:
        q = (
            db.query(*query_cols)
            .join(Cliente, Visita.id_cliente == Cliente.id)
            .join(PuntoInteres, Visita.punto_id == PuntoInteres.id)
            .join(Mercaderista, Visita.mercaderista_id == Mercaderista.id)
            .outerjoin(act_alias, (act_alias.c.visita_id == Visita.id) & (act_alias.c.rn == 1))
            .outerjoin(des_alias, (des_alias.c.visita_id == Visita.id) & (des_alias.c.rn == 1))
            .outerjoin(ruta_pre_alias, (ruta_pre_alias.c.id_punto_interes == PuntoInteres.id) & (ruta_pre_alias.c.rn == 1))
            .outerjoin(chat_pre_alias, chat_pre_alias.c.visita_id == Visita.id)
            .filter((act_alias.c.id_foto.isnot(None)) | (des_alias.c.id_foto.isnot(None)))
            .filter(Visita.fecha >= d_desde, Visita.fecha <= d_hasta)
        )
        if cliente_id:
            q = q.filter(Cliente.id == cliente_id)
        if is_analyst and analista_id:
            q = q.filter(
                exists()
                .where(RutaProgramacion.punto_id == PuntoInteres.id)
                .where(RutaProgramacion.activo == True)
                .where(AnalistaRuta.id_ruta == RutaProgramacion.ruta_id)
                .where(AnalistaRuta.id_analista == analista_id)
            )
        return q.order_by(Visita.fecha.desc()).all()
    finally:
        db.close()


def _run_secondary_queries(sf,
                           d_desde, d_hasta, cliente_id, is_analyst, analista_id):
    """Hilo 2 — Plan count + UNION ALL planned breakdowns.

    Returns
    -------
    tuple
        (total_planificadas, planned_pp, planned_pc, planned_merc)
    """
    db = sf()
    try:
        # ── Plan count ──
        pq = (
            db.query(func.count(Visita.id.distinct()))
            .join(Cliente, Visita.id_cliente == Cliente.id)
            .join(PuntoInteres, Visita.punto_id == PuntoInteres.id)
            .filter(Visita.fecha >= d_desde, Visita.fecha <= d_hasta)
        )
        if cliente_id:
            pq = pq.filter(Cliente.id == cliente_id)
        if is_analyst and analista_id:
            pq = pq.filter(
                exists()
                .where(RutaProgramacion.punto_id == PuntoInteres.id)
                .where(RutaProgramacion.activo == True)
                .where(AnalistaRuta.id_ruta == RutaProgramacion.ruta_id)
                .where(AnalistaRuta.id_analista == analista_id)
            )
        total_planificadas = pq.scalar() or 0

        # ── UNION ALL planned breakdowns ──
        _pf = [Visita.fecha >= d_desde, Visita.fecha <= d_hasta]
        if cliente_id:
            _pf.append(Cliente.id == cliente_id)

        _af = None
        if is_analyst and analista_id:
            _af = exists().where(RutaProgramacion.punto_id == PuntoInteres.id) \
                         .where(RutaProgramacion.activo == True) \
                         .where(AnalistaRuta.id_ruta == RutaProgramacion.ruta_id) \
                         .where(AnalistaRuta.id_analista == analista_id)

        q_pp = (
            db.query(literal_column("'pp'").label("grp"),
                     cast(PuntoInteres.id, String(255)).label("gid"),
                     func.count(Visita.id.distinct()).label("cnt"))
            .join(Cliente, Visita.id_cliente == Cliente.id)
            .join(PuntoInteres, Visita.punto_id == PuntoInteres.id)
            .filter(*_pf)
        )
        if _af is not None:
            q_pp = q_pp.filter(_af)
        q_pp = q_pp.group_by(cast(PuntoInteres.id, String(255)))

        q_pc = (
            db.query(literal_column("'pc'").label("grp"),
                     cast(Cliente.id, String(255)).label("gid"),
                     func.count(Visita.id.distinct()).label("cnt"))
            .join(Cliente, Visita.id_cliente == Cliente.id)
            .join(PuntoInteres, Visita.punto_id == PuntoInteres.id)
            .filter(*_pf)
        )
        if _af is not None:
            q_pc = q_pc.filter(_af)
        q_pc = q_pc.group_by(Cliente.id)

        q_pm = (
            db.query(literal_column("'pm'").label("grp"),
                     cast(Mercaderista.id, String(255)).label("gid"),
                     func.count(Visita.id.distinct()).label("cnt"))
            .join(Cliente, Visita.id_cliente == Cliente.id)
            .join(PuntoInteres, Visita.punto_id == PuntoInteres.id)
            .join(Mercaderista, Visita.mercaderista_id == Mercaderista.id)
            .filter(*_pf)
        )
        if _af is not None:
            q_pm = q_pm.filter(_af)
        q_pm = q_pm.group_by(Mercaderista.id)

        _merged = q_pp.union_all(q_pc, q_pm).all()

        planned_pp = {}
        planned_pc = {}
        planned_merc = {}
        for grp, gid, cnt in _merged:
            if gid is None:
                continue
            tgt = {'pp': planned_pp, 'pc': planned_pc, 'pm': planned_merc}[grp]
            key = gid if grp == 'pp' else int(gid)
            tgt[key] = int(cnt)

        return total_planificadas, planned_pp, planned_pc, planned_merc
    finally:
        db.close()


def _run_pending_query(sf,
                       d_desde, d_hasta, cliente_id, is_analyst, analista_id):
    """Hilo 3 — Pendientes por mercaderista.

    Returns
    -------
    tuple
        (pend_rows_raw, dias_rango)
    """
    db = sf()
    try:
        # ── Calcular días del rango ──
        _dias_set = set()
        _cur = d_desde
        while _cur <= d_hasta:
            _dias_set.add(_dia_es(_cur))
            _cur += timedelta(days=1)
        dias_rango = list(_dias_set)

        if not dias_rango:
            return [], dias_rango

        # ── Subquery con DISTINCT + labels únicos ──
        inner_q = (
            db.query(
                Mercaderista.id.label("mid"),
                Mercaderista.nombre.label("mnom"),
                PuntoInteres.id.label("pid"),
                PuntoInteres.nombre.label("pnom"),
                RutaProgramacion.id_cliente.label("idc"),
                func.coalesce(Cliente.nombre, '').label("cliente"),
                func.coalesce(PuntoInteres.ciudad, '').label("ciudad"),
                func.coalesce(Ruta.nombre, 'Sin ruta').label("ruta"),
                func.coalesce(PuntoInteres.departamento, '').label("departamento"),
                func.coalesce(RutaProgramacion.prioridad, '').label("prioridad"),
                func.coalesce(Ruta.cuadrante, '').label("cuadrante")
            )
            .distinct()
            .join(MercaderistaRuta, MercaderistaRuta.mercaderista_id == Mercaderista.id)
            .join(RutaProgramacion, RutaProgramacion.ruta_id == MercaderistaRuta.ruta_id)
            .join(Ruta, Ruta.id == RutaProgramacion.ruta_id)
            .join(PuntoInteres, PuntoInteres.id == RutaProgramacion.punto_id)
            .outerjoin(Cliente, Cliente.id == RutaProgramacion.id_cliente)
            .filter(
                Mercaderista.activo == True,
                RutaProgramacion.activo == True,
                RutaProgramacion.dia.in_(dias_rango)
            )
        )
        if cliente_id:
            inner_q = inner_q.filter(RutaProgramacion.id_cliente == cliente_id)
        if is_analyst and analista_id:
            inner_q = inner_q.filter(
                exists()
                .where(RutaProgramacion.punto_id == PuntoInteres.id)
                .where(RutaProgramacion.activo == True)
                .where(AnalistaRuta.id_ruta == RutaProgramacion.ruta_id)
                .where(AnalistaRuta.id_analista == analista_id)
            )

        pend_sub = inner_q.subquery()
        pend_rows = (
            db.query(pend_sub)
            .order_by(pend_sub.c.mnom, pend_sub.c.cliente)
            .all()
        )
        return pend_rows, dias_rango
    finally:
        db.close()


# ──────────────────────────────────────────────
#  Endpoint principal
# ──────────────────────────────────────────────

@router.get("/activaciones")
def get_activaciones(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    cliente_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    try:
        is_analyst = current_user.rol == 'analyst'

        if current_user.is_client and not current_user.rol == 'admin':
            cliente_id = current_user.id_perfil

        if desde and hasta:
            d_desde = datetime.strptime(desde, '%Y-%m-%d').date()
            d_hasta = datetime.strptime(hasta, '%Y-%m-%d').date()
        else:
            d_desde = _date.today()
            d_hasta = d_desde

        analista_id = int(current_user.id_perfil) if (is_analyst and current_user.id_perfil) else None

        # ── Redis cache check (clave SIN current_user.id para compartir entre usuarios) ──
        cache_key = make_cache_key(
            "activaciones", desde, hasta, cliente_id,
            is_analyst, analista_id
        )
        cached_data = check_cache(cache_key)
        if type(cached_data) is not type(_MISS):
            return cached_data

        # ── Window function subqueries for photos ──
        act_rn = (
            db.query(
                Foto.visita_id.label("visita_id"),
                Foto.id.label("id_foto"),
                Foto.blob_path.label("file_path"),
                Foto.fecha_registro.label("fecha_registro"),
                Foto.estado.label("Estado"),
                func.row_number().over(
                    partition_by=Foto.visita_id,
                    order_by=Foto.fecha_registro.desc()
                ).label("rn")
            )
            .filter(Foto.id_tipo_foto == 5)
            .subquery()
        )
        act_alias = aliased(act_rn, name="act")

        des_rn = (
            db.query(
                Foto.visita_id.label("visita_id"),
                Foto.id.label("id_foto"),
                Foto.blob_path.label("file_path"),
                Foto.fecha_registro.label("fecha_registro"),
                Foto.estado.label("Estado"),
                func.row_number().over(
                    partition_by=Foto.visita_id,
                    order_by=Foto.fecha_registro.desc()
                ).label("rn")
            )
            .filter(Foto.id_tipo_foto == 6)
            .subquery()
        )
        des_alias = aliased(des_rn, name="des")

        # ── Subquery for Route programming (ruta_pre) ──
        rp2 = aliased(RutaProgramacion, name="rp2")
        rn2 = aliased(Ruta, name="rn2")
        ar2 = aliased(AnalistaRuta, name="ar2")
        a2 = aliased(Analista, name="a2")

        ruta_pre_rn = (
            db.query(
                rp2.punto_id.label("id_punto_interes"),
                rn2.nombre.label("ruta"),
                rn2.id.label("id_ruta"),
                a2.nombre.label("analista"),
                rn2.cuadrante.label("cuadrante"),
                func.row_number().over(
                    partition_by=rp2.punto_id,
                    order_by=rn2.id
                ).label("rn")
            )
            .join(rn2, rp2.ruta_id == rn2.id)
            .outerjoin(ar2, ar2.id_ruta == rn2.id)
            .outerjoin(a2, a2.id == ar2.id_analista)
            .filter(rp2.activo == True)
            .subquery()
        )
        ruta_pre_alias = aliased(ruta_pre_rn, name="ruta_pre")

        # ── Subquery for chat unread messages ──
        chat_pre_q = (
            db.query(
                ChatMensaje.visita_id.label("visita_id"),
                func.sum(
                    case(((ChatMensaje.leido == False) & (ChatMensaje.sender_type == 'usuario'), 1), else_=0)
                ).label("no_leidos")
            )
            .group_by(ChatMensaje.visita_id)
            .subquery()
        )
        chat_pre_alias = aliased(chat_pre_q, name="chat_pre")

        # ── Main query projection columns ──
        query_cols = (
            Visita.id.label("id_visita"),
            Cliente.nombre.label("cliente"),
            Cliente.id.label("id_cliente"),
            PuntoInteres.nombre.label("punto_de_interes"),
            PuntoInteres.id.label("id_punto"),
            func.coalesce(PuntoInteres.departamento, '').label("departamento"),
            func.coalesce(PuntoInteres.ciudad, '').label("ciudad"),
            Mercaderista.nombre.label("mercaderista"),
            Mercaderista.id.label("id_mercaderista"),
            Visita.fecha.label("fecha_visita"),
            func.coalesce(PuntoInteres.jerarquia_n2, '').label("tipo_pdv"),

            act_alias.c.id_foto.label("id_foto_activacion"),
            act_alias.c.file_path.label("file_path_activacion"),
            act_alias.c.fecha_registro.label("fecha_activacion"),
            act_alias.c.Estado.label("estado_activacion"),

            des_alias.c.id_foto.label("id_foto_desactivacion"),
            des_alias.c.file_path.label("file_path_desactivacion"),
            des_alias.c.fecha_registro.label("fecha_desactivacion"),
            des_alias.c.Estado.label("estado_desactivacion"),

            func.coalesce(ruta_pre_alias.c.ruta, 'Sin ruta').label("ruta"),
            func.coalesce(ruta_pre_alias.c.id_ruta, 0).label("id_ruta"),
            func.coalesce(ruta_pre_alias.c.analista, '').label("nombre_analista"),
            func.coalesce(ruta_pre_alias.c.cuadrante, '').label("cuadrante"),

            func.coalesce(chat_pre_alias.c.no_leidos, 0).label("mensajes_no_leidos")
        )

        # ══════════════════════════════════════════
        #  EJECUCIÓN PARALELA (3 hilos)
        # ══════════════════════════════════════════
        with ThreadPoolExecutor(max_workers=3) as ex:
            f_main = ex.submit(
                _run_main_query, SessionLocal, query_cols,
                act_alias, des_alias, ruta_pre_alias, chat_pre_alias,
                d_desde, d_hasta, cliente_id, is_analyst, analista_id
            )
            f_sec = ex.submit(
                _run_secondary_queries, SessionLocal,
                d_desde, d_hasta, cliente_id, is_analyst, analista_id
            )
            f_pend = ex.submit(
                _run_pending_query, SessionLocal,
                d_desde, d_hasta, cliente_id, is_analyst, analista_id
            )

            rows = f_main.result()
            total_planificadas, planned_pp, planned_pc, planned_merc = f_sec.result()
            pend_rows, dias_rango = f_pend.result()

        # ──────────────────────────────────────────
        #  Procesamiento post‑consultas (todo en el
        #  hilo principal, solo transformación Python)
        # ──────────────────────────────────────────

        # SAS URL helper
        def _foto_url(path):
            if not path:
                return None
            try:
                return azure_service.get_sas_url(path)
            except Exception:
                return None

        activaciones = []
        seen_ids = set()
        total_con_activacion = total_con_desactivacion = 0
        total_completas = total_activos_ahora = 0
        rutas_set = set()
        rutas_eje_set = set()

        for row in rows:
            vid = row.id_visita
            if vid in seen_ids:
                continue
            seen_ids.add(vid)

            activaciones.append({
                "id_visita":               row.id_visita,
                "cliente":                 row.cliente,
                "id_cliente":              row.id_cliente,
                "punto_de_interes":        row.punto_de_interes,
                "id_punto":                row.id_punto,
                "departamento":            row.departamento,
                "ciudad":                  row.ciudad,
                "mercaderista":            row.mercaderista,
                "id_mercaderista":         row.id_mercaderista,
                "fecha_visita":            row.fecha_visita.isoformat() if row.fecha_visita else None,
                "tipo_pdv":                row.tipo_pdv,
                "id_foto_activacion":      row.id_foto_activacion,
                "file_path_activacion":    row.file_path_activacion,
                "url_activacion":          _foto_url(row.file_path_activacion),
                "fecha_activacion":        row.fecha_activacion.isoformat() if row.fecha_activacion else None,
                "estado_activacion":       row.estado_activacion,
                "id_foto_desactivacion":   row.id_foto_desactivacion,
                "file_path_desactivacion": row.file_path_desactivacion,
                "url_desactivacion":       _foto_url(row.file_path_desactivacion),
                "fecha_desactivacion":     row.fecha_desactivacion.isoformat() if row.fecha_desactivacion else None,
                "estado_desactivacion":    row.estado_desactivacion,
                "ruta":                    row.ruta,
                "id_ruta":                 row.id_ruta,
                "analista":                row.nombre_analista,
                "mensajes_no_leidos":      row.mensajes_no_leidos,
                "duracion_minutos":        None,
                "estado_presencia":        None,
                "foto_heredada":           False,
            })

        # ── Tradex Photo Propagation ──
        _grp = _dd(list)
        for v in activaciones:
            _grp[(v["id_mercaderista"], v["id_punto"], (v["fecha_visita"] or "")[:10])].append(v)
        for grp in _grp.values():
            act_src = next((x for x in grp if x["id_foto_activacion"]), None)
            des_src = next((x for x in grp if x["id_foto_desactivacion"]), None)
            for x in grp:
                if act_src and not x["id_foto_activacion"]:
                    x["id_foto_activacion"]   = act_src["id_foto_activacion"]
                    x["url_activacion"]       = act_src["url_activacion"]
                    x["file_path_activacion"] = act_src["file_path_activacion"]
                    x["fecha_activacion"]     = act_src["fecha_activacion"]
                    x["foto_heredada"]        = True
                if des_src and not x["id_foto_desactivacion"]:
                    x["id_foto_desactivacion"]   = des_src["id_foto_desactivacion"]
                    x["url_desactivacion"]       = des_src["url_desactivacion"]
                    x["file_path_desactivacion"] = des_src["file_path_desactivacion"]
                    x["fecha_desactivacion"]     = des_src["fecha_desactivacion"]
                    x["foto_heredada"]           = True

        # ── Recalculate execution state/durations ──
        for v in activaciones:
            ta = v["id_foto_activacion"] is not None
            td = v["id_foto_desactivacion"] is not None
            v["estado_presencia"] = "completa" if ta and td else ("activo" if ta else "solo_salida")
            if ta and td and v["fecha_activacion"] and v["fecha_desactivacion"]:
                try:
                    v["duracion_minutos"] = int(
                        (datetime.fromisoformat(v["fecha_desactivacion"]) - datetime.fromisoformat(v["fecha_activacion"])).total_seconds() / 60
                    )
                except Exception:
                    v["duracion_minutos"] = None
            if ta: total_con_activacion += 1
            if td: total_con_desactivacion += 1
            if ta and td: total_completas += 1
            if ta and not td: total_activos_ahora += 1
            if v["id_ruta"] and v["id_ruta"] != 0:
                rutas_set.add(v["id_ruta"])
                if ta: rutas_eje_set.add(v["id_ruta"])

        total = len(activaciones)

        # Asegurar total_planificadas >= total real
        if total_planificadas == 0:
            total_planificadas = total

        base_prog             = total_planificadas if total_planificadas > 0 else (total if total > 0 else 1)
        pct_cumplimiento      = round(total_con_activacion / base_prog * 100, 1)
        progreso_activaciones = round(total_con_activacion / base_prog * 100, 1)
        progreso_completas    = round(total_completas      / base_prog * 100, 1)

        # ── Procesar pendientes ──
        pendientes = []
        planned_merc_exec = {}   # mid -> set (id_punto, id_cliente) planificados
        planned_merc_info = {}   # mid -> nombre
        planned_merc_pdvs = {}   # mid -> set id_punto
        planned_merc_clis = {}   # mid -> set id_cliente

        if pend_rows:
            activated_pdv = {(v["id_mercaderista"], v["id_punto"]) for v in activaciones if v["id_foto_activacion"]}
            seen_pend = set()
            for r in pend_rows:
                mid, mnom, idp, pnom, idc, cli, ciu, ruta, depto, prio, cuad = r
                planned_merc_info[mid] = mnom
                planned_merc_exec.setdefault(mid, set()).add((idp, idc))
                planned_merc_pdvs.setdefault(mid, set()).add(idp)
                planned_merc_clis.setdefault(mid, set()).add(idc)
                if (mid, idp) in activated_pdv:
                    continue
                key = (idp, idc, mid)
                if key in seen_pend:
                    continue
                seen_pend.add(key)
                pendientes.append({
                    "id_punto": idp, "punto_de_interes": pnom,
                    "cliente": cli, "id_cliente": idc,
                    "mercaderista": mnom, "id_mercaderista": mid,
                    "ciudad": ciu, "ruta": ruta,
                    "departamento": depto, "prioridad": prio, "cuadrante": cuad
                })

        # ── Por mercaderista execution breakdown ──
        act_exec = {}    # mid -> set (id_punto, id_cliente) activadas
        com_exec = {}    # mid -> set completadas
        durs_merc = {}   # mid -> [duraciones]
        activo_now = {}  # mid -> bool (en punto)
        act_pdvs = {}    # mid -> set id_punto (fallback total_puntos)
        act_clis = {}    # mid -> set id_cliente
        nombre_merc = {}
        merc_rutas_set = {}
        merc_deptos_set = {}
        merc_cuads_set = {}
        for v in activaciones:
            mid = v["id_mercaderista"]; nombre_merc[mid] = v["mercaderista"]
            ek = (v["id_punto"], v["id_cliente"])
            if v["id_foto_activacion"]:            act_exec.setdefault(mid, set()).add(ek)
            if v["estado_presencia"] == "completa": com_exec.setdefault(mid, set()).add(ek)
            if v["estado_presencia"] == "activo":   activo_now[mid] = True
            act_pdvs.setdefault(mid, set()).add(v["id_punto"])
            act_clis.setdefault(mid, set()).add(v["id_cliente"])
            if v["duracion_minutos"] is not None:   durs_merc.setdefault(mid, []).append(v["duracion_minutos"])
            if v.get("ruta") and v["ruta"] != "Sin ruta": merc_rutas_set.setdefault(mid, set()).add(v["ruta"])
            if v.get("departamento"): merc_deptos_set.setdefault(mid, set()).add(v["departamento"])
            if v.get("cuadrante"): merc_cuads_set.setdefault(mid, set()).add(v["cuadrante"])

        pend_merc_count = {}
        for p in pendientes:
            mid = p["id_mercaderista"]
            pend_merc_count[mid] = pend_merc_count.get(mid, 0) + 1
            if p.get("ruta") and p["ruta"] != "Sin ruta": merc_rutas_set.setdefault(mid, set()).add(p["ruta"])
            if p.get("departamento"): merc_deptos_set.setdefault(mid, set()).add(p["departamento"])
            if p.get("cuadrante"): merc_cuads_set.setdefault(mid, set()).add(p["cuadrante"])

        all_mids = set(planned_merc_info.keys()) | set(nombre_merc.keys())
        por_mercaderista = []
        for mid in all_mids:
            activadas_cnt = len(act_exec.get(mid, set()))
            completas_cnt = len(com_exec.get(mid, set()))
            pend_cnt = pend_merc_count.get(mid, 0)
            planificadas_cnt = len(planned_merc_exec.get(mid, set()))
            if planificadas_cnt == 0:
                planificadas_cnt = activadas_cnt + pend_cnt
            planificadas_cnt = max(planificadas_cnt, activadas_cnt, completas_cnt)
            total_puntos = len(planned_merc_pdvs.get(mid, set())) or len(act_pdvs.get(mid, set()))
            total_clientes = len(planned_merc_clis.get(mid, set())) or len(act_clis.get(mid, set()))
            deptos_list = list(merc_deptos_set.get(mid, set()))
            deptos_str = " y ".join(deptos_list[:2])
            if len(deptos_list) > 2:
                deptos_str += f" (+{len(deptos_list) - 2})"
            elif not deptos_str:
                deptos_str = "Sin departamento"

            rutas_str = ", ".join(list(merc_rutas_set.get(mid, set())))
            if not rutas_str: rutas_str = "Sin ruta"

            cuads_str = ", ".join(list(merc_cuads_set.get(mid, set())))
            if not cuads_str: cuads_str = "Sin cuadrante"

            por_mercaderista.append({
                "nombre": planned_merc_info.get(mid) or nombre_merc.get(mid) or "?",
                "id_mercaderista": mid,
                "total": activadas_cnt,
                "planificadas": planificadas_cnt,
                "activaciones": activadas_cnt,
                "completas": completas_cnt,
                "pendientes": pend_cnt,
                "pct_activacion": round(activadas_cnt / planificadas_cnt * 100, 1) if planificadas_cnt else 0,
                "pct_completas":  round(completas_cnt / planificadas_cnt * 100, 1) if planificadas_cnt else 0,
                "activo_ahora": activo_now.get(mid, False),
                "total_puntos": total_puntos,
                "total_clientes": total_clientes,
                "duracion_prom": round(sum(durs_merc[mid]) / len(durs_merc[mid])) if durs_merc.get(mid) else None,
                "departamentos_str": deptos_str,
                "rutas_str": rutas_str,
                "cuadrantes_str": cuads_str,
            })
        por_mercaderista.sort(key=lambda x: x["pct_activacion"], reverse=True)

        # ── Desglose function ──
        def _desglose(key_fn, id_fn, planned_map):
            act_m, com_m = {}, {}
            for v in activaciones:
                k = key_fn(v); kid = id_fn(v)
                ta = v["id_foto_activacion"] is not None
                tc = v["estado_presencia"] == "completa"
                for mp, cond in [(act_m, ta), (com_m, tc)]:
                    if kid not in mp:
                        mp[kid] = {"nombre": k, "id": kid, "con": 0}
                    if cond:
                        mp[kid]["con"] += 1
            def _s(mp):
                out = []
                for kid, v in mp.items():
                    tot = max(planned_map.get(kid, 0), v["con"])
                    out.append({
                        "nombre": v["nombre"], "id": kid, "total": tot, "con": v["con"],
                        "porcentaje": round(v["con"] / tot * 100, 1) if tot else 0,
                    })
                return sorted(out, key=lambda x: x["porcentaje"], reverse=True)
            return _s(act_m), _s(com_m)

        pp_act, pp_com = _desglose(lambda v: v["punto_de_interes"], lambda v: v["id_punto"], planned_pp)
        pc_act, pc_com = _desglose(lambda v: v["cliente"], lambda v: v["id_cliente"], planned_pc)

        # ── Gestión por día (gestion_por_dia) ──
        act4_sub = (
            db.query(Foto.visita_id.label("visita_id"), func.min(Foto.id).label("id_foto"))
            .filter(Foto.id_tipo_foto == 5)
            .group_by(Foto.visita_id)
            .subquery()
        )
        des4_sub = (
            db.query(Foto.visita_id.label("visita_id"), func.min(Foto.id).label("id_foto"))
            .filter(Foto.id_tipo_foto == 6)
            .group_by(Foto.visita_id)
            .subquery()
        )
        act4_alias = aliased(act4_sub, name="act4")
        des4_alias = aliased(des4_sub, name="des4")

        ft4 = aliased(Foto, name="ft4")
        exists_foto = (
            exists()
            .where(ft4.visita_id == Visita.id)
            .where(ft4.id_tipo_foto.in_([5, 6]))
        )

        date_limit = _date.today() - timedelta(days=6)

        q_gpd = (
            db.query(
                Visita.fecha.label("fecha"),
                Cliente.nombre.label("cliente"),
                func.count(Visita.id.distinct()).label("total"),
                func.sum(case((act4_alias.c.id_foto.isnot(None), 1), else_=0)).label("ejecutadas"),
                func.sum(case(((act4_alias.c.id_foto.isnot(None)) & (des4_alias.c.id_foto.isnot(None)), 1), else_=0)).label("completas")
            )
            .join(Cliente, Visita.id_cliente == Cliente.id)
            .join(PuntoInteres, Visita.punto_id == PuntoInteres.id)
            .outerjoin(act4_alias, act4_alias.c.visita_id == Visita.id)
            .outerjoin(des4_alias, des4_alias.c.visita_id == Visita.id)
            .filter(Visita.fecha >= date_limit)
        )
        if cliente_id:
            q_gpd = q_gpd.filter(Cliente.id == cliente_id)
        if is_analyst and analista_id:
            q_gpd = q_gpd.filter(
                exists()
                .where(RutaProgramacion.punto_id == PuntoInteres.id)
                .where(RutaProgramacion.activo == True)
                .where(AnalistaRuta.id_ruta == RutaProgramacion.ruta_id)
                .where(AnalistaRuta.id_analista == analista_id)
            )

        q_gpd = q_gpd.group_by(Visita.fecha, Cliente.nombre).order_by(Visita.fecha.desc(), Cliente.nombre)
        gpd_rows = q_gpd.all()

        gpd_c = {}
        gpd_f = set()
        for r in gpd_rows:
            fs = r.fecha.strftime('%Y-%m-%d') if r.fecha else ""
            cl = r.cliente
            gpd_f.add(fs)
            if cl not in gpd_c:
                gpd_c[cl] = {}
            gpd_c[cl][fs] = {
                "total": r.total,
                "ejecutadas": r.ejecutadas,
                "completas": r.completas,
                "label": f"{r.ejecutadas}/{r.total}",
                "pct": round(r.ejecutadas / r.total * 100, 0) if r.total else 0
            }
        gestion_por_dia = {
            "fechas": sorted(list(gpd_f), reverse=True),
            "clientes": [{"cliente": k, "dias": gpd_c[k]} for k in sorted(gpd_c.keys())]
        }

        stats = {
            "total_registros":       total,
            "total_planificadas":    total_planificadas,
            "con_activacion":        total_con_activacion,
            "con_desactivacion":     total_con_desactivacion,
            "completas":             total_completas,
            "activos_ahora":         total_activos_ahora,
            "pdvs_pendientes":       len(pendientes),
            "pct_cumplimiento":      pct_cumplimiento,
            "total_rutas":           len(rutas_set),
            "rutas_ejecutadas":      len(rutas_eje_set),
            "progreso_activaciones": progreso_activaciones,
            "progreso_completas":    progreso_completas,
            "pp_activaciones": pp_act, "pp_completas": pp_com,
            "pc_activaciones": pc_act, "pc_completas": pc_com,
        }

        _result = {
            "success":             True,
            "total":               total,
            "activaciones":        activaciones,
            "stats":               stats,
            "por_mercaderista":    por_mercaderista,
            "pendientes":          pendientes,
            "gestion_por_dia":     gestion_por_dia,
        }

        # ── TTL adaptativo ──
        #   - Rangos completamente históricos (ayer o antes): 1 hora
        #   - Rangos que incluyen hoy: 45 segundos (datos en tiempo real)
        cache_ttl = 3600 if d_hasta < _date.today() else 45
        set_cache(cache_key, cache_ttl, _result)
        return _result

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
