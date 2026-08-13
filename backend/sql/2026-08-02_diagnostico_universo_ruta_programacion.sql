-- ¿Cuántas combinaciones (ruta, PDV, cliente) distintas están activa=1 en
-- RUTA_PROGRAMACION? Esto es el "universo" real que usa Plan de Acción --
-- si es un número mucho más grande que el ritmo real de visitas semanales
-- (~1620/semana según el diagnóstico anterior), o el equipo está genuinamente
-- desbordado, o hay filas activa=1 que en la práctica ya no se visitan
-- (clientes/rutas dados de baja sin desactivar la programación).

SELECT COUNT(*) AS combinaciones_distintas
FROM (
    SELECT DISTINCT id_ruta, id_punto_interes, id_cliente
    FROM RUTA_PROGRAMACION
    WHERE activa = 1
) x;

-- De esas combinaciones, ¿cuántas tuvieron AL MENOS una visita (cualquier
-- estado de foto) en los últimos 31 días? Si es un número bajo comparado
-- con el total de arriba, confirma que gran parte del universo no se está
-- tocando en absoluto -- no es que las fotos no se aprueben, es que
-- directamente no hay visita reciente.
SELECT COUNT(DISTINCT CONCAT(rp.id_ruta, '|', rp.id_punto_interes, '|', rp.id_cliente)) AS combinaciones_con_alguna_visita_31d
FROM RUTA_PROGRAMACION rp
WHERE rp.activa = 1
  AND EXISTS (
      SELECT 1 FROM VISITAS_MERCADERISTA vm
      WHERE vm.identificador_punto_interes = rp.id_punto_interes
        AND vm.id_cliente = rp.id_cliente
        AND vm.fecha_visita >= DATEADD(day, -31, CAST(GETDATE() AS DATE))
  );
