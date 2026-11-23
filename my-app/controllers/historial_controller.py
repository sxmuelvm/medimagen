"""Paciente: sus citas, historial de consultas, recetas y resultados.

La cuenta de MySQL del paciente solo puede leer vistas, y cada consulta se filtra por la cedula que viene de la
SESION (nunca de la URL ni del formulario), asi que un paciente solo ve lo suyo.
"""
from conexion.conexionBD import consultar, ejecutar
from utils import validators
from utils.constants import CUENTA_PACIENTE, ESTADOS_CITA
from utils.errors import ErrorNegocio
from utils.helpers import pagina_actual, paginar
from utils.logger import obtener_logger

log = obtener_logger("historial")

POR_PAGINA = 10

# Las tres agendas (consulta, imagenologia, laboratorio) en una sola lista de citas del paciente
_UNION_CITAS = """
    SELECT id_cita, 'Consulta médica' AS area, fecha_cita, hora_inicio, hora_fin, estado, costo_aplicado,
           especialidad AS detalle, medico AS profesional, consultorio AS lugar, NULL AS estado_examen
    FROM v_agenda_consultas WHERE cedula_paciente = %s
    UNION ALL
    SELECT id_cita, 'Imagenología', fecha_cita, hora_inicio, hora_fin, estado, costo_aplicado,
           subtipo, medico_solicitante, equipo, estado_procedimiento
    FROM v_agenda_imagenologia WHERE cedula_paciente = %s
    UNION ALL
    SELECT id_cita, 'Laboratorio', fecha_cita, hora_inicio, hora_fin, estado, costo_aplicado,
           examen, medico_solicitante, puesto, estado_examen
    FROM v_agenda_laboratorio WHERE cedula_paciente = %s"""


def _fecha_o_none(valor):
    try:
        return validators.fecha(valor)
    except ErrorNegocio:
        return None


def _cuantos_ids(ids):
    return ", ".join(["%s"] * len(ids))


# ---------------------------------------------------------------------------
# Citas
# ---------------------------------------------------------------------------
def mis_citas(usuario, cedula, estado=None, desde=None, hasta=None, pagina=1):
    """Todas las citas del paciente (mas recientes primero) y, aparte, sus proximas citas."""
    condiciones, parametros = [], []
    desde_f, hasta_f = _fecha_o_none(desde), _fecha_o_none(hasta)
    if desde_f:
        condiciones.append("fecha_cita >= %s")
        parametros.append(desde_f)
    if hasta_f:
        condiciones.append("fecha_cita <= %s")
        parametros.append(hasta_f)
    if estado in ESTADOS_CITA:
        condiciones.append("estado = %s")
        parametros.append(estado)
    donde = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""
    base = [cedula] * 3

    total = consultar(CUENTA_PACIENTE, f"SELECT COUNT(*) AS total FROM ({_UNION_CITAS}) t {donde}", base + parametros,
                      id_usuario_app=usuario, uno=True)["total"]
    pag = paginar(total, pagina_actual(pagina), POR_PAGINA)
    citas = consultar(CUENTA_PACIENTE, f"""SELECT * FROM ({_UNION_CITAS}) t {donde}
                                           ORDER BY fecha_cita DESC, hora_inicio DESC, id_cita DESC
                                           LIMIT %s OFFSET %s""",
                      base + parametros + [pag["por_pagina"], pag["offset"]], id_usuario_app=usuario)
    proximas = consultar(CUENTA_PACIENTE, f"""
        SELECT * FROM ({_UNION_CITAS}) t
        WHERE estado IN ('pendiente', 'confirmada') AND TIMESTAMP(fecha_cita, hora_inicio) > NOW()
        ORDER BY fecha_cita, hora_inicio LIMIT 5""", base, id_usuario_app=usuario)
    return {"citas": citas, "proximas": proximas, "paginacion": pag, "estados": ESTADOS_CITA,
            "filtros": {"estado": estado or "", "desde": desde_f.isoformat() if desde_f else "",
                        "hasta": hasta_f.isoformat() if hasta_f else ""}}


