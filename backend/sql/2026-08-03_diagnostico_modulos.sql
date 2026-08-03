-- Contenido completo de MODULOS (jerarquía padre/hijo) para poder rediseñar
-- la pantalla de Permisos: qué existe hoy, qué está obsoleto (ya no tiene
-- ruta real en el sidebar), y qué falta (módulos nuevos de esta sesión:
-- Plan de Acción, SKU vs SKU, Centro de Mando Auditoría, Frecuencias PDVs).

SELECT id_modulo, clave, nombre, id_padre, tipo, ruta, icono, orden, activo
FROM MODULOS
ORDER BY ISNULL(id_padre, id_modulo), id_padre, orden, id_modulo;
