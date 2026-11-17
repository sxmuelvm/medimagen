-- =====================================================================
-- MEDIMAGEN | 00_limpieza.sql
-- Borra la base y las cuentas de Medimagen para volver a crearlas desde cero.
-- Ejecutar con root. No toca ninguna otra base ni cuenta (profesor, prof_user, etc.).
-- Docker NO ejecuta este archivo (esta en extras/): el volumen nuevo ya llega vacio.
-- =====================================================================
DROP DATABASE IF EXISTS medimagen;

DROP USER IF EXISTS 'dba_medimagen'@'%';
DROP USER IF EXISTS 'usr_administrador'@'%';
DROP USER IF EXISTS 'usr_recepcion'@'%';
DROP USER IF EXISTS 'usr_medico'@'%';
DROP USER IF EXISTS 'usr_imagenologia'@'%';
DROP USER IF EXISTS 'usr_laboratorio'@'%';
DROP USER IF EXISTS 'usr_paciente'@'%';
DROP USER IF EXISTS 'usr_respaldo'@'%';
DROP USER IF EXISTS 'usr_reportes'@'%';
DROP USER IF EXISTS 'usr_login'@'%';

-- Restos de versiones anteriores (cuentas creadas solo para localhost)
DROP USER IF EXISTS 'dba_medimagen'@'localhost';
DROP USER IF EXISTS 'usr_administrador'@'localhost';
DROP USER IF EXISTS 'usr_recepcion'@'localhost';
DROP USER IF EXISTS 'usr_medico'@'localhost';
DROP USER IF EXISTS 'usr_imagenologia'@'localhost';
DROP USER IF EXISTS 'usr_laboratorio'@'localhost';
DROP USER IF EXISTS 'usr_paciente'@'localhost';
DROP USER IF EXISTS 'usr_respaldo'@'localhost';
DROP USER IF EXISTS 'usr_reportes'@'localhost';
DROP USER IF EXISTS 'usr_login'@'localhost';

DROP ROLE IF EXISTS 'rol_administrador', 'rol_recepcion', 'rol_medico',
                    'rol_imagenologia', 'rol_laboratorio', 'rol_paciente', 'rol_respaldo';
