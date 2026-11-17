"""Rutas de citas. Las usan recepcion y el administrador."""
from flask import Blueprint, flash, jsonify, redirect, request, session, url_for

from controllers import citas_controller as ctrl
from utils.constants import CUENTA_ADMINISTRADOR, CUENTA_RECEPCION
from utils.decorators import roles_permitidos
from utils.errors import ErrorNegocio, resultado_accion
from utils.helpers import render_pagina

bp = Blueprint("citas", __name__, url_prefix="/citas")
ADMIN_O_RECEPCION = roles_permitidos(CUENTA_ADMINISTRADOR, CUENTA_RECEPCION)


def _quien():
    return session["cuenta"], session["id_usuario"]


@bp.get("/")
@ADMIN_O_RECEPCION
def agenda():
    cuenta, usuario = _quien()
    datos = ctrl.agenda(cuenta, usuario, request.args.get("q"), request.args.get("id_area"),
                        request.args.get("estado"), request.args.get("desde"), request.args.get("hasta"),
                        request.args.get("pagina"))
    return render_pagina("public/citas/agenda.html", **datos)


@bp.get("/horarios")
@ADMIN_O_RECEPCION
def horarios():
    """Horarios libres en formato JSON, para que el formulario los consulte al elegir fecha, medico o equipo."""
    cuenta, usuario = _quien()
    try:
        lista = ctrl.horarios_disponibles(cuenta, usuario, request.args.get("fecha"), request.args.get("id_area"),
                                          request.args.get("id_medico"), request.args.get("id_recurso"),
                                          request.args.get("cedula_paciente"), request.args.get("excluir_cita"))
    except ErrorNegocio as error:
        return jsonify({"error": error.mensaje}), error.codigo
    return jsonify({"horarios": lista})


@bp.route("/nueva", methods=["GET", "POST"])
@ADMIN_O_RECEPCION
def nueva():
    cuenta, usuario = _quien()
    if request.method == "POST":
        try:
            creada = ctrl.crear(cuenta, usuario, request.form)
        except ErrorNegocio as error:
            if error.codigo != 400:
                raise
            flash(error.mensaje, "error")
            return render_pagina("public/citas/nueva.html", form=request.form,
                                 **ctrl.opciones_nueva(cuenta, usuario, request.form.get("cedula_paciente"))), 400
        flash("Cita registrada.", "exito")
        return redirect(url_for("citas.detalle", id_cita=creada["id_cita"]))
    return render_pagina("public/citas/nueva.html", form={},
                         **ctrl.opciones_nueva(cuenta, usuario, request.args.get("cedula")))


@bp.get("/<int:id_cita>")
@ADMIN_O_RECEPCION
def detalle(id_cita):
    cuenta, usuario = _quien()
    return render_pagina("public/citas/detalle.html", **ctrl.detalle(cuenta, usuario, id_cita))


@bp.route("/<int:id_cita>/reprogramar", methods=["GET", "POST"])
@ADMIN_O_RECEPCION
def reprogramar(id_cita):
    cuenta, usuario = _quien()
    cita = ctrl.obtener(cuenta, usuario, id_cita)
    if request.method == "POST":
        try:
            ctrl.reprogramar(cuenta, usuario, id_cita, request.form)
        except ErrorNegocio as error:
            if error.codigo != 400:
                raise
            flash(error.mensaje, "error")
            return render_pagina("public/citas/reprogramar.html", cita=cita, form=request.form,
                                 **ctrl.opciones_nueva(cuenta, usuario)), 400
        flash("Cita reprogramada.", "exito")
        return redirect(url_for("citas.detalle", id_cita=id_cita))
    return render_pagina("public/citas/reprogramar.html", cita=cita, form={}, **ctrl.opciones_nueva(cuenta, usuario))


@bp.post("/<int:id_cita>/estado")
@ADMIN_O_RECEPCION
def estado(id_cita):
    cuenta, usuario = _quien()
    nuevo = request.form.get("estado")
    return resultado_accion(lambda: ctrl.cambiar_estado(cuenta, usuario, id_cita, nuevo),
                            "Estado de la cita actualizado.", url_for("citas.detalle", id_cita=id_cita))


@bp.post("/<int:id_cita>/eliminar")
@ADMIN_O_RECEPCION
def eliminar(id_cita):
    cuenta, usuario = _quien()
    return resultado_accion(lambda: ctrl.eliminar(cuenta, usuario, id_cita),
                            "Cita eliminada.", url_for("citas.agenda"))