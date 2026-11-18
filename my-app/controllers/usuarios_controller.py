"""Administracion de usuarios del sistema (solo administrador).

El administrador crea la cuenta con una clave temporal: la persona esta obligada a cambiarla en su primer ingreso.
Los usuarios no se eliminan (rol_administrador no tiene DELETE sobre usuario): se desactivan o se bloquean.
"""
import secrets

from conexion.conexionBD import consultar, ejecutar
from utils import validators
from utils.constants import CUENTA_ADMINISTRADOR, ROL_BD_A_CUENTA
from utils.errors import ErrorNegocio
from utils.helpers import pagina_actual, paginar, patron_like
from utils.logger import obtener_logger
from utils.security import hashear_clave

log = obtener_logger("usuarios")

CUENTA = CUENTA_ADMINISTRADOR
ESTADOS = ("activo", "inactivo", "bloqueado")
POR_PAGINA = 10

_SQL_USUARIO = """
    SELECT u.id_usuario, u.cedula, u.id_rol, r.nombre AS rol, u.id_medico, u.cedula_paciente, u.id_personal,
           u.nombres, u.apellidos, u.nombre_usuario, u.correo, u.estado, u.fecha_creacion, u.ultimo_acceso,
           u.intentos_fallidos, u.bloqueado_hasta, u.cambio_clave_obligatorio,
           (u.bloqueado_hasta IS NOT NULL AND u.bloqueado_hasta > NOW()) AS bloqueo_temporal
    FROM usuario u
    JOIN rol r ON r.id_rol = u.id_rol
    WHERE u.id_usuario = %s"""


def tipo_perfil(nombre_rol):
    """Tipo de perfil que exige cada rol (igual que sp_validar_perfil_usuario en MySQL)."""
    if nombre_rol == "medico":
        return "medico"
    if nombre_rol == "paciente":
        return "paciente"
    return "personal"


def generar_clave_temporal(largo=10):
    """Clave aleatoria sin caracteres confusos (0/O, 1/l/I). Siempre tiene letras y numeros."""
    letras = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ"
    numeros = "23456789"
    caracteres = [secrets.choice(numeros) for _ in range(3)] + [secrets.choice(letras) for _ in range(largo - 3)]
    secrets.SystemRandom().shuffle(caracteres)
    return "".join(caracteres)


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------
def listar(administrador, q=None, rol=None, estado=None, pagina=1):
    condiciones, parametros = [], []
    patron = patron_like(q)
    if patron:
        condiciones.append("(cedula LIKE %s OR nombres LIKE %s OR apellidos LIKE %s "
                           "OR nombre_usuario LIKE %s OR correo LIKE %s)")
        parametros += [patron] * 5
    if rol:
        condiciones.append("rol = %s")
        parametros.append(rol)
    if estado in ESTADOS:
        condiciones.append("estado = %s")
        parametros.append(estado)
    donde = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""

    total = consultar(CUENTA, f"SELECT COUNT(*) AS total FROM v_usuarios {donde}", parametros,
                      id_usuario_app=administrador, uno=True)["total"]
    pag = paginar(total, pagina_actual(pagina), POR_PAGINA)
    usuarios = consultar(CUENTA, f"""
        SELECT v.*, (v.bloqueado_hasta IS NOT NULL AND v.bloqueado_hasta > NOW()) AS bloqueo_temporal
        FROM v_usuarios v {donde}
        ORDER BY v.apellidos, v.nombres LIMIT %s OFFSET %s""",
                         parametros + [pag["por_pagina"], pag["offset"]], id_usuario_app=administrador)
    return {"usuarios": usuarios, "paginacion": pag, "roles": roles_todos(administrador),
            "filtros": {"q": q or "", "rol": rol or "", "estado": estado or ""}}


def roles_todos(administrador):
    return consultar(CUENTA, "SELECT id_rol, nombre FROM rol ORDER BY id_rol", id_usuario_app=administrador)


def roles_asignables(administrador, tipo=None):
    """Roles activos con acceso al sistema. Si se indica un tipo de perfil, solo los de ese tipo."""
    filas = consultar(CUENTA, "SELECT id_rol, nombre, descripcion FROM rol WHERE estado = 'activo' ORDER BY id_rol",
                      id_usuario_app=administrador)
    resultado = []
    for fila in filas:
        if fila["nombre"] not in ROL_BD_A_CUENTA:
            continue
        fila["tipo_perfil"] = tipo_perfil(fila["nombre"])
        if tipo is None or fila["tipo_perfil"] == tipo:
            resultado.append(fila)
    return resultado


