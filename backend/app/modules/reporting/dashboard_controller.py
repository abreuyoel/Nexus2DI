from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import date as _date, datetime, timedelta
import calendar as _calendar
from app.db.session import get_db
from app.core.dependencies import get_current_user, require_analyst_or_admin
from app.modules.auth.entities import Usuario
from app.shared.azure_service import azure_service

router = APIRouter(prefix="/api/centro-mando", tags=["Centro de Mando"])


def execute_query(db: Session, query: str, params: tuple = ()):
    try:
        conn = db.connection().connection
        cursor = conn.cursor()
        cursor.execute(query, params)
        if cursor.description:
            rows = cursor.fetchall()
            return rows
        return []
    except Exception as e:
        print(f"Error in execute_query: {e}")
        raise


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


def mk_analyst(is_analyst: bool, analista_id: int, vm_a='vm', pin_a='pin', c_a='c'):
    if not (is_analyst and analista_id):
        return "", []
    f = f"""
    AND EXISTS (SELECT 1 FROM RUTA_PROGRAMACION rp_a
        JOIN analistas_rutas ar_a ON rp_a.id_ruta = ar_a.id_ruta
        WHERE rp_a.id_punto_interes = {pin_a}.identificador
          AND rp_a.activa = 1 AND ar_a.id_analista = ?)
    AND EXISTS (SELECT 1 FROM ANALISTAS_CLIENTE ac_a
        WHERE ac_a.id_cliente = {c_a}.id_cliente AND ac_a.id_analista = ?)
    """
    return f, [analista_id, analista_id]


