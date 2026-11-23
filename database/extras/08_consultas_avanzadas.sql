-- =====================================================================
-- MEDIMAGEN | 08_consultas_avanzadas.sql
-- 10 consultas de nivel medio-avanzado. Solo leen datos (SELECT): se pueden ejecutar
-- en cualquier orden y todas las veces que quieras. Ejecutar sobre la base recién creada (00 al 05).
-- Cada una indica qué aprendes con ella y qué resultado esperar con los datos de ejemplo.
-- =====================================================================
USE medimagen2;

-- 1. GROUP BY + CASE | Recepción | Cuántas citas hay por área y en qué estado están
--    Aprendes: contar con condiciones (SUM + CASE) para armar una tabla resumen.
SELECT a.nombre AS area,
       COUNT(*) AS total,
       SUM(CASE WHEN c.estado = 'atendida'  THEN 1 ELSE 0 END) AS atendidas,
       SUM(CASE WHEN c.estado = 'cancelada' THEN 1 ELSE 0 END) AS canceladas,
       SUM(CASE WHEN c.estado IN ('pendiente','confirmada') THEN 1 ELSE 0 END) AS por_atender
FROM cita c
JOIN area a ON a.id_area = c.id_area
GROUP BY a.id_area, a.nombre
ORDER BY a.id_area;

-- 2. SUM + GROUP BY | Administrador | Dinero facturado por especialidad (solo consultas atendidas)
--    Aprendes: sumar un valor por grupo y ordenar de mayor a menor.
SELECT e.nombre AS especialidad,
       COUNT(*) AS consultas,
       SUM(c.costo_aplicado) AS total_facturado
FROM cita c
JOIN cita_consulta cc ON cc.id_cita = c.id_cita
JOIN medico m ON m.id_medico = cc.id_medico
JOIN especialidad e ON e.id_especialidad = m.id_especialidad
WHERE c.estado = 'atendida'
GROUP BY e.id_especialidad, e.nombre
ORDER BY total_facturado DESC;

-- 3. COUNT + ORDER BY + LIMIT | Administrador | Los 5 médicos con más consultas
--    Aprendes: ranking "top N".
SELECT CONCAT(m.nombres, ' ', m.apellidos) AS medico,
       e.nombre AS especialidad,
       COUNT(*) AS consultas
FROM cita_consulta cc
JOIN medico m ON m.id_medico = cc.id_medico
JOIN especialidad e ON e.id_especialidad = m.id_especialidad
JOIN cita c ON c.id_cita = cc.id_cita
WHERE c.estado <> 'cancelada'
GROUP BY m.id_medico, m.nombres, m.apellidos, e.nombre
ORDER BY consultas DESC, medico
LIMIT 5;

-- 4. LEFT JOIN + IS NULL | Recepción | Pacientes que nunca han tenido una cita
--    Aprendes: encontrar "lo que no tiene relación" (LEFT JOIN y filtrar los NULL).
SELECT p.cedula_paciente,
       CONCAT(p.nombres, ' ', p.apellidos) AS paciente,
       p.telefono
FROM paciente p
LEFT JOIN cita c ON c.cedula_paciente = p.cedula_paciente
WHERE c.id_cita IS NULL
ORDER BY p.apellidos;

-- 5. NOT EXISTS | Administrador | Médicos activos que todavía no tienen ninguna consulta
--    Aprendes: subconsulta correlacionada (la subconsulta usa datos de la consulta de afuera).
SELECT m.id_medico, CONCAT(m.nombres, ' ', m.apellidos) AS medico, e.nombre AS especialidad
FROM medico m
JOIN especialidad e ON e.id_especialidad = m.id_especialidad
WHERE m.estado = 'activo'
  AND NOT EXISTS (SELECT 1 FROM cita_consulta cc WHERE cc.id_medico = m.id_medico)
ORDER BY e.nombre, m.apellidos;

-- 6. Subconsulta con AVG | Administrador | Pacientes que han gastado más que el promedio
--    Aprendes: comparar el total de cada paciente contra un valor calculado por otra consulta.
SELECT p.cedula_paciente,
       CONCAT(p.nombres, ' ', p.apellidos) AS paciente,
       SUM(c.costo_aplicado) AS total_gastado
FROM paciente p
JOIN cita c ON c.cedula_paciente = p.cedula_paciente
WHERE c.estado = 'atendida'
GROUP BY p.cedula_paciente, p.nombres, p.apellidos
HAVING SUM(c.costo_aplicado) > (SELECT AVG(costo_aplicado) FROM cita WHERE estado = 'atendida')
ORDER BY total_gastado DESC;

-- 7. COUNT + LEFT JOIN | Administrador | Uso de cada consultorio, equipo y puesto (aunque no tenga citas)
--    Aprendes: LEFT JOIN para que también salgan los recursos con 0 citas.
SELECT r.nombre_recurso AS recurso,
       a.nombre AS area,
       COUNT(c.id_cita) AS citas_activas
FROM recurso_atencion r
JOIN area a ON a.id_area = r.id_area
LEFT JOIN cita c ON c.id_recurso = r.id_recurso AND c.estado <> 'cancelada'
GROUP BY r.id_recurso, r.nombre_recurso, a.nombre
ORDER BY a.nombre, citas_activas DESC;

-- 8. UNION ALL + GROUP BY | Imagenología y laboratorio | Los 5 exámenes más solicitados
--    Aprendes: juntar dos tablas con UNION ALL, agrupar por el nombre del examen y rankear.
SELECT t.nombre AS tipo,
       s.nombre AS examen,
       COUNT(*) AS veces_solicitado
FROM (SELECT id_subtipo FROM cita_imagenologia
      UNION ALL
      SELECT id_subtipo FROM cita_laboratorio) pedidos
JOIN subtipo_examen s ON s.id_subtipo = pedidos.id_subtipo
JOIN tipo_procedimiento t ON t.id_tipo = s.id_tipo
GROUP BY s.id_subtipo, t.nombre, s.nombre
ORDER BY veces_solicitado DESC, examen
LIMIT 5;

-- 9. DAYNAME + GROUP BY | Recepción | ¿Qué día de la semana tiene más citas?
--    Aprendes: funciones de fecha (DAYOFWEEK / DAYNAME) para analizar la demanda.
SELECT DAYOFWEEK(fecha_cita) AS numero_dia,
       ELT(DAYOFWEEK(fecha_cita), 'Domingo','Lunes','Martes','Miércoles','Jueves','Viernes','Sábado') AS dia,
       COUNT(*) AS citas
FROM cita
WHERE estado <> 'cancelada'
GROUP BY numero_dia, dia
ORDER BY citas DESC;

-- 10. JOIN con roles + CASE | Administrador | Usuarios por rol, cuántos están activos y los nombres de usuario repetidos
--     Aprendes: resumen por rol y detectar los nombres de usuario que llevan número (cmarin01, cmarin02...).
SELECT r.nombre AS rol,
       COUNT(*) AS usuarios,
       SUM(CASE WHEN u.estado = 'activo' THEN 1 ELSE 0 END) AS activos,
       SUM(CASE WHEN u.nombre_usuario REGEXP '[0-9]{2}$' THEN 1 ELSE 0 END) AS con_numero
FROM usuario u
JOIN rol r ON r.id_rol = u.id_rol
GROUP BY r.id_rol, r.nombre
ORDER BY usuarios DESC;
