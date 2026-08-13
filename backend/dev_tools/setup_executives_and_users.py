import sys
import os

# Ruta del backend: subimos un nivel desde dev_tools/
backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_path)

from app.db.session import SessionLocal
from sqlalchemy import text
from app.core.security import get_password_hash

def run_setup():
    db = SessionLocal()
    try:
        print("--- 1. Creating EJECUTIVOS table ---")
        ddl_table = """
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'EJECUTIVOS')
        BEGIN
            CREATE TABLE EJECUTIVOS (
                id_ejecutivo INT IDENTITY(1,1) PRIMARY KEY,
                nombre_ejecutivo VARCHAR(200) NOT NULL
            );
            print('Table EJECUTIVOS created.');
        END
        ELSE
        BEGIN
            print('Table EJECUTIVOS already exists.');
        END
        """
        db.execute(text(ddl_table))
        db.commit()

        print("\n--- 2. Inserting Ejecutivo de Cuenta Role ---")
        ddl_role = """
        IF NOT EXISTS (SELECT * FROM ROLES WHERE id_rol = 15)
        BEGIN
            SET IDENTITY_INSERT ROLES ON;
            INSERT INTO ROLES (id_rol, rol) VALUES (15, 'Ejecutivo de Cuenta');
            SET IDENTITY_INSERT ROLES OFF;
            print('Role 15 inserted.');
        END
        ELSE
        BEGIN
            print('Role 15 already exists.');
        END
        """
        db.execute(text(ddl_role))
        db.commit()

        print("\n--- 3. Creating Executive profile for Jesus Salazar ---")
        # Check if executive exists
        exec_check = db.execute(text("SELECT id_ejecutivo FROM EJECUTIVOS WHERE nombre_ejecutivo = 'Jesus Salazar'")).fetchone()
        if not exec_check:
            db.execute(text("INSERT INTO EJECUTIVOS (nombre_ejecutivo) VALUES ('Jesus Salazar')"))
            db.commit()
            exec_id = db.execute(text("SELECT id_ejecutivo FROM EJECUTIVOS WHERE nombre_ejecutivo = 'Jesus Salazar'")).fetchone()[0]
            print(f"Created Jesus Salazar executive profile with ID: {exec_id}")
        else:
            exec_id = exec_check[0]
            print(f"Jesus Salazar executive profile already exists with ID: {exec_id}")

        print("\n--- 4. Creating user jsalazar ---")
        user_check = db.execute(text("SELECT id_usuario FROM USUARIOS WHERE username = 'jsalazar'")).fetchone()
        hashed_pwd = get_password_hash("Epran2026*")
        if not user_check:
            db.execute(text("""
                INSERT INTO USUARIOS (username, password_hash, email, id_rol, id_perfil, activo)
                VALUES ('jsalazar', :pwd, 'jsalazar@epran.net', 15, :profile_id, 1)
            """), {"pwd": hashed_pwd, "profile_id": exec_id})
            db.commit()
            jsalazar_id = db.execute(text("SELECT id_usuario FROM USUARIOS WHERE username = 'jsalazar'")).fetchone()[0]
            print(f"Created user jsalazar with ID: {jsalazar_id}")
        else:
            jsalazar_id = user_check[0]
            db.execute(text("""
                UPDATE USUARIOS SET id_rol = 15, id_perfil = :profile_id, activo = 1 WHERE id_usuario = :uid
            """), {"profile_id": exec_id, "uid": jsalazar_id})
            db.commit()
            print(f"Updated user jsalazar with ID: {jsalazar_id}")

        print("\n--- 5. Creating user ymorillo ---")
        user_check_y = db.execute(text("SELECT id_usuario FROM USUARIOS WHERE username = 'ymorillo'")).fetchone()
        if not user_check_y:
            db.execute(text("""
                INSERT INTO USUARIOS (username, password_hash, email, id_rol, id_perfil, activo)
                VALUES ('ymorillo', :pwd, 'ymorillo@epran.net', 3, NULL, 1)
            """), {"pwd": hashed_pwd})
            db.commit()
            ymorillo_id = db.execute(text("SELECT id_usuario FROM USUARIOS WHERE username = 'ymorillo'")).fetchone()[0]
            print(f"Created user ymorillo with ID: {ymorillo_id}")
        else:
            ymorillo_id = user_check_y[0]
            db.execute(text("""
                UPDATE USUARIOS SET id_rol = 3, activo = 1 WHERE id_usuario = :uid
            """), {"uid": ymorillo_id})
            db.commit()
            print(f"Updated user ymorillo with ID: {ymorillo_id}")

        print("\n--- 6. Setting permissions in usuario_permisos ---")
        permissions_to_set = [
            ("chat", 1, 0, 0),
            ("cliente-encuestador", 1, 0, 0),
            ("encuestador", 1, 1, 0)
        ]

        for user_id, uname in [(jsalazar_id, "jsalazar"), (ymorillo_id, "ymorillo")]:
            print(f"Assigning permissions for {uname} (ID {user_id})...")
            for module, read, write, delete in permissions_to_set:
                perm_check = db.execute(text(
                    "SELECT id FROM usuario_permisos WHERE id_usuario = :uid AND module = :mod"
                ), {"uid": user_id, "mod": module}).fetchone()

                if not perm_check:
                    db.execute(text("""
                        INSERT INTO usuario_permisos (id_usuario, module, can_read, can_write, can_delete, can_see_all)
                        VALUES (:uid, :mod, :r, :w, :d, 0)
                    """), {"uid": user_id, "mod": module, "r": read, "w": write, "d": delete})
                    print(f"  Added permission: {module} (R:{read}, W:{write})")
                else:
                    db.execute(text("""
                        UPDATE usuario_permisos SET can_read = :r, can_write = :w, can_delete = :d, can_see_all = 0
                        WHERE id_usuario = :uid AND module = :mod
                    """), {"uid": user_id, "mod": module, "r": read, "w": write, "d": delete})
                    print(f"  Updated permission: {module} (R:{read}, W:{write})")
            db.commit()

        print("\nVerification of user permissions:")
        for user_id, uname in [(jsalazar_id, "jsalazar"), (ymorillo_id, "ymorillo")]:
            res = db.execute(text(
                "SELECT module, can_read, can_write FROM usuario_permisos WHERE id_usuario = :uid"
            ), {"uid": user_id}).fetchall()
            print(f"  {uname} permissions in DB: {res}")

        print("\nSetup completed successfully!")

    except Exception as e:
        print("Error during setup execution:", e)
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run_setup()
