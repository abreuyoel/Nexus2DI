-- Solo lectura -- investiga qué del respaldo offline de Henry
-- (respaldo_encuestador_2026-08-14.json) ya está en la base y qué falta,
-- antes de armar el INSERT de recuperación. No modifica nada.

-- 1) Encontrar a Henry
SELECT id, username, nombre, id_rol, id_perfil
FROM USUARIOS
WHERE username LIKE '%henry%' OR nombre LIKE '%henry%';

-- 2) Médicos del respaldo: los 5 con cédula real, por id_medico_externo
--    (clave más confiable, no depende de acentos/encoding)
SELECT id_medico, id_medico_externo, apellido1, apellido2, nombre1, telefono, fecha_registro
FROM medicos
WHERE id_medico_externo IN ('13978726','8524788','9097807','20663167','13551809');

-- 3) Médicos del respaldo SIN cédula (4) -- buscados por teléfono, que es
--    exacto en el JSON y no se corrompe con encoding
SELECT id_medico, id_medico_externo, apellido1, apellido2, nombre1, telefono, fecha_registro
FROM medicos
WHERE telefono IN ('04164279655','04242529480','04141109879');
-- (Roberto Penott Martinez, tel 04143210516, ya cae en la lista del punto 2
--  si existe, porque en ese caso también aparecería con teléfono -- si no
--  aparece en ninguna de las dos consultas, no existe todavía)

-- 4) La encuesta #78 (real, ya sincronizada antes de este respaldo) --
--    a qué jornada/centro pertenece y si de verdad sigue existiendo
SELECT * FROM encuestas_centro WHERE id_encuesta = 78;

-- 5) Jornadas de Henry en la ventana del respaldo (12 al 15 de agosto)
SELECT id_jornada, id_usuario, fecha_inicio, fecha_fin, estado, ciudad, estado_geo
FROM JORNADAS_ENCUESTADOR
WHERE id_usuario = (SELECT id FROM USUARIOS WHERE username LIKE '%henry%' OR nombre LIKE '%henry%')
  AND fecha_inicio BETWEEN '2026-08-12' AND '2026-08-15'
ORDER BY id_jornada;

-- 6) Encuestas (centro) de Henry en la misma ventana -- para ver cuáles de
--    las 11 aperturas del respaldo (centros 46, 6, 31, 49, 8, 50) ya están
SELECT id_encuesta, id_usuario, id_centro, fecha_verificacion, id_jornada, estado, creado_en
FROM encuestas_centro
WHERE id_usuario = (SELECT id FROM USUARIOS WHERE username LIKE '%henry%' OR nombre LIKE '%henry%')
  AND fecha_verificacion BETWEEN '2026-08-12' AND '2026-08-15'
ORDER BY id_encuesta;

-- 7) Los centros que aparecen en el respaldo -- confirmar que existen y ver
--    sus nombres (el respaldo solo trae id_centro numérico)
SELECT id_centro, nombre_centro, ciudad, estado
FROM centros_salud
WHERE id_centro IN (46, 6, 31, 49, 8, 50);
