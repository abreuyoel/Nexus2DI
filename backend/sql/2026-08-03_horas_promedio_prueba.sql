-- Datos de PRUEBA para HORAS_PROMEDIO_EJECUCION -- desbloquea la matemática
-- de capacidad de Plan de Acción (Fase 3) mientras el usuario carga los
-- valores reales por cliente/tipo de negocio en la pantalla "Horas Promedio
-- Ejecución". 45 minutos es un placeholder genérico, NO un dato real -- hay
-- que revisarlo/corregirlo desde esa pantalla.
--
-- Join confirmado con datos reales (2026-08-02): jerarquia_nivel_2 es la
-- columna que matchea contra CAT_TIPO_NEGOCIO.nombre (5098/5116 PDVs),
-- no jerarquia_nivel_2_2 como decía el comentario del modelo.
--
-- Solo inserta combinaciones (cliente, tipo_negocio) que hoy tienen
-- programación activa Y que todavía no tengan una fila cargada -- si el
-- usuario ya cargó algo real para alguna combinación, este script no la pisa.

INSERT INTO HORAS_PROMEDIO_EJECUCION (id_cliente, id_tipo_negocio, minutos_promedio, fecha_creado)
SELECT DISTINCT rp.id_cliente, ctn.id, 45, GETDATE()
FROM RUTA_PROGRAMACION rp
JOIN PUNTOS_INTERES1 pi ON pi.identificador = rp.id_punto_interes
JOIN CAT_TIPO_NEGOCIO ctn ON ctn.nombre = pi.jerarquia_nivel_2
WHERE rp.activa = 1
  AND rp.id_cliente IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM HORAS_PROMEDIO_EJECUCION h
      WHERE h.id_cliente = rp.id_cliente AND h.id_tipo_negocio = ctn.id
  );
