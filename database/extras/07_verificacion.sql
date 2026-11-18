-- =====================================================================
-- MEDIMAGEN | 07_verificacion.sql
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

SELECT cedula, nombre_usuario, rol, tipo_perfil, estado FROM medimagen.v_usuarios;
SELECT COUNT(*) AS registros_auditoria_cita FROM medimagen.auditoria_cita;      -- 27 antes de las consultas
SELECT COUNT(*) AS registros_auditoria_acceso FROM medimagen.auditoria_acceso;  -- 10 antes de usar el sistema

-- Deben fallar por las reglas de la base (con root tambien fallan):
-- (a) cedula que no coincide con el perfil
INSERT INTO medimagen.usuario (cedula, id_rol, id_personal, nombres, apellidos, nombre_usuario, correo, password_hash)
VALUES ('0999999999', 2, 2, 'X', 'Y', 'prueba', 'x@y.com', 'h');
-- (b) sabado
INSERT INTO medimagen.cita (cedula_paciente,id_area,id_recurso,id_usuario_registra,fecha_cita,hora_inicio,hora_fin)
VALUES ('0000000021',1,2,2,'2026-11-14','08:00:00','09:00:00');
-- (c) paciente con dos citas a la misma hora
INSERT INTO medimagen.cita (cedula_paciente,id_area,id_recurso,id_usuario_registra,fecha_cita,hora_inicio,hora_fin)
VALUES ('0000000021',1,2,2,'2026-11-02','08:00:00','09:00:00');
-- (d) eliminar una cita atendida
DELETE FROM medimagen.cita WHERE id_cita = 1;
-- (e) borrar o modificar el registro de accesos
DELETE FROM medimagen.auditoria_acceso WHERE id_acceso = 1;
UPDATE medimagen.auditoria_acceso SET resultado = 'exitoso' WHERE id_acceso = 5;
-- (f) consulta fuera del turno del medico 7 (solo atiende de 15:00 a 18:00)
INSERT INTO medimagen.cita (cedula_paciente,id_area,id_recurso,id_usuario_registra,fecha_cita,hora_inicio,hora_fin)
VALUES ('0000000023',1,2,2,'2026-12-01','08:00:00','09:00:00');
INSERT INTO medimagen.cita_consulta (id_cita, id_medico) VALUES (LAST_INSERT_ID(), 7);

-- ---------------------------------------------------------------------
-- B. Con usr_administrador (conexion nueva, clave uno234cinco)
-- ---------------------------------------------------------------------
-- Debe funcionar:
SELECT * FROM medimagen.v_usuarios;
UPDATE medimagen.usuario SET estado = 'inactivo' WHERE nombre_usuario = 'acordero';
UPDATE medimagen.usuario SET estado = 'activo', intentos_fallidos = 0, bloqueado_hasta = NULL WHERE nombre_usuario = 'acordero';
ALTER TABLE medimagen.medicamento ADD COLUMN prueba INT;
ALTER TABLE medimagen.medicamento DROP COLUMN prueba;
INSERT INTO medimagen.medicamento (nombre, presentacion, concentracion) VALUES ('Prueba','Tableta','1 mg');
DELETE FROM medimagen.medicamento WHERE nombre = 'Prueba';
SELECT * FROM medimagen.auditoria_acceso ORDER BY fecha DESC;
SELECT * FROM medimagen.horario_medico WHERE id_medico = 1 ORDER BY dia_semana, hora_inicio;

-- Eliminar usuarios: el administrador puede, pero MySQL lo bloquea (error 1451) si el usuario ya tiene accesos,
-- citas o resultados registrados. Para un usuario nunca usado funciona (se crea y se elimina):
INSERT INTO medimagen.paciente (cedula_paciente, nombres, apellidos, fecha_nacimiento, sexo)
VALUES ('0000000097', 'Prueba', 'Eliminar', '1990-01-01', 'M');
INSERT INTO medimagen.usuario (cedula, id_rol, cedula_paciente, nombres, apellidos, nombre_usuario, correo, password_hash)
SELECT '0000000097', id_rol, '0000000097', 'Prueba', 'Eliminar', 'pruebaelim', 'pruebaelim@medimagen.ec', 'x'
FROM medimagen.rol WHERE nombre = 'paciente';
DELETE FROM medimagen.usuario WHERE nombre_usuario = 'pruebaelim';
DELETE FROM medimagen.paciente WHERE cedula_paciente = '0000000097';

-- Debe dar error 1451 (el usuario tiene accesos registrados, se debe desactivar):
DELETE FROM medimagen.usuario WHERE nombre_usuario = 'candrade';

-- Debe dar error de permisos (1044 o 1142):
DROP TABLE medimagen.usuario;
TRUNCATE TABLE medimagen.auditoria_cita;       -- la auditoria no se puede vaciar
TRUNCATE TABLE medimagen.auditoria_acceso;
DELETE FROM medimagen.auditoria_cita;
DROP TABLE medimagen.auditoria_acceso;

CREATE DATABASE otra_bd;
DROP DATABASE medimagen;   -- ejecutala al final; debe fallar

-- ---------------------------------------------------------------------
-- C. Con usr_login (conexion nueva, clave uno234cinco)
-- ---------------------------------------------------------------------
-- Debe funcionar:
SELECT cedula, nombre_usuario, password_hash, id_rol, estado, intentos_fallidos, bloqueado_hasta, cambio_clave_obligatorio
FROM medimagen.usuario WHERE cedula = '0000000021';
UPDATE medimagen.usuario SET intentos_fallidos = intentos_fallidos + 1 WHERE cedula = '0000000021';
UPDATE medimagen.usuario SET intentos_fallidos = 0, ultimo_acceso = NOW() WHERE cedula = '0000000021';
INSERT INTO medimagen.auditoria_acceso (cedula_intento, id_usuario, resultado, ip, navegador)
VALUES ('0000000021', 14, 'exitoso', '127.0.0.1', 'Prueba');

-- Debe dar error 1142 / 1143 / 1054:
SELECT * FROM medimagen.paciente;
SELECT * FROM medimagen.auditoria_acceso;
SELECT correo FROM medimagen.usuario;
UPDATE medimagen.usuario SET id_rol = 1 WHERE cedula = '0000000021';
UPDATE medimagen.usuario SET estado = 'activo' WHERE cedula = '0000000021';

-- ---------------------------------------------------------------------
-- D. Con usr_paciente (conexion nueva, clave uno234cinco)
-- ---------------------------------------------------------------------
SELECT * FROM medimagen.v_agenda_consultas;          -- funciona
SELECT * FROM medimagen.paciente;                    -- error 1142
INSERT INTO medimagen.rol (nombre) VALUES ('x');     -- error 1142

-- ---------------------------------------------------------------------
-- E. Con usr_recepcion (conexion nueva, clave uno234cinco)
-- ---------------------------------------------------------------------
SELECT * FROM medimagen.paciente;                    -- funciona
SELECT * FROM medimagen.horario_medico;              -- funciona (solo lectura)
SELECT * FROM medimagen.consulta_medica;             -- error 1142 (sin datos clinicos)
UPDATE medimagen.cita SET costo_aplicado = 0 WHERE id_cita = 18;   -- error 1143 (el costo lo fija el trigger)
INSERT INTO medimagen.horario_medico (id_medico, dia_semana, hora_inicio, hora_fin)
VALUES (1, 1, '07:00:00', '08:00:00');               -- error 1142 (solo el administrador cambia turnos)