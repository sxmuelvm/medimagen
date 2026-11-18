-- =====================================================================
-- MEDIMAGEN | 01_tablas_vistas.sql
-- Base de datos, 25 tablas y 8 vistas. Ejecutar con root.
-- =====================================================================
CREATE DATABASE medimagen CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE medimagen;

CREATE TABLE secuencia_codigo (
    prefijo VARCHAR(10) PRIMARY KEY,
    ultimo_valor INT NOT NULL DEFAULT 0
) ENGINE=InnoDB;

CREATE TABLE rol (
    id_rol INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    descripcion VARCHAR(255),
    estado ENUM('activo','inactivo') NOT NULL DEFAULT 'activo'
) ENGINE=InnoDB;

CREATE TABLE personal (
    id_personal INT AUTO_INCREMENT PRIMARY KEY,
    cedula VARCHAR(10) NOT NULL UNIQUE,
    nombres VARCHAR(100) NOT NULL,
    apellidos VARCHAR(100) NOT NULL,
    telefono VARCHAR(15),
    correo VARCHAR(100) UNIQUE,
    cargo VARCHAR(80) NOT NULL,
    estado ENUM('activo','inactivo') NOT NULL DEFAULT 'activo',
    CONSTRAINT chk_personal_cedula CHECK (cedula REGEXP '^[0-9]{10}$')
) ENGINE=InnoDB;

CREATE TABLE area (
    id_area INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    descripcion VARCHAR(255),
    estado ENUM('activo','inactivo') NOT NULL DEFAULT 'activo'
) ENGINE=InnoDB;

CREATE TABLE especialidad (
    id_especialidad VARCHAR(10) PRIMARY KEY,
    nombre VARCHAR(80) NOT NULL UNIQUE,
    descripcion VARCHAR(255),
    costo_consulta DECIMAL(10,2) NOT NULL,
    estado ENUM('activo','inactivo') NOT NULL DEFAULT 'activo',
    CONSTRAINT chk_esp_costo CHECK (costo_consulta >= 0)
) ENGINE=InnoDB;

CREATE TABLE bloque_horario (
    hora_inicio TIME PRIMARY KEY,
    hora_fin TIME NOT NULL,
    CONSTRAINT uq_bloque UNIQUE (hora_inicio, hora_fin),
    CONSTRAINT chk_bloque CHECK (hora_fin = ADDTIME(hora_inicio, '01:00:00'))
) ENGINE=InnoDB;

CREATE TABLE paciente (
    cedula_paciente VARCHAR(10) PRIMARY KEY,
    nombres VARCHAR(100) NOT NULL,
    apellidos VARCHAR(100) NOT NULL,
    fecha_nacimiento DATE NOT NULL,
    sexo ENUM('M','F') NOT NULL,
    telefono VARCHAR(15),
    correo VARCHAR(100) UNIQUE,
    direccion VARCHAR(200),
    fecha_registro DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    estado ENUM('activo','inactivo') NOT NULL DEFAULT 'activo',
    CONSTRAINT chk_pac_cedula CHECK (cedula_paciente REGEXP '^[0-9]{10}$')
) ENGINE=InnoDB;

CREATE TABLE medico (
    id_medico INT AUTO_INCREMENT PRIMARY KEY,
    id_especialidad VARCHAR(10) NOT NULL,
    cedula VARCHAR(10) NOT NULL UNIQUE,
    nombres VARCHAR(100) NOT NULL,
    apellidos VARCHAR(100) NOT NULL,
    telefono VARCHAR(15),
    correo VARCHAR(100) UNIQUE,
    estado ENUM('activo','inactivo') NOT NULL DEFAULT 'activo',
    CONSTRAINT fk_medico_especialidad FOREIGN KEY (id_especialidad) REFERENCES especialidad(id_especialidad),
    CONSTRAINT chk_med_cedula CHECK (cedula REGEXP '^[0-9]{10}$')
) ENGINE=InnoDB;

