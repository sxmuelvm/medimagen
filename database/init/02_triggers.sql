-- =====================================================================
-- MEDIMAGEN | 02_triggers.sql
-- Triggers y procedimientos almacenados. Ejecutar con root.
-- =====================================================================
USE medimagen2;
DELIMITER $$

-- Códigos automáticos: ESP-01, RX-01, TAC-01, RM-01, DO-01, LAB-01
CREATE TRIGGER trg_especialidad_bi BEFORE INSERT ON especialidad
FOR EACH ROW
BEGIN
    DECLARE v_num INT;
    SELECT COALESCE(MAX(CAST(SUBSTRING(id_especialidad, 5) AS UNSIGNED)), 0) + 1 INTO v_num FROM especialidad;
    SET NEW.id_especialidad = CONCAT('ESP-', LPAD(v_num, GREATEST(2, CHAR_LENGTH(v_num)), '0'));
END$$

CREATE TRIGGER trg_subtipo_examen_bi BEFORE INSERT ON subtipo_examen
FOR EACH ROW
BEGIN
    DECLARE v_num INT;
    SELECT COALESCE(MAX(CAST(SUBSTRING_INDEX(id_subtipo, '-', -1) AS UNSIGNED)), 0) + 1 INTO v_num
    FROM subtipo_examen WHERE id_tipo = NEW.id_tipo;
    SET NEW.id_subtipo = CONCAT(NEW.id_tipo, '-', LPAD(v_num, GREATEST(2, CHAR_LENGTH(v_num)), '0'));
END$$

-- Usuario: una sola columna `cedula`. Segun el rol debe existir en la ficha correspondiente
-- (medico -> medico.cedula, paciente -> paciente.cedula_paciente); el resto del personal no tiene ficha.
-- Para medico y paciente los nombres y apellidos se copian de la ficha, asi no se repiten ni se contradicen.
CREATE PROCEDURE sp_validar_perfil_usuario(IN p_rol INT, IN p_cedula VARCHAR(10),
                                           INOUT p_nombres VARCHAR(100), INOUT p_apellidos VARCHAR(100))
BEGIN
    DECLARE v_rol VARCHAR(50) DEFAULT NULL;
    DECLARE v_nombres VARCHAR(100) DEFAULT NULL;
    DECLARE v_apellidos VARCHAR(100) DEFAULT NULL;
    SELECT nombre INTO v_rol FROM rol WHERE id_rol = p_rol;
    IF v_rol = 'medico' THEN
        SELECT nombres, apellidos INTO v_nombres, v_apellidos FROM medico WHERE cedula = p_cedula;
        IF v_nombres IS NULL THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La cédula no pertenece a ningún médico registrado';
        END IF;
        SET p_nombres = v_nombres, p_apellidos = v_apellidos;
    ELSEIF v_rol = 'paciente' THEN
        SELECT nombres, apellidos INTO v_nombres, v_apellidos FROM paciente WHERE cedula_paciente = p_cedula;
        IF v_nombres IS NULL THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La cédula no pertenece a ningún paciente registrado';
        END IF;
        SET p_nombres = v_nombres, p_apellidos = v_apellidos;
    END IF;
END$$

