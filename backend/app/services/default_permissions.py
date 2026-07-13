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
from sqlalchemy.orm import Session
from app.models.user import Usuario, UserPermission

ROLE_DEFAULT_PERMISSIONS: dict[str, dict[str, dict[str, bool]]] = {
    "analyst": {
        "dashboard": {"read": True},
        "chat": {"read": True},
        "centro-mando": {"read": True},
        "routes": {"read": True, "write": True},
        "routes.asignar_merc": {"read": True, "write": True},
        "clientes-rutas": {"read": True, "write": True},
        "frecuencias-pdvs-cliente": {"read": True, "write": True},
        "atencion-cliente": {"read": True, "write": True},
        "data": {"read": True},
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
    },
    "cliente_encuestador": {
        "dashboard": {"read": True},
        "chat": {"read": True},
        "cliente-encuestador": {"read": True},
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
}


def seed_default_permissions(db: Session, usuario: Usuario, overwrite: bool = False) -> int:
    """Crea filas usuario_permisos según ROLE_DEFAULT_PERMISSIONS para el rol
    del usuario. Si overwrite=True, borra antes las filas existentes de ese
    usuario (usado en el backfill sobre usuarios ya existentes). Devuelve la
    cantidad de filas creadas. No hace nada si el rol no está en el mapa."""
    grants = ROLE_DEFAULT_PERMISSIONS.get(usuario.rol)
    if not grants:
        return 0
    if overwrite:
        db.query(UserPermission).filter(UserPermission.user_id == usuario.id).delete()
        db.flush()
    creados = 0
    for clave, flags in grants.items():
        existente = db.query(UserPermission).filter_by(user_id=usuario.id, module=clave).first()
        if existente:
            continue
        db.add(UserPermission(
            user_id=usuario.id, module=clave,
            can_read=flags.get("read", False), can_write=flags.get("write", False),
            can_delete=flags.get("delete", False), can_see_all=flags.get("see_all", False),
        ))
        creados += 1
    return creados
