-- =====================================================================
-- MEDIMAGEN | 04_roles.sql
-- Roles de MySQL y los privilegios de cada rol. Ejecutar con root.
-- rol_administrador: datos y estructura de medimagen, pero SIN DROP de la base
-- ni de la tabla usuario y SIN privilegios globales (no crea otras bases).
-- =====================================================================
CREATE ROLE IF NOT EXISTS 'rol_administrador', 'rol_recepcion', 'rol_medico',
                          'rol_imagenologia', 'rol_laboratorio', 'rol_paciente', 'rol_respaldo';

-- rol_administrador: datos y estructura de medimagen; no crea otras bases ni borra la base
GRANT SELECT, INSERT, UPDATE, EXECUTE, CREATE, ALTER, INDEX, REFERENCES,
      CREATE VIEW, SHOW VIEW, TRIGGER, CREATE ROUTINE, ALTER ROUTINE
      ON medimagen.* TO 'rol_administrador';

-- DELETE y DROP tabla por tabla, excepto usuario (solo DELETE, ver abajo) y las tablas de auditoría (inmutables)
GRANT DELETE, DROP ON medimagen.secuencia_codigo TO 'rol_administrador';
GRANT DELETE, DROP ON medimagen.rol TO 'rol_administrador';
GRANT DELETE, DROP ON medimagen.personal TO 'rol_administrador';
GRANT DELETE, DROP ON medimagen.area TO 'rol_administrador';
GRANT DELETE, DROP ON medimagen.especialidad TO 'rol_administrador';
GRANT DELETE, DROP ON medimagen.bloque_horario TO 'rol_administrador';
GRANT DELETE, DROP ON medimagen.paciente TO 'rol_administrador';
GRANT DELETE, DROP ON medimagen.medico TO 'rol_administrador';
GRANT DELETE, DROP ON medimagen.horario_medico TO 'rol_administrador';
GRANT DELETE, DROP ON medimagen.recurso_atencion TO 'rol_administrador';
GRANT DELETE, DROP ON medimagen.tipo_procedimiento TO 'rol_administrador';
GRANT DELETE, DROP ON medimagen.subtipo_examen TO 'rol_administrador';
GRANT DELETE, DROP ON medimagen.medicamento TO 'rol_administrador';
GRANT DELETE, DROP ON medimagen.cita TO 'rol_administrador';
GRANT DELETE, DROP ON medimagen.cita_consulta TO 'rol_administrador';
GRANT DELETE, DROP ON medimagen.cita_imagenologia TO 'rol_administrador';
GRANT DELETE, DROP ON medimagen.cita_laboratorio TO 'rol_administrador';
GRANT DELETE, DROP ON medimagen.consulta_medica TO 'rol_administrador';
GRANT DELETE, DROP ON medimagen.diagnostico TO 'rol_administrador';
GRANT DELETE, DROP ON medimagen.prescripcion TO 'rol_administrador';
GRANT DELETE, DROP ON medimagen.detalle_prescripcion TO 'rol_administrador';
GRANT DELETE, DROP ON medimagen.resultado_laboratorio TO 'rol_administrador';

-- Eliminar usuarios: solo DELETE (nunca DROP de la tabla). MySQL lo bloquea si el usuario ya tiene citas,
-- resultados o accesos registrados (llaves foráneas): en ese caso se desactiva.
GRANT DELETE ON medimagen.usuario TO 'rol_administrador';

-- DROP de las vistas
GRANT DROP ON medimagen.v_usuarios TO 'rol_administrador';
GRANT DROP ON medimagen.v_agenda_consultas TO 'rol_administrador';
GRANT DROP ON medimagen.v_agenda_imagenologia TO 'rol_administrador';
GRANT DROP ON medimagen.v_agenda_laboratorio TO 'rol_administrador';
GRANT DROP ON medimagen.v_historial_paciente TO 'rol_administrador';
GRANT DROP ON medimagen.v_recetas TO 'rol_administrador';
GRANT DROP ON medimagen.v_resultados_laboratorio TO 'rol_administrador';
GRANT DROP ON medimagen.v_reporte_ingresos TO 'rol_administrador';
GRANT DROP ON medimagen.v_contacto_paciente TO 'rol_administrador';

