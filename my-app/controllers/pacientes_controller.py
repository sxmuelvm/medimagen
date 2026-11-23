"""Pacientes. Lo usan el administrador y recepcion, cada uno con su propia cuenta de MySQL.

Recepcion puede registrar, buscar, modificar, desactivar y (si no tienen citas ni usuario) eliminar pacientes;
no ve datos clinicos ni usuarios.
Cambiar el estado y eliminar es solo del administrador (lo controla el router).
"""
from datetime import date

from conexion.conexionBD import consultar, ejecutar, transaccion
from utils import validators
from utils.constants import CUENTA_ADMINISTRADOR
from utils.errors import ErrorNegocio
from utils.helpers import pagina_actual, paginar, patron_like
from utils.logger import obtener_logger

log = obtener_logger("pacientes")

ESTADOS = ("activo", "inactivo")
SEXOS = ("M", "F")
POR_PAGINA = 10

_COLUMNAS = """p.cedula_paciente, p.nombres, p.apellidos, p.fecha_nacimiento, p.sexo, p.telefono, p.correo,
               p.direccion, p.fecha_registro, p.estado,
               TIMESTAMPDIFF(YEAR, p.fecha_nacimiento, CURDATE()) AS edad"""
# recepcion no puede leer la tabla usuario: el nombre de usuario solo se consulta con la cuenta del administrador
_USUARIO = ", (SELECT u.nombre_usuario FROM usuario u WHERE u.cedula = p.cedula_paciente) AS usuario"


def _cedula_ruta(cedula):
    try:
        return validators.cedula(cedula)
    except ErrorNegocio:
        raise ErrorNegocio("El paciente no existe.", 404) from None


def _sql_base(cuenta):
    return f"SELECT {_COLUMNAS}{_USUARIO if cuenta == CUENTA_ADMINISTRADOR else ''} FROM paciente p"


def listar(cuenta, usuario_app, q=None, estado=None, pagina=1):
    condiciones, parametros = [], []
    patron = patron_like(q)
    if patron:
        condiciones.append("(p.cedula_paciente LIKE %s OR p.nombres LIKE %s OR p.apellidos LIKE %s)")
        parametros += [patron] * 3
    if estado in ESTADOS:
        condiciones.append("p.estado = %s")
        parametros.append(estado)
    donde = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""

    total = consultar(cuenta, f"SELECT COUNT(*) AS total FROM paciente p {donde}", parametros,
                      id_usuario_app=usuario_app, uno=True)["total"]
    pag = paginar(total, pagina_actual(pagina), POR_PAGINA)
    filas = consultar(cuenta, f"{_sql_base(cuenta)} {donde} ORDER BY p.apellidos, p.nombres LIMIT %s OFFSET %s",
                      parametros + [pag["por_pagina"], pag["offset"]], id_usuario_app=usuario_app)
    return {"pacientes": filas, "paginacion": pag, "filtros": {"q": q or "", "estado": estado or ""}}


def obtener(cuenta, usuario_app, cedula):
    cedula = _cedula_ruta(cedula)
    fila = consultar(cuenta, f"{_sql_base(cuenta)} WHERE p.cedula_paciente = %s", (cedula,),
                     id_usuario_app=usuario_app, uno=True)
    if fila is None:
        raise ErrorNegocio("El paciente no existe.", 404)
    return fila


def ficha(cuenta, usuario_app, cedula):
    """Datos del paciente y sus ultimas 10 citas (consultas, imagenologia y laboratorio)."""
    paciente = obtener(cuenta, usuario_app, cedula)
    citas = consultar(cuenta, """
        SELECT id_cita, fecha_cita, hora_inicio, estado, 'Consulta' AS tipo, especialidad AS detalle
        FROM v_agenda_consultas WHERE cedula_paciente = %(c)s
        UNION ALL
        SELECT id_cita, fecha_cita, hora_inicio, estado, 'Imagenología', subtipo
        FROM v_agenda_imagenologia WHERE cedula_paciente = %(c)s
        UNION ALL
        SELECT id_cita, fecha_cita, hora_inicio, estado, 'Laboratorio', examen
        FROM v_agenda_laboratorio WHERE cedula_paciente = %(c)s
        ORDER BY fecha_cita DESC, hora_inicio DESC LIMIT 10""",
                      {"c": paciente["cedula_paciente"]}, id_usuario_app=usuario_app)
    return {"paciente": paciente, "citas": citas}


