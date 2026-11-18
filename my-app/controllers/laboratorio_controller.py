"""Personal de laboratorio: agenda de examenes y registro del resultado."""
from conexion.conexionBD import consultar, transaccion
from utils import validators
from utils.constants import CUENTA_LABORATORIO, ESTADOS_ACTIVOS_CITA
from utils.errors import ErrorNegocio
from utils.helpers import pagina_actual, paginar, patron_like
from utils.logger import obtener_logger

log = obtener_logger("laboratorio")

POR_PAGINA = 15
ESTADOS_EXAMEN = ("pendiente", "realizado", "cancelado")

_SQL_EXAMEN = """
    SELECT a.id_cita, a.fecha_cita, a.hora_inicio, a.hora_fin, a.estado, a.cedula_paciente, a.paciente,
           a.medico_solicitante, a.id_subtipo, a.examen, a.estado_examen, a.fecha_realizacion, a.puesto,
           rl.id_resultado, (a.fecha_cita <= CURDATE()) AS llego_el_dia
    FROM v_agenda_laboratorio a
    LEFT JOIN v_resultados_laboratorio rl ON rl.id_cita = a.id_cita"""


def _completar(fila):
    fila["puede_registrar"] = (fila["estado"] in ESTADOS_ACTIVOS_CITA and fila["estado_examen"] == "pendiente"
                               and bool(fila["llego_el_dia"]))
    fila["puede_corregir"] = fila["id_resultado"] is not None
    return fila


def _fecha_o_none(valor):
    try:
        return validators.fecha(valor)
    except ErrorNegocio:
        return None


def agenda(usuario, q=None, estado=None, desde=None, hasta=None, pagina=1):
    """Examenes de laboratorio desde la fecha indicada (por defecto, desde hoy)."""
    hoy = consultar(CUENTA_LABORATORIO, "SELECT CURDATE() AS hoy", id_usuario_app=usuario, uno=True)["hoy"]
    desde_f = _fecha_o_none(desde) or hoy
    hasta_f = _fecha_o_none(hasta)
    condiciones, parametros = ["a.fecha_cita >= %s"], [desde_f]
    if hasta_f:
        condiciones.append("a.fecha_cita <= %s")
        parametros.append(hasta_f)
    patron = patron_like(q)
    if patron:
        condiciones.append("(a.cedula_paciente LIKE %s OR a.paciente LIKE %s)")
        parametros += [patron, patron]
    if estado in ESTADOS_EXAMEN:
        condiciones.append("a.estado_examen = %s")
        parametros.append(estado)
    donde = "WHERE " + " AND ".join(condiciones)

    total = consultar(CUENTA_LABORATORIO, f"SELECT COUNT(*) AS total FROM v_agenda_laboratorio a {donde}",
                      parametros, id_usuario_app=usuario, uno=True)["total"]
    pag = paginar(total, pagina_actual(pagina), POR_PAGINA)
    filas = consultar(CUENTA_LABORATORIO, f"{_SQL_EXAMEN} {donde} ORDER BY a.fecha_cita, a.hora_inicio, a.id_cita LIMIT %s OFFSET %s",
                      parametros + [pag["por_pagina"], pag["offset"]], id_usuario_app=usuario)
    return {"examenes": [_completar(f) for f in filas], "paginacion": pag, "estados": ESTADOS_EXAMEN,
            "filtros": {"q": q or "", "estado": estado or "", "desde": desde_f.isoformat(),
                        "hasta": hasta_f.isoformat() if hasta_f else ""}}


def obtener(usuario, id_cita):
    """El examen y, si ya existe, su resultado (para registrarlo o corregirlo)."""
    fila = consultar(CUENTA_LABORATORIO, f"{_SQL_EXAMEN} WHERE a.id_cita = %s", (id_cita,),
                     id_usuario_app=usuario, uno=True)
    if fila is None:
        raise ErrorNegocio("El examen no existe.", 404)
    resultado = None
    if fila["id_resultado"]:
        resultado = consultar(CUENTA_LABORATORIO, """
            SELECT fecha_resultado, resultado, observaciones FROM resultado_laboratorio WHERE id_cita = %s""",
                              (id_cita,), id_usuario_app=usuario, uno=True)
    return {"examen": _completar(fila), "resultado": resultado}