def perfiles_disponibles(administrador):
    """Medicos, pacientes y personal activos que todavia no tienen usuario (para el formulario de creacion)."""
    medicos = consultar(CUENTA, """
        SELECT m.id_medico, m.cedula, m.nombres, m.apellidos, m.correo, e.nombre AS especialidad
        FROM medico m JOIN especialidad e ON e.id_especialidad = m.id_especialidad
        WHERE m.estado = 'activo' AND NOT EXISTS (SELECT 1 FROM usuario u WHERE u.id_medico = m.id_medico)
        ORDER BY m.apellidos, m.nombres""", id_usuario_app=administrador)
    pacientes = consultar(CUENTA, """
        SELECT p.cedula_paciente, p.nombres, p.apellidos, p.correo
        FROM paciente p
        WHERE p.estado = 'activo' AND NOT EXISTS (SELECT 1 FROM usuario u WHERE u.cedula_paciente = p.cedula_paciente)
        ORDER BY p.apellidos, p.nombres""", id_usuario_app=administrador)
    personal = consultar(CUENTA, """
        SELECT pe.id_personal, pe.cedula, pe.nombres, pe.apellidos, pe.correo, pe.cargo
        FROM personal pe
        WHERE pe.estado = 'activo' AND NOT EXISTS (SELECT 1 FROM usuario u WHERE u.id_personal = pe.id_personal)
        ORDER BY pe.apellidos, pe.nombres""", id_usuario_app=administrador)
    return {"medicos": medicos, "pacientes": pacientes, "personal": personal}


def opciones_crear(administrador):
    return {"roles": roles_asignables(administrador), **perfiles_disponibles(administrador)}


def obtener(id_usuario, administrador):
    fila = consultar(CUENTA, _SQL_USUARIO, (id_usuario,), id_usuario_app=administrador, uno=True)
    if fila is None:
        raise ErrorNegocio("El usuario no existe.", 404)
    fila["tipo_perfil"] = tipo_perfil(fila["rol"])
    return fila


def detalle(id_usuario, administrador):
    """Datos del usuario, roles a los que se lo puede cambiar y sus ultimos accesos."""
    usuario = obtener(id_usuario, administrador)
    return {"usuario": usuario,
            "roles": roles_asignables(administrador, usuario["tipo_perfil"]),
            "accesos": accesos_recientes(id_usuario, administrador)}


def accesos_recientes(id_usuario, administrador, limite=10):
    return consultar(CUENTA, """
        SELECT fecha, resultado, ip, navegador FROM auditoria_acceso
        WHERE id_usuario = %s ORDER BY fecha DESC, id_acceso DESC LIMIT %s""",
                     (id_usuario, limite), id_usuario_app=administrador)


# ---------------------------------------------------------------------------
# Crear
# ---------------------------------------------------------------------------
def _buscar_perfil(tipo, valor, administrador):
    """Busca el medico, paciente o miembro del personal elegido y comprueba que este libre y activo."""
    if tipo == "medico":
        clave = validators.entero(valor, "El médico", minimo=1)
        perfil = consultar(CUENTA, "SELECT cedula, nombres, apellidos, correo, estado FROM medico WHERE id_medico = %s",
                           (clave,), id_usuario_app=administrador, uno=True)
        ocupado = consultar(CUENTA, "SELECT id_usuario FROM usuario WHERE id_medico = %s", (clave,),
                            id_usuario_app=administrador, uno=True)
        etiqueta = "médico"
    elif tipo == "paciente":
        clave = validators.cedula(valor, "La cédula del paciente")
        perfil = consultar(CUENTA, """SELECT cedula_paciente AS cedula, nombres, apellidos, correo, estado
                                      FROM paciente WHERE cedula_paciente = %s""",
                           (clave,), id_usuario_app=administrador, uno=True)
        ocupado = consultar(CUENTA, "SELECT id_usuario FROM usuario WHERE cedula_paciente = %s", (clave,),
                            id_usuario_app=administrador, uno=True)
        etiqueta = "paciente"
    else:
        clave = validators.entero(valor, "El miembro del personal", minimo=1)
        perfil = consultar(CUENTA, "SELECT cedula, nombres, apellidos, correo, estado FROM personal WHERE id_personal = %s",
                           (clave,), id_usuario_app=administrador, uno=True)
        ocupado = consultar(CUENTA, "SELECT id_usuario FROM usuario WHERE id_personal = %s", (clave,),
                            id_usuario_app=administrador, uno=True)
        etiqueta = "miembro del personal"

    if perfil is None:
        raise ErrorNegocio(f"El {etiqueta} seleccionado no existe.")
    if perfil["estado"] != "activo":
        raise ErrorNegocio(f"El {etiqueta} seleccionado está inactivo.")
    if ocupado is not None:
        raise ErrorNegocio(f"Ese {etiqueta} ya tiene un usuario.")
    perfil["clave"] = clave
    return perfil