-- Turnos de atencion de cada medico: un tramo por fila (dia_semana 1 = lunes ... 5 = viernes).
-- Un medico sin turnos se atiende en el horario general. El almuerzo (13:00 a 15:00) lo aplica el sistema a todos.
CREATE TABLE horario_medico (
    id_horario INT AUTO_INCREMENT PRIMARY KEY,
    id_medico INT NOT NULL,
    dia_semana TINYINT NOT NULL,
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL,
    CONSTRAINT fk_hm_medico FOREIGN KEY (id_medico) REFERENCES medico(id_medico) ON DELETE CASCADE,
    CONSTRAINT fk_hm_inicio FOREIGN KEY (hora_inicio) REFERENCES bloque_horario(hora_inicio),
    CONSTRAINT uq_hm UNIQUE (id_medico, dia_semana, hora_inicio),
    CONSTRAINT chk_hm_dia CHECK (dia_semana BETWEEN 1 AND 5),
    CONSTRAINT chk_hm_horas CHECK (hora_fin > hora_inicio)
) ENGINE=InnoDB;

CREATE TABLE usuario (
    id_usuario INT AUTO_INCREMENT PRIMARY KEY,
    cedula VARCHAR(10) NOT NULL UNIQUE,
    id_rol INT NOT NULL,
    id_medico INT NULL UNIQUE,
    cedula_paciente VARCHAR(10) NULL UNIQUE,
    id_personal INT NULL UNIQUE,
    nombres VARCHAR(100) NOT NULL,
    apellidos VARCHAR(100) NOT NULL,
    nombre_usuario VARCHAR(50) NOT NULL UNIQUE,
    correo VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    estado ENUM('activo','inactivo','bloqueado') NOT NULL DEFAULT 'activo',
    fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ultimo_acceso DATETIME NULL,
    intentos_fallidos TINYINT UNSIGNED NOT NULL DEFAULT 0,
    bloqueado_hasta DATETIME NULL,
    cambio_clave_obligatorio TINYINT NOT NULL DEFAULT 0,
    CONSTRAINT fk_usuario_rol FOREIGN KEY (id_rol) REFERENCES rol(id_rol),
    CONSTRAINT fk_usuario_medico FOREIGN KEY (id_medico) REFERENCES medico(id_medico),
    CONSTRAINT fk_usuario_paciente FOREIGN KEY (cedula_paciente) REFERENCES paciente(cedula_paciente),
    CONSTRAINT fk_usuario_personal FOREIGN KEY (id_personal) REFERENCES personal(id_personal),
    CONSTRAINT chk_usuario_cedula CHECK (cedula REGEXP '^[0-9]{10}$'),
    CONSTRAINT chk_usuario_perfil CHECK (
        (id_medico IS NOT NULL) + (cedula_paciente IS NOT NULL) + (id_personal IS NOT NULL) = 1)
) ENGINE=InnoDB;

CREATE TABLE recurso_atencion (
    id_recurso INT AUTO_INCREMENT PRIMARY KEY,
    id_area INT NOT NULL,
    nombre_recurso VARCHAR(80) NOT NULL,
    tipo_recurso ENUM('consultorio','equipo','puesto_laboratorio') NOT NULL,
    descripcion VARCHAR(255),
    estado ENUM('activo','inactivo','mantenimiento') NOT NULL DEFAULT 'activo',
    CONSTRAINT fk_recurso_area FOREIGN KEY (id_area) REFERENCES area(id_area),
    CONSTRAINT uq_recurso_nombre UNIQUE (id_area, nombre_recurso),
    CONSTRAINT uq_recurso_area UNIQUE (id_recurso, id_area)
) ENGINE=InnoDB;

CREATE TABLE tipo_procedimiento (
    id_tipo VARCHAR(5) PRIMARY KEY,
    id_area INT NOT NULL,
    nombre VARCHAR(80) NOT NULL UNIQUE,
    CONSTRAINT fk_tipo_area FOREIGN KEY (id_area) REFERENCES area(id_area)
) ENGINE=InnoDB;

