"""Aplica ROLE_DEFAULT_PERMISSIONS a todos los usuarios EXISTENTES de los
roles restringidos, para que su sidebar salga de usuario_permisos en vez
del fallback por rol. Sobreescribe (borra + recrea) las filas de esos
usuarios para dejarlas exactamente iguales al mapa vigente."""
import app.main  # noqa: F401 (registra todos los modelos/relaciones antes de consultar)
from app.db.session import SessionLocal
from app.models.user import Usuario
from app.services.default_permissions import seed_default_permissions, ROLE_DEFAULT_PERMISSIONS

if __name__ == "__main__":
    db = SessionLocal()
    total_usuarios = 0
    total_filas = 0
    for usuario in db.query(Usuario).filter(Usuario.activo == True).all():
        if usuario.rol not in ROLE_DEFAULT_PERMISSIONS:
            continue
        n = seed_default_permissions(db, usuario, overwrite=True)
        total_usuarios += 1
        total_filas += n
        print(f"  usuario {usuario.id} ({usuario.username}, rol={usuario.rol}): {n} permisos")
    db.commit()
    print(f"Listo: {total_usuarios} usuarios actualizados, {total_filas} filas de permisos creadas.")
    db.close()
