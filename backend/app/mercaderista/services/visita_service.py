"""
Servicio de Visitas del Mercaderista.
Gestiona el ciclo de vida completo de una visita: inicio, fotos, balances,
finalización. Usa exclusivamente SQLAlchemy ORM.
"""

import os
import uuid
from datetime import date, datetime
from typing import Optional, List, BinaryIO

from sqlalchemy.orm import Session
from sqlalchemy import and_, cast, Date

from app.models.mercaderista import Mercaderista
from app.models.visita import Visita
from app.models.foto import Foto, NotificacionRechazoFoto
from app.models.balance import Balance
from app.models.producto import Categoria, Producto
from app.models.cliente import Cliente, CategoriaCliente
from app.models.punto import PuntoInteres

FOTO_TIPOS = {
    "gestion_antes":        {"label": "Gestión (Antes)",            "solo_camara": False, "id": 1},
    "gestion_despues":      {"label": "Gestión (Después)",          "solo_camara": False, "id": 2},
    "precios":              {"label": "Precios",                    "solo_camara": False, "id": 3},
    "exhibicion_antes":     {"label": "Exhibición Adic. (Antes)",   "solo_camara": False, "id": 4},
    "exhibiciones_antes":   {"label": "Exhibición Adic. (Antes)",   "solo_camara": False, "id": 4},
    "activacion":           {"label": "Activación",                 "solo_camara": True,  "id": 5},
    "desactivacion":        {"label": "Desactivación",              "solo_camara": True,  "id": 6},
    "exhibicion_despues":   {"label": "Exhibición Adic. (Después)", "solo_camara": False, "id": 7},
    "exhibiciones_despues": {"label": "Exhibición Adic. (Después)", "solo_camara": False, "id": 7},
    "pop_antes":            {"label": "Material POP (Antes)",       "solo_camara": False, "id": 8},
    "material_pop_antes":   {"label": "Material POP (Antes)",       "solo_camara": False, "id": 8},
    "pop_despues":          {"label": "Material POP (Después)",     "solo_camara": False, "id": 10},
    "material_pop_despues": {"label": "Material POP (Después)",     "solo_camara": False, "id": 10},
}

FOTOS_DIR = "app/static/fotos_mercaderista"


DAY_MAP_ES = {
    0: "Lunes", 1: "Martes", 2: "Miércoles",
    3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo",
}


