-- =============================================================================
-- Script: Inicialización, Homologación y Estandarización de Catálogos Encuestador
-- Tablas involucradas: CATALOGOS_ENCUESTADOR y medicos
-- Fecha: 2026-08-14
-- Descripción:
--   1. Asegura columnas de auditoría en CATALOGOS_ENCUESTADOR.
--   2. Inserta el catálogo oficial estandarizado completo.
--   3. HOMOLOGA Y ACTUALIZA la tabla MEDICOS (convierte 'UCV' -> 'Universidad Central de Venezuela (UCV)', 
--      'UDO' -> 'Universidad de Oriente (UDO)', 'PEDIATRA' -> 'Pediatría y Puericultura', etc.).
--   4. Normaliza mayúsculas, minúsculas y espacios en estados y ciudades de médicos.
--   5. Limpia siglas antiguas o registros de prueba en CATALOGOS_ENCUESTADOR que ya fueron migrados.
--   6. Muestra resumen final del estado de los datos.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 0. Garantizar columnas de auditoría en CATALOGOS_ENCUESTADOR
-- -----------------------------------------------------------------------------
IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('CATALOGOS_ENCUESTADOR') AND name = 'creado_por')
BEGIN
    ALTER TABLE CATALOGOS_ENCUESTADOR ADD creado_por VARCHAR(150) NULL;
END;

IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('CATALOGOS_ENCUESTADOR') AND name = 'creado_en')
BEGIN
    ALTER TABLE CATALOGOS_ENCUESTADOR ADD creado_en DATETIME NULL DEFAULT GETDATE();
END;

IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('CATALOGOS_ENCUESTADOR') AND name = 'modificado_en')
BEGIN
    ALTER TABLE CATALOGOS_ENCUESTADOR ADD modificado_en DATETIME NULL;
END;
GO

-- -----------------------------------------------------------------------------
-- 1. Insertar Catálogo Oficial de UNIVERSIDADES
-- -----------------------------------------------------------------------------
INSERT INTO CATALOGOS_ENCUESTADOR (tipo, nombre, creado_por, creado_en)
SELECT 'universidad', T.val, 'Sistema', GETDATE()
FROM (VALUES 
    ('Universidad Central de Venezuela (UCV)'),
    ('Universidad de Los Andes (ULA)'),
    ('Universidad del Zulia (LUZ)'),
    ('Universidad de Carabobo (UC)'),
    ('Universidad de Oriente (UDO)'),
    ('Universidad Centroccidental Lisandro Alvarado (UCLA)'),
    ('Universidad Nacional Experimental Francisco de Miranda (UNEFM)'),
    ('Universidad Nacional Experimental Rómulo Gallegos (UNERG)'),
    ('Universidad Católica Andrés Bello (UCAB)'),
    ('Universidad Santa María (USM)'),
    ('Escuela Latinoamericana de Medicina (ELAM)'),
    ('Universidad Nacional Experimental de los Llanos Ezequiel Zamora (UNELLEZ)'),
    ('Universidad Nacional Experimental de las Fuerzas Armadas (UNEFA)'),
    ('Universidad del Táchira (UNET)'),
    ('Universidad Rafael Belloso Chacín (URBE)'),
    ('Universidad Metropolitana (UNIMET)'),
    ('Universidad José Antonio Páez (UJAP)'),
    ('Universidad Arturo Michelena (UAM)'),
    ('Universidad Nororiental Privada Gran Mariscal de Ayacucho (UGMA)'),
    ('Universidad de Ciencias de la Salud Hugo Chávez Frías (UCS)'),
    ('Universidad Extranjera / Revalida')
) AS T(val)
WHERE NOT EXISTS (
    SELECT 1 FROM CATALOGOS_ENCUESTADOR 
    WHERE tipo = 'universidad' AND nombre = T.val
);
GO

