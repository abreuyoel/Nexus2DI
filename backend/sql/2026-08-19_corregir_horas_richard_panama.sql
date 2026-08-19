-- ============================================================================
-- CORREGIR HORAS DE RICHARD SANCHEZ (id_mercaderista 808) — Panamá UTC-5
-- Base de datos: epran (producción)
-- Fecha: 2026-08-19
--
-- PROBLEMA: Richard opera en Panamá (UTC-5) pero el sistema registra en hora
-- de Venezuela (UTC-4). Sus registros quedaron 1 HORA ADELANTADOS.
-- Esta corrección RESTA 1 HORA a todas sus fechas (visitas + activaciones +
-- fecha_registro de fotos).
--
-- ALCANCE VERIFICADO (conteos en prod):
--   VISITAS_MERCADERISTA     : 73 filas  (columna fecha_visita)
--   RUTAS_ACTIVADAS          : 23 filas  (columna fecha_hora_activacion)
--   FOTOS_TOTALES            : 377 filas (columna fecha_registro SOLO;
--                                          fecha_disparo EXIF se deja intacta,
--                                          ya está en hora Panamá correcta)
--   FOTOS_RECHAZADAS         : 0 filas   (no hay nada que corregir)
--   FOTOS_MERCADERISTA       : 0 filas   (no hay nada que corregir)
--   MERC_AUDITORIA_TIEMPO    : 0 filas   (no hay nada que corregir)
--
-- NOTA: los file_path de activaciones/desactivaciones contienen la hora en el
-- NOMBRE del archivo (ej. 808_SUX0010_20260819_184148.jpg). El UPDATE no
-- cambia nombres de archivos, solo timestamps en BD.
-- ============================================================================

BEGIN TRANSACTION;

-- ═══════════════════════════════════════════════════════════════════════════
-- 1) VERIFICACIÓN PREVIA: conteo y muestra de lo que se va a corregir
-- ═══════════════════════════════════════════════════════════════════════════
PRINT '=== VISITAS (antes) ===';
SELECT TOP 5 id_visita, identificador_punto_interes, fecha_visita, estado
FROM VISITAS_MERCADERISTA
WHERE id_mercaderista = 808
ORDER BY fecha_visita DESC;

PRINT '=== ACTIVACIONES (antes) ===';
SELECT TOP 5 id_ruta_activada, id_ruta, fecha_hora_activacion, estado
FROM RUTAS_ACTIVADAS
WHERE id_mercaderista = 808
ORDER BY fecha_hora_activacion DESC;

PRINT '=== FOTOS (antes) ===';
SELECT TOP 5 id_foto, id_visita, id_tipo_foto, fecha_registro, fecha_disparo
FROM FOTOS_TOTALES
WHERE id_visita IN (SELECT id_visita FROM VISITAS_MERCADERISTA WHERE id_mercaderista = 808)
ORDER BY id_foto DESC;

-- ═══════════════════════════════════════════════════════════════════════════
-- 2) CORRECCIÓN: RESTAR 1 HORA (DATEADD hour, -1)
-- ═══════════════════════════════════════════════════════════════════════════

-- 2.1 Visitas
UPDATE VISITAS_MERCADERISTA
SET fecha_visita = DATEADD(HOUR, -1, fecha_visita)
WHERE id_mercaderista = 808
  AND fecha_visita IS NOT NULL;

-- 2.2 Activaciones de rutas
UPDATE RUTAS_ACTIVADAS
SET fecha_hora_activacion = DATEADD(HOUR, -1, fecha_hora_activacion)
WHERE id_mercaderista = 808
  AND fecha_hora_activacion IS NOT NULL;

-- 2.3 FOTOS: SOLO fecha_registro (hora servidor Venezuela).
--     fecha_disparo (EXIF del celular) ya está en hora Panamá y NO se toca.
UPDATE FOTOS_TOTALES
SET fecha_registro = DATEADD(HOUR, -1, fecha_registro)
WHERE id_visita IN (SELECT id_visita FROM VISITAS_MERCADERISTA WHERE id_mercaderista = 808)
  AND fecha_registro IS NOT NULL;

-- ═══════════════════════════════════════════════════════════════════════════
-- 3) VERIFICACIÓN POSTERIOR
-- ═══════════════════════════════════════════════════════════════════════════
PRINT '=== VISITAS (después) ===';
SELECT TOP 5 id_visita, identificador_punto_interes, fecha_visita, estado
FROM VISITAS_MERCADERISTA
WHERE id_mercaderista = 808
ORDER BY fecha_visita DESC;

PRINT '=== ACTIVACIONES (después) ===';
SELECT TOP 5 id_ruta_activada, id_ruta, fecha_hora_activacion, estado
FROM RUTAS_ACTIVADAS
WHERE id_mercaderista = 808
ORDER BY fecha_hora_activacion DESC;

PRINT '=== FOTOS (después) ===';
SELECT TOP 5 id_foto, id_visita, id_tipo_foto, fecha_registro, fecha_disparo
FROM FOTOS_TOTALES
WHERE id_visita IN (SELECT id_visita FROM VISITAS_MERCADERISTA WHERE id_mercaderista = 808)
ORDER BY id_foto DESC;

PRINT '=== CONTEOS CORREGIDOS ===';
SELECT
  (SELECT COUNT(*) FROM VISITAS_MERCADERISTA WHERE id_mercaderista = 808) AS visitas,
  (SELECT COUNT(*) FROM RUTAS_ACTIVADAS WHERE id_mercaderista = 808) AS activaciones,
  (SELECT COUNT(*) FROM FOTOS_TOTALES
     WHERE id_visita IN (SELECT id_visita FROM VISITAS_MERCADERISTA WHERE id_mercaderista = 808)) AS fotos;

-- Revisa que cada fecha haya bajado exactamente 1 hora y que la coherencia
-- con los EXIF (fecha_disparo) se mantenga (diferencia ~4h de subida).
-- Si todo se ve correcto, ejecuta:
--   COMMIT;
-- Si algo salió mal, revierte con:
--   ROLLBACK;
