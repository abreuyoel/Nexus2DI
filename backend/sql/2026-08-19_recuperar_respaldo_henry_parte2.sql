-- Parte 2 -- completa los medicos que faltaron en la parte 1
-- (2026-08-19_recuperar_respaldo_henry.sql).
--
-- medicos.id_medico_externo es NOT NULL + UNIQUE en la base real (el
-- modelo SQLAlchemy dice nullable=True, desactualizado). '' colisiono con
-- una fila preexistente (id_medico 118); NULL no esta permitido. Se usa el
-- telefono como placeholder para los que no tienen cedula real -- decision
-- del usuario, confirmado sin colisiones contra la tabla.
--
-- Maura Perez Sepeda e Ismarua Perez Cepeda compartian telefono
-- (04164279655) y numero de MPPS (49302) -- decision del usuario: es un
-- solo medico, se descarta la entrada de "Ismarua" (typo/duplicado).
--
-- Mapeo confirmado de encuestas ya insertadas en la parte 1:
-- 78=preexistente(centro97) 119=centro46/12ago 120=centro6/12ago
-- 121=centro31/13ago(1) 122=centro31/13ago(2) 123=centro49/13ago
-- 124=centro49/13ago(2) 125=centro49/13ago(3) 126=centro8/14ago
-- 127=centro50/14ago 128=centro49/14ago 129=centro46/14ago(Abierta)

SET XACT_ABORT ON;
BEGIN TRANSACTION;

-- 1) Perez Sepeda, Maura -- encuesta 78 -- id_medico_externo = telefono (sin cedula real)
DECLARE @med1 INT;
INSERT INTO medicos (id_medico_externo, apellido1, apellido2, nombre1, nombre2, especialidad, sub_especialidad, universidad_graduacion, nro_MPPS, nro_colegiado, ciudad, estado, telefono, whatsapp, email, linkedin, instagram, fecha_registro)
VALUES (N'04164279655', N'Pérez', N'Sepeda', N'Maura', NULL, N'Medicina Famikiar', NULL, N'UCV', N'49302', NULL, N'Caracas', N'Miranda', N'04164279655', NULL, N'caramelo.5med@gmail.com', NULL, N'Drperezi', '2026-08-12T10:58:25.275831');
SET @med1 = SCOPE_IDENTITY();
INSERT INTO medico_consultorios (id_medico, nombre_clinica, piso_consultorio, direccion_especifica, horarios_json, valor_consulta_rango, promedio_pacientes_semanal_rango, creado_en)
VALUES (@med1, N'SISALUD', NULL, NULL, N'{"Lun":{"activo":true,"desde":"08:00","hasta":"12:00"},"Mar":{"activo":true,"desde":"08:00","hasta":"12:00"},"Mié":{"activo":true,"desde":"08:00","hasta":"12:00"},"Jue":{"activo":true,"desde":"08:00","hasta":"12:00"},"Vie":{"activo":true,"desde":"08:00","hasta":"12:00"},"Sáb":{"activo":false,"desde":"08:00","hasta":"12:00"},"Dom":{"activo":false,"desde":"08:00","hasta":"12:00"}}', N'Entre 50$ a 60$', N'6 a 10 pacientes', '2026-08-12T10:58:25.275831');
INSERT INTO medico_centro_encuesta (id_encuesta, id_medico, actualizado_en) VALUES (78, @med1, '2026-08-12T10:58:25.275831');