-- rol_recepcion: pacientes y agendamiento; puede eliminar citas; sin acceso a datos clínicos
GRANT SELECT ON medimagen.v_agenda_consultas TO 'rol_recepcion';
GRANT SELECT ON medimagen.v_agenda_imagenologia TO 'rol_recepcion';
GRANT SELECT ON medimagen.v_agenda_laboratorio TO 'rol_recepcion';
-- DELETE solo para corregir un registro hecho por error: MySQL lo bloquea si el paciente tiene citas o usuario
GRANT SELECT, INSERT, UPDATE, DELETE ON medimagen.paciente TO 'rol_recepcion';
GRANT SELECT ON medimagen.medico TO 'rol_recepcion';
GRANT SELECT ON medimagen.especialidad TO 'rol_recepcion';
GRANT SELECT ON medimagen.area TO 'rol_recepcion';
GRANT SELECT ON medimagen.recurso_atencion TO 'rol_recepcion';
GRANT SELECT ON medimagen.bloque_horario TO 'rol_recepcion';
GRANT SELECT ON medimagen.horario_medico TO 'rol_recepcion';
GRANT SELECT ON medimagen.tipo_procedimiento TO 'rol_recepcion';
GRANT SELECT ON medimagen.subtipo_examen TO 'rol_recepcion';
GRANT SELECT, INSERT, DELETE ON medimagen.cita TO 'rol_recepcion';
GRANT UPDATE (id_recurso, fecha_cita, hora_inicio, hora_fin, estado, observacion) ON medimagen.cita TO 'rol_recepcion';
GRANT SELECT, INSERT ON medimagen.cita_consulta TO 'rol_recepcion';
GRANT UPDATE (id_medico) ON medimagen.cita_consulta TO 'rol_recepcion';
GRANT SELECT, INSERT ON medimagen.cita_imagenologia TO 'rol_recepcion';
GRANT UPDATE (id_subtipo, estado_procedimiento) ON medimagen.cita_imagenologia TO 'rol_recepcion';
GRANT SELECT, INSERT ON medimagen.cita_laboratorio TO 'rol_recepcion';
GRANT UPDATE (id_subtipo, estado_examen) ON medimagen.cita_laboratorio TO 'rol_recepcion';
GRANT EXECUTE ON PROCEDURE medimagen.sp_horarios_disponibles TO 'rol_recepcion';

-- rol_medico: atención, diagnóstico, recetas y solicitud de exámenes; puede corregir diagnósticos y medicamentos
GRANT SELECT ON medimagen.v_agenda_consultas TO 'rol_medico';
GRANT SELECT ON medimagen.v_agenda_imagenologia TO 'rol_medico';
GRANT SELECT ON medimagen.v_agenda_laboratorio TO 'rol_medico';
GRANT SELECT ON medimagen.v_historial_paciente TO 'rol_medico';
GRANT SELECT ON medimagen.v_recetas TO 'rol_medico';
GRANT SELECT ON medimagen.v_resultados_laboratorio TO 'rol_medico';
GRANT SELECT ON medimagen.paciente TO 'rol_medico';
GRANT SELECT ON medimagen.medico TO 'rol_medico';
GRANT SELECT ON medimagen.especialidad TO 'rol_medico';
GRANT SELECT ON medimagen.area TO 'rol_medico';
GRANT SELECT ON medimagen.recurso_atencion TO 'rol_medico';
GRANT SELECT ON medimagen.bloque_horario TO 'rol_medico';
GRANT SELECT ON medimagen.horario_medico TO 'rol_medico';
GRANT SELECT ON medimagen.tipo_procedimiento TO 'rol_medico';
GRANT SELECT ON medimagen.subtipo_examen TO 'rol_medico';
GRANT SELECT ON medimagen.medicamento TO 'rol_medico';
GRANT SELECT ON medimagen.cita_consulta TO 'rol_medico';
GRANT SELECT, INSERT ON medimagen.cita TO 'rol_medico';
-- Reprogramar o cancelar los exámenes que el médico solicitó (la app comprueba que sean suyos y estén pendientes)
GRANT UPDATE (id_recurso, fecha_cita, hora_inicio, hora_fin, estado, observacion) ON medimagen.cita TO 'rol_medico';
GRANT SELECT, INSERT ON medimagen.cita_imagenologia TO 'rol_medico';
GRANT UPDATE (estado_procedimiento) ON medimagen.cita_imagenologia TO 'rol_medico';
GRANT SELECT, INSERT ON medimagen.cita_laboratorio TO 'rol_medico';
GRANT UPDATE (estado_examen) ON medimagen.cita_laboratorio TO 'rol_medico';
GRANT SELECT, INSERT, UPDATE ON medimagen.consulta_medica TO 'rol_medico';
GRANT SELECT, INSERT, UPDATE, DELETE ON medimagen.diagnostico TO 'rol_medico';
GRANT SELECT, INSERT, UPDATE ON medimagen.prescripcion TO 'rol_medico';
GRANT SELECT, INSERT, UPDATE, DELETE ON medimagen.detalle_prescripcion TO 'rol_medico';
GRANT EXECUTE ON PROCEDURE medimagen.sp_horarios_disponibles TO 'rol_medico';

