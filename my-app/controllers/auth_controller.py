"""Inicio y cierre de sesion. Todo se hace con la cuenta usr_login, que solo ve lo necesario para autenticar."""
import re

from config import Config
from conexion.conexionBD import consultar, transaccion
from utils.constants import CUENTA_MEDICO, CUENTA_PACIENTE, ROL_BD_A_CUENTA
from utils.errors import ErrorAutenticacion, ErrorNegocio
from utils.logger import obtener_logger
from utils.security import clave_correcta, hash_falso

log = obtener_logger("auth")

_USUARIO = re.compile(r"[A-Za-z0-9._\-]{4,50}")

_SQL_USUARIO = """
    SELECT u.id_usuario, u.id_rol, r.nombre AS rol, r.estado AS rol_estado,
           u.cedula, (SELECT m.id_medico FROM medico m WHERE m.cedula = u.cedula) AS id_medico,
           u.nombres, u.apellidos, u.nombre_usuario,
           u.password, u.estado, u.cambio_clave_obligatorio,
           (u.bloqueado_hasta IS NOT NULL AND u.bloqueado_hasta > NOW()) AS bloqueado_activo
    FROM usuario u
    JOIN rol r ON r.id_rol = u.id_rol
    WHERE u.nombre_usuario = %s"""

# Un solo UPDATE atomico. MySQL evalua las asignaciones de izquierda a derecha:
# la segunda ya ve el valor nuevo de intentos_fallidos.
# Si un bloqueo ya vencio, el conteo vuelve a empezar en 1.
_SQL_FALLO = """
    UPDATE usuario
    SET intentos_fallidos = IF(bloqueado_hasta IS NOT NULL AND bloqueado_hasta <= NOW(), 1, intentos_fallidos + 1),
        bloqueado_hasta = IF(intentos_fallidos >= %s, DATE_ADD(NOW(), INTERVAL %s MINUTE),
                             IF(bloqueado_hasta <= NOW(), NULL, bloqueado_hasta))
    WHERE id_usuario = %s"""

_SQL_EXITO = """
    UPDATE usuario
    SET intentos_fallidos = 0, bloqueado_hasta = NULL, ultimo_acceso = NOW()
    WHERE id_usuario = %s"""


def _mensaje_generico():
    # El mismo texto para usuario inexistente, clave incorrecta y cuenta bloqueada temporalmente
    return (f"Usuario o contraseña incorrectos. Tras {Config.MAX_INTENTOS} intentos fallidos "
            f"la cuenta se bloquea {Config.MINUTOS_BLOQUEO} minutos.")


def _limpiar_intento(valor):
    return "".join(c for c in str(valor or "") if c.isprintable())[:50]


def _registrar_acceso(usuario_intento, id_usuario, resultado, ip, navegador):
    """El documento no define una tabla de accesos: cada intento queda en el registro de la aplicacion (logs/)."""
    log.info("Acceso %s: usuario %r (id %s) desde %s", resultado, _limpiar_intento(usuario_intento), id_usuario, ip)