# ---------------------------------------------------------------------------
# Historial de consultas
# ---------------------------------------------------------------------------
def mi_historial(usuario, cedula, pagina=1):
    """Consultas atendidas (mas recientes primero), cada una con sus diagnosticos."""
    total = consultar(CUENTA_PACIENTE, """
        SELECT COUNT(DISTINCT id_consulta) AS total FROM v_historial_paciente WHERE cedula_paciente = %s""",
                      (cedula,), id_usuario_app=usuario, uno=True)["total"]
    pag = paginar(total, pagina_actual(pagina), POR_PAGINA)
    ids = [f["id_consulta"] for f in consultar(CUENTA_PACIENTE, """
        SELECT id_consulta FROM v_historial_paciente WHERE cedula_paciente = %s
        GROUP BY id_consulta, fecha_hora_atencion
        ORDER BY fecha_hora_atencion DESC, id_consulta DESC LIMIT %s OFFSET %s""",
                                               (cedula, pag["por_pagina"], pag["offset"]), id_usuario_app=usuario)]
    consultas = []
    if ids:
        filas = consultar(CUENTA_PACIENTE, f"""
            SELECT id_consulta, fecha_hora_atencion, medico, especialidad, motivo_consulta, observaciones, diagnostico
            FROM v_historial_paciente WHERE cedula_paciente = %s AND id_consulta IN ({_cuantos_ids(ids)})
            ORDER BY fecha_hora_atencion DESC, id_consulta DESC""", [cedula] + ids, id_usuario_app=usuario)
        por_id = {}
        for fila in filas:
            consulta = por_id.get(fila["id_consulta"])
            if consulta is None:
                consulta = por_id[fila["id_consulta"]] = {
                    "id_consulta": fila["id_consulta"], "fecha_hora_atencion": fila["fecha_hora_atencion"],
                    "medico": fila["medico"], "especialidad": fila["especialidad"],
                    "motivo_consulta": fila["motivo_consulta"], "observaciones": fila["observaciones"],
                    "diagnosticos": []}
                consultas.append(consulta)
            if fila["diagnostico"]:
                consulta["diagnosticos"].append(fila["diagnostico"])
    return {"consultas": consultas, "paginacion": pag}


# ---------------------------------------------------------------------------
# Recetas
# ---------------------------------------------------------------------------
def mis_recetas(usuario, cedula, pagina=1):
    """Recetas (mas recientes primero), cada una con sus medicamentos."""
    total = consultar(CUENTA_PACIENTE, """
        SELECT COUNT(DISTINCT id_prescripcion) AS total FROM v_recetas WHERE cedula_paciente = %s""",
                      (cedula,), id_usuario_app=usuario, uno=True)["total"]
    pag = paginar(total, pagina_actual(pagina), POR_PAGINA)
    ids = [f["id_prescripcion"] for f in consultar(CUENTA_PACIENTE, """
        SELECT id_prescripcion FROM v_recetas WHERE cedula_paciente = %s
        GROUP BY id_prescripcion, fecha_prescripcion
        ORDER BY fecha_prescripcion DESC, id_prescripcion DESC LIMIT %s OFFSET %s""",
                                                   (cedula, pag["por_pagina"], pag["offset"]),
                                                   id_usuario_app=usuario)]
    recetas = []
    if ids:
        filas = consultar(CUENTA_PACIENTE, f"""
            SELECT id_prescripcion, fecha_prescripcion, medico, medicamento,
                   dosis, frecuencia, duracion, indicaciones
            FROM v_recetas WHERE cedula_paciente = %s AND id_prescripcion IN ({_cuantos_ids(ids)})
            ORDER BY fecha_prescripcion DESC, id_prescripcion DESC, medicamento""", [cedula] + ids,
                          id_usuario_app=usuario)
        por_id = {}
        for fila in filas:
            receta = por_id.get(fila["id_prescripcion"])
            if receta is None:
                receta = por_id[fila["id_prescripcion"]] = {
                    "id_prescripcion": fila["id_prescripcion"], "fecha_prescripcion": fila["fecha_prescripcion"],
                    "medico": fila["medico"], "medicamentos": []}
                recetas.append(receta)
            receta["medicamentos"].append({k: fila[k] for k in ("medicamento", "dosis", "frecuencia", "duracion", "indicaciones")})
    return {"recetas": recetas, "paginacion": pag}


