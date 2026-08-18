-- Recuperacion del respaldo offline de Henrry Farias (usuario 2478 / '15815074')
-- respaldo_encuestador_2026-08-14.json -- 43 operaciones nunca sincronizadas por
-- el bug de la cola offline de encuestador (ya corregido esta sesion, ver
-- encuestador_sync_service.dart). Todo el trabajo ocurrio bajo la jornada 35 --
-- la unica que realmente estuvo abierta server-side durante el 12-14 de agosto,
-- confirmado contra la base: sus intentos de cerrar/reabrir jornada ese dia nunca
-- llegaron a sincronizar, asi que el servidor la mantuvo abierta hasta el 16 de agosto.

BEGIN TRANSACTION;

-- ============================================================
-- 11 encuestas nuevas (la #78 ya existia -- centro 97, jornada 35, Cerrada)
-- ============================================================

DECLARE @enc1 INT;
INSERT INTO encuestas_centro (id_usuario, id_centro, id_jornada, fecha_verificacion, fuente_informacion, notas_generales, creado_en, estado)
VALUES (2478, 46, 35, '2026-08-12', N'Visita presencial', NULL, '2026-08-12T13:27:44.242121', 'Cerrada');
SET @enc1 = SCOPE_IDENTITY();
-- @enc1 = encuesta centro 46 del 2026-08-12 (local_id 7450fa3d...)

DECLARE @enc2 INT;
INSERT INTO encuestas_centro (id_usuario, id_centro, id_jornada, fecha_verificacion, fuente_informacion, notas_generales, creado_en, estado)
VALUES (2478, 6, 35, '2026-08-12', N'Visita presencial', NULL, '2026-08-12T14:10:44.498098', 'Cerrada');
SET @enc2 = SCOPE_IDENTITY();
-- @enc2 = encuesta centro 6 del 2026-08-12 (local_id 5fc75db8...)

DECLARE @enc3 INT;
INSERT INTO encuestas_centro (id_usuario, id_centro, id_jornada, fecha_verificacion, fuente_informacion, notas_generales, creado_en, estado)
VALUES (2478, 31, 35, '2026-08-13', N'Visita presencial', NULL, '2026-08-13T11:33:11.668402', 'Cerrada');
SET @enc3 = SCOPE_IDENTITY();
-- @enc3 = encuesta centro 31 del 2026-08-13 (local_id 9f885458...)

DECLARE @enc4 INT;
INSERT INTO encuestas_centro (id_usuario, id_centro, id_jornada, fecha_verificacion, fuente_informacion, notas_generales, creado_en, estado)
VALUES (2478, 31, 35, '2026-08-13', N'Visita presencial', NULL, '2026-08-13T11:33:49.346541', 'Cerrada');
SET @enc4 = SCOPE_IDENTITY();
-- @enc4 = encuesta centro 31 del 2026-08-13 (local_id d03a0ba7...)

DECLARE @enc5 INT;
INSERT INTO encuestas_centro (id_usuario, id_centro, id_jornada, fecha_verificacion, fuente_informacion, notas_generales, creado_en, estado)
VALUES (2478, 49, 35, '2026-08-13', N'Visita presencial', NULL, '2026-08-13T12:20:25.560153', 'Cerrada');
SET @enc5 = SCOPE_IDENTITY();
-- @enc5 = encuesta centro 49 del 2026-08-13 (local_id 0d0b3ca4...)

DECLARE @enc6 INT;
INSERT INTO encuestas_centro (id_usuario, id_centro, id_jornada, fecha_verificacion, fuente_informacion, notas_generales, creado_en, estado)
VALUES (2478, 49, 35, '2026-08-13', N'Visita presencial', NULL, '2026-08-13T14:43:14.071874', 'Cerrada');
SET @enc6 = SCOPE_IDENTITY();
-- @enc6 = encuesta centro 49 del 2026-08-13 (local_id 2321043e...)

DECLARE @enc7 INT;
INSERT INTO encuestas_centro (id_usuario, id_centro, id_jornada, fecha_verificacion, fuente_informacion, notas_generales, creado_en, estado)
VALUES (2478, 49, 35, '2026-08-13', N'Visita presencial', NULL, '2026-08-13T18:25:20.971984', 'Cerrada');
SET @enc7 = SCOPE_IDENTITY();
-- @enc7 = encuesta centro 49 del 2026-08-13 (local_id c8132f47...)

DECLARE @enc8 INT;
INSERT INTO encuestas_centro (id_usuario, id_centro, id_jornada, fecha_verificacion, fuente_informacion, notas_generales, creado_en, estado)
VALUES (2478, 8, 35, '2026-08-14', N'Visita presencial', NULL, '2026-08-14T07:06:09.708546', 'Cerrada');
SET @enc8 = SCOPE_IDENTITY();
-- @enc8 = encuesta centro 8 del 2026-08-14 (local_id 33002d06...)

DECLARE @enc9 INT;
INSERT INTO encuestas_centro (id_usuario, id_centro, id_jornada, fecha_verificacion, fuente_informacion, notas_generales, creado_en, estado)
VALUES (2478, 50, 35, '2026-08-14', N'Visita presencial', NULL, '2026-08-14T07:06:35.953847', 'Cerrada');
SET @enc9 = SCOPE_IDENTITY();
-- @enc9 = encuesta centro 50 del 2026-08-14 (local_id 129a573d...)

DECLARE @enc10 INT;
INSERT INTO encuestas_centro (id_usuario, id_centro, id_jornada, fecha_verificacion, fuente_informacion, notas_generales, creado_en, estado)
VALUES (2478, 49, 35, '2026-08-14', N'Visita presencial', NULL, '2026-08-14T07:06:59.718784', 'Cerrada');
SET @enc10 = SCOPE_IDENTITY();
-- @enc10 = encuesta centro 49 del 2026-08-14 (local_id 508fa901...)

-- OJO: quedo ABIERTA de verdad -- el respaldo termina justo aca (ultima
-- operacion capturada) sin un cierre correspondiente. Confirmar con Henry
-- si esa visita se completo antes de darla por Cerrada.
DECLARE @enc11 INT;
INSERT INTO encuestas_centro (id_usuario, id_centro, id_jornada, fecha_verificacion, fuente_informacion, notas_generales, creado_en, estado)
VALUES (2478, 46, 35, '2026-08-14', N'Visita presencial', NULL, '2026-08-14T09:54:51.524967', 'Abierta');
SET @enc11 = SCOPE_IDENTITY();
-- @enc11 = encuesta centro 46 del 2026-08-14 (local_id c5d7b46f...)

-- ============================================================
-- 9 medicos nuevos + consultorios + vinculo a su encuesta
-- ============================================================

-- 1) Pérez Sepeda, Maura -- va a encuesta 78 (centro 97 (#78))
DECLARE @med1 INT;
INSERT INTO medicos (id_medico_externo, apellido1, apellido2, nombre1, nombre2, especialidad, sub_especialidad, universidad_graduacion, nro_MPPS, nro_colegiado, ciudad, estado, telefono, whatsapp, email, linkedin, instagram, fecha_registro)
VALUES ('', N'Pérez', N'Sepeda', N'Maura', NULL, N'Medicina Famikiar', NULL, N'UCV', N'49302', NULL, N'Caracas', N'Miranda', N'04164279655', NULL, N'caramelo.5med@gmail.com', NULL, N'Drperezi', '2026-08-12T10:58:25.275831');
SET @med1 = SCOPE_IDENTITY();
INSERT INTO medico_consultorios (id_medico, nombre_clinica, piso_consultorio, direccion_especifica, horarios_json, valor_consulta_rango, promedio_pacientes_semanal_rango, creado_en)
VALUES (@med1, N'SISALUD', NULL, NULL, N'{"Lun":{"activo":true,"desde":"08:00","hasta":"12:00"},"Mar":{"activo":true,"desde":"08:00","hasta":"12:00"},"Mié":{"activo":true,"desde":"08:00","hasta":"12:00"},"Jue":{"activo":true,"desde":"08:00","hasta":"12:00"},"Vie":{"activo":true,"desde":"08:00","hasta":"12:00"},"Sáb":{"activo":false,"desde":"08:00","hasta":"12:00"},"Dom":{"activo":false,"desde":"08:00","hasta":"12:00"}}', N'Entre 50$ a 60$', N'6 a 10 pacientes', '2026-08-12T10:58:25.275831');
INSERT INTO medico_centro_encuesta (id_encuesta, id_medico, actualizado_en) VALUES (78, @med1, '2026-08-12T10:58:25.275831');

-- 2) Godoy Sanchez, Luz -- va a encuesta 78 (centro 97 (#78))
DECLARE @med2 INT;
INSERT INTO medicos (id_medico_externo, apellido1, apellido2, nombre1, nombre2, especialidad, sub_especialidad, universidad_graduacion, nro_MPPS, nro_colegiado, ciudad, estado, telefono, whatsapp, email, linkedin, instagram, fecha_registro)
VALUES ('', N'Godoy', N'Sanchez', N'Luz', NULL, N'Medicina Interna', NULL, N'ULA', N'44871', N'24744', N'Caracas', N'Miranda', N'04242529480', N'04242529480', N'luzma66@gmail.com', NULL, NULL, '2026-08-12T11:08:18.461672');
SET @med2 = SCOPE_IDENTITY();
INSERT INTO medico_consultorios (id_medico, nombre_clinica, piso_consultorio, direccion_especifica, horarios_json, valor_consulta_rango, promedio_pacientes_semanal_rango, creado_en)
VALUES (@med2, N'SISALUD', N'piso 1', NULL, N'{"Lun":{"activo":true,"desde":"08:00","hasta":"12:00"},"Mar":{"activo":true,"desde":"08:00","hasta":"12:00"},"Mié":{"activo":true,"desde":"08:00","hasta":"12:00"},"Jue":{"activo":true,"desde":"08:00","hasta":"12:00"},"Vie":{"activo":true,"desde":"08:00","hasta":"12:00"},"Sáb":{"activo":false,"desde":"08:00","hasta":"12:00"},"Dom":{"activo":false,"desde":"08:00","hasta":"12:00"}}', N'Entre 50$ a 60$', N'6 a 10 pacientes', '2026-08-12T11:08:18.461672');
INSERT INTO medico_centro_encuesta (id_encuesta, id_medico, actualizado_en) VALUES (78, @med2, '2026-08-12T11:08:18.461672');

-- 3) Pérez Cepeda, Ismarua -- va a encuesta 78 (centro 97 (#78))
DECLARE @med3 INT;
INSERT INTO medicos (id_medico_externo, apellido1, apellido2, nombre1, nombre2, especialidad, sub_especialidad, universidad_graduacion, nro_MPPS, nro_colegiado, ciudad, estado, telefono, whatsapp, email, linkedin, instagram, fecha_registro)
VALUES ('', N'Pérez', N'Cepeda', N'Ismarua', NULL, N'Medicina Familiar', NULL, N'UCV', N'49302', NULL, N'Caracas', N'Miranda', N'04164279655', N'04164279655', NULL, NULL, NULL, '2026-08-12T12:37:50.777052');
SET @med3 = SCOPE_IDENTITY();
INSERT INTO medico_consultorios (id_medico, nombre_clinica, piso_consultorio, direccion_especifica, horarios_json, valor_consulta_rango, promedio_pacientes_semanal_rango, creado_en)
VALUES (@med3, N'SISALUD', N'Planta', NULL, N'{"Lun":{"activo":true,"desde":"08:00","hasta":"12:00"},"Mar":{"activo":true,"desde":"08:00","hasta":"12:00"},"Mié":{"activo":true,"desde":"08:00","hasta":"12:00"},"Jue":{"activo":true,"desde":"08:00","hasta":"12:00"},"Vie":{"activo":true,"desde":"08:00","hasta":"12:00"},"Sáb":{"activo":false,"desde":"08:00","hasta":"12:00"},"Dom":{"activo":false,"desde":"08:00","hasta":"12:00"}}', N'Entre 50$ a 60$', N'6 a 10 pacientes', '2026-08-12T12:37:50.777052');
INSERT INTO medico_centro_encuesta (id_encuesta, id_medico, actualizado_en) VALUES (78, @med3, '2026-08-12T12:37:50.777052');

-- 4) Diaz Mirabal, Mariela -- va a encuesta @enc5 (centro 49)
DECLARE @med4 INT;
INSERT INTO medicos (id_medico_externo, apellido1, apellido2, nombre1, nombre2, especialidad, sub_especialidad, universidad_graduacion, nro_MPPS, nro_colegiado, ciudad, estado, telefono, whatsapp, email, linkedin, instagram, fecha_registro)
VALUES (N'13978726', N'Diaz', N'Mirabal', N'Mariela', NULL, N'Ginecólogo', NULL, N'UCV', N'66402', N'17777', N'Guatire', N'Miranda', N'04141109879', NULL, N'ginecologiaaldia@gmail.com', NULL, NULL, '2026-08-13T12:28:21.375412');
SET @med4 = SCOPE_IDENTITY();
INSERT INTO medico_consultorios (id_medico, nombre_clinica, piso_consultorio, direccion_especifica, horarios_json, valor_consulta_rango, promedio_pacientes_semanal_rango, creado_en)
VALUES (@med4, N'CENTRO MEDICO BUENAVENTURA', N'piso 1', NULL, N'{"Lun":{"activo":true,"desde":"07:00","hasta":"13:00"},"Mar":{"activo":false,"desde":"08:00","hasta":"12:00"},"Mié":{"activo":false,"desde":"08:00","hasta":"12:00"},"Jue":{"activo":true,"desde":"07:00","hasta":"13:00"},"Vie":{"activo":false,"desde":"08:00","hasta":"12:00"},"Sáb":{"activo":true,"desde":"07:00","hasta":"12:00"},"Dom":{"activo":false,"desde":"08:00","hasta":"12:00"}}', N'Entre 30$ a 50$', N'6 a 10 pacientes', '2026-08-13T12:28:21.375412');
INSERT INTO medico_consultorios (id_medico, nombre_clinica, piso_consultorio, direccion_especifica, horarios_json, valor_consulta_rango, promedio_pacientes_semanal_rango, creado_en)
VALUES (@med4, N'Centro medico la Hacienda', NULL, NULL, N'{"Lun":{"activo":true,"desde":"02:00","hasta":"18:00"},"Mar":{"activo":true,"desde":"08:00","hasta":"12:00"},"Mié":{"activo":true,"desde":"08:00","hasta":"12:00"},"Jue":{"activo":true,"desde":"02:00","hasta":"18:00"},"Vie":{"activo":true,"desde":"08:00","hasta":"12:00"},"Sáb":{"activo":false,"desde":"08:00","hasta":"12:00"},"Dom":{"activo":false,"desde":"08:00","hasta":"12:00"}}', N'Entre 30$ a 50$', N'6 a 10 pacientes', '2026-08-13T12:28:21.375412');
INSERT INTO medico_centro_encuesta (id_encuesta, id_medico, actualizado_en) VALUES (@enc5, @med4, '2026-08-13T12:28:21.375412');

-- 5) Penott Martinez, Roberto -- va a encuesta @enc5 (centro 49)
DECLARE @med5 INT;
INSERT INTO medicos (id_medico_externo, apellido1, apellido2, nombre1, nombre2, especialidad, sub_especialidad, universidad_graduacion, nro_MPPS, nro_colegiado, ciudad, estado, telefono, whatsapp, email, linkedin, instagram, fecha_registro)
VALUES ('', N'Penott', N'Martinez', N'Roberto', NULL, N'Cirugía General', NULL, N'UCV', N'34354', N'12888', N'Guatire', N'Miranda', N'04143210516', N'04143210516', N'dr.robertopenott1996@gmail.com', NULL, NULL, '2026-08-13T12:42:09.442037');
SET @med5 = SCOPE_IDENTITY();
INSERT INTO medico_consultorios (id_medico, nombre_clinica, piso_consultorio, direccion_especifica, horarios_json, valor_consulta_rango, promedio_pacientes_semanal_rango, creado_en)
VALUES (@med5, N'CENTRO MEDICO BUENAVENTURA', N'piso 1', NULL, N'{"Lun":{"activo":false,"desde":"08:00","hasta":"12:00"},"Mar":{"activo":false,"desde":"08:00","hasta":"12:00"},"Mié":{"activo":true,"desde":"08:00","hasta":"12:00"},"Jue":{"activo":false,"desde":"08:00","hasta":"12:00"},"Vie":{"activo":false,"desde":"08:00","hasta":"12:00"},"Sáb":{"activo":false,"desde":"08:00","hasta":"12:00"},"Dom":{"activo":false,"desde":"08:00","hasta":"12:00"}}', N'Entre 30$ a 50$', N'1 a 5 pacientes', '2026-08-13T12:42:09.442037');
INSERT INTO medico_centro_encuesta (id_encuesta, id_medico, actualizado_en) VALUES (@enc5, @med5, '2026-08-13T12:42:09.442037');

-- 6) Moreno Castillo, Reinaldo -- va a encuesta @enc5 (centro 49)
DECLARE @med6 INT;
INSERT INTO medicos (id_medico_externo, apellido1, apellido2, nombre1, nombre2, especialidad, sub_especialidad, universidad_graduacion, nro_MPPS, nro_colegiado, ciudad, estado, telefono, whatsapp, email, linkedin, instagram, fecha_registro)
VALUES (N'8524788', N'Moreno', N'Castillo', N'Reinaldo', NULL, N'Traumatologia Ortopedia', NULL, N'UCV', N'32476', N'15005', N'Guatire', N'Miranda', N'04166289635', NULL, NULL, NULL, NULL, '2026-08-13T14:23:01.210925');
SET @med6 = SCOPE_IDENTITY();
INSERT INTO medico_consultorios (id_medico, nombre_clinica, piso_consultorio, direccion_especifica, horarios_json, valor_consulta_rango, promedio_pacientes_semanal_rango, creado_en)
VALUES (@med6, N'CENTRO MEDICO BUENAVENTURA', N'Piaso 1', NULL, N'{"Lun":{"activo":true,"desde":"08:00","hasta":"12:00"},"Mar":{"activo":false,"desde":"08:00","hasta":"12:00"},"Mié":{"activo":false,"desde":"08:00","hasta":"12:00"},"Jue":{"activo":true,"desde":"08:00","hasta":"12:00"},"Vie":{"activo":false,"desde":"08:00","hasta":"12:00"},"Sáb":{"activo":false,"desde":"08:00","hasta":"12:00"},"Dom":{"activo":false,"desde":"08:00","hasta":"12:00"}}', N'Entre 30$ a 50$', N'6 a 10 pacientes', '2026-08-13T14:23:01.210925');
INSERT INTO medico_centro_encuesta (id_encuesta, id_medico, actualizado_en) VALUES (@enc5, @med6, '2026-08-13T14:23:01.210925');

-- 7) Shadie Shaide, Tawsire -- va a encuesta @enc5 (centro 49)
DECLARE @med7 INT;
INSERT INTO medicos (id_medico_externo, apellido1, apellido2, nombre1, nombre2, especialidad, sub_especialidad, universidad_graduacion, nro_MPPS, nro_colegiado, ciudad, estado, telefono, whatsapp, email, linkedin, instagram, fecha_registro)
VALUES (N'9097807', N'Shadie', N'Shaide', N'Tawsire', NULL, N'Traumatologo', NULL, N'UCV', N'46712', N'23191', N'Guatire', N'Miranda', N'O4241450858', NULL, NULL, NULL, NULL, '2026-08-13T14:25:22.136951');
SET @med7 = SCOPE_IDENTITY();
INSERT INTO medico_consultorios (id_medico, nombre_clinica, piso_consultorio, direccion_especifica, horarios_json, valor_consulta_rango, promedio_pacientes_semanal_rango, creado_en)
VALUES (@med7, N'CENTRO MEDICO BUENAVENTURA', N'piso 1', NULL, N'{"Lun":{"activo":false,"desde":"08:00","hasta":"12:00"},"Mar":{"activo":true,"desde":"08:00","hasta":"12:00"},"Mié":{"activo":false,"desde":"08:00","hasta":"12:00"},"Jue":{"activo":true,"desde":"08:00","hasta":"12:00"},"Vie":{"activo":false,"desde":"08:00","hasta":"12:00"},"Sáb":{"activo":false,"desde":"08:00","hasta":"12:00"},"Dom":{"activo":false,"desde":"08:00","hasta":"12:00"}}', N'Entre 50$ a 60$', N'6 a 10 pacientes', '2026-08-13T14:25:22.136951');
INSERT INTO medico_centro_encuesta (id_encuesta, id_medico, actualizado_en) VALUES (@enc5, @med7, '2026-08-13T14:25:22.136951');

