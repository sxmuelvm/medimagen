"""Rutas del medico: agenda, atender consulta y examenes solicitados."""
from itertools import zip_longest

from flask import Blueprint, abort, flash, jsonify, redirect, request, session, url_for

from controllers import citas_controller as citas
from controllers import consultas_controller as ctrl
from utils import validators
from utils.constants import CUENTA_MEDICO
from utils.decorators import roles_permitidos
from utils.errors import ErrorNegocio, resultado_accion
from utils.helpers import render_pagina

bp = Blueprint("consultas", __name__, url_prefix="/consultas")
SOLO_MEDICO = roles_permitidos(CUENTA_MEDICO)
MAX_FILAS = 20          # medicamentos por receta


def _medico():
    """(id del usuario, id del medico), ambos de la sesion. Un usuario 'medico' sin ficha no puede entrar."""
    if not session.get("id_medico"):
        abort(403)
    return session["id_usuario"], session["id_medico"]


def _medicamentos(form):
    """Arma la lista de medicamentos de la receta a partir de los campos repetidos del formulario."""
    return [{"medicamento": a, "dosis": b, "frecuencia": c, "duracion": d, "indicaciones": e}
            for a, b, c, d, e in zip_longest(form.getlist("medicamento"), form.getlist("dosis"),
                                             form.getlist("frecuencia"), form.getlist("duracion"),
                                             form.getlist("indicaciones_med"), fillvalue="")][:MAX_FILAS]


@bp.get("/")
@SOLO_MEDICO
def mi_agenda():
    usuario, id_medico = _medico()
    datos = ctrl.mi_agenda(usuario, id_medico, request.args.get("q"), request.args.get("estado"),
                           request.args.get("desde"), request.args.get("hasta"), request.args.get("pagina"))
    return render_pagina("public/consultas/mi_agenda.html", **datos)


@bp.route("/<int:id_cita>/atender", methods=["GET", "POST"])
@SOLO_MEDICO
def atender(id_cita):
    usuario, id_medico = _medico()
    if request.method == "POST":
        medicamentos = _medicamentos(request.form)
        try:
            ctrl.atender(usuario, id_medico, id_cita, request.form, medicamentos)
        except ErrorNegocio as error:
            if error.codigo != 400:
                raise
            flash(error.mensaje, "error")
            return render_pagina("public/consultas/atender.html", form=request.form,
                                 filas_medicamentos=medicamentos,
                                 **ctrl.preparar_atencion(usuario, id_medico, id_cita)), 400
        flash("Consulta registrada.", "exito")
        return redirect(url_for("consultas.atender", id_cita=id_cita))
    return render_pagina("public/consultas/atender.html", form={}, filas_medicamentos=[],
                         **ctrl.preparar_atencion(usuario, id_medico, id_cita))


@bp.route("/examenes/nuevo", methods=["GET", "POST"])
@SOLO_MEDICO
def solicitar_examen():
    usuario, id_medico = _medico()
    if request.method == "POST":
        try:
            creado = ctrl.solicitar_examen(usuario, id_medico, request.form)
        except ErrorNegocio as error:
            if error.codigo != 400:
                raise
            flash(error.mensaje, "error")
            return render_pagina("public/consultas/solicitar_examen.html", form=request.form,
                                 paciente=citas.buscar_paciente(CUENTA_MEDICO, usuario,
                                                                request.form.get("cedula_paciente")),
                                 busqueda="", resultados=None, **ctrl.opciones_examen(usuario)), 400
        flash("Examen solicitado y agendado.", "exito")
        return redirect(url_for("consultas.examenes_solicitados", cita=creado["id_cita"]))
    # Misma busqueda que en recepcion: solo numeros = cedula (maximo 10 digitos); con letras, por nombre y apellido
    busqueda = " ".join((request.args.get("q") or "").split())
    if busqueda.isdigit():
        busqueda = busqueda[:10]
    cedula = request.args.get("cedula")
    if not cedula and busqueda.isdigit() and len(busqueda) == 10:
        cedula = busqueda
    paciente = citas.buscar_paciente(CUENTA_MEDICO, usuario, cedula) if cedula else None
    resultados = None
    if not paciente and busqueda:
        resultados = citas.buscar_pacientes(CUENTA_MEDICO, usuario, busqueda, limite=10)
    return render_pagina("public/consultas/solicitar_examen.html", form={}, paciente=paciente,
                         busqueda=busqueda, resultados=resultados, **ctrl.opciones_examen(usuario))


@bp.get("/pacientes")
@SOLO_MEDICO
def pacientes():
    """Pacientes que coinciden con lo escrito (cedula o nombre), para las sugerencias al solicitar un examen."""
    usuario, _ = _medico()
    return jsonify({"pacientes": citas.buscar_pacientes(CUENTA_MEDICO, usuario, request.args.get("q"))})


@bp.get("/examenes/horarios")
@SOLO_MEDICO
def horarios_examen():
    """Horarios libres para un examen (JSON). Solo areas 2 (imagenologia) y 3 (laboratorio)."""
    usuario, _ = _medico()
    try:
        area = validators.entero(request.args.get("id_area"), "El área", minimo=2, maximo=3)
        lista = citas.horarios_disponibles(CUENTA_MEDICO, usuario, request.args.get("fecha"), area,
                                           id_subtipo=request.args.get("id_subtipo"),
                                           cedula_paciente=request.args.get("cedula_paciente"))
    except ErrorNegocio as error:
        return jsonify({"error": error.mensaje}), error.codigo
    return jsonify({"horarios": lista})


@bp.get("/examenes")
@SOLO_MEDICO
def examenes_solicitados():
    usuario, id_medico = _medico()
    return render_pagina("public/consultas/examenes_solicitados.html",
                         **ctrl.examenes_solicitados(usuario, id_medico, request.args.get("estado"),
                                                     request.args.get("q"), request.args.get("pagina")))


@bp.get("/examenes/<int:id_cita>/resultado")
@SOLO_MEDICO
def resultado_examen(id_cita):
    usuario, id_medico = _medico()
    return render_pagina("public/consultas/resultado_examen.html",
                         resultado=ctrl.resultado_examen(usuario, id_medico, id_cita), id_cita=id_cita)

@bp.route("/examenes/<int:id_cita>/editar", methods=["GET", "POST"])
@SOLO_MEDICO
def modificar_examen(id_cita):
    """Reprograma un examen que el medico solicito y que sigue pendiente."""
    usuario, id_medico = _medico()
    examen = ctrl.examen_propio(usuario, id_medico, id_cita)
    if request.method == "POST":
        try:
            ctrl.modificar_examen(usuario, id_medico, id_cita, request.form)
        except ErrorNegocio as error:
            if error.codigo != 400:
                raise
            flash(error.mensaje, "error")
            return render_pagina("public/consultas/modificar_examen.html", form=request.form, examen=examen,
                                 **ctrl.opciones_examen(usuario)), 400
        flash("Examen modificado.", "exito")
        return redirect(url_for("consultas.examenes_solicitados", cita=id_cita))
    return render_pagina("public/consultas/modificar_examen.html", form={}, examen=examen,
                         **ctrl.opciones_examen(usuario))


@bp.post("/examenes/<int:id_cita>/cancelar")
@SOLO_MEDICO
def cancelar_examen(id_cita):
    usuario, id_medico = _medico()
    return resultado_accion(lambda: ctrl.cancelar_examen(usuario, id_medico, id_cita),
                            "Examen cancelado.", url_for("consultas.examenes_solicitados"))