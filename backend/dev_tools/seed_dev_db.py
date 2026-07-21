# backend/dev_tools/seed_dev_db.py
# Script de inicialización (seed) de roles y usuario administrador en desarrollo local.

import sys
import os

# Asegurar que el directorio raíz de backend esté en el PYTHONPATH
backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

# Configurar UTF8 para evitar errores de codificación en consolas de Windows
os.environ['PYTHONUTF8'] = '1'

from app.db.session import SessionLocal
from app.core.security import get_password_hash
from sqlalchemy import text

def seed():
    db = SessionLocal()
    try:
        # 1. Insertar roles base del sistema
        roles = [
            (1, 'client'),
            (2, 'analyst'),
            (3, 'coordinador_exclusivo'),
            (4, 'coordinador_tradex'),
            (5, 'mercaderista'),
            (6, 'supervisor'),
            (7, 'auditor'),
            (8, 'admin'),
            (9, 'vendedor'),
            (10, 'atc'),
            (11, 'coordinador_general'),
            (12, 'encuestador'),
            (13, 'cliente_encuestador'),
            (14, 'auditor_campo'),
        ]
        
        print("Insertando roles base...")
        # Habilitar inserción explícita de IDs en SQL Server
        db.execute(text("SET IDENTITY_INSERT ROLES ON"))
        
        for rid, nombre in roles:
            # Validamos si ya existe el rol
            exists = db.execute(
                text("SELECT 1 FROM ROLES WHERE id_rol = :id"), 
                {"id": rid}
            ).fetchone()
            
            if not exists:
                db.execute(
                    text("INSERT INTO ROLES (id_rol, rol) VALUES (:id, :nombre)"),
                    {"id": rid, "nombre": nombre}
                )
                print(f"  -> Rol '{nombre}' (ID: {rid}) insertado.")
        
        db.execute(text("SET IDENTITY_INSERT ROLES OFF"))
        
        # 2. Crear usuario administrador de prueba
        print("\nVerificando usuario administrador...")
        admin_exists = db.execute(
            text("SELECT 1 FROM USUARIOS WHERE username = 'admin'")
        ).fetchone()
        
        if not admin_exists:
            hashed_pw = get_password_hash("Admin1234!")
            db.execute(
                text("""
                    INSERT INTO USUARIOS (username, password_hash, email, id_rol, activo)
                    VALUES (:username, :password, :email, :rol, 1)
                """),
                {
                    "username": "admin",
                    "password": hashed_pw,
                    "email": "admin@epran.com",
                    "rol": 8 # Admin
                }
            )
            print("  -> Usuario 'admin' creado con contraseña: Admin1234!")
        else:
            print("  -> El usuario 'admin' ya existe en la base de datos.")
            
        db.commit()
        print("\n¡Semilla de desarrollo completada exitosamente!")
        
    except Exception as e:
        db.rollback()
        print(f"\nError durante el seed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
