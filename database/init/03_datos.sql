-- =====================================================================
-- MEDIMAGEN | 03_datos.sql
-- Datos iniciales (ficticios). Los 16 usuarios entran con la clave uno234cinco
-- (hash de werkzeug). Ejecutar con root.
-- =====================================================================
USE medimagen;

INSERT INTO rol (nombre, descripcion) VALUES
('administrador','Gestión de usuarios, roles, médicos, pacientes, especialidades y catálogos'),
('recepcion','Registra pacientes, agenda, modifica y cancela citas'),
('medico','Consulta su agenda, atiende pacientes, prescribe y solicita exámenes'),
('personal_imagenologia','Consulta agendas y registra la realización de procedimientos'),
('personal_laboratorio','Consulta agendas, registra exámenes y almacena resultados'),
('paciente','Consulta citas, historial médico, recetas y resultados');

INSERT INTO area (nombre, descripcion) VALUES
('Consultas médicas','Atención médica por especialidad'),
('Imagenología','Radiografía, tomografía, resonancia y densitometría ósea'),
('Laboratorio clínico','Exámenes de orina, heces y sangre');

INSERT INTO bloque_horario (hora_inicio, hora_fin) VALUES
('07:00:00','08:00:00'),('08:00:00','09:00:00'),('09:00:00','10:00:00'),('10:00:00','11:00:00'),
('11:00:00','12:00:00'),('12:00:00','13:00:00'),('13:00:00','14:00:00'),('14:00:00','15:00:00'),
('15:00:00','16:00:00'),('16:00:00','17:00:00'),('17:00:00','18:00:00');

INSERT INTO especialidad (nombre, descripcion, costo_consulta) VALUES
('Medicina General','Atención médica integral y primer contacto',20.00),
('Pediatría','Atención de niños y adolescentes',25.00),
('Nutricionista','Evaluación y plan nutricional',25.00),
('Dermatología','Enfermedades de la piel',30.00),
('Odontología','Salud bucal',25.00),
('Gastroenterología','Enfermedades del aparato digestivo',35.00),
('Cardiología','Enfermedades del corazón',40.00);

INSERT INTO tipo_procedimiento (id_tipo, id_area, nombre) VALUES
('RX',2,'Radiografía'),('TAC',2,'Tomografía'),('RM',2,'Resonancia magnética'),
('DO',2,'Densitometría ósea'),('LAB',3,'Laboratorio clínico');

INSERT INTO subtipo_examen (id_tipo, nombre, costo) VALUES
('RX','Cráneo',25.00),('RX','Columna cervical',28.00),('RX','Columna dorsal',28.00),
('RX','Columna lumbar',30.00),('RX','Lumbosacra',30.00),('RX','Miembro superior derecho',25.00),
('RX','Miembro superior izquierdo',25.00),('RX','Miembro inferior derecho',27.00),
('RX','Miembro inferior izquierdo',27.00),
('TAC','UROTAC',150.00),('TAC','Senos paranasales',110.00),('TAC','Abdominal',140.00),('TAC','Cráneo',130.00),
('RM','Simple',250.00),('RM','Contrastada',320.00),
('DO','Básica: miembros superiores',40.00),('DO','Completa: miembros superiores e inferiores',60.00),
('LAB','Orina',8.00),('LAB','Heces',8.00),('LAB','Sangre',15.00);

INSERT INTO medicamento (nombre, presentacion, concentracion) VALUES
('Paracetamol','Tableta','500 mg'),('Ibuprofeno','Tableta','400 mg'),
('Amoxicilina','Suspensión','250 mg/5 ml'),('Propranolol','Tableta','10 mg'),
('Hidrocortisona','Crema','1%'),('Omeprazol','Cápsula','20 mg'),
('Vitamina D','Cápsula','1000 UI'),('Enalapril','Tableta','10 mg'),
('Multivitamínico','Tableta',NULL),('Loratadina','Tableta','10 mg');

