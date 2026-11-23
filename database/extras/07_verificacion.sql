-- =====================================================================
-- MEDIMAGEN2 | 07_verificacion.sql
-- Comprobaciones de seguridad y de reglas. Ejecutar por partes (A, B, C, D, E).
-- Servidor Docker: Workbench en 127.0.0.1 puerto 3007. Servidor local: puerto 3306.
-- =====================================================================

-- ---------------------------------------------------------------------
-- A. Con ROOT: cuentas, roles y datos (no prueba permisos: root puede todo)
-- ---------------------------------------------------------------------
SELECT user, host FROM mysql.user WHERE user LIKE 'usr\_%' OR user LIKE 'dba\_%';
SELECT FROM_USER AS rol, TO_USER AS usuario FROM mysql.role_edges;
SHOW GRANTS FOR 'usr_administrador'@'%' USING 'rol_administrador';
SHOW GRANTS FOR 'usr_login'@'%';

SELECT cedula, nombre_usuario, rol, tipo_perfil, estado FROM medimagen2.v_usuarios;
SELECT COUNT(*) AS tablas FROM information_schema.tables
WHERE table_schema = 'medimagen2' AND table_type = 'BASE TABLE';               -- 17

-- Deben fallar por las reglas de la base (con root tambien fallan):
-- (a) usuario con rol medico cuya cedula no pertenece a ningun medico registrado
INSERT INTO medimagen2.usuario (id_rol, cedula, nombres, apellidos, correo, password)
VALUES (3, '0000098765', 'X', 'Y', 'x@y.com', 'h');
-- (a2) nombre de usuario automatico: 'Cristian Marin' ya existe (cmarin), el siguiente homonimo recibe numero
INSERT INTO medimagen2.usuario (id_rol, cedula, nombres, apellidos, correo, password)
VALUES (2, '0000098001', 'Carlos Luis', 'Marin Prueba', 'cmarin.prueba@medimagen.ec', 'h');
SELECT cedula, nombre_usuario FROM medimagen2.usuario WHERE cedula = '0000098001';   -- cmarin04
DELETE FROM medimagen2.usuario WHERE cedula = '0000098001';
-- (b) sabado
INSERT INTO medimagen2.cita (cedula_paciente,id_area,id_recurso,id_usuario_registra,fecha_cita,hora_inicio,hora_fin)
VALUES ('0000000021',1,2,2,'2026-11-14','08:00:00','09:00:00');
-- (c) paciente con dos citas a la misma hora
INSERT INTO medimagen2.cita (cedula_paciente,id_area,id_recurso,id_usuario_registra,fecha_cita,hora_inicio,hora_fin)
VALUES ('0000000021',1,2,2,'2026-11-02','08:00:00','09:00:00');
-- (d) eliminar una cita atendida
DELETE FROM medimagen2.cita WHERE id_cita = 1;
-- (e) hora fuera de la jornada (la ultima cita empieza a las 17:00) o que no dura 60 minutos
INSERT INTO medimagen2.cita (cedula_paciente,id_area,id_recurso,id_usuario_registra,fecha_cita,hora_inicio,hora_fin)
VALUES ('0000000023',1,2,2,'2026-12-01','18:00:00','19:00:00');
INSERT INTO medimagen2.cita (cedula_paciente,id_area,id_recurso,id_usuario_registra,fecha_cita,hora_inicio,hora_fin)
VALUES ('0000000023',1,2,2,'2026-12-01','08:00:00','09:30:00');
-- (f) dejar a una especialidad sin su ultimo medico activo
UPDATE medimagen2.medico SET estado = 'inactivo' WHERE id_medico IN (1,2,3,16);

