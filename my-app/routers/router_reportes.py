"""Rutas de reportes (solo administrador)."""
from flask import Blueprint, flash, request, session

from controllers import reportes_controller as ctrl
from utils.constants import CUENTA_ADMINISTRADOR
from utils.decorators import roles_permitidos
from utils.errors import ErrorNegocio
from utils.helpers import render_pagina

bp = Blueprint("reportes", __name__, url_prefix="/reportes")
SOLO_ADMIN = roles_permitidos(CUENTA_ADMINISTRADOR)


@bp.get("/ingresos")
@SOLO_ADMIN
def ingresos():
    usuario = session["id_usuario"]
    try:
        datos = ctrl.ingresos(usuario, request.args.get("desde"), request.args.get("hasta"), request.args.get("area"))
        estado = 200
    except ErrorNegocio as error:
        if error.codigo != 400:
            raise
        flash(error.mensaje, "error")
        datos, estado = ctrl.ingresos(usuario), 400       # se muestra el reporte completo junto al aviso
    return render_pagina("public/reportes/ingresos.html", **datos), estado