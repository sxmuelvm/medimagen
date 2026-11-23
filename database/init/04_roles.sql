-- =====================================================================
-- MEDIMAGEN2 | 04_roles.sql
-- Roles de MySQL y los privilegios de cada rol sobre la base medimagen2. Ejecutar con root.
-- Los roles se crean solo si no existen: si ya existen por la base medimagen, se les suman los privilegios nuevos.
-- rol_administrador: datos y estructura de medimagen2, pero SIN DROP de la base
-- ni de la tabla usuario y SIN privilegios globales (no crea otras bases).
-- =====================================================================
CREATE ROLE IF NOT EXISTS 'rol_administrador', 'rol_recepcion', 'rol_medico',
                          'rol_imagenologia', 'rol_laboratorio', 'rol_paciente', 'rol_respaldo';

-- rol_administrador: datos y estructura de medimagen2; no crea otras bases ni borra la base
GRANT SELECT, INSERT, UPDATE, EXECUTE, CREATE, ALTER, INDEX, REFERENCES,
      CREATE VIEW, SHOW VIEW, TRIGGER, CREATE ROUTINE, ALTER ROUTINE
      ON medimagen2.* TO 'rol_administrador';

-- DELETE y DROP tabla por tabla, excepto usuario (solo DELETE, ver abajo)
GRANT DELETE, DROP ON medimagen2.rol TO 'rol_administrador';
GRANT DELETE, DROP ON medimagen2.area TO 'rol_administrador';
GRANT DELETE, DROP ON medimagen2.especialidad TO 'rol_administrador';
GRANT DELETE, DROP ON medimagen2.paciente TO 'rol_administrador';
GRANT DELETE, DROP ON medimagen2.medico TO 'rol_administrador';
GRANT DELETE, DROP ON medimagen2.recurso_atencion TO 'rol_administrador';
GRANT DELETE, DROP ON medimagen2.tipo_procedimiento TO 'rol_administrador';
GRANT DELETE, DROP ON medimagen2.subtipo_examen TO 'rol_administrador';
GRANT DELETE, DROP ON medimagen2.cita TO 'rol_administrador';
GRANT DELETE, DROP ON medimagen2.cita_consulta TO 'rol_administrador';
GRANT DELETE, DROP ON medimagen2.cita_imagenologia TO 'rol_administrador';
GRANT DELETE, DROP ON medimagen2.cita_laboratorio TO 'rol_administrador';
GRANT DELETE, DROP ON medimagen2.consulta_medica TO 'rol_administrador';
GRANT DELETE, DROP ON medimagen2.prescripcion TO 'rol_administrador';
GRANT DELETE, DROP ON medimagen2.detalle_prescripcion TO 'rol_administrador';
GRANT DELETE, DROP ON medimagen2.resultado_laboratorio TO 'rol_administrador';

-- Eliminar usuarios: solo DELETE (nunca DROP de la tabla). MySQL lo bloquea si el usuario ya tiene citas,
-- resultados registrados (llaves foráneas): en ese caso se desactiva.
GRANT DELETE ON medimagen2.usuario TO 'rol_administrador';

-- DROP de las vistas
GRANT DROP ON medimagen2.v_usuarios TO 'rol_administrador';
GRANT DROP ON medimagen2.v_agenda_consultas TO 'rol_administrador';
GRANT DROP ON medimagen2.v_agenda_imagenologia TO 'rol_administrador';
GRANT DROP ON medimagen2.v_agenda_laboratorio TO 'rol_administrador';
GRANT DROP ON medimagen2.v_historial_paciente TO 'rol_administrador';
GRANT DROP ON medimagen2.v_recetas TO 'rol_administrador';
GRANT DROP ON medimagen2.v_resultados_laboratorio TO 'rol_administrador';
GRANT DROP ON medimagen2.v_reporte_ingresos TO 'rol_administrador';
GRANT DROP ON medimagen2.v_contacto_paciente TO 'rol_administrador';