INSERT INTO paciente (cedula_paciente, nombres, apellidos, fecha_nacimiento, sexo, telefono, correo, direccion) VALUES
('0102030405','Carlos','Andrade Pinos','1990-03-14','M','0991111111','carlos.andrade@mail.com','Av. Loja y Remigio Crespo'),
('0103040506','María','Vintimilla Cueva','1985-07-22','F','0992222222','maria.vintimilla@mail.com','Calle Larga 4-35'),
('0104050607','José','Quezada Brito','2016-11-05','M','0993333333','jose.quezada@mail.com','Ricaurte, Cuenca'),
('0105060708','Ana','Cordero Ríos','1972-01-30','F','0994444444','ana.cordero@mail.com','Av. Ordóñez Lasso 2-10'),
('0106070809','Luis','Pesántez Mora','1998-09-18','M','0995555555','luis.pesantez@mail.com','Challuabamba'),
('0107080910','Daniela','Ortiz Tapia','2001-05-09','F','0996666666','daniela.ortiz@mail.com','Av. de las Américas 8-20'),
('0108091011','Pedro','Calle Arévalo','1965-12-02','M','0997777777','pedro.calle@mail.com','Baños, Cuenca'),
('0109101112','Sofía','Barrera León','1993-04-27','F','0998888888','sofia.barrera@mail.com','El Batán'),
('0110111213','Andrés','Idrovo Sarmiento','1980-08-11','M','0999999999','andres.idrovo@mail.com','Totoracocha'),
('0111121314','Camila','Loja Zhunio','2004-02-19','F','0981234567','camila.loja@mail.com','Monay');

INSERT INTO medico (id_especialidad, cedula, nombres, apellidos, telefono, correo) VALUES
('ESP-01','0301000001','Ricardo','Salamea Ochoa','0970000001','ricardo.salamea@medimagen.com'),
('ESP-01','0301000002','Patricia','Crespo Vélez','0970000002','patricia.crespo@medimagen.com'),
('ESP-01','0301000003','Esteban','Peña Alvear','0970000003','esteban.pena@medimagen.com'),
('ESP-02','0301000004','Gabriela','Mora Ullauri','0970000004','gabriela.mora@medimagen.com'),
('ESP-03','0301000005','Verónica','Astudillo Cabrera','0970000005','veronica.astudillo@medimagen.com'),
('ESP-04','0301000006','Marcelo','Tello Bravo','0970000006','marcelo.tello@medimagen.com'),
('ESP-05','0301000007','Lucía','Serrano Maldonado','0970000007','lucia.serrano@medimagen.com'),
('ESP-06','0301000008','Fernando','Guamán Pacheco','0970000008','fernando.guaman@medimagen.com'),
('ESP-07','0301000009','Mónica','Jaramillo Heredia','0970000009','monica.jaramillo@medimagen.com'),
('ESP-07','0301000010','Santiago','Rivera Coronel','0970000010','santiago.rivera@medimagen.com');

INSERT INTO personal (cedula, nombres, apellidos, telefono, correo, cargo) VALUES
('0301100001','Mateo','Cárdenas Gil','0960000001','mateo.cardenas@medimagen.com','Administrador'),
('0301100002','Karla','Villacís Ponce','0960000002','karla.villacis@medimagen.com','Recepcionista'),
('0301100003','Mónica','Vargas Ruiz','0960000003','monica.vargas@medimagen.com','Recepcionista'),
('0301100004','Esteban','Calle Paredes','0960000004','esteban.calle@medimagen.com','Recepcionista'),
('0301100005','Roberto','Peñafiel Mora','0960000005','roberto.penafiel@medimagen.com','Técnico de imagenología'),
('0301100006','Diego','Ochoa Brito','0960000006','diego.ochoa@medimagen.com','Técnico de imagenología'),
('0301100007','Lucas','Paredes Soto','0960000007','lucas.paredes@medimagen.com','Técnico de imagenología'),
('0301100008','Andrea','Sornoza Viteri','0960000008','andrea.sornoza@medimagen.com','Laboratorista'),
('0301100009','Elena','Rojas Cabrera','0960000009','elena.rojas@medimagen.com','Laboratorista'),
('0301100010','Nelson','Tapia Ullauri','0960000010','nelson.tapia@medimagen.com','Laboratorista');

