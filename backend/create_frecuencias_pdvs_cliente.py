"""Crea FRECUENCIAS_PDVS_CLIENTE: cuantas veces por semana debe visitarse un PDV
para un cliente dado (5, 3, 1, 0.5, 0.25, etc. — ver conversacion para el
significado de cada valor)."""
from app.db.session import SessionLocal
from sqlalchemy import text

DDL = """
CREATE TABLE FRECUENCIAS_PDVS_CLIENTE (
  id_frecuencia_pdv_cliente INT IDENTITY PRIMARY KEY,
  id_cliente INT NOT NULL,
  id_punto_interes VARCHAR(50) NOT NULL,
  frecuencia_semanal DECIMAL(5,2) NOT NULL,
  observaciones VARCHAR(500) NULL,
  activo BIT NOT NULL DEFAULT 1,
  fecha_creacion DATETIME NOT NULL DEFAULT GETDATE(),
  fecha_modificacion DATETIME NULL,
  id_usuario INT NULL,
  CONSTRAINT FK_FRECPDVCLI_CLIENTE FOREIGN KEY (id_cliente) REFERENCES CLIENTES(id_cliente),
  CONSTRAINT FK_FRECPDVCLI_PDV FOREIGN KEY (id_punto_interes) REFERENCES PUNTOS_INTERES1(identificador),
  CONSTRAINT FK_FRECPDVCLI_USUARIO FOREIGN KEY (id_usuario) REFERENCES USUARIOS(id_usuario)
);
"""

if __name__ == "__main__":
    db = SessionLocal()
    existing = db.execute(text(
        "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'FRECUENCIAS_PDVS_CLIENTE'"
    )).fetchall()
    if existing:
        print("Ya existe, no se crea nada:", existing)
    else:
        for stmt in DDL.strip().split(";\n\n"):
            stmt = stmt.strip().rstrip(";")
            if stmt:
                db.execute(text(stmt))
        db.commit()
        print("Tabla creada.")

    r = db.execute(text(
        "SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_NAME = 'FRECUENCIAS_PDVS_CLIENTE' ORDER BY ORDINAL_POSITION"
    )).fetchall()
    for row in r:
        print(row)
    db.close()
