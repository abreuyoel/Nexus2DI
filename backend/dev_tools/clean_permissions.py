import os
from sqlalchemy import text
from app.db.session import SessionLocal
from app.models.user import Usuario, UserPermission
from app.models.sesion import SesionActiva
from app.models.solicitud import Solicitud

def main():
    db = SessionLocal()
    try:
        # Get all analysts
        analistas = db.query(Usuario).filter(Usuario.id_rol == 2).all()
        print(f"Encontrados {len(analistas)} analistas.")
        
        analyst_ids = [a.id for a in analistas]
        
        if analyst_ids:
            # Delete all explicit permissions for analysts
            # Since we just deployed 'inherited permissions', analysts will fall back to their role defaults
            deleted = db.query(UserPermission).filter(UserPermission.user_id.in_(analyst_ids)).delete(synchronize_session=False)
            db.commit()
            print(f"✅ Se borraron {deleted} registros de permisos explícitos para analistas.")
            print("Ahora todos los analistas heredarán los permisos por defecto de su rol.")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
