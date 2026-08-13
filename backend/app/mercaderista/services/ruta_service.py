"""
Servicio de Rutas del Mercaderista.
Consulta las rutas asignadas, los PDVs programados para hoy y los clientes
de cada PDV. Usa exclusivamente SQLAlchemy ORM.
"""

from datetime import date, datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import cast, Date

from app.models.mercaderista import Mercaderista, MercaderistaRuta
from app.models.ruta import Ruta, RutaProgramacion, RutaActivada
from app.models.punto import PuntoInteres
from app.models.cliente import Cliente
from app.models.visita import Visita

DAY_MAP_ES = {
    0: "Lunes", 1: "Martes", 2: "Miércoles",
    3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo",
}


class RutaService:
    """Consulta de rutas del mercaderista para el día actual."""

    def __init__(self, db: Session):
        self.db = db

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _get_mercaderista(self, current_user) -> Mercaderista:
        """Obtiene el registro MERCADERISTAS asociado al usuario autenticado."""
        merc = (
            self.db.query(Mercaderista)
            .filter(Mercaderista.cedula == str(current_user.username))
            .first()
        )
        if not merc:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Mercaderista no encontrado")
        return merc

    def _dia_semana_hoy(self) -> dict:
        """Devuelve el día de la semana en español y la fecha actual."""
        hoy = date.today()
        return {
            "dia_semana": DAY_MAP_ES[hoy.weekday()],
            "fecha": hoy.isoformat(),
            "dia_numero": hoy.weekday(),
        }

    # ── Rutas asignadas ──────────────────────────────────────────────────────

    def get_rutas_asignadas(self, mercaderista_id: int) -> List[dict]:
        """Obtiene todas las rutas asignadas al mercaderista."""
        rows = (
            self.db.query(MercaderistaRuta, Ruta)
            .join(Ruta, MercaderistaRuta.ruta_id == Ruta.id)
            .filter(MercaderistaRuta.mercaderista_id == mercaderista_id)
            .all()
        )
        return [
            {
                "id_ruta": mr.ruta_id,
                "tipo": mr.tipo_ruta,
                "nombre": r.nombre,
            }
            for mr, r in rows
        ]

    # ── PDVs del día ─────────────────────────────────────────────────────────

    def get_pdvs_programados(
        self, mercaderista_id: int, dia_numero: int
    ) -> List[dict]:
        """
        Obtiene los PDVs programados para hoy con sus clientes y estado de visita.
        Une RUTA_PROGRAMACION → PUNTOS_INTERES1 → CLIENTES.
        Filtra por mercaderista_id y día de la semana.
        """
        dia_es = DAY_MAP_ES[dia_numero]
        print(f"\n[get_pdvs_programados] 🔍 mercaderista_id={mercaderista_id}, dia={dia_es}")

        # Obtenemos las rutas del mercaderista
        mis_rutas_ids = [
            mr.ruta_id
            for mr in self.db.query(MercaderistaRuta.ruta_id)
            .filter(MercaderistaRuta.mercaderista_id == mercaderista_id)
            .all()
        ]
        print(f"[get_pdvs_programados] 📋 Rutas asignadas: {mis_rutas_ids}")

        if not mis_rutas_ids:
            print("[get_pdvs_programados] ⚠️ Sin rutas asignadas, retornando vacío")
            return []

        # Obtener los nombres de todas las rutas de una sola vez
        rutas_nombres = {
            r.id: r.nombre
            for r in self.db.query(Ruta.id, Ruta.nombre)
            .filter(Ruta.id.in_(mis_rutas_ids))
            .all()
        }
        print(f"[get_pdvs_programados] 🏷️ Nombres de rutas: {rutas_nombres}")

        # PDVs programados para hoy en las rutas del mercaderista
        programaciones = (
            self.db.query(RutaProgramacion, PuntoInteres, Cliente)
            .join(PuntoInteres, RutaProgramacion.punto_id == PuntoInteres.id)
            .join(Cliente, RutaProgramacion.id_cliente == Cliente.id)
            .filter(
                RutaProgramacion.ruta_id.in_(mis_rutas_ids),
                RutaProgramacion.dia == dia_es,
                RutaProgramacion.activo == True,
            )
            .all()
        )
        print(f"[get_pdvs_programados] 📊 Programaciones encontradas: {len(programaciones)}")
        for prog, punto, cliente in programaciones:
            print(f"  ruta={prog.ruta_id} pdv={punto.id} '{punto.nombre}' cliente={cliente.id} '{cliente.nombre}' prioridad={prog.prioridad}")

        # Obtener todas las visitas de este mercaderista hoy de una sola vez
        hoy = date.today()
        visitas_hoy_db = (
            self.db.query(Visita)
            .filter(
                Visita.mercaderista_id == mercaderista_id,
                Visita.fecha == hoy,
            )
            .all()
        )
        print(f"[get_pdvs_programados] 📝 Visitas hoy: {len(visitas_hoy_db)}")
        for v in visitas_hoy_db:
            print(f"  visita_id={v.id} pdv={v.punto_id} cliente={v.id_cliente} estado='{v.estado}'")
        
        # Crear un mapa/dict de visitas hoy indexado por (punto_id, id_cliente): (id_visita, estado)
        visitas_hoy_map = {
            (v.punto_id, v.id_cliente): (v.id, v.estado)
            for v in visitas_hoy_db
        }

        # Agrupar por PDV
        pdvs_map: dict = {}
        for prog, punto, cliente in programaciones:
            key = punto.id
            if key not in pdvs_map:
                ruta_nombre = rutas_nombres.get(prog.ruta_id)

                pdvs_map[key] = {
                    "id_punto": punto.id,
                    "nombre": punto.nombre or "Sin nombre",
                    "cadena": punto.cadena,
                    "direccion": punto.direccion,
                    "latitud": punto.latitud,
                    "longitud": punto.longitud,
                    "prioridad": prog.prioridad,
                    "id_ruta": prog.ruta_id,
                    "ruta_nombre": ruta_nombre,
                    "clientes": [],
                }

            visita_info = visitas_hoy_map.get((punto.id, cliente.id))
            id_visita = visita_info[0] if visita_info else None
            estado_visita = visita_info[1] if visita_info else None
            # IDÉNTICO al APK: solo se marca como visitado si la visita está Finalizada
            cliente_visitado = (estado_visita == "Finalizada")
            pdvs_map[key]["clientes"].append({
                "id_cliente": cliente.id,
                "nombre": cliente.nombre,
                "visitado": cliente_visitado,
                "id_visita": id_visita,
            })

        # Limpiar y convertir a lista
        result = list(pdvs_map.values())

        # Ordenar por prioridad
        PRIORIDAD_ORDEN = {"Alta": 0, "Media": 1, "Baja": 2}
        result.sort(key=lambda p: PRIORIDAD_ORDEN.get(p.get("prioridad", "Media"), 1))

        print(f"[get_pdvs_programados] 🎯 Resultado final: {len(result)} PDVs")
        for pdv in result:
            print(f"  PDV '{pdv['nombre']}' ruta={pdv['id_ruta']} prioridad={pdv['prioridad']} clientes={len(pdv['clientes'])}")
            for c in pdv['clientes']:
                print(f"    cliente id={c['id_cliente']} '{c['nombre']}' visitado={c['visitado']} id_visita={c['id_visita']}")

        return result

    # ── API principal ────────────────────────────────────────────────────────

    def get_mis_rutas(self, current_user) -> dict:
        """
        Devuelve la estructura completa de rutas del día para el mercaderista.
        Separa en rutas fijas y variables. Incluye campo 'activada' desde RUTAS_ACTIVADAS.
        """
        merc = self._get_mercaderista(current_user)
        dia_info = self._dia_semana_hoy()
        hoy = date.today()

        rutas_asignadas = self.get_rutas_asignadas(merc.id)
        pdvs = self.get_pdvs_programados(merc.id, dia_info["dia_numero"])

        # Consultar RUTAS_ACTIVADAS para hoy — determina qué rutas están activadas y cuáles finalizadas
        today_start = datetime.combine(hoy, datetime.min.time())
        today_end = datetime.combine(hoy, datetime.max.time())
        activaciones_hoy = (
            self.db.query(RutaActivada)
            .filter(
                RutaActivada.mercaderista_id == merc.id,
                RutaActivada.fecha_hora_activacion >= today_start,
                RutaActivada.fecha_hora_activacion <= today_end,
            )
            .all()
        )
        rutas_activadas_ids = {a.ruta_id for a in activaciones_hoy if a.ruta_id and a.estado == "activo"}
        rutas_finalizadas_ids = {a.ruta_id for a in activaciones_hoy if a.ruta_id and a.estado == "Finalizado"}
        print(f"\n[get_mis_rutas] 🔍 merc_id={merc.id}, hoy={hoy}, dia={dia_info['dia_semana']}")
        print(f"[get_mis_rutas] 📋 Activaciones hoy: {[(a.id, a.ruta_id, a.estado, a.tipo_activacion) for a in activaciones_hoy]}")
        print(f"[get_mis_rutas] ✅ Rutas activadas: {rutas_activadas_ids} | Finalizadas: {rutas_finalizadas_ids}")

        # Indexar PDVs por ruta
        pdvs_por_ruta: dict = {}
        for pdv in pdvs:
            rid = pdv["id_ruta"]
            if rid not in pdvs_por_ruta:
                pdvs_por_ruta[rid] = []
            pdvs_por_ruta[rid].append(pdv)

        # Separar en fijas y variables
        rutas_fijas = []
        rutas_variables = []
        for ra in rutas_asignadas:
            ruta_pdvs = pdvs_por_ruta.get(ra["id_ruta"], [])
            ruta_data = {
                "id_ruta": ra["id_ruta"],
                "tipo": ra["tipo"],
                "nombre": ra["nombre"],
                "pdvs": ruta_pdvs,
                "activada": ra["id_ruta"] in rutas_activadas_ids,
                "finalizada": ra["id_ruta"] in rutas_finalizadas_ids,
            }
            if ra["tipo"] == "Variable":
                rutas_variables.append(ruta_data)
            else:
                rutas_fijas.append(ruta_data)

        return {
            "mercaderista_id": merc.id,
            "dia_semana": dia_info["dia_semana"],
            "fecha": dia_info["fecha"],
            "rutas_fijas": rutas_fijas,
            "rutas_variables": rutas_variables,
        }

    def get_pdvs_de_ruta(self, current_user, id_ruta: int) -> dict:
        """
        Todos los PDV de una ruta (sin filtro de día), con estado de visita de hoy.
        Equivale al endpoint GET /api/merc/ruta/{id_ruta}/pdvs de mercaderista_portal.py.
        """
        merc = self._get_mercaderista(current_user)
        hoy = date.today()

        programaciones = (
            self.db.query(RutaProgramacion, PuntoInteres, Cliente)
            .join(PuntoInteres, RutaProgramacion.punto_id == PuntoInteres.id)
            .join(Cliente, RutaProgramacion.id_cliente == Cliente.id)
            .filter(
                RutaProgramacion.ruta_id == id_ruta,
                RutaProgramacion.activo == True,
            )
            .order_by(PuntoInteres.nombre)
            .all()
        )

        visitas_hoy = {
            (v.punto_id, v.id_cliente): (v.id, v.estado)
            for v in self.db.query(Visita)
            .filter(
                Visita.mercaderista_id == merc.id,
                Visita.fecha == hoy,
            )
            .all()
        }

        pdvs_map: dict = {}
        for prog, punto, cliente in programaciones:
            key = punto.id
            if key not in pdvs_map:
                lat = None
                lon = None
                try:
                    if punto.latitud:
                        lat = float(str(punto.latitud).replace(",", "."))
                    if punto.longitud:
                        lon = float(str(punto.longitud).replace(",", "."))
                except (ValueError, TypeError):
                    pass

                pdvs_map[key] = {
                    "id_punto": punto.id,
                    "nombre": punto.nombre or "Sin nombre",
                    "cadena": punto.cadena,
                    "direccion": punto.direccion,
                    "latitud": lat,
                    "longitud": lon,
                    "id_ruta": id_ruta,
                    "clients": [],
                }

            visita_info = visitas_hoy.get((punto.id, cliente.id))
            id_visita = visita_info[0] if visita_info else None
            estado_visita = visita_info[1] if visita_info else None
            # IDÉNTICO al APK: solo se marca como visitado si la visita está Finalizada
            cliente_visitado = (estado_visita == "Finalizada")
            pdvs_map[key]["clients"].append({
                "id_cliente": cliente.id,
                "nombre": cliente.nombre,
                "visitado": cliente_visitado,
                "visita_id": id_visita,
            })

        return {"id_ruta": id_ruta, "pdvs": list(pdvs_map.values())}

    def get_programacion_completa(self, current_user) -> dict:
        """
        Programación completa del día: mercaderista + rutas + productos.
        Equivale a getProgramacion() de la APK — un solo endpoint para el dashboard.
        """
        merc = self._get_mercaderista(current_user)
        dia_info = self._dia_semana_hoy()

        # Rutas (misma lógica que get_mis_rutas)
        rutas_asignadas = self.get_rutas_asignadas(merc.id)
        pdvs = self.get_pdvs_programados(merc.id, dia_info["dia_numero"])
        hoy = date.today()

        # Consultar RUTAS_ACTIVADAS para hoy
        today_start = datetime.combine(hoy, datetime.min.time())
        today_end = datetime.combine(hoy, datetime.max.time())
        activaciones_hoy = (
            self.db.query(RutaActivada)
            .filter(
                RutaActivada.mercaderista_id == merc.id,
                RutaActivada.fecha_hora_activacion >= today_start,
                RutaActivada.fecha_hora_activacion <= today_end,
            )
            .all()
        )
        rutas_activadas_ids = {a.ruta_id for a in activaciones_hoy if a.ruta_id and a.estado == "activo"}
        rutas_finalizadas_ids = {a.ruta_id for a in activaciones_hoy if a.ruta_id and a.estado == "Finalizado"}

        pdvs_por_ruta: dict = {}
        for pdv in pdvs:
            rid = pdv["id_ruta"]
            if rid not in pdvs_por_ruta:
                pdvs_por_ruta[rid] = []
            pdvs_por_ruta[rid].append(pdv)

        rutas_fijas = []
        rutas_variables = []
        for ra in rutas_asignadas:
            ruta_pdvs = pdvs_por_ruta.get(ra["id_ruta"], [])
            ruta_data = {
                "id_ruta": ra["id_ruta"],
                "tipo": ra["tipo"],
                "nombre": ra["nombre"],
                "pdvs": ruta_pdvs,
                "activada": ra["id_ruta"] in rutas_activadas_ids,
                "finalizada": ra["id_ruta"] in rutas_finalizadas_ids,
            }
            if ra["tipo"] == "Variable":
                rutas_variables.append(ruta_data)
            else:
                rutas_fijas.append(ruta_data)

        # Productos (catálogo completo)
        from app.mercaderista.services.visita_service import VisitaService
        prod_result = VisitaService(self.db).get_productos_catalogo(id_cliente=None)

        # Aplanar productos de todas las categorías
        productos = []
        for cat in prod_result.get("categorias", []):
            for p in cat.get("productos", []):
                productos.append({
                    "id_producto": p.get("id_producto"),
                    "sku": p.get("sku"),
                    "nombre": p.get("nombre"),
                    "fabricante": p.get("fabricante"),
                    "categoria_id": cat.get("id_categoria"),
                    "categoria_nombre": cat.get("nombre"),
                    "precio_base_bs": p.get("precio_base_bs"),
                    "precio_base_ds": p.get("precio_base_ds"),
                })

        return {
            "fecha": dia_info["fecha"],
            "dia_semana": dia_info["dia_semana"],
            "mercaderista": {
                "id": merc.id,
                "nombre": merc.nombre,
                "cedula": merc.cedula,
            },
            "rutas_fijas": rutas_fijas,
            "rutas_variables": rutas_variables,
            "productos": productos,
        }
