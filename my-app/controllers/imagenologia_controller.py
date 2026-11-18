"""Personal de imagenologia: agenda de examenes y registro de que el examen se realizo."""
from conexion.conexionBD import consultar, transaccion
from utils import validators
from utils.constants import CUENTA_IMAGENOLOGIA, ESTADOS_ACTIVOS_CITA
from utils.errors import ErrorNegocio
from utils.helpers import pagina_actual, paginar, patron_like
from utils.logger import obtener_logger

log = obtener_logger("imagenologia")

POR_PAGINA = 15
ESTADOS_PROCEDIMIENTO = ("pendiente", "realizado", "cancelado")


def _completar(fila):
    pendiente = fila["estado"] in ESTADOS_ACTIVOS_CITA and fila["estado_procedimiento"] == "pendiente"
    fila["puede_registrar"] = pendiente and bool(fila["llego_el_dia"])
    fila["puede_cancelar"] = pendiente
    return fila


def _fecha_o_none(valor):
    try:
        return validators.fecha(valor)
    except ErrorNegocio:
        return None


def agenda(usuario, q=None, estado=None, desde=None, hasta=None, pagina=1):
    """Examenes de imagenologia desde la fecha indicada (por defecto, desde hoy)."""
    hoy = consultar(CUENTA_IMAGENOLOGIA, "SELECT CURDATE() AS hoy", id_usuario_app=usuario, uno=True)["hoy"]
    desde_f = _fecha_o_none(desde) or hoy
    hasta_f = _fecha_o_none(hasta)
    condiciones, parametros = ["fecha_cita >= %s"], [desde_f]
    if hasta_f:
        condiciones.append("fecha_cita <= %s")
        parametros.append(hasta_f)
    patron = patron_like(q)
    if patron:
        condiciones.append("(cedula_paciente LIKE %s OR paciente LIKE %s)")
        parametros += [patron, patron]
    if estado in ESTADOS_PROCEDIMIENTO:
        condiciones.append("estado_procedimiento = %s")
        parametros.append(estado)
    donde = "WHERE " + " AND ".join(condiciones)

    total = consultar(CUENTA_IMAGENOLOGIA, f"SELECT COUNT(*) AS total FROM v_agenda_imagenologia {donde}",
                      parametros, id_usuario_app=usuario, uno=True)["total"]
    pag = paginar(total, pagina_actual(pagina), POR_PAGINA)
    filas = consultar(CUENTA_IMAGENOLOGIA, f"""
        SELECT *, (fecha_cita <= CURDATE()) AS llego_el_dia FROM v_agenda_imagenologia {donde}
        ORDER BY fecha_cita, hora_inicio, id_cita LIMIT %s OFFSET %s""",
                      parametros + [pag["por_pagina"], pag["offset"]], id_usuario_app=usuario)
    return {"examenes": [_completar(f) for f in filas], "paginacion": pag, "estados": ESTADOS_PROCEDIMIENTO,
            "filtros": {"q": q or "", "estado": estado or "", "desde": desde_f.isoformat(),
                        "hasta": hasta_f.isoformat() if hasta_f else ""}}


def obtener(usuario, id_cita):
    fila = consultar(CUENTA_IMAGENOLOGIA, """
        SELECT *, (fecha_cita <= CURDATE()) AS llego_el_dia FROM v_agenda_imagenologia WHERE id_cita = %s""",
                     (id_cita,), id_usuario_app=usuario, uno=True)
    if fila is None:
        raise ErrorNegocio("El examen no existe.", 404)
    return _completar(fila)


def registrar_realizacion(usuario, id_cita):
    """Marca el examen como realizado (fecha y hora actuales, quien lo hizo) y la cita como atendida."""
    examen = obtener(usuario, id_cita)
    if examen["estado"] not in ESTADOS_ACTIVOS_CITA or examen["estado_procedimiento"] != "pendiente":
        raise ErrorNegocio("Este examen ya no se puede registrar como realizado.")
    if not examen["llego_el_dia"]:
        raise ErrorNegocio("El examen se registra el día de la cita, no antes.")

    with transaccion(CUENTA_IMAGENOLOGIA, usuario) as cursor:
        # Los UPDATE con condicion hacen de candado: si otra pestana ya lo registro, no cambian ninguna fila.
        cursor.execute("""UPDATE cita SET estado = 'atendida'
                          WHERE id_cita = %s AND estado IN ('pendiente', 'confirmada')""", (id_cita,))
        if cursor.rowcount != 1:
            raise ErrorNegocio("Este examen ya no se puede registrar como realizado.")
        cursor.execute("""UPDATE cita_imagenologia
                          SET estado_procedimiento = 'realizado', fecha_realizacion = NOW(), id_usuario_realiza = %s
                          WHERE id_cita = %s AND estado_procedimiento = 'pendiente'""", (usuario, id_cita))
        if cursor.rowcount != 1:
            raise ErrorNegocio("Este examen ya no se puede registrar como realizado.")
    log.info("Examen de imagenologia %s realizado (usuario %s)", id_cita, usuario)

def cancelar(usuario, id_cita):
    """Cancela un examen pendiente (por ejemplo, si el equipo no esta disponible o el paciente no puede venir)."""
    examen = obtener(usuario, id_cita)
    if not examen["puede_cancelar"]:
        raise ErrorNegocio("Este examen ya no se puede cancelar.")
    with transaccion(CUENTA_IMAGENOLOGIA, usuario) as cursor:
        cursor.execute("""UPDATE cita SET estado = 'cancelada'
                          WHERE id_cita = %s AND estado IN ('pendiente', 'confirmada')""", (id_cita,))
        if cursor.rowcount != 1:
            raise ErrorNegocio("Este examen ya no se puede cancelar.")
        cursor.execute("""UPDATE cita_imagenologia SET estado_procedimiento = 'cancelado'
                          WHERE id_cita = %s AND estado_procedimiento = 'pendiente'""", (id_cita,))
        if cursor.rowcount != 1:
            raise ErrorNegocio("Este examen ya no se puede cancelar.")
    log.info("Examen de imagenologia %s cancelado (usuario %s)", id_cita, usuario)