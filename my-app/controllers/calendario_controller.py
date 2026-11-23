"""Calendario semanal de citas (lunes a viernes, de 07:00 a 18:00 en turnos de una hora).

Lo usan todos los roles que tienen que ver con citas. Cada uno ve solo lo suyo:
  - paciente: sus propias citas (la cedula sale de la sesion).
  - medico: sus consultas.
  - imagenologia / laboratorio: las citas de su area.
  - recepcion / administrador: todas, con filtros por area, medico y equipo; desde aqui se agenda.
Los datos salen de las vistas v_agenda_*, que ya tienen permisos para cada cuenta de MySQL.
"""
from datetime import datetime, time, timedelta

from flask import url_for

from conexion.conexionBD import consultar
from utils import validators
from utils.constants import (AREA_CONSULTAS, AREA_IMAGENOLOGIA, AREA_LABORATORIO, CUENTA_ADMINISTRADOR,
                             CUENTA_IMAGENOLOGIA, CUENTA_LABORATORIO, CUENTA_MEDICO, CUENTA_PACIENTE,
                             CUENTA_RECEPCION, ESTADOS_ACTIVOS_CITA)
from utils.errors import ErrorNegocio

HORA_PRIMERA, HORA_ULTIMA = 7, 17  # el ultimo turno empieza a las 17:00 y termina a las 18:00

# Las tres vistas con las mismas columnas. area: 1 consulta, 2 imagenologia, 3 laboratorio.
_CAMPOS = """id_cita, fecha_cita, hora_inicio, hora_fin, estado, cedula_paciente, paciente"""
_SQL = {
    AREA_CONSULTAS: f"""SELECT {_CAMPOS}, 1 AS id_area, id_medico, medico AS medico, especialidad AS detalle,
                               consultorio AS lugar, NULL AS estado_examen, id_medico AS id_medico_atiende
                        FROM v_agenda_consultas""",
    AREA_IMAGENOLOGIA: f"""SELECT {_CAMPOS}, 2 AS id_area, id_medico, medico_solicitante AS medico,
                                  CONCAT(tipo, ' · ', subtipo) AS detalle, equipo AS lugar,
                                  estado_procedimiento AS estado_examen, NULL AS id_medico_atiende
                           FROM v_agenda_imagenologia""",
    AREA_LABORATORIO: f"""SELECT {_CAMPOS}, 3 AS id_area, id_medico, medico_solicitante AS medico,
                                 examen AS detalle, puesto AS lugar, estado_examen,
                                 NULL AS id_medico_atiende
                          FROM v_agenda_laboratorio""",
}


def lunes_de(dia):
    return dia - timedelta(days=dia.weekday())


def _fecha_o_hoy(valor, cuenta, usuario):
    try:
        return validators.fecha(valor)
    except ErrorNegocio:
        return consultar(cuenta, "SELECT CURDATE() AS hoy", id_usuario_app=usuario, uno=True)["hoy"]


def _hm(valor):
    segundos = int(valor.total_seconds())
    return f"{segundos // 3600:02d}:{(segundos % 3600) // 60:02d}"


def _opcional_entero(valor):
    try:
        return int(valor) if valor else None
    except (TypeError, ValueError):
        return None


def _areas_visibles(cuenta):
    if cuenta == CUENTA_MEDICO:
        return (AREA_CONSULTAS,)
    if cuenta == CUENTA_IMAGENOLOGIA:
        return (AREA_IMAGENOLOGIA,)
    if cuenta == CUENTA_LABORATORIO:
        return (AREA_LABORATORIO,)
    return (AREA_CONSULTAS, AREA_IMAGENOLOGIA, AREA_LABORATORIO)


def _acciones(cuenta, c):
    """Botones del panel de detalle de una cita, segun el rol. Los permisos reales los aplica cada ruta."""
    acciones = []
    activa = c["estado"] in ESTADOS_ACTIVOS_CITA
    if cuenta in (CUENTA_ADMINISTRADOR, CUENTA_RECEPCION):
        acciones.append({"texto": "Ver detalle", "url": url_for("citas.detalle", id_cita=c["id_cita"])})
        if activa:
            acciones.append({"texto": "Reprogramar", "url": url_for("citas.reprogramar", id_cita=c["id_cita"])})
    elif cuenta == CUENTA_MEDICO and c["id_area"] == AREA_CONSULTAS and activa:
        acciones.append({"texto": "Atender consulta", "url": url_for("consultas.atender", id_cita=c["id_cita"])})
    elif cuenta == CUENTA_IMAGENOLOGIA and activa:
        acciones.append({"texto": "Registrar estudio",
                         "url": url_for("imagenologia.registrar_realizacion", id_cita=c["id_cita"])})
    elif cuenta == CUENTA_LABORATORIO and activa:
        acciones.append({"texto": "Registrar resultado",
                         "url": url_for("laboratorio.registrar_resultado", id_cita=c["id_cita"])})
    elif cuenta == CUENTA_PACIENTE and c["puede_cancelar"]:
        acciones.append({"texto": "Cancelar mi cita", "url": url_for("historial.cancelar_cita", id_cita=c["id_cita"]),
                         "metodo": "post", "peligro": True})
    return acciones


