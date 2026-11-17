"""Medicos (solo administrador)."""
from conexion.conexionBD import consultar, ejecutar, transaccion
from utils import validators
from utils.constants import CUENTA_ADMINISTRADOR
from utils.errors import ErrorNegocio
from utils.helpers import pagina_actual, paginar, patron_like
from utils.logger import obtener_logger

log = obtener_logger("medicos")

CUENTA = CUENTA_ADMINISTRADOR
ESTADOS = ("activo", "inactivo")
POR_PAGINA = 10

_SQL_BASE = """
    SELECT m.id_medico, m.id_especialidad, e.nombre AS especialidad, m.cedula, m.nombres, m.apellidos,
           m.telefono, m.correo, m.estado, u.id_usuario, u.nombre_usuario
    FROM medico m
    JOIN especialidad e ON e.id_especialidad = m.id_especialidad
    LEFT JOIN usuario u ON u.id_medico = m.id_medico"""


def especialidades_activas(administrador):
    return consultar(CUENTA, """SELECT id_especialidad, nombre, costo_consulta FROM especialidad
                                WHERE estado = 'activo' ORDER BY nombre""", id_usuario_app=administrador)


def listar(administrador, q=None, id_especialidad=None, estado=None, pagina=1):
    condiciones, parametros = [], []
    patron = patron_like(q)
    if patron:
        condiciones.append("(m.cedula LIKE %s OR m.nombres LIKE %s OR m.apellidos LIKE %s)")
        parametros += [patron] * 3
    if id_especialidad:
        condiciones.append("m.id_especialidad = %s")
        parametros.append(id_especialidad)
    if estado in ESTADOS:
        condiciones.append("m.estado = %s")
        parametros.append(estado)
    donde = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""

    total = consultar(CUENTA, f"SELECT COUNT(*) AS total FROM medico m {donde}", parametros,
                      id_usuario_app=administrador, uno=True)["total"]
    pag = paginar(total, pagina_actual(pagina), POR_PAGINA)
    filas = consultar(CUENTA, f"{_SQL_BASE} {donde} ORDER BY m.apellidos, m.nombres LIMIT %s OFFSET %s",
                      parametros + [pag["por_pagina"], pag["offset"]], id_usuario_app=administrador)
    return {"medicos": filas, "paginacion": pag,
            "especialidades": consultar(CUENTA, "SELECT id_especialidad, nombre FROM especialidad ORDER BY nombre",
                                        id_usuario_app=administrador),
            "filtros": {"q": q or "", "id_especialidad": id_especialidad or "", "estado": estado or ""}}


def obtener(id_medico, administrador):
    fila = consultar(CUENTA, f"{_SQL_BASE} WHERE m.id_medico = %s", (id_medico,),
                     id_usuario_app=administrador, uno=True)
    if fila is None:
        raise ErrorNegocio("El médico no existe.", 404)
    return fila


def _validar(datos, administrador):
    id_especialidad = validators.texto(datos.get("id_especialidad"), "La especialidad", maximo=10)
    existe = consultar(CUENTA, "SELECT estado FROM especialidad WHERE id_especialidad = %s", (id_especialidad,),
                       id_usuario_app=administrador, uno=True)
    if existe is None or existe["estado"] != "activo":
        raise ErrorNegocio("La especialidad seleccionada no existe o está inactiva.")
    return {
        "id_especialidad": id_especialidad,
        "nombres": validators.nombre_persona(datos.get("nombres"), "Los nombres"),
        "apellidos": validators.nombre_persona(datos.get("apellidos"), "Los apellidos"),
        "telefono": validators.telefono(datos.get("telefono")),
        "correo": validators.correo(datos.get("correo"), obligatorio=False),
    }


def crear(datos, administrador):
    cedula = validators.cedula(datos.get("cedula"))
    v = _validar(datos, administrador)
    resultado = ejecutar(CUENTA, """
        INSERT INTO medico (id_especialidad, cedula, nombres, apellidos, telefono, correo)
        VALUES (%s, %s, %s, %s, %s, %s)""",
                         (v["id_especialidad"], cedula, v["nombres"], v["apellidos"], v["telefono"], v["correo"]),
                         id_usuario_app=administrador)
    log.info("Medico creado: %s por el usuario %s", cedula, administrador)
    return resultado["id"]


def actualizar(id_medico, datos, administrador):
    """La cedula no se cambia. Los nombres tambien se actualizan en su usuario."""
    obtener(id_medico, administrador)
    v = _validar(datos, administrador)
    with transaccion(CUENTA, administrador) as cursor:
        cursor.execute("""UPDATE medico SET id_especialidad = %s, nombres = %s, apellidos = %s, telefono = %s,
                                 correo = %s WHERE id_medico = %s""",
                       (v["id_especialidad"], v["nombres"], v["apellidos"], v["telefono"], v["correo"], id_medico))
        cursor.execute("UPDATE usuario SET nombres = %s, apellidos = %s WHERE id_medico = %s",
                       (v["nombres"], v["apellidos"], id_medico))
    log.info("Medico %s modificado por el usuario %s", id_medico, administrador)


def cambiar_estado(id_medico, estado, administrador):
    """Al desactivar a un medico tambien se desactiva su usuario. Al reactivarlo, el usuario se activa aparte."""
    estado = validators.opcion(estado, ESTADOS, "El estado")
    obtener(id_medico, administrador)
    with transaccion(CUENTA, administrador) as cursor:
        cursor.execute("UPDATE medico SET estado = %s WHERE id_medico = %s", (estado, id_medico))
        if estado == "inactivo":
            cursor.execute("UPDATE usuario SET estado = 'inactivo' WHERE id_medico = %s AND estado = 'activo'",
                           (id_medico,))
    log.info("Medico %s pasa a %s (por el usuario %s)", id_medico, estado, administrador)


def eliminar(id_medico, administrador):
    actual = obtener(id_medico, administrador)
    if actual["id_usuario"]:
        raise ErrorNegocio("Tiene un usuario asociado. Desactívalo en lugar de eliminarlo.")
    # Si tiene citas o examenes solicitados, MySQL lo impide (clave foranea) y se muestra el mensaje correspondiente
    ejecutar(CUENTA, "DELETE FROM medico WHERE id_medico = %s", (id_medico,), id_usuario_app=administrador)
    log.info("Medico %s eliminado por el usuario %s", id_medico, administrador)