-- 2) Godoy Sanchez, Luz -- encuesta 78 -- id_medico_externo = telefono
DECLARE @med2 INT;
INSERT INTO medicos (id_medico_externo, apellido1, apellido2, nombre1, nombre2, especialidad, sub_especialidad, universidad_graduacion, nro_MPPS, nro_colegiado, ciudad, estado, telefono, whatsapp, email, linkedin, instagram, fecha_registro)
VALUES (N'04242529480', N'Godoy', N'Sanchez', N'Luz', NULL, N'Medicina Interna', NULL, N'ULA', N'44871', N'24744', N'Caracas', N'Miranda', N'04242529480', N'04242529480', N'luzma66@gmail.com', NULL, NULL, '2026-08-12T11:08:18.461672');
SET @med2 = SCOPE_IDENTITY();
INSERT INTO medico_consultorios (id_medico, nombre_clinica, piso_consultorio, direccion_especifica, horarios_json, valor_consulta_rango, promedio_pacientes_semanal_rango, creado_en)
VALUES (@med2, N'SISALUD', N'piso 1', NULL, N'{"Lun":{"activo":true,"desde":"08:00","hasta":"12:00"},"Mar":{"activo":true,"desde":"08:00","hasta":"12:00"},"Mié":{"activo":true,"desde":"08:00","hasta":"12:00"},"Jue":{"activo":true,"desde":"08:00","hasta":"12:00"},"Vie":{"activo":true,"desde":"08:00","hasta":"12:00"},"Sáb":{"activo":false,"desde":"08:00","hasta":"12:00"},"Dom":{"activo":false,"desde":"08:00","hasta":"12:00"}}', N'Entre 50$ a 60$', N'6 a 10 pacientes', '2026-08-12T11:08:18.461672');
INSERT INTO medico_centro_encuesta (id_encuesta, id_medico, actualizado_en) VALUES (78, @med2, '2026-08-12T11:08:18.461672');

-- 3) Penott Martinez, Roberto -- encuesta 123 -- id_medico_externo = telefono
DECLARE @med3 INT;
INSERT INTO medicos (id_medico_externo, apellido1, apellido2, nombre1, nombre2, especialidad, sub_especialidad, universidad_graduacion, nro_MPPS, nro_colegiado, ciudad, estado, telefono, whatsapp, email, linkedin, instagram, fecha_registro)
VALUES (N'04143210516', N'Penott', N'Martinez', N'Roberto', NULL, N'Cirugía General', NULL, N'UCV', N'34354', N'12888', N'Guatire', N'Miranda', N'04143210516', N'04143210516', N'dr.robertopenott1996@gmail.com', NULL, NULL, '2026-08-13T12:42:09.442037');
SET @med3 = SCOPE_IDENTITY();
INSERT INTO medico_consultorios (id_medico, nombre_clinica, piso_consultorio, direccion_especifica, horarios_json, valor_consulta_rango, promedio_pacientes_semanal_rango, creado_en)
VALUES (@med3, N'CENTRO MEDICO BUENAVENTURA', N'piso 1', NULL, N'{"Lun":{"activo":false,"desde":"08:00","hasta":"12:00"},"Mar":{"activo":false,"desde":"08:00","hasta":"12:00"},"Mié":{"activo":true,"desde":"08:00","hasta":"12:00"},"Jue":{"activo":false,"desde":"08:00","hasta":"12:00"},"Vie":{"activo":false,"desde":"08:00","hasta":"12:00"},"Sáb":{"activo":false,"desde":"08:00","hasta":"12:00"},"Dom":{"activo":false,"desde":"08:00","hasta":"12:00"}}', N'Entre 30$ a 50$', N'1 a 5 pacientes', '2026-08-13T12:42:09.442037');
INSERT INTO medico_centro_encuesta (id_encuesta, id_medico, actualizado_en) VALUES (123, @med3, '2026-08-13T12:42:09.442037');

COMMIT TRANSACTION;

-- Verificacion final -- debe dar 8 medicos (9 del respaldo - 1 duplicado descartado)
SELECT COUNT(*) AS medicos_total_respaldo FROM medicos WHERE fecha_registro BETWEEN '2026-08-12' AND '2026-08-15';
SELECT e.id_encuesta, e.id_centro, e.estado, COUNT(mce.id_medico) AS medicos_vinculados
FROM encuestas_centro e
LEFT JOIN medico_centro_encuesta mce ON mce.id_encuesta = e.id_encuesta
WHERE e.id_usuario = 2478 AND e.fecha_verificacion BETWEEN '2026-08-12' AND '2026-08-15'
GROUP BY e.id_encuesta, e.id_centro, e.estado
ORDER BY e.id_encuesta;
