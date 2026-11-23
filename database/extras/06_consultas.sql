-- =====================================================================
-- MEDIMAGEN | 06_consultas.sql
-- Las 10 consultas del proyecto (CRUD). Más consultas de análisis en 08_consultas_avanzadas.sql. Ejecutar con root, EN ORDEN, sobre la base recien creada.
-- La 2 crea una cita, la 3 la reprograma y la 5 la atiende.
-- Para repetirlas hay que volver a crear la base (00 al 05).
-- =====================================================================
USE medimagen2;

-- 1. READ | Recepción (ccriollo) | Horarios libres del consultorio 1 el 2026-11-11
--    El procedimiento genera los bloques de 07:00 a 17:00 y quita los que ya tienen cita activa.
--    Esperado: 10 bloques (falta el de las 09:00)
CALL sp_horarios_disponibles('2026-11-11', 1, NULL);

-- 2. CREATE | Recepción (ccriollo) | Agendar una consulta para Ana Cordero con el médico 2
--    Los triggers validan el horario y asignan el costo (20.00)
START TRANSACTION;
INSERT INTO cita (cedula_paciente, id_area, id_recurso, id_usuario_registra, fecha_cita, hora_inicio, hora_fin, estado)
VALUES ('0000000024', 1, 2, 2, '2026-11-17', '10:00:00', '11:00:00', 'pendiente');
INSERT INTO cita_consulta (id_cita, id_medico) VALUES (LAST_INSERT_ID(), 2);
COMMIT;

SELECT id_cita, cedula_paciente, fecha_cita, hora_inicio, estado, costo_aplicado
FROM cita
WHERE cedula_paciente = '0000000024' AND fecha_cita = '2026-11-17';

-- 3. UPDATE | Recepción (ccriollo) | Reprogramar esa cita al 2026-11-18 a las 12:00
UPDATE cita
SET fecha_cita = '2026-11-18', hora_inicio = '12:00:00', hora_fin = '13:00:00'
WHERE cedula_paciente = '0000000024'
  AND fecha_cita = '2026-11-17'
  AND estado = 'pendiente';

-- 4. DELETE | Administrador (admin) | Eliminar una cita cancelada
DELETE FROM cita
WHERE id_cita = 17 AND estado = 'cancelada';

SELECT COUNT(*) AS citas_con_id_17 FROM cita WHERE id_cita = 17;   -- Esperado: 0

-- 5. CREATE | Médico (cmarin) | Registrar la atención, el diagnóstico y la receta de esa cita
--    Ejecuta todo el bloque junto, porque usa variables (@)
START TRANSACTION;

SET @id_cita = (SELECT id_cita FROM cita
                WHERE cedula_paciente = '0000000024' AND fecha_cita = '2026-11-18' AND id_area = 1);

INSERT INTO consulta_medica (id_cita, fecha_hora_atencion, motivo_consulta, diagnostico, observaciones)
VALUES (@id_cita, '2026-11-18 12:00:00', 'Control de rutina', 'Paciente sano', 'Control anual');
SET @id_consulta = LAST_INSERT_ID();

INSERT INTO prescripcion (id_consulta, indicaciones_generales)
VALUES (@id_consulta, 'Mantener hábitos saludables');
SET @id_prescripcion = LAST_INSERT_ID();

INSERT INTO detalle_prescripcion (id_prescripcion, medicamento, dosis, frecuencia, duracion)
VALUES (@id_prescripcion, 'Multivitamínico tableta', '1 tableta', 'Cada 24 horas', '30 días');

UPDATE cita SET estado = 'atendida' WHERE id_cita = @id_cita;

COMMIT;

-- 6. READ | Médico (cmarin) | Exámenes de imagenología que solicitó el médico 1 y su estado
SELECT c.fecha_cita, c.hora_inicio,
       CONCAT(p.nombres, ' ', p.apellidos) AS paciente,
       t.nombre AS tipo, s.nombre AS examen,
       ci.estado_procedimiento AS estado
FROM cita_imagenologia ci
JOIN cita c ON c.id_cita = ci.id_cita
JOIN paciente p ON p.cedula_paciente = c.cedula_paciente
JOIN subtipo_examen s ON s.id_subtipo = ci.id_subtipo
JOIN tipo_procedimiento t ON t.id_tipo = s.id_tipo
WHERE ci.id_medico_solicitante = 1
ORDER BY c.fecha_cita;

-- 7. CREATE + READ | Administrador (admin) | Crear la cuenta de un recepcionista
--    El personal no tiene tabla propia: el usuario lleva su cédula, nombres, apellidos y correo.
--    El nombre de usuario NO se escribe: MySQL lo genera solo (inicial del nombre + primer apellido: lmendieta;
--    si ya existe, lmendieta01, lmendieta02...). La contraseña va como hash (el de uno234cinco).
INSERT INTO usuario (id_rol, cedula, nombres, apellidos, correo, password, cambio_clave_obligatorio)
VALUES (2, '0000000060', 'Laura', 'Mendieta Cobos', 'laura.mendieta@medimagen.ec',
        'pbkdf2:sha256:1000000$B6H7bOn922NqQi5j$0b4c23fafb117e8a7c093bc856036717abfa6304426f43f8958de0df3b0ce82c', 1);

SELECT u.cedula, u.nombre_usuario, u.nombres, u.apellidos, r.nombre AS rol, u.estado   -- Esperado: lmendieta
FROM usuario u
JOIN rol r ON r.id_rol = u.id_rol
WHERE u.cedula = '0000000060';

-- 8. UPDATE | Personal de imagenología (mbajana) | Registrar la realización de un procedimiento pendiente
START TRANSACTION;
UPDATE cita_imagenologia
SET estado_procedimiento = 'realizado',
    fecha_realizacion = '2026-11-17 10:00:00',
    id_usuario_realiza = 5
WHERE id_cita = 18 AND estado_procedimiento = 'pendiente';

UPDATE cita
SET estado = 'atendida'
WHERE id_cita = 18;
COMMIT;

-- 9. READ | Personal de laboratorio (asornoza) | Pacientes con más de un examen realizado y total facturado
--    Esperado: Carlos Andrade, 2 exámenes, total 23.00
SELECT p.cedula_paciente, p.nombres, p.apellidos,
       COUNT(*) AS examenes,
       SUM(c.costo_aplicado) AS total
FROM cita_laboratorio cl
JOIN cita c ON c.id_cita = cl.id_cita
JOIN paciente p ON p.cedula_paciente = c.cedula_paciente
WHERE cl.estado_examen = 'realizado'
GROUP BY p.cedula_paciente, p.nombres, p.apellidos
HAVING COUNT(*) > 1;

-- 10. READ | Paciente (acordero) | Historial de Ana Cordero: diagnóstico y medicamentos recetados
--     Esperado: 2 filas (Taquicardia sinusal con Propranolol y Paciente sano con Multivitamínico)
SELECT cm.fecha_hora_atencion, cm.motivo_consulta,
       cm.diagnostico,
       dp.medicamento, dp.dosis, dp.frecuencia, dp.duracion
FROM consulta_medica cm
JOIN cita c ON c.id_cita = cm.id_cita
JOIN prescripcion pr ON pr.id_consulta = cm.id_consulta
JOIN detalle_prescripcion dp ON dp.id_prescripcion = pr.id_prescripcion
WHERE c.cedula_paciente = '0000000024'
ORDER BY cm.fecha_hora_atencion DESC;