-- -----------------------------------------------------------------------------
-- 2. Insertar Catálogo Oficial de ESPECIALIDADES MÉDICAS
-- -----------------------------------------------------------------------------
INSERT INTO CATALOGOS_ENCUESTADOR (tipo, nombre, creado_por, creado_en)
SELECT 'especialidad', T.val, 'Sistema', GETDATE()
FROM (VALUES 
    ('Anestesiología'),
    ('Cardiología'),
    ('Cirugía General'),
    ('Cirugía Pediátrica'),
    ('Cirugía Plástica y Reconstructiva'),
    ('Dermatología'),
    ('Endocrinología'),
    ('Fisiatría y Rehabilitación'),
    ('Gastroenterología'),
    ('Geriatría'),
    ('Ginecología y Obstetricia'),
    ('Hematología'),
    ('Infectología'),
    ('Inmunología y Alergología'),
    ('Medicina Crítica y Terapia Intensiva'),
    ('Medicina de Emergencia'),
    ('Medicina Familiar'),
    ('Medicina General'),
    ('Medicina Interna'),
    ('Medicina Ocupacional'),
    ('Nefrología'),
    ('Neumonología'),
    ('Neurocirugía'),
    ('Neurología'),
    ('Nutriología y Dietética'),
    ('Odontología General'),
    ('Oftalmología'),
    ('Oncología Médica'),
    ('Oncología Radioterápica'),
    ('Ortopedia y Traumatología'),
    ('Otorrinolaringología'),
    ('Patología y Anatomía Patológica'),
    ('Pediatría y Puericultura'),
    ('Psicología Clínica'),
    ('Psiquiatría'),
    ('Radiología e Imagenología'),
    ('Reumatología'),
    ('Toxicología'),
    ('Urología')
) AS T(val)
WHERE NOT EXISTS (
    SELECT 1 FROM CATALOGOS_ENCUESTADOR 
    WHERE tipo = 'especialidad' AND nombre = T.val
);
GO

-- -----------------------------------------------------------------------------
-- 3. Insertar Catálogo Oficial de SUB-ESPECIALIDADES MÉDICAS
-- -----------------------------------------------------------------------------
INSERT INTO CATALOGOS_ENCUESTADOR (tipo, nombre, creado_por, creado_en)
SELECT 'subespecialidad', T.val, 'Sistema', GETDATE()
FROM (VALUES 
    ('Cardiología Intervencionista / Hemodinamia'),
    ('Cardiología Pediátrica'),
    ('Cirugía Bariátrica y Metabólica'),
    ('Cirugía Cardiovascular'),
    ('Cirugía de Columna y Mano'),
    ('Cirugía de Cabeza y Cuello'),
    ('Cirugía Laparoscópica y Mínima Invasión'),
    ('Cirugía Oncológica'),
    ('Cirugía Pediátrica'),
    ('Cirugía Plástica Facial'),
    ('Cirugía Plástica y Reconstructiva'),
    ('Cirugía Vascular Periférica'),
    ('Coloproctología'),
    ('Dermatología Estética'),
    ('Dermatología Pediátrica'),
    ('Ecografía / Ecosonografía Integral'),
    ('Electrofisiología Cardíaca'),
    ('Endocrinología Pediátrica'),
    ('Endodoncia'),
    ('Gastroenterología Pediátrica'),
    ('Ginecología Infanto-Juvenil'),
    ('Ginecología Oncológica'),
    ('Hematología Pediátrica'),
    ('Hepatología'),
    ('Implantología Oral'),
    ('Infectología Pediátrica'),
    ('Mastología / Senología'),
    ('Medicina Crítica Pediátrica y Neonatal'),
    ('Medicina del Dolor y Cuidados Paliativos'),
    ('Medicina Fetal y Perinatología'),
    ('Medicina Materno Fetal'),
    ('Nefrología Pediátrica'),
    ('Neonatología'),
    ('Neumonología Pediátrica'),
    ('Neurocirugía Pediátrica y Vascular'),
    ('Neurofisiología Clínica'),
    ('Neurología Pediátrica'),
    ('Nutrición Clínica y Pediátrica'),
    ('Odontopediatría'),
    ('Oftalmología Pediátrica y Estrabismo'),
    ('Oncología Médica'),
    ('Oncología Pediátrica'),
    ('Ortodoncia y Ortopedia Maxilofacial'),
    ('Periodoncia'),
    ('Psicoanálisis y Terapia Familiar'),
    ('Psiquiatría Infantil y de la Adolescencia'),
    ('Radiología Intervencionista'),
    ('Reproducción Humana y Fertilidad'),
    ('Resonancia Magnética y Tomografía'),
    ('Reumatología Pediátrica'),
    ('Sexología Médica'),
    ('Traumatología Deportiva y Artroscopia'),
    ('Traumatología y Ortopedia Infantil'),
    ('Urología Pediátrica y Ginecológica')
) AS T(val)
WHERE NOT EXISTS (
    SELECT 1 FROM CATALOGOS_ENCUESTADOR 
    WHERE tipo = 'subespecialidad' AND nombre = T.val
);
GO

