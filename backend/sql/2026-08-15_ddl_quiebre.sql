-- Quiebre dinámico (roadmap predictivo, N2): alertar antes de que un
-- producto llegue a 0, no cuando ya llegó. estado_producto='quiebre' es un
-- registro del pasado; estas tablas guardan la predicción hacia adelante.

-- Capa 1: línea base (percentiles P10/P25 de `caras`) por grupo --
-- categoría × jerarquía del PDV × bucket de frecuencia × cliente.
CREATE TABLE QUIEBRE_LINEA_BASE (
    id_linea_base       INT IDENTITY(1,1) PRIMARY KEY,
    id_categoria         INT NULL,
    jerarquia_nivel_2     NVARCHAR(200) NULL,
    bucket_frecuencia     VARCHAR(20) NOT NULL,
    id_cliente            INT NOT NULL,
    p10_caras             FLOAT NOT NULL,
    p25_caras             FLOAT NOT NULL,
    n_muestras            INT NOT NULL,
    fecha_calculo         DATETIME NOT NULL DEFAULT GETDATE()
);
CREATE INDEX IX_QUIEBRE_LINEA_BASE_grupo
    ON QUIEBRE_LINEA_BASE(id_categoria, jerarquia_nivel_2, bucket_frecuencia, id_cliente);

-- Capa 2: alerta vigente por (PDV, producto, cliente) -- se reemplaza
-- entera en cada recálculo, mismo patrón que PLAN_ACCION_PENDIENTES.
CREATE TABLE ALERTAS_QUIEBRE (
    id_alerta                  INT IDENTITY(1,1) PRIMARY KEY,
    identificador_pdv           VARCHAR(100) NOT NULL,
    id_product                   INT NOT NULL,
    id_cliente                   INT NOT NULL,
    producto                     NVARCHAR(255) NULL,
    caras_actual                 FLOAT NULL,
    caras_anterior                FLOAT NULL,
    tendencia                    FLOAT NULL,
    riesgo                       VARCHAR(20) NOT NULL,   -- Normal | Riesgo MEDIO | Riesgo ALTO | Quiebre
    urgente                      BIT NOT NULL DEFAULT 0,
    dias_hasta_proxima_visita     INT NULL,
    dias_para_llegar_a_cero        FLOAT NULL,
    fecha_calculo                 DATETIME NOT NULL DEFAULT GETDATE()
);
CREATE INDEX IX_ALERTAS_QUIEBRE_riesgo ON ALERTAS_QUIEBRE(riesgo, urgente);
CREATE INDEX IX_ALERTAS_QUIEBRE_pdv ON ALERTAS_QUIEBRE(identificador_pdv, id_product, id_cliente);
