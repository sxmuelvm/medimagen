"""Datos del panel de inicio de cada rol. Cada consulta usa la cuenta de MySQL del propio rol."""
from conexion.conexionBD import consultar
from utils.constants import (CUENTA_ADMINISTRADOR, CUENTA_IMAGENOLOGIA, CUENTA_LABORATORIO,
                             CUENTA_MEDICO, CUENTA_PACIENTE, CUENTA_RECEPCION)


def resumen(sesion):
    """Devuelve un diccionario con los indicadores y listas del panel del rol de la sesion."""
    funcion = _RESUMENES.get(sesion["cuenta"])
    return funcion(sesion) if funcion else {}


def _administrador(sesion):
    cuenta, yo = CUENTA_ADMINISTRADOR, sesion["id_usuario"]
    indicadores = consultar(cuenta, """
        SELECT
          (SELECT COUNT(*) FROM usuario WHERE estado = 'activo') AS usuarios_activos,
          (SELECT COUNT(*) FROM usuario WHERE estado <> 'activo'
              OR (bloqueado_hasta IS NOT NULL AND bloqueado_hasta > NOW())) AS usuarios_bloqueados,
          (SELECT COUNT(*) FROM paciente WHERE estado = 'activo') AS pacientes,
          (SELECT COUNT(*) FROM medico WHERE estado = 'activo') AS medicos,
          (SELECT COUNT(*) FROM cita WHERE fecha_cita = CURDATE()
              AND estado IN ('pendiente','confirmada')) AS citas_hoy,
          (SELECT COUNT(*) FROM cita WHERE estado = 'pendiente') AS citas_pendientes""", id_usuario_app=yo, uno=True)
    ingresos = consultar(cuenta, """
        SELECT area, mes, citas_atendidas, ingresos
        FROM v_reporte_ingresos ORDER BY mes DESC, area LIMIT 6""", id_usuario_app=yo)
    return {"indicadores": indicadores, "ingresos": ingresos}


def _recepcion(sesion):
    cuenta, yo = CUENTA_RECEPCION, sesion["id_usuario"]
    indicadores = consultar(cuenta, """
        SELECT
          (SELECT COUNT(*) FROM cita WHERE fecha_cita = CURDATE()
              AND estado IN ('pendiente','confirmada')) AS citas_hoy,
          (SELECT COUNT(*) FROM cita WHERE estado = 'pendiente') AS citas_pendientes,
          (SELECT COUNT(*) FROM paciente WHERE estado = 'activo') AS pacientes""",
                            id_usuario_app=yo, uno=True)
    proximas = consultar(cuenta, """
        SELECT c.id_cita, c.fecha_cita, c.hora_inicio, c.estado, a.nombre AS area,
               CONCAT(p.nombres, ' ', p.apellidos) AS paciente
        FROM cita c
        JOIN paciente p ON p.cedula_paciente = c.cedula_paciente
        JOIN area a ON a.id_area = c.id_area
        WHERE c.fecha_cita >= CURDATE() AND c.estado IN ('pendiente','confirmada')
        ORDER BY c.fecha_cita, c.hora_inicio LIMIT 8""", id_usuario_app=yo)
    return {"indicadores": indicadores, "proximas": proximas}


def _medico(sesion):
    cuenta, yo, medico = CUENTA_MEDICO, sesion["id_usuario"], sesion["id_medico"]
    indicadores = consultar(cuenta, """
        SELECT
          (SELECT COUNT(*) FROM v_agenda_consultas WHERE id_medico = %(m)s AND fecha_cita = CURDATE()
              AND estado IN ('pendiente','confirmada')) AS citas_hoy,
          (SELECT COUNT(*) FROM v_agenda_consultas WHERE id_medico = %(m)s AND fecha_cita >= CURDATE()
              AND estado IN ('pendiente','confirmada')) AS citas_por_atender,
          (SELECT COUNT(*) FROM v_agenda_consultas WHERE id_medico = %(m)s AND estado = 'atendida') AS atendidas,
          (SELECT COUNT(*) FROM v_agenda_imagenologia WHERE id_medico = %(m)s
              AND estado_procedimiento = 'pendiente') AS imagenes_pendientes,
          (SELECT COUNT(*) FROM v_agenda_laboratorio WHERE id_medico = %(m)s
              AND estado_examen = 'pendiente') AS laboratorios_pendientes""",
                            {"m": medico}, id_usuario_app=yo, uno=True)
    proximas = consultar(cuenta, """
        SELECT id_cita, fecha_cita, hora_inicio, estado, paciente, consultorio
        FROM v_agenda_consultas
        WHERE id_medico = %s AND fecha_cita >= CURDATE() AND estado IN ('pendiente','confirmada')
        ORDER BY fecha_cita, hora_inicio LIMIT 8""", (medico,), id_usuario_app=yo)
    return {"indicadores": indicadores, "proximas": proximas}