-- -----------------------------------------------------------------------------
-- 4. Insertar Catálogo Oficial de ESTADOS Y CIUDADES
-- -----------------------------------------------------------------------------
INSERT INTO CATALOGOS_ENCUESTADOR (tipo, nombre, creado_por, creado_en)
SELECT 'estado', T.val, 'Sistema', GETDATE()
FROM (VALUES 
    ('Amazonas'), ('Anzoátegui'), ('Apure'), ('Aragua'), ('Barinas'),
    ('Bolívar'), ('Carabobo'), ('Cojedes'), ('Delta Amacuro'), ('Distrito Capital'),
    ('Falcón'), ('Guárico'), ('Lara'), ('Mérida'), ('Miranda'),
    ('Monagas'), ('Nueva Esparta'), ('Portuguesa'), ('Sucre'), ('Táchira'),
    ('Trujillo'), ('Vargas (La Guaira)'), ('Yaracuy'), ('Zulia'), ('Dependencias Federales')
) AS T(val)
WHERE NOT EXISTS (
    SELECT 1 FROM CATALOGOS_ENCUESTADOR 
    WHERE tipo = 'estado' AND nombre = T.val
);

INSERT INTO CATALOGOS_ENCUESTADOR (tipo, nombre, creado_por, creado_en)
SELECT 'ciudad', T.val, 'Sistema', GETDATE()
FROM (VALUES 
    ('Caracas'), ('Maracaibo'), ('Valencia'), ('Barquisimeto'), ('Maracay'),
    ('Ciudad Guayana (Puerto Ordaz / San Félix)'), ('Barcelona'), ('Maturín'),
    ('Puerto La Cruz'), ('San Cristóbal'), ('Mérida'), ('Ciudad Bolívar'),
    ('Cumaná'), ('Barinas'), ('Cabimas'), ('Punto Fijo'), ('Coro'),
    ('Guatire'), ('Guarenas'), ('Los Teques'), ('San Felipe'), ('San Juan de los Morros'),
    ('San Fernando de Apure'), ('Carora'), ('El Tigre'), ('Acarigua / Araure'),
    ('Guanare'), ('Valera'), ('La Guaira'), ('Porlamar (Isla de Margarita)'),
    ('Carúpano'), ('Tucupita'), ('Puerto Ayacucho'), ('Charallave'), ('Cúa'),
    ('Ocumare del Tuy'), ('Boconó'), ('Tinaquillo'), ('San Carlos'), ('Calabozo'),
    ('Valle de la Pascua'), ('Anaco')
) AS T(val)
WHERE NOT EXISTS (
    SELECT 1 FROM CATALOGOS_ENCUESTADOR 
    WHERE tipo = 'ciudad' AND nombre = T.val
);
GO

-- =============================================================================
-- 5. HOMOLOGACIÓN Y EMPAREJAMIENTO DE LA TABLA MEDICOS (ACTUALIZACIÓN EN CASCADA)
-- =============================================================================

