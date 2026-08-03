-- Alta de módulos/acciones nuevas en MODULOS para que Permisos controle de
-- verdad los módulos agregados en la sesión del 2026-08-02/03: Centro de
-- Mando Auditoría, Plan de Acción, SKU vs SKU, y las acciones que faltaban
-- en Frecuencias PDVs (ya existía como módulo pero sin hijos de acción,
-- a diferencia de Productos/Rutas/Puntos de Venta que sí las tienen).
-- Idempotente: todo con IF NOT EXISTS por clave.

-- ── Centro de Mando Auditoría (solo lectura, sin acciones propias) ──
IF NOT EXISTS (SELECT 1 FROM MODULOS WHERE clave = 'centro-mando-auditoria')
    INSERT INTO MODULOS (clave, nombre, id_padre, tipo, ruta, icono, orden, activo)
    VALUES ('centro-mando-auditoria', 'Centro de Mando Auditoría', NULL, 'modulo', '/centro-mando-auditoria', 'fact_check', 21, 1);

-- ── Plan de Acción ──
IF NOT EXISTS (SELECT 1 FROM MODULOS WHERE clave = 'plan-accion')
    INSERT INTO MODULOS (clave, nombre, id_padre, tipo, ruta, icono, orden, activo)
    VALUES ('plan-accion', 'Plan de Acción', NULL, 'modulo', '/plan-accion', 'assignment_late', 22, 1);

IF NOT EXISTS (SELECT 1 FROM MODULOS WHERE clave = 'plan-accion.recalcular')
    INSERT INTO MODULOS (clave, nombre, id_padre, tipo, orden, activo)
    SELECT 'plan-accion.recalcular', 'Recalcular ahora', id_modulo, 'accion', 1, 1
    FROM MODULOS WHERE clave = 'plan-accion';

IF NOT EXISTS (SELECT 1 FROM MODULOS WHERE clave = 'plan-accion.crear_ruta')
    INSERT INTO MODULOS (clave, nombre, id_padre, tipo, orden, activo)
    SELECT 'plan-accion.crear_ruta', 'Crear y asignar ruta BCK', id_modulo, 'accion', 2, 1
    FROM MODULOS WHERE clave = 'plan-accion';

-- ── SKU vs SKU ──
IF NOT EXISTS (SELECT 1 FROM MODULOS WHERE clave = 'sku-competencia')
    INSERT INTO MODULOS (clave, nombre, id_padre, tipo, ruta, icono, orden, activo)
    VALUES ('sku-competencia', 'SKU vs SKU', NULL, 'modulo', '/sku-competencia', 'compare_arrows', 81, 1);

IF NOT EXISTS (SELECT 1 FROM MODULOS WHERE clave = 'sku-competencia.crear')
    INSERT INTO MODULOS (clave, nombre, id_padre, tipo, orden, activo)
    SELECT 'sku-competencia.crear', 'Crear mapeo', id_modulo, 'accion', 1, 1
    FROM MODULOS WHERE clave = 'sku-competencia';

IF NOT EXISTS (SELECT 1 FROM MODULOS WHERE clave = 'sku-competencia.eliminar')
    INSERT INTO MODULOS (clave, nombre, id_padre, tipo, orden, activo)
    SELECT 'sku-competencia.eliminar', 'Eliminar mapeo', id_modulo, 'accion', 2, 1
    FROM MODULOS WHERE clave = 'sku-competencia';

-- ── Frecuencias PDVs: ya existía el módulo (id 45), le faltaban las acciones ──
IF NOT EXISTS (SELECT 1 FROM MODULOS WHERE clave = 'frecuencias-pdvs-cliente.crear')
    INSERT INTO MODULOS (clave, nombre, id_padre, tipo, orden, activo)
    SELECT 'frecuencias-pdvs-cliente.crear', 'Crear frecuencia', id_modulo, 'accion', 1, 1
    FROM MODULOS WHERE clave = 'frecuencias-pdvs-cliente';

IF NOT EXISTS (SELECT 1 FROM MODULOS WHERE clave = 'frecuencias-pdvs-cliente.editar')
    INSERT INTO MODULOS (clave, nombre, id_padre, tipo, orden, activo)
    SELECT 'frecuencias-pdvs-cliente.editar', 'Editar frecuencia', id_modulo, 'accion', 2, 1
    FROM MODULOS WHERE clave = 'frecuencias-pdvs-cliente';

IF NOT EXISTS (SELECT 1 FROM MODULOS WHERE clave = 'frecuencias-pdvs-cliente.eliminar')
    INSERT INTO MODULOS (clave, nombre, id_padre, tipo, orden, activo)
    SELECT 'frecuencias-pdvs-cliente.eliminar', 'Eliminar frecuencia', id_modulo, 'accion', 3, 1
    FROM MODULOS WHERE clave = 'frecuencias-pdvs-cliente';

IF NOT EXISTS (SELECT 1 FROM MODULOS WHERE clave = 'frecuencias-pdvs-cliente.carga_masiva')
    INSERT INTO MODULOS (clave, nombre, id_padre, tipo, orden, activo)
    SELECT 'frecuencias-pdvs-cliente.carga_masiva', 'Carga masiva', id_modulo, 'accion', 4, 1
    FROM MODULOS WHERE clave = 'frecuencias-pdvs-cliente';