# ---------------------------------------------------------------------------
# Resultados
# ---------------------------------------------------------------------------
def mis_resultados(usuario, cedula, pagina=1):
    """Resultados de laboratorio (con su texto) y estudios de imagenologia ya realizados."""
    total = consultar(CUENTA_PACIENTE, "SELECT COUNT(*) AS total FROM v_resultados_laboratorio WHERE cedula_paciente = %s",
                      (cedula,), id_usuario_app=usuario, uno=True)["total"]
    pag = paginar(total, pagina_actual(pagina), POR_PAGINA)
    laboratorio = consultar(CUENTA_PACIENTE, """
        SELECT id_resultado, id_cita, examen, medico_solicitante, fecha_realizacion, fecha_resultado, resultado,
               observaciones
        FROM v_resultados_laboratorio WHERE cedula_paciente = %s
        ORDER BY fecha_resultado DESC, id_resultado DESC LIMIT %s OFFSET %s""",
                            (cedula, pag["por_pagina"], pag["offset"]), id_usuario_app=usuario)
    imagenologia = consultar(CUENTA_PACIENTE, """
        SELECT id_cita, fecha_cita, tipo, subtipo, medico_solicitante, equipo, fecha_realizacion
        FROM v_agenda_imagenologia WHERE cedula_paciente = %s AND estado_procedimiento = 'realizado'
        ORDER BY fecha_realizacion DESC, id_cita DESC LIMIT 20""", (cedula,), id_usuario_app=usuario)
    return {"laboratorio": laboratorio, "imagenologia": imagenologia, "paginacion": pag}

# ---------------------------------------------------------------------------
# Lo que el paciente puede modificar de lo suyo (por procedimientos que comprueban que todo sea suyo)
# ---------------------------------------------------------------------------
def mis_datos(usuario, cedula):
    """Datos de contacto del paciente (la cedula sale de la sesion, nunca del formulario)."""
    fila = consultar(CUENTA_PACIENTE, "SELECT * FROM v_contacto_paciente WHERE cedula_paciente = %s", (cedula,),
                     id_usuario_app=usuario, uno=True)
    if fila is None:
        raise ErrorNegocio("No se encontró tu ficha de paciente.", 404)
    return fila


def actualizar_contacto(usuario, cedula, datos):
    """El paciente cambia solo su telefono y correo. Nombre, cedula y fecha de nacimiento los corrige
    recepcion."""
    ejecutar(CUENTA_PACIENTE, "CALL sp_paciente_actualizar_contacto(%s, %s, %s)",
             (cedula, validators.telefono(datos.get("telefono")),
              validators.correo(datos.get("correo"), obligatorio=False)),
             id_usuario_app=usuario)
    log.info("El paciente %s actualizo su contacto (usuario %s)", cedula, usuario)


def cancelar_cita(usuario, cedula, id_cita):
    """El paciente cancela una cita suya pendiente que aun no empezo. Reservar sigue siendo trabajo de recepcion."""
    ejecutar(CUENTA_PACIENTE, "CALL sp_paciente_cancelar_cita(%s, %s)", (cedula, id_cita), id_usuario_app=usuario)
    log.info("El paciente %s cancelo la cita %s (usuario %s)", cedula, id_cita, usuario)