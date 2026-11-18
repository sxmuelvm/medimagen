-- =====================================================================
-- MEDIMAGEN | 06_consultas.sql
-- Las 10 consultas del proyecto. Ejecutar con root, EN ORDEN, sobre la base recien creada.
-- La 2 crea una cita, la 3 la reprograma y la 5 la atiende.
-- Para repetirlas hay que volver a crear la base (00 al 05).
-- =====================================================================
USE medimagen;

-- 1. READ | Recepción (ccriollo) | Horarios libres del consultorio 1 el 2026-11-11
--    Muestra los bloques que no tienen cita activa. Esperado: 10 bloques (falta el de las 09:00)
SELECT b.hora_inicio, b.hora_fin
FROM bloque_horario b
LEFT JOIN cita c ON c.hora_inicio = b.hora_inicio
                AND c.id_recurso = 1
                AND c.fecha_cita = '2026-11-11'
                AND c.estado NOT IN ('cancelada','no_asistio')
WHERE c.id_cita IS NULL
ORDER BY b.hora_inicio;

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

-- 4. DELETE | Administrador (admin) | Eliminar una cita cancelada y ver su registro en la auditoría
DELETE FROM cita
WHERE id_cita = 17 AND estado = 'cancelada';

SELECT id_cita, estado_anterior, estado_nuevo, usuario_bd, fecha_cambio
FROM auditoria_cita
WHERE id_cita = 17;

-- 5. CREATE | Médico (cmarin) | Registrar la atención, el diagnóstico y la receta de esa cita
--    Ejecuta todo el bloque junto, porque usa variables (@)
START TRANSACTION;

SET @id_cita = (SELECT id_cita FROM cita
                WHERE cedula_paciente = '0000000024' AND fecha_cita = '2026-11-18' AND id_area = 1);

INSERT INTO consulta_medica (id_cita, fecha_hora_atencion, motivo_consulta, observaciones)
VALUES (@id_cita, '2026-11-18 12:00:00', 'Control de rutina', 'Sin novedades');
SET @id_consulta = LAST_INSERT_ID();

INSERT INTO diagnostico (id_consulta, descripcion, observacion)
VALUES (@id_consulta, 'Paciente sano', 'Control anual');

INSERT INTO prescripcion (id_consulta, indicaciones_generales)
VALUES (@id_consulta, 'Mantener hábitos saludables');
SET @id_prescripcion = LAST_INSERT_ID();

INSERT INTO detalle_prescripcion (id_prescripcion, id_medicamento, dosis, frecuencia, duracion)
VALUES (@id_prescripcion, 9, '1 tableta', 'Cada 24 horas', '30 días');

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

-- 7. CREATE + READ | Administrador (admin) | Crear la cuenta de un recepcionista (perfil + usuario)
--    La contraseña va como hash (el de uno234cinco). Flask lo genera con werkzeug
START TRANSACTION;
INSERT INTO personal (cedula, nombres, apellidos, telefono, correo, cargo)
VALUES ('0000000031', 'Laura', 'Mendieta Cobos', '0960000031', 'laura.mendieta@medimagen.ec', 'Recepcionista');

INSERT INTO usuario (cedula, id_rol, id_personal, nombres, apellidos, nombre_usuario, correo, password_hash)
VALUES ('0000000031', 2,
        (SELECT id_personal FROM personal WHERE cedula = '0000000031'),
        'Laura', 'Mendieta Cobos', 'lmendieta', 'laura.mendieta@medimagen.ec',
        'pbkdf2:sha256:1000000$B6H7bOn922NqQi5j$0b4c23fafb117e8a7c093bc856036717abfa6304426f43f8958de0df3b0ce82c');
COMMIT;

SELECT u.cedula, u.nombres, u.apellidos, u.nombre_usuario, r.nombre AS rol, pe.cargo, u.estado
FROM usuario u
JOIN rol r ON r.id_rol = u.id_rol
JOIN personal pe ON pe.id_personal = u.id_personal
WHERE u.cedula = '0000000031';

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
       d.descripcion AS diagnostico,
       md.nombre AS medicamento, dp.dosis, dp.frecuencia, dp.duracion
FROM consulta_medica cm
JOIN cita c ON c.id_cita = cm.id_cita
JOIN diagnostico d ON d.id_consulta = cm.id_consulta
JOIN prescripcion pr ON pr.id_consulta = cm.id_consulta
JOIN detalle_prescripcion dp ON dp.id_prescripcion = pr.id_prescripcion
JOIN medicamento md ON md.id_medicamento = dp.id_medicamento
WHERE c.cedula_paciente = '0000000024'
ORDER BY cm.fecha_hora_atencion DESC;