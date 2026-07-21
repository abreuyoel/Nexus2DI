import os
from sqlalchemy import text
from app.core.database import SessionLocal

def homologar_bcv():
    db = SessionLocal()
    try:
        # Check if bcv exists in epran
        print("Verificando existencia de la tabla bcv en epran...")
        check_src = db.execute(text("SELECT count(*) FROM epran.sys.tables WHERE name = 'bcv'")).scalar()
        if check_src == 0:
            print("❌ La tabla 'bcv' no existe en la base de datos 'epran'.")
            return

        # Check if bcv exists in epran-qa
        print("Verificando existencia de la tabla bcv en epran-qa...")
        check_dst = db.execute(text("SELECT count(*) FROM [epran-qa].sys.tables WHERE name = 'bcv'")).scalar()
        if check_dst == 0:
            print("❌ La tabla 'bcv' no existe en la base de datos 'epran-qa'.")
            return

        print("Homologando tabla bcv de epran a epran-qa...")
        
        # Eliminar datos actuales en QA para evitar duplicados si la tabla no tiene primary key / merge logic
        print("Limpiando bcv en epran-qa...")
        db.execute(text("DELETE FROM [epran-qa].[dbo].[bcv]"))
        
        # Insertar datos de epran a epran-qa
        print("Copiando datos de epran a epran-qa...")
        # Since identity columns might exist, we turn on IDENTITY_INSERT if needed, 
        # but usually bcv table is just date and rate. We'll try a direct insert first.
        try:
            res = db.execute(text("INSERT INTO [epran-qa].[dbo].[bcv] SELECT * FROM [epran].[dbo].[bcv]"))
            db.commit()
            print(f"✅ ¡Homologación completada con éxito! Filas copiadas: {res.rowcount}")
        except Exception as e:
            db.rollback()
            err_msg = str(e)
            if "IDENTITY_INSERT" in err_msg:
                print("Se detectó una columna IDENTITY. Reintentando con IDENTITY_INSERT ON...")
                # Get column names
                cols = db.execute(text("""
                    SELECT COLUMN_NAME
                    FROM [epran-qa].INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_NAME = 'bcv'
                """)).fetchall()
                col_names = ", ".join([f"[{c[0]}]" for c in cols])
                
                db.execute(text("SET IDENTITY_INSERT [epran-qa].[dbo].[bcv] ON"))
                res = db.execute(text(f"INSERT INTO [epran-qa].[dbo].[bcv] ({col_names}) SELECT {col_names} FROM [epran].[dbo].[bcv]"))
                db.execute(text("SET IDENTITY_INSERT [epran-qa].[dbo].[bcv] OFF"))
                db.commit()
                print(f"✅ ¡Homologación completada con éxito (con IDENTITY_INSERT)! Filas copiadas: {res.rowcount}")
            else:
                raise e

    except Exception as e:
        print(f"❌ Error durante la homologación: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    homologar_bcv()
