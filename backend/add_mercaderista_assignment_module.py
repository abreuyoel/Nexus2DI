import os
from sqlalchemy import text
from app.db.session import SessionLocal
from app.models.user import Usuario, UserPermission
from app.models.sesion import SesionActiva
from app.models.solicitud import Solicitud

def main():
    db = SessionLocal()
    try:
        # 1. Check for parent module 'rutas'
        rutas_mod = db.execute(text("SELECT id_modulo FROM MODULOS WHERE clave = 'rutas'")).fetchone()
        id_padre = rutas_mod[0] if rutas_mod else None

        # 2. Insert submodules if they don't exist
        submodules = [
            {'clave': 'routes.asignar_merc', 'nombre': 'Asignación Mercaderistas', 'icono': 'people'},
            {'clave': 'routes.asignar_analista', 'nombre': 'Asignación Analistas', 'icono': 'analytics'},
            {'clave': 'routes.asignar_supervisor', 'nombre': 'Asignación Supervisores', 'icono': 'supervisor_account'}
        ]

        for sub in submodules:
            submod = db.execute(text("SELECT id_modulo FROM MODULOS WHERE clave = :clave"), {"clave": sub['clave']}).fetchone()
            if not submod:
                print(f"Creando submódulo '{sub['clave']}'...")
                # Get max order
                if id_padre:
                    max_orden = db.execute(text("SELECT ISNULL(MAX(orden), 0) FROM MODULOS WHERE id_padre = :padre"), {"padre": id_padre}).scalar()
                else:
                    max_orden = db.execute(text("SELECT ISNULL(MAX(orden), 0) FROM MODULOS WHERE id_padre IS NULL")).scalar()
                
                db.execute(text("""
                    INSERT INTO MODULOS (clave, nombre, id_padre, tipo, ruta, icono, orden, activo)
                    VALUES (:clave, :nombre, :padre, 'submodulo', '/routes', :icono, :orden, 1)
                """), {
                    "clave": sub['clave'],
                    "nombre": sub['nombre'],
                    "padre": id_padre,
                    "icono": sub['icono'],
                    "orden": (max_orden or 0) + 1
                })
                db.commit()
                print(f"✅ Submódulo '{sub['clave']}' creado.")
            else:
                print(f"✅ Submódulo '{sub['clave']}' ya existe.")

        # 3. Grant full permissions to analysts (rol=2) for 'routes.asignar_merc'
        print("Asignando permisos a analistas (rol=2) para 'routes.asignar_merc'...")
        analistas = db.query(Usuario).filter(Usuario.id_rol == 2, Usuario.activo == True).all()
        
        count = 0
        for analista in analistas:
            perm = db.query(UserPermission).filter(
                UserPermission.user_id == analista.id,
                UserPermission.module == 'routes.asignar_merc'
            ).first()
            
            if not perm:
                perm = UserPermission(
                    user_id=analista.id,
                    module='routes.asignar_merc',
                    can_read=True,
                    can_write=True,
                    can_delete=True,
                    can_see_all=True
                )
                db.add(perm)
                count += 1
            else:
                perm.can_read = True
                perm.can_write = True
                perm.can_delete = True
                perm.can_see_all = True
                count += 1
                
        db.commit()
        print(f"✅ Permisos actualizados/insertados para {count} analistas.")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
