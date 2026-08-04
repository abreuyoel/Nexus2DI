-- Diagnóstico antes de tocar el PDV duplicado "Farmatodo Susana"
-- (APZ0020 vs FTD0067). Cuenta referencias a cada identificador en TODAS
-- las tablas que pueden apuntar a PUNTOS_INTERES1.identificador, para saber
-- qué hay que reasignar antes de poder borrar APZ0020 con seguridad.
-- Nada de esto escribe -- son solo SELECTs.

-- 1) Confirmar que ambos PDV existen y ver su info básica
SELECT identificador, punto_de_interes, Direccion, departamento, ciudad,
       jerarquia_nivel_2, jerarquia_nivel_2_2, clasificacion_de_canal
FROM PUNTOS_INTERES1
WHERE identificador IN ('APZ0020', 'FTD0067');

-- 2) Visitas registradas (la tabla más importante -- si tiene historial real,
--    hay que reasignarlo, no perderlo)
SELECT identificador_punto_interes, COUNT(*) AS visitas, MIN(fecha_visita) AS primera, MAX(fecha_visita) AS ultima
FROM VISITAS_MERCADERISTA
WHERE identificador_punto_interes IN ('APZ0020', 'FTD0067')
GROUP BY identificador_punto_interes;

-- 3) Programación de rutas activa
SELECT id_punto_interes, id_ruta, id_cliente, dia, activa, prioridad
FROM RUTA_PROGRAMACION
WHERE id_punto_interes IN ('APZ0020', 'FTD0067')
ORDER BY id_punto_interes, id_ruta;

-- 4) Frecuencias por cliente
SELECT id_punto_interes, id_cliente, frecuencia_semanal, activo
FROM FRECUENCIAS_PDVS_CLIENTE
WHERE id_punto_interes IN ('APZ0020', 'FTD0067');

-- 5) Balances de inventario cargados
SELECT identificador_pdv, COUNT(*) AS balances, MIN(fecha_balance) AS primera, MAX(fecha_balance) AS ultima
FROM BALANCES_TOTALES
WHERE identificador_pdv IN ('APZ0020', 'FTD0067')
GROUP BY identificador_pdv;

-- 6) Activaciones (tabla vieja, puede no tener nada, pero se revisa igual)
SELECT identificador_punto_interes, COUNT(*) AS filas
FROM ACTIVACIONES
WHERE identificador_punto_interes IN ('APZ0020', 'FTD0067')
GROUP BY identificador_punto_interes;

-- 7) Conversaciones de chat ancladas al PDV
SELECT id_punto_interes, COUNT(*) AS conversaciones
FROM CHAT_CONVERSACIONES
WHERE id_punto_interes IN ('APZ0020', 'FTD0067')
GROUP BY id_punto_interes;
