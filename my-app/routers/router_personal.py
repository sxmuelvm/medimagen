"""Rutas del personal del centro (solo administrador)."""
from flask import Blueprint, flash, redirect, request, session, url_for

from controllers import personal_controller as ctrl
from utils.constants import CUENTA_ADMINISTRADOR
from utils.decorators import roles_permitidos
from utils.errors import ErrorNegocio, resultado_accion
from utils.helpers import render_pagina

bp = Blueprint("personal", __name__, url_prefix="/personal")
SOLO_ADMIN = roles_permitidos(CUENTA_ADMINISTRADOR)


@bp.get("/")
@SOLO_ADMIN
def lista():
    datos = ctrl.listar(session["id_usuario"], request.args.get("q"), request.args.get("estado"),
                        request.args.get("pagina"))
    return render_pagina("public/personal/lista.html", **datos)


@bp.route("/nuevo", methods=["GET", "POST"])
@SOLO_ADMIN
def crear():
    if request.method == "POST":
        try:
            ctrl.crear(request.form, session["id_usuario"])
        except ErrorNegocio as error:
            if error.codigo != 400:
                raise
            flash(error.mensaje, "error")
            return render_pagina("public/personal/formulario.html", persona=None, form=request.form), 400
        flash("Miembro del personal registrado.", "exito")
        return redirect(url_for("personal.lista"))
    return render_pagina("public/personal/formulario.html", persona=None, form={})


@bp.route("/<int:id_personal>/editar", methods=["GET", "POST"])
@SOLO_ADMIN
def editar(id_personal):
    admin = session["id_usuario"]
    persona = ctrl.obtener(id_personal, admin)
    if request.method == "POST":
        try:
            ctrl.actualizar(id_personal, request.form, admin)
        except ErrorNegocio as error:
            if error.codigo != 400:
                raise
            flash(error.mensaje, "error")
            return render_pagina("public/personal/formulario.html", persona=persona, form=request.form), 400
        flash("Cambios guardados.", "exito")
        return redirect(url_for("personal.lista"))
    return render_pagina("public/personal/formulario.html", persona=persona, form={})


@bp.post("/<int:id_personal>/estado")
@SOLO_ADMIN
def estado(id_personal):
    nuevo = request.form.get("estado")
    return resultado_accion(lambda: ctrl.cambiar_estado(id_personal, nuevo, session["id_usuario"]),
                            "Estado actualizado.", url_for("personal.lista"))


@bp.post("/<int:id_personal>/eliminar")
@SOLO_ADMIN
def eliminar(id_personal):
    return resultado_accion(lambda: ctrl.eliminar(id_personal, session["id_usuario"]),
                            "Registro eliminado.", url_for("personal.lista"))