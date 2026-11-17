"""Rutas de medicos (solo administrador)."""
from flask import Blueprint, flash, redirect, request, session, url_for

from controllers import medicos_controller as ctrl
from utils.constants import CUENTA_ADMINISTRADOR
from utils.decorators import roles_permitidos
from utils.errors import ErrorNegocio, resultado_accion
from utils.helpers import render_pagina

bp = Blueprint("medicos", __name__, url_prefix="/medicos")
SOLO_ADMIN = roles_permitidos(CUENTA_ADMINISTRADOR)


@bp.get("/")
@SOLO_ADMIN
def lista():
    datos = ctrl.listar(session["id_usuario"], request.args.get("q"), request.args.get("id_especialidad"),
                        request.args.get("estado"), request.args.get("pagina"))
    return render_pagina("public/medicos/lista.html", **datos)


@bp.route("/nuevo", methods=["GET", "POST"])
@SOLO_ADMIN
def crear():
    admin = session["id_usuario"]
    if request.method == "POST":
        try:
            ctrl.crear(request.form, admin)
        except ErrorNegocio as error:
            if error.codigo != 400:
                raise
            flash(error.mensaje, "error")
            return render_pagina("public/medicos/formulario.html", medico=None, form=request.form,
                                 especialidades=ctrl.especialidades_activas(admin)), 400
        flash("Médico registrado.", "exito")
        return redirect(url_for("medicos.lista"))
    return render_pagina("public/medicos/formulario.html", medico=None, form={},
                         especialidades=ctrl.especialidades_activas(admin))


@bp.route("/<int:id_medico>/editar", methods=["GET", "POST"])
@SOLO_ADMIN
def editar(id_medico):
    admin = session["id_usuario"]
    medico = ctrl.obtener(id_medico, admin)
    if request.method == "POST":
        try:
            ctrl.actualizar(id_medico, request.form, admin)
        except ErrorNegocio as error:
            if error.codigo != 400:
                raise
            flash(error.mensaje, "error")
            return render_pagina("public/medicos/formulario.html", medico=medico, form=request.form,
                                 especialidades=ctrl.especialidades_activas(admin)), 400
        flash("Cambios guardados.", "exito")
        return redirect(url_for("medicos.lista"))
    return render_pagina("public/medicos/formulario.html", medico=medico, form={},
                         especialidades=ctrl.especialidades_activas(admin))


@bp.post("/<int:id_medico>/estado")
@SOLO_ADMIN
def estado(id_medico):
    nuevo = request.form.get("estado")
    return resultado_accion(lambda: ctrl.cambiar_estado(id_medico, nuevo, session["id_usuario"]),
                            "Estado actualizado.", url_for("medicos.lista"))


@bp.post("/<int:id_medico>/eliminar")
@SOLO_ADMIN
def eliminar(id_medico):
    return resultado_accion(lambda: ctrl.eliminar(id_medico, session["id_usuario"]),
                            "Médico eliminado.", url_for("medicos.lista"))