def _clave_inicial(clave, cedula):
    """Si no se escribio ninguna clave se genera una temporal. Devuelve (clave, fue_generada)."""
    if not clave:
        return generar_clave_temporal(), True
    return validators.clave_segura(clave, cedula), False


def crear(datos, administrador):
    """Crea el usuario. Devuelve {'id_usuario', 'nombre_usuario', 'clave_temporal'} (la clave solo si se genero)."""
    id_rol = validators.entero(datos.get("id_rol"), "El rol", minimo=1)
    rol = consultar(CUENTA, "SELECT id_rol, nombre, estado FROM rol WHERE id_rol = %s", (id_rol,),
                    id_usuario_app=administrador, uno=True)
    if rol is None or rol["estado"] != "activo":
        raise ErrorNegocio("El rol seleccionado no existe o está inactivo.")
    if rol["nombre"] not in ROL_BD_A_CUENTA:
        raise ErrorNegocio("Ese rol no tiene acceso al sistema.")

    tipo = tipo_perfil(rol["nombre"])
    perfil = _buscar_perfil(tipo, datos.get("id_perfil"), administrador)
    nombre_usuario = validators.nombre_usuario(datos.get("nombre_usuario"))
    correo = validators.correo(datos.get("correo"), obligatorio=False) or perfil["correo"]
    if not correo:
        raise ErrorNegocio("El correo es obligatorio: el perfil elegido no tiene uno registrado.")
    clave, generada = _clave_inicial(datos.get("clave"), perfil["cedula"])

    resultado = ejecutar(CUENTA, """
        INSERT INTO usuario (cedula, id_rol, id_medico, cedula_paciente, id_personal, nombres, apellidos,
                             nombre_usuario, correo, password_hash, cambio_clave_obligatorio)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1)""",
                         (perfil["cedula"], id_rol,
                          perfil["clave"] if tipo == "medico" else None,
                          perfil["clave"] if tipo == "paciente" else None,
                          perfil["clave"] if tipo == "personal" else None,
                          perfil["nombres"], perfil["apellidos"], nombre_usuario, correo, hashear_clave(clave)),
                         id_usuario_app=administrador)
    log.info("Usuario creado: %s (%s) por el usuario %s", nombre_usuario, rol["nombre"], administrador)
    return {"id_usuario": resultado["id"], "nombre_usuario": nombre_usuario,
            "clave_temporal": clave if generada else None}


# ---------------------------------------------------------------------------
# Modificar
# ---------------------------------------------------------------------------
def actualizar(id_usuario, datos, administrador):
    """Cambia nombre de usuario, correo y rol (solo a otro rol del mismo tipo de perfil)."""
    actual = obtener(id_usuario, administrador)
    nombre_usuario = validators.nombre_usuario(datos.get("nombre_usuario"))
    correo = validators.correo(datos.get("correo"))
    id_rol = validators.entero(datos.get("id_rol", actual["id_rol"]), "El rol", minimo=1)

    if id_rol != actual["id_rol"]:
        if id_usuario == administrador:
            raise ErrorNegocio("No puedes cambiar tu propio rol.")
        permitidos = {r["id_rol"] for r in roles_asignables(administrador, actual["tipo_perfil"])}
        if id_rol not in permitidos:
            raise ErrorNegocio("Ese rol no es compatible con el perfil de este usuario.")

    ejecutar(CUENTA, "UPDATE usuario SET nombre_usuario = %s, correo = %s, id_rol = %s WHERE id_usuario = %s",
             (nombre_usuario, correo, id_rol, id_usuario), id_usuario_app=administrador)
    log.info("Usuario %s modificado por el usuario %s", id_usuario, administrador)


