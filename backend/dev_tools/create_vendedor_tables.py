"""Crea VENDEDOR_JORNADAS y VENDEDOR_VISITAS, que el modulo Vendedor de main
asume que existen pero nunca se crearon en la base real. Ver plan del modulo
Ventas (version2) para el detalle de por que hacen falta."""
from app.db.session import SessionLocal
from sqlalchemy import text

DDL = """
CREATE TABLE VENDEDOR_JORNADAS (
  id_jornada INT IDENTITY PRIMARY KEY,
  id_usuario INT NOT NULL,
  fecha_inicio DATETIME NOT NULL DEFAULT GETDATE(),
  fecha_fin DATETIME NULL,
  estado VARCHAR(50) NOT NULL DEFAULT 'En Progreso'
);

CREATE TABLE VENDEDOR_VISITAS (
  id_visita_vendedor INT IDENTITY PRIMARY KEY,
  id_jornada INT NOT NULL,
  id_usuario INT NOT NULL,
  id_punto_interes VARCHAR(100) NOT NULL,
  id_cliente INT NOT NULL,
  fecha_hora DATETIME NOT NULL DEFAULT GETDATE(),
  vendio BIT NOT NULL,
  monto FLOAT NULL,
  razon_no_venta VARCHAR(500) NULL,
  latitud FLOAT NULL,
  longitud FLOAT NULL
);
"""

if __name__ == "__main__":
    db = SessionLocal()
    existing = db.execute(text(
        "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME IN ('VENDEDOR_JORNADAS','VENDEDOR_VISITAS')"
    )).fetchall()
    if existing:
        print("Ya existen, no se crea nada:", existing)
    else:
        for stmt in DDL.strip().split(";\n\n"):
            stmt = stmt.strip().rstrip(";")
            if stmt:
                db.execute(text(stmt))
        db.commit()
        print("Tablas creadas.")

    r = db.execute(text(
        "SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_NAME IN ('VENDEDOR_JORNADAS','VENDEDOR_VISITAS') ORDER BY TABLE_NAME, ORDINAL_POSITION"
    )).fetchall()
    for row in r:
        print(row)
    db.close()
