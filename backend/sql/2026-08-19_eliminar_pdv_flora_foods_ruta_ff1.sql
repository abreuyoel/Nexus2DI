-- ============================================================================
-- ELIMINAR 3 PDV de Flora Foods de la Ruta FF1 (Panamá) — ELIMINA LA FILA
-- Base de datos: epran (producción)
-- Fecha: 2026-08-19
--
-- ⚠️ IMPORTANTE: Este script ELIMINA (DELETE) las filas de RUTA_PROGRAMACION
-- para que los 3 PDV queden SIN cliente asignado y SIN ruta FF1. El PDV NO se
-- borra del catálogo PUNTOS_INTERES1 — solo se quita su programación de la
-- ruta.
--
-- ⚠️ NOTA SOBRE id_cliente: en RUTA_PROGRAMACION la columna id_cliente es
-- NOT NULL y tiene FK a CLIENTES, por lo que NO se puede dejar "sin cliente"
-- (poner NULL). La única forma de "quitar el cliente asignado" es ELIMINAR la
-- fila de programación. Esta es la opción que elegiste.
--
-- Verificado: NO existe ninguna FK que apunte a RUTA_PROGRAMACION (0 filas en
-- sys.foreign_keys), así que el DELETE es seguro y no deja datos huérfanos.
--
-- Registros a eliminar (Ruta FF1 = id_ruta 1574, cuadrante "Panamá Metro",
-- cliente Flora Foods = id_cliente 69):
--   id_programacion 33594  -> SUP0001 "Super 99 Albrook"       (Lunes,   Flora Foods)
--   id_programacion 33600  -> SUP0002 "Super 99 Transístmica"  (Martes,  Flora Foods)
--   id_programacion 33602  -> RIB0003 "Riba Smith Transístmica"(Martes,  Flora Foods)
--
-- ❗ IRREVERSIBLE: una vez borradas, las filas no se recuperan. Los PDV
-- siguen en PUNTOS_INTERES1 y se pueden volver a programar, pero se perderá
-- la programación/día/prioridad actual. Si dudas, usa primero la versión
-- activa=0 (2026-08-19_desactivar_pdv_flora_foods_ruta_ff1_FIX.sql).
-- ============================================================================

-- 1) VERIFICACIÓN PREVIA: muestra las filas que se van a ELIMINAR
PRINT '=== FILAS A ELIMINAR (antes del DELETE) ===';
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

-- 2) ELIMINAR (DELETE) — SIN transacción: se confirma al instante
DELETE FROM RUTA_PROGRAMACION
WHERE id_programacion IN (33602, 33594, 33600)
  AND id_cliente = 69;   -- protección extra: solo toca registros de Flora Foods

-- 3) VERIFICACIÓN POSTERIOR: NO debe devolver filas (0 registros)
PRINT '=== FILAS RESTANTES (despues del DELETE — debe ser 0) ===';
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

-- 4) VERIFICACIÓN de que los PDV SIGUEN en el catálogo (no se borraron)
PRINT '=== LOS PDV SIGUEN EN CATALOGO PUNTOS_INTERES1 ===';
SELECT identificador, punto_de_interes, ciudad, departamento
FROM PUNTOS_INTERES1
WHERE identificador IN ('SUP0001','SUP0002','RIB0003');

-- Si la consulta 3 devuelve 0 filas y la consulta 4 devuelve los 3 PDV,
-- el cambio quedó APLICADO en producción. No necesitas hacer nada más.

-- ============================================================================
-- Para volver a asignarlos (recrear la programación), ejecuta SOLO esto:
--   INSERT INTO RUTA_PROGRAMACION (id_ruta, dia, id_punto_interes, id_cliente,
--                                  prioridad, activa, punto_interes)
--   VALUES
--     (1574, 'Lunes',   'SUP0001', 69, 'Media', 1, 'Super 99 Albrook'),
--     (1574, 'Martes',  'SUP0002', 69, 'Media', 1, 'Super 99 Transístmica'),
--     (1574, 'Martes',  'RIB0003', 69, 'Media', 1, 'Riba Smith Transístmica');
-- ============================================================================