-- Hash werkzeug (pbkdf2:sha256) de la contraseña de prueba: uno234cinco
SET @hash = 'pbkdf2:sha256:1000000$B6H7bOn922NqQi5j$0b4c23fafb117e8a7c093bc856036717abfa6304426f43f8958de0df3b0ce82c';

INSERT INTO usuario (cedula, id_rol, id_medico, cedula_paciente, id_personal, nombres, apellidos, nombre_usuario, correo, password_hash) VALUES
('0301100001',1,NULL,NULL,1,'Mateo','Cárdenas Gil','admin','mateo.cardenas@medimagen.com',@hash),
('0301100002',2,NULL,NULL,2,'Karla','Villacís Ponce','kvillacis','karla.villacis@medimagen.com',@hash),
('0301100003',2,NULL,NULL,3,'Mónica','Vargas Ruiz','mvargas','monica.vargas@medimagen.com',@hash),
('0301100004',2,NULL,NULL,4,'Esteban','Calle Paredes','ecalle','esteban.calle@medimagen.com',@hash),
('0301100005',4,NULL,NULL,5,'Roberto','Peñafiel Mora','rpenafiel','roberto.penafiel@medimagen.com',@hash),
('0301100006',4,NULL,NULL,6,'Diego','Ochoa Brito','dochoa','diego.ochoa@medimagen.com',@hash),
('0301100007',4,NULL,NULL,7,'Lucas','Paredes Soto','lparedes','lucas.paredes@medimagen.com',@hash),
('0301100008',5,NULL,NULL,8,'Andrea','Sornoza Viteri','asornoza','andrea.sornoza@medimagen.com',@hash),
('0301100009',5,NULL,NULL,9,'Elena','Rojas Cabrera','erojas','elena.rojas@medimagen.com',@hash),
('0301100010',5,NULL,NULL,10,'Nelson','Tapia Ullauri','ntapia','nelson.tapia@medimagen.com',@hash),
('0301000001',3,1,NULL,NULL,'Ricardo','Salamea Ochoa','rsalamea','ricardo.salamea@medimagen.com',@hash),
('0301000004',3,4,NULL,NULL,'Gabriela','Mora Ullauri','gmora','gabriela.mora@medimagen.com',@hash),
('0301000009',3,9,NULL,NULL,'Mónica','Jaramillo Heredia','mjaramillo','monica.jaramillo@medimagen.com',@hash),
('0102030405',6,NULL,'0102030405',NULL,'Carlos','Andrade Pinos','candrade','carlos.andrade@mail.com',@hash),
('0103040506',6,NULL,'0103040506',NULL,'María','Vintimilla Cueva','mvintimilla','maria.vintimilla@mail.com',@hash),
('0105060708',6,NULL,'0105060708',NULL,'Ana','Cordero Ríos','acordero','ana.cordero@mail.com',@hash);

INSERT INTO recurso_atencion (id_area, nombre_recurso, tipo_recurso, descripcion) VALUES
(1,'Consultorio 1','consultorio','Planta baja'),
(1,'Consultorio 2','consultorio','Planta baja'),
(1,'Consultorio 3','consultorio','Primer piso'),
(1,'Consultorio 4','consultorio','Primer piso'),
(2,'Sala de Rayos X','equipo','Equipo de radiografía digital'),
(2,'Tomógrafo','equipo','Tomógrafo multicorte'),
(2,'Resonador','equipo','Resonador magnético 1.5T'),
(2,'Densitómetro','equipo','Densitómetro óseo DXA'),
(3,'Puesto de laboratorio 1','puesto_laboratorio','Toma de muestras'),
(3,'Puesto de laboratorio 2','puesto_laboratorio','Toma de muestras');