-- rol_imagenologia: agenda y registro de procedimientos
GRANT SELECT ON medimagen.v_agenda_imagenologia TO 'rol_imagenologia';
GRANT SELECT ON medimagen.cita TO 'rol_imagenologia';
GRANT UPDATE (estado) ON medimagen.cita TO 'rol_imagenologia';
GRANT SELECT ON medimagen.cita_imagenologia TO 'rol_imagenologia';
GRANT UPDATE (estado_procedimiento, fecha_realizacion, id_usuario_realiza) ON medimagen.cita_imagenologia TO 'rol_imagenologia';

-- rol_laboratorio: agenda, estado de exámenes y resultados
GRANT SELECT ON medimagen.v_agenda_laboratorio TO 'rol_laboratorio';
GRANT SELECT ON medimagen.v_resultados_laboratorio TO 'rol_laboratorio';
GRANT SELECT ON medimagen.cita TO 'rol_laboratorio';
GRANT UPDATE (estado) ON medimagen.cita TO 'rol_laboratorio';
GRANT SELECT ON medimagen.cita_laboratorio TO 'rol_laboratorio';
GRANT UPDATE (estado_examen, fecha_realizacion) ON medimagen.cita_laboratorio TO 'rol_laboratorio';
-- DELETE: eliminar un resultado propio para volver a registrarlo (la app comprueba que lo registró esa persona)
GRANT SELECT, INSERT, UPDATE, DELETE ON medimagen.resultado_laboratorio TO 'rol_laboratorio';

-- rol_paciente: lectura de vistas y, por procedimientos (que validan que todo sea suyo), editar su contacto
-- y cancelar sus citas pendientes. No tiene permisos directos sobre ninguna tabla.
GRANT SELECT ON medimagen.v_agenda_consultas TO 'rol_paciente';
GRANT SELECT ON medimagen.v_agenda_imagenologia TO 'rol_paciente';
GRANT SELECT ON medimagen.v_agenda_laboratorio TO 'rol_paciente';
GRANT SELECT ON medimagen.v_historial_paciente TO 'rol_paciente';
GRANT SELECT ON medimagen.v_recetas TO 'rol_paciente';
GRANT SELECT ON medimagen.v_resultados_laboratorio TO 'rol_paciente';
GRANT SELECT ON medimagen.v_contacto_paciente TO 'rol_paciente';
GRANT EXECUTE ON PROCEDURE medimagen.sp_paciente_actualizar_contacto TO 'rol_paciente';
GRANT EXECUTE ON PROCEDURE medimagen.sp_paciente_cancelar_cita TO 'rol_paciente';

-- rol_respaldo: lo necesario para mysqldump
GRANT SELECT, SHOW VIEW, TRIGGER, EVENT, LOCK TABLES ON medimagen.* TO 'rol_respaldo';
-- mysqldump 9.x hace FLUSH TABLES al iniciar la copia
GRANT FLUSH_TABLES ON *.* TO 'rol_respaldo';