def _validar(datos):
    nacimiento = validators.no_futura(validators.fecha(datos.get("fecha_nacimiento"), "La fecha de nacimiento"),
                                      "La fecha de nacimiento")
    if nacimiento < date(1900, 1, 1):
        raise ErrorNegocio("La fecha de nacimiento no es válida.")
    return {
        "nombres": validators.nombre_persona(datos.get("nombres"), "Los nombres"),
        "apellidos": validators.nombre_persona(datos.get("apellidos"), "Los apellidos"),
        "fecha_nacimiento": nacimiento,
        "sexo": validators.opcion(datos.get("sexo"), SEXOS, "El sexo"),
        "telefono": validators.telefono(datos.get("telefono")),
        "correo": validators.correo(datos.get("correo"), obligatorio=False),
        "direccion": validators.texto(datos.get("direccion"), "La dirección", maximo=200, obligatorio=False),
    }


def crear(cuenta, usuario_app, datos):
    cedula = validators.cedula(datos.get("cedula_paciente"), "La cédula del paciente")
    v = _validar(datos)
    ejecutar(cuenta, """
        INSERT INTO paciente (cedula_paciente, nombres, apellidos, fecha_nacimiento, sexo, telefono, correo, direccion)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
             (cedula, v["nombres"], v["apellidos"], v["fecha_nacimiento"], v["sexo"], v["telefono"], v["correo"],
              v["direccion"]), id_usuario_app=usuario_app)
    log.info("Paciente creado: %s (cuenta %s, usuario %s)", cedula, cuenta, usuario_app)
    return cedula


def actualizar(cuenta, usuario_app, cedula, datos):
    """La cedula no se cambia. Si cambian los nombres, MySQL los actualiza tambien en su usuario (trigger)."""
    obtener(cuenta, usuario_app, cedula)
    v = _validar(datos)
    with transaccion(cuenta, usuario_app) as cursor:
        cursor.execute("""UPDATE paciente SET nombres = %s, apellidos = %s, fecha_nacimiento = %s, sexo = %s,
                                 telefono = %s, correo = %s, direccion = %s WHERE cedula_paciente = %s""",
                       (v["nombres"], v["apellidos"], v["fecha_nacimiento"], v["sexo"], v["telefono"], v["correo"],
                        v["direccion"], cedula))
    log.info("Paciente %s modificado (cuenta %s, usuario %s)", cedula, cuenta, usuario_app)


def cambiar_estado(cuenta, usuario_app, cedula, estado):
    """Administrador y recepcion. Al desactivar a un paciente, un trigger de la base desactiva tambien su usuario."""
    estado = validators.opcion(estado, ESTADOS, "El estado")
    obtener(cuenta, usuario_app, cedula)
    ejecutar(cuenta, "UPDATE paciente SET estado = %s WHERE cedula_paciente = %s", (estado, cedula),
             id_usuario_app=usuario_app)
    log.info("Paciente %s pasa a %s (cuenta %s, usuario %s)", cedula, estado, cuenta, usuario_app)


def eliminar(cuenta, usuario_app, cedula):
    """Administrador y recepcion, solo para corregir un registro hecho por error. Si el paciente ya tiene citas o
    usuario no se elimina: se desactiva (ademas, MySQL lo bloquea con las llaves foraneas)."""
    paciente = obtener(cuenta, usuario_app, cedula)
    if paciente.get("usuario"):                  # solo el administrador puede leer la tabla usuario
        raise ErrorNegocio("Tiene un usuario asociado. Desactívalo en lugar de eliminarlo.")
    citas = consultar(cuenta, "SELECT COUNT(*) AS total FROM cita WHERE cedula_paciente = %s",
                      (cedula,), id_usuario_app=usuario_app, uno=True)["total"]
    if citas:
        raise ErrorNegocio("Tiene citas registradas. Desactívalo en lugar de eliminarlo.")
    try:
        ejecutar(cuenta, "DELETE FROM paciente WHERE cedula_paciente = %s", (cedula,), id_usuario_app=usuario_app)
    except ErrorNegocio as error:
        if error.codigo == 400:
            raise ErrorNegocio("Tiene un usuario asociado. Desactívalo en lugar de eliminarlo.") from error
        raise
    log.info("Paciente %s eliminado (cuenta %s, usuario %s)", cedula, cuenta, usuario_app)
