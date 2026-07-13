import re
import os

filepath = r"C:\Users\Yoel Abreu\Documents\epran\Astroweb\AppWeb_v2\backend\app\routes\centro_mando.py"

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Define the new resumen_dia function
new_resumen_dia = """@router.get("/resumen-dia")
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

        # Calcular day_counts
        day_counts = { 'Lunes':0, 'Martes':0, 'Miércoles':0, 'Jueves':0, 'Viernes':0, 'Sábado':0, 'Domingo':0 }
        curr = d_desde
        while curr <= d_hasta:
            day_counts[_dia_es(curr)] += 1
            curr += timedelta(days=1)
            
        days_in_range = [d for d, c in day_counts.items() if c > 0]
        if not days_in_range:
            days_in_range = ['Lunes'] # fallback

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

        # 1) MERCADERISTAS ASIGNADOS
        if cliente_id:
            merc_asig_q = f\"\"\"
                SELECT DISTINCT m.id_mercaderista, m.nombre, m.cedula,
                                ISNULL(m.tipo,'Mercaderista') AS tipo_camp
                FROM MERCADERISTAS m
                JOIN MERCADERISTAS_RUTAS mr ON mr.id_mercaderista = m.id_mercaderista
                JOIN RUTA_PROGRAMACION rp   ON rp.id_ruta = mr.id_ruta
                JOIN RUTAS_NUEVAS rn        ON rn.id_ruta = rp.id_ruta
                WHERE m.activo = 1 AND rp.activa = 1 AND rp.id_cliente = ?{serv_filter}
            \"\"\"
            asignados = execute_query(db, merc_asig_q, (cliente_id,))
        else:
            merc_asig_q = \"\"\"
                SELECT DISTINCT m.id_mercaderista, m.nombre, m.cedula,
                                ISNULL(m.tipo,'Mercaderista') AS tipo_camp
                FROM MERCADERISTAS m
                JOIN MERCADERISTAS_RUTAS mr ON mr.id_mercaderista = m.id_mercaderista
                JOIN RUTA_PROGRAMACION rp   ON rp.id_ruta = mr.id_ruta
                WHERE m.activo = 1 AND rp.activa = 1
            \"\"\"
            asignados = execute_query(db, merc_asig_q)

        asignados_map = {r[0]: {"id_mercaderista": r[0], "nombre": r[1],
                                "cedula": r[2], "tipo_campo": r[3]}
                         for r in asignados}

        # 2) MERCADERISTAS PLANIFICADOS
        ph = ",".join("?" for _ in days_in_range)
        if cliente_id:
            plan_hoy_q = f\"\"\"
                SELECT DISTINCT m.id_mercaderista, rp.dia
                FROM MERCADERISTAS m
                JOIN MERCADERISTAS_RUTAS mr ON mr.id_mercaderista = m.id_mercaderista
                JOIN RUTA_PROGRAMACION rp   ON rp.id_ruta         = mr.id_ruta
                JOIN RUTAS_NUEVAS rn        ON rn.id_ruta = rp.id_ruta
                WHERE m.activo = 1 AND rp.activa = 1
                  AND rp.dia IN ({ph}) AND rp.id_cliente = ?{serv_filter}
            \"\"\"
            plan_hoy = execute_query(db, plan_hoy_q, tuple(days_in_range + [cliente_id]))
        else:
            plan_hoy_q = f\"\"\"
                SELECT DISTINCT m.id_mercaderista, rp.dia
                FROM MERCADERISTAS m
                JOIN MERCADERISTAS_RUTAS mr ON mr.id_mercaderista = m.id_mercaderista
                JOIN RUTA_PROGRAMACION rp   ON rp.id_ruta         = mr.id_ruta
                WHERE m.activo = 1 AND rp.activa = 1
                  AND rp.dia IN ({ph})
            \"\"\"
            plan_hoy = execute_query(db, plan_hoy_q, tuple(days_in_range))
            
        plan_counts = {}
        for r in plan_hoy:
            mid = r[0]
            dia = r[1]
            plan_counts[mid] = plan_counts.get(mid, 0) + day_counts.get(dia, 0)
        
        total_planificados = sum(plan_counts.values())

        # 3) MERCADERISTAS QUE ACTIVARON
        if cliente_id:
            activos_hoy_q = f\"\"\"
                SELECT DISTINCT ra.id_mercaderista, CAST(ra.fecha_hora_activacion AS DATE)
                FROM RUTAS_ACTIVADAS ra
                JOIN MERCADERISTAS_RUTAS mr ON mr.id_ruta = ra.id_ruta
                JOIN RUTA_PROGRAMACION rp   ON rp.id_ruta = ra.id_ruta
                JOIN RUTAS_NUEVAS rn        ON rn.id_ruta = rp.id_ruta
                WHERE CAST(ra.fecha_hora_activacion AS DATE) BETWEEN ? AND ?
                  AND mr.id_mercaderista = ra.id_mercaderista
                  AND rp.id_cliente = ?{serv_filter}
            \"\"\"
            activos_rows = execute_query(db, activos_hoy_q, (d_desde, d_hasta, cliente_id))
        else:
            activos_hoy_q = \"\"\"
                SELECT DISTINCT ra.id_mercaderista, CAST(ra.fecha_hora_activacion AS DATE)
                FROM RUTAS_ACTIVADAS ra
                JOIN MERCADERISTAS_RUTAS mr ON mr.id_ruta = ra.id_ruta
                JOIN RUTA_PROGRAMACION rp   ON rp.id_ruta = ra.id_ruta
                WHERE CAST(ra.fecha_hora_activacion AS DATE) BETWEEN ? AND ?
                  AND mr.id_mercaderista = ra.id_mercaderista
            \"\"\"
            activos_rows = execute_query(db, activos_hoy_q, (d_desde, d_hasta))
            
        act_counts = {}
        for r in activos_rows:
            mid = r[0]
            act_counts[mid] = act_counts.get(mid, 0) + 1
            
        total_activos = sum(act_counts.values())

        # 4) CLASIFICACIÓN
        if asignados_map:
            ids = list(asignados_map.keys())
            ph2 = ",".join("?" for _ in ids)
            clas_q = f\"\"\"
                SELECT mr.id_mercaderista, COUNT(DISTINCT rp.id_cliente) AS n_cli
                FROM MERCADERISTAS_RUTAS mr
                JOIN RUTA_PROGRAMACION rp ON rp.id_ruta = mr.id_ruta
                WHERE mr.id_mercaderista IN ({ph2}) AND rp.activa = 1
                GROUP BY mr.id_mercaderista
            \"\"\"
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

        # 5) RUTAS
        if cliente_id:
            rutas_plan_q = f\"\"\"
                SELECT DISTINCT rp.id_ruta, rn.ruta, mr.id_mercaderista, m.nombre, rp.dia
                FROM RUTA_PROGRAMACION rp
                JOIN RUTAS_NUEVAS rn        ON rn.id_ruta = rp.id_ruta
                JOIN MERCADERISTAS_RUTAS mr ON mr.id_ruta = rp.id_ruta
                JOIN MERCADERISTAS m        ON m.id_mercaderista = mr.id_mercaderista
                WHERE rp.activa = 1 AND m.activo = 1
                  AND rp.dia IN ({ph}) AND rp.id_cliente = ?{serv_filter}
            \"\"\"
            rutas_plan_rows = execute_query(db, rutas_plan_q, tuple(days_in_range + [cliente_id]))
        else:
            rutas_plan_q = f\"\"\"
                SELECT DISTINCT rp.id_ruta, rn.ruta, mr.id_mercaderista, m.nombre, rp.dia
                FROM RUTA_PROGRAMACION rp
                JOIN RUTAS_NUEVAS rn        ON rn.id_ruta = rp.id_ruta
                JOIN MERCADERISTAS_RUTAS mr ON mr.id_ruta = rp.id_ruta
                JOIN MERCADERISTAS m        ON m.id_mercaderista = mr.id_mercaderista
                WHERE rp.activa = 1 AND m.activo = 1
                  AND rp.dia IN ({ph})
            \"\"\"
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

        ra_q = \"\"\"
            SELECT ra.id_ruta, ra.id_mercaderista, ra.estado, CAST(ra.fecha_hora_activacion AS DATE) as fd
            FROM RUTAS_ACTIVADAS ra
            WHERE CAST(ra.fecha_hora_activacion AS DATE) BETWEEN ? AND ?
        \"\"\"
        ra_rows = execute_query(db, ra_q, (d_desde, d_hasta))
        
        # Agrupar estado por ruta_merc
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

        # 6) POIs
        if cliente_id:
            pois_plan_q = f\"\"\"
                SELECT DISTINCT rp.id_punto_interes, mr.id_mercaderista,
                                pin.punto_de_interes, rp.id_ruta, rn.ruta, rp.dia
                FROM RUTA_PROGRAMACION rp
                JOIN MERCADERISTAS_RUTAS mr ON mr.id_ruta = rp.id_ruta
                JOIN RUTAS_NUEVAS rn        ON rn.id_ruta = rp.id_ruta
                JOIN PUNTOS_INTERES1 pin    ON pin.identificador = rp.id_punto_interes
                JOIN MERCADERISTAS m        ON m.id_mercaderista = mr.id_mercaderista
                WHERE rp.activa = 1 AND m.activo = 1
                  AND rp.dia IN ({ph}) AND rp.id_cliente = ?{serv_filter}
            \"\"\"
            pois_plan_rows = execute_query(db, pois_plan_q, tuple(days_in_range + [cliente_id]))
        else:
            pois_plan_q = f\"\"\"
                SELECT DISTINCT rp.id_punto_interes, mr.id_mercaderista,
                                pin.punto_de_interes, rp.id_ruta, rn.ruta, rp.dia
                FROM RUTA_PROGRAMACION rp
                JOIN MERCADERISTAS_RUTAS mr ON mr.id_ruta = rp.id_ruta
                JOIN RUTAS_NUEVAS rn        ON rn.id_ruta = rp.id_ruta
                JOIN PUNTOS_INTERES1 pin    ON pin.identificador = rp.id_punto_interes
                JOIN MERCADERISTAS m        ON m.id_mercaderista = mr.id_mercaderista
                WHERE rp.activa = 1 AND m.activo = 1
                  AND rp.dia IN ({ph})
            \"\"\"
            pois_plan_rows = execute_query(db, pois_plan_q, tuple(days_in_range))

        if cliente_id:
            estado_visita_q = \"\"\"
                SELECT vm.identificador_punto_interes, vm.id_mercaderista, vm.id_cliente, CAST(vm.fecha_visita AS DATE),
                       MAX(CASE WHEN ft.id_tipo_foto=5 AND ft.Estado='Aprobada' THEN 1 ELSE 0 END) AS tiene_act,
                       MAX(CASE WHEN ft.id_tipo_foto=6 AND ft.Estado='Aprobada' THEN 1 ELSE 0 END) AS tiene_des
                FROM VISITAS_MERCADERISTA vm
                LEFT JOIN FOTOS_TOTALES ft ON ft.id_visita = vm.id_visita
                WHERE CAST(vm.fecha_visita AS DATE) BETWEEN ? AND ?
                  AND vm.id_cliente = ?
                GROUP BY vm.identificador_punto_interes, vm.id_mercaderista, vm.id_cliente, CAST(vm.fecha_visita AS DATE)
            \"\"\"
            ev_rows = execute_query(db, estado_visita_q, (d_desde, d_hasta, cliente_id))
        else:
            estado_visita_q = \"\"\"
                SELECT vm.identificador_punto_interes, vm.id_mercaderista, vm.id_cliente, CAST(vm.fecha_visita AS DATE),
                       MAX(CASE WHEN ft.id_tipo_foto=5 AND ft.Estado='Aprobada' THEN 1 ELSE 0 END) AS tiene_act,
                       MAX(CASE WHEN ft.id_tipo_foto=6 AND ft.Estado='Aprobada' THEN 1 ELSE 0 END) AS tiene_des
                FROM VISITAS_MERCADERISTA vm
                LEFT JOIN FOTOS_TOTALES ft ON ft.id_visita = vm.id_visita
                WHERE CAST(vm.fecha_visita AS DATE) BETWEEN ? AND ?
                GROUP BY vm.identificador_punto_interes, vm.id_mercaderista, vm.id_cliente, CAST(vm.fecha_visita AS DATE)
            \"\"\"
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
        for id_punto, id_merc, nombre_punto, id_ruta, ruta_nombre, dia in pois_plan_rows:
            key = (id_punto, id_merc)
            if key not in pois_status:
                pois_status[key] = {
                    "id_punto": id_punto, "punto_de_interes": nombre_punto,
                    "id_mercaderista": id_merc, "id_ruta": id_ruta, "ruta": ruta_nombre,
                    "mercaderista": asignados_map.get(id_merc, {}).get("nombre", "Desconocido"),
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

        # 7) CLIENTES
        tradex_ids = [mid for mid, m in asignados_map.items()
                      if m.get("tipo_servicio") == "Tradex"]
        clientes_plan = clientes_act = clientes_com = 0

        if tradex_ids:
            ph2 = ",".join("?" for _ in tradex_ids)
            tradex_pois_q = f\"\"\"
                SELECT rp.id_punto_interes, mr.id_mercaderista, rp.id_cliente, rp.dia
                FROM RUTA_PROGRAMACION rp
                JOIN MERCADERISTAS_RUTAS mr ON mr.id_ruta = rp.id_ruta
                WHERE rp.activa = 1 AND rp.dia IN ({ph})
                  AND mr.id_mercaderista IN ({ph2})
            \"\"\"
            tradex_rows = execute_query(db, tradex_pois_q, tuple(days_in_range + tradex_ids))

            estado_visita_full_q = \"\"\"
                SELECT vm.identificador_punto_interes, vm.id_mercaderista, vm.id_cliente, CAST(vm.fecha_visita AS DATE),
                       MAX(CASE WHEN ft.id_tipo_foto=5 AND ft.Estado='Aprobada' THEN 1 ELSE 0 END),
                       MAX(CASE WHEN ft.id_tipo_foto=6 AND ft.Estado='Aprobada' THEN 1 ELSE 0 END)
                FROM VISITAS_MERCADERISTA vm
                LEFT JOIN FOTOS_TOTALES ft ON ft.id_visita = vm.id_visita
                WHERE CAST(vm.fecha_visita AS DATE) BETWEEN ? AND ?
                GROUP BY vm.identificador_punto_interes, vm.id_mercaderista, vm.id_cliente, CAST(vm.fecha_visita AS DATE)
            \"\"\"
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

        # 8) DETALLE
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
                "planificado_hoy":  p_cnt > 0, # compat
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
"""

# Find the start and end of the existing resumen_dia function
start_idx = content.find('@router.get("/resumen-dia")')
end_idx = content.find('@router.get("/activaciones")')

if start_idx != -1 and end_idx != -1:
    new_content = content[:start_idx] + new_resumen_dia + "\n\n" + content[end_idx:]
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Updated resumen_dia in centro_mando.py successfully.")
else:
    print("Could not find boundaries for replacement.")
