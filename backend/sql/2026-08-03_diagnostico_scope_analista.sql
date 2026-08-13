-- Diagnóstico: ¿por qué ymontenegro (analista) puede estar viendo datos de
-- clientes que no le corresponden en la pantalla "Data"? El código de
-- app/routes/client_data.py YA filtra por analista (analistas_rutas ->
-- RUTA_PROGRAMACION), pero ese filtro se salta por completo si
-- USUARIOS.id_perfil no está seteado o no matchea con ningún ANALISTAS.id_analista
-- con rutas asignadas -- en ese caso el sistema, a propósito, no filtra nada
-- (falla "abierto" en vez de "cerrado").

-- 1) ¿Tiene id_perfil seteado, y matchea con una fila real de ANALISTAS?
SELECT u.id_usuario, u.username, u.id_rol, u.id_perfil, a.id_analista, a.nombre_analista
FROM USUARIOS u
LEFT JOIN ANALISTAS a ON a.id_analista = u.id_perfil
WHERE u.username = 'ymontenegro';

-- 2) Si tiene id_perfil válido, ¿tiene rutas asignadas en analistas_rutas?
--    (reemplazar :id_analista por el id_analista que devuelva la consulta de arriba)
SELECT ar.id_ruta, rn.ruta
FROM analistas_rutas ar
JOIN RUTAS_NUEVAS rn ON rn.id_ruta = ar.id_ruta
WHERE ar.id_analista = (SELECT id_perfil FROM USUARIOS WHERE username = 'ymontenegro');