-- ---------------------------------------------------------------------
-- B. Con usr_administrador (conexion nueva, clave uno234cinco)
-- ---------------------------------------------------------------------
-- Debe funcionar:
SELECT * FROM medimagen2.v_usuarios;
UPDATE medimagen2.usuario SET estado = 'inactivo' WHERE nombre_usuario = 'acordero';
UPDATE medimagen2.usuario SET estado = 'activo', intentos_fallidos = 0, bloqueado_hasta = NULL WHERE nombre_usuario = 'acordero';
ALTER TABLE medimagen2.area ADD COLUMN prueba INT;
ALTER TABLE medimagen2.area DROP COLUMN prueba;
INSERT INTO medimagen2.especialidad (nombre, descripcion, costo_consulta) VALUES ('Prueba', 'Codigo automatico por trigger', 10);
SELECT id_especialidad, nombre FROM medimagen2.especialidad ORDER BY id_especialidad DESC LIMIT 1;   -- ESP-08
DELETE FROM medimagen2.especialidad WHERE nombre = 'Prueba';

-- Eliminar usuarios: el administrador puede, pero MySQL lo bloquea (error 1451) si el usuario ya tiene
-- citas o resultados registrados. Para un usuario nunca usado funciona (se crea y se elimina):
INSERT INTO medimagen2.paciente (cedula_paciente, nombres, apellidos, fecha_nacimiento, sexo)
VALUES ('0000000097', 'Prueba', 'Eliminar', '1990-01-01', 'M');
INSERT INTO medimagen2.usuario (id_rol, cedula, nombres, apellidos, nombre_usuario, correo, password)
SELECT id_rol, '0000000097', 'Prueba', 'Eliminar', 'pruebaelim', 'pruebaelim@medimagen.ec', 'x'
FROM medimagen2.rol WHERE nombre = 'paciente';
DELETE FROM medimagen2.usuario WHERE nombre_usuario = 'pruebaelim';
DELETE FROM medimagen2.paciente WHERE cedula_paciente = '0000000097';

-- Debe dar error 1451 (el usuario ya registro citas, se debe desactivar):
DELETE FROM medimagen2.usuario WHERE nombre_usuario = 'ccriollo';

-- Debe dar error de permisos (1044 o 1142):
DROP TABLE medimagen2.usuario;
DROP TABLE medimagen2.cita;
TRUNCATE TABLE medimagen2.usuario;

CREATE DATABASE otra_bd;
DROP DATABASE medimagen;   -- ejecutala al final; debe fallar

-- ---------------------------------------------------------------------
-- C. Con usr_login (conexion nueva, clave uno234cinco)
-- ---------------------------------------------------------------------
-- Debe funcionar:
SELECT nombre_usuario, password, id_rol, estado, intentos_fallidos, bloqueado_hasta, cambio_clave_obligatorio
FROM medimagen2.usuario WHERE nombre_usuario = 'candrade';
UPDATE medimagen2.usuario SET intentos_fallidos = intentos_fallidos + 1 WHERE nombre_usuario = 'candrade';
UPDATE medimagen2.usuario SET intentos_fallidos = 0, ultimo_acceso = NOW() WHERE nombre_usuario = 'candrade';

-- Debe dar error 1142 / 1143 / 1054:
SELECT * FROM medimagen2.paciente;
SELECT correo FROM medimagen2.usuario;
UPDATE medimagen2.usuario SET id_rol = 1 WHERE nombre_usuario = 'candrade';
UPDATE medimagen2.usuario SET estado = 'activo' WHERE nombre_usuario = 'candrade';

-- ---------------------------------------------------------------------
-- D. Con usr_paciente (conexion nueva, clave uno234cinco)
-- ---------------------------------------------------------------------
SELECT * FROM medimagen2.v_agenda_consultas;          -- funciona
SELECT * FROM medimagen2.paciente;                    -- error 1142
INSERT INTO medimagen2.rol (nombre) VALUES ('x');     -- error 1142

-- ---------------------------------------------------------------------
-- E. Con usr_recepcion (conexion nueva, clave uno234cinco)
-- ---------------------------------------------------------------------
SELECT * FROM medimagen2.paciente;                    -- funciona
SELECT * FROM medimagen2.especialidad;                -- funciona (solo lectura)
SELECT * FROM medimagen2.consulta_medica;             -- error 1142 (sin datos clinicos)
UPDATE medimagen2.cita SET costo_aplicado = 0 WHERE id_cita = 18;   -- error 1143 (el costo lo fija el trigger)
INSERT INTO medimagen2.especialidad (nombre, costo_consulta) VALUES ('X', 1);   -- error 1142 (solo el administrador)