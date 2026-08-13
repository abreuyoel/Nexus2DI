"""
Servicio de Chat del Mercaderista.
Gestiona la bandeja de entrada, mensajes por visita y envío de mensajes.
Usa exclusivamente SQLAlchemy ORM.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import desc, text

from app.modules.merchandisers.entities import Mercaderista
from app.modules.visits.entities import Visita, Foto, NotificacionRechazoFoto
from app.modules.chat.entities import ChatMensaje



class ChatService:
    """Bandeja de chat y mensajería por visita."""

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

    # ── Bandeja de Entrada ───────────────────────────────────────────────────

    def get_inbox(self, current_user) -> List[dict]:
        """Devuelve las conversaciones agrupadas por visita."""
        merc = self._get_mercaderista(current_user)

        # Visitas del mercaderista que tienen mensajes
        visitas = (
            self.db.query(Visita)
            .filter(Visita.mercaderista_id == merc.id)
            .order_by(Visita.fecha.desc())
            .all()
        )

        result = []
        for v in visitas:
            # Contar mensajes
            total = (
                self.db.query(ChatMensaje)
                .filter(ChatMensaje.visita_id == v.id)
                .count()
            )

            # Último mensaje
            ultimo = (
                self.db.query(ChatMensaje)
                .filter(ChatMensaje.visita_id == v.id)
                .order_by(desc(ChatMensaje.created_at))
                .first()
            )

            punto = v.punto
            cliente = v.cliente

            result.append({
                "id_visita": v.id,
                "fecha_visita": str(v.fecha) if v.fecha else None,
                "estado": v.estado,
                "pdv_nombre": punto.nombre if punto else None,
                "cliente_nombre": cliente.nombre if cliente else None,
                "total_msgs": total,
                "ultimo_mensaje": ultimo.mensaje if ultimo else None,
                "ultimo_timestamp": str(ultimo.created_at) if ultimo and ultimo.created_at else None,
            })

        # Filtrar solo las que tienen mensajes
        return [r for r in result if r["total_msgs"] > 0]

    # ── Mensajes de una Visita ───────────────────────────────────────────────

    def get_mensajes(self, visita_id: int) -> List[dict]:
        """Obtiene los mensajes de chat de una visita."""
        mensajes = (
            self.db.query(ChatMensaje)
            .filter(ChatMensaje.visita_id == visita_id)
            .order_by(ChatMensaje.created_at)
            .all()
        )

        return [
            {
                "id_mensaje": m.id,
                "id_visita": m.visita_id,
                "sender_nombre": m.sender_nombre,
                "mensaje": m.mensaje,
                "tipo_mensaje": m.sender_type,
                "fecha_envio": str(m.created_at) if m.created_at else None,
                "foto_adjunta": m.foto_adjunta,
            }
            for m in mensajes
        ]

    # ── Enviar Mensaje ───────────────────────────────────────────────────────

    def enviar_mensaje(
        self,
        current_user,
        visita_id: int,
        mensaje: str,
        sender_nombre: Optional[str] = None,
    ) -> dict:
        """Envía un mensaje a una visita."""
        merc = self._get_mercaderista(current_user)
        now = datetime.utcnow()

        # Verificar que la visita pertenece al mercaderista
        visita = (
            self.db.query(Visita)
            .filter(Visita.id == visita_id, Visita.mercaderista_id == merc.id)
            .first()
        )
        if not visita:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Visita no encontrada")

        msg = ChatMensaje(
            visita_id=visita_id,
            sender_nombre=sender_nombre or merc.nombre,
            mensaje=mensaje,
            sender_type="mercaderista",
            created_at=now,
            leido=False,
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)

        # Notificar por WebSocket
        try:
            from app.services.realtime import notify_event
            notify_event("chat.new_message", {
                "id_mensaje": msg.id,
                "id_visita": visita_id,
                "sender_nombre": msg.sender_nombre,
                "mensaje": mensaje,
                "fecha_envio": str(now),
            })
        except Exception:
            pass

        return {
            "id_mensaje": msg.id,
            "id_visita": visita_id,
            "sender_nombre": msg.sender_nombre,
            "mensaje": mensaje,
            "fecha_envio": str(now),
        }

    # ── Notificaciones (Rechazos, Aprobaciones, Visitas Revisadas) ─────────

    def get_notificaciones(self, current_user) -> dict:
        """
        Devuelve todas las notificaciones pendientes del mercaderista:
        - Rechazos: fotos rechazadas por AI/analista con motivo
        - Aprobaciones: fotos aprobadas
        - Visitas revisadas: visitas marcadas como 'Revisado' por analista
        
        Equivale a fetchRechazos() + fetchEventos() en la APK.
        """
        merc = self._get_mercaderista(current_user)

        # ── Rechazos ──────────────────────────────────────────────────────


        rechazos_raw = (
            self.db.query(NotificacionRechazoFoto, Foto, Visita)
            .join(Foto, NotificacionRechazoFoto.foto_id == Foto.id)
            .join(Visita, Foto.visita_id == Visita.id)
            .filter(Visita.mercaderista_id == merc.id)
            .order_by(NotificacionRechazoFoto.fecha_notificacion.desc())
            .limit(50)
            .all()
        )

        id_to_codigo = {v["id"]: k for k, v in {
            "gestion_antes":      {"label": "Gestión (Antes)",            "id": 1},
            "gestion_despues":    {"label": "Gestión (Después)",          "id": 2},
            "precios":            {"label": "Precios",                    "id": 3},
            "exhibicion_antes":   {"label": "Exhibición Adic. (Antes)",   "id": 4},
            "activacion":         {"label": "Activación",                 "id": 5},
            "desactivacion":      {"label": "Desactivación",              "id": 6},
            "exhibicion_despues": {"label": "Exhibición Adic. (Después)", "id": 7},
            "pop_antes":          {"label": "Material POP (Antes)",       "id": 8},
            "pop_despues":        {"label": "Material POP (Después)",     "id": 10},
        }.items()}

        rechazos = []
        for notif, foto, visita in rechazos_raw:
            punto = visita.punto
            cliente = visita.cliente
            tipo_codigo = id_to_codigo.get(foto.id_tipo_foto, "gestion_antes")
            rechazos.append({
                "id_foto": foto.id,
                "id_visita": visita.id,
                "tipo_foto": tipo_codigo,
                "url": self._foto_url(foto.blob_path, foto.id),
                "motivo_rechazo": notif.motivo,
                "fecha_rechazo": str(notif.fecha_creacion) if notif.fecha_creacion else None,
                "leido": notif.leido or False,
                "punto_nombre": punto.nombre if punto else None,
                "cliente_nombre": cliente.nombre if cliente else None,
            })

        # ── Aprobaciones (fotos pasadas a estado 'aprobado') ──────────────
        aprobaciones_raw = (
            self.db.query(Foto, Visita)
            .join(Visita, Foto.visita_id == Visita.id)
            .filter(
                Visita.mercaderista_id == merc.id,
                Foto.estado.in_(["aprobado", "aprobada"]),
            )
            .order_by(Foto.fecha_registro.desc())
            .limit(30)
            .all()
        )

        aprobaciones = []
        for foto, visita in aprobaciones_raw:
            punto = visita.punto
            tipo_codigo = id_to_codigo.get(foto.id_tipo_foto, "gestion_antes")
            aprobaciones.append({
                "id_foto": foto.id,
                "id_visita": visita.id,
                "tipo_foto": tipo_codigo,
                "url": self._foto_url(foto.blob_path, foto.id),
                "fecha_aprobacion": str(foto.fecha_registro) if foto.fecha_registro else None,
                "leido": False,
                "punto_nombre": punto.nombre if punto else None,
            })

        # ── Visitas Revisadas ─────────────────────────────────────────────
        visitas_revisadas_raw = (
            self.db.query(Visita)
            .filter(
                Visita.mercaderista_id == merc.id,
                Visita.estado == "Revisado",
            )
            .order_by(Visita.fecha_revision.desc())
            .limit(20)
            .all()
        )

        visitas_revisadas = []
        for v in visitas_revisadas_raw:
            punto = v.punto
            cliente = v.cliente
            visitas_revisadas.append({
                "id_visita": v.id,
                "punto_nombre": punto.nombre if punto else None,
                "cliente_nombre": cliente.nombre if cliente else None,
                "fecha_revision": str(v.fecha_revision) if v.fecha_revision else None,
                "leido": False,
            })

        return {
            "rechazos": rechazos,
            "aprobaciones": aprobaciones,
            "visitas_revisadas": visitas_revisadas,
        }

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _foto_url(self, blob_path, foto_id: int):
        """Genera URL para una foto."""
        if not blob_path:
            return None
        if isinstance(blob_path, str) and blob_path.startswith("http"):
            return blob_path
        return f"/api/media/foto/{foto_id}"

    def _az_foto_url(self, blob_path) -> Optional[str]:
        """Convierte blob_path a URL proxy de Azure, si aplica."""
        if not blob_path:
            return None
        from app.services.azure_service import azure_service
        return azure_service.get_proxy_url(blob_path)

    # ── Grupos de Chat (Equipo Operativo / Equipo + Cliente) ───────────────

    def get_mis_grupos(self, current_user) -> List[dict]:
        """Devuelve los grupos de chat a los que pertenece el mercaderista,
        con conteo de no-leídos y preview del último mensaje."""
        from app.services.chat_grupos_membresia import get_grupos_de_usuario

        grupos = get_grupos_de_usuario(self.db, current_user.id)
        if not grupos:
            return []

        ids = [g["id_grupo"] for g in grupos]
        ph = ",".join(str(int(i)) for i in ids)

        unread_rows = self.db.execute(text("""
            SELECT m.id_grupo, COUNT(*)
            FROM CHAT_GRUPO_MENSAJES m
            LEFT JOIN CHAT_GRUPO_LECTURAS l
                   ON l.id_grupo = m.id_grupo AND l.id_usuario = :uid
            WHERE m.id_grupo IN ({ph})
              AND m.id_usuario <> :uid
              AND m.id_mensaje > ISNULL(l.last_read_id_mensaje, 0)
            GROUP BY m.id_grupo
        """.replace("{ph}", ph)), {"uid": current_user.id}).fetchall()
        unread = {int(r[0]): int(r[1]) for r in unread_rows}

        last_rows = self.db.execute(text("""
            SELECT x.id_grupo, x.mensaje, x.fecha_envio
            FROM (
                SELECT m.id_grupo, m.mensaje, m.fecha_envio,
                       ROW_NUMBER() OVER (PARTITION BY m.id_grupo ORDER BY m.id_mensaje DESC) AS rn
                FROM CHAT_GRUPO_MENSAJES m
                WHERE m.id_grupo IN ({ph})
                  AND NOT (
                      m.tipo_mensaje = 'sistema'
                      AND (
                          m.mensaje LIKE N'%Foto Rechazada%'
                          OR m.mensaje LIKE N'%Foto rechazada%'
                          OR m.mensaje LIKE N'%🚫%'
                      )
                  )
            ) x
            WHERE x.rn = 1
        """.replace("{ph}", ph))).fetchall()
        last = {int(r[0]): {"mensaje": r[1], "fecha": str(r[2]) if r[2] else None} for r in last_rows}

        result = []
        for g in grupos:
            result.append({
                "id_grupo": g["id_grupo"],
                "id_cliente": g["id_cliente"],
                "tipo_grupo": g["tipo_grupo"],
                "nombre": g["nombre"],
                "no_leidos": unread.get(g["id_grupo"], 0),
                "ultimo_mensaje": last.get(g["id_grupo"], {}).get("mensaje"),
                "ultimo_mensaje_fecha": last.get(g["id_grupo"], {}).get("fecha"),
            })
        result.sort(key=lambda g: (-g["no_leidos"], g["nombre"] or ""))
        return result

    def _autorizado_grupo(self, current_user, id_grupo: int) -> bool:
        """Verifica que el usuario pertenezca al grupo."""
        from app.services.chat_grupos_membresia import get_grupos_de_usuario
        return any(g["id_grupo"] == id_grupo for g in get_grupos_de_usuario(self.db, current_user.id))

    def _grupo_info(self, id_grupo: int):
        """Obtiene metadata de un grupo."""
        return self.db.execute(text("""
            SELECT id_grupo, id_cliente, tipo_grupo, nombre, activa
            FROM CHAT_GRUPOS WHERE id_grupo = :id
        """), {"id": id_grupo}).fetchone()

    def get_mensajes_grupo(
        self, current_user, id_grupo: int, limit: int = 50, before_id: Optional[int] = None
    ) -> List[dict]:
        """Devuelve los mensajes del chat general de un grupo."""
        from fastapi import HTTPException
        if not self._autorizado_grupo(current_user, id_grupo):
            raise HTTPException(status_code=403, detail="No autorizado")

        cond = " AND m.id_mensaje < :before_id" if before_id else ""
        params = {"limit": limit, "id_grupo": id_grupo}
        if before_id:
            params["before_id"] = before_id

        rows = self.db.execute(text("""
            SELECT TOP (:limit) m.id_mensaje, m.id_grupo, m.id_usuario, m.username,
                                 m.mensaje, m.tipo_mensaje, m.fecha_envio, m.foto_adjunta
            FROM CHAT_GRUPO_MENSAJES m
            WHERE m.id_grupo = :id_grupo""" + cond + """
              AND NOT (
                  m.tipo_mensaje = 'sistema'
                  AND (
                      m.mensaje LIKE N'%Foto Rechazada%'
                      OR m.mensaje LIKE N'%Foto rechazada%'
                      OR m.mensaje LIKE N'%🚫%'
                  )
              )
            ORDER BY m.id_mensaje DESC
        """), params).fetchall()

        mensajes = [{
            "id_mensaje": r[0], "id_grupo": r[1], "id_usuario": r[2], "username": r[3],
            "mensaje": r[4], "tipo_mensaje": r[5], "fecha_envio": str(r[6]) if r[6] else None,
            "foto_adjunta": self._az_foto_url(r[7]), "es_mio": r[2] == current_user.id,
        } for r in rows]

        mensajes.reverse()
        return mensajes

    def enviar_mensaje_grupo(self, current_user, id_grupo: int, mensaje: str) -> dict:
        """Envía un mensaje al chat general del grupo."""
        from fastapi import HTTPException
        if not self._autorizado_grupo(current_user, id_grupo):
            raise HTTPException(status_code=403, detail="No autorizado")

        texto = (mensaje or "").strip()
        if not texto:
            raise HTTPException(status_code=400, detail="Mensaje vacío")

        ahora = datetime.now()
        row = self.db.execute(text("""
            INSERT INTO CHAT_GRUPO_MENSAJES (id_grupo, id_usuario, username, mensaje, tipo_mensaje, fecha_envio)
            OUTPUT INSERTED.id_mensaje
            VALUES (:id_grupo, :uid, :username, :mensaje, 'usuario', :fecha)
        """), {"id_grupo": id_grupo, "uid": current_user.id, "username": current_user.username,
               "mensaje": texto, "fecha": ahora}).fetchone()
        self.db.commit()
        id_mensaje = row[0]

        # WebSocket: notificar nuevo mensaje en grupo
        try:
            from app.services.realtime import notify_event
            notify_event("chat.new_message", {
                "id_grupo": id_grupo,
                "id_usuario": current_user.id,
                "username": current_user.username,
                "id_mensaje": id_mensaje,
            })
        except Exception:
            pass

        return {
            "id_mensaje": id_mensaje, "id_grupo": id_grupo,
            "id_usuario": current_user.id, "username": current_user.username,
            "mensaje": texto, "tipo_mensaje": "usuario",
            "fecha_envio": str(ahora), "foto_adjunta": None, "es_mio": True,
        }

    def get_miembros_grupo(self, current_user, id_grupo: int) -> List[dict]:
        """Devuelve los miembros de un grupo (resolución dinámica)."""
        from fastapi import HTTPException
        from app.services.chat_grupos_membresia import get_miembros_grupo

        if not self._autorizado_grupo(current_user, id_grupo):
            raise HTTPException(status_code=403, detail="No autorizado")
        info = self._grupo_info(id_grupo)
        if not info:
            raise HTTPException(status_code=404, detail="Grupo no encontrado")
        return get_miembros_grupo(self.db, info[1], info[2])

    def get_visitas_activas_grupo(self, current_user, id_grupo: int) -> List[dict]:
        """Devuelve las visitas activas que tienen hilo de chat en este grupo."""
        from fastapi import HTTPException

        if not self._autorizado_grupo(current_user, id_grupo):
            raise HTTPException(status_code=403, detail="No autorizado")
        info = self._grupo_info(id_grupo)
        if not info:
            raise HTTPException(status_code=404, detail="Grupo no encontrado")

        id_cliente = info[1]
        tipo_grupo = info[2]

        rows = self.db.execute(text("""
            SELECT v.id_visita, v.fecha_visita, m.nombre AS mercaderista, p.punto_de_interes,
                   v.estado, x.ultimo_mensaje, x.fecha_ultimo
            FROM (
                SELECT DISTINCT id_visita FROM CHAT_MENSAJES_GRUPO_VISITA
                WHERE id_cliente = :cid AND tipo_grupo = :tipo
            ) gv
            JOIN VISITAS_MERCADERISTA v ON v.id_visita = gv.id_visita
            LEFT JOIN MERCADERISTAS m ON m.id_mercaderista = v.id_mercaderista
            LEFT JOIN PUNTOS_INTERES1 p ON p.identificador = v.identificador_punto_interes
            CROSS APPLY (
                SELECT TOP 1 mensaje AS ultimo_mensaje, fecha_envio AS fecha_ultimo
                FROM CHAT_MENSAJES_GRUPO_VISITA
                WHERE id_visita = v.id_visita AND id_cliente = :cid AND tipo_grupo = :tipo
                ORDER BY fecha_envio DESC
            ) x
            ORDER BY x.fecha_ultimo DESC
        """), {"cid": id_cliente, "tipo": tipo_grupo}).fetchall()

        return [{
            "id_visita": r[0],
            "fecha_visita": str(r[1]) if r[1] else None,
            "mercaderista": r[2],
            "punto": r[3],
            "estado": r[4],
            "ultimo_mensaje": r[5],
            "fecha_ultimo": str(r[6]) if r[6] else None,
        } for r in rows]

    def get_mensajes_grupo_visita(
        self, current_user, id_grupo: int, id_visita: int
    ) -> List[dict]:
        """Devuelve los mensajes del sub-hilo de visita dentro del grupo."""
        from fastapi import HTTPException
        from app.services.chat_grupos_membresia import usuario_es_miembro

        if not self._autorizado_grupo(current_user, id_grupo):
            raise HTTPException(status_code=403, detail="No autorizado")
        info = self._grupo_info(id_grupo)
        if not info:
            raise HTTPException(status_code=404, detail="Grupo no encontrado")

        id_cliente = info[1]
        tipo_grupo = info[2]

        rows = self.db.execute(text("""
            SELECT id_mensaje, id_usuario, username, mensaje, tipo_mensaje, fecha_envio, foto_adjunta
            FROM CHAT_MENSAJES_GRUPO_VISITA
            WHERE id_cliente = :cid AND tipo_grupo = :tipo AND id_visita = :vid
            ORDER BY fecha_envio ASC
        """), {"cid": id_cliente, "tipo": tipo_grupo, "vid": id_visita}).fetchall()

        return [{
            "id_mensaje": r[0], "id_cliente": id_cliente, "tipo_grupo": tipo_grupo,
            "id_visita": id_visita, "id_usuario": r[1], "username": r[2],
            "mensaje": r[3], "tipo_mensaje": r[4],
            "fecha_envio": str(r[5]) if r[5] else None,
            "foto_adjunta": self._az_foto_url(r[6]),
            "es_mio": r[1] == current_user.id,
        } for r in rows]

    def enviar_mensaje_grupo_visita(
        self, current_user, id_grupo: int, id_visita: int, mensaje: str
    ) -> dict:
        """Envía un mensaje al sub-hilo de visita dentro del grupo."""
        from fastapi import HTTPException

        if not self._autorizado_grupo(current_user, id_grupo):
            raise HTTPException(status_code=403, detail="No autorizado")
        info = self._grupo_info(id_grupo)
        if not info:
            raise HTTPException(status_code=404, detail="Grupo no encontrado")

        id_cliente = info[1]
        tipo_grupo = info[2]

        texto = (mensaje or "").strip()
        if not texto:
            raise HTTPException(status_code=400, detail="Mensaje vacío")

        ahora = datetime.now()
        row = self.db.execute(text("""
            INSERT INTO CHAT_MENSAJES_GRUPO_VISITA
                (id_cliente, tipo_grupo, id_visita, id_usuario, username, mensaje, tipo_mensaje, fecha_envio)
            OUTPUT INSERTED.id_mensaje
            VALUES (:cid, :tipo, :vid, :uid, :username, :mensaje, 'usuario', :fecha)
        """), {"cid": id_cliente, "tipo": tipo_grupo, "vid": id_visita,
               "uid": current_user.id, "username": current_user.username,
               "mensaje": texto, "fecha": ahora}).fetchone()
        self.db.commit()
        id_mensaje = row[0]

        # WebSocket: notificar nuevo mensaje en hilo de visita del grupo
        try:
            from app.services.realtime import notify_event
            notify_event("chat.new_message", {
                "id_grupo": id_grupo,
                "id_visita": id_visita,
                "id_usuario": current_user.id,
                "username": current_user.username,
                "id_mensaje": id_mensaje,
            })
        except Exception:
            pass

        return {
            "id_mensaje": id_mensaje, "id_cliente": id_cliente, "tipo_grupo": tipo_grupo,
            "id_visita": id_visita, "id_usuario": current_user.id,
            "username": current_user.username, "mensaje": texto,
            "tipo_mensaje": "usuario", "fecha_envio": str(ahora),
            "foto_adjunta": None, "es_mio": True,
        }

    def marcar_leido_grupo(self, current_user, id_grupo: int) -> dict:
        """Marca como leído el grupo hasta su último mensaje."""
        from fastapi import HTTPException
        if not self._autorizado_grupo(current_user, id_grupo):
            raise HTTPException(status_code=403, detail="No autorizado")

        last = self.db.execute(text("""
            SELECT MAX(id_mensaje) FROM CHAT_GRUPO_MENSAJES WHERE id_grupo = :id
        """), {"id": id_grupo}).scalar()
        last_id = int(last or 0)

        self.db.execute(text("""
            MERGE CHAT_GRUPO_LECTURAS AS t
            USING (SELECT :id_grupo AS id_grupo, :uid AS id_usuario) AS s
               ON t.id_grupo = s.id_grupo AND t.id_usuario = s.id_usuario
            WHEN MATCHED THEN
                UPDATE SET last_read_id_mensaje = :last_id, fecha_actualizacion = GETDATE()
            WHEN NOT MATCHED THEN
                INSERT (id_grupo, id_usuario, last_read_id_mensaje, fecha_actualizacion)
                VALUES (:id_grupo, :uid, :last_id, GETDATE());
        """), {"id_grupo": id_grupo, "uid": current_user.id, "last_id": last_id})
        self.db.commit()

        # WebSocket: notificar lectura del grupo
        try:
            from app.services.realtime import notify_grupo_lectura
            notify_grupo_lectura(
                id_grupo=id_grupo,
                id_usuario=current_user.id,
                username=current_user.username,
            )
        except Exception:
            pass

        return {"last_read_id_mensaje": last_id}
