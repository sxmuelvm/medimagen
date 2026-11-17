-- =====================================================================
-- MEDIMAGEN | 05_usuarios.sql
-- Cuentas de MySQL (host '%': sirve en local y en Docker), privilegios directos
-- y asignacion de roles. Ejecutar con root.
-- En Docker el puerto de MySQL solo se publica en 127.0.0.1, por eso '%' es seguro.
-- =====================================================================

-- Creacion de usuarios
CREATE USER IF NOT EXISTS 'dba_medimagen'@'%' IDENTIFIED BY 'uno234cinco'
    WITH MAX_USER_CONNECTIONS 5 PASSWORD EXPIRE INTERVAL 90 DAY FAILED_LOGIN_ATTEMPTS 5 PASSWORD_LOCK_TIME 1;
CREATE USER IF NOT EXISTS 'usr_administrador'@'%' IDENTIFIED BY 'uno234cinco' WITH MAX_USER_CONNECTIONS 10;
CREATE USER IF NOT EXISTS 'usr_recepcion'@'%' IDENTIFIED BY 'uno234cinco' WITH MAX_USER_CONNECTIONS 20;
CREATE USER IF NOT EXISTS 'usr_medico'@'%' IDENTIFIED BY 'uno234cinco' WITH MAX_USER_CONNECTIONS 20;
CREATE USER IF NOT EXISTS 'usr_imagenologia'@'%' IDENTIFIED BY 'uno234cinco' WITH MAX_USER_CONNECTIONS 10;
CREATE USER IF NOT EXISTS 'usr_laboratorio'@'%' IDENTIFIED BY 'uno234cinco' WITH MAX_USER_CONNECTIONS 10;
CREATE USER IF NOT EXISTS 'usr_paciente'@'%' IDENTIFIED BY 'uno234cinco' WITH MAX_USER_CONNECTIONS 30;
CREATE USER IF NOT EXISTS 'usr_respaldo'@'%' IDENTIFIED BY 'uno234cinco' WITH MAX_USER_CONNECTIONS 2;
CREATE USER IF NOT EXISTS 'usr_reportes'@'%' IDENTIFIED BY 'uno234cinco' WITH MAX_USER_CONNECTIONS 5;
CREATE USER IF NOT EXISTS 'usr_login'@'%' IDENTIFIED BY 'uno234cinco' WITH MAX_USER_CONNECTIONS 20;

-- Usuarios con privilegios especificos (directos, sin rol)
GRANT ALL PRIVILEGES ON medimagen.* TO 'dba_medimagen'@'%' WITH GRANT OPTION;
GRANT SELECT ON medimagen.v_reporte_ingresos TO 'usr_reportes'@'%';

-- usr_login: solo autenticacion. Lee las columnas necesarias, actualiza solo las del login
-- y puede insertar (nunca leer ni modificar) en el registro de accesos.
GRANT SELECT (id_usuario, cedula, id_rol, id_medico, cedula_paciente, id_personal, nombres, apellidos,
              nombre_usuario, password_hash, estado, intentos_fallidos, bloqueado_hasta, cambio_clave_obligatorio)
    ON medimagen.usuario TO 'usr_login'@'%';
GRANT UPDATE (ultimo_acceso, intentos_fallidos, bloqueado_hasta, cambio_clave_obligatorio, password_hash)
    ON medimagen.usuario TO 'usr_login'@'%';
GRANT SELECT ON medimagen.rol TO 'usr_login'@'%';
GRANT INSERT ON medimagen.auditoria_acceso TO 'usr_login'@'%';

-- Asignacion de roles a usuarios
GRANT 'rol_administrador' TO 'usr_administrador'@'%';
GRANT 'rol_recepcion' TO 'usr_recepcion'@'%';
GRANT 'rol_medico' TO 'usr_medico'@'%';
GRANT 'rol_imagenologia' TO 'usr_imagenologia'@'%';
GRANT 'rol_laboratorio' TO 'usr_laboratorio'@'%';
GRANT 'rol_paciente' TO 'usr_paciente'@'%';
GRANT 'rol_respaldo' TO 'usr_respaldo'@'%';

-- Activar el rol al iniciar sesion
SET DEFAULT ROLE ALL TO 'usr_administrador'@'%', 'usr_recepcion'@'%', 'usr_medico'@'%',
    'usr_imagenologia'@'%', 'usr_laboratorio'@'%', 'usr_paciente'@'%', 'usr_respaldo'@'%';