-- rol_recepcion: pacientes y agendamiento; puede eliminar citas; sin acceso a datos clínicos
GRANT SELECT ON medimagen2.v_agenda_consultas TO 'rol_recepcion';
GRANT SELECT ON medimagen2.v_agenda_imagenologia TO 'rol_recepcion';
GRANT SELECT ON medimagen2.v_agenda_laboratorio TO 'rol_recepcion';
-- DELETE solo para corregir un registro hecho por error: MySQL lo bloquea si el paciente tiene citas o usuario
GRANT SELECT, INSERT, UPDATE, DELETE ON medimagen2.paciente TO 'rol_recepcion';
GRANT SELECT ON medimagen2.medico TO 'rol_recepcion';
GRANT SELECT ON medimagen2.especialidad TO 'rol_recepcion';
GRANT SELECT ON medimagen2.area TO 'rol_recepcion';
GRANT SELECT ON medimagen2.recurso_atencion TO 'rol_recepcion';
GRANT SELECT ON medimagen2.tipo_procedimiento TO 'rol_recepcion';
GRANT SELECT ON medimagen2.subtipo_examen TO 'rol_recepcion';
GRANT SELECT, INSERT, DELETE ON medimagen2.cita TO 'rol_recepcion';
GRANT UPDATE (id_recurso, fecha_cita, hora_inicio, hora_fin, estado, observacion) ON medimagen2.cita TO 'rol_recepcion';
GRANT SELECT, INSERT ON medimagen2.cita_consulta TO 'rol_recepcion';
GRANT UPDATE (id_medico) ON medimagen2.cita_consulta TO 'rol_recepcion';
GRANT SELECT, INSERT ON medimagen2.cita_imagenologia TO 'rol_recepcion';
GRANT UPDATE (id_subtipo, estado_procedimiento) ON medimagen2.cita_imagenologia TO 'rol_recepcion';
GRANT SELECT, INSERT ON medimagen2.cita_laboratorio TO 'rol_recepcion';
GRANT UPDATE (id_subtipo, estado_examen) ON medimagen2.cita_laboratorio TO 'rol_recepcion';
GRANT EXECUTE ON PROCEDURE medimagen2.sp_horarios_disponibles TO 'rol_recepcion';

-- rol_medico: atención, diagnóstico, recetas y solicitud de exámenes; puede corregir la receta
GRANT SELECT ON medimagen2.v_agenda_consultas TO 'rol_medico';
GRANT SELECT ON medimagen2.v_agenda_imagenologia TO 'rol_medico';
GRANT SELECT ON medimagen2.v_agenda_laboratorio TO 'rol_medico';
GRANT SELECT ON medimagen2.v_historial_paciente TO 'rol_medico';
GRANT SELECT ON medimagen2.v_recetas TO 'rol_medico';
GRANT SELECT ON medimagen2.v_resultados_laboratorio TO 'rol_medico';
GRANT SELECT ON medimagen2.paciente TO 'rol_medico';
GRANT SELECT ON medimagen2.medico TO 'rol_medico';
GRANT SELECT ON medimagen2.especialidad TO 'rol_medico';
GRANT SELECT ON medimagen2.area TO 'rol_medico';
GRANT SELECT ON medimagen2.recurso_atencion TO 'rol_medico';
GRANT SELECT ON medimagen2.tipo_procedimiento TO 'rol_medico';
GRANT SELECT ON medimagen2.subtipo_examen TO 'rol_medico';
GRANT SELECT ON medimagen2.cita_consulta TO 'rol_medico';
GRANT SELECT, INSERT ON medimagen2.cita TO 'rol_medico';
-- Reprogramar o cancelar los exámenes que el médico solicitó (la app comprueba que sean suyos y estén pendientes)
GRANT UPDATE (id_recurso, fecha_cita, hora_inicio, hora_fin, estado, observacion) ON medimagen2.cita TO 'rol_medico';
GRANT SELECT, INSERT ON medimagen2.cita_imagenologia TO 'rol_medico';
GRANT UPDATE (estado_procedimiento) ON medimagen2.cita_imagenologia TO 'rol_medico';
GRANT SELECT, INSERT ON medimagen2.cita_laboratorio TO 'rol_medico';
GRANT UPDATE (estado_examen) ON medimagen2.cita_laboratorio TO 'rol_medico';
GRANT SELECT, INSERT, UPDATE ON medimagen2.consulta_medica TO 'rol_medico';
GRANT SELECT, INSERT, UPDATE ON medimagen2.prescripcion TO 'rol_medico';
GRANT SELECT, INSERT, UPDATE, DELETE ON medimagen2.detalle_prescripcion TO 'rol_medico';
GRANT EXECUTE ON PROCEDURE medimagen2.sp_horarios_disponibles TO 'rol_medico';

