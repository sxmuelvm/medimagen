"""Rutas de pacientes. Administrador y recepcion."""
from flask import Blueprint, flash, redirect, request, session, url_for

from controllers import pacientes_controller as ctrl
from utils.constants import CUENTA_ADMINISTRADOR, CUENTA_RECEPCION
from utils.decorators import roles_permitidos
from utils.errors import ErrorNegocio, resultado_accion
from utils.helpers import render_pagina

bp = Blueprint("pacientes", __name__, url_prefix="/pacientes")
ADMIN_O_RECEPCION = roles_permitidos(CUENTA_ADMINISTRADOR, CUENTA_RECEPCION)


@bp.get("/")
@ADMIN_O_RECEPCION
def lista():
    datos = ctrl.listar(session["cuenta"], session["id_usuario"], request.args.get("q"),
                        request.args.get("estado"), request.args.get("pagina"))
    return render_pagina("public/pacientes/lista.html", **datos)


@bp.route("/nuevo", methods=["GET", "POST"])
@ADMIN_O_RECEPCION
def crear():
    if request.method == "POST":
        try:
            cedula = ctrl.crear(session["cuenta"], session["id_usuario"], request.form)
        except ErrorNegocio as error:
            if error.codigo != 400:
                raise
            flash(error.mensaje, "error")
            return render_pagina("public/pacientes/formulario.html", paciente=None, form=request.form), 400
        flash("Paciente registrado.", "exito")
        return redirect(url_for("pacientes.ficha", cedula=cedula))
    return render_pagina("public/pacientes/formulario.html", paciente=None, form={})


@bp.get("/<cedula>")
@ADMIN_O_RECEPCION
def ficha(cedula):
    return render_pagina("public/pacientes/ficha.html",
                         **ctrl.ficha(session["cuenta"], session["id_usuario"], cedula))


@bp.route("/<cedula>/editar", methods=["GET", "POST"])
@ADMIN_O_RECEPCION
def editar(cedula):
    cuenta, usuario = session["cuenta"], session["id_usuario"]
    paciente = ctrl.obtener(cuenta, usuario, cedula)
    if request.method == "POST":
        try:
            ctrl.actualizar(cuenta, usuario, cedula, request.form)
        except ErrorNegocio as error:
            if error.codigo != 400:
                raise
            flash(error.mensaje, "error")
            return render_pagina("public/pacientes/formulario.html", paciente=paciente, form=request.form), 400
        flash("Cambios guardados.", "exito")
        return redirect(url_for("pacientes.ficha", cedula=cedula))
    return render_pagina("public/pacientes/formulario.html", paciente=paciente, form={})


@bp.post("/<cedula>/estado")
@ADMIN_O_RECEPCION
def estado(cedula):
    nuevo = request.form.get("estado")
    return resultado_accion(lambda: ctrl.cambiar_estado(session["cuenta"], session["id_usuario"], cedula, nuevo),
                            "Estado actualizado.", url_for("pacientes.ficha", cedula=cedula))


@bp.post("/<cedula>/eliminar")
@ADMIN_O_RECEPCION
def eliminar(cedula):
    return resultado_accion(lambda: ctrl.eliminar(session["cuenta"], session["id_usuario"], cedula),
                            "Paciente eliminado.", url_for("pacientes.lista"))