def semana(cuenta, usuario, datos_sesion, fecha=None, id_area=None, id_medico=None):
    """Citas de la semana que contiene `fecha`, en el formato que lee calendario.js."""
    dia = _fecha_o_hoy(fecha, cuenta, usuario)
    lunes = lunes_de(dia)
    viernes = lunes + timedelta(days=4)
    areas = _areas_visibles(cuenta)
    area_pedida = _opcional_entero(id_area)
    if area_pedida in areas and cuenta in (CUENTA_ADMINISTRADOR, CUENTA_RECEPCION):
        areas = (area_pedida,)

    citas = []
    for area in areas:
        condiciones = ["fecha_cita BETWEEN %s AND %s"]
        parametros = [lunes, viernes]
        if cuenta == CUENTA_PACIENTE:
            condiciones.append("cedula_paciente = %s")
            parametros.append(datos_sesion["cedula_paciente"])
        elif cuenta == CUENTA_MEDICO:
            condiciones.append("id_medico = %s")
            parametros.append(datos_sesion["id_medico"])
        elif _opcional_entero(id_medico) and area == AREA_CONSULTAS:
            condiciones.append("id_medico = %s")
            parametros.append(_opcional_entero(id_medico))
        elif _opcional_entero(id_medico):
            continue  # filtrar por medico solo aplica a las consultas
        citas += consultar(cuenta, f"{_SQL[area]} WHERE {' AND '.join(condiciones)} "
                                   "ORDER BY fecha_cita, hora_inicio, id_cita",
                           parametros, id_usuario_app=usuario)

    ahora = consultar(cuenta, "SELECT NOW() AS ahora", id_usuario_app=usuario, uno=True)["ahora"]
    salida = []
    for c in citas:
        inicio = c["fecha_cita"]
        hora = _hm(c["hora_inicio"])
        empieza = datetime.combine(inicio, time()) + c["hora_inicio"]
        c["puede_cancelar"] = c["estado"] in ESTADOS_ACTIVOS_CITA and empieza > ahora
        salida.append({
            "id_cita": c["id_cita"], "fecha": inicio.isoformat(), "dia": inicio.weekday() + 1,
            "hora": hora, "hora_fin": _hm(c["hora_fin"]), "estado": c["estado"],
            "area": c["id_area"], "paciente": c["paciente"], "cedula": c["cedula_paciente"],
            "medico": c["medico"], "detalle": c["detalle"], "lugar": c["lugar"],
            "id_medico": c["id_medico"] if c["id_area"] == AREA_CONSULTAS else None,
            "acciones": _acciones(cuenta, c),
        })
    return {
        "lunes": lunes.isoformat(), "viernes": viernes.isoformat(),
        "anterior": (lunes - timedelta(days=7)).isoformat(), "siguiente": (lunes + timedelta(days=7)).isoformat(),
        "hoy": ahora.date().isoformat(), "ahora": ahora.strftime("%Y-%m-%d %H:%M"),
        "primera": HORA_PRIMERA, "ultima": HORA_ULTIMA, "citas": salida,
    }


def filtros_agenda(cuenta, usuario):
    """Listas para los filtros de recepcion y administrador (area, medico)."""
    if cuenta not in (CUENTA_ADMINISTRADOR, CUENTA_RECEPCION):
        return {"areas": [], "medicos": []}
    return {
        "areas": consultar(cuenta, "SELECT id_area, nombre FROM area WHERE estado = 'activo' ORDER BY id_area",
                           id_usuario_app=usuario),
        "medicos": consultar(cuenta, """
            SELECT m.id_medico, CONCAT(m.nombres, ' ', m.apellidos) AS nombre, e.nombre AS especialidad
            FROM medico m JOIN especialidad e ON e.id_especialidad = m.id_especialidad
            WHERE m.estado = 'activo' ORDER BY m.apellidos, m.nombres""", id_usuario_app=usuario),
    }
