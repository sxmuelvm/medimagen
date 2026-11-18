-- =====================================================================
-- MEDIMAGEN | 02_triggers.sql
-- Triggers y procedimientos almacenados. Ejecutar con root.
-- =====================================================================
USE medimagen;
DELIMITER $$

-- Códigos automáticos: ESP-01, RX-01, TAC-01, RM-01, DO-01, LAB-01
CREATE TRIGGER trg_especialidad_bi BEFORE INSERT ON especialidad
FOR EACH ROW
BEGIN
    DECLARE v_num INT;
    INSERT INTO secuencia_codigo (prefijo, ultimo_valor) VALUES ('ESP', 1)
        ON DUPLICATE KEY UPDATE ultimo_valor = ultimo_valor + 1;
    SELECT ultimo_valor INTO v_num FROM secuencia_codigo WHERE prefijo = 'ESP';
    SET NEW.id_especialidad = CONCAT('ESP-', LPAD(v_num, GREATEST(2, CHAR_LENGTH(v_num)), '0'));
END$$

CREATE TRIGGER trg_subtipo_examen_bi BEFORE INSERT ON subtipo_examen
FOR EACH ROW
BEGIN
    DECLARE v_num INT;
    INSERT INTO secuencia_codigo (prefijo, ultimo_valor) VALUES (NEW.id_tipo, 1)
        ON DUPLICATE KEY UPDATE ultimo_valor = ultimo_valor + 1;
    SELECT ultimo_valor INTO v_num FROM secuencia_codigo WHERE prefijo = NEW.id_tipo;
    SET NEW.id_subtipo = CONCAT(NEW.id_tipo, '-', LPAD(v_num, GREATEST(2, CHAR_LENGTH(v_num)), '0'));
END$$

-- Usuario: el perfil debe corresponder al rol y la cédula debe ser la del perfil
CREATE PROCEDURE sp_validar_perfil_usuario(IN p_rol INT, IN p_cedula VARCHAR(10),
    IN p_medico INT, IN p_paciente VARCHAR(10), IN p_personal INT)
BEGIN
    DECLARE v_rol VARCHAR(50) DEFAULT NULL;
    DECLARE v_cedula VARCHAR(10) DEFAULT NULL;
    SELECT nombre INTO v_rol FROM rol WHERE id_rol = p_rol;
    IF (v_rol = 'medico' AND p_medico IS NULL)
       OR (v_rol = 'paciente' AND p_paciente IS NULL)
       OR (v_rol NOT IN ('medico','paciente') AND p_personal IS NULL) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El perfil asociado no corresponde al rol del usuario';
    END IF;
    IF p_medico IS NOT NULL THEN
        SELECT cedula INTO v_cedula FROM medico WHERE id_medico = p_medico;
    ELSEIF p_paciente IS NOT NULL THEN
        SET v_cedula = p_paciente;
    ELSEIF p_personal IS NOT NULL THEN
        SELECT cedula INTO v_cedula FROM personal WHERE id_personal = p_personal;
    END IF;
    IF v_cedula IS NULL OR v_cedula <> p_cedula THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La cédula del usuario no coincide con la de su perfil';
    END IF;
END$$

CREATE TRIGGER trg_usuario_bi BEFORE INSERT ON usuario
FOR EACH ROW
BEGIN
    CALL sp_validar_perfil_usuario(NEW.id_rol, NEW.cedula, NEW.id_medico, NEW.cedula_paciente, NEW.id_personal);
END$$

-- Solo se revalida cuando cambia el rol, la cedula o el perfil. Asi el login
-- (intentos, bloqueo, ultimo acceso, clave) no ejecuta la validacion en cada UPDATE.
CREATE TRIGGER trg_usuario_bu BEFORE UPDATE ON usuario
FOR EACH ROW
BEGIN
    IF NOT (OLD.id_rol <=> NEW.id_rol AND OLD.cedula <=> NEW.cedula AND OLD.id_medico <=> NEW.id_medico
            AND OLD.cedula_paciente <=> NEW.cedula_paciente AND OLD.id_personal <=> NEW.id_personal) THEN
        CALL sp_validar_perfil_usuario(NEW.id_rol, NEW.cedula, NEW.id_medico, NEW.cedula_paciente, NEW.id_personal);
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

-- El médico solo atiende dentro de sus turnos (horario_medico). Sin turnos registrados se usa el horario general.
CREATE PROCEDURE sp_validar_turno_medico(IN p_id_medico INT, IN p_fecha DATE, IN p_hora TIME)
BEGIN
    IF EXISTS (SELECT 1 FROM horario_medico WHERE id_medico = p_id_medico)
       AND NOT EXISTS (SELECT 1 FROM horario_medico
                       WHERE id_medico = p_id_medico
                         AND dia_semana = WEEKDAY(p_fecha) + 1
                         AND hora_inicio <= p_hora
                         AND ADDTIME(p_hora, '01:00:00') <= hora_fin) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El médico no atiende en ese día u horario';
    END IF;
END$$

-- Turnos: la hora de fin debe terminar un bloque y los turnos de un mismo médico no se solapan
CREATE PROCEDURE sp_validar_horario_medico(IN p_id_horario INT, IN p_id_medico INT, IN p_dia TINYINT,
                                           IN p_inicio TIME, IN p_fin TIME)
