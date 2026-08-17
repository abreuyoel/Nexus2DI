-- Cataloga universidad_graduacion (roadmap: dropdown buscable + "Otro" en
-- web y APK, en vez de texto libre). Mismo patrón ya usado para
-- especialidad/estado/ciudad: tabla CATALOGOS_ENCUESTADOR, tipo='universidad'.
--
-- Dos fuentes, sin duplicar:
--   1) Lista curada de universidades venezolanas conocidas por formar médicos.
--   2) Backfill de los valores reales que YA existen en medicos.universidad_graduacion
--      (dato histórico, texto libre) -- para no perder ningún registro real
--      al pasar el campo a catálogo cerrado-con-opción-de-agregar.

INSERT INTO CATALOGOS_ENCUESTADOR (tipo, nombre)
SELECT 'universidad', v.nombre
FROM (VALUES
    ('Universidad Central de Venezuela (UCV)'),
    ('Universidad del Zulia (LUZ)'),
    ('Universidad de Los Andes (ULA)'),
    ('Universidad de Oriente (UDO)'),
    ('Universidad Centroccidental Lisandro Alvarado (UCLA)'),
    ('Universidad Católica Andrés Bello (UCAB)'),
    ('Universidad de Carabobo (UC)'),
    ('Universidad Nacional Experimental Francisco de Miranda (UNEFM)'),
    ('Universidad Nacional Experimental Rómulo Gallegos (UNERG)'),
    ('Universidad Metropolitana (UNIMET)'),
    ('Universidad Rafael Urdaneta (URU)'),
    ('Universidad José María Vargas (UJMV)'),
    ('Universidad Santa María (USM)'),
    ('Universidad Nororiental Privada Gran Mariscal de Ayacucho (UGMA)'),
    ('Universidad Arturo Michelena (UAM)'),
    ('Universidad Alejandro de Humboldt (UAH)'),
    ('Universidad Bicentenaria de Aragua (UBA)'),
    ('Universidad Fermín Toro'),
    ('Universidad Yacambú'),
    ('Universidad Nacional Experimental de los Llanos Occidentales Ezequiel Zamora (UNELLEZ)'),
    ('Universidad de Ciencias Médicas de La Habana'),
    ('Escuela Latinoamericana de Medicina (ELAM, Cuba)'),
    ('Otra')
) AS v(nombre)
WHERE NOT EXISTS (
    SELECT 1 FROM CATALOGOS_ENCUESTADOR c WHERE c.tipo = 'universidad' AND c.nombre = v.nombre
);

-- Backfill: valores reales ya cargados que no estén en la lista curada de
-- arriba -- así ningún médico existente "pierde" su universidad al pasar el
-- campo a catálogo. Las dos columnas (universidad_graduacion y
-- segunda_universidad_graduacion) alimentan el MISMO catálogo -- la app usa
-- una sola lista de universidades para ambos selectores -- así que se unen
-- acá (UNION ya deduplica solapamientos entre las dos columnas).
INSERT INTO CATALOGOS_ENCUESTADOR (tipo, nombre)
SELECT 'universidad', m.uni
FROM (
    SELECT DISTINCT LTRIM(RTRIM(universidad_graduacion)) AS uni
    FROM medicos
    WHERE universidad_graduacion IS NOT NULL AND LTRIM(RTRIM(universidad_graduacion)) <> ''
    UNION
    SELECT DISTINCT LTRIM(RTRIM(segunda_universidad_graduacion)) AS uni
    FROM medicos
    WHERE segunda_universidad_graduacion IS NOT NULL AND LTRIM(RTRIM(segunda_universidad_graduacion)) <> ''
) m
WHERE NOT EXISTS (
    SELECT 1 FROM CATALOGOS_ENCUESTADOR c WHERE c.tipo = 'universidad' AND c.nombre = m.uni
);
