"""Crea HORAS_PROMEDIO_EJECUCION: minutos promedio de ejecucion esperados
para un cliente segun la clasificacion de PDV (CAT_TIPO_NEGOCIO, que en
PUNTOS_INTERES1 corresponde a jerarquia_nivel_2_2)."""
from app.db.session import SessionLocal
from sqlalchemy import text

DDL = """
CREATE TABLE HORAS_PROMEDIO_EJECUCION (
  id_horas_promedio_ejecucion INT IDENTITY PRIMARY KEY,
  id_cliente INT NOT NULL,
  id_tipo_negocio INT NOT NULL,
  minutos_promedio INT NOT NULL,
  fecha_creado DATETIME NOT NULL DEFAULT GETDATE(),
  fecha_modificado DATETIME NULL,
  id_usuario_creador INT NULL,
  id_usuario_modificador INT NULL,
  CONSTRAINT FK_HPE_CLIENTE FOREIGN KEY (id_cliente) REFERENCES CLIENTES(id_cliente),
  CONSTRAINT FK_HPE_TIPO_NEGOCIO FOREIGN KEY (id_tipo_negocio) REFERENCES CAT_TIPO_NEGOCIO(id),
  CONSTRAINT FK_HPE_USUARIO_CREADOR FOREIGN KEY (id_usuario_creador) REFERENCES USUARIOS(id_usuario),
  CONSTRAINT FK_HPE_USUARIO_MODIFICADOR FOREIGN KEY (id_usuario_modificador) REFERENCES USUARIOS(id_usuario)
);
"""

if __name__ == "__main__":
    db = SessionLocal()
    existing = db.execute(text(
        "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'HORAS_PROMEDIO_EJECUCION'"
    )).fetchall()
    if existing:
        print("Ya existe, no se crea nada:", existing)
    else:
        db.execute(text(DDL.strip().rstrip(";")))
        db.commit()
        print("Tabla creada.")

    r = db.execute(text(
        "SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_NAME = 'HORAS_PROMEDIO_EJECUCION' ORDER BY ORDINAL_POSITION"
    )).fetchall()
    for row in r:
        print(row)
    db.close()