-- A) Homologar UNIVERSIDADES en medicos
UPDATE medicos
SET universidad_graduacion = 'Universidad Central de Venezuela (UCV)'
WHERE RTRIM(LTRIM(universidad_graduacion)) IN ('UCV', 'ucv', 'uxv', 'Universidad Central de Venezuela');

UPDATE medicos
SET universidad_graduacion = 'Universidad de Oriente (UDO)'
WHERE RTRIM(LTRIM(universidad_graduacion)) IN ('UDO', 'udo', 'Universidad de Oriente');

UPDATE medicos
SET universidad_graduacion = 'Universidad del Zulia (LUZ)'
WHERE RTRIM(LTRIM(universidad_graduacion)) IN ('LUZ', 'luz', 'Universidad del Zulia');

UPDATE medicos
SET universidad_graduacion = 'Universidad de Los Andes (ULA)'
WHERE RTRIM(LTRIM(universidad_graduacion)) IN ('ULA', 'ula', 'Universidad de Los Andes');

UPDATE medicos
SET universidad_graduacion = 'Universidad de Carabobo (UC)'
WHERE RTRIM(LTRIM(universidad_graduacion)) IN ('UC', 'uc', 'Universidad de Carabobo');

UPDATE medicos
SET universidad_graduacion = 'Universidad Centroccidental Lisandro Alvarado (UCLA)'
WHERE RTRIM(LTRIM(universidad_graduacion)) IN ('UCLA', 'ucla');

UPDATE medicos
SET universidad_graduacion = 'Universidad Nacional Experimental Francisco de Miranda (UNEFM)'
WHERE RTRIM(LTRIM(universidad_graduacion)) IN ('UNEFM', 'unefm');

UPDATE medicos
SET universidad_graduacion = 'Universidad Nacional Experimental Rómulo Gallegos (UNERG)'
WHERE RTRIM(LTRIM(universidad_graduacion)) IN ('UNERG', 'unerg');

UPDATE medicos
SET universidad_graduacion = 'Universidad Católica Andrés Bello (UCAB)'
WHERE RTRIM(LTRIM(universidad_graduacion)) IN ('UCAB', 'ucab');

UPDATE medicos
SET universidad_graduacion = 'Universidad Santa María (USM)'
WHERE RTRIM(LTRIM(universidad_graduacion)) IN ('USM', 'usm');

UPDATE medicos
SET universidad_graduacion = 'Escuela Latinoamericana de Medicina (ELAM)'
WHERE RTRIM(LTRIM(universidad_graduacion)) IN ('ELAM', 'elam');

UPDATE medicos
SET universidad_graduacion = 'Universidad del Táchira (UNET)'
WHERE RTRIM(LTRIM(universidad_graduacion)) IN ('UNET', 'unet');

UPDATE medicos
SET universidad_graduacion = 'Universidad Rafael Belloso Chacín (URBE)'
WHERE RTRIM(LTRIM(universidad_graduacion)) IN ('URBE', 'urbe');

UPDATE medicos
SET universidad_graduacion = 'Universidad Metropolitana (UNIMET)'
WHERE RTRIM(LTRIM(universidad_graduacion)) IN ('UNIMET', 'unimet');

-- B) Homologar ESPECIALIDADES en medicos
UPDATE medicos
SET especialidad = 'Pediatría y Puericultura'
WHERE RTRIM(LTRIM(especialidad)) IN ('PEDIATRA', 'pediatra', 'Pediatra', 'Pediatría', 'pediatria');

UPDATE medicos
SET especialidad = 'Geriatría'
WHERE RTRIM(LTRIM(especialidad)) IN ('GERIATRA', 'geriatra', 'Geriatra', 'geriatria');

UPDATE medicos
SET especialidad = 'Cirugía General'
WHERE RTRIM(LTRIM(especialidad)) IN ('Cirujano', 'cirujano', 'CIRUJANO', 'Cirujana', 'cirujana');

