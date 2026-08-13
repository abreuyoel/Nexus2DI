-- Diagnóstico previo a Fase 3 (Plan de Acción: geo-clustering + capacidad +
-- generación de rutas BCK). Antes de escribir el código quiero confirmar
-- estas 4 cosas con datos reales.

-- 1) ¿Existe ya un SERVICIOS con prefijo "BCK"? (hace falta para poder
--    crear rutas nuevas vía POST /api/routes/)
SELECT id, nombre, prefijo, activo FROM SERVICIOS ORDER BY nombre;

-- 2) HORAS_PROMEDIO_EJECUCION: ¿el join correcto es contra jerarquia_nivel_2
--    o jerarquia_nivel_2_2? Compara cuántos PDVs matchean por cada camino.
SELECT
    (SELECT COUNT(*) FROM HORAS_PROMEDIO_EJECUCION) AS filas_horas_promedio,
    (SELECT COUNT(*) FROM PUNTOS_INTERES1 pi
       JOIN CAT_TIPO_NEGOCIO ctn ON ctn.nombre = pi.jerarquia_nivel_2) AS pdvs_matchean_por_jerarquia_2,
    (SELECT COUNT(*) FROM PUNTOS_INTERES1 pi
       JOIN CAT_TIPO_NEGOCIO ctn ON ctn.nombre = pi.jerarquia_nivel_2_2) AS pdvs_matchean_por_jerarquia_2_2;

-- 3) Completitud de coordenadas en PUNTOS_INTERES1 (texto, puede venir vacío/NULL)
SELECT
    COUNT(*) AS total_puntos,
    SUM(CASE WHEN latitud IS NOT NULL AND latitud <> '' AND longitud IS NOT NULL AND longitud <> '' THEN 1 ELSE 0 END) AS con_coordenadas
FROM PUNTOS_INTERES1;

-- 4) Completitud de coordenadas en FOTOS_TOTALES (último mes, para no escanear todo el histórico)
SELECT
    COUNT(*) AS total_fotos_ultimo_mes,
    SUM(CASE WHEN latitud IS NOT NULL AND longitud IS NOT NULL THEN 1 ELSE 0 END) AS con_coordenadas
FROM FOTOS_TOTALES
WHERE fecha_registro >= DATEADD(day, -31, CAST(GETDATE() AS DATE));
