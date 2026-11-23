"""Rutas de catalogos (solo administrador). Cada catalogo tiene una sola pantalla con su lista y su formulario:
para editar se abre la misma pantalla con ?editar=<codigo>."""
from flask import Blueprint, flash, redirect, request, session, url_for

from controllers import catalogos_controller as ctrl
from utils.constants import CUENTA_ADMINISTRADOR
from utils.decorators import roles_permitidos
from utils.errors import ErrorNegocio, resultado_accion
from utils.helpers import render_pagina

bp = Blueprint("catalogos", __name__, url_prefix="/catalogos")
SOLO_ADMIN = roles_permitidos(CUENTA_ADMINISTRADOR)


def _admin():
    return session["id_usuario"]


def _guardar(plantilla, contexto, accion, mensaje_ok, destino):
    """Ejecuta crear/modificar. Si hay un error de validacion vuelve a mostrar la pantalla con lo escrito."""
    try:
        accion()
    except ErrorNegocio as error:
        if error.codigo != 400:
            raise
        flash(error.mensaje, "error")
        return render_pagina(plantilla, form=request.form, **contexto()), 400
    flash(mensaje_ok, "exito")
    return redirect(destino)


@bp.get("/")
@SOLO_ADMIN
def index():
    return render_pagina("public/catalogos/index.html", **ctrl.resumen(_admin()))


# ---------- Areas ----------
@bp.get("/areas")
@SOLO_ADMIN
def areas():
    editar = request.args.get("editar", type=int)
    editando = ctrl.obtener_area(editar, _admin()) if editar else None
    return render_pagina("public/catalogos/areas.html", form={}, editando=editando, **ctrl.listar_areas(_admin()))


@bp.post("/areas/<int:id_area>")
@SOLO_ADMIN
def area_guardar(id_area):
    return _guardar("public/catalogos/areas.html",
                    lambda: {"editando": ctrl.obtener_area(id_area, _admin()), **ctrl.listar_areas(_admin())},
                    lambda: ctrl.actualizar_area(id_area, request.form, _admin()),
                    "Área actualizada.", url_for("catalogos.areas"))


# ---------- Recursos de atencion ----------
@bp.get("/recursos")
@SOLO_ADMIN
def recursos():
    editar = request.args.get("editar", type=int)
    editando = ctrl.obtener_recurso(editar, _admin()) if editar else None
    datos = ctrl.listar_recursos(_admin(), request.args.get("id_area", type=int), request.args.get("estado"))
    return render_pagina("public/catalogos/recursos.html", form={}, editando=editando, **datos)


@bp.post("/recursos")
@SOLO_ADMIN
def recurso_crear():
    return _guardar("public/catalogos/recursos.html",
                    lambda: {"editando": None, **ctrl.listar_recursos(_admin())},
                    lambda: ctrl.crear_recurso(request.form, _admin()),
                    "Recurso registrado.", url_for("catalogos.recursos"))


@bp.post("/recursos/<int:id_recurso>")
@SOLO_ADMIN
def recurso_guardar(id_recurso):
    return _guardar("public/catalogos/recursos.html",
                    lambda: {"editando": ctrl.obtener_recurso(id_recurso, _admin()), **ctrl.listar_recursos(_admin())},
                    lambda: ctrl.actualizar_recurso(id_recurso, request.form, _admin()),
                    "Recurso actualizado.", url_for("catalogos.recursos"))


@bp.post("/recursos/<int:id_recurso>/eliminar")
@SOLO_ADMIN
def recurso_eliminar(id_recurso):
    return resultado_accion(lambda: ctrl.eliminar_recurso(id_recurso, _admin()),
                            "Recurso eliminado.", url_for("catalogos.recursos"))


# ---------- Tipos de examen ----------
@bp.get("/tipos-examen")
@SOLO_ADMIN
def tipos_examen():
    editar = request.args.get("editar")
    editando = ctrl.obtener_tipo(editar, _admin()) if editar else None
    return render_pagina("public/catalogos/tipos_examen.html", form={}, editando=editando,
                         **ctrl.listar_tipos(_admin()))


@bp.post("/tipos-examen")
@SOLO_ADMIN
def tipo_crear():
    return _guardar("public/catalogos/tipos_examen.html",
                    lambda: {"editando": None, **ctrl.listar_tipos(_admin())},
                    lambda: ctrl.crear_tipo(request.form, _admin()),
                    "Tipo de examen registrado.", url_for("catalogos.tipos_examen"))


@bp.post("/tipos-examen/<id_tipo>")
@SOLO_ADMIN
def tipo_guardar(id_tipo):
    return _guardar("public/catalogos/tipos_examen.html",
                    lambda: {"editando": ctrl.obtener_tipo(id_tipo, _admin()), **ctrl.listar_tipos(_admin())},
                    lambda: ctrl.actualizar_tipo(id_tipo, request.form, _admin()),
                    "Tipo de examen actualizado.", url_for("catalogos.tipos_examen"))


@bp.post("/tipos-examen/<id_tipo>/eliminar")
@SOLO_ADMIN
def tipo_eliminar(id_tipo):
    return resultado_accion(lambda: ctrl.eliminar_tipo(id_tipo, _admin()),
                            "Tipo de examen eliminado.", url_for("catalogos.tipos_examen"))


# ---------- Subtipos de examen ----------
def _contexto_subtipos(editando=None):
    return lambda: {"editando": editando() if editando else None,
                    **ctrl.listar_subtipos(_admin(), request.args.get("q"), request.args.get("id_tipo"),
                                           request.args.get("estado"), request.args.get("pagina"))}


@bp.get("/subtipos-examen")
@SOLO_ADMIN
def subtipos_examen():
    editar = request.args.get("editar")
    editando = ctrl.obtener_subtipo(editar, _admin()) if editar else None
    datos = ctrl.listar_subtipos(_admin(), request.args.get("q"), request.args.get("id_tipo"),
                                 request.args.get("estado"), request.args.get("pagina"))
    return render_pagina("public/catalogos/subtipos_examen.html", form={}, editando=editando, **datos)


@bp.post("/subtipos-examen")
@SOLO_ADMIN
def subtipo_crear():
    return _guardar("public/catalogos/subtipos_examen.html", _contexto_subtipos(),
                    lambda: ctrl.crear_subtipo(request.form, _admin()),
                    "Examen registrado.", url_for("catalogos.subtipos_examen"))


@bp.post("/subtipos-examen/<id_subtipo>")
@SOLO_ADMIN
def subtipo_guardar(id_subtipo):
    return _guardar("public/catalogos/subtipos_examen.html",
                    _contexto_subtipos(lambda: ctrl.obtener_subtipo(id_subtipo, _admin())),
                    lambda: ctrl.actualizar_subtipo(id_subtipo, request.form, _admin()),
                    "Examen actualizado.", url_for("catalogos.subtipos_examen"))


@bp.post("/subtipos-examen/<id_subtipo>/eliminar")
@SOLO_ADMIN
def subtipo_eliminar(id_subtipo):
    return resultado_accion(lambda: ctrl.eliminar_subtipo(id_subtipo, _admin()),
                            "Examen eliminado.", url_for("catalogos.subtipos_examen"))
