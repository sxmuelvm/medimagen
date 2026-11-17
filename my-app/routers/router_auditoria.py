"""Rutas de auditoria (solo administrador): cambios de citas y accesos al sistema."""
from flask import Blueprint, request, session

from controllers import auditoria_controller as ctrl
from utils.constants import CUENTA_ADMINISTRADOR
from utils.decorators import roles_permitidos
from utils.helpers import render_pagina

bp = Blueprint("auditoria", __name__, url_prefix="/auditoria")
SOLO_ADMIN = roles_permitidos(CUENTA_ADMINISTRADOR)


@bp.get("/")
@SOLO_ADMIN
def lista():
    datos = ctrl.lista(session["id_usuario"], request.args.get("id_cita"), request.args.get("estado"),
                       request.args.get("cuenta_bd"), request.args.get("desde"), request.args.get("hasta"),
                       request.args.get("pagina"))
    return render_pagina("public/auditoria/lista.html", **datos)


@bp.get("/accesos")
@SOLO_ADMIN
def accesos():
    datos = ctrl.accesos(session["id_usuario"], request.args.get("q"), request.args.get("resultado"),
                         request.args.get("desde"), request.args.get("hasta"), request.args.get("pagina"))
    return render_pagina("public/auditoria/accesos.html", **datos)