-- rol_imagenologia: agenda y registro de procedimientos
GRANT SELECT ON medimagen2.v_agenda_imagenologia TO 'rol_imagenologia';
GRANT SELECT ON medimagen2.cita TO 'rol_imagenologia';
GRANT UPDATE (estado) ON medimagen2.cita TO 'rol_imagenologia';
GRANT SELECT ON medimagen2.cita_imagenologia TO 'rol_imagenologia';
GRANT UPDATE (estado_procedimiento, fecha_realizacion, id_usuario_realiza) ON medimagen2.cita_imagenologia TO 'rol_imagenologia';

-- rol_laboratorio: agenda, estado de exámenes y resultados
GRANT SELECT ON medimagen2.v_agenda_laboratorio TO 'rol_laboratorio';
GRANT SELECT ON medimagen2.v_resultados_laboratorio TO 'rol_laboratorio';
GRANT SELECT ON medimagen2.cita TO 'rol_laboratorio';
GRANT UPDATE (estado) ON medimagen2.cita TO 'rol_laboratorio';
GRANT SELECT ON medimagen2.cita_laboratorio TO 'rol_laboratorio';
GRANT UPDATE (estado_examen, fecha_realizacion) ON medimagen2.cita_laboratorio TO 'rol_laboratorio';
-- DELETE: eliminar un resultado propio para volver a registrarlo (la app comprueba que lo registró esa persona)
GRANT SELECT, INSERT, UPDATE, DELETE ON medimagen2.resultado_laboratorio TO 'rol_laboratorio';

-- rol_paciente: lectura de vistas y, por procedimientos (que validan que todo sea suyo), editar su contacto
-- y cancelar sus citas pendientes. No tiene permisos directos sobre ninguna tabla.
GRANT SELECT ON medimagen2.v_agenda_consultas TO 'rol_paciente';
GRANT SELECT ON medimagen2.v_agenda_imagenologia TO 'rol_paciente';
GRANT SELECT ON medimagen2.v_agenda_laboratorio TO 'rol_paciente';
GRANT SELECT ON medimagen2.v_historial_paciente TO 'rol_paciente';
GRANT SELECT ON medimagen2.v_recetas TO 'rol_paciente';
GRANT SELECT ON medimagen2.v_resultados_laboratorio TO 'rol_paciente';
GRANT SELECT ON medimagen2.v_contacto_paciente TO 'rol_paciente';
GRANT EXECUTE ON PROCEDURE medimagen2.sp_paciente_actualizar_contacto TO 'rol_paciente';
GRANT EXECUTE ON PROCEDURE medimagen2.sp_paciente_cancelar_cita TO 'rol_paciente';

-- rol_respaldo: lo necesario para mysqldump
GRANT SELECT, SHOW VIEW, TRIGGER, EVENT, LOCK TABLES ON medimagen2.* TO 'rol_respaldo';
-- mysqldump 9.x hace FLUSH TABLES al iniciar la copia
GRANT FLUSH_TABLES ON *.* TO 'rol_respaldo';