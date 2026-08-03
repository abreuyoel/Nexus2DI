-- Valida que los índices de 2026-08-02_indices_centro_mando.sql existan
-- realmente (y de paso, cuántas filas tiene cada tabla involucrada -- eso
-- solo ayuda a entender si el volumen de datos explica la lentitud de
-- Plan de Acción incluso con los índices puestos).

SELECT
    t.name AS tabla,
    i.name AS indice,
    CASE WHEN i.name IS NULL THEN 'FALTA' ELSE 'OK' END AS estado
FROM (VALUES
    ('VISITAS_MERCADERISTA', 'IX_VisitasMercaderista_FechaVisita'),
    ('VISITAS_MERCADERISTA', 'IX_VisitasMercaderista_Mercaderista_Fecha'),
    ('FOTOS_TOTALES',        'IX_FotosTotales_Visita_Tipo'),
    ('FOTOS_TOTALES',        'IX_FotosTotales_FechaRegistro'),
    ('RUTAS_ACTIVADAS',      'IX_RutasActivadas_Fecha'),
    ('RUTA_PROGRAMACION',    'IX_RutaProgramacion_Ruta_Activa'),
    ('RUTA_PROGRAMACION',    'IX_RutaProgramacion_Punto_Cliente'),
    ('MERCADERISTAS_RUTAS',  'IX_MercaderistasRutas_Ruta_Merc'),
    ('analistas_rutas',      'IX_AnalistasRutas_Ruta_Analista'),
    ('BALANCES_TOTALES',     'IX_BalancesTotales_Cliente_Fecha'),
    ('BALANCES_TOTALES',     'IX_BalancesTotales_Pdv')
) AS esperados(tabla_nombre, indice_nombre)
CROSS APPLY (SELECT OBJECT_ID(tabla_nombre) AS obj_id) o
JOIN sys.tables t ON t.object_id = o.obj_id
LEFT JOIN sys.indexes i ON i.object_id = o.obj_id AND i.name = indice_nombre
ORDER BY estado DESC, tabla;

-- Volumen real de las tablas que toca Plan de Acción -- si RUTA_PROGRAMACION
-- o VISITAS_MERCADERISTA tienen cientos de miles de filas, el GROUP BY
-- puede tardar aunque el índice exista (el índice ayuda a filtrar/ordenar,
-- no reduce mágicamente el trabajo de agregar millones de filas).
SELECT 'RUTA_PROGRAMACION' AS tabla, COUNT(*) AS filas, SUM(CASE WHEN activa = 1 THEN 1 ELSE 0 END) AS filas_activas FROM RUTA_PROGRAMACION
UNION ALL
SELECT 'VISITAS_MERCADERISTA', COUNT(*), SUM(CASE WHEN fecha_visita >= DATEADD(day, -31, CAST(GETDATE() AS DATE)) THEN 1 ELSE 0 END) FROM VISITAS_MERCADERISTA
UNION ALL
SELECT 'FOTOS_TOTALES', COUNT(*), NULL FROM FOTOS_TOTALES
UNION ALL
SELECT 'FRECUENCIAS_PDVS_CLIENTE', COUNT(*), SUM(CASE WHEN activo = 1 THEN 1 ELSE 0 END) FROM FRECUENCIAS_PDVS_CLIENTE;