def _estado_perfil(id_usuario, administrador):
    fila = consultar(CUENTA, """
        SELECT CASE WHEN u.id_medico IS NOT NULL THEN m.estado
                    WHEN u.cedula_paciente IS NOT NULL THEN p.estado
                    ELSE pe.estado END AS estado_perfil
        FROM usuario u
        LEFT JOIN medico m ON m.id_medico = u.id_medico
        LEFT JOIN paciente p ON p.cedula_paciente = u.cedula_paciente
        LEFT JOIN personal pe ON pe.id_personal = u.id_personal
        WHERE u.id_usuario = %s""", (id_usuario,), id_usuario_app=administrador, uno=True)
    return fila["estado_perfil"] if fila else None


def cambiar_estado(id_usuario, estado, administrador):
    """Activa, desactiva o bloquea. Al activar tambien se limpian los intentos fallidos y el bloqueo temporal."""
    estado = validators.opcion(estado, ESTADOS, "El estado")
    obtener(id_usuario, administrador)
    if id_usuario == administrador and estado != "activo":
        raise ErrorNegocio("No puedes desactivar ni bloquear tu propia cuenta.")

    if estado == "activo":
        if _estado_perfil(id_usuario, administrador) != "activo":
            raise ErrorNegocio("El perfil asociado (médico, paciente o personal) está inactivo. Actívalo primero.")
        ejecutar(CUENTA, """UPDATE usuario SET estado = 'activo', intentos_fallidos = 0, bloqueado_hasta = NULL
                            WHERE id_usuario = %s""", (id_usuario,), id_usuario_app=administrador)
    else:
        ejecutar(CUENTA, "UPDATE usuario SET estado = %s WHERE id_usuario = %s", (estado, id_usuario),
                 id_usuario_app=administrador)
    log.info("Usuario %s pasa a %s (por el usuario %s)", id_usuario, estado, administrador)


def desbloquear(id_usuario, administrador):
    """Quita el bloqueo temporal por intentos fallidos."""
    obtener(id_usuario, administrador)
    ejecutar(CUENTA, "UPDATE usuario SET intentos_fallidos = 0, bloqueado_hasta = NULL WHERE id_usuario = %s",
             (id_usuario,), id_usuario_app=administrador)
    log.info("Usuario %s desbloqueado por el usuario %s", id_usuario, administrador)


def restablecer_clave(id_usuario, datos, administrador):
    """Pone una clave nueva (la escribe el administrador o se genera) y obliga a cambiarla al entrar."""
    usuario = obtener(id_usuario, administrador)
    if id_usuario == administrador:
        raise ErrorNegocio("Para cambiar tu propia contraseña usa la opción de tu perfil.")
    clave, generada = _clave_inicial(datos.get("clave"), usuario["cedula"])
    ejecutar(CUENTA, """
        UPDATE usuario SET password_hash = %s, cambio_clave_obligatorio = 1, intentos_fallidos = 0,
                           bloqueado_hasta = NULL
        WHERE id_usuario = %s""", (hashear_clave(clave), id_usuario), id_usuario_app=administrador)
    log.info("Clave restablecida: usuario %s (por el usuario %s)", id_usuario, administrador)
    return {"usuario": usuario, "clave_temporal": clave if generada else None}

def eliminar(id_usuario, administrador):
    """Elimina un usuario que nunca se uso (sin citas, resultados ni accesos registrados).
    Si ya tiene actividad, MySQL lo impide con las llaves foraneas y se ofrece desactivarlo."""
    obtener(id_usuario, administrador)
    if id_usuario == administrador:
        raise ErrorNegocio("No puedes eliminar tu propia cuenta.")
    try:
        ejecutar(CUENTA, "DELETE FROM usuario WHERE id_usuario = %s", (id_usuario,), id_usuario_app=administrador)
    except ErrorNegocio as error:
        if error.codigo == 400:
            raise ErrorNegocio("Este usuario ya tiene actividad registrada (accesos, citas o resultados) y no se "
                               "puede eliminar. Desactívalo en su lugar.") from error
        raise
    log.info("Usuario %s eliminado por el usuario %s", id_usuario, administrador)