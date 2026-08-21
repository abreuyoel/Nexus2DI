"""Permisos por defecto por rol (usuario_permisos), para que la visibilidad
del sidebar salga de la tabla de permisos y no de arrays de roles hardcodeados
en el frontend. Solo se seedean los roles con restricciones explícitas
solicitadas; el resto de roles (mercaderista, supervisor, atc, vendedor,
auditor, admin) sigue sin filas propias y cae al fallback por rol existente.

'dashboard' y 'chat' son de acceso universal en el sidebar (roles: []) — hay
que concederlos explícitamente en CADA rol seedeado, porque en cuanto un
usuario tiene alguna fila de permisos, ese fallback universal deja de
aplicarle (auth.service.ts: canAccess -> si hasAnyPerms() ignora el array
roles por completo)."""
from typing import Any
from sqlalchemy.orm import Session
from app.models.user import Usuario, UserPermission

ROLE_DEFAULT_PERMISSIONS: dict[str, dict[str, dict[str, bool]]] = {
    "analyst": {
        "dashboard": {"read": True},
        "chat": {"read": True},
        "centro-mando": {"read": True},
        "centro-mando-auditoria": {"read": True},
        "plan-accion": {"read": True},
        # "delete" faltaba acá (21 ago) -- un analista con esta fila ya
        # seedeada quedaba con can_delete=False EXPLICITO, lo cual además
        # bloquea el fallback por rol que de otro modo le habría dado
        # acceso (require_permission: si existe la fila, manda ella sola,
        # no cae al fallback). Confirmado en vivo: analistas SIN esta fila
        # sí podían eliminar puntos de RUTA_PROGRAMACION (via fallback),
        # los que SÍ tenían la fila (seedeada o tocada desde Permisos) no.
        "routes": {"read": True, "write": True, "delete": True},
        "routes.asignar_merc": {"read": True, "write": True},
        "clientes-rutas": {"read": True, "write": True},
        # "frecuencias-pdvs-cliente" pasó a tener acciones propias
        # (crear/editar/eliminar/carga_masiva) en vez de un solo
        # read/write en el padre -- si no se conceden acá, un analista
        # con permisos ya customizados (cualquier fila propia en
        # usuario_permisos) pierde la capacidad de cargar/editar
        # frecuencias aunque antes sí podía.
        "frecuencias-pdvs-cliente": {"read": True},
        "frecuencias-pdvs-cliente.crear": {"read": True},
        "frecuencias-pdvs-cliente.editar": {"read": True},
        "frecuencias-pdvs-cliente.eliminar": {"read": True},
        "frecuencias-pdvs-cliente.carga_masiva": {"read": True},
        "atencion-cliente": {"read": True, "write": True},
        "data": {"read": True},
        "supervisor-encuestadores": {"read": True, "write": True, "delete": True},
        "auditoria-usuarios": {"read": True},
    },
    "auditor_campo": {
        "dashboard": {"read": True},
        "chat": {"read": True},
        "auditor-campo": {"read": True, "write": True},
    },
    "encuestador": {
        "dashboard": {"read": True},
        "chat": {"read": True},
        "encuestador": {"read": True, "write": True},
        "encuestador-configuracion": {"read": True, "write": True},
    },
    "cliente_encuestador": {
        # Sin "dashboard": este rol (IQVIA) entra directo a BI Encuestas
        # (redirectAfterLogin ya apunta ahí) -- el dashboard genérico no le
        # aporta nada y solo confunde en el sidebar.
        # "encuestador" con write: decisión explícita -- IQVIA puede activar
        # jornadas y cargar médicos igual que el rol Encuestador (ver
        # check_rol_encuestador en encuestador.py, que ahora también acepta
        # id_rol=13, no solo 12).
        "chat": {"read": True},
        "cliente-encuestador": {"read": True},
        "encuestador": {"read": True, "write": True},
        "encuestador-configuracion": {"read": True, "write": True},
    },
    "ejecutivo_cuenta": {
        "chat": {"read": True},
        "cliente-encuestador": {"read": True},
        "encuestador": {"read": True, "write": True},
    },
    "client": {
        "dashboard": {"read": True},
        "chat": {"read": True},
        "client-visits": {"read": True},
        "data": {"read": True},
    },
    "coordinador_exclusivo": {
        "dashboard": {"read": True},
        "chat": {"read": True},
        "data": {"read": True},
        "centro-mando": {"read": True},
        "client": {"read": True},
        "client-visits": {"read": True},
    },
    "coordinador_tradex": {
        "dashboard": {"read": True},
        "chat": {"read": True},
        "data": {"read": True},
        "client": {"read": True},
        "client-visits": {"read": True},
    },
    "coordinador_general": {
        "dashboard": {"read": True},
        "chat": {"read": True},
        "data": {"read": True},
        "centro-mando": {"read": True},
    },
    # Supervisor no tenía entrada acá -- todo su acceso (incluido /routes,
    # ver app.routes.ts) venía de arrays de roles hardcodeados en el
    # frontend, sin fila propia en usuario_permisos. Eso funciona bien para
    # LECTURA (roleGuard cae al array si no hay fila explícita) pero
    # 'routes'.write/delete en el BACKEND (require_permission) no tiene
    # fallback para id_rol=6 -- sin esta fila, un supervisor no puede
    # crear/editar/eliminar PDVs de RUTA_PROGRAMACION aunque el admin se lo
    # habilite manualmente después (21 ago, pedido explícito). Solo se
    # agrega 'routes' acá -- no se reseedea todo el resto del acceso de
    # supervisor, que sigue viniendo del fallback existente.
    "supervisor": {
        "routes": {"read": True, "write": True, "delete": True},
    },
}


