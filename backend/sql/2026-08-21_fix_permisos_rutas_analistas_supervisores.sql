-- Fix: analistas y supervisores no podían crear/editar/eliminar PDVs en
-- RUTA_PROGRAMACION pese a que se les "dio acceso" desde el panel de Permisos.
--
-- Causas encontradas (21 ago 2026):
-- 1) El default de permisos de analista (ROLE_DEFAULT_PERMISSIONS en
--    default_permissions.py) daba routes.write=True pero NUNCA routes.delete
--    -- cualquier analista con esa fila ya seedeada quedaba con
--    can_delete=False EXPLICITO, lo cual bloquea el fallback por rol que de
--    otro modo le habría dado acceso (require_permission: si existe la fila
--    para el módulo, manda ella sola, no cae al fallback de rol).
-- 2) Ningún supervisor (id_rol=6) tenía NINGUNA fila para module='routes' --
--    ese rol no tiene fallback automático en require_permission (a
--    diferencia de analyst/auditor), así que sin fila quedan bloqueados
--    para crear/editar/eliminar, no solo para eliminar.
-- 3) La causa raíz de por qué "se dio acceso pero no funcionó": el panel de
--    Permisos muestra sub-ítems "Crear ruta"/"Editar ruta"/"Eliminar ruta"
--    (MODULOS.clave = routes.crear/routes.editar/routes.eliminar) que
--    parecen ser el control real, pero NO están referenciados en ningún
--    lado del código (ni backend ni frontend) -- el único control real es
--    el checkbox "Eliminar"/"Modificar" de la fila padre "Rutas"
--    (module='routes'). Se desactivan acá para no seguir confundiendo.
--
-- Corre esto en epran (prod) y epran-qa.

-- 1) Analistas: normalizar can_read/write/delete=1 en filas 'routes' YA
--    existentes (las que faltan se crean solas la próxima vez que ese
--    usuario dispare async_seed_default_permissions, o via fallback ya que
--    ahora sí tienen esa fila completa).
UPDATE up
SET up.can_read = 1, up.can_write = 1, up.can_delete = 1
FROM usuario_permisos up
JOIN USUARIOS u ON u.id_usuario = up.id_usuario
WHERE up.module = 'routes' AND u.id_rol = 2;

-- 2) Supervisores activos: crear la fila 'routes' que no existía para
--    ninguno (solo si no existe ya, por si alguno la tiene desde antes).
INSERT INTO usuario_permisos (id_usuario, module, can_read, can_write, can_delete, can_see_all)
SELECT u.id_usuario, 'routes', 1, 1, 1, 0
FROM USUARIOS u
WHERE u.id_rol = 6 AND u.activo = 1
  AND NOT EXISTS (
    SELECT 1 FROM usuario_permisos up2
    WHERE up2.id_usuario = u.id_usuario AND up2.module = 'routes'
  );

-- 3) Desactivar los sub-módulos decorativos que no hacen nada, para que
--    dejen de aparecer en el panel de Permisos y no vuelvan a confundir.
UPDATE MODULOS SET activo = 0
WHERE clave IN ('routes.crear', 'routes.editar', 'routes.eliminar');
