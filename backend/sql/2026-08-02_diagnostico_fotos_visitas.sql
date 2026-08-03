-- Diagnóstico: ¿por qué Plan de Acción casi no cuenta ninguna visita como
-- "completa"? Compara cuántas visitas del último mes tienen fotos de
-- activación/desactivación (tipo 5/6, el criterio que usa Plan de Acción)
-- contra otros tipos de foto, y cómo se distribuye el campo Estado.

-- 1) De las visitas del último mes, ¿cuántas tienen cada tipo de foto?
SELECT
    COUNT(DISTINCT vm.id_visita) AS total_visitas,
    SUM(CASE WHEN EXISTS (SELECT 1 FROM FOTOS_TOTALES f WHERE f.id_visita = vm.id_visita AND f.id_tipo_foto = 5) THEN 1 ELSE 0 END) AS con_activacion,
    SUM(CASE WHEN EXISTS (SELECT 1 FROM FOTOS_TOTALES f WHERE f.id_visita = vm.id_visita AND f.id_tipo_foto = 6) THEN 1 ELSE 0 END) AS con_desactivacion,
    SUM(CASE WHEN EXISTS (SELECT 1 FROM FOTOS_TOTALES f WHERE f.id_visita = vm.id_visita AND f.id_tipo_foto IN (1,2,3,4,7,8,10)) THEN 1 ELSE 0 END) AS con_otras_fotos_gestion
FROM VISITAS_MERCADERISTA vm
WHERE vm.fecha_visita >= DATEADD(day, -31, CAST(GETDATE() AS DATE));

-- 2) Distribución real de Estado en fotos del último mes (¿existe 'Rechazada' en la práctica?)
SELECT f.Estado, COUNT(*) AS cantidad
FROM FOTOS_TOTALES f
JOIN VISITAS_MERCADERISTA vm ON vm.id_visita = f.id_visita
WHERE vm.fecha_visita >= DATEADD(day, -31, CAST(GETDATE() AS DATE))
GROUP BY f.Estado
ORDER BY cantidad DESC;

-- 3) Distribución de tipos de foto realmente usados en ese período
SELECT f.id_tipo_foto, COUNT(*) AS cantidad
FROM FOTOS_TOTALES f
JOIN VISITAS_MERCADERISTA vm ON vm.id_visita = f.id_visita
WHERE vm.fecha_visita >= DATEADD(day, -31, CAST(GETDATE() AS DATE))
GROUP BY f.id_tipo_foto
ORDER BY f.id_tipo_foto;
