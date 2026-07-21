import sys
import os
import bcrypt

sys.path.append('.')
from app.db.session import engine
from sqlalchemy import text
from sqlalchemy.orm import Session

def setup_db():
    with Session(engine) as session:
        # Create Tables
        tables_sql = """
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='JORNADAS_ENCUESTADOR' AND xtype='U')
        CREATE TABLE JORNADAS_ENCUESTADOR (
            id_jornada INT IDENTITY(1,1) PRIMARY KEY,
            id_usuario INT NOT NULL,
            fecha_inicio DATETIME2 NOT NULL,
            fecha_fin DATETIME2 NULL,
            estado VARCHAR(20) NOT NULL,
            latitud FLOAT NULL,
            longitud FLOAT NULL,
            ciudad VARCHAR(100) NULL,
            estado_geo VARCHAR(100) NULL,
            notas VARCHAR(MAX) NULL
        );

        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='centros_salud' AND xtype='U')
        CREATE TABLE centros_salud (
            id_centro INT IDENTITY(1,1) PRIMARY KEY,
            nombre_centro VARCHAR(255) NOT NULL,
            direccion_completa VARCHAR(MAX) NOT NULL,
            ciudad VARCHAR(100) NULL,
            estado VARCHAR(100) NULL
        );

        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='encuestas_centro' AND xtype='U')
        CREATE TABLE encuestas_centro (
            id_encuesta INT IDENTITY(1,1) PRIMARY KEY,
            id_usuario INT NOT NULL,
            id_centro INT NOT NULL,
            fecha_verificacion DATE NOT NULL,
            fuente_informacion VARCHAR(255) NOT NULL,
            notas_generales TEXT NULL,
            creado_en DATETIME2 DEFAULT GETDATE(),
            id_jornada INT NULL,
            estado VARCHAR(20) NOT NULL
        );

        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='medicos' AND xtype='U')
        CREATE TABLE medicos (
            id_medico INT IDENTITY(1,1) PRIMARY KEY,
            id_medico_externo VARCHAR(20) NOT NULL,
            apellido1 VARCHAR(100) NOT NULL,
            apellido2 VARCHAR(100) NULL,
            nombre1 VARCHAR(100) NOT NULL,
            nombre2 VARCHAR(100) NULL,
            especialidad VARCHAR(100) NOT NULL,
            sub_especialidad VARCHAR(100) NULL,
            universidad_graduacion VARCHAR(255) NULL,
            nro_MPPS VARCHAR(50) NULL,
            nro_colegiado VARCHAR(50) NULL,
            ciudad VARCHAR(100) NOT NULL,
            estado VARCHAR(100) NOT NULL,
            telefono VARCHAR(20) NULL,
            whatsapp VARCHAR(20) NULL,
            email VARCHAR(100) NULL,
            linkedin VARCHAR(255) NULL,
            instagram VARCHAR(255) NULL,
            fecha_registro DATETIME2 DEFAULT GETDATE()
        );

        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='medico_centro_encuesta' AND xtype='U')
        CREATE TABLE medico_centro_encuesta (
            id_medico_centro INT IDENTITY(1,1) PRIMARY KEY,
            id_encuesta INT NOT NULL,
            id_medico INT NOT NULL,
            piso_consultorio VARCHAR(50) NULL,
            horarios_consulta VARCHAR(255) NULL,
            dias_consulta VARCHAR(255) NULL,
            direccion_especifica VARCHAR(MAX) NULL,
            clinica2_nombre VARCHAR(255) NULL,
            piso_consultorio2 VARCHAR(50) NULL,
            horarios_consulta2 VARCHAR(255) NULL,
            dias_consulta2 VARCHAR(255) NULL,
            direccion_especifica2 VARCHAR(MAX) NULL,
            valor_consulta_rango VARCHAR(30) NOT NULL,
            promedio_pacientes_semanal_rango VARCHAR(30) NOT NULL,
            actualizado_en DATETIME2 DEFAULT GETDATE()
        );
        """
        try:
            session.execute(text(tables_sql))
            session.commit()
            print("Tablas creadas exitosamente.")
        except Exception as e:
            session.rollback()
            print(f"Error creando tablas: {e}")

        # Insert Roles
        roles_sql = """
        IF NOT EXISTS (SELECT * FROM ROLES WHERE id_rol = 12)
            INSERT INTO ROLES (id_rol, rol) VALUES (12, 'Encuestador');
        IF NOT EXISTS (SELECT * FROM ROLES WHERE id_rol = 13)
            INSERT INTO ROLES (id_rol, rol) VALUES (13, 'Cliente Encuestador');
        """
        try:
            session.execute(text(roles_sql))
            session.commit()
            print("Roles insertados exitosamente.")
        except Exception as e:
            session.rollback()
            print(f"Error insertando roles: {e}")

        # Insert Test Users
        try:
            # Hash '123456' using bcrypt
            salt = bcrypt.gensalt()
            hashed_pwd = bcrypt.hashpw(b"123456", salt).decode('utf-8')

            check_u1 = session.execute(text("SELECT id_usuario FROM USUARIOS WHERE username = 'encuestador_test'")).fetchone()
            if not check_u1:
                session.execute(text("INSERT INTO USUARIOS (username, email, password_hash, id_rol, activo) VALUES ('encuestador_test', 'encuestador@test.com', :pwd, 12, 1)"), {"pwd": hashed_pwd})
            
            check_u2 = session.execute(text("SELECT id_usuario FROM USUARIOS WHERE username = 'cliente_encuestador_test'")).fetchone()
            if not check_u2:
                session.execute(text("INSERT INTO USUARIOS (username, email, password_hash, id_rol, activo) VALUES ('cliente_encuestador_test', 'cliente@test.com', :pwd, 13, 1)"), {"pwd": hashed_pwd})
                
            session.commit()
            print("Usuarios de prueba insertados exitosamente.")
        except Exception as e:
            session.rollback()
            print(f"Error insertando usuarios: {e}")

if __name__ == '__main__':
    setup_db()
