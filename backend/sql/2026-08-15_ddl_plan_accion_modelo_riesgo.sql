-- Plan de Acción: persistencia del modelo entrenado que reemplaza el
-- peso_tipo hardcodeado (0.6/1.0) de plan_accion_service.py por una
-- probabilidad de rechazo real, entrenada con LightGBM sobre el historial
-- de VISITAS_MERCADERISTA/FOTOS_TOTALES.
--
-- El booster se guarda como texto (LightGBM Booster.model_to_string(), su
-- formato nativo) en vez de un pickle -- no depende de que la versión de
-- lightgbm en producción coincida byte a byte con la de entrenamiento, y no
-- ejecuta código arbitrario al cargarlo (a diferencia de un pickle).
--
-- "activo" en vez de borrar filas viejas: permite comparar métricas entre
-- entrenamientos sucesivos sin perder el historial.

CREATE TABLE PLAN_ACCION_MODELO_RIESGO (
    id_modelo            INT IDENTITY(1,1) PRIMARY KEY,
    fecha_entrenamiento   DATETIME NOT NULL DEFAULT GETDATE(),
    modelo_texto          NVARCHAR(MAX) NOT NULL,
    features_json         NVARCHAR(MAX) NOT NULL,
    metricas_json         NVARCHAR(MAX) NOT NULL,
    tasa_base_global       FLOAT NOT NULL,
    n_entrenamiento        INT NOT NULL,
    n_validacion            INT NOT NULL,
    activo                BIT NOT NULL DEFAULT 1
);

CREATE INDEX IX_PLAN_ACCION_MODELO_RIESGO_activo ON PLAN_ACCION_MODELO_RIESGO(activo, fecha_entrenamiento DESC);

-- Columnas nuevas en la tabla ya existente PLAN_ACCION_PENDIENTES: además
-- del score final, dejar visible CON QUÉ peso de riesgo se calculó y si
-- salió del modelo entrenado o del PESO_TIPO fijo de respaldo (0.6/1.0) --
-- mismo espíritu que SHAP, que el usuario pueda ver por qué salió ese score,
-- no solo el número final.
ALTER TABLE PLAN_ACCION_PENDIENTES ADD peso_riesgo FLOAT NULL;
ALTER TABLE PLAN_ACCION_PENDIENTES ADD riesgo_de_modelo BIT NOT NULL DEFAULT 0;