class VisitaService:
    """CRUD y operaciones del ciclo de vida de una visita."""

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

    # ── Iniciar Visita ───────────────────────────────────────────────────────

    def iniciar_visita(
        self, current_user, id_punto: str, id_cliente: int
    ) -> dict:
        """Crea una nueva visita o devuelve una existente del día."""
        merc = self._get_mercaderista(current_user)
        hoy = date.today()

        # Verificar si ya existe visita hoy para ese PDV+cliente
        existente = (
            self.db.query(Visita)
            .filter(
                Visita.mercaderista_id == merc.id,
                Visita.punto_id == id_punto,
                Visita.id_cliente == id_cliente,
                Visita.fecha == hoy,
            )
            .first()
        )

        if existente:
            return {"id_visita": existente.id, "nueva": False}

        # Crear nueva visita
        visita = Visita(
            mercaderista_id=merc.id,
            punto_id=id_punto,
            id_cliente=id_cliente,
            fecha=hoy,
            estado="Pendiente",
            estado_data="Sin Data",
        )
        self.db.add(visita)
        self.db.commit()
        self.db.refresh(visita)
        return {"id_visita": visita.id, "nueva": True}

    # ── Historial de Visitas ─────────────────────────────────────────────────

    def get_mis_visitas(
        self,
        current_user,
        fecha_inicio: Optional[str] = None,
        fecha_fin: Optional[str] = None,
    ) -> List[dict]:
        """Devuelve el historial de visitas del mercaderista."""
        merc = self._get_mercaderista(current_user)

        fi = fecha_inicio or str(date.today())
        ff = fecha_fin or str(date.today())

        visitas = (
            self.db.query(Visita)
            .filter(
                Visita.mercaderista_id == merc.id,
                Visita.fecha >= fi,
                Visita.fecha <= ff,
            )
            .order_by(Visita.fecha.desc())
            .all()
        )

        # Optimización N+1: Obtener conteos agrupados por visita_id en una sola consulta
        visita_ids = [v.id for v in visitas]
        
        fotos_counts = {}
        balances_counts = {}
        if visita_ids:
            from sqlalchemy import func
            res_fotos = (
                self.db.query(Foto.visita_id, func.count(Foto.id))
                .filter(Foto.visita_id.in_(visita_ids))
                .group_by(Foto.visita_id)
                .all()
            )
            fotos_counts = {r[0]: r[1] for r in res_fotos if r[0] is not None}

            res_balances = (
                self.db.query(Balance.visita_id, func.count(Balance.id))
                .filter(Balance.visita_id.in_(visita_ids))
                .group_by(Balance.visita_id)
                .all()
            )
            balances_counts = {r[0]: r[1] for r in res_balances if r[0] is not None}

        result = []
        for v in visitas:
            punto = v.punto
            cliente = v.cliente

            fotos_count = fotos_counts.get(v.id, 0)
            balances_count = balances_counts.get(v.id, 0)

            result.append({
                "id_visita": v.id,
                "fecha": str(v.fecha) if v.fecha else None,
                "fecha_visita": str(v.fecha) if v.fecha else None,
                "estado": v.estado,
                "estado_data": v.estado_data,
                "observaciones": getattr(v, "observaciones", None),
                "identificador_punto": v.punto_id,
                "identificador_punto_interes": v.punto_id,
                "pdv_nombre": punto.nombre if punto else None,
                "cadena": getattr(punto, "cadena", None) if punto else None,
                "region": getattr(punto, "jerarquia_n2_2", None) if punto else None,
                "cliente_nombre": cliente.nombre if cliente else None,
                "id_cliente": v.id_cliente,
                "fotos_count": fotos_count,
                "total_fotos": fotos_count,
                "balances_count": balances_count,
                "total_balances": balances_count,
                "fotos_rechazadas": 0,
                "fotos_aprobadas": 0,
            })

        return result

    # ── Fotos ────────────────────────────────────────────────────────────────

    def get_fotos_visita(self, visita_id: int) -> dict:
        """Devuelve las fotos de una visita agrupadas por tipo."""
        fotos = (
            self.db.query(Foto)
            .filter(Foto.visita_id == visita_id)
            .order_by(Foto.fecha_registro.desc())
            .all()
        )

        por_codigo: dict = {}
        # Mapa inverso: id_tipo_foto → codigo (priorizando claves estándar)
        id_to_codigo = {}
        for k, v in FOTO_TIPOS.items():
            if k in ["exhibicion_antes", "exhibicion_despues", "pop_antes", "pop_despues", "fachada", "firma", "gestion_antes", "gestion_despues", "desactivacion"]:
                id_to_codigo[v["id"]] = k
            elif v["id"] not in id_to_codigo:
                id_to_codigo[v["id"]] = k

        for f in fotos:
            codigo = id_to_codigo.get(f.id_tipo_foto, "gestion_antes")
            if codigo not in por_codigo:
                por_codigo[codigo] = []
            por_codigo[codigo].append({
                "id_foto": f.id,
                "estado": f.estado,
                "fecha": str(f.fecha_registro) if f.fecha_registro else None,
                "url": self._foto_url(f.blob_path, f.id),
            })

        tipos_info = [
            {
                "codigo": k,
                "label": v["label"],
                "solo_camara": v["solo_camara"],
                "fotos": por_codigo.get(k, []),
            }
            for k, v in FOTO_TIPOS.items()
        ]

        return {"visita_id": visita_id, "tipos": tipos_info}

    def upload_foto(
        self,
        current_user,
        visita_id: int,
        tipo_foto: str,
        file_bytes: bytes,
        filename: str,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
    ) -> dict:
        """Sube una foto para una visita."""
        if tipo_foto not in FOTO_TIPOS:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail=f"Tipo de foto inválido: {tipo_foto}")

        # Validar extensión
        ext = (filename or "foto.jpg").rsplit(".", 1)[-1].lower()
        if ext not in ("jpg", "jpeg", "png", "webp"):
            ext = "jpg"

        blob_path = None

        # Intentar usar Azure Blob Storage
        try:
            from app.services.azure_service import azure_service
            blob_name = f"mercaderista/{visita_id}/{uuid.uuid4()}.{ext}"
            blob_path = azure_service.upload_bytes(file_bytes, blob_name)
        except Exception:
            pass

        # Fallback: guardar localmente
        if not blob_path:
            os.makedirs(FOTOS_DIR, exist_ok=True)
            local_name = f"{visita_id}_{uuid.uuid4().hex[:12]}.{ext}"
            local_path = os.path.join(FOTOS_DIR, local_name)
            with open(local_path, "wb") as f:
                f.write(file_bytes)
            blob_path = f"/static/fotos_mercaderista/{local_name}"

        foto = Foto(
            visita_id=visita_id,
            id_tipo_foto=FOTO_TIPOS[tipo_foto]["id"],
            blob_path=blob_path,
            fecha_registro=datetime.utcnow(),
            estado="pendiente",
            latitud=lat,
            longitud=lon,
        )
        self.db.add(foto)
        self.db.commit()
        self.db.refresh(foto)

        return {
            "id_foto": foto.id,
            "url": self._foto_url(foto.blob_path, foto.id),
            "tipo_foto": tipo_foto,
            "estado": foto.estado,
        }

    # ── Balances ─────────────────────────────────────────────────────────────

    def save_balances(
        self,
        current_user,
        visita_id: int,
        id_cliente: Optional[int],
        id_pdv: Optional[str],
        productos: List[dict],
    ) -> dict:
        """Guarda los balances de productos de una visita."""
        merc = self._get_mercaderista(current_user)
        now = datetime.utcnow()

        # Validar que la visita pertenece al mercaderista
        visita = (
            self.db.query(Visita)
            .filter(Visita.id == visita_id, Visita.mercaderista_id == merc.id)
            .first()
        )
        if not visita:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Visita no encontrada")

        for p in productos:
            fefo_date = None
            if p.get("fifo"):
                try:
                    fefo_date = datetime.strptime(p.get("fifo"), "%Y-%m-%d").date()
                except Exception:
                    pass

            balance = Balance(
                id_cliente=id_cliente or merc.id,
                fecha_balance=now,
                identificador_pdv=id_pdv or "",
                mercaderista=merc.nombre,
                producto=p.get("sku", ""),
                categoria=p.get("categoria", ""),
                fabricante=p.get("fabricante", ""),
                inv_inicial=p.get("inv_inicial"),
                inv_final=p.get("inv_final"),
                inv_deposito=p.get("inv_deposito"),
                caras=p.get("caras"),
                precio_bs=p.get("precio_bs") or 0,
                precio_ds=p.get("precio_ds") or 0,
                visita_id=visita_id,
                fecha_inicio_modificacion=now,
                fecha_modificacion=now,
                FEFO=fefo_date,
                estado_producto=p.get("estado_producto", "normal"),
                no_existe=p.get("no_existe", False),
            )
            self.db.add(balance)

        # Actualizar estado_data de la visita
        visita.estado_data = "Cargado"

        self.db.commit()

        return {"success": True, "productos_guardados": len(productos)}

    # ── Finalizar Visita ─────────────────────────────────────────────────────

    def finalizar_visita(self, current_user, id_visita: int) -> dict:
        """Cierra el ciclo de vida de una visita."""
        merc = self._get_mercaderista(current_user)

        visita = (
            self.db.query(Visita)
            .filter(Visita.id == id_visita, Visita.mercaderista_id == merc.id)
            .first()
        )
        if not visita:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Visita no encontrada")

        visita.estado = "Finalizada"
        self.db.commit()

        # Notificar por WebSocket
        try:
            from app.services.realtime import notify_event
            notify_event("visit.finished", {"id_visita": id_visita})
        except Exception:
            pass

        return {"success": True, "id_visita": id_visita}

    # ── Productos para Balance ───────────────────────────────────────────────

    def get_productos_balance(self, id_cliente: Optional[int] = None) -> List[dict]:
        """
        Devuelve los productos disponibles para el formulario de balance.
        Filtra por las categorías asignadas al cliente si se especifica.
        """
        if id_cliente:
            # Obtener categorías del cliente (CATEGORIAS_CLIENTES + fallback a CLIENTES.id_categoria)
            cats_cliente = [
                cc.id_categoria
                for cc in self.db.query(CategoriaCliente)
                .filter(CategoriaCliente.id_cliente == id_cliente)
                .all()
            ]

            if not cats_cliente:
                cliente = self.db.query(Cliente).filter(Cliente.id == id_cliente).first()
                if cliente and cliente.id_categoria:
                    cats_cliente = [cliente.id_categoria]

            if cats_cliente:
                productos = (
                    self.db.query(Producto)
                    .filter(Producto.id_categoria.in_(cats_cliente))
                    .all()
                )
            else:
                return []
        else:
            productos = self.db.query(Producto).all()

        result = []
        for p in productos:
            cat = p.subcategoria.categoria if p.subcategoria else None
            result.append({
                "id": p.id,
                "sku": p.sku,
                "nombre": p.nombre,
                "fabricante": p.fabricante,
                "categoria": cat.nombre if cat else None,
                "id_categoria": p.id_categoria,
            })

        return result

    # ── Catálogo Completo de Productos ──────────────────────────────────────

    def get_productos_catalogo(self, id_cliente: Optional[int] = None) -> dict:
        """
        Devuelve el catálogo completo de productos agrupados por categoría.
        Si se especifica id_cliente, filtra solo categorías de ese cliente.
        Este endpoint reemplaza /api/mobile/productos de la APK.
        """
        if id_cliente:
            cats_cliente = [
                cc.id_categoria
                for cc in self.db.query(CategoriaCliente)
                .filter(CategoriaCliente.id_cliente == id_cliente)
                .all()
            ]

            if not cats_cliente:
                cliente = self.db.query(Cliente).filter(Cliente.id == id_cliente).first()
                if cliente and cliente.id_categoria:
                    cats_cliente = [cliente.id_categoria]

            if cats_cliente:
                categorias = (
                    self.db.query(Categoria)
                    .filter(Categoria.id_categoria.in_(cats_cliente))
                    .all()
                )
            else:
                return {"categorias": [], "total_productos": 0}
        else:
            categorias = self.db.query(Categoria).all()

        result_categorias = []
        total_productos = 0

        for cat in categorias:
            productos = (
                self.db.query(Producto)
                .filter(Producto.id_categoria == cat.id_categoria)
                .all()
            )
            if not productos:
                continue

            items = []
            for p in productos:
                items.append({
                    "id_producto": p.id_producto,
                    "sku": p.cod_prod or p.producto_gu or "",
                    "nombre": p.descripcion_bi or p.producto_gu or "",
                    "fabricante": getattr(p, "fabricante", None),
                    "categoria": cat.nombre,
                    "id_categoria": cat.id_categoria,
                    "categoria_nombre": cat.nombre,
                })
                total_productos += 1

            result_categorias.append({
                "id_categoria": cat.id_categoria,
                "nombre": cat.nombre,
                "productos": items,
            })

        return {
            "categorias": result_categorias,
            "total_productos": total_productos,
        }

    # ── Detalle Completo de Visita ──────────────────────────────────────────

    def get_visita_detalle(self, current_user, visita_id: int) -> dict:
        """
        Devuelve el detalle completo de una visita: metadata, fotos con
        estado de revisión AI (motivo de rechazo si aplica), y balances.
        Equivale a getDataVisita() en la APK (/api/mobile/mis-visitas/{id}/data).
        """
        merc = self._get_mercaderista(current_user)

        visita = (
            self.db.query(Visita)
            .filter(Visita.id == visita_id, Visita.mercaderista_id == merc.id)
            .first()
        )
        if not visita:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Visita no encontrada")

        punto = visita.punto
        cliente = visita.cliente

        # Fotos con estado de revisión
        fotos = (
            self.db.query(Foto)
            .filter(Foto.visita_id == visita_id)
            .order_by(Foto.fecha_registro.desc())
            .all()
        )

        id_to_codigo = {v["id"]: k for k, v in FOTO_TIPOS.items()}
        fotos_result = []
        for f in fotos:
            tipo_codigo = id_to_codigo.get(f.id_tipo_foto, "gestion_antes")
            tipo_label = FOTO_TIPOS.get(tipo_codigo, {}).get("label", tipo_codigo)

            # Obtener motivo de rechazo si existe
            motivo_rechazo = None
            if f.estado and f.estado.lower() in ("rechazado", "rechazada"):
                notif = (
                    self.db.query(NotificacionRechazoFoto)
                    .filter(NotificacionRechazoFoto.id_foto == f.id)
                    .order_by(NotificacionRechazoFoto.fecha_creacion.desc())
                    .first()
                )
                if notif:
                    motivo_rechazo = notif.motivo

            fotos_result.append({
                "id_foto": f.id,
                "estado": f.estado,
                "fecha": str(f.fecha_registro) if f.fecha_registro else None,
                "url": self._foto_url(f.blob_path, f.id),
                "tipo_foto": tipo_codigo,
                "categoria": tipo_label,
                "motivo_rechazo": motivo_rechazo,
                "latitud": f.latitud,
                "longitud": f.longitud,
            })

        # Balances
        balances = (
            self.db.query(Balance)
            .filter(Balance.visita_id == visita_id)
            .all()
        )
        balances_result = []
        for b in balances:
            balances_result.append({
                "id_balance": b.id,
                "producto": b.producto,
                "categoria": b.categoria,
                "fabricante": b.fabricante,
                "inv_inicial": b.inv_inicial,
                "inv_final": b.inv_final,
                "inv_deposito": b.inv_deposito,
                "caras": b.caras,
                "precio_bs": b.precio_bs,
                "precio_ds": b.precio_ds,
                "fefo": str(b.FEFO) if b.FEFO else None,
                "estado_producto": b.estado_producto or "normal",
                "no_existe": b.no_existe or False,
            })

        # Check if PDV is activated today
        from app.models.ruta import RutaActivada, RutaProgramacion
        from app.models.mercaderista import MercaderistaRuta
        hoy = date.today()
        punto_activado = False
        if punto:
            activacion = (
                self.db.query(RutaActivada)
                .filter(
                    RutaActivada.mercaderista_id == merc.id,
                    RutaActivada.identificador_punto_interes == punto.id,
                    cast(RutaActivada.fecha_hora_activacion, Date) == hoy,
                )
                .first()
            )
            punto_activado = activacion is not None

        # Check if es_ultimo_cliente
        es_ultimo_cliente = False
        if punto:
            dia_numero = hoy.weekday()
            # Obtener las rutas asociadas al mercaderista
            mis_rutas_ids = [
                mr.ruta_id
                for mr in self.db.query(MercaderistaRuta.ruta_id)
                .filter(MercaderistaRuta.mercaderista_id == merc.id)
                .all()
            ]
            if mis_rutas_ids:
                programaciones = (
                    self.db.query(RutaProgramacion)
                    .filter(
                        RutaProgramacion.punto_id == punto.id,
                        RutaProgramacion.ruta_id.in_(mis_rutas_ids),
                        RutaProgramacion.dia == DAY_MAP_ES[dia_numero],
                        RutaProgramacion.activo == True,
                    )
                    .all()
                )
                if programaciones:
                    clientes_pendientes = []
                    for prog in programaciones:
                        visita_hoy = (
                            self.db.query(Visita)
                            .filter(
                                Visita.mercaderista_id == merc.id,
                                Visita.punto_id == punto.id,
                                Visita.id_cliente == prog.id_cliente,
                                Visita.fecha == hoy,
                            )
                            .first()
                        )
                        if not visita_hoy:
                            clientes_pendientes.append(prog.id_cliente)
                    if len(clientes_pendientes) == 0:
                        es_ultimo_cliente = True
                    elif len(clientes_pendientes) == 1 and clientes_pendientes[0] == visita.id_cliente:
                        es_ultimo_cliente = True

        return {
            "id_visita": visita.id,
            "fecha": str(visita.fecha) if visita.fecha else None,
            "estado": visita.estado,
            "estado_data": visita.estado_data,
            "punto_nombre": punto.nombre if punto else None,
            "cadena": getattr(punto, "cadena", None) if punto else None,
            "direccion": getattr(punto, "direccion", None) if punto else None,
            "cliente_nombre": cliente.nombre if cliente else None,
            "revisada_por": visita.revisada_por,
            "fecha_revision": str(visita.fecha_revision) if visita.fecha_revision else None,
            "fotos": fotos_result,
            "balances": balances_result,
            "punto": {"id": punto.id, "nombre": punto.nombre} if punto else None,
            "punto_activado": punto_activado,
            "es_ultimo_cliente": es_ultimo_cliente,
        }

    # ── Helpers ──────────────────────────────────────────────────────────────

    def delete_foto(self, current_user, foto_id: int) -> None:
        """
        Elimina una foto individual. Solo el mercaderista dueño de la visita
        puede eliminar sus propias fotos.
        """
        from fastapi import HTTPException
        from app.services.azure_service import azure_service

        merc = self._get_mercaderista(current_user)

        foto = self.db.query(Foto).filter(Foto.id == foto_id).first()
        if not foto:
            raise HTTPException(status_code=404, detail="Foto no encontrada")

        # Verificar que la foto pertenece a una visita del mercaderista
        if not foto.visita_id:
            raise HTTPException(status_code=403, detail="La foto no está asociada a una visita")

        visita = self.db.query(Visita).filter(
            Visita.id == foto.visita_id,
            Visita.mercaderista_id == merc.id,
        ).first()
        if not visita:
            raise HTTPException(status_code=403, detail="No tenés permiso para eliminar esta foto")

        # Eliminar blob de Azure si existe
        if foto.blob_path:
            try:
                azure_service.delete_blob(foto.blob_path)
            except Exception:
                pass  # Si falla el delete del blob, seguimos adelante

        # Eliminar notificaciones asociadas
        self.db.query(NotificacionRechazoFoto).filter(
            NotificacionRechazoFoto.id_foto == foto_id
        ).delete()

        # Eliminar la foto
        self.db.delete(foto)
        self.db.commit()

    def _foto_url(self, blob_path: Optional[str], foto_id: int) -> Optional[str]:
        """Genera URL para una foto. Incluye token JWT para que <img> tags
        puedan autenticarse sin enviar header Authorization."""
        if not blob_path:
            return None
        if blob_path.startswith("http"):
            return blob_path
        import urllib.parse
        from app.core.security import create_media_token
        token = create_media_token()
        return (
            f"/api/media/foto?path={urllib.parse.quote(blob_path, safe='')}"
            f"&token={urllib.parse.quote(token, safe='')}"
        )

    def registrar_auditoria_tiempo(
        self, current_user, payload
    ) -> dict:
        from app.models.auditoria_tiempo import AuditoriaTiempo
        merc = self._get_mercaderista(current_user)
        audit = AuditoriaTiempo(
            id_visita=payload.id_visita,
            identificador_punto_interes=payload.identificador_punto_interes,
            id_mercaderista=merc.id,
            evento=payload.evento,
            detalle=payload.detalle,
            tiempo_restante_segundos=payload.tiempo_restante_segundos,
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(audit)
        return {"success": True, "id_auditoria_tiempo": audit.id}

    def reabrir_visita(self, current_user, id_visita: int) -> dict:
        """Reabre una visita que estaba Finalizada, cambiándola a Pendiente.
        También reactiva la ruta asociada si ya estaba finalizada hoy."""
        from app.models.ruta import RutaProgramacion, RutaActivada
        from datetime import date
        from sqlalchemy import cast, Date
        
        merc = self._get_mercaderista(current_user)
        visita = (
            self.db.query(Visita)
            .filter(Visita.id == id_visita, Visita.mercaderista_id == merc.id)
            .first()
        )
        if not visita:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Visita no encontrada")
            
        if visita.estado != "Finalizada":
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="La visita no está finalizada")
            
        # Reabrir
        visita.estado = "Pendiente"
        
        # Encontrar la programación de hoy para reactivar la ruta si es necesario
        hoy = date.today()
        dia_numero = hoy.weekday()
        dia_semana_hoy = DAY_MAP_ES[dia_numero]

        prog = (
            self.db.query(RutaProgramacion)
            .filter(
                RutaProgramacion.punto_id == visita.punto_id,
                RutaProgramacion.id_cliente == visita.id_cliente,
                RutaProgramacion.dia == dia_semana_hoy,
                RutaProgramacion.activo == True
            )
            .first()
        )

        if prog:
            activacion = (
                self.db.query(RutaActivada)
                .filter(
                    RutaActivada.mercaderista_id == merc.id,
                    RutaActivada.ruta_id == prog.ruta_id,
                    cast(RutaActivada.fecha_hora_activacion, Date) == hoy,
                )
                .first()
            )
            if activacion and activacion.estado == "Finalizado":
                activacion.estado = "activo"
                
        self.db.commit()
        return {"success": True, "mensaje": "Visita reabierta con éxito"}
