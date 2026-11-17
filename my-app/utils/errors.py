"""Errores del sistema: excepciones propias, traduccion de errores de MySQL y paginas de error."""
import re

from flask import jsonify, request
from flask_wtf.csrf import CSRFError

from utils.helpers import render_pagina
from utils.logger import obtener_logger

log = obtener_logger("errores")


class ErrorNegocio(Exception):
    """Error que se le puede mostrar al usuario tal cual (mensaje en espanol, sin detalles tecnicos)."""

    def __init__(self, mensaje, codigo=400):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


class ErrorAutenticacion(ErrorNegocio):
    def __init__(self, mensaje):
        super().__init__(mensaje, 401)


_DUPLICADOS = {
    "cita.uq_cita_paciente_horario": "El paciente ya tiene una cita en ese horario.",
    "cita.uq_cita_recurso_horario": "Ese consultorio, equipo o puesto ya está ocupado en ese horario.",
    "usuario.cedula": "Ya existe un usuario con esa cédula.",
    "usuario.nombre_usuario": "Ese nombre de usuario ya está en uso.",
    "usuario.correo": "Ese correo ya está registrado en otro usuario.",
    "usuario.id_medico": "Ese médico ya tiene un usuario.",
    "usuario.id_personal": "Ese miembro del personal ya tiene un usuario.",
    "usuario.cedula_paciente": "Ese paciente ya tiene un usuario.",
    "paciente.PRIMARY": "Ya existe un paciente con esa cédula.",
    "paciente.correo": "Ese correo ya está registrado en otro paciente.",
    "medico.cedula": "Ya existe un médico con esa cédula.",
    "medico.correo": "Ese correo ya está registrado en otro médico.",
    "personal.cedula": "Ya existe un miembro del personal con esa cédula.",
    "personal.correo": "Ese correo ya está registrado en otro miembro del personal.",
    "especialidad.nombre": "Ya existe una especialidad con ese nombre.",
    "rol.nombre": "Ya existe un rol con ese nombre.",
    "area.nombre": "Ya existe un área con ese nombre.",
    "recurso_atencion.uq_recurso_nombre": "Ya existe un recurso con ese nombre en el área.",
    "tipo_procedimiento.nombre": "Ya existe un tipo con ese nombre.",
    "subtipo_examen.uq_subtipo": "Ya existe un examen con ese nombre en el tipo.",
    "medicamento.uq_medicamento": "Ese medicamento ya está registrado.",
}

_CHECKS = {
    "chk_cita_dia": "Las citas solo se agendan de lunes a viernes.",
    "chk_cita_costo": "El costo no puede ser negativo.",
    "chk_esp_costo": "El costo no puede ser negativo.",
    "chk_subtipo_costo": "El costo no puede ser negativo.",
    "chk_usuario_perfil": "El usuario debe estar asociado a un solo perfil (médico, paciente o personal).",
}

_PERMISO = {1044, 1142, 1143, 1370, 1227}
_CONEXION = {2002, 2003, 2006, 2013, 1045, 1040, 1203}


def traducir_error_mysql(error):
    """Convierte un error de mysql.connector en un mensaje seguro para el usuario."""
    numero = getattr(error, "errno", None)
    texto = getattr(error, "msg", "") or str(error)

    if numero == 1644:      # SIGNAL de nuestros triggers: ya vienen en espanol y son seguros
        return texto
    if numero == 1062:
        llave = re.search(r"for key '([^']+)'", texto)
        return _DUPLICADOS.get(llave.group(1) if llave else "", "Ya existe un registro con esos datos.")
    if numero == 3819:
        nombre = re.search(r"Check constraint '([^']+)'", texto)
        nombre = nombre.group(1) if nombre else ""
        if nombre in _CHECKS:
            return _CHECKS[nombre]
        if nombre.endswith("cedula"):
            return "La cédula debe tener exactamente 10 dígitos."
        return "Un dato no cumple las reglas del sistema."
    if numero == 1451:
        return "No se puede eliminar o cambiar este registro porque tiene información relacionada."
    if numero == 1452:
        return "Uno de los datos relacionados no existe."
    if numero == 1048:
        return "Falta un dato obligatorio."
    if numero == 1406:
        return "Un dato es demasiado largo."
    if numero in (1264, 1292, 1366, 1265):
        return "Un dato tiene un formato o valor no válido."
    if numero in (1205, 1213):
        return "El sistema está ocupado. Intenta nuevamente."
    if numero in _PERMISO:
        log.warning("Permiso denegado por MySQL (%s): %s", numero, texto)
        return "No tienes permiso para realizar esta acción."
    if numero in _CONEXION:
        log.error("Fallo de conexion con MySQL (%s): %s", numero, texto)
        return "No se pudo conectar con la base de datos. Intenta más tarde."
    if error.__class__.__name__ == "PoolError":
        log.error("Pool de conexiones agotado: %s", texto)
        return "El sistema está ocupado. Intenta nuevamente en unos segundos."

    log.error("Error de MySQL no clasificado (%s): %s", numero, texto)
    return "No se pudo completar la operación."


# ---------------------------------------------------------------------------
# Paginas de error
# ---------------------------------------------------------------------------
_PLANTILLA = {400: 400, 403: 403, 404: 404, 405: 400, 413: 400, 429: 429, 500: 500, 503: 500}
_MENSAJES = {
    400: "La solicitud no es válida.",
    403: "No tienes permiso para ver esta página.",
    404: "La página que buscas no existe.",
    405: "Acción no permitida.",
    413: "El envío es demasiado grande.",
    429: "Demasiados intentos. Espera un momento e inténtalo de nuevo.",
    500: "Ocurrió un error inesperado. Ya fue registrado.",
    503: "El servicio no está disponible por ahora.",
}


def _quiere_json():
    return (request.is_json or request.headers.get("X-Requested-With") == "fetch"
            or request.accept_mimetypes.best == "application/json")


def _responder(codigo, mensaje=None):
    mensaje = mensaje or _MENSAJES.get(codigo, _MENSAJES[500])
    if _quiere_json():
        return jsonify({"error": mensaje}), codigo
    pagina = render_pagina(f"errors/{_PLANTILLA.get(codigo, 500)}.html", codigo=codigo, mensaje=mensaje)
    return pagina, codigo


def registrar_manejadores_errores(app):
    @app.errorhandler(CSRFError)
    def _csrf(error):
        log.warning("CSRF rechazado en %s: %s", request.path, error.description)
        return _responder(400, "El formulario expiró o no es válido. Recarga la página e inténtalo de nuevo.")

    @app.errorhandler(ErrorNegocio)
    def _negocio(error):
        return _responder(error.codigo, error.mensaje)

    for codigo in (400, 403, 404, 405, 413, 429):
        app.register_error_handler(codigo, lambda error, c=codigo: _responder(c))

    @app.errorhandler(500)
    def _interno(error):
        log.error("Error 500 en %s", request.path, exc_info=getattr(error, "original_exception", None))
        return _responder(500)



def resultado_accion(funcion, mensaje_ok, destino):
    """Ejecuta una accion (cambiar estado, eliminar...) y vuelve a `destino` con un mensaje de exito o de error."""
    from flask import flash, redirect

    try:
        funcion()
        flash(mensaje_ok, "exito")
    except ErrorNegocio as error:
        if error.codigo != 400:
            raise
        flash(error.mensaje, "error")
    return redirect(destino)