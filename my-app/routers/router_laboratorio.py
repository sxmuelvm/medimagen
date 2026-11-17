"""Rutas del personal de laboratorio."""
from flask import Blueprint, flash, redirect, request, session, url_for

from controllers import laboratorio_controller as ctrl
from utils.constants import CUENTA_LABORATORIO
from utils.decorators import roles_permitidos
from utils.errors import ErrorNegocio
from utils.helpers import render_pagina

bp = Blueprint("laboratorio", __name__, url_prefix="/laboratorio")
SOLO_LABORATORIO = roles_permitidos(CUENTA_LABORATORIO)


@bp.get("/")
@SOLO_LABORATORIO
def agenda():
    datos = ctrl.agenda(session["id_usuario"], request.args.get("q"), request.args.get("estado"),
                        request.args.get("desde"), request.args.get("hasta"), request.args.get("pagina"))
    return render_pagina("public/laboratorio/agenda.html", **datos)


@bp.route("/<int:id_cita>/resultado", methods=["GET", "POST"])
@SOLO_LABORATORIO
def registrar_resultado(id_cita):
    """Registra el resultado de un examen pendiente o corrige el de uno ya registrado."""
    usuario = session["id_usuario"]
    contexto = ctrl.obtener(usuario, id_cita)
    if request.method == "POST":
        try:
            if contexto["resultado"] is None:
                ctrl.registrar_resultado(usuario, id_cita, request.form)
                flash("Resultado registrado.", "exito")
            else:
                ctrl.corregir_resultado(usuario, id_cita, request.form)
                flash("Resultado corregido.", "exito")
        except ErrorNegocio as error:
            if error.codigo != 400:
                raise
            flash(error.mensaje, "error")
            return render_pagina("public/laboratorio/registrar_resultado.html", form=request.form, **contexto), 400
        return redirect(url_for("laboratorio.agenda"))
    if contexto["resultado"] is None and not contexto["examen"]["puede_registrar"]:
        flash("A este examen no se le puede registrar un resultado ahora.", "aviso")
        return redirect(url_for("laboratorio.agenda"))
    return render_pagina("public/laboratorio/registrar_resultado.html", form=contexto["resultado"] or {}, **contexto)