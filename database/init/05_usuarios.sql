-- =====================================================================
-- MEDIMAGEN2 | 05_usuarios.sql
-- Cuentas de MySQL (host '%': sirve en local y en Docker), privilegios directos
-- y asignacion de roles. Ejecutar con root.
-- En Docker el puerto de MySQL solo se publica en 127.0.0.1, por eso '%' es seguro.
-- =====================================================================

-- Creacion de usuarios
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
GRANT SELECT ON medimagen2.v_reporte_ingresos TO 'usr_reportes'@'%';

-- usr_login: solo autenticacion. Lee las columnas necesarias, actualiza solo las del login
-- 
GRANT SELECT (id_usuario, id_rol, cedula, nombres, apellidos,
              nombre_usuario, password, estado, intentos_fallidos, bloqueado_hasta, cambio_clave_obligatorio)
    ON medimagen2.usuario TO 'usr_login'@'%';
GRANT UPDATE (ultimo_acceso, intentos_fallidos, bloqueado_hasta, cambio_clave_obligatorio, password)
    ON medimagen2.usuario TO 'usr_login'@'%';
GRANT SELECT ON medimagen2.rol TO 'usr_login'@'%';
-- Para saber el id_medico de quien entra (se busca por la cedula)
GRANT SELECT (id_medico, cedula) ON medimagen2.medico TO 'usr_login'@'%';

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