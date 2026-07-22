import os
from sqlalchemy import text
from app.db.session import SessionLocal
from app.models.user import Usuario, UserPermission
from app.models.sesion import SesionActiva
from app.models.solicitud import Solicitud

# Todos los módulos a los que un analista tenía acceso por rol,
# más el nuevo routes.asignar_merc.
# La clave se deriva de la ruta: /routes → "routes", /centro-mando → "centro-mando"
ANALYST_MODULES = [
    # Módulos que el analista ya veía por rol (roles: ['admin','analyst',...])
    "dashboard",
    "centro-mando",
    "routes",
    "clientes-rutas",
    "frecuencias-pdvs-cliente",
    "chat",
    "atencion-cliente",
    "data",
    # Submódulos de rutas
    "routes.asignar_merc",
    "routes.asignar_analista",
    "routes.asignar_supervisor",
]

def main():
    db = SessionLocal()
    try:
        analistas = db.query(Usuario).filter(Usuario.id_rol == 2, Usuario.activo == True).all()
        print(f"Encontrados {len(analistas)} analistas activos.")

        count_updated = 0
        count_created = 0

        for analista in analistas:
            for mod in ANALYST_MODULES:
                perm = db.query(UserPermission).filter(
                    UserPermission.user_id == analista.id,
                    UserPermission.module == mod
                ).first()

                if perm:
                    # Asegurar que tenga todos los permisos
                    changed = False
                    if not perm.can_read:
                        perm.can_read = True
                        changed = True
                    if not perm.can_write:
                        perm.can_write = True
                        changed = True
                    if not perm.can_delete:
                        perm.can_delete = True
                        changed = True
                    if not perm.can_see_all:
                        perm.can_see_all = True
                        changed = True
                    if changed:
                        count_updated += 1
                else:
                    perm = UserPermission(
                        user_id=analista.id,
                        module=mod,
                        can_read=True,
                        can_write=True,
                        can_delete=True,
                        can_see_all=True,
                    )
                    db.add(perm)
                    count_created += 1

        db.commit()
        print(f"✅ Permisos creados: {count_created}, actualizados: {count_updated}")
        print(f"   Módulos asignados a cada analista: {', '.join(ANALYST_MODULES)}")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
