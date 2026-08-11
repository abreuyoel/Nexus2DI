"""
Servicio de PDV (Activación / Desactivación).
Gestiona la activación y desactivación de puntos de interés, con validación
de que todos los clientes del PDV estén visitados antes de permitir el cierre.
Usa exclusivamente SQLAlchemy ORM.
"""

from datetime import date, datetime
from typing import List

from sqlalchemy import cast, Date
from sqlalchemy.orm import Session

from app.models.mercaderista import Mercaderista, MercaderistaRuta
from app.models.visita import Visita
from app.models.ruta import RutaProgramacion, RutaActivada, Ruta
from app.models.cliente import Cliente
from app.models.punto import PuntoInteres


DAY_MAP_ES = {
    0: "Lunes", 1: "Martes", 2: "Miércoles",
    3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo",
}


class PdvService:
    """Gestión de activación/desactivación de PDVs."""

    def __init__(self, db: Session):
        self.db = db

    def _get_mercaderista(self, current_user) -> Mercaderista:
        merc = (
            self.db.query(Mercaderista)
            .filter(Mercaderista.cedula == str(current_user.username))
            .first()
        )
        if not merc:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Mercaderista no encontrado")
        return merc

    # ── PDVs Activos ─────────────────────────────────────────────────────────

    def get_pdv_activos(self, current_user) -> List[dict]:
        """
        Devuelve los PDVs que tienen trabajo pendiente hoy.
        Un PDV está activo si:
        - Su ruta está activada en RUTAS_ACTIVADAS (estado="activo")
        - Tiene programación hoy
        - Tiene al menos un cliente sin visitar, O
        - Todos los clientes están visitados pero falta la desactivación
        """
        merc = self._get_mercaderista(current_user)
        hoy = date.today()
        dia_numero = hoy.weekday()

        print(f"\n[get_pdv_activos] 🔍 mercaderista_id={merc.id}, hoy={hoy}, dia={DAY_MAP_ES[dia_numero]}")

        # DEBUG: ver TODAS las activaciones del mercaderista sin filtrar
        todas_activaciones = (
            self.db.query(RutaActivada)
            .filter(RutaActivada.mercaderista_id == merc.id)
            .all()
        )
        print(f"[get_pdv_activos] 📋 Todas las activaciones ({len(todas_activaciones)}):")
        for a in todas_activaciones:
            ruta_n = self.db.query(Ruta).filter(Ruta.id == a.ruta_id).first()
            print(f"  id={a.id} ruta={a.ruta_id} ({ruta_n.nombre if ruta_n else '?'}) estado='{a.estado}' tipo='{a.tipo_activacion}' fecha={a.fecha_hora_activacion}")

        # Solo rutas que están realmente activadas por este mercaderista
        rutas_activadas = (
            self.db.query(RutaActivada.ruta_id)
            .filter(
                RutaActivada.mercaderista_id == merc.id,
                RutaActivada.estado == "activo",
                RutaActivada.tipo_activacion == "ruta",
            )
            .all()
        )
        rutas_activadas_ids = [r[0] for r in rutas_activadas]
        print(f"[get_pdv_activos] ✅ Rutas activadas filtradas (estado='activo', tipo='ruta'): {rutas_activadas_ids}")

        if not rutas_activadas_ids:
            # Intentar también con tipo_activacion="pdv" (PDVs activados individualmente)
            print("[get_pdv_activos] ⚠️ Sin rutas activadas. Buscando PDVs activados individualmente...")
            pdvs_activados = (
                self.db.query(RutaActivada)
                .filter(
                    RutaActivada.mercaderista_id == merc.id,
                    RutaActivada.estado == "activo",
                    RutaActivada.tipo_activacion == "pdv",
                )
                .all()
            )
            print(f"[get_pdv_activos] PDVs activados individualmente: {[(a.id, a.ruta_id, a.identificador_punto_interes) for a in pdvs_activados]}")
            # Si hay PDVs activados, usar sus rutas
            if pdvs_activados:
                rutas_activadas_ids = list(set(a.ruta_id for a in pdvs_activados if a.ruta_id))
                print(f"[get_pdv_activos] 🟢 Usando rutas de PDVs activados: {rutas_activadas_ids}")

        # 🆕 Fallback: buscar visitas NO finalizadas hoy para construir resultado directo
        modo_fallback_visitas = False
        fallback_puntos_ids = []

        if not rutas_activadas_ids:
            print("[get_pdv_activos] ⚠️ Sin activaciones formales. Buscando visitas pendientes hoy...")

            # Rutas que YA fueron finalizadas hoy (no deben aparecer en el fallback)
            rutas_finalizadas_hoy = (
                self.db.query(RutaActivada.ruta_id)
                .filter(
                    RutaActivada.mercaderista_id == merc.id,
                    RutaActivada.estado == "Finalizado",
                    RutaActivada.tipo_activacion == "ruta",
                    cast(RutaActivada.fecha_hora_activacion, Date) == hoy,
                )
                .all()
            )
            rutas_finalizadas_ids = set(r[0] for r in rutas_finalizadas_hoy)
            print(f"[get_pdv_activos] 🚫 Rutas ya finalizadas hoy: {rutas_finalizadas_ids}")

            visitas_pendientes = (
                self.db.query(Visita)
                .filter(
                    Visita.mercaderista_id == merc.id,
                    Visita.fecha == hoy,
                    Visita.estado != "Finalizada",
                )
                .all()
            )
            print(f"[get_pdv_activos] 📝 Visitas pendientes hoy: {[(v.id, v.punto_id, v.id_cliente, v.estado) for v in visitas_pendientes]}")
            if visitas_pendientes:
                puntos_ids = list(set(v.punto_id for v in visitas_pendientes))
                print(f"[get_pdv_activos] 🎯 Puntos con visitas pendientes: {puntos_ids}")
                # Buscar las rutas asociadas a esos puntos hoy
                rutas_de_puntos = (
                    self.db.query(RutaProgramacion.ruta_id)
                    .filter(
                        RutaProgramacion.punto_id.in_(puntos_ids),
                        RutaProgramacion.dia == DAY_MAP_ES[dia_numero],
                        RutaProgramacion.activo == True,
                    )
                    .distinct()
                    .all()
                )
                todas_rutas_ids = [r[0] for r in rutas_de_puntos]
                print(f"[get_pdv_activos] 🔗 Rutas de los puntos con visitas: {todas_rutas_ids}")

                # Filtrar: solo incluir rutas que NO estan finalizadas
                rutas_filtradas = [rid for rid in todas_rutas_ids if rid not in rutas_finalizadas_ids]
                print(f"[get_pdv_activos] 🟢 Rutas NO finalizadas con visitas pendientes: {rutas_filtradas}")

                if rutas_filtradas:
                    # Solo incluir puntos cuyas rutas NO esten finalizadas
                    puntos_filtrados = []
                    for pid in puntos_ids:
                        prog_punto = (
                            self.db.query(RutaProgramacion)
                            .filter(
                                RutaProgramacion.punto_id == pid,
                                RutaProgramacion.dia == DAY_MAP_ES[dia_numero],
                                RutaProgramacion.activo == True,
                            )
                            .first()
                        )
                        if prog_punto and prog_punto.ruta_id not in rutas_finalizadas_ids:
                            puntos_filtrados.append(pid)

                    print(f"[get_pdv_activos] 🎯 Puntos con visitas en rutas NO finalizadas: {puntos_filtrados}")

                    if puntos_filtrados:
                        rutas_activadas_ids = rutas_filtradas
                        fallback_puntos_ids = puntos_filtrados
                        modo_fallback_visitas = True
                        print(f"[get_pdv_activos] 🔒 Modo fallback: solo puntos {fallback_puntos_ids}")

        if not rutas_activadas_ids:
            return []

        # Programaciones de hoy para las rutas activadas
        # Si es fallback de visitas, filtrar SOLO por los puntos con visitas reales
        if modo_fallback_visitas and fallback_puntos_ids:
            programaciones = (
                self.db.query(RutaProgramacion)
                .filter(
                    RutaProgramacion.punto_id.in_(fallback_puntos_ids),
                    RutaProgramacion.dia == DAY_MAP_ES[dia_numero],
                    RutaProgramacion.activo == True
                )
                .all()
            )
        else:
            programaciones = (
                self.db.query(RutaProgramacion)
                .filter(
                    RutaProgramacion.ruta_id.in_(rutas_activadas_ids),
                    RutaProgramacion.dia == DAY_MAP_ES[dia_numero],
                    RutaProgramacion.activo == True
                )
                .all()
            )

        if not programaciones:
            return []

        # Pre-cache de nombres de ruta (una sola query)
        ruta_nombres = {}
        for rid in set(p.ruta_id for p in programaciones):
            r = self.db.query(Ruta).filter(Ruta.id == rid).first()
            ruta_nombres[rid] = r.nombre if r else f"Ruta #{rid}"

        # Agrupar por PDV
        pdvs: dict = {}
        for prog in programaciones:
            key = prog.punto_id
            if key not in pdvs:
                punto = self.db.query(PuntoInteres).filter(PuntoInteres.id == key).first()
                pdvs[key] = {
                    "punto_id": key,
                    "punto_nombre": punto.nombre if punto else "Sin nombre",
                    "ruta_id": prog.ruta_id,
                    "ruta_nombre": ruta_nombres.get(prog.ruta_id, f"Ruta #{prog.ruta_id}"),
                    "clientes_pendientes": [],
                    "clientes_listos": [],
                    "falta_desactivacion": False,
                    "ultima_visita_local_id": None,
                    "ultima_visita_cliente_id": None,
                    "ultima_visita_cliente_nombre": None,
                }

            cliente = self.db.query(Cliente).filter(Cliente.id == prog.id_cliente).first()
            cliente_nombre = cliente.nombre if cliente else f"Cliente #{prog.id_cliente}"

            # Verificar si este cliente ya tiene visita hoy
            visita_hoy = (
                self.db.query(Visita)
                .filter(
                    Visita.mercaderista_id == merc.id,
                    Visita.punto_id == key,
                    Visita.id_cliente == prog.id_cliente,
                    Visita.fecha == hoy,
                )
                .first()
            )

            if visita_hoy:
                pdvs[key]["clientes_listos"].append(cliente_nombre)
                pdvs[key]["ultima_visita_local_id"] = visita_hoy.id
                pdvs[key]["ultima_visita_cliente_id"] = prog.id_cliente
                pdvs[key]["ultima_visita_cliente_nombre"] = cliente_nombre
            else:
                pdvs[key]["clientes_pendientes"].append(cliente_nombre)

        # Determinar si falta desactivación: todos los clientes visitados
        # pero el PDV no está desactivado.
        # ⚠️ Solo incluir PDVs que tienen al menos una visita real creada hoy.
        # Si un PDV no tiene ninguna visita, no hay "trabajo en progreso".
        result = []
        for pdv_data in pdvs.values():
            if not pdv_data["clientes_pendientes"] and not pdv_data["clientes_listos"]:
                continue  # Sin clientes, ignorar

            # 🆕 Filtrar: solo PDVs con al menos una visita real hoy
            if pdv_data["ultima_visita_local_id"] is None:
                continue  # Sin visitas → no hay trabajo real

            if not pdv_data["clientes_pendientes"]:
                # Todos visitados → ¿falta desactivación?
                # Solo marcamos falta_desactivacion si hay al menos un cliente listo
                pdv_data["falta_desactivacion"] = len(pdv_data["clientes_listos"]) > 0

            result.append(pdv_data)

        return result

    # ── Activar PDV ──────────────────────────────────────────────────────────

    def activar_pdv(
        self, current_user, id_punto: str, id_ruta: int = None
    ) -> dict:
        """Registra la activación de un PDV."""
        merc = self._get_mercaderista(current_user)
        hoy = date.today()

        # Verificar si ya está activado hoy (estado Activo)
        existente = (
            self.db.query(RutaActivada)
            .filter(
                RutaActivada.mercaderista_id == merc.id,
                RutaActivada.identificador_punto_interes == id_punto,
                cast(RutaActivada.fecha_hora_activacion, Date) == hoy,
            )
            .first()
        )

        if existente:
            return {"success": True, "id_activacion": existente.id, "ya_activado": True}

        activacion = RutaActivada(
            mercaderista_id=merc.id,
            identificador_punto_interes=id_punto,
            ruta_id=id_ruta,
            fecha_hora_activacion=datetime.now(),
            estado="Activo",
            tipo_activacion="mercaderista",
        )
        self.db.add(activacion)
        self.db.commit()
        self.db.refresh(activacion)

        return {"success": True, "id_activacion": activacion.id, "ya_activado": False}

    # ── Activar Ruta ──────────────────────────────────────────────────────────

    def activar_ruta(self, current_user, id_ruta: int) -> dict:
        """Registra la activación de una ruta completa a nivel de backend.
        Inserta un registro en RUTAS_ACTIVADAS que persiste entre sesiones del navegador."""
        merc = self._get_mercaderista(current_user)
        hoy = date.today()

        # Verificar si ya existe una activación para esta ruta hoy
        existente = (
            self.db.query(RutaActivada)
            .filter(
                RutaActivada.mercaderista_id == merc.id,
                RutaActivada.ruta_id == id_ruta,
                cast(RutaActivada.fecha_hora_activacion, Date) == hoy,
            )
            .first()
        )

        if existente:
            # Si estaba finalizado, reactivar
            if existente.estado != "activo":
                existente.estado = "activo"
                existente.tipo_activacion = "ruta"
                existente.fecha_hora_activacion = datetime.now()
                self.db.commit()
                print(f"[activar_ruta] 🔄 Reactivando ruta {id_ruta} (estaba '{existente.estado}') -> id={existente.id}")
                return {"success": True, "id_activacion": existente.id, "ya_activado": False, "reactivado": True}
            print(f"[activar_ruta] ℹ️ Ruta {id_ruta} ya activa, id={existente.id}")
            return {"success": True, "id_activacion": existente.id, "ya_activado": True}

        activacion = RutaActivada(
            mercaderista_id=merc.id,
            ruta_id=id_ruta,
            fecha_hora_activacion=datetime.now(),
            estado="activo",
            tipo_activacion="ruta",
        )
        self.db.add(activacion)
        self.db.commit()
        self.db.refresh(activacion)

        return {"success": True, "id_activacion": activacion.id, "ya_activado": False}

    # ── Finalizar Ruta ───────────────────────────────────────────────────────

    def finalizar_ruta(self, current_user, id_ruta: int) -> dict:
        """Marca como Finalizado el registro de RUTAS_ACTIVADAS para esta ruta.
        Antes de finalizar, valida que no haya visitas pendientes en los PDVs
        de esta ruta para hoy. Si hay pendientes, rechaza la finalización."""
        merc = self._get_mercaderista(current_user)
        hoy = date.today()
        dia_numero = hoy.weekday()

        # Aceptar ambas variantes de casing: "activo" (ruta) y "Activo" (pdv)
        activacion = (
            self.db.query(RutaActivada)
            .filter(
                RutaActivada.mercaderista_id == merc.id,
                RutaActivada.ruta_id == id_ruta,
                cast(RutaActivada.fecha_hora_activacion, Date) == hoy,
                RutaActivada.estado.in_(["activo", "Activo"]),
            )
            .first()
        )

        if not activacion:
            return {"success": True, "mensaje": "Ruta ya estaba finalizada"}

        # Validar que no haya visitas pendientes en los PDVs de esta ruta hoy
        puntos_de_ruta = (
            self.db.query(RutaProgramacion.punto_id)
            .filter(
                RutaProgramacion.ruta_id == id_ruta,
                RutaProgramacion.dia == DAY_MAP_ES[dia_numero],
                RutaProgramacion.activo == True,
            )
            .distinct()
            .all()
        )
        puntos_ids = [p[0] for p in puntos_de_ruta]

        if puntos_ids:
            visitas_pendientes = (
                self.db.query(Visita)
                .filter(
                    Visita.mercaderista_id == merc.id,
                    Visita.punto_id.in_(puntos_ids),
                    Visita.fecha == hoy,
                    Visita.estado.in_(["Pendiente", "En Progreso"]),
                )
                .all()
            )

            if visitas_pendientes:
                puntos_con_pendientes = list(set(v.punto_id for v in visitas_pendientes))
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "visitas_pendientes",
                        "mensaje": f"No se puede finalizar la ruta. Hay {len(visitas_pendientes)} visita(s) pendiente(s) en {len(puntos_con_pendientes)} PDV(s).",
                        "visitas_pendientes": [
                            {"id_visita": v.id, "punto_id": v.punto_id, "id_cliente": v.id_cliente, "estado": v.estado}
                            for v in visitas_pendientes
                        ],
                    },
                )

        activacion.estado = "Finalizado"
        self.db.commit()

        return {"success": True, "mensaje": "Ruta finalizada correctamente"}

    # ── Desactivar PDV ───────────────────────────────────────────────────────

    def desactivar_pdv(self, current_user, id_punto: str) -> dict:
        """Desactiva un PDV (actualiza estado a Finalizado).
        
        Busca tanto registros de activación por ruta (estado="activo")
        como por PDV individual (estado="Activo"). Si no encuentra ninguno,
        finaliza las visitas pendientes asociadas para evitar que el fallback
        de get_pdv_activos() siga devolviendo el PDV.
        """
        merc = self._get_mercaderista(current_user)
        hoy = date.today()

        # Buscar con ambas variantes de casing: "activo" (ruta) y "Activo" (pdv)
        activacion = (
            self.db.query(RutaActivada)
            .filter(
                RutaActivada.mercaderista_id == merc.id,
                RutaActivada.identificador_punto_interes == id_punto,
                cast(RutaActivada.fecha_hora_activacion, Date) == hoy,
                RutaActivada.estado.in_(["activo", "Activo"]),
            )
            .first()
        )

        print(f"[desactivar_pdv] 🔍 Buscando activación para punto={id_punto} merc={merc.id}: {'encontrada' if activacion else 'NO encontrada'}")

        if activacion:
            activacion.estado = "Finalizado"
            self.db.commit()
            print(f"[desactivar_pdv] ✅ Activación id={activacion.id} marcada como Finalizado")
            return {"success": True, "mensaje": "PDV desactivado correctamente"}

        # No se encontró registro RUTAS_ACTIVADAS, pero puede haber visitas
        # pendientes que el fallback de get_pdv_activos() está detectando.
        # Finalizar esas visitas para que el PDV deje de aparecer como activo.
        visitas_pendientes = (
            self.db.query(Visita)
            .filter(
                Visita.mercaderista_id == merc.id,
                Visita.punto_id == id_punto,
                Visita.fecha == hoy,
                Visita.estado.in_(["Pendiente", "En Progreso"]),
            )
            .all()
        )

        if visitas_pendientes:
            for v in visitas_pendientes:
                v.estado = "Finalizada"
            self.db.commit()
            print(f"[desactivar_pdv] ⚠️ Sin registro RUTAS_ACTIVADAS, pero se finalizaron {len(visitas_pendientes)} visita(s) pendiente(s) para {id_punto}")
            return {"success": True, "mensaje": f"PDV desactivado ({len(visitas_pendientes)} visita(s) finalizada(s))"}

        print(f"[desactivar_pdv] ℹ️ Sin activación ni visitas pendientes para {id_punto}")
        return {"success": True, "mensaje": "PDV ya estaba desactivado"}

    # ── Validar Cierre de PDV ────────────────────────────────────────────────

    def validar_cierre_pdv(
        self, current_user, id_punto: str
    ) -> dict:
        """
        Valida que todos los clientes programados en un PDV para hoy
        estén visitados antes de permitir la desactivación.
        """
        merc = self._get_mercaderista(current_user)
        hoy = date.today()
        dia_numero = hoy.weekday()

        # Rutas del mercaderista
        mis_rutas_ids = [
            mr.ruta_id
            for mr in self.db.query(MercaderistaRuta.ruta_id)
            .filter(MercaderistaRuta.mercaderista_id == merc.id)
            .all()
        ]

        # Obtener todos los clientes programados hoy para este PDV
        programaciones = (
            self.db.query(RutaProgramacion)
            .filter(
                RutaProgramacion.punto_id == id_punto,
                RutaProgramacion.ruta_id.in_(mis_rutas_ids),
                RutaProgramacion.dia == DAY_MAP_ES[dia_numero],
                RutaProgramacion.activo == True,
            )
            .all()
        )

        if not programaciones:
            return {
                "puede_cerrar": True,
                "total_clientes": 0,
                "clientes_visitados": 0,
                "clientes_pendientes": [],
                "mensaje": "No hay clientes programados para hoy en este PDV",
            }

        total_clientes = len(programaciones)
        clientes_pendientes: List[str] = []

        for prog in programaciones:
            cliente = self.db.query(Cliente).filter(Cliente.id == prog.id_cliente).first()
            cliente_nombre = cliente.nombre if cliente else f"Cliente #{prog.id_cliente}"

            visita_hoy = (
                self.db.query(Visita)
                .filter(
                    Visita.mercaderista_id == merc.id,
                    Visita.punto_id == id_punto,
                    Visita.id_cliente == prog.id_cliente,
                    Visita.fecha == hoy,
                )
                .first()
            )

            if not visita_hoy:
                clientes_pendientes.append(cliente_nombre)

        clientes_visitados = total_clientes - len(clientes_pendientes)
        puede_cerrar = len(clientes_pendientes) == 0

        return {
            "puede_cerrar": puede_cerrar,
            "total_clientes": total_clientes,
            "clientes_visitados": clientes_visitados,
            "clientes_pendientes": clientes_pendientes,
            "mensaje": (
                "Todos los clientes han sido visitados" if puede_cerrar
                else f"Faltan {len(clientes_pendientes)} cliente(s) por visitar: {', '.join(clientes_pendientes)}"
            ),
        }
