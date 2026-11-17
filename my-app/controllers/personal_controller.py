"""Personal del centro: administradores, recepcion, tecnicos de imagenologia y laboratoristas (solo administrador)."""
from conexion.conexionBD import consultar, ejecutar, transaccion
from utils import validators
from utils.constants import CUENTA_ADMINISTRADOR
from utils.errors import ErrorNegocio
from utils.helpers import pagina_actual, paginar, patron_like
from utils.logger import obtener_logger

log = obtener_logger("personal")

CUENTA = CUENTA_ADMINISTRADOR
ESTADOS = ("activo", "inactivo")
POR_PAGINA = 10

_SQL_BASE = """
    SELECT p.id_personal, p.cedula, p.nombres, p.apellidos, p.telefono, p.correo, p.cargo, p.estado,
           u.id_usuario, u.nombre_usuario, r.nombre AS rol
    FROM personal p
    LEFT JOIN usuario u ON u.id_personal = p.id_personal
    LEFT JOIN rol r ON r.id_rol = u.id_rol"""


def listar(administrador, q=None, estado=None, pagina=1):
    condiciones, parametros = [], []
    patron = patron_like(q)
    if patron:
        condiciones.append("(p.cedula LIKE %s OR p.nombres LIKE %s OR p.apellidos LIKE %s OR p.cargo LIKE %s)")
        parametros += [patron] * 4
    if estado in ESTADOS:
        condiciones.append("p.estado = %s")
        parametros.append(estado)
    donde = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""

    total = consultar(CUENTA, f"SELECT COUNT(*) AS total FROM personal p {donde}", parametros,
                      id_usuario_app=administrador, uno=True)["total"]
    pag = paginar(total, pagina_actual(pagina), POR_PAGINA)
    filas = consultar(CUENTA, f"{_SQL_BASE} {donde} ORDER BY p.apellidos, p.nombres LIMIT %s OFFSET %s",
                      parametros + [pag["por_pagina"], pag["offset"]], id_usuario_app=administrador)
    return {"personal": filas, "paginacion": pag, "filtros": {"q": q or "", "estado": estado or ""}}


def obtener(id_personal, administrador):
    fila = consultar(CUENTA, f"{_SQL_BASE} WHERE p.id_personal = %s", (id_personal,),
                     id_usuario_app=administrador, uno=True)
    if fila is None:
        raise ErrorNegocio("El miembro del personal no existe.", 404)
    return fila


def _validar(datos):
    return {
        "nombres": validators.nombre_persona(datos.get("nombres"), "Los nombres"),
        "apellidos": validators.nombre_persona(datos.get("apellidos"), "Los apellidos"),
        "telefono": validators.telefono(datos.get("telefono")),
        "correo": validators.correo(datos.get("correo"), obligatorio=False),
        "cargo": validators.texto(datos.get("cargo"), "El cargo", maximo=80, minimo=2),
    }


def crear(datos, administrador):
    cedula = validators.cedula(datos.get("cedula"))
    v = _validar(datos)
    resultado = ejecutar(CUENTA, """
        INSERT INTO personal (cedula, nombres, apellidos, telefono, correo, cargo)
        VALUES (%s, %s, %s, %s, %s, %s)""",
                         (cedula, v["nombres"], v["apellidos"], v["telefono"], v["correo"], v["cargo"]),
                         id_usuario_app=administrador)
    log.info("Personal creado: %s por el usuario %s", cedula, administrador)
    return resultado["id"]


def actualizar(id_personal, datos, administrador):
    """La cedula no se cambia (el usuario la comparte). Los nombres tambien se actualizan en su usuario."""
    obtener(id_personal, administrador)
    v = _validar(datos)
    with transaccion(CUENTA, administrador) as cursor:
        cursor.execute("""UPDATE personal SET nombres = %s, apellidos = %s, telefono = %s, correo = %s, cargo = %s
                          WHERE id_personal = %s""",
                       (v["nombres"], v["apellidos"], v["telefono"], v["correo"], v["cargo"], id_personal))
        cursor.execute("UPDATE usuario SET nombres = %s, apellidos = %s WHERE id_personal = %s",
                       (v["nombres"], v["apellidos"], id_personal))
    log.info("Personal %s modificado por el usuario %s", id_personal, administrador)


def cambiar_estado(id_personal, estado, administrador):
    """Al desactivar a alguien tambien se desactiva su usuario. Al reactivarlo, el usuario se activa aparte."""
    estado = validators.opcion(estado, ESTADOS, "El estado")
    actual = obtener(id_personal, administrador)
    if estado == "inactivo" and actual["id_usuario"] == administrador:
        raise ErrorNegocio("No puedes desactivar tu propio perfil.")
    with transaccion(CUENTA, administrador) as cursor:
        cursor.execute("UPDATE personal SET estado = %s WHERE id_personal = %s", (estado, id_personal))
        if estado == "inactivo":
            cursor.execute("UPDATE usuario SET estado = 'inactivo' WHERE id_personal = %s AND estado = 'activo'",
                           (id_personal,))
    log.info("Personal %s pasa a %s (por el usuario %s)", id_personal, estado, administrador)


def eliminar(id_personal, administrador):
    actual = obtener(id_personal, administrador)
    if actual["id_usuario"]:
        raise ErrorNegocio("Tiene un usuario asociado. Desactívalo en lugar de eliminarlo.")
    ejecutar(CUENTA, "DELETE FROM personal WHERE id_personal = %s", (id_personal,), id_usuario_app=administrador)
    log.info("Personal %s eliminado por el usuario %s", id_personal, administrador)