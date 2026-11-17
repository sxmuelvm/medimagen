"""Cambio de contrasena de la persona que tiene la sesion abierta (usa la cuenta usr_login)."""
from conexion.conexionBD import consultar, ejecutar
from utils import validators
from utils.errors import ErrorNegocio
from utils.logger import obtener_logger
from utils.security import clave_correcta, hashear_clave

log = obtener_logger("perfil")


def cambiar_clave(id_usuario, cedula, clave_actual, clave_nueva, confirmacion):
    if not clave_actual:
        raise ErrorNegocio("Escribe tu contraseña actual.")
    if clave_nueva != confirmacion:
        raise ErrorNegocio("La confirmación no coincide con la nueva contraseña.")
    validators.clave_segura(clave_nueva, cedula)

    fila = consultar("login", "SELECT password_hash FROM usuario WHERE id_usuario = %s", (id_usuario,), uno=True)
    if fila is None or not clave_correcta(fila["password_hash"], clave_actual):
        log.warning("Cambio de clave rechazado: contrasena actual incorrecta (usuario %s)", id_usuario)
        raise ErrorNegocio("La contraseña actual no es correcta.")
    if clave_correcta(fila["password_hash"], clave_nueva):
        raise ErrorNegocio("La nueva contraseña debe ser distinta de la actual.")

    ejecutar("login",
             "UPDATE usuario SET password_hash = %s, cambio_clave_obligatorio = 0 WHERE id_usuario = %s",
             (hashear_clave(clave_nueva), id_usuario))
    log.info("Contrasena cambiada: usuario %s", id_usuario)