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

from app.core.timezone import get_adjusted_now, get_adjusted_today

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
        - Tiene al menos una visita real hoy y clientes por completar/desactivar
        """
        merc = self._get_mercaderista(current_user)
        hoy = get_adjusted_today(self.db, merc.id)
        dia_numero = hoy.weekday()
        dia_es = DAY_MAP_ES[dia_numero]

        # 1. Buscar rutas activadas por este mercaderista
        rutas_activadas = (
            self.db.query(RutaActivada.ruta_id)
            .filter(
                RutaActivada.mercaderista_id == merc.id,
                RutaActivada.estado == "activo",
                RutaActivada.tipo_activacion == "ruta",
            )
            .all()
        )
        rutas_activadas_ids = [r[0] for r in rutas_activadas if r[0]]

        if not rutas_activadas_ids:
            # Buscar PDVs activados individualmente
            pdvs_activados = (
                self.db.query(RutaActivada.ruta_id)
                .filter(
                    RutaActivada.mercaderista_id == merc.id,
                    RutaActivada.estado == "activo",
                    RutaActivada.tipo_activacion == "pdv",
                )
                .all()
            )
            if pdvs_activados:
                rutas_activadas_ids = list(set(r[0] for r in pdvs_activados if r[0]))

        modo_fallback_visitas = False
        fallback_puntos_ids = []

        if not rutas_activadas_ids:
            # Fallback: buscar si hay visitas pendientes hoy
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
            rutas_finalizadas_ids = set(r[0] for r in rutas_finalizadas_hoy if r[0])

            visitas_pendientes = (
                self.db.query(Visita.punto_id)
                .filter(
                    Visita.mercaderista_id == merc.id,
                    Visita.fecha == hoy,
                    Visita.estado != "Finalizada",
                )
                .all()
            )
            if visitas_pendientes:
                puntos_ids = list(set(v[0] for v in visitas_pendientes if v[0]))
                if puntos_ids:
                    progs = (
                        self.db.query(RutaProgramacion.punto_id, RutaProgramacion.ruta_id)
                        .filter(
                            RutaProgramacion.punto_id.in_(puntos_ids),
                            RutaProgramacion.dia == dia_es,
                            RutaProgramacion.activo == True,
                        )
                        .all()
                    )
                    rutas_validas = set()
                    puntos_validos = []
                    for pid, rid in progs:
                        if rid and rid not in rutas_finalizadas_ids:
                            rutas_validas.add(rid)
                            puntos_validos.append(pid)

                    if rutas_validas and puntos_validos:
                        rutas_activadas_ids = list(rutas_validas)
                        fallback_puntos_ids = list(set(puntos_validos))
                        modo_fallback_visitas = True

        if not rutas_activadas_ids:
            return []

        # 2. Programaciones de hoy
        prog_query = self.db.query(RutaProgramacion).filter(
            RutaProgramacion.dia == dia_es,
            RutaProgramacion.activo == True,
        )
        if modo_fallback_visitas and fallback_puntos_ids:
            prog_query = prog_query.filter(RutaProgramacion.punto_id.in_(fallback_puntos_ids))
        else:
            prog_query = prog_query.filter(RutaProgramacion.ruta_id.in_(rutas_activadas_ids))

        programaciones = prog_query.all()
        if not programaciones:
            return []

        # 3. BATCH PRELOAD: Evitar N+1 queries
        puntos_ids_set = set(p.punto_id for p in programaciones)
        clientes_ids_set = set(p.id_cliente for p in programaciones)
        rutas_ids_set = set(p.ruta_id for p in programaciones)

        # Batch Nombres de Ruta
        rutas_db = self.db.query(Ruta.id, Ruta.nombre).filter(Ruta.id.in_(rutas_ids_set)).all()
        ruta_nombres = {r[0]: r[1] for r in rutas_db}

        # Batch Puntos
        puntos_db = self.db.query(PuntoInteres.id, PuntoInteres.nombre).filter(PuntoInteres.id.in_(puntos_ids_set)).all()
        puntos_nombres = {p[0]: p[1] for p in puntos_db}

        # Batch Clientes
        clientes_db = self.db.query(Cliente.id, Cliente.nombre).filter(Cliente.id.in_(clientes_ids_set)).all()
        clientes_nombres = {c[0]: c[1] for c in clientes_db}

        # Batch Visitas de hoy para estos puntos y clientes
        visitas_hoy_db = (
            self.db.query(Visita)
            .filter(
                Visita.mercaderista_id == merc.id,
                Visita.punto_id.in_(puntos_ids_set),
                Visita.id_cliente.in_(clientes_ids_set),
                Visita.fecha == hoy,
            )
            .all()
        )
        visitas_map = {(v.punto_id, v.id_cliente): v for v in visitas_hoy_db}

        # Batch PDVs desactivados hoy (para no mostrarlos como pendientes de desactivación)
        pdvs_desactivados_hoy = {
            a[0]
            for a in self.db.query(RutaActivada.identificador_punto_interes)
            .filter(
                RutaActivada.mercaderista_id == merc.id,
                RutaActivada.estado == "Finalizado",
                cast(RutaActivada.fecha_hora_activacion, Date) == hoy,
            )
            .all()
            if a[0]
        }

        # 4. Agrupar en memoria
        pdvs: dict = {}
        for prog in programaciones:
            key = prog.punto_id
            if key not in pdvs:
                pdvs[key] = {
                    "punto_id": key,
                    "punto_nombre": puntos_nombres.get(key, "Sin nombre"),
                    "ruta_id": prog.ruta_id,
                    "ruta_nombre": ruta_nombres.get(prog.ruta_id, f"Ruta #{prog.ruta_id}"),
                    "clientes_pendientes": [],
                    "clientes_listos": [],
                    "falta_desactivacion": False,
                    "ultima_visita_local_id": None,
                    "ultima_visita_cliente_id": None,
                    "ultima_visita_cliente_nombre": None,
                }

            cliente_nombre = clientes_nombres.get(prog.id_cliente, f"Cliente #{prog.id_cliente}")
            visita_hoy = visitas_map.get((key, prog.id_cliente))

            if visita_hoy:
                pdvs[key]["clientes_listos"].append(cliente_nombre)
                pdvs[key]["ultima_visita_local_id"] = visita_hoy.id
                pdvs[key]["ultima_visita_cliente_id"] = prog.id_cliente
                pdvs[key]["ultima_visita_cliente_nombre"] = cliente_nombre
            else:
                pdvs[key]["clientes_pendientes"].append(cliente_nombre)

        result = []
        for pdv_data in pdvs.values():
            if not pdv_data["clientes_pendientes"] and not pdv_data["clientes_listos"]:
                continue
            # Solo PDVs con al menos una visita real hoy
            if pdv_data["ultima_visita_local_id"] is None:
                continue

            # Si ya fue desactivado hoy, no mostrarlo en la lista de trabajo pendiente
            if pdv_data["punto_id"] in pdvs_desactivados_hoy:
                continue

            if not pdv_data["clientes_pendientes"]:
                pdv_data["falta_desactivacion"] = len(pdv_data["clientes_listos"]) > 0

            result.append(pdv_data)

        return result

    # ── Activar PDV ──────────────────────────────────────────────────────────

    def activar_pdv(
        self, current_user, id_punto: str, id_ruta: int = None
    ) -> dict:
        """Registra la activación de un PDV."""
        merc = self._get_mercaderista(current_user)
        hoy = get_adjusted_today(self.db, merc.id)

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
            fecha_hora_activacion=get_adjusted_now(self.db, merc.id),
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
        hoy = get_adjusted_today(self.db, merc.id)

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
                existente.fecha_hora_activacion = get_adjusted_now(self.db, merc.id)
                self.db.commit()
                print(f"[activar_ruta] 🔄 Reactivando ruta {id_ruta} (estaba '{existente.estado}') -> id={existente.id}")
                return {"success": True, "id_activacion": existente.id, "ya_activado": False, "reactivado": True}
            print(f"[activar_ruta] ℹ️ Ruta {id_ruta} ya activa, id={existente.id}")
            return {"success": True, "id_activacion": existente.id, "ya_activado": True}

        activacion = RutaActivada(
            mercaderista_id=merc.id,
            ruta_id=id_ruta,
            fecha_hora_activacion=get_adjusted_now(self.db, merc.id),
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
        hoy = get_adjusted_today(self.db, merc.id)
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
        hoy = get_adjusted_today(self.db, merc.id)

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
            return {"success": True, "mensaje": "PDV desactivado correctamente"}

        # Buscar id_ruta para respetar la restricción NOT NULL de la base de datos
        prog = (
            self.db.query(RutaProgramacion.ruta_id)
            .filter(
                RutaProgramacion.punto_id == id_punto,
                RutaProgramacion.activo == True,
            )
            .first()
        )
        ruta_id = prog[0] if prog else None
        if not ruta_id:
            mr = self.db.query(MercaderistaRuta.ruta_id).filter(MercaderistaRuta.mercaderista_id == merc.id).first()
            ruta_id = mr[0] if mr else 1

        desactivacion = RutaActivada(
            mercaderista_id=merc.id,
            ruta_id=ruta_id,
            identificador_punto_interes=id_punto,
            fecha_hora_activacion=get_adjusted_now(self.db, merc.id),
            estado="Finalizado",
            tipo_activacion="pdv",
        )
        self.db.add(desactivacion)

        # Finalizar cualquier visita pendiente remanente para este punto
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
        for v in visitas_pendientes:
            v.estado = "Finalizada"

        self.db.commit()
        return {"success": True, "mensaje": "PDV desactivado correctamente"}

    # ── Validar Cierre de PDV ────────────────────────────────────────────────

    def validar_cierre_pdv(
        self, current_user, id_punto: str
    ) -> dict:
        """
        Valida que todos los clientes programados en un PDV para hoy
        estén visitados antes de permitir la desactivación.
        """
        merc = self._get_mercaderista(current_user)
        hoy = get_adjusted_today(self.db, merc.id)
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
