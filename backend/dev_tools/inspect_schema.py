import sys; sys.path.append('.')
from app.db.session import SessionLocal
from sqlalchemy import text
db = SessionLocal()

# Check if FOTOS_MERCADERISTA exists
try:
    r = db.execute(text("SELECT TOP 1 * FROM FOTOS_MERCADERISTA")).fetchall()
    print("Table exists, sample:", r)
    r2 = db.execute(text("SELECT COLUMN_NAME FROM information_schema.columns WHERE table_name = 'FOTOS_MERCADERISTA'")).fetchall()
    print("Columns:", [x[0] for x in r2])
except Exception as e:
    print("Table does NOT exist:", e)
    # Create it
    try:
        db.execute(text("""
            CREATE TABLE FOTOS_MERCADERISTA (
                id_foto INT IDENTITY(1,1) PRIMARY KEY,
                id_visita INT NOT NULL,
                tipo_foto NVARCHAR(50) NOT NULL,
                file_path NVARCHAR(500),
                estado NVARCHAR(50) DEFAULT 'pendiente',
                fecha_subida DATETIME DEFAULT GETDATE(),
                CONSTRAINT FK_FotosMerc_Visita FOREIGN KEY (id_visita)
                    REFERENCES VISITAS_MERCADERISTA(id_visita)
            )
        """))
        db.commit()
        print("Table FOTOS_MERCADERISTA created successfully!")
    except Exception as e2:
        print("Error creating table:", e2)