-- 8) Leon Ojeda, Leonardo -- va a encuesta @enc6 (centro 49)
DECLARE @med8 INT;
INSERT INTO medicos (id_medico_externo, apellido1, apellido2, nombre1, nombre2, especialidad, sub_especialidad, universidad_graduacion, nro_MPPS, nro_colegiado, ciudad, estado, telefono, whatsapp, email, linkedin, instagram, fecha_registro)
VALUES (N'20663167', N'Leon', N'Ojeda', N'Leonardo', N'José', N'Neurocirugía', NULL, N'UCV', N'110889', N'12180', N'Guatire', N'Miranda', N'04124077492', N'04124077492', N'leonardojleono@gmail.com', NULL, NULL, '2026-08-13T15:12:09.010992');
SET @med8 = SCOPE_IDENTITY();
INSERT INTO medico_consultorios (id_medico, nombre_clinica, piso_consultorio, direccion_especifica, horarios_json, valor_consulta_rango, promedio_pacientes_semanal_rango, creado_en)
VALUES (@med8, N'CENTRO MEDICO BUENAVENTURA', N'piso 1/ unidad 5', NULL, N'{"Lun":{"activo":false,"desde":"08:00","hasta":"12:00"},"Mar":{"activo":false,"desde":"08:00","hasta":"12:00"},"Mié":{"activo":false,"desde":"08:00","hasta":"12:00"},"Jue":{"activo":true,"desde":"08:00","hasta":"12:00"},"Vie":{"activo":false,"desde":"08:00","hasta":"12:00"},"Sáb":{"activo":false,"desde":"08:00","hasta":"12:00"},"Dom":{"activo":false,"desde":"08:00","hasta":"12:00"}}', N'Entre 50$ a 60$', N'6 a 10 pacientes', '2026-08-13T15:12:09.010992');
INSERT INTO medico_centro_encuesta (id_encuesta, id_medico, actualizado_en) VALUES (@enc6, @med8, '2026-08-13T15:12:09.010992');

