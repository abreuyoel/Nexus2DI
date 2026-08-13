-- ── Agregar columnas de fin de jornada en JORNADAS_ENCUESTADOR ──

IF NOT EXISTS (
    SELECT 1 FROM sys.columns 
    WHERE object_id = OBJECT_ID('JORNADAS_ENCUESTADOR') AND name = 'latitud_fin'
)
BEGIN
    ALTER TABLE JORNADAS_ENCUESTADOR ADD latitud_fin FLOAT NULL;
    PRINT 'Columna latitud_fin agregada a JORNADAS_ENCUESTADOR';
END;

IF NOT EXISTS (
    SELECT 1 FROM sys.columns 
    WHERE object_id = OBJECT_ID('JORNADAS_ENCUESTADOR') AND name = 'longitud_fin'
)
BEGIN
    ALTER TABLE JORNADAS_ENCUESTADOR ADD longitud_fin FLOAT NULL;
    PRINT 'Columna longitud_fin agregada a JORNADAS_ENCUESTADOR';
END;

IF NOT EXISTS (
    SELECT 1 FROM sys.columns 
    WHERE object_id = OBJECT_ID('JORNADAS_ENCUESTADOR') AND name = 'ciudad_fin'
)
BEGIN
    ALTER TABLE JORNADAS_ENCUESTADOR ADD ciudad_fin VARCHAR(100) NULL;
    PRINT 'Columna ciudad_fin agregada a JORNADAS_ENCUESTADOR';
END;

IF NOT EXISTS (
    SELECT 1 FROM sys.columns 
    WHERE object_id = OBJECT_ID('JORNADAS_ENCUESTADOR') AND name = 'estado_geo_fin'
)
BEGIN
    ALTER TABLE JORNADAS_ENCUESTADOR ADD estado_geo_fin VARCHAR(100) NULL;
    PRINT 'Columna estado_geo_fin agregada a JORNADAS_ENCUESTADOR';
END;
