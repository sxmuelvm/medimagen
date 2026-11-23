"""Calendario semanal de citas: una pagina y los datos de la semana en JSON. Cada rol ve solo lo suyo."""
from flask import Blueprint, jsonify, request, session

from controllers import calendario_controller as ctrl
from utils.constants import CUENTA_ADMINISTRADOR, CUENTA_RECEPCION
from utils.decorators import login_requerido
from utils.helpers import render_pagina

bp = Blueprint("calendario", __name__, url_prefix="/calendario")


def _sesion():
    return session["cuenta"], session["id_usuario"], {"cedula_paciente": session.get("cedula_paciente"),
                                                      "id_medico": session.get("id_medico")}


@bp.get("/")
@login_requerido
def semana():
    cuenta, usuario, _ = _sesion()
    return render_pagina("public/calendario/semana.html", puede_agendar=cuenta in (CUENTA_ADMINISTRADOR, CUENTA_RECEPCION),
                         **ctrl.filtros_agenda(cuenta, usuario))


@bp.get("/datos")
@login_requerido
def datos():
    cuenta, usuario, sesion = _sesion()
    return jsonify(ctrl.semana(cuenta, usuario, sesion, request.args.get("fecha"), request.args.get("id_area"),
                               request.args.get("id_medico")))
