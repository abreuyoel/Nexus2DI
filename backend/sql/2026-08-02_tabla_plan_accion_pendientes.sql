-- Módulo "Plan de Acción" (Fase 2): tabla donde el job en background guarda
-- el último cálculo de "qué (ruta, PDV, cliente) sigue debiendo visita este
-- período (semana o mes, según su frecuencia) y qué tan urgente es".
-- Se recalcula completa en cada corrida (DELETE + INSERT) -- no guarda
-- historial, es siempre la foto más reciente. Ver
-- app/services/plan_accion_service.py para la fórmula de score.

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'PLAN_ACCION_PENDIENTES')
BEGIN
    CREATE TABLE PLAN_ACCION_PENDIENTES (
        id_pendiente        INT IDENTITY(1,1) PRIMARY KEY,
        id_ruta             INT NOT NULL,
        ruta_nombre         NVARCHAR(200) NULL,
        id_punto_interes    NVARCHAR(100) NOT NULL,
        punto_de_interes    NVARCHAR(300) NULL,
        departamento        NVARCHAR(200) NULL,
        ciudad              NVARCHAR(200) NULL,
        id_cliente          INT NOT NULL,
        cliente_nombre      NVARCHAR(200) NULL,
        prioridad_ruta      NVARCHAR(50) NULL,
        frecuencia_semanal  DECIMAL(6,2) NULL,
        periodo             NVARCHAR(10) NOT NULL,   -- 'semana' | 'mes'
        tipo_pendiente      NVARCHAR(30) NOT NULL,   -- 'nunca_visitado' | 'fotos_rechazadas'
        visitas_requeridas  DECIMAL(6,2) NULL,
        visitas_hechas      DECIMAL(6,2) NULL,
        visitas_faltantes   DECIMAL(6,2) NULL,
        dias_disponibles    INT NULL,
        urgencia            DECIMAL(10,4) NULL,
        score               DECIMAL(10,4) NOT NULL,
        fecha_calculo       DATETIME NOT NULL DEFAULT GETDATE(),
        CONSTRAINT UQ_PlanAccionPendientes UNIQUE (id_ruta, id_punto_interes, id_cliente)
    );

    CREATE INDEX IX_PlanAccionPendientes_Score ON PLAN_ACCION_PENDIENTES (score DESC);
    CREATE INDEX IX_PlanAccionPendientes_Ruta ON PLAN_ACCION_PENDIENTES (id_ruta);
    CREATE INDEX IX_PlanAccionPendientes_Cliente ON PLAN_ACCION_PENDIENTES (id_cliente);
END