-- Citas 1-10 consultas (usuario 2), 11-20 imagenología (usuario 3), 21-30 laboratorio (usuario 4)
INSERT INTO cita (cedula_paciente, id_area, id_recurso, id_usuario_registra, fecha_cita, hora_inicio, hora_fin, estado) VALUES
('0102030405',1,1,2,'2026-11-02','08:00:00','09:00:00','confirmada'),
('0103040506',1,1,2,'2026-11-02','09:00:00','10:00:00','confirmada'),
('0104050607',1,2,2,'2026-11-03','10:00:00','11:00:00','confirmada'),
('0105060708',1,3,2,'2026-11-04','11:00:00','12:00:00','confirmada'),
('0106070809',1,4,2,'2026-11-05','14:00:00','15:00:00','confirmada'),
('0107080910',1,2,2,'2026-11-06','15:00:00','16:00:00','confirmada'),
('0108091011',1,3,2,'2026-11-09','07:00:00','08:00:00','confirmada'),
('0109101112',1,4,2,'2026-11-10','16:00:00','17:00:00','confirmada'),
('0110111213',1,1,2,'2026-11-11','09:00:00','10:00:00','confirmada'),
('0111121314',1,3,2,'2026-11-12','17:00:00','18:00:00','confirmada'),
('0102030405',2,5,3,'2026-11-02','10:00:00','11:00:00','confirmada'),
('0103040506',2,5,3,'2026-11-03','08:00:00','09:00:00','confirmada'),
('0104050607',2,5,3,'2026-11-04','09:00:00','10:00:00','confirmada'),
('0105060708',2,6,3,'2026-11-05','10:00:00','11:00:00','confirmada'),
('0106070809',2,7,3,'2026-11-06','11:00:00','12:00:00','confirmada'),
('0107080910',2,8,3,'2026-11-09','08:00:00','09:00:00','confirmada'),
('0108091011',2,6,3,'2026-11-10','09:00:00','10:00:00','confirmada'),
('0109101112',2,5,3,'2026-11-17','10:00:00','11:00:00','pendiente'),
('0110111213',2,7,3,'2026-11-18','08:00:00','09:00:00','confirmada'),
('0111121314',2,6,3,'2026-11-19','14:00:00','15:00:00','pendiente'),
('0102030405',3,9,4,'2026-11-03','07:00:00','08:00:00','confirmada'),
('0102030405',3,10,4,'2026-11-03','08:00:00','09:00:00','confirmada'),
('0103040506',3,9,4,'2026-11-04','07:00:00','08:00:00','confirmada'),
('0104050607',3,10,4,'2026-11-05','08:00:00','09:00:00','confirmada'),
('0105060708',3,9,4,'2026-11-06','07:00:00','08:00:00','confirmada'),
('0106070809',3,10,4,'2026-11-09','09:00:00','10:00:00','confirmada'),
('0107080910',3,9,4,'2026-11-10','07:00:00','08:00:00','confirmada'),
('0108091011',3,10,4,'2026-11-11','08:00:00','09:00:00','confirmada'),
('0109101112',3,9,4,'2026-11-12','07:00:00','08:00:00','confirmada'),
('0111121314',3,10,4,'2026-11-13','08:00:00','09:00:00','confirmada');

-- Los triggers asignan costo_aplicado en estos tres INSERT
INSERT INTO cita_consulta (id_cita, id_medico) VALUES
(1,1),(2,1),(3,4),(4,9),(5,6),(6,7),(7,8),(8,5),(9,2),(10,10);

INSERT INTO cita_imagenologia (id_cita, id_medico_solicitante, id_subtipo, estado_procedimiento, fecha_realizacion, id_usuario_realiza) VALUES
(11,1,'RX-04','realizado','2026-11-02 10:00:00',5),
(12,1,'RX-01','realizado','2026-11-03 08:00:00',5),
(13,4,'RX-06','realizado','2026-11-04 09:00:00',6),
(14,9,'TAC-03','realizado','2026-11-05 10:00:00',6),
(15,6,'RM-02','realizado','2026-11-06 11:00:00',7),
(16,2,'DO-02','realizado','2026-11-09 08:00:00',7),
(17,8,'TAC-01','cancelado',NULL,NULL),
(18,3,'RX-08','pendiente',NULL,NULL),
(19,10,'RM-01','pendiente',NULL,NULL),
(20,9,'TAC-04','pendiente',NULL,NULL);

