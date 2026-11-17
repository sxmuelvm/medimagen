"""Perfil de la persona con sesion abierta y cambio de contrasena."""
from flask import Blueprint, flash, redirect, request, session, url_for

from config import Config
from controllers import perfil_controller
from extensions import limiter
from utils.decorators import login_requerido
from utils.errors import ErrorNegocio
from utils.helpers import render_pagina

bp = Blueprint("perfil", __name__, url_prefix="/perfil")


@bp.get("/")
@login_requerido
def mi_perfil():
    return render_pagina("public/perfil/mi_perfil.html")


# Solo cuentan para el limite los intentos rechazados (respuesta 400)
@bp.route("/clave", methods=["GET", "POST"])
@limiter.limit(Config.LIMITE_CLAVE, methods=["POST"], deduct_when=lambda respuesta: respuesta.status_code == 400)
@login_requerido
def cambiar_clave():
    if request.method == "POST":
        try:
            perfil_controller.cambiar_clave(
                session["id_usuario"], session.get("cedula"),
                request.form.get("clave_actual", ""),
                request.form.get("clave_nueva", ""),
                request.form.get("clave_confirmacion", ""))
        except ErrorNegocio as error:
            flash(error.mensaje, "error")
            return render_pagina("public/perfil/cambiar_clave.html"), 400

        session["cambio_clave"] = False
        flash("Tu contraseña se cambió correctamente.", "exito")
        return redirect(url_for("dashboard.inicio"))

    return render_pagina("public/perfil/cambiar_clave.html")