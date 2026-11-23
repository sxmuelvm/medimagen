-- =====================================================================
-- MEDIMAGEN2 | 00_limpieza.sql
-- Borra solo la base medimagen2 para volver a crearla desde cero.
-- NO borra cuentas ni roles de MySQL: son compartidos con la base medimagen y se vuelven a usar.
-- Ejecutar con root. Docker NO ejecuta este archivo (esta en extras/).
-- =====================================================================
DROP DATABASE IF EXISTS medimagen2;
