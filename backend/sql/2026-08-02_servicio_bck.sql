-- Fase 3 de Plan de Acción va a crear rutas de respaldo ("BCK") para cubrir
-- visitas pendientes agrupadas por cercanía. Crear una ruta vía
-- POST /api/routes/ exige que exista un SERVICIOS con prefijo seteado
-- (routes/rutas.py::_get_servicio_prefijo) -- hoy no hay ninguno para backup.

IF NOT EXISTS (SELECT 1 FROM SERVICIOS WHERE prefijo = 'BCK')
BEGIN
    INSERT INTO SERVICIOS (nombre, prefijo, activo)
    VALUES ('Backup', 'BCK', 1);
END
