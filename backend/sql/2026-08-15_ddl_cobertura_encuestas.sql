-- Curva de cobertura de encuestas médicas (roadmap predictivo, S4): cuántos
-- médicos nuevos se registran por semana en cada estado, ajustado con una
-- curva logística sobre el acumulado (proceso que se satura, no una serie
-- estacionaria de demanda). Ver app/services/cobertura_encuestas_service.py.
CREATE TABLE COBERTURA_ENCUESTAS_CURVA (
    id_curva                INT IDENTITY(1,1) PRIMARY KEY,
    estado                    VARCHAR(100) NOT NULL,
    n_semanas_historial        INT NOT NULL,
    n_medicos_total            INT NOT NULL,
    curva_valida               BIT NOT NULL DEFAULT 0,
    asintota_l                 FLOAT NULL,  -- L: techo estimado de médicos alcanzables en la zona
    tasa_crecimiento_k         FLOAT NULL,  -- k: qué tan rápido se acerca al techo
    semana_punto_medio_x0        FLOAT NULL,  -- x0: semana del punto de inflexión
    r2                        FLOAT NULL,
    semana_inicio               DATE NOT NULL,           -- lunes de la primera semana con datos
    serie_json                  NVARCHAR(MAX) NOT NULL,   -- histórico real: [{semana, nuevos, acumulado}]
    proyeccion_json              NVARCHAR(MAX) NULL,       -- solo si curva_valida: [{semana, proyectado}]
    fecha_calculo                DATETIME NOT NULL DEFAULT GETDATE()
);
CREATE INDEX IX_COBERTURA_ENCUESTAS_CURVA_estado ON COBERTURA_ENCUESTAS_CURVA(estado);