UPDATE medicos
SET especialidad = 'Ginecología y Obstetricia'
WHERE RTRIM(LTRIM(especialidad)) IN ('Ginecólogo', 'Ginecóloga', 'ginecologo', 'ginecologa', 'Ginecologia', 'Obstetricia');

UPDATE medicos
SET especialidad = 'Cardiología'
WHERE RTRIM(LTRIM(especialidad)) IN ('Cardiólogo', 'Cardióloga', 'cardiologo', 'cardiologa', 'Cardiologia');

UPDATE medicos
SET especialidad = 'Traumatología y Ortopedia'
WHERE RTRIM(LTRIM(especialidad)) IN ('Traumatólogo', 'traumatologo', 'Traumatologia');

-- C) Homologar SUB-ESPECIALIDADES en medicos
UPDATE medicos
SET sub_especialidad = 'Cirugía Plástica y Reconstructiva'
WHERE RTRIM(LTRIM(sub_especialidad)) IN ('Plastico', 'plastico', 'Plástica', 'plastica', 'Cirugía Plástica', 'Cirugia Plastica');

UPDATE medicos
SET sub_especialidad = 'Pediatría y Puericultura'
WHERE RTRIM(LTRIM(sub_especialidad)) IN ('PEDIATRA', 'pediatra', 'Pediatra');

UPDATE medicos
SET sub_especialidad = 'Geriatría'
WHERE RTRIM(LTRIM(sub_especialidad)) IN ('GERIATRA', 'geriatra', 'Geriatra');

-- D) Normalizar ESTADOS y CIUDADES en medicos
UPDATE medicos
SET estado = 'Distrito Capital'
WHERE UPPER(RTRIM(LTRIM(estado))) = 'DISTRITO CAPITAL';

UPDATE medicos
SET ciudad = 'Caracas'
WHERE UPPER(RTRIM(LTRIM(ciudad))) = 'CARACAS';
GO

-- =============================================================================
-- 6. LIMPIEZA DE ENTRADAS OBSOLETAS O DUPLICADAS EN CATALOGOS_ENCUESTADOR
-- =============================================================================

-- Eliminar siglas antiguas que ya tienen su equivalente oficial
DELETE FROM CATALOGOS_ENCUESTADOR
WHERE tipo = 'universidad'
  AND nombre IN ('UCV', 'UDO', 'LUZ', 'ULA', 'UC', 'UCLA', 'UNEFM', 'UNERG', 'UCAB', 'USM', 'ELAM', 'UNET', 'URBE', 'UNIMET');

DELETE FROM CATALOGOS_ENCUESTADOR
WHERE tipo = 'especialidad'
  AND nombre IN ('PEDIATRA', 'GERIATRA', 'Cirujano', 'djdjz', 'ududhdz', 'uduzuz');

DELETE FROM CATALOGOS_ENCUESTADOR
WHERE tipo = 'subespecialidad'
  AND nombre IN ('PEDIATRA', 'GERIATRA', 'Plastico', 'duduuz', 'jdjzjz', 'jzjzjz');

DELETE FROM CATALOGOS_ENCUESTADOR
WHERE tipo = 'estado'
  AND nombre IN ('hdhdhd');

DELETE FROM CATALOGOS_ENCUESTADOR
WHERE tipo = 'ciudad'
  AND nombre IN ('hshshs');
GO

-- =============================================================================
-- 7. AUDITORÍA Y VERIFICACIÓN FINAL
-- =============================================================================

-- A) Resumen de ítems en el catálogo
SELECT tipo, COUNT(*) AS total_registros
FROM CATALOGOS_ENCUESTADOR
GROUP BY tipo
ORDER BY tipo;

-- B) Resumen de médicos y sus valores emparejados
SELECT 
    id_medico,
    nombre1,
    apellido1,
    especialidad,
    sub_especialidad,
    universidad_graduacion,
    ciudad,
    estado
FROM medicos;
GO