def iniciar_sesion(nombre_usuario, clave, ip, navegador):
    """Valida nombre de usuario y contrasena. Devuelve los datos de la sesion o lanza ErrorAutenticacion."""
    cedula = (nombre_usuario or "").strip()      # lo escrito en el login
    clave = clave or ""

    if not _USUARIO.fullmatch(cedula) or not clave or len(clave) > 128:
        clave_correcta(hash_falso(), clave or "x")
        _registrar_acceso(cedula, None, "fallido", ip, navegador)
        raise ErrorAutenticacion(_mensaje_generico())

    usuario = consultar("login", _SQL_USUARIO, (cedula,), uno=True)

    if usuario is None:
        clave_correcta(hash_falso(), clave)          # mismo tiempo de respuesta que un usuario real
        _registrar_acceso(cedula, None, "fallido", ip, navegador)
        log.warning("Intento de acceso con usuario inexistente desde %s", ip)
        raise ErrorAutenticacion(_mensaje_generico())

    if usuario["bloqueado_activo"]:
        _registrar_acceso(cedula, usuario["id_usuario"], "bloqueado", ip, navegador)
        log.warning("Intento sobre cuenta bloqueada: usuario %s desde %s", usuario["id_usuario"], ip)
        raise ErrorAutenticacion(_mensaje_generico())

    if not clave_correcta(usuario["password"], clave):
        _registrar_fallo(usuario["id_usuario"], cedula, ip, navegador)
        raise ErrorAutenticacion(_mensaje_generico())

    # A partir de aqui la contrasena es correcta: ya se puede decir por que no entra
    if usuario["estado"] != "activo":
        _registrar_acceso(cedula, usuario["id_usuario"], "bloqueado", ip, navegador)
        raise ErrorAutenticacion("Tu cuenta está inactiva o bloqueada. Comunícate con el administrador.")

    cuenta = ROL_BD_A_CUENTA.get(usuario["rol"])
    if cuenta is None or usuario["rol_estado"] != "activo":
        _registrar_acceso(cedula, usuario["id_usuario"], "bloqueado", ip, navegador)
        log.warning("Rol sin acceso: usuario %s, rol %r", usuario["id_usuario"], usuario["rol"])
        raise ErrorAutenticacion("Tu rol no tiene acceso al sistema. Comunícate con el administrador.")

    with transaccion("login") as cursor:
        cursor.execute(_SQL_EXITO, (usuario["id_usuario"],))

    log.info("Inicio de sesion: usuario %s (%s) desde %s", usuario["id_usuario"], cuenta, ip)
    return {
        "id_usuario": usuario["id_usuario"],
        "nombres": usuario["nombres"],
        "apellidos": usuario["apellidos"],
        "nombre_usuario": usuario["nombre_usuario"],
        "id_rol": usuario["id_rol"],
        "rol": usuario["rol"],
        "cuenta": cuenta,
        "id_medico": usuario["id_medico"] if cuenta == CUENTA_MEDICO else None,
        "cedula": usuario["cedula"],
        "cedula_paciente": usuario["cedula"] if cuenta == CUENTA_PACIENTE else None,
        "cambio_clave": bool(usuario["cambio_clave_obligatorio"]),
    }


def _registrar_fallo(id_usuario, cedula, ip, navegador):
    try:
        with transaccion("login") as cursor:
            cursor.execute(_SQL_FALLO, (Config.MAX_INTENTOS, Config.MINUTOS_BLOQUEO, id_usuario))
            cursor.execute("SELECT (bloqueado_hasta IS NOT NULL AND bloqueado_hasta > NOW()) AS bloqueado "
                           "FROM usuario WHERE id_usuario = %s", (id_usuario,))
            fila = cursor.fetchone()
        if fila and fila["bloqueado"]:
            log.warning("Cuenta bloqueada %s minutos: usuario %s desde %s", Config.MINUTOS_BLOQUEO, id_usuario, ip)
    except ErrorNegocio:
        log.error("No se pudo registrar el intento fallido del usuario %s", id_usuario)


def registrar_cierre_sesion(id_usuario, nombre_usuario, ip, navegador):
    _registrar_acceso(nombre_usuario, id_usuario, "cierre_sesion", ip, navegador)
    log.info("Cierre de sesion: usuario %s", id_usuario)


def sesion_vigente(id_usuario, id_rol):
    """False si el usuario o su rol ya no estan activos, o si le cambiaron el rol con la sesion abierta."""
    fila = consultar("login", """
        SELECT u.estado, u.id_rol, r.estado AS rol_estado
        FROM usuario u JOIN rol r ON r.id_rol = u.id_rol
        WHERE u.id_usuario = %s""", (id_usuario,), uno=True)
    return bool(fila and fila["estado"] == "activo" and fila["id_rol"] == id_rol
                and fila["rol_estado"] == "activo")