from sqlalchemy import select, delete

def seed_default_permissions(db: Any, usuario: Usuario, overwrite: bool = False) -> int:
    """Crea filas usuario_permisos según ROLE_DEFAULT_PERMISSIONS para el rol
    del usuario. Si overwrite=True, borra antes las filas existentes de ese
    usuario (usado en el backfill sobre usuarios ya existentes). Devuelve la
    cantidad de filas creadas. No hace nada si el rol no está en el mapa."""
    grants = ROLE_DEFAULT_PERMISSIONS.get(usuario.rol)
    if not grants:
        return 0
    if overwrite:
        db.execute(delete(UserPermission).where(UserPermission.user_id == usuario.id))
        db.flush()
    creados = 0
    for clave, flags in grants.items():
        stmt = select(UserPermission).filter_by(user_id=usuario.id, module=clave)
        existente = db.execute(stmt).scalars().first()
        if existente:
            continue
        db.add(UserPermission(
            user_id=usuario.id, module=clave,
            can_read=flags.get("read", False), can_write=flags.get("write", False),
            can_delete=flags.get("delete", False), can_see_all=flags.get("see_all", False),
        ))
        creados += 1
    return creados


from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

async def async_seed_default_permissions(db: AsyncSession, usuario: Usuario, overwrite: bool = False) -> int:
    grants = ROLE_DEFAULT_PERMISSIONS.get(usuario.rol)
    if not grants:
        return 0
    if overwrite:
        await db.execute(delete(UserPermission).where(UserPermission.user_id == usuario.id))
        await db.flush()
    creados = 0
    for clave, flags in grants.items():
        stmt = select(UserPermission).filter_by(user_id=usuario.id, module=clave)
        result = await db.execute(stmt)
        existente = result.scalars().first()
        if existente:
            continue
        db.add(UserPermission(
            user_id=usuario.id, module=clave,
            can_read=flags.get("read", False), can_write=flags.get("write", False),
            can_delete=flags.get("delete", False), can_see_all=flags.get("see_all", False),
        ))
        creados += 1
    return creados