CREATE TABLE subtipo_examen (
    id_subtipo VARCHAR(10) PRIMARY KEY,
    id_tipo VARCHAR(5) NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    costo DECIMAL(10,2) NOT NULL,
    estado ENUM('activo','inactivo') NOT NULL DEFAULT 'activo',
    CONSTRAINT fk_subtipo_tipo FOREIGN KEY (id_tipo) REFERENCES tipo_procedimiento(id_tipo),
    CONSTRAINT uq_subtipo UNIQUE (id_tipo, nombre),
    CONSTRAINT chk_subtipo_costo CHECK (costo >= 0)
) ENGINE=InnoDB;

CREATE TABLE medicamento (
    id_medicamento INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(120) NOT NULL,
    presentacion VARCHAR(100),
    concentracion VARCHAR(80),
    estado ENUM('activo','inactivo') NOT NULL DEFAULT 'activo',
    CONSTRAINT uq_medicamento UNIQUE (nombre, presentacion, concentracion)
) ENGINE=InnoDB;

CREATE TABLE cita (
    id_cita INT AUTO_INCREMENT PRIMARY KEY,
    cedula_paciente VARCHAR(10) NOT NULL,
    id_area INT NOT NULL,
    id_recurso INT NOT NULL,
    id_usuario_registra INT NOT NULL,
    fecha_cita DATE NOT NULL,
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL,
    estado ENUM('pendiente','confirmada','atendida','cancelada','no_asistio') NOT NULL DEFAULT 'pendiente',
    costo_aplicado DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    observacion VARCHAR(255),
    fecha_registro DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    activa TINYINT GENERATED ALWAYS AS (IF(estado IN ('cancelada','no_asistio'), NULL, 1)) STORED,
    CONSTRAINT fk_cita_paciente FOREIGN KEY (cedula_paciente) REFERENCES paciente(cedula_paciente),
    CONSTRAINT fk_cita_recurso FOREIGN KEY (id_recurso, id_area) REFERENCES recurso_atencion(id_recurso, id_area),
    CONSTRAINT fk_cita_usuario FOREIGN KEY (id_usuario_registra) REFERENCES usuario(id_usuario),
    CONSTRAINT fk_cita_bloque FOREIGN KEY (hora_inicio, hora_fin) REFERENCES bloque_horario(hora_inicio, hora_fin),
    CONSTRAINT uq_cita_paciente_horario UNIQUE (cedula_paciente, fecha_cita, hora_inicio, activa),
    CONSTRAINT uq_cita_recurso_horario UNIQUE (id_recurso, fecha_cita, hora_inicio, activa),
    CONSTRAINT chk_cita_dia CHECK (WEEKDAY(fecha_cita) < 5),
    CONSTRAINT chk_cita_costo CHECK (costo_aplicado >= 0),
    INDEX idx_cita_fecha (fecha_cita, estado)
) ENGINE=InnoDB;

CREATE TABLE cita_consulta (
    id_cita INT PRIMARY KEY,
    id_medico INT NOT NULL,
    CONSTRAINT fk_cconsulta_cita FOREIGN KEY (id_cita) REFERENCES cita(id_cita) ON DELETE CASCADE,
    CONSTRAINT fk_cconsulta_medico FOREIGN KEY (id_medico) REFERENCES medico(id_medico)
) ENGINE=InnoDB;

CREATE TABLE cita_imagenologia (
    id_cita INT PRIMARY KEY,
    id_medico_solicitante INT NOT NULL,
    id_subtipo VARCHAR(10) NOT NULL,
    estado_procedimiento ENUM('pendiente','realizado','cancelado') NOT NULL DEFAULT 'pendiente',
    fecha_realizacion DATETIME NULL,
    id_usuario_realiza INT NULL,
    CONSTRAINT fk_cimagen_cita FOREIGN KEY (id_cita) REFERENCES cita(id_cita) ON DELETE CASCADE,
    CONSTRAINT fk_cimagen_medico FOREIGN KEY (id_medico_solicitante) REFERENCES medico(id_medico),
    CONSTRAINT fk_cimagen_subtipo FOREIGN KEY (id_subtipo) REFERENCES subtipo_examen(id_subtipo),
    CONSTRAINT fk_cimagen_usuario FOREIGN KEY (id_usuario_realiza) REFERENCES usuario(id_usuario),
    CONSTRAINT chk_cimagen_fecha CHECK (estado_procedimiento <> 'realizado' OR fecha_realizacion IS NOT NULL)
) ENGINE=InnoDB;