@router.get("/clientes")
def listar_clientes(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    try:
        filtro = ""
        params: tuple = ()
        if current_user.is_analyst and current_user.id_perfil:
            filtro = """
                AND EXISTS (SELECT 1 FROM analistas_rutas ar_a
                    WHERE ar_a.id_ruta = rp.id_ruta AND ar_a.id_analista = ?)
                AND EXISTS (SELECT 1 FROM ANALISTAS_CLIENTE ac_a
                    WHERE ac_a.id_cliente = c.id_cliente AND ac_a.id_analista = ?)
            """
            params = (current_user.id_perfil, current_user.id_perfil)

        rows = execute_query(db, f"""
            SELECT DISTINCT c.id_cliente, c.cliente
            FROM CLIENTES c
            JOIN RUTA_PROGRAMACION rp ON rp.id_cliente = c.id_cliente
            WHERE rp.activa = 1 AND c.cliente IS NOT NULL
            {filtro}
            ORDER BY c.cliente
        """, params)
        return {
            "success": True,
            "clientes": [{"id_cliente": r[0], "cliente": r[1]} for r in rows]
        }
    except Exception as e:
        return {"success": False, "message": str(e), "clientes": []}


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
            cli_row = execute_query(db, "SELECT cliente, id_tipo_cliente FROM CLIENTES WHERE id_cliente = ?", (cliente_id,))
            if cli_row:
                cliente_nombre = cli_row[0][0]
                cliente_tipo = cli_row[0][1]
            else:
                cliente_nombre = f"Cliente {cliente_id}"

        serv_filter = " AND rn.servicio = 'Exclusivo'" if cliente_tipo == 3 else ""

        if cliente_id:
            merc_asig_q = f"""
                SELECT DISTINCT m.id_mercaderista, m.nombre, m.cedula,
                                ISNULL(m.tipo,'Mercaderista') AS tipo_camp
                FROM MERCADERISTAS m
                JOIN MERCADERISTAS_RUTAS mr ON mr.id_mercaderista = m.id_mercaderista
                JOIN RUTA_PROGRAMACION rp   ON rp.id_ruta = mr.id_ruta
                JOIN RUTAS_NUEVAS rn        ON rn.id_ruta = rp.id_ruta
                WHERE m.activo = 1 AND rp.activa = 1 AND rp.id_cliente = ?{serv_filter}
            """
            asignados = execute_query(db, merc_asig_q, (cliente_id,))
        else:
            merc_asig_q = """
                SELECT DISTINCT m.id_mercaderista, m.nombre, m.cedula,
                                ISNULL(m.tipo,'Mercaderista') AS tipo_camp
                FROM MERCADERISTAS m
                JOIN MERCADERISTAS_RUTAS mr ON mr.id_mercaderista = m.id_mercaderista
                JOIN RUTA_PROGRAMACION rp   ON rp.id_ruta = mr.id_ruta
                WHERE m.activo = 1 AND rp.activa = 1
            """
            asignados = execute_query(db, merc_asig_q)

        asignados_map = {r[0]: {"id_mercaderista": r[0], "nombre": r[1],
                                "cedula": r[2], "tipo_campo": r[3]}
                         for r in asignados}

        ph = ",".join("?" for _ in days_in_range)
        if cliente_id:
            plan_hoy_q = f"""
                SELECT DISTINCT m.id_mercaderista, rp.dia
                FROM MERCADERISTAS m
                JOIN MERCADERISTAS_RUTAS mr ON mr.id_mercaderista = m.id_mercaderista
                JOIN RUTA_PROGRAMACION rp   ON rp.id_ruta         = mr.id_ruta
                JOIN RUTAS_NUEVAS rn        ON rn.id_ruta = rp.id_ruta
                WHERE m.activo = 1 AND rp.activa = 1
                  AND rp.dia IN ({ph}) AND rp.id_cliente = ?{serv_filter}
            """
            plan_hoy = execute_query(db, plan_hoy_q, tuple(days_in_range + [cliente_id]))
        else:
            plan_hoy_q = f"""
                SELECT DISTINCT m.id_mercaderista, rp.dia
                FROM MERCADERISTAS m
                JOIN MERCADERISTAS_RUTAS mr ON mr.id_mercaderista = m.id_mercaderista
                JOIN RUTA_PROGRAMACION rp   ON rp.id_ruta         = mr.id_ruta
                WHERE m.activo = 1 AND rp.activa = 1
                  AND rp.dia IN ({ph})
            """
            plan_hoy = execute_query(db, plan_hoy_q, tuple(days_in_range))
            
        plan_counts = {}
        for r in plan_hoy:
            mid = r[0]
            dia = r[1]
            plan_counts[mid] = plan_counts.get(mid, 0) + day_counts.get(dia, 0)
        
        total_planificados = sum(plan_counts.values())

        if cliente_id:
            activos_hoy_q = f"""
                SELECT DISTINCT ra.id_mercaderista, CAST(ra.fecha_hora_activacion AS DATE)
                FROM RUTAS_ACTIVADAS ra
                JOIN MERCADERISTAS_RUTAS mr ON mr.id_ruta = ra.id_ruta
                JOIN RUTA_PROGRAMACION rp   ON rp.id_ruta = ra.id_ruta
                JOIN RUTAS_NUEVAS rn        ON rn.id_ruta = rp.id_ruta
                WHERE CAST(ra.fecha_hora_activacion AS DATE) BETWEEN ? AND ?
                  AND mr.id_mercaderista = ra.id_mercaderista
                  AND rp.id_cliente = ?{serv_filter}
            """
            activos_rows = execute_query(db, activos_hoy_q, (d_desde, d_hasta, cliente_id))
        else:
            activos_hoy_q = """
                SELECT DISTINCT ra.id_mercaderista, CAST(ra.fecha_hora_activacion AS DATE)
                FROM RUTAS_ACTIVADAS ra
                JOIN MERCADERISTAS_RUTAS mr ON mr.id_ruta = ra.id_ruta
                JOIN RUTA_PROGRAMACION rp   ON rp.id_ruta = ra.id_ruta
                WHERE CAST(ra.fecha_hora_activacion AS DATE) BETWEEN ? AND ?
                  AND mr.id_mercaderista = ra.id_mercaderista
            """
            activos_rows = execute_query(db, activos_hoy_q, (d_desde, d_hasta))
            
        act_counts = {}
        for r in activos_rows:
            mid = r[0]
            act_counts[mid] = act_counts.get(mid, 0) + 1
            
        total_activos = sum(act_counts.values())

        if asignados_map:
            ids = list(asignados_map.keys())
            ph2 = ",".join("?" for _ in ids)
            clas_q = f"""
                SELECT mr.id_mercaderista, COUNT(DISTINCT rp.id_cliente) AS n_cli
                FROM MERCADERISTAS_RUTAS mr
                JOIN RUTA_PROGRAMACION rp ON rp.id_ruta = mr.id_ruta
                WHERE mr.id_mercaderista IN ({ph2}) AND rp.activa = 1
                GROUP BY mr.id_mercaderista
            """
            for mid, n in execute_query(db, clas_q, tuple(ids)):
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

        if cliente_id:
            rutas_plan_q = f"""
                SELECT DISTINCT rp.id_ruta, rn.ruta, mr.id_mercaderista, m.nombre, rp.dia
                FROM RUTA_PROGRAMACION rp
                JOIN RUTAS_NUEVAS rn        ON rn.id_ruta = rp.id_ruta
                JOIN MERCADERISTAS_RUTAS mr ON mr.id_ruta = rp.id_ruta
                JOIN MERCADERISTAS m        ON m.id_mercaderista = mr.id_mercaderista
                WHERE rp.activa = 1 AND m.activo = 1
                  AND rp.dia IN ({ph}) AND rp.id_cliente = ?{serv_filter}
            """
            rutas_plan_rows = execute_query(db, rutas_plan_q, tuple(days_in_range + [cliente_id]))
        else:
            rutas_plan_q = f"""
                SELECT DISTINCT rp.id_ruta, rn.ruta, mr.id_mercaderista, m.nombre, rp.dia
                FROM RUTA_PROGRAMACION rp
                JOIN RUTAS_NUEVAS rn        ON rn.id_ruta = rp.id_ruta
                JOIN MERCADERISTAS_RUTAS mr ON mr.id_ruta = rp.id_ruta
                JOIN MERCADERISTAS m        ON m.id_mercaderista = mr.id_mercaderista
                WHERE rp.activa = 1 AND m.activo = 1
                  AND rp.dia IN ({ph})
            """
            rutas_plan_rows = execute_query(db, rutas_plan_q, tuple(days_in_range))

        ruta_merc_pairs = {}
        for r in rutas_plan_rows:
            id_ruta = r[0]
            ruta_nombre = r[1]
            id_merc = r[2]
            nombre_merc = r[3]
            dia = r[4]
            k = (id_ruta, id_merc)
            if k not in ruta_merc_pairs:
                ruta_merc_pairs[k] = {
                    "id_ruta": id_ruta, "ruta": ruta_nombre,
                    "id_mercaderista": id_merc, "nombre_mercaderista": nombre_merc,
                    "estado": "Planificada",
                    "planificadas": 0, "activas": 0, "completadas": 0,
                    "pois_plan": 0, "pois_act": 0, "pois_com": 0,
                    "clientes_plan": 0, "clientes_act": 0, "clientes_com": 0
                }
            ruta_merc_pairs[k]["planificadas"] += day_counts.get(dia, 0)

        ra_q = """
            SELECT ra.id_ruta, ra.id_mercaderista, ra.estado, CAST(ra.fecha_hora_activacion AS DATE) as fd
            FROM RUTAS_ACTIVADAS ra
            WHERE CAST(ra.fecha_hora_activacion AS DATE) BETWEEN ? AND ?
        """
        ra_rows = execute_query(db, ra_q, (d_desde, d_hasta))
        
        for rid, mid, estado, fd in ra_rows:
            k = (rid, mid)
            if k in ruta_merc_pairs:
                if estado == 'Finalizado':
                    ruta_merc_pairs[k]["completadas"] += 1
                    ruta_merc_pairs[k]["activas"] += 1
                elif estado == 'En Progreso':
                    ruta_merc_pairs[k]["activas"] += 1

        rutas_planificadas = sum(x["planificadas"] for x in ruta_merc_pairs.values())
        rutas_activas      = sum(x["activas"] for x in ruta_merc_pairs.values())
        rutas_completadas  = sum(x["completadas"] for x in ruta_merc_pairs.values())

        if cliente_id:
            pois_plan_q = f"""
                SELECT DISTINCT rp.id_punto_interes, mr.id_mercaderista,
                                pin.punto_de_interes, rp.id_ruta, rn.ruta, rp.dia,
                                pin.departamento, rp.prioridad
                FROM RUTA_PROGRAMACION rp
                JOIN MERCADERISTAS_RUTAS mr ON mr.id_ruta = rp.id_ruta
                JOIN RUTAS_NUEVAS rn        ON rn.id_ruta = rp.id_ruta
                JOIN PUNTOS_INTERES1 pin    ON pin.identificador = rp.id_punto_interes
                JOIN MERCADERISTAS m        ON m.id_mercaderista = mr.id_mercaderista
                WHERE rp.activa = 1 AND m.activo = 1
                  AND rp.dia IN ({ph}) AND rp.id_cliente = ?{serv_filter}
            """
            pois_plan_rows = execute_query(db, pois_plan_q, tuple(days_in_range + [cliente_id]))
        else:
            pois_plan_q = f"""
                SELECT DISTINCT rp.id_punto_interes, mr.id_mercaderista,
                                pin.punto_de_interes, rp.id_ruta, rn.ruta, rp.dia,
                                pin.departamento, rp.prioridad
                FROM RUTA_PROGRAMACION rp
                JOIN MERCADERISTAS_RUTAS mr ON mr.id_ruta = rp.id_ruta
                JOIN RUTAS_NUEVAS rn        ON rn.id_ruta = rp.id_ruta
                JOIN PUNTOS_INTERES1 pin    ON pin.identificador = rp.id_punto_interes
                JOIN MERCADERISTAS m        ON m.id_mercaderista = mr.id_mercaderista
                WHERE rp.activa = 1 AND m.activo = 1
                  AND rp.dia IN ({ph})
            """
            pois_plan_rows = execute_query(db, pois_plan_q, tuple(days_in_range))

        if cliente_id:
            estado_visita_q = """
                SELECT vm.identificador_punto_interes, vm.id_mercaderista, vm.id_cliente, CAST(vm.fecha_visita AS DATE),
                       MAX(CASE WHEN ft.id_tipo_foto=5 AND ft.Estado='Aprobada' THEN 1 ELSE 0 END) AS tiene_act,
                       MAX(CASE WHEN ft.id_tipo_foto=6 AND ft.Estado='Aprobada' THEN 1 ELSE 0 END) AS tiene_des
                FROM VISITAS_MERCADERISTA vm
                LEFT JOIN FOTOS_TOTALES ft ON ft.id_visita = vm.id_visita
                WHERE CAST(vm.fecha_visita AS DATE) BETWEEN ? AND ?
                  AND vm.id_cliente = ?
                GROUP BY vm.identificador_punto_interes, vm.id_mercaderista, vm.id_cliente, CAST(vm.fecha_visita AS DATE)
            """
            ev_rows = execute_query(db, estado_visita_q, (d_desde, d_hasta, cliente_id))
        else:
            estado_visita_q = """
                SELECT vm.identificador_punto_interes, vm.id_mercaderista, vm.id_cliente, CAST(vm.fecha_visita AS DATE),
                       MAX(CASE WHEN ft.id_tipo_foto=5 AND ft.Estado='Aprobada' THEN 1 ELSE 0 END) AS tiene_act,
                       MAX(CASE WHEN ft.id_tipo_foto=6 AND ft.Estado='Aprobada' THEN 1 ELSE 0 END) AS tiene_des
                FROM VISITAS_MERCADERISTA vm
                LEFT JOIN FOTOS_TOTALES ft ON ft.id_visita = vm.id_visita
                WHERE CAST(vm.fecha_visita AS DATE) BETWEEN ? AND ?
                GROUP BY vm.identificador_punto_interes, vm.id_mercaderista, vm.id_cliente, CAST(vm.fecha_visita AS DATE)
            """
            ev_rows = execute_query(db, estado_visita_q, (d_desde, d_hasta))
            
        estado_visita = {(r[0], r[1], r[2], r[3]): {"act": bool(r[4]), "des": bool(r[5])}
                         for r in ev_rows}

        ev_agg = {}
        for (id_punto, id_merc, _cli, _fd), st in estado_visita.items():
            d = ev_agg.setdefault((id_punto, id_merc), {"act": 0, "com": 0})
            if st["act"]:               d["act"] += 1
            if st["act"] and st["des"]: d["com"] += 1
            
        ev_agg_cli = {}
        for (id_punto, id_merc, id_cli, _fd), st in estado_visita.items():
            d = ev_agg_cli.setdefault((id_punto, id_merc, id_cli), {"act": 0, "com": 0})
            if st["act"]:               d["act"] += 1
            if st["act"] and st["des"]: d["com"] += 1

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
                pair["clientes_act"]  += ent["clientes_act"]
                pair["clientes_com"]  += ent["clientes_com"]

        pois_planificados = sum(v["plan"] for v in pois_status.values())
        pois_activos      = sum(v["act"] for v in pois_status.values())
        pois_completados  = sum(v["com"] for v in pois_status.values())

        tradex_ids = [mid for mid, m in asignados_map.items()
                      if m.get("tipo_servicio") == "Tradex"]
        clientes_plan = clientes_act = clientes_com = 0

        if tradex_ids:
            ph2 = ",".join("?" for _ in tradex_ids)
            tradex_pois_q = f"""
                SELECT rp.id_punto_interes, mr.id_mercaderista, rp.id_cliente, rp.dia
                FROM RUTA_PROGRAMACION rp
                JOIN MERCADERISTAS_RUTAS mr ON mr.id_ruta = rp.id_ruta
                WHERE rp.activa = 1 AND rp.dia IN ({ph})
                  AND mr.id_mercaderista IN ({ph2})
            """
            tradex_rows = execute_query(db, tradex_pois_q, tuple(days_in_range + tradex_ids))

            estado_visita_full_q = """
                SELECT vm.identificador_punto_interes, vm.id_mercaderista, vm.id_cliente, CAST(vm.fecha_visita AS DATE),
                       MAX(CASE WHEN ft.id_tipo_foto=5 AND ft.Estado='Aprobada' THEN 1 ELSE 0 END),
                       MAX(CASE WHEN ft.id_tipo_foto=6 AND ft.Estado='Aprobada' THEN 1 ELSE 0 END)
                FROM VISITAS_MERCADERISTA vm
                LEFT JOIN FOTOS_TOTALES ft ON ft.id_visita = vm.id_visita
                WHERE CAST(vm.fecha_visita AS DATE) BETWEEN ? AND ?
                GROUP BY vm.identificador_punto_interes, vm.id_mercaderista, vm.id_cliente, CAST(vm.fecha_visita AS DATE)
            """
            ev_full = execute_query(db, estado_visita_full_q, (d_desde, d_hasta))
            ev_full_map = {(r[0], r[1], r[2], r[3]): {"act": bool(r[4]), "des": bool(r[5])}
                           for r in ev_full}
                           
            ev_full_agg = {}
            for (id_p, id_m, id_c, fd), st in ev_full_map.items():
                d = ev_full_agg.setdefault((id_p, id_m, id_c), {"act": 0, "com": 0})
                if st["act"]: d["act"] += 1
                if st["act"] and st["des"]: d["com"] += 1

            t_plan = {}
            for id_punto, id_merc, id_cli, dia in tradex_rows:
                key = (id_punto, id_merc, id_cli)
                t_plan[key] = t_plan.get(key, 0) + day_counts.get(dia, 0)
                
            clientes_plan = sum(t_plan.values())
            for key, plan_cnt in t_plan.items():
                ev = ev_full_agg.get(key)
                if ev:
                    clientes_act += ev["act"]
                    clientes_com += ev["com"]

        merc_pois = {}
        for (id_punto, id_merc), ent in pois_status.items():
            d = merc_pois.setdefault(id_merc, {"pois_plan":0, "pois_act":0, "pois_com":0})
            d["pois_plan"] += ent["plan"]
            d["pois_act"] += ent["act"]
            d["pois_com"] += ent["com"]

        merc_rutas = {}
        for (id_ruta, id_merc), ent in ruta_merc_pairs.items():
            d = merc_rutas.setdefault(id_merc, {"rutas_plan":0, "rutas_act":0, "rutas_com":0,
                                                "rutas_nombres": []})
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
            
            mp = merc_pois.get(mid, {"pois_plan":0,"pois_act":0,"pois_com":0})
            mr = merc_rutas.get(mid, {"rutas_plan":0,"rutas_act":0,"rutas_com":0,"rutas_nombres":[]})

            estado = ("No planificado" if p_cnt == 0 else
                      ("Faltante" if faltas > 0 else "Activo"))

            det = {
                **m,
                "planificado_hoy":  p_cnt > 0,
                "planificados":     p_cnt,
                "activos":          a_cnt,
                "faltas":           faltas,
                "estado":           estado,
                "rutas_planificadas": mr["rutas_plan"],
                "rutas_activas":      mr["rutas_act"],
                "rutas_completadas":  mr["rutas_com"],
                "rutas_nombres":      mr["rutas_nombres"],
                "pois_planificados":  mp["pois_plan"],
                "pois_activos":       mp["pois_act"],
                "pois_completados":   mp["pois_com"],
            }
            mercaderistas_detalle.append(det)
            if faltas > 0:
                faltantes.append(det)
            if a_cnt > 0:
                activos.append(det)

        prio = {"Faltante":0,"Activo":1,"No planificado":2}
        mercaderistas_detalle.sort(key=lambda x: (prio.get(x["estado"],99), x["nombre"] or ""))
        
        total_faltantes = sum(max(0, plan_counts.get(m, 0) - act_counts.get(m, 0)) for m in plan_counts.keys())

        return {
            "success":         True,
            "cliente_id":      cliente_id,
            "cliente_nombre":  cliente_nombre,
            "desde":           d_desde.isoformat(),
            "hasta":           d_hasta.isoformat(),
            "mercaderistas": {
                "total_asignados":         len(asignados_map),
                "planificados_hoy":        total_planificados,
                "activos_hoy":             total_activos,
                "faltantes_hoy":           total_faltantes,
                "exclusivos":              sum(1 for m in asignados_map.values()
                                               if m["tipo_servicio"] == "Exclusivo"),
                "tradex":                  sum(1 for m in asignados_map.values()
                                               if m["tipo_servicio"] == "Tradex"),
                "detalle":                 mercaderistas_detalle,
                "faltantes":               faltantes,
                "activos":                 activos,
            },
            "rutas": {
                "planificadas":  rutas_planificadas,
                "activas":       rutas_activas,
                "completadas":   rutas_completadas,
                "detalle":       list(ruta_merc_pairs.values()),
            },
            "puntos_interes": {
                "planificados":  pois_planificados,
                "activos":       pois_activos,
                "completados":   pois_completados,
                "detalle":       list(pois_status.values()),
            },
            "clientes_tradex": {
                "planificados":  clientes_plan,
                "activos":       clientes_act,
                "completados":   clientes_com,
                "aplica":        bool(tradex_ids),
            },
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


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
            rango_filter = " AND CAST(vm.fecha_visita AS DATE) BETWEEN ? AND ?"
            rango_params = [desde, hasta]
        else:
            rango_filter = " AND CAST(vm.fecha_visita AS DATE) = CAST(GETDATE() AS DATE)"
            rango_params = []

        analista_id = current_user.id_perfil if is_analyst else None

        af, ap = mk_analyst(is_analyst, analista_id)
        if cliente_id:
            af += " AND c.id_cliente = ?"
            ap = ap + [cliente_id]

        base_query = """
            SELECT
                vm.id_visita,
                c.cliente,
                c.id_cliente,
                pin.punto_de_interes,
                pin.identificador           AS id_punto,
                ISNULL(pin.departamento,'') AS departamento,
                ISNULL(pin.ciudad,'')       AS ciudad,
                m.nombre                    AS mercaderista,
                m.id_mercaderista,
                vm.fecha_visita,
                ISNULL(pin.jerarquia_nivel_2,'') AS tipo_pdv,

                act.id_foto                 AS id_foto_activacion,
                act.file_path               AS file_path_activacion,
                act.fecha_registro          AS fecha_activacion,
                act.Estado                  AS estado_activacion,

                des.id_foto                 AS id_foto_desactivacion,
                des.file_path               AS file_path_desactivacion,
                des.fecha_registro          AS fecha_desactivacion,
                des.Estado                  AS estado_desactivacion,

                ISNULL(ruta_pre.ruta,   'Sin ruta') AS ruta,
                ISNULL(ruta_pre.id_ruta, 0)         AS id_ruta,
                ISNULL(ruta_pre.analista,'')         AS nombre_analista,
                ISNULL(ruta_pre.cuadrante,'')        AS cuadrante,

                ISNULL(chat_pre.no_leidos, 0)        AS mensajes_no_leidos

            FROM VISITAS_MERCADERISTA vm
            JOIN CLIENTES       c   ON vm.id_cliente                  = c.id_cliente
            JOIN PUNTOS_INTERES1 pin ON vm.identificador_punto_interes = pin.identificador
            JOIN MERCADERISTAS  m   ON vm.id_mercaderista             = m.id_mercaderista

            LEFT JOIN (
                SELECT ft.id_visita, ft.id_foto, ft.file_path,
                       ft.fecha_registro, ft.Estado,
                       ROW_NUMBER() OVER (PARTITION BY ft.id_visita
                                          ORDER BY ft.fecha_registro DESC) AS rn
                FROM FOTOS_TOTALES ft
                WHERE ft.id_tipo_foto = 5
            ) act ON act.id_visita = vm.id_visita AND act.rn = 1

            LEFT JOIN (
                SELECT ft.id_visita, ft.id_foto, ft.file_path,
                       ft.fecha_registro, ft.Estado,
                       ROW_NUMBER() OVER (PARTITION BY ft.id_visita
                                          ORDER BY ft.fecha_registro DESC) AS rn
                FROM FOTOS_TOTALES ft
                WHERE ft.id_tipo_foto = 6
            ) des ON des.id_visita = vm.id_visita AND des.rn = 1

            LEFT JOIN (
                SELECT rp2.id_punto_interes,
                       rn2.ruta,
                       rn2.id_ruta,
                       a2.nombre_analista AS analista,
                       rn2.cuadrante,
                       ROW_NUMBER() OVER (PARTITION BY rp2.id_punto_interes
                                          ORDER BY rn2.id_ruta) AS rn
                FROM RUTA_PROGRAMACION rp2
                JOIN RUTAS_NUEVAS rn2 ON rp2.id_ruta  = rn2.id_ruta
                LEFT JOIN analistas_rutas ar2 ON ar2.id_ruta = rn2.id_ruta
                LEFT JOIN analistas a2 ON a2.id_analista = ar2.id_analista
                WHERE rp2.activa = 1
            ) ruta_pre ON ruta_pre.id_punto_interes = pin.identificador
                      AND ruta_pre.rn = 1

            LEFT JOIN (
                SELECT id_visita,
                       SUM(CASE WHEN visto = 0 AND tipo_mensaje = 'usuario' THEN 1 ELSE 0 END)
                           AS no_leidos
                FROM CHAT_MENSAJES
                GROUP BY id_visita
            ) chat_pre ON chat_pre.id_visita = vm.id_visita

            WHERE (act.id_foto IS NOT NULL OR des.id_foto IS NOT NULL)
        """ + rango_filter + af + " ORDER BY vm.fecha_visita DESC"

        all_params = rango_params + ap
        rows = execute_query(db, base_query, all_params)

        def _foto_url(path):
            try:
                return azure_service.get_sas_url(path) if path else None
            except Exception:
                return None

        activaciones = []
        seen_ids = set()
        total_con_activacion = total_con_desactivacion = 0
        total_completas = total_activos_ahora = 0
        rutas_set = set()
        rutas_eje_set = set()

        for row in rows:
            vid = row[0]
            if vid in seen_ids: continue
            seen_ids.add(vid)

            activaciones.append({
                "id_visita":               row[0],
                "cliente":                 row[1],
                "id_cliente":              row[2],
                "punto_de_interes":        row[3],
                "id_punto":                row[4],
                "departamento":            row[5],
                "ciudad":                  row[6],
                "mercaderista":            row[7],
                "id_mercaderista":         row[8],
                "fecha_visita":            row[9].isoformat()  if row[9]  else None,
                "tipo_pdv":                row[10],
                "id_foto_activacion":      row[11],
                "file_path_activacion":    row[12],
                "url_activacion":          _foto_url(row[12]),
                "fecha_activacion":        row[13].isoformat() if row[13] else None,
                "estado_activacion":       row[14],
                "id_foto_desactivacion":   row[15],
                "file_path_desactivacion": row[16],
                "url_desactivacion":       _foto_url(row[16]),
                "fecha_desactivacion":     row[17].isoformat() if row[17] else None,
                "estado_desactivacion":    row[18],
                "ruta":                    row[19],
                "id_ruta":                 row[20],
                "analista":                row[21],
                "mensajes_no_leidos":      row[22],
                "duracion_minutos":        None,
                "estado_presencia":        None,
                "foto_heredada":           False,
            })

        from collections import defaultdict as _dd
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

        from datetime import datetime as _dt
        for v in activaciones:
            ta = v["id_foto_activacion"] is not None
            td = v["id_foto_desactivacion"] is not None
            v["estado_presencia"] = "completa" if ta and td else ("activo" if ta else "solo_salida")
            if ta and td and v["fecha_activacion"] and v["fecha_desactivacion"]:
                try:
                    v["duracion_minutos"] = int(
                        (_dt.fromisoformat(v["fecha_desactivacion"]) - _dt.fromisoformat(v["fecha_activacion"])).total_seconds() / 60
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

        plan_query = """
            SELECT COUNT(DISTINCT vm2.id_visita)
            FROM VISITAS_MERCADERISTA vm2
            JOIN CLIENTES        c2  ON vm2.id_cliente                  = c2.id_cliente
            JOIN PUNTOS_INTERES1 pin2 ON vm2.identificador_punto_interes = pin2.identificador
            WHERE 1=1
        """ + rango_filter.replace("vm.", "vm2.")
        af2, ap2 = mk_analyst(is_analyst, analista_id, 'vm2', 'pin2', 'c2')
        if cliente_id:
            af2 += " AND c2.id_cliente = ?"
            ap2 = ap2 + [cliente_id]
        plan_query += af2
        plan_params = rango_params + ap2
        
        plan_result = execute_query(db, plan_query, plan_params)
        
        total_planificadas = total
        if plan_result and len(plan_result) > 0:
             total_planificadas = int(plan_result[0][0]) if plan_result[0][0] is not None else total

        def _planned_map(group_col: str, extra_join: str = "") -> dict:
            q = (
                "SELECT " + group_col + " AS gid, COUNT(DISTINCT vm2.id_visita) AS cnt "
                "FROM VISITAS_MERCADERISTA vm2 "
                "JOIN CLIENTES c2 ON vm2.id_cliente = c2.id_cliente "
                "JOIN PUNTOS_INTERES1 pin2 ON vm2.identificador_punto_interes = pin2.identificador "
                + extra_join +
                " WHERE 1=1" + rango_filter.replace("vm.", "vm2.") + af2 +
                " GROUP BY " + group_col
            )
            res = execute_query(db, q, plan_params)
            return {r[0]: int(r[1]) for r in (res or []) if r[0] is not None}

        planned_pp = _planned_map("pin2.identificador")
        planned_pc = _planned_map("c2.id_cliente")
        planned_merc = _planned_map(
            "vm2.id_mercaderista",
            "JOIN MERCADERISTAS m2 ON vm2.id_mercaderista = m2.id_mercaderista",
        )

        base_prog             = total_planificadas if total_planificadas > 0 else (total if total > 0 else 1)
        pct_cumplimiento      = round(total_con_activacion / base_prog * 100, 1)
        progreso_activaciones = round(total_con_activacion / base_prog * 100, 1)
        progreso_completas    = round(total_completas      / base_prog * 100, 1)

        from datetime import timedelta as _tdp, date as _dproute
        if desde and hasta:
            _d0 = _dproute.fromisoformat(desde); _d1 = _dproute.fromisoformat(hasta)
        else:
            _d0 = _d1 = _dproute.today()
        _dias_set = set(); _cur = _d0
        while _cur <= _d1:
            _dias_set.add(_dia_es(_cur)); _cur += _tdp(days=1)
        dias_rango = list(_dias_set)

        pendientes = []
        planned_merc_exec: dict = {}
        planned_merc_info: dict = {}
        planned_merc_pdvs: dict = {}
        planned_merc_clis: dict = {}
        if dias_rango:
            af_p, ap_p = mk_analyst(is_analyst, analista_id, 'vmx', 'pin', 'c')
            ph_dias = ",".join("?" for _ in dias_rango)
            cli_filter = " AND rp.id_cliente = ?" if cliente_id else ""
            pend_query = f"""
                SELECT DISTINCT
                    m.id_mercaderista, m.nombre AS mercaderista,
                    pin.identificador AS id_punto, pin.punto_de_interes,
                    rp.id_cliente, ISNULL(c.cliente,'') AS cliente,
                    ISNULL(pin.ciudad,'') AS ciudad, ISNULL(rn.ruta,'Sin ruta') AS ruta,
                    ISNULL(pin.departamento,'') AS departamento, ISNULL(rp.prioridad,'') AS prioridad,
                    ISNULL(rn.cuadrante,'') AS cuadrante
                FROM MERCADERISTAS m
                JOIN MERCADERISTAS_RUTAS mr ON mr.id_mercaderista = m.id_mercaderista
                JOIN RUTA_PROGRAMACION rp   ON rp.id_ruta = mr.id_ruta
                JOIN RUTAS_NUEVAS rn        ON rn.id_ruta = rp.id_ruta
                JOIN PUNTOS_INTERES1 pin    ON pin.identificador = rp.id_punto_interes
                LEFT JOIN CLIENTES c        ON c.id_cliente = rp.id_cliente
                WHERE m.activo = 1 AND rp.activa = 1 AND rp.dia IN ({ph_dias}){cli_filter}{af_p}
                ORDER BY m.nombre, ISNULL(c.cliente,'')
            """
            pend_params = list(dias_rango) + ([cliente_id] if cliente_id else []) + ap_p
            pend_rows = execute_query(db, pend_query, pend_params)

            activated_pdv = {(v["id_mercaderista"], v["id_punto"]) for v in activaciones if v["id_foto_activacion"]}
            seen_pend = set()
            for r in (pend_rows or []):
                mid, mnom, idp, pnom, idc, cli, ciu, ruta, depto, prio, cuad = r
                planned_merc_info[mid] = mnom
                planned_merc_exec.setdefault(mid, set()).add((idp, idc))
                planned_merc_pdvs.setdefault(mid, set()).add(idp)
                planned_merc_clis.setdefault(mid, set()).add(idc)
                if (mid, idp) in activated_pdv:
                    continue
                key = (idp, idc, mid)
                if key in seen_pend: continue
                seen_pend.add(key)
                pendientes.append({
                    "id_punto": idp, "punto_de_interes": pnom,
                    "cliente": cli, "id_cliente": idc,
                    "mercaderista": mnom, "id_mercaderista": mid,
                    "ciudad": ciu, "ruta": ruta,
                    "departamento": depto, "prioridad": prio, "cuadrante": cuad
                })

        act_exec: dict = {}
        com_exec: dict = {}
        durs_merc: dict = {}
        activo_now: dict = {}
        act_pdvs: dict = {}
        act_clis: dict = {}
        nombre_merc = {}
        merc_rutas_set: dict = {}
        merc_deptos_set: dict = {}
        merc_cuads_set: dict = {}
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

        pend_merc_count: dict = {}
        for p in pendientes:
            mid = p["id_mercaderista"]
            pend_merc_count[mid] = pend_merc_count.get(mid, 0) + 1
            if p.get("ruta") and p["ruta"] != "Sin ruta": merc_rutas_set.setdefault(mid, set()).add(p["ruta"])
            if p.get("departamento"): merc_deptos_set.setdefault(mid, set()).add(p["departamento"])
            if p.get("cuadrante"): merc_cuads_set.setdefault(mid, set()).add(p["cuadrante"])

        all_mids = set(planned_merc_info.keys()) | set(nombre_merc.keys())
        por_mercaderista = []
        for mid in all_mids:
            activadas = len(act_exec.get(mid, set()))
            completas = len(com_exec.get(mid, set()))
            pend = pend_merc_count.get(mid, 0)
            planificadas = len(planned_merc_exec.get(mid, set()))
            if planificadas == 0:
                planificadas = activadas + pend
            planificadas = max(planificadas, activadas, completas)
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
                "total": activadas,
                "planificadas": planificadas,
                "activaciones": activadas,
                "completas": completas,
                "pendientes": pend,
                "pct_activacion": round(activadas / planificadas * 100, 1) if planificadas else 0,
                "pct_completas":  round(completas / planificadas * 100, 1) if planificadas else 0,
                "activo_ahora": activo_now.get(mid, False),
                "total_puntos": total_puntos,
                "total_clientes": total_clientes,
                "duracion_prom": round(sum(durs_merc[mid]) / len(durs_merc[mid])) if durs_merc.get(mid) else None,
                "departamentos_str": deptos_str,
                "rutas_str": rutas_str,
                "cuadrantes_str": cuads_str,
            })
        por_mercaderista.sort(key=lambda x: x["pct_activacion"], reverse=True)

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
                    total = max(planned_map.get(kid, 0), v["con"])
                    out.append({
                        "nombre": v["nombre"], "id": kid, "total": total, "con": v["con"],
                        "porcentaje": round(v["con"] / total * 100, 1) if total else 0,
                    })
                return sorted(out, key=lambda x: x["porcentaje"], reverse=True)
            return _s(act_m), _s(com_m)

        pp_act, pp_com = _desglose(lambda v: v["punto_de_interes"], lambda v: v["id_punto"], planned_pp)
        pc_act, pc_com = _desglose(lambda v: v["cliente"], lambda v: v["id_cliente"], planned_pc)

        gpd_af, gpd_ap = mk_analyst(is_analyst, analista_id, 'vm4','pin4','c4')
        if cliente_id:
            gpd_af += " AND c4.id_cliente = ?"
            gpd_ap = gpd_ap + [cliente_id]
        gestion_query = """
            SELECT CAST(vm4.fecha_visita AS DATE) AS fecha,
                   c4.cliente,
                   COUNT(DISTINCT vm4.id_visita)  AS total,
                   SUM(CASE WHEN act4.id_foto IS NOT NULL THEN 1 ELSE 0 END) AS ejecutadas,
                   SUM(CASE WHEN act4.id_foto IS NOT NULL AND des4.id_foto IS NOT NULL THEN 1 ELSE 0 END) AS completas
            FROM VISITAS_MERCADERISTA vm4
            JOIN CLIENTES c4 ON vm4.id_cliente = c4.id_cliente
            JOIN PUNTOS_INTERES1 pin4 ON vm4.identificador_punto_interes = pin4.identificador
            LEFT JOIN (SELECT id_visita, MIN(id_foto) AS id_foto FROM FOTOS_TOTALES WHERE id_tipo_foto=5 GROUP BY id_visita) act4 ON act4.id_visita=vm4.id_visita
            LEFT JOIN (SELECT id_visita, MIN(id_foto) AS id_foto FROM FOTOS_TOTALES WHERE id_tipo_foto=6 GROUP BY id_visita) des4 ON des4.id_visita=vm4.id_visita
            WHERE CAST(vm4.fecha_visita AS DATE) >= CAST(DATEADD(day,-6,GETDATE()) AS DATE)
              AND EXISTS (SELECT 1 FROM FOTOS_TOTALES ft4 WHERE ft4.id_visita=vm4.id_visita AND ft4.id_tipo_foto IN (5,6))
        """ + gpd_af + """
            GROUP BY CAST(vm4.fecha_visita AS DATE), c4.cliente
            ORDER BY fecha DESC, c4.cliente
        """
        gpd_rows = execute_query(db, gpd_query, gpd_ap)
        gpd_c = {}; gpd_f = set()
        for r in gpd_rows:
            fs = r[0].strftime('%Y-%m-%d'); cl = r[1]; gpd_f.add(fs)
            if cl not in gpd_c: gpd_c[cl] = {}
            gpd_c[cl][fs] = {"total":r[2],"ejecutadas":r[3],"completas":r[4],
                             "label":f"{r[3]}/{r[2]}","pct":round(r[3]/r[2]*100,0) if r[2] else 0}
        gestion_por_dia = {"fechas":sorted(list(gpd_f),reverse=True),
                           "clientes":[{"cliente":k,"dias":gpd_c[k]} for k in sorted(gpd_c.keys())]}

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

        return {
            "success":             True,
            "total":               total,
            "activaciones":        activaciones,
            "stats":               stats,
            "por_mercaderista":    por_mercaderista,
            "pendientes":          pendientes,
            "gestion_por_dia":     gestion_por_dia,
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