INSERT INTO cita_laboratorio (id_cita, id_medico_solicitante, id_subtipo, estado_examen, fecha_realizacion) VALUES
(21,1,'LAB-03','realizado','2026-11-03'),
(22,1,'LAB-01','realizado','2026-11-03'),
(23,1,'LAB-03','realizado','2026-11-04'),
(24,4,'LAB-02','realizado','2026-11-05'),
(25,9,'LAB-03','realizado','2026-11-06'),
(26,6,'LAB-01','realizado','2026-11-09'),
(27,2,'LAB-03','realizado','2026-11-10'),
(28,8,'LAB-02','realizado','2026-11-11'),
(29,5,'LAB-03','realizado','2026-11-12'),
(30,3,'LAB-01','realizado','2026-11-13');

-- Estos UPDATE generan 27 registros en auditoria_cita por medio del trigger
UPDATE cita SET estado = 'atendida' WHERE id_cita BETWEEN 1 AND 16 OR id_cita BETWEEN 21 AND 30;
UPDATE cita SET estado = 'cancelada' WHERE id_cita = 17;

INSERT INTO resultado_laboratorio (id_cita, registrado_por, fecha_resultado, resultado, observaciones) VALUES
(21,8,'2026-11-04','Hemoglobina 14.2 g/dL, glucosa 92 mg/dL','Valores normales'),
(22,8,'2026-11-04','Sin hallazgos patológicos','Muestra adecuada'),
(23,9,'2026-11-05','Hemoglobina 12.8 g/dL, leucocitos 7200/uL','Valores normales'),
(24,9,'2026-11-06','Ausencia de parásitos','Examen coproparasitario negativo'),
(25,9,'2026-11-07','Colesterol total 215 mg/dL, triglicéridos 180 mg/dL','Colesterol ligeramente elevado'),
(26,10,'2026-11-10','Presencia leve de leucocitos','Se sugiere control'),
(27,10,'2026-11-11','Glucosa 101 mg/dL, hemoglobina 13.5 g/dL','Glucosa en el límite superior'),
(28,10,'2026-11-12','Sangre oculta negativa','Sin hallazgos'),
(29,8,'2026-11-13','Hemoglobina 13.1 g/dL, glucosa 88 mg/dL','Valores normales'),
(30,8,'2026-11-14','Sin hallazgos patológicos','Muestra adecuada');

INSERT INTO consulta_medica (id_cita, fecha_hora_atencion, motivo_consulta, observaciones) VALUES
(1,'2026-11-02 08:00:00','Dolor de cabeza persistente','Reposo e hidratación'),
(2,'2026-11-02 09:00:00','Control general','Control anual'),
(3,'2026-11-03 10:00:00','Fiebre y tos','Vigilar temperatura'),
(4,'2026-11-04 11:00:00','Palpitaciones','Solicitar chequeo de seguimiento'),
(5,'2026-11-05 14:00:00','Manchas en la piel','Evitar jabones perfumados'),
(6,'2026-11-06 15:00:00','Dolor dental','Programar calzado dental'),
(7,'2026-11-09 07:00:00','Dolor abdominal','Dieta blanda por una semana'),
(8,'2026-11-10 16:00:00','Control de peso','Plan nutricional de 4 semanas'),
(9,'2026-11-11 09:00:00','Dolor de garganta','Reposo vocal'),
(10,'2026-11-12 17:00:00','Control de presión arterial','Continuar tratamiento');

