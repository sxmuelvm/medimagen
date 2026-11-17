"""Rutas de roles (solo administrador)."""
from flask import Blueprint, flash, redirect, request, session, url_for

from controllers import roles_controller as ctrl
from utils.constants import CUENTA_ADMINISTRADOR
from utils.decorators import roles_permitidos
from utils.errors import ErrorNegocio
from utils.helpers import render_pagina

bp = Blueprint("roles", __name__, url_prefix="/roles")
SOLO_ADMIN = roles_permitidos(CUENTA_ADMINISTRADOR)


@bp.get("/")
@SOLO_ADMIN
def lista():
    return render_pagina("public/roles/lista.html", **ctrl.listar(session["id_usuario"]))


@bp.route("/<int:id_rol>/editar", methods=["GET", "POST"])
@SOLO_ADMIN
def editar(id_rol):
    admin = session["id_usuario"]
    if request.method == "POST":
        try:
            ctrl.actualizar(id_rol, request.form, admin)
        except ErrorNegocio as error:
            if error.codigo != 400:
                raise
            flash(error.mensaje, "error")
            return render_pagina("public/roles/formulario.html", rol=ctrl.obtener(id_rol, admin),
                                 form=request.form), 400
        flash("Rol actualizado.", "exito")
        return redirect(url_for("roles.lista"))
    return render_pagina("public/roles/formulario.html", rol=ctrl.obtener(id_rol, admin), form={})