-- Nombre de usuario automatico: primera letra del primer nombre + primer apellido, en minusculas y sin tildes
-- (Cristian Marin -> cmarin). Si ya existe se agrega 01, 02, ... (cmarin01, cmarin02).
CREATE FUNCTION fn_nombre_usuario(p_nombres VARCHAR(100), p_apellidos VARCHAR(100)) RETURNS VARCHAR(50)
READS SQL DATA
BEGIN
    DECLARE v_base VARCHAR(50);
    DECLARE v_candidato VARCHAR(50);
    DECLARE v_n INT DEFAULT 0;
    SET v_base = LOWER(CONCAT(LEFT(TRIM(SUBSTRING_INDEX(TRIM(p_nombres), ' ', 1)), 1),
                              TRIM(SUBSTRING_INDEX(TRIM(p_apellidos), ' ', 1))));
    SET v_base = REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(v_base,
                 'á','a'),'é','e'),'í','i'),'ó','o'),'ú','u'),'ü','u'),'ñ','n');
    SET v_base = LEFT(REGEXP_REPLACE(v_base, '[^a-z0-9]', ''), 44);
    IF CHAR_LENGTH(v_base) < 4 THEN
        SET v_base = RPAD(v_base, 4, '0');
    END IF;
    SET v_candidato = v_base;
    WHILE EXISTS (SELECT 1 FROM usuario WHERE nombre_usuario = v_candidato) DO
        SET v_n = v_n + 1;
        SET v_candidato = CONCAT(v_base, LPAD(v_n, 2, '0'));
    END WHILE;
    RETURN v_candidato;
END$$

CREATE TRIGGER trg_usuario_bi BEFORE INSERT ON usuario
FOR EACH ROW
BEGIN
    CALL sp_validar_perfil_usuario(NEW.id_rol, NEW.cedula, NEW.nombres, NEW.apellidos);
    IF NEW.nombre_usuario IS NULL OR NEW.nombre_usuario = '' THEN
        SET NEW.nombre_usuario = fn_nombre_usuario(NEW.nombres, NEW.apellidos);
    END IF;
END$$

-- Solo se revalida cuando cambia el rol o la cedula. Asi el login
-- (intentos, bloqueo, ultimo acceso, clave) no ejecuta la validacion en cada UPDATE.
CREATE TRIGGER trg_usuario_bu BEFORE UPDATE ON usuario
FOR EACH ROW
BEGIN
    IF NOT (OLD.id_rol <=> NEW.id_rol AND OLD.cedula <=> NEW.cedula) THEN
        CALL sp_validar_perfil_usuario(NEW.id_rol, NEW.cedula, NEW.nombres, NEW.apellidos);
    END IF;
END$$

-- Un médico no puede tener dos consultas activas en el mismo bloque
CREATE PROCEDURE sp_validar_medico_libre(IN p_id_cita INT, IN p_id_medico INT, IN p_fecha DATE, IN p_hora TIME)
BEGIN
    IF EXISTS (SELECT 1
               FROM cita_consulta cc
               JOIN cita c ON c.id_cita = cc.id_cita
               WHERE cc.id_medico = p_id_medico
                 AND c.id_cita <> p_id_cita
                 AND c.fecha_cita = p_fecha
                 AND c.hora_inicio = p_hora
                 AND c.activa = 1) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El médico ya tiene una consulta en ese horario';
    END IF;
END$$

-- Una especialidad activa nunca se queda sin médico: no se puede desactivar, eliminar ni pasar a otra especialidad
-- al último médico activo que la atiende.
CREATE PROCEDURE sp_validar_cobertura_especialidad(IN p_id_medico INT, IN p_id_especialidad VARCHAR(10))
BEGIN
    IF EXISTS (SELECT 1 FROM especialidad WHERE id_especialidad = p_id_especialidad AND estado = 'activo')
       AND NOT EXISTS (SELECT 1 FROM medico WHERE id_especialidad = p_id_especialidad
                         AND estado = 'activo' AND id_medico <> p_id_medico) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Es el único médico activo de su especialidad: primero asigna otro médico a esa especialidad';
    END IF;
END$$

CREATE TRIGGER trg_medico_bu BEFORE UPDATE ON medico
FOR EACH ROW
BEGIN
    IF OLD.estado = 'activo' AND (NEW.estado <> 'activo' OR NEW.id_especialidad <> OLD.id_especialidad) THEN
        CALL sp_validar_cobertura_especialidad(OLD.id_medico, OLD.id_especialidad);
    END IF;
END$$