def _imagenologia(sesion):
    cuenta, yo = CUENTA_IMAGENOLOGIA, sesion["id_usuario"]
    indicadores = consultar(cuenta, """
        SELECT
          (SELECT COUNT(*) FROM v_agenda_imagenologia WHERE estado_procedimiento = 'pendiente'
              AND estado IN ('pendiente','confirmada')) AS pendientes,
          (SELECT COUNT(*) FROM v_agenda_imagenologia WHERE fecha_cita = CURDATE()
              AND estado IN ('pendiente','confirmada')) AS hoy,
          (SELECT COUNT(*) FROM v_agenda_imagenologia WHERE estado_procedimiento = 'realizado') AS realizados""",
                            id_usuario_app=yo, uno=True)
    proximas = consultar(cuenta, """
        SELECT id_cita, fecha_cita, hora_inicio, paciente, tipo, subtipo, equipo, estado_procedimiento
        FROM v_agenda_imagenologia
        WHERE estado_procedimiento = 'pendiente' AND estado IN ('pendiente','confirmada')
        ORDER BY fecha_cita, hora_inicio LIMIT 8""", id_usuario_app=yo)
    return {"indicadores": indicadores, "proximas": proximas}


def _laboratorio(sesion):
    cuenta, yo = CUENTA_LABORATORIO, sesion["id_usuario"]
    indicadores = consultar(cuenta, """
        SELECT
          (SELECT COUNT(*) FROM v_agenda_laboratorio WHERE estado_examen = 'pendiente'
              AND estado IN ('pendiente','confirmada')) AS pendientes,
          (SELECT COUNT(*) FROM v_agenda_laboratorio WHERE fecha_cita = CURDATE()
              AND estado IN ('pendiente','confirmada')) AS hoy,
          (SELECT COUNT(*) FROM v_resultados_laboratorio) AS resultados_registrados""",
                            id_usuario_app=yo, uno=True)
    proximas = consultar(cuenta, """
        SELECT id_cita, fecha_cita, hora_inicio, paciente, examen, puesto, estado_examen
        FROM v_agenda_laboratorio
        WHERE estado_examen = 'pendiente' AND estado IN ('pendiente','confirmada')
        ORDER BY fecha_cita, hora_inicio LIMIT 8""", id_usuario_app=yo)
    return {"indicadores": indicadores, "proximas": proximas}


def _paciente(sesion):
    cuenta, yo, cedula = CUENTA_PACIENTE, sesion["id_usuario"], sesion["cedula_paciente"]
    proximas = consultar(cuenta, """
        SELECT fecha_cita, hora_inicio, estado, 'Consulta' AS tipo, especialidad AS detalle
        FROM v_agenda_consultas WHERE cedula_paciente = %(c)s AND fecha_cita >= CURDATE()
          AND estado IN ('pendiente','confirmada','cancelada')
        UNION ALL
        SELECT fecha_cita, hora_inicio, estado, 'Imagenología', subtipo
        FROM v_agenda_imagenologia WHERE cedula_paciente = %(c)s AND fecha_cita >= CURDATE()
          AND estado IN ('pendiente','confirmada','cancelada')
        UNION ALL
        SELECT fecha_cita, hora_inicio, estado, 'Laboratorio', examen
        FROM v_agenda_laboratorio WHERE cedula_paciente = %(c)s AND fecha_cita >= CURDATE()
          AND estado IN ('pendiente','confirmada','cancelada')
        ORDER BY fecha_cita, hora_inicio LIMIT 8""", {"c": cedula}, id_usuario_app=yo)
    indicadores = consultar(cuenta, """
        SELECT
          (SELECT COUNT(*) FROM v_historial_paciente WHERE cedula_paciente = %(c)s) AS consultas_realizadas,
          (SELECT COUNT(DISTINCT id_prescripcion) FROM v_recetas WHERE cedula_paciente = %(c)s) AS recetas,
          (SELECT COUNT(*) FROM v_resultados_laboratorio WHERE cedula_paciente = %(c)s) AS resultados""",
                            {"c": cedula}, id_usuario_app=yo, uno=True)
    # Las canceladas se muestran (para que el paciente sepa), pero no cuentan como próximas
    indicadores["proximas_citas"] = sum(1 for c in proximas if c["estado"] != "cancelada")
    return {"indicadores": indicadores, "proximas": proximas}


_RESUMENES = {
    CUENTA_ADMINISTRADOR: _administrador,
    CUENTA_RECEPCION: _recepcion,
    CUENTA_MEDICO: _medico,
    CUENTA_IMAGENOLOGIA: _imagenologia,
    CUENTA_LABORATORIO: _laboratorio,
    CUENTA_PACIENTE: _paciente,
}
