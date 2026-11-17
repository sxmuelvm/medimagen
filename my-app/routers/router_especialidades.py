"""Rutas de especialidades (solo administrador)."""
from flask import Blueprint, flash, redirect, request, session, url_for

from controllers import especialidades_controller as ctrl
from utils.constants import CUENTA_ADMINISTRADOR
from utils.decorators import roles_permitidos
from utils.errors import ErrorNegocio, resultado_accion
from utils.helpers import render_pagina

bp = Blueprint("especialidades", __name__, url_prefix="/especialidades")
SOLO_ADMIN = roles_permitidos(CUENTA_ADMINISTRADOR)


@bp.get("/")
@SOLO_ADMIN
def lista():
    datos = ctrl.listar(session["id_usuario"], request.args.get("q"), request.args.get("estado"),
                        request.args.get("pagina"))
    return render_pagina("public/especialidades/lista.html", **datos)


@bp.route("/nueva", methods=["GET", "POST"])
@SOLO_ADMIN
def crear():
    if request.method == "POST":
        try:
            ctrl.crear(request.form, session["id_usuario"])
        except ErrorNegocio as error:
            if error.codigo != 400:
                raise
            flash(error.mensaje, "error")
            return render_pagina("public/especialidades/formulario.html", especialidad=None,
                                 form=request.form), 400
        flash("Especialidad registrada.", "exito")
        return redirect(url_for("especialidades.lista"))
    return render_pagina("public/especialidades/formulario.html", especialidad=None, form={})


@bp.route("/<codigo>/editar", methods=["GET", "POST"])
@SOLO_ADMIN
def editar(codigo):
    admin = session["id_usuario"]
    especialidad = ctrl.obtener(codigo, admin)
    if request.method == "POST":
        try:
            ctrl.actualizar(codigo, request.form, admin)
        except ErrorNegocio as error:
            if error.codigo != 400:
                raise
            flash(error.mensaje, "error")
            return render_pagina("public/especialidades/formulario.html", especialidad=especialidad,
                                 form=request.form), 400
        flash("Cambios guardados.", "exito")
        return redirect(url_for("especialidades.lista"))
    return render_pagina("public/especialidades/formulario.html", especialidad=especialidad, form={})


@bp.post("/<codigo>/estado")
@SOLO_ADMIN
def estado(codigo):
    nuevo = request.form.get("estado")
    return resultado_accion(lambda: ctrl.cambiar_estado(codigo, nuevo, session["id_usuario"]),
                            "Estado actualizado.", url_for("especialidades.lista"))


@bp.post("/<codigo>/eliminar")
@SOLO_ADMIN
def eliminar(codigo):
    return resultado_accion(lambda: ctrl.eliminar(codigo, session["id_usuario"]),
                            "Especialidad eliminada.", url_for("especialidades.lista"))