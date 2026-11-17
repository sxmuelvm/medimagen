"""Seguridad de la aplicacion: hash de claves, cabeceras HTTP y validacion de la sesion en cada peticion."""
from functools import lru_cache

from flask import redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from utils.logger import obtener_logger

log = obtener_logger("seguridad")

METODO_HASH = "pbkdf2:sha256"    # el mismo de los usuarios de prueba (03_datos.sql)

# Rutas que puede usar alguien que debe cambiar su clave antes de seguir
_PERMITIDAS_CAMBIO_CLAVE = {"perfil.cambiar_clave", "auth.logout", "static", "salud.salud"}
# Rutas que no necesitan validar la sesion contra la base
_SIN_VALIDACION = {"static", "salud.salud"}


def hashear_clave(clave):
    return generate_password_hash(clave, method=METODO_HASH)


def clave_correcta(hash_guardado, clave):
    try:
        return check_password_hash(hash_guardado, clave)
    except (ValueError, TypeError):
        return False


@lru_cache(maxsize=1)
def hash_falso():
    """Hash de relleno: se compara cuando la cedula no existe, para que tarde lo mismo que una real."""
    return hashear_clave("clave-que-nadie-usa-1")


_CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "font-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'")


def registrar_seguridad(app):
    @app.before_request
    def _validar_sesion():
        if not session.get("id_usuario") or request.endpoint is None or request.endpoint in _SIN_VALIDACION:
            return None

        # Import tardio: evita una importacion circular al arrancar
        from controllers import auth_controller

        if not auth_controller.sesion_vigente(session["id_usuario"], session.get("id_rol")):
            log.warning("Sesion invalidada: usuario %s inactivo o con rol cambiado", session.get("id_usuario"))
            session.clear()
            return redirect(url_for("auth.login"))

        if session.get("cambio_clave") and request.endpoint not in _PERMITIDAS_CAMBIO_CLAVE:
            return redirect(url_for("perfil.cambiar_clave"))
        return None

    @app.after_request
    def _cabeceras(respuesta):
        respuesta.headers["Content-Security-Policy"] = _CSP
        respuesta.headers["X-Content-Type-Options"] = "nosniff"
        respuesta.headers["X-Frame-Options"] = "DENY"
        respuesta.headers["Referrer-Policy"] = "same-origin"
        respuesta.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        respuesta.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        if request.is_secure:
            respuesta.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        if request.endpoint != "static" and (session.get("id_usuario") or request.endpoint == "auth.login"):
            respuesta.headers["Cache-Control"] = "no-store"
            respuesta.headers["Pragma"] = "no-cache"
        return respuesta