def _validar_datos(examen, datos):
    resultado = validators.texto(datos.get("resultado"), "El resultado", maximo=5000)
    observaciones = validators.texto(datos.get("observaciones"), "Las observaciones", maximo=2000, obligatorio=False)
    texto_fecha = str(datos.get("fecha_resultado") or "").strip()
    if texto_fecha:
        fecha = validators.no_futura(validators.fecha(texto_fecha, "La fecha del resultado"), "La fecha del resultado")
        if fecha < examen["fecha_cita"]:
            raise ErrorNegocio("La fecha del resultado no puede ser anterior a la fecha de la cita.")
    else:
        fecha = None                                    # se usa la fecha de hoy de la base de datos
    return resultado, observaciones, fecha


def registrar_resultado(usuario, id_cita, datos):
    """Registra el resultado, marca el examen como realizado y la cita como atendida."""
    examen = obtener(usuario, id_cita)["examen"]
    if examen["estado"] not in ESTADOS_ACTIVOS_CITA or examen["estado_examen"] != "pendiente":
        raise ErrorNegocio("A este examen ya no se le puede registrar un resultado.")
    if not examen["llego_el_dia"]:
        raise ErrorNegocio("El resultado se registra el día de la cita, no antes.")
    resultado, observaciones, fecha = _validar_datos(examen, datos)

    with transaccion(CUENTA_LABORATORIO, usuario) as cursor:
        cursor.execute("""UPDATE cita SET estado = 'atendida'
                          WHERE id_cita = %s AND estado IN ('pendiente', 'confirmada')""", (id_cita,))
        if cursor.rowcount != 1:
            raise ErrorNegocio("A este examen ya no se le puede registrar un resultado.")
        cursor.execute("""UPDATE cita_laboratorio SET estado_examen = 'realizado', fecha_realizacion = CURDATE()
                          WHERE id_cita = %s AND estado_examen = 'pendiente'""", (id_cita,))
        if cursor.rowcount != 1:
            raise ErrorNegocio("A este examen ya no se le puede registrar un resultado.")
        cursor.execute("""INSERT INTO resultado_laboratorio (id_cita, registrado_por, fecha_resultado, resultado,
                                                             observaciones)
                          VALUES (%s, %s, COALESCE(%s, CURDATE()), %s, %s)""",
                       (id_cita, usuario, fecha, resultado, observaciones))
    log.info("Resultado de laboratorio registrado en la cita %s (usuario %s)", id_cita, usuario)


def corregir_resultado(usuario, id_cita, datos):
    """Corrige el texto, las observaciones o la fecha de un resultado ya registrado."""
    contexto = obtener(usuario, id_cita)
    examen = contexto["examen"]
    if contexto["resultado"] is None:
        raise ErrorNegocio("Este examen todavía no tiene resultado.")
    resultado, observaciones, fecha = _validar_datos(examen, datos)
    with transaccion(CUENTA_LABORATORIO, usuario) as cursor:
        cursor.execute("""UPDATE resultado_laboratorio
                          SET resultado = %s, observaciones = %s, fecha_resultado = COALESCE(%s, fecha_resultado)
                          WHERE id_cita = %s""", (resultado, observaciones, fecha, id_cita))
    log.info("Resultado de laboratorio corregido en la cita %s (usuario %s)", id_cita, usuario)

def eliminar_resultado(usuario, id_cita):
    """Elimina un resultado que registro esta misma persona (por ejemplo, para corregir un error de fondo) y deja el
    examen otra vez pendiente para volver a registrarlo."""
    contexto = obtener(usuario, id_cita)
    if contexto["resultado"] is None:
        raise ErrorNegocio("Este examen no tiene resultado.")
    with transaccion(CUENTA_LABORATORIO, usuario) as cursor:
        cursor.execute("DELETE FROM resultado_laboratorio WHERE id_cita = %s AND registrado_por = %s",
                       (id_cita, usuario))
        if cursor.rowcount != 1:
            raise ErrorNegocio("Solo puedes eliminar los resultados que tú registraste.")
        cursor.execute("""UPDATE cita_laboratorio SET estado_examen = 'pendiente', fecha_realizacion = NULL
                          WHERE id_cita = %s AND estado_examen = 'realizado'""", (id_cita,))
        cursor.execute("UPDATE cita SET estado = 'pendiente' WHERE id_cita = %s AND estado = 'atendida'", (id_cita,))
    log.info("Resultado de laboratorio eliminado en la cita %s (usuario %s)", id_cita, usuario)