CREATE TRIGGER trg_medico_bd BEFORE DELETE ON medico
FOR EACH ROW
BEGIN
    IF EXISTS (SELECT 1 FROM usuario WHERE cedula = OLD.cedula) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El médico tiene un usuario asociado: desactívalo en lugar de eliminarlo';
    END IF;
    IF OLD.estado = 'activo' THEN
        CALL sp_validar_cobertura_especialidad(OLD.id_medico, OLD.id_especialidad);
    END IF;
END$$

-- Consulta: valida área 1, disponibilidad del médico y asigna el costo de la especialidad
CREATE PROCEDURE sp_preparar_consulta(IN p_id_cita INT, IN p_id_medico INT)
BEGIN
    DECLARE v_area INT;
    DECLARE v_fecha DATE;
    DECLARE v_hora TIME;
    DECLARE v_activa TINYINT;
    DECLARE v_costo DECIMAL(10,2);
    SELECT id_area, fecha_cita, hora_inicio, activa INTO v_area, v_fecha, v_hora, v_activa
    FROM cita WHERE id_cita = p_id_cita;
    IF v_area <> 1 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La cita no pertenece al área de consultas médicas';
    END IF;
    IF v_activa = 1 THEN
        CALL sp_validar_medico_libre(p_id_cita, p_id_medico, v_fecha, v_hora);
    END IF;
    SELECT e.costo_consulta INTO v_costo
    FROM medico m JOIN especialidad e ON e.id_especialidad = m.id_especialidad
    WHERE m.id_medico = p_id_medico;
    UPDATE cita SET costo_aplicado = v_costo WHERE id_cita = p_id_cita;
END$$

-- Imagenología (área 2) y laboratorio (área 3): valida el área y asigna el costo del examen
CREATE PROCEDURE sp_preparar_examen(IN p_id_cita INT, IN p_id_subtipo VARCHAR(10), IN p_area INT)
BEGIN
    DECLARE v_area_cita INT;
    DECLARE v_area_tipo INT;
    DECLARE v_costo DECIMAL(10,2);
    SELECT id_area INTO v_area_cita FROM cita WHERE id_cita = p_id_cita;
    SELECT t.id_area, s.costo INTO v_area_tipo, v_costo
    FROM subtipo_examen s JOIN tipo_procedimiento t ON t.id_tipo = s.id_tipo
    WHERE s.id_subtipo = p_id_subtipo;
    IF v_area_cita <> p_area OR v_area_tipo IS NULL OR v_area_tipo <> p_area THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La cita o el examen no pertenecen al área correspondiente';
    END IF;
    UPDATE cita SET costo_aplicado = v_costo WHERE id_cita = p_id_cita;
END$$

CREATE TRIGGER trg_cita_consulta_bi BEFORE INSERT ON cita_consulta
FOR EACH ROW
BEGIN
    CALL sp_preparar_consulta(NEW.id_cita, NEW.id_medico);
END$$

CREATE TRIGGER trg_cita_consulta_bu BEFORE UPDATE ON cita_consulta
FOR EACH ROW
BEGIN
    IF NOT (OLD.id_medico <=> NEW.id_medico) THEN
        CALL sp_preparar_consulta(NEW.id_cita, NEW.id_medico);
    END IF;
END$$

CREATE TRIGGER trg_cita_imagenologia_bi BEFORE INSERT ON cita_imagenologia
FOR EACH ROW
BEGIN
    CALL sp_preparar_examen(NEW.id_cita, NEW.id_subtipo, 2);
END$$

CREATE TRIGGER trg_cita_imagenologia_bu BEFORE UPDATE ON cita_imagenologia
FOR EACH ROW
BEGIN
    IF NOT (OLD.id_subtipo <=> NEW.id_subtipo) THEN
        CALL sp_preparar_examen(NEW.id_cita, NEW.id_subtipo, 2);
    END IF;
END$$

CREATE TRIGGER trg_cita_laboratorio_bi BEFORE INSERT ON cita_laboratorio
FOR EACH ROW
BEGIN
    CALL sp_preparar_examen(NEW.id_cita, NEW.id_subtipo, 3);
