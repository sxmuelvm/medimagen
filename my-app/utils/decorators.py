"""Decoradores de acceso para las rutas."""
from functools import wraps

from flask import abort, flash, redirect, session, url_for

from utils.logger import obtener_logger

log = obtener_logger("acceso")


def login_requerido(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if not session.get("id_usuario"):
            flash("Inicia sesión para continuar.", "aviso")
            return redirect(url_for("auth.login"))
        return vista(*args, **kwargs)
    return envoltura


def roles_permitidos(*cuentas):
    """Solo deja pasar a las cuentas indicadas, por ejemplo @roles_permitidos('administrador', 'recepcion')."""
    def decorador(vista):
        @wraps(vista)
        def envoltura(*args, **kwargs):
            if session.get("cuenta") not in cuentas:
                log.warning("Acceso denegado: usuario %s (%s) a %s", session.get("id_usuario"),
                            session.get("cuenta"), vista.__name__)
                abort(403)
            return vista(*args, **kwargs)
        return login_requerido(envoltura)
    return decorador