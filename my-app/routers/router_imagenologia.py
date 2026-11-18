"""Rutas del personal de imagenologia."""
from flask import Blueprint, flash, redirect, session, request, url_for

from controllers import imagenologia_controller as ctrl
from utils.constants import CUENTA_IMAGENOLOGIA
from utils.decorators import roles_permitidos
from utils.errors import resultado_accion
from utils.helpers import render_pagina

bp = Blueprint("imagenologia", __name__, url_prefix="/imagenologia")
SOLO_IMAGENOLOGIA = roles_permitidos(CUENTA_IMAGENOLOGIA)


@bp.get("/")
@SOLO_IMAGENOLOGIA
def agenda():
    datos = ctrl.agenda(session["id_usuario"], request.args.get("q"), request.args.get("estado"),
                        request.args.get("desde"), request.args.get("hasta"), request.args.get("pagina"))
    return render_pagina("public/imagenologia/agenda.html", **datos)


@bp.get("/<int:id_cita>/realizar")
@SOLO_IMAGENOLOGIA
def registrar_realizacion(id_cita):
    """Pantalla de confirmacion con los datos del examen."""
    examen = ctrl.obtener(session["id_usuario"], id_cita)
    if not examen["puede_registrar"]:
        flash("Este examen no se puede registrar como realizado ahora.", "aviso")
        return redirect(url_for("imagenologia.agenda"))
    return render_pagina("public/imagenologia/registrar_realizacion.html", examen=examen)


@bp.post("/<int:id_cita>/realizar")
@SOLO_IMAGENOLOGIA
def confirmar_realizacion(id_cita):
    return resultado_accion(lambda: ctrl.registrar_realizacion(session["id_usuario"], id_cita),
                            "Examen registrado como realizado.", url_for("imagenologia.agenda"))

@bp.post("/<int:id_cita>/cancelar")
@SOLO_IMAGENOLOGIA
def cancelar(id_cita):
    return resultado_accion(lambda: ctrl.cancelar(session["id_usuario"], id_cita),
                            "Examen cancelado.", url_for("imagenologia.agenda"))