INSERT INTO diagnostico (id_consulta, descripcion, observacion) VALUES
(1,'Cefalea tensional','Sin signos de alarma'),
(2,'Paciente sano','Exámenes de rutina solicitados'),
(3,'Infección respiratoria aguda','Sin dificultad respiratoria'),
(4,'Taquicardia sinusal','Se recomienda evitar cafeína'),
(5,'Dermatitis de contacto','Lesiones leves en antebrazo'),
(6,'Caries en molar inferior','Pieza 36'),
(7,'Gastritis leve','Evitar irritantes'),
(8,'Sobrepeso grado I','IMC 27.5'),
(9,'Faringitis aguda','Sin placas'),
(10,'Hipertensión arterial controlada','Presión 125/80');

INSERT INTO prescripcion (id_consulta, fecha_prescripcion, indicaciones_generales) VALUES
(1,'2026-11-02 09:00:00','Reposo e hidratación abundante'),
(2,'2026-11-02 10:00:00','Mantener alimentación balanceada'),
(3,'2026-11-03 11:00:00','Completar el tratamiento'),
(4,'2026-11-04 12:00:00','Control en 15 días'),
(5,'2026-11-05 15:00:00','Aplicar en zona afectada'),
(6,'2026-11-06 16:00:00','Tomar después de las comidas'),
(7,'2026-11-09 08:00:00','Dieta blanda'),
(8,'2026-11-10 17:00:00','Exposición solar moderada'),
(9,'2026-11-11 10:00:00','Evitar bebidas frías'),
(10,'2026-11-12 18:00:00','Control mensual de presión');

INSERT INTO detalle_prescripcion (id_prescripcion, id_medicamento, dosis, frecuencia, duracion, indicaciones) VALUES
(1,1,'1 tableta','Cada 8 horas','3 días','Si persiste el dolor, acudir a control'),
(2,9,'1 tableta','Cada 24 horas','30 días',NULL),
(3,3,'5 ml','Cada 8 horas','7 días','Agitar antes de usar'),
(3,1,'5 ml','Cada 8 horas si hay fiebre','3 días',NULL),
(4,4,'1 tableta','Cada 12 horas','15 días',NULL),
(5,5,'Aplicación local','Cada 12 horas','10 días','No aplicar en heridas abiertas'),
(5,10,'1 tableta','Cada 24 horas','7 días',NULL),
(6,2,'1 tableta','Cada 8 horas','3 días','Tomar con alimentos'),
(7,6,'1 cápsula','Cada 24 horas en ayunas','14 días',NULL),
(8,7,'1 cápsula','Cada 24 horas','30 días',NULL),
(9,2,'1 tableta','Cada 8 horas','5 días','Tomar con alimentos'),
(10,8,'1 tableta','Cada 24 horas','30 días','Tomar a la misma hora');

-- Accesos de demostracion (el sistema real los escribe Flask con usr_login)
INSERT INTO auditoria_acceso (cedula_intento, id_usuario, resultado, ip, navegador, fecha) VALUES
('0301100001',1,'exitoso','127.0.0.1','Chrome','2026-11-02 07:45:00'),
('0301100002',2,'exitoso','127.0.0.1','Chrome','2026-11-02 07:50:00'),
('0301000001',11,'exitoso','127.0.0.1','Firefox','2026-11-02 07:55:00'),
('0102030405',14,'exitoso','127.0.0.1','Chrome','2026-11-02 18:10:00'),
('0103040506',15,'fallido','127.0.0.1','Edge','2026-11-03 09:00:00'),
('0103040506',15,'exitoso','127.0.0.1','Edge','2026-11-03 09:01:00'),
('0999999999',NULL,'fallido','127.0.0.1','Chrome','2026-11-03 10:20:00'),
('0301100005',5,'exitoso','127.0.0.1','Chrome','2026-11-04 08:00:00'),
('0301100008',8,'exitoso','127.0.0.1','Chrome','2026-11-04 08:05:00'),
('0301100001',1,'cierre_sesion','127.0.0.1','Chrome','2026-11-04 17:30:00');
