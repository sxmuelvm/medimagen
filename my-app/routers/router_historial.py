"""Rutas del paciente: sus citas, historial, recetas y resultados. Siempre con la cedula de la sesion."""
from flask import Blueprint, abort, request, session

from controllers import historial_controller as ctrl
from utils.constants import CUENTA_PACIENTE
from utils.decorators import roles_permitidos
from utils.helpers import render_pagina

bp = Blueprint("historial", __name__, url_prefix="/historial")
SOLO_PACIENTE = roles_permitidos(CUENTA_PACIENTE)


def _paciente():
    """(id del usuario, cedula del paciente), ambos de la sesion. Un usuario 'paciente' sin ficha no entra."""
    if not session.get("cedula_paciente"):
        abort(403)
    return session["id_usuario"], session["cedula_paciente"]


@bp.get("/citas")
@SOLO_PACIENTE
def mis_citas():
    usuario, cedula = _paciente()
    datos = ctrl.mis_citas(usuario, cedula, request.args.get("estado"), request.args.get("desde"),
                           request.args.get("hasta"), request.args.get("pagina"))
    return render_pagina("public/historial/mis_citas.html", **datos)


@bp.get("/")
@SOLO_PACIENTE
def mi_historial():
    usuario, cedula = _paciente()
    return render_pagina("public/historial/mi_historial.html",
                         **ctrl.mi_historial(usuario, cedula, request.args.get("pagina")))


@bp.get("/recetas")
@SOLO_PACIENTE
def mis_recetas():
    usuario, cedula = _paciente()
    return render_pagina("public/historial/mis_recetas.html",
                         **ctrl.mis_recetas(usuario, cedula, request.args.get("pagina")))


@bp.get("/resultados")
@SOLO_PACIENTE
def mis_resultados():
    usuario, cedula = _paciente()
    return render_pagina("public/historial/mis_resultados.html",
                         **ctrl.mis_resultados(usuario, cedula, request.args.get("pagina")))