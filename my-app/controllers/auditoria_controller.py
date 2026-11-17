"""Auditoria para el administrador: cambios de las citas y accesos al sistema.

Los registros no se pueden editar ni borrar (lo impiden triggers de la base de datos): aqui solo se consultan.
"""
from conexion.conexionBD import consultar
from utils import validators
from utils.constants import CUENTA_ADMINISTRADOR
from utils.errors import ErrorNegocio
from utils.helpers import pagina_actual, paginar, patron_like

POR_PAGINA = 20
RESULTADOS_ACCESO = ("exitoso", "fallido", "bloqueado", "cierre_sesion")
ESTADOS_AUDITADOS = ("pendiente", "confirmada", "atendida", "cancelada", "no_asistio", "eliminada")


def _fecha_o_none(valor):
    try:
        return validators.fecha(valor)
    except ErrorNegocio:
        return None


def lista(usuario, id_cita=None, estado=None, cuenta_bd=None, desde=None, hasta=None, pagina=1):
    """Cambios de las citas: quien (cuenta de MySQL y persona del sistema), cuando y que cambio."""
    condiciones, parametros = [], []
    try:
        numero = validators.entero(id_cita, "La cita", minimo=1) if str(id_cita or "").strip() else None
    except ErrorNegocio:
        numero = None
    if numero:
        condiciones.append("a.id_cita = %s")
        parametros.append(numero)
    if estado in ESTADOS_AUDITADOS:
        condiciones.append("a.estado_nuevo = %s")
        parametros.append(estado)
    patron = patron_like(cuenta_bd)
    if patron:
        condiciones.append("a.usuario_bd LIKE %s")
        parametros.append(patron)
    desde_f, hasta_f = _fecha_o_none(desde), _fecha_o_none(hasta)
    if desde_f:
        condiciones.append("a.fecha_cambio >= %s")
        parametros.append(desde_f)
    if hasta_f:
        condiciones.append("a.fecha_cambio < %s + INTERVAL 1 DAY")
        parametros.append(hasta_f)
    donde = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""

    total = consultar(CUENTA_ADMINISTRADOR, f"SELECT COUNT(*) AS total FROM auditoria_cita a {donde}", parametros,
                      id_usuario_app=usuario, uno=True)["total"]
    pag = paginar(total, pagina_actual(pagina), POR_PAGINA)
    filas = consultar(CUENTA_ADMINISTRADOR, f"""
        SELECT a.id_auditoria, a.fecha_cambio, a.id_cita, a.estado_anterior, a.estado_nuevo, a.fecha_anterior,
               a.fecha_nueva, a.hora_anterior, a.hora_nueva, a.usuario_bd, a.id_usuario_app,
               u.nombre_usuario, CONCAT(u.nombres, ' ', u.apellidos) AS persona
        FROM auditoria_cita a LEFT JOIN usuario u ON u.id_usuario = a.id_usuario_app {donde}
        ORDER BY a.fecha_cambio DESC, a.id_auditoria DESC LIMIT %s OFFSET %s""",
                      parametros + [pag["por_pagina"], pag["offset"]], id_usuario_app=usuario)
    return {"cambios": filas, "paginacion": pag, "estados": ESTADOS_AUDITADOS,
            "filtros": {"id_cita": numero or "", "estado": estado or "", "cuenta_bd": cuenta_bd or "",
                        "desde": desde_f.isoformat() if desde_f else "",
                        "hasta": hasta_f.isoformat() if hasta_f else ""}}


def accesos(usuario, q=None, resultado=None, desde=None, hasta=None, pagina=1):
    """Inicios y cierres de sesion, intentos fallidos y bloqueos."""
    condiciones, parametros = [], []
    patron = patron_like(q)
    if patron:
        condiciones.append("(a.cedula_intento LIKE %s OR u.nombre_usuario LIKE %s)")
        parametros += [patron, patron]
    if resultado in RESULTADOS_ACCESO:
        condiciones.append("a.resultado = %s")
        parametros.append(resultado)
    desde_f, hasta_f = _fecha_o_none(desde), _fecha_o_none(hasta)
    if desde_f:
        condiciones.append("a.fecha >= %s")
        parametros.append(desde_f)
    if hasta_f:
        condiciones.append("a.fecha < %s + INTERVAL 1 DAY")
        parametros.append(hasta_f)
    donde = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""

    total = consultar(CUENTA_ADMINISTRADOR, f"""SELECT COUNT(*) AS total FROM auditoria_acceso a
                                                LEFT JOIN usuario u ON u.id_usuario = a.id_usuario {donde}""",
                      parametros, id_usuario_app=usuario, uno=True)["total"]
    pag = paginar(total, pagina_actual(pagina), POR_PAGINA)
    filas = consultar(CUENTA_ADMINISTRADOR, f"""
        SELECT a.id_acceso, a.fecha, a.cedula_intento, a.id_usuario, a.resultado, a.ip, a.navegador,
               u.nombre_usuario, CONCAT(u.nombres, ' ', u.apellidos) AS persona
        FROM auditoria_acceso a LEFT JOIN usuario u ON u.id_usuario = a.id_usuario {donde}
        ORDER BY a.fecha DESC, a.id_acceso DESC LIMIT %s OFFSET %s""",
                      parametros + [pag["por_pagina"], pag["offset"]], id_usuario_app=usuario)
    resumen = consultar(CUENTA_ADMINISTRADOR, """
        SELECT resultado, COUNT(*) AS cantidad FROM auditoria_acceso
        WHERE fecha >= NOW() - INTERVAL 1 DAY GROUP BY resultado""", id_usuario_app=usuario)
    return {"accesos": filas, "paginacion": pag, "resultados": RESULTADOS_ACCESO,
            "resumen_24h": {f["resultado"]: f["cantidad"] for f in resumen},
            "filtros": {"q": q or "", "resultado": resultado or "",
                        "desde": desde_f.isoformat() if desde_f else "",
                        "hasta": hasta_f.isoformat() if hasta_f else ""}}