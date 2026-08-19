-- ============================================================================
-- DESACTIVAR 3 PDV de Flora Foods en la Ruta FF1 (Panamá) — VERSIÓN CORREGIDA
-- Base de datos: epran (producción)
-- Fecha: 2026-08-19
--
-- ⚠️ DIFERENCIA CON LA VERSIÓN ANTERIOR:
-- La versión anterior usaba BEGIN TRANSACTION y NO se ejecutó COMMIT;. Como el
-- UPDATE quedó dentro de una transacción abierta, al cerrar la sesión SQL Server
-- lo REVIRTIÓ automáticamente (por eso seguía visible en producción).
--
-- ESTA versión NO abre transacción: cada UPDATE se confirma (commit) al terminar
-- la instrucción. Así queda aplicado de forma definitiva.
--
-- Objetivo: que Flora Foods (id_cliente 69) NO vea estos 3 PDV, sin eliminar
-- registros. Se logra poniendo activa = 0 en RUTA_PROGRAMACION, que es la
-- bandera que usan el portal del cliente (points.py _apply_client_pdv_filter
-- -> rp.activa = 1) y los servicios del mercaderista para mostrar los PDV.
-- Es 100% reversible: basta volver a poner activa = 1.
--
-- Registros afectados (Ruta FF1 = id_ruta 1574, cuadrante "Panamá Metro"):
--   id_programacion 33594  -> SUP0001 "Super 99 Albrook"       (Lunes,   Flora Foods)
--   id_programacion 33600  -> SUP0002 "Super 99 Transístmica"  (Martes,  Flora Foods)
--   id_programacion 33602  -> RIB0003 "Riba Smith Transístmica"(Martes,  Flora Foods)
--
-- NOTA: FRECUENCIAS_PDVS_CLIENTE está vacía para id_cliente=69, por lo que
-- no hay filas de frecuencia que desactivar para Flora Foods.
-- ============================================================================

-- 1) VERIFICACIÓN PREVIA: muestra los registros que se van a desactivar
PRINT '=== REGISTROS A DESACTIVAR (antes) ===';
SELECT
    rp.id_programacion,
    rp.id_punto_interes,
    rp.punto_interes,
    rp.id_ruta,
    rn.ruta            AS nombre_ruta,
    rn.cuadrante,
    rp.dia,
    rp.activa,
    c.cliente          AS cliente_asignado
FROM RUTA_PROGRAMACION rp
LEFT JOIN RUTAS_NUEVAS rn ON rn.id_ruta = rp.id_ruta
LEFT JOIN CLIENTES c     ON c.id_cliente = rp.id_cliente
WHERE rp.id_programacion IN (33602, 33594, 33600);

-- 2) DESACTIVAR (UPDATE, NO DELETE) — SIN transacción: se confirma al instante
UPDATE RUTA_PROGRAMACION
SET activa = 0
WHERE id_programacion IN (33602, 33594, 33600)
  AND id_cliente = 69;   -- protección extra: solo toca registros de Flora Foods

-- 3) VERIFICACIÓN POSTERIOR: activa DEBE ser 0
PRINT '=== REGISTROS DESPUES DEL UPDATE ===';
SELECT
    rp.id_programacion,
    rp.id_punto_interes,
    rp.punto_interes,
    rp.id_ruta,
    rn.ruta            AS nombre_ruta,
    rp.dia,
    rp.activa,
    c.cliente          AS cliente_asignado
FROM RUTA_PROGRAMACION rp
LEFT JOIN RUTAS_NUEVAS rn ON rn.id_ruta = rp.id_ruta
LEFT JOIN CLIENTES c     ON c.id_cliente = rp.id_cliente
WHERE rp.id_programacion IN (33602, 33594, 33600);

-- Si la columna activa sale en 0, el cambio ya quedó APLICADO en producción.
-- No necesitas hacer nada más. Cierra la pestaña y listo.

-- ============================================================================
-- Para revertir el cambio más adelante (reactivar), ejecuta SOLO esto:
--   UPDATE RUTA_PROGRAMACION SET activa = 1
--   WHERE id_programacion IN (33602, 33594, 33600)
--     AND id_cliente = 69;
-- ============================================================================
