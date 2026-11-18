"""Rutas de administracion de usuarios (solo administrador)."""
from flask import Blueprint, flash, redirect, request, session, url_for

from controllers import usuarios_controller as ctrl
from utils.constants import CUENTA_ADMINISTRADOR
from utils.decorators import roles_permitidos
from utils.errors import ErrorNegocio, resultado_accion
from utils.helpers import render_pagina

bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")
SOLO_ADMIN = roles_permitidos(CUENTA_ADMINISTRADOR)


@bp.get("/")
@SOLO_ADMIN
def lista():
    datos = ctrl.listar(session["id_usuario"], request.args.get("q"), request.args.get("rol"),
                        request.args.get("estado"), request.args.get("pagina"))
    return render_pagina("public/usuarios/lista.html", **datos)


@bp.route("/nuevo", methods=["GET", "POST"])
@SOLO_ADMIN
def crear():
    admin = session["id_usuario"]
    if request.method == "POST":
        try:
            nuevo = ctrl.crear(request.form, admin)
        except ErrorNegocio as error:
            if error.codigo != 400:
                raise
            flash(error.mensaje, "error")
            return render_pagina("public/usuarios/crear.html", form=request.form, **ctrl.opciones_crear(admin)), 400
        flash("Usuario creado. Deberá cambiar su contraseña al iniciar sesión.", "exito")
        if nuevo["clave_temporal"]:
            # La clave generada se muestra una sola vez, en esta respuesta (no se guarda en la sesion)
            return render_pagina("public/usuarios/crear.html", creado=nuevo, form={}, **ctrl.opciones_crear(admin))
        return redirect(url_for("usuarios.lista"))
    return render_pagina("public/usuarios/crear.html", form={}, **ctrl.opciones_crear(admin))


@bp.route("/<int:id_usuario>/editar", methods=["GET", "POST"])
@SOLO_ADMIN
def editar(id_usuario):
    admin = session["id_usuario"]
    if request.method == "POST":
        try:
            ctrl.actualizar(id_usuario, request.form, admin)
        except ErrorNegocio as error:
            if error.codigo != 400:
                raise
            flash(error.mensaje, "error")
            return render_pagina("public/usuarios/editar.html", form=request.form,
                                 **ctrl.detalle(id_usuario, admin)), 400
        flash("Cambios guardados.", "exito")
        return redirect(url_for("usuarios.lista"))
    return render_pagina("public/usuarios/editar.html", form={}, **ctrl.detalle(id_usuario, admin))


@bp.post("/<int:id_usuario>/estado")
@SOLO_ADMIN
def estado(id_usuario):
    nuevo = request.form.get("estado")
    return resultado_accion(lambda: ctrl.cambiar_estado(id_usuario, nuevo, session["id_usuario"]),
                            "Estado actualizado.", url_for("usuarios.editar", id_usuario=id_usuario))


@bp.post("/<int:id_usuario>/eliminar")
@SOLO_ADMIN
def eliminar(id_usuario):
    return resultado_accion(lambda: ctrl.eliminar(id_usuario, session["id_usuario"]),
                            "Usuario eliminado.", url_for("usuarios.lista"))

@bp.post("/<int:id_usuario>/desbloquear")
@SOLO_ADMIN
def desbloquear(id_usuario):
    return resultado_accion(lambda: ctrl.desbloquear(id_usuario, session["id_usuario"]),
                            "Usuario desbloqueado.", url_for("usuarios.editar", id_usuario=id_usuario))


@bp.route("/<int:id_usuario>/clave", methods=["GET", "POST"])
@SOLO_ADMIN
def restablecer_clave(id_usuario):
    admin = session["id_usuario"]
    if request.method == "POST":
        try:
            resultado = ctrl.restablecer_clave(id_usuario, request.form, admin)
        except ErrorNegocio as error:
            if error.codigo != 400:
                raise
            flash(error.mensaje, "error")
            return render_pagina("public/usuarios/restablecer_clave.html",
                                 usuario=ctrl.obtener(id_usuario, admin)), 400
        flash("Contraseña restablecida. Deberá cambiarla al iniciar sesión.", "exito")
        if resultado["clave_temporal"]:
            return render_pagina("public/usuarios/restablecer_clave.html", usuario=resultado["usuario"],
                                 clave_temporal=resultado["clave_temporal"])
        return redirect(url_for("usuarios.lista"))
    return render_pagina("public/usuarios/restablecer_clave.html", usuario=ctrl.obtener(id_usuario, admin))