-- 9) Avariano Farfan, Yubisay -- va a encuesta @enc6 (centro 49)
DECLARE @med9 INT;
INSERT INTO medicos (id_medico_externo, apellido1, apellido2, nombre1, nombre2, especialidad, sub_especialidad, universidad_graduacion, nro_MPPS, nro_colegiado, ciudad, estado, telefono, whatsapp, email, linkedin, instagram, fecha_registro)
VALUES (N'13551809', N'Avariano', N'Farfan', N'Yubisay', NULL, N'Cirugía Plastica', NULL, N'UCV', N'61172', N'27917', N'Guatire', N'Miranda', N'04223871058', NULL, N'dra.yubiavarianof@gmail.com', NULL, N'dra.yubiavariano', '2026-08-13T15:25:49.760484');
SET @med9 = SCOPE_IDENTITY();
INSERT INTO medico_consultorios (id_medico, nombre_clinica, piso_consultorio, direccion_especifica, horarios_json, valor_consulta_rango, promedio_pacientes_semanal_rango, creado_en)
VALUES (@med9, N'CENTRO MEDICO BUENAVENTURA', N'Piso 1/ unidad 5', NULL, N'{"Lun":{"activo":false,"desde":"08:00","hasta":"12:00"},"Mar":{"activo":false,"desde":"08:00","hasta":"12:00"},"Mié":{"activo":true,"desde":"02:00","hasta":"17:00"},"Jue":{"activo":false,"desde":"08:00","hasta":"12:00"},"Vie":{"activo":false,"desde":"08:00","hasta":"12:00"},"Sáb":{"activo":false,"desde":"08:00","hasta":"12:00"},"Dom":{"activo":false,"desde":"08:00","hasta":"12:00"}}', N'Entre 50$ a 60$', N'1 a 5 pacientes', '2026-08-13T15:25:49.760484');
INSERT INTO medico_centro_encuesta (id_encuesta, id_medico, actualizado_en) VALUES (@enc6, @med9, '2026-08-13T15:25:49.760484');

COMMIT TRANSACTION;

-- Verificacion rapida post-insert
SELECT COUNT(*) AS medicos_insertados FROM medicos WHERE fecha_registro BETWEEN '2026-08-12' AND '2026-08-15';
SELECT id_encuesta, id_centro, fecha_verificacion, estado FROM encuestas_centro WHERE id_usuario=2478 AND fecha_verificacion BETWEEN '2026-08-12' AND '2026-08-15' ORDER BY id_encuesta;