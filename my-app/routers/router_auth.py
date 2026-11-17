"""Rutas de inicio y cierre de sesion."""
from flask import Blueprint, flash, redirect, request, session, url_for

from config import Config
from controllers import auth_controller
from extensions import limiter
from utils.decorators import login_requerido
from utils.errors import ErrorAutenticacion
from utils.helpers import ip_cliente, navegador, render_pagina

bp = Blueprint("auth", __name__)


@bp.get("/")
def raiz():
    destino = "dashboard.inicio" if session.get("id_usuario") else "auth.login"
    return redirect(url_for(destino))


# Solo cuentan para el limite los intentos fallidos (respuesta 401)
@bp.route("/login", methods=["GET", "POST"])
@limiter.limit(Config.LIMITE_LOGIN, methods=["POST"], deduct_when=lambda respuesta: respuesta.status_code == 401)
def login():
    if session.get("id_usuario"):
        return redirect(url_for("dashboard.inicio"))

    cedula = ""
    if request.method == "POST":
        cedula = request.form.get("cedula", "").strip()
        clave = request.form.get("clave", "")
        try:
            datos = auth_controller.iniciar_sesion(cedula, clave, ip_cliente(), navegador())
        except ErrorAutenticacion as error:
            flash(error.mensaje, "error")
            return render_pagina("public/auth/login.html", cedula=cedula), 401

        session.clear()                       # sesion nueva: evita la fijacion de sesion
        session.update(datos)
        session.permanent = True
        flash(f"Bienvenido(a), {datos['nombres']}.", "exito")
        if datos["cambio_clave"]:
            flash("Debes cambiar tu contraseña antes de continuar.", "aviso")
            return redirect(url_for("perfil.cambiar_clave"))
        return redirect(url_for("dashboard.inicio"))

    return render_pagina("public/auth/login.html", cedula=cedula)


@bp.post("/logout")
@login_requerido
def logout():
    auth_controller.registrar_cierre_sesion(session["id_usuario"], session.get("cedula"), ip_cliente(), navegador())
    session.clear()
    flash("Cerraste sesión correctamente.", "exito")
    return redirect(url_for("auth.login"))