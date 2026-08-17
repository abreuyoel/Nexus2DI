-- Normaliza universidades "gemelas" en el catálogo (tipo='universidad'):
-- el backfill de 2026-08-16_seed_catalogo_universidad.sql matcheaba por
-- texto EXACTO, así que el mismo texto real sin sigla (ej. "Universidad
-- Central de Venezuela") y la versión curada con sigla (ej. "Universidad
-- Central de Venezuela (UCV)") quedaron como dos filas distintas -- el
-- selector de la app las muestra como opciones separadas para la misma
-- institución.
--
-- Redirige los médicos que tienen la versión sin sigla (en cualquiera de
-- las dos columnas -- comparten el mismo catálogo) al texto curado, y
-- después borra la fila duplicada del catálogo. Idempotente: si ya no hay
-- ningún médico con la versión sin sigla, el UPDATE no afecta filas y el
-- DELETE de esa fila del catálogo igual corre (por eso el orden importa:
-- primero migrar los médicos, recién después borrar del catálogo).

DECLARE @map TABLE (bare NVARCHAR(200), curada NVARCHAR(200));
INSERT INTO @map (bare, curada) VALUES
    ('Universidad Bicentenaria de Aragua', 'Universidad Bicentenaria de Aragua (UBA)'),
    ('Universidad Central de Venezuela', 'Universidad Central de Venezuela (UCV)'),
    ('Universidad de Carabobo', 'Universidad de Carabobo (UC)'),
    ('Universidad de Los Andes', 'Universidad de Los Andes (ULA)'),
    ('Universidad de Oriente', 'Universidad de Oriente (UDO)'),
    ('Universidad del Zulia', 'Universidad del Zulia (LUZ)'),
    ('Universidad Nacional Experimental Francisco de Miranda', 'Universidad Nacional Experimental Francisco de Miranda (UNEFM)'),
    ('Universidad Nacional Experimental Rómulo Gallegos', 'Universidad Nacional Experimental Rómulo Gallegos (UNERG)'),
    ('Universidad Santa María', 'Universidad Santa María (USM)');

UPDATE m
SET m.universidad_graduacion = map.curada
FROM medicos m
JOIN @map map ON LTRIM(RTRIM(m.universidad_graduacion)) = map.bare;

UPDATE m
SET m.segunda_universidad_graduacion = map.curada
FROM medicos m
JOIN @map map ON LTRIM(RTRIM(m.segunda_universidad_graduacion)) = map.bare;

DELETE c
FROM CATALOGOS_ENCUESTADOR c
JOIN @map map ON c.tipo = 'universidad' AND c.nombre = map.bare;