CREATE TABLE cita_laboratorio (
    id_cita INT PRIMARY KEY,
    id_medico_solicitante INT NOT NULL,
    id_subtipo VARCHAR(10) NOT NULL,
    estado_examen ENUM('pendiente','realizado','cancelado') NOT NULL DEFAULT 'pendiente',
    fecha_realizacion DATE NULL,
    CONSTRAINT fk_clab_cita FOREIGN KEY (id_cita) REFERENCES cita(id_cita) ON DELETE CASCADE,
    CONSTRAINT fk_clab_medico FOREIGN KEY (id_medico_solicitante) REFERENCES medico(id_medico),
    CONSTRAINT fk_clab_subtipo FOREIGN KEY (id_subtipo) REFERENCES subtipo_examen(id_subtipo),
    CONSTRAINT chk_clab_fecha CHECK (estado_examen <> 'realizado' OR fecha_realizacion IS NOT NULL)
) ENGINE=InnoDB;

CREATE TABLE consulta_medica (
    id_consulta INT AUTO_INCREMENT PRIMARY KEY,
    id_cita INT NOT NULL UNIQUE,
    fecha_hora_atencion DATETIME NOT NULL,
    motivo_consulta VARCHAR(255) NOT NULL,
    observaciones TEXT,
    CONSTRAINT fk_cmedica_cita FOREIGN KEY (id_cita) REFERENCES cita_consulta(id_cita) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE diagnostico (
    id_diagnostico INT AUTO_INCREMENT PRIMARY KEY,
    id_consulta INT NOT NULL,
    descripcion VARCHAR(500) NOT NULL,
    observacion TEXT,
    fecha_registro DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_diagnostico_consulta FOREIGN KEY (id_consulta) REFERENCES consulta_medica(id_consulta) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE prescripcion (
    id_prescripcion INT AUTO_INCREMENT PRIMARY KEY,
    id_consulta INT NOT NULL UNIQUE,
    fecha_prescripcion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    indicaciones_generales TEXT,
    CONSTRAINT fk_prescripcion_consulta FOREIGN KEY (id_consulta) REFERENCES consulta_medica(id_consulta) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE detalle_prescripcion (
    id_detalle INT AUTO_INCREMENT PRIMARY KEY,
    id_prescripcion INT NOT NULL,
    id_medicamento INT NOT NULL,
    dosis VARCHAR(100) NOT NULL,
    frecuencia VARCHAR(100) NOT NULL,
    duracion VARCHAR(100) NOT NULL,
    indicaciones TEXT,
    CONSTRAINT fk_detalle_prescripcion FOREIGN KEY (id_prescripcion) REFERENCES prescripcion(id_prescripcion) ON DELETE CASCADE,
    CONSTRAINT fk_detalle_medicamento FOREIGN KEY (id_medicamento) REFERENCES medicamento(id_medicamento)
) ENGINE=InnoDB;

CREATE TABLE resultado_laboratorio (
    id_resultado INT AUTO_INCREMENT PRIMARY KEY,
    id_cita INT NOT NULL UNIQUE,
    registrado_por INT NOT NULL,
    fecha_resultado DATE NOT NULL,
    resultado TEXT NOT NULL,
    observaciones TEXT,
    fecha_registro DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_resultado_cita FOREIGN KEY (id_cita) REFERENCES cita_laboratorio(id_cita) ON DELETE CASCADE,
    CONSTRAINT fk_resultado_usuario FOREIGN KEY (registrado_por) REFERENCES usuario(id_usuario)
) ENGINE=InnoDB;

-- Sin clave foránea a propósito: el registro se conserva aunque la cita se elimine
CREATE TABLE auditoria_cita (
    id_auditoria BIGINT AUTO_INCREMENT PRIMARY KEY,
    id_cita INT NOT NULL,
    estado_anterior VARCHAR(20),
    estado_nuevo VARCHAR(20),
    fecha_anterior DATE,
    fecha_nueva DATE,
    hora_anterior TIME,
    hora_nueva TIME,
    usuario_bd VARCHAR(100),
    id_usuario_app INT NULL,
    fecha_cambio DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_auditoria_cita (id_cita)
) ENGINE=InnoDB;

-- Registro de inicios y cierres de sesion. Lo escribe Flask con la cuenta usr_login.
-- cedula_intento guarda lo que se escribio en el login (exista o no el usuario).
CREATE TABLE auditoria_acceso (
    id_acceso BIGINT AUTO_INCREMENT PRIMARY KEY,
    cedula_intento VARCHAR(20) NOT NULL,
    id_usuario INT NULL,
    resultado ENUM('exitoso','fallido','bloqueado','cierre_sesion') NOT NULL,
    ip VARCHAR(45),
    navegador VARCHAR(255),
    fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_acceso_usuario FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario),
    INDEX idx_acceso_cedula (cedula_intento, fecha),
    INDEX idx_acceso_usuario (id_usuario),
    INDEX idx_acceso_fecha (fecha)
) ENGINE=InnoDB;

-- Vistas
CREATE VIEW v_usuarios AS
SELECT u.id_usuario, u.cedula, u.nombres, u.apellidos, u.nombre_usuario, u.correo,
       r.nombre AS rol,
       CASE WHEN u.id_medico IS NOT NULL THEN 'Médico'
            WHEN u.cedula_paciente IS NOT NULL THEN 'Paciente'
            ELSE 'Personal' END AS tipo_perfil,
       u.estado, u.intentos_fallidos, u.bloqueado_hasta, u.cambio_clave_obligatorio,
       u.fecha_creacion, u.ultimo_acceso
FROM usuario u
JOIN rol r ON r.id_rol = u.id_rol;

CREATE VIEW v_agenda_consultas AS
SELECT c.id_cita, c.fecha_cita, c.hora_inicio, c.hora_fin, c.estado, c.costo_aplicado,
       p.cedula_paciente, CONCAT(p.nombres, ' ', p.apellidos) AS paciente,
       m.id_medico, CONCAT(m.nombres, ' ', m.apellidos) AS medico,
       e.nombre AS especialidad, r.nombre_recurso AS consultorio
FROM cita c
JOIN cita_consulta cc ON cc.id_cita = c.id_cita
JOIN paciente p ON p.cedula_paciente = c.cedula_paciente
JOIN medico m ON m.id_medico = cc.id_medico
JOIN especialidad e ON e.id_especialidad = m.id_especialidad
JOIN recurso_atencion r ON r.id_recurso = c.id_recurso;

CREATE VIEW v_agenda_imagenologia AS
SELECT c.id_cita, c.fecha_cita, c.hora_inicio, c.hora_fin, c.estado, c.costo_aplicado,
       p.cedula_paciente, CONCAT(p.nombres, ' ', p.apellidos) AS paciente,
       m.id_medico, CONCAT(m.nombres, ' ', m.apellidos) AS medico_solicitante,
       t.nombre AS tipo, s.id_subtipo, s.nombre AS subtipo,
       ci.estado_procedimiento, ci.fecha_realizacion, r.nombre_recurso AS equipo
FROM cita c
JOIN cita_imagenologia ci ON ci.id_cita = c.id_cita
JOIN paciente p ON p.cedula_paciente = c.cedula_paciente
JOIN medico m ON m.id_medico = ci.id_medico_solicitante
JOIN subtipo_examen s ON s.id_subtipo = ci.id_subtipo
JOIN tipo_procedimiento t ON t.id_tipo = s.id_tipo
JOIN recurso_atencion r ON r.id_recurso = c.id_recurso;

CREATE VIEW v_agenda_laboratorio AS
SELECT c.id_cita, c.fecha_cita, c.hora_inicio, c.hora_fin, c.estado, c.costo_aplicado,
       p.cedula_paciente, CONCAT(p.nombres, ' ', p.apellidos) AS paciente,
       m.id_medico, CONCAT(m.nombres, ' ', m.apellidos) AS medico_solicitante,
       s.id_subtipo, s.nombre AS examen, cl.estado_examen, cl.fecha_realizacion,
       r.nombre_recurso AS puesto
FROM cita c
JOIN cita_laboratorio cl ON cl.id_cita = c.id_cita
JOIN paciente p ON p.cedula_paciente = c.cedula_paciente
JOIN medico m ON m.id_medico = cl.id_medico_solicitante
JOIN subtipo_examen s ON s.id_subtipo = cl.id_subtipo
JOIN recurso_atencion r ON r.id_recurso = c.id_recurso;

CREATE VIEW v_historial_paciente AS
SELECT p.cedula_paciente, CONCAT(p.nombres, ' ', p.apellidos) AS paciente,
       cm.id_consulta, cm.fecha_hora_atencion, m.id_medico,
       CONCAT(m.nombres, ' ', m.apellidos) AS medico, e.nombre AS especialidad,
       cm.motivo_consulta, d.descripcion AS diagnostico, cm.observaciones
FROM consulta_medica cm
JOIN cita_consulta cc ON cc.id_cita = cm.id_cita
JOIN cita c ON c.id_cita = cc.id_cita
JOIN paciente p ON p.cedula_paciente = c.cedula_paciente
JOIN medico m ON m.id_medico = cc.id_medico
JOIN especialidad e ON e.id_especialidad = m.id_especialidad
LEFT JOIN diagnostico d ON d.id_consulta = cm.id_consulta;

CREATE VIEW v_recetas AS
SELECT p.cedula_paciente, CONCAT(p.nombres, ' ', p.apellidos) AS paciente,
       pr.id_prescripcion, pr.id_consulta, pr.fecha_prescripcion, m.id_medico,
       CONCAT(m.nombres, ' ', m.apellidos) AS medico,
       md.nombre AS medicamento, md.presentacion, md.concentracion,
       dp.dosis, dp.frecuencia, dp.duracion, dp.indicaciones
FROM prescripcion pr
JOIN consulta_medica cm ON cm.id_consulta = pr.id_consulta
JOIN cita_consulta cc ON cc.id_cita = cm.id_cita
JOIN cita c ON c.id_cita = cc.id_cita
JOIN paciente p ON p.cedula_paciente = c.cedula_paciente
JOIN medico m ON m.id_medico = cc.id_medico
JOIN detalle_prescripcion dp ON dp.id_prescripcion = pr.id_prescripcion
JOIN medicamento md ON md.id_medicamento = dp.id_medicamento;

CREATE VIEW v_resultados_laboratorio AS
SELECT rl.id_resultado, c.id_cita, p.cedula_paciente, CONCAT(p.nombres, ' ', p.apellidos) AS paciente,
       m.id_medico, CONCAT(m.nombres, ' ', m.apellidos) AS medico_solicitante,
       s.nombre AS examen, cl.fecha_realizacion, rl.fecha_resultado, rl.resultado, rl.observaciones
FROM resultado_laboratorio rl
JOIN cita_laboratorio cl ON cl.id_cita = rl.id_cita
JOIN cita c ON c.id_cita = cl.id_cita
JOIN paciente p ON p.cedula_paciente = c.cedula_paciente
JOIN medico m ON m.id_medico = cl.id_medico_solicitante
JOIN subtipo_examen s ON s.id_subtipo = cl.id_subtipo;

CREATE VIEW v_reporte_ingresos AS
SELECT a.nombre AS area, DATE_FORMAT(c.fecha_cita, '%Y-%m') AS mes,
       COUNT(*) AS citas_atendidas, SUM(c.costo_aplicado) AS ingresos
FROM cita c
JOIN area a ON a.id_area = c.id_area
WHERE c.estado = 'atendida'
GROUP BY a.nombre, DATE_FORMAT(c.fecha_cita, '%Y-%m');