BEGIN
    IF NOT EXISTS (SELECT 1 FROM bloque_horario WHERE hora_fin = p_fin) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La hora de fin no corresponde a un bloque horario';
    END IF;
    IF EXISTS (SELECT 1 FROM horario_medico
               WHERE id_medico = p_id_medico AND dia_semana = p_dia AND id_horario <> p_id_horario
                 AND hora_inicio < p_fin AND hora_fin > p_inicio) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El turno se cruza con otro turno del mismo médico';
    END IF;
END$$

CREATE TRIGGER trg_horario_medico_bi BEFORE INSERT ON horario_medico
FOR EACH ROW
BEGIN
    CALL sp_validar_horario_medico(0, NEW.id_medico, NEW.dia_semana, NEW.hora_inicio, NEW.hora_fin);
END$$

CREATE TRIGGER trg_horario_medico_bu BEFORE UPDATE ON horario_medico
FOR EACH ROW
BEGIN
    CALL sp_validar_horario_medico(OLD.id_horario, NEW.id_medico, NEW.dia_semana, NEW.hora_inicio, NEW.hora_fin);
END$$

-- Consulta: valida área 1, disponibilidad y turno del médico y asigna el costo de la especialidad
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
        CALL sp_validar_turno_medico(p_id_medico, v_fecha, v_hora);
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

-- Al reprogramar o reactivar una consulta, el médico no puede quedar con dos pacientes
-- y la nueva fecha y hora deben caer dentro de sus turnos
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
            CALL sp_validar_turno_medico(v_medico, NEW.fecha_cita, NEW.hora_inicio);
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

-- Auditoría: cuenta de MySQL (USER()) y persona del sistema (@app_usuario, lo define Flask)
CREATE TRIGGER trg_cita_au AFTER UPDATE ON cita
FOR EACH ROW
BEGIN
    IF NOT (OLD.estado <=> NEW.estado AND OLD.fecha_cita <=> NEW.fecha_cita AND OLD.hora_inicio <=> NEW.hora_inicio) THEN
        INSERT INTO auditoria_cita (id_cita, estado_anterior, estado_nuevo, fecha_anterior, fecha_nueva,
                                    hora_anterior, hora_nueva, usuario_bd, id_usuario_app)
        VALUES (OLD.id_cita, OLD.estado, NEW.estado, OLD.fecha_cita, NEW.fecha_cita,
                OLD.hora_inicio, NEW.hora_inicio, USER(), @app_usuario);
    END IF;
END$$

CREATE TRIGGER trg_cita_ad AFTER DELETE ON cita
FOR EACH ROW
BEGIN
    INSERT INTO auditoria_cita (id_cita, estado_anterior, estado_nuevo, fecha_anterior, hora_anterior,
                                usuario_bd, id_usuario_app)
    VALUES (OLD.id_cita, OLD.estado, 'eliminada', OLD.fecha_cita, OLD.hora_inicio, USER(), @app_usuario);
END$$

-- La auditoría no se puede alterar ni borrar
CREATE TRIGGER trg_auditoria_bu BEFORE UPDATE ON auditoria_cita
FOR EACH ROW
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La auditoría no se puede modificar'$$

CREATE TRIGGER trg_auditoria_bd BEFORE DELETE ON auditoria_cita
FOR EACH ROW
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La auditoría no se puede eliminar'$$

-- El registro de accesos tampoco se puede alterar ni borrar
CREATE TRIGGER trg_acceso_bu BEFORE UPDATE ON auditoria_acceso
FOR EACH ROW
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El registro de accesos no se puede modificar'$$

CREATE TRIGGER trg_acceso_bd BEFORE DELETE ON auditoria_acceso
FOR EACH ROW
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El registro de accesos no se puede eliminar'$$

-- Horarios libres de un recurso (y opcionalmente de un médico, dentro de sus turnos) en una fecha
CREATE PROCEDURE sp_horarios_disponibles(IN p_fecha DATE, IN p_id_recurso INT, IN p_id_medico INT)
BEGIN
    SELECT b.hora_inicio, b.hora_fin
    FROM bloque_horario b
    WHERE WEEKDAY(p_fecha) < 5
      AND NOT EXISTS (SELECT 1 FROM cita c
                      WHERE c.id_recurso = p_id_recurso AND c.fecha_cita = p_fecha
                        AND c.hora_inicio = b.hora_inicio AND c.activa = 1)
      AND (p_id_medico IS NULL OR NOT EXISTS (SELECT 1 FROM cita c
                      JOIN cita_consulta cc ON cc.id_cita = c.id_cita
                      WHERE cc.id_medico = p_id_medico AND c.fecha_cita = p_fecha
                        AND c.hora_inicio = b.hora_inicio AND c.activa = 1))
      AND (p_id_medico IS NULL
           OR NOT EXISTS (SELECT 1 FROM horario_medico h0 WHERE h0.id_medico = p_id_medico)
           OR EXISTS (SELECT 1 FROM horario_medico h
                      WHERE h.id_medico = p_id_medico AND h.dia_semana = WEEKDAY(p_fecha) + 1
                        AND h.hora_inicio <= b.hora_inicio AND b.hora_fin <= h.hora_fin))
    ORDER BY b.hora_inicio;
END$$

DELIMITER ;