END$$

CREATE TRIGGER trg_cita_laboratorio_bu BEFORE UPDATE ON cita_laboratorio
FOR EACH ROW
BEGIN
    IF NOT (OLD.id_subtipo <=> NEW.id_subtipo) THEN
        CALL sp_preparar_examen(NEW.id_cita, NEW.id_subtipo, 3);
    END IF;
END$$

-- Al reprogramar o reactivar una consulta, el médico no puede quedar con dos pacientes en el mismo bloque
CREATE TRIGGER trg_cita_bu BEFORE UPDATE ON cita
FOR EACH ROW
BEGIN
    DECLARE v_medico INT DEFAULT NULL;
    IF NEW.estado NOT IN ('cancelada','no_asistio')
       AND (NEW.fecha_cita <> OLD.fecha_cita OR NEW.hora_inicio <> OLD.hora_inicio
            OR OLD.estado IN ('cancelada','no_asistio')) THEN
        SELECT id_medico INTO v_medico FROM cita_consulta WHERE id_cita = NEW.id_cita;
        IF v_medico IS NOT NULL THEN
            CALL sp_validar_medico_libre(NEW.id_cita, v_medico, NEW.fecha_cita, NEW.hora_inicio);
        END IF;
    END IF;
END$$

-- Una cita atendida forma parte del historial clínico y no se elimina
CREATE TRIGGER trg_cita_bd BEFORE DELETE ON cita
FOR EACH ROW
BEGIN
    IF OLD.estado = 'atendida' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'No se puede eliminar una cita atendida: forma parte del historial clínico';
    END IF;
END$$

-- Al desactivar a un paciente se desactiva también su usuario (recepción puede desactivar pacientes pero no ve usuarios).
-- Si cambian sus nombres, también cambian en el usuario (así no se repiten datos distintos).
CREATE TRIGGER trg_paciente_au AFTER UPDATE ON paciente
FOR EACH ROW
BEGIN
    IF NEW.estado = 'inactivo' AND OLD.estado <> 'inactivo' THEN
        UPDATE usuario u JOIN rol r ON r.id_rol = u.id_rol
        SET u.estado = 'inactivo'
        WHERE u.cedula = NEW.cedula_paciente AND r.nombre = 'paciente' AND u.estado = 'activo';
    END IF;
    IF NOT (OLD.nombres <=> NEW.nombres AND OLD.apellidos <=> NEW.apellidos) THEN
        UPDATE usuario u JOIN rol r ON r.id_rol = u.id_rol
        SET u.nombres = NEW.nombres, u.apellidos = NEW.apellidos
        WHERE u.cedula = NEW.cedula_paciente AND r.nombre = 'paciente';
    END IF;
END$$

-- Un paciente con usuario no se elimina (se desactiva)
CREATE TRIGGER trg_paciente_bd BEFORE DELETE ON paciente
FOR EACH ROW
BEGIN
    IF EXISTS (SELECT 1 FROM usuario WHERE cedula = OLD.cedula_paciente) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El paciente tiene un usuario asociado: desactívalo en lugar de eliminarlo';
    END IF;
END$$

-- Si cambian los nombres de un médico, también cambian en su usuario
CREATE TRIGGER trg_medico_au AFTER UPDATE ON medico
FOR EACH ROW
BEGIN
    IF NOT (OLD.nombres <=> NEW.nombres AND OLD.apellidos <=> NEW.apellidos) THEN
        UPDATE usuario u JOIN rol r ON r.id_rol = u.id_rol
        SET u.nombres = NEW.nombres, u.apellidos = NEW.apellidos
        WHERE u.cedula = NEW.cedula AND r.nombre = 'medico';
    END IF;
END$$

-- El paciente edita solo su teléfono y correo (la cédula la pone la sesión, nunca el formulario)
CREATE PROCEDURE sp_paciente_actualizar_contacto(IN p_cedula VARCHAR(10), IN p_telefono VARCHAR(15),
    IN p_correo VARCHAR(100))
BEGIN
    UPDATE paciente SET telefono = p_telefono, correo = p_correo
    WHERE cedula_paciente = p_cedula AND estado = 'activo';
    IF ROW_COUNT() = 0 AND NOT EXISTS (SELECT 1 FROM paciente WHERE cedula_paciente = p_cedula
                                       AND telefono <=> p_telefono AND correo <=> p_correo) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'No se pudo actualizar tu información';
    END IF;
END$$

-- El paciente cancela solo sus propias citas, pendientes o confirmadas, que aún no empezaron
CREATE PROCEDURE sp_paciente_cancelar_cita(IN p_cedula VARCHAR(10), IN p_id_cita INT)
BEGIN
    DECLARE v_estado VARCHAR(20) DEFAULT NULL;
    DECLARE v_area INT DEFAULT NULL;
    DECLARE v_futura TINYINT DEFAULT 0;
    DECLARE v_examen VARCHAR(20) DEFAULT NULL;
    SELECT estado, id_area, TIMESTAMP(fecha_cita, hora_inicio) > NOW()
      INTO v_estado, v_area, v_futura
    FROM cita WHERE id_cita = p_id_cita AND cedula_paciente = p_cedula;
    IF v_estado IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La cita no existe';
    END IF;
    IF v_estado NOT IN ('pendiente', 'confirmada') OR v_futura = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Solo puedes cancelar citas pendientes que aún no han empezado';
    END IF;
    IF v_area = 2 THEN
        SELECT estado_procedimiento INTO v_examen FROM cita_imagenologia WHERE id_cita = p_id_cita;
    ELSEIF v_area = 3 THEN
        SELECT estado_examen INTO v_examen FROM cita_laboratorio WHERE id_cita = p_id_cita;
    END IF;
    IF v_examen IS NOT NULL AND v_examen <> 'pendiente' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Solo puedes cancelar citas pendientes que aún no han empezado';
    END IF;
    UPDATE cita SET estado = 'cancelada' WHERE id_cita = p_id_cita;
    IF v_area = 2 THEN
        UPDATE cita_imagenologia SET estado_procedimiento = 'cancelado' WHERE id_cita = p_id_cita;
    ELSEIF v_area = 3 THEN
        UPDATE cita_laboratorio SET estado_examen = 'cancelado' WHERE id_cita = p_id_cita;
    END IF;
END$$

-- Horarios libres de un recurso (y opcionalmente de un médico) en una fecha: lunes a viernes, bloques de 60 minutos
-- desde las 07:00 hasta las 17:00 (el último paciente se agenda a las 17:00)
CREATE PROCEDURE sp_horarios_disponibles(IN p_fecha DATE, IN p_id_recurso INT, IN p_id_medico INT)
BEGIN
    WITH RECURSIVE h (hora) AS (
        SELECT 7 UNION ALL SELECT hora + 1 FROM h WHERE hora < 17
    )
    SELECT MAKETIME(h.hora, 0, 0) AS hora_inicio, MAKETIME(h.hora + 1, 0, 0) AS hora_fin
    FROM h
    WHERE WEEKDAY(p_fecha) < 5
      AND NOT EXISTS (SELECT 1 FROM cita c
                      WHERE c.id_recurso = p_id_recurso AND c.fecha_cita = p_fecha
                        AND c.hora_inicio = MAKETIME(h.hora, 0, 0) AND c.activa = 1)
      AND (p_id_medico IS NULL OR NOT EXISTS (SELECT 1 FROM cita c
                      JOIN cita_consulta cc ON cc.id_cita = c.id_cita
                      WHERE cc.id_medico = p_id_medico AND c.fecha_cita = p_fecha
                        AND c.hora_inicio = MAKETIME(h.hora, 0, 0) AND c.activa = 1))
    ORDER BY h.hora;
END$$

DELIMITER ;