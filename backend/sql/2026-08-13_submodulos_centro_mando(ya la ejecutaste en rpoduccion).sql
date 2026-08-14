-- ── Sub-módulos del Centro de Mando en la tabla MODULOS ──

-- 1. Hijo directo: Activaciones
IF NOT EXISTS (SELECT 1 FROM MODULOS WHERE clave = 'centro-mando.activaciones')
BEGIN
    INSERT INTO MODULOS (clave, nombre, id_padre, tipo, orden, activo)
    SELECT 'centro-mando.activaciones', 'Activaciones', id_modulo, 'submodulo', 1, 1
    FROM MODULOS WHERE clave = 'centro-mando';
END;

-- 2. Hijo directo: Visitas
IF NOT EXISTS (SELECT 1 FROM MODULOS WHERE clave = 'centro-mando.visitas')
BEGIN
    INSERT INTO MODULOS (clave, nombre, id_padre, tipo, orden, activo)
    SELECT 'centro-mando.visitas', 'Visitas', id_modulo, 'submodulo', 2, 1
    FROM MODULOS WHERE clave = 'centro-mando';
END;

-- 3. Nietos de Activaciones:
-- Dashboard
IF NOT EXISTS (SELECT 1 FROM MODULOS WHERE clave = 'centro-mando.activaciones.dashboard')
BEGIN
    INSERT INTO MODULOS (clave, nombre, id_padre, tipo, orden, activo)
    SELECT 'centro-mando.activaciones.dashboard', 'Dashboard', id_modulo, 'accion', 1, 1
    FROM MODULOS WHERE clave = 'centro-mando.activaciones';
END;

-- Gestión del Día
IF NOT EXISTS (SELECT 1 FROM MODULOS WHERE clave = 'centro-mando.activaciones.gestion_dia')
BEGIN
    INSERT INTO MODULOS (clave, nombre, id_padre, tipo, orden, activo)
    SELECT 'centro-mando.activaciones.gestion_dia', 'Gestión del Día', id_modulo, 'accion', 2, 1
    FROM MODULOS WHERE clave = 'centro-mando.activaciones';
END;

-- Pendientes
IF NOT EXISTS (SELECT 1 FROM MODULOS WHERE clave = 'centro-mando.activaciones.pendientes')
BEGIN
    INSERT INTO MODULOS (clave, nombre, id_padre, tipo, orden, activo)
    SELECT 'centro-mando.activaciones.pendientes', 'Pendientes', id_modulo, 'accion', 3, 1
    FROM MODULOS WHERE clave = 'centro-mando.activaciones';
END;

-- Horas Trabajadas (Restringido para clientes)
IF NOT EXISTS (SELECT 1 FROM MODULOS WHERE clave = 'centro-mando.activaciones.horas_trabajadas')
BEGIN
    INSERT INTO MODULOS (clave, nombre, id_padre, tipo, orden, activo)
    SELECT 'centro-mando.activaciones.horas_trabajadas', 'Horas Trabajadas', id_modulo, 'accion', 4, 1
    FROM MODULOS WHERE clave = 'centro-mando.activaciones';
END;
