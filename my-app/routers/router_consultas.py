"""Rutas del medico: agenda, atender consulta y examenes solicitados."""
from itertools import zip_longest

from flask import Blueprint, abort, flash, jsonify, redirect, request, session, url_for

from controllers import citas_controller as citas
from controllers import consultas_controller as ctrl
from utils import validators
from utils.constants import CUENTA_MEDICO
from utils.decorators import roles_permitidos
from utils.errors import ErrorNegocio
from utils.helpers import render_pagina

bp = Blueprint("consultas", __name__, url_prefix="/consultas")
SOLO_MEDICO = roles_permitidos(CUENTA_MEDICO)
MAX_FILAS = 20          # diagnosticos o medicamentos por consulta


def _medico():
    """(id del usuario, id del medico), ambos de la sesion. Un usuario 'medico' sin ficha no puede entrar."""
    if not session.get("id_medico"):
        abort(403)
    return session["id_usuario"], session["id_medico"]


def _listas(form):
    """Arma las listas de diagnosticos y medicamentos a partir de los campos repetidos del formulario."""
    diagnosticos = [{"descripcion": d, "observacion": o}
                    for d, o in zip_longest(form.getlist("diagnostico"), form.getlist("diagnostico_obs"),
                                            fillvalue="")][:MAX_FILAS]
    medicamentos = [{"id_medicamento": a, "dosis": b, "frecuencia": c, "duracion": d, "indicaciones": e}
                    for a, b, c, d, e in zip_longest(form.getlist("id_medicamento"), form.getlist("dosis"),
                                                     form.getlist("frecuencia"), form.getlist("duracion"),
                                                     form.getlist("indicaciones_med"), fillvalue="")][:MAX_FILAS]
    return diagnosticos, medicamentos


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
        diagnosticos, medicamentos = _listas(request.form)
        try:
            ctrl.atender(usuario, id_medico, id_cita, request.form, diagnosticos, medicamentos)
        except ErrorNegocio as error:
            if error.codigo != 400:
                raise
            flash(error.mensaje, "error")
            return render_pagina("public/consultas/atender.html", form=request.form, diagnosticos=diagnosticos,
                                 filas_medicamentos=medicamentos,
                                 **ctrl.preparar_atencion(usuario, id_medico, id_cita)), 400
        flash("Consulta registrada.", "exito")
        return redirect(url_for("consultas.atender", id_cita=id_cita))
    return render_pagina("public/consultas/atender.html", form={}, diagnosticos=[], filas_medicamentos=[],
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
                                 **ctrl.opciones_examen(usuario)), 400
        flash("Examen solicitado y agendado.", "exito")
        return redirect(url_for("consultas.examenes_solicitados", cita=creado["id_cita"]))
    return render_pagina("public/consultas/solicitar_examen.html", form={},
                         paciente=citas.buscar_paciente(CUENTA_MEDICO, usuario, request.args.get("cedula")),
                         **ctrl.opciones_examen(usuario))


@bp.get("/examenes/horarios")
@SOLO_MEDICO
def horarios_examen():
    """Horarios libres para un examen (JSON). Solo areas 2 (imagenologia) y 3 (laboratorio)."""
    usuario, _ = _medico()
    try:
        area = validators.entero(request.args.get("id_area"), "El área", minimo=2, maximo=3)
        lista = citas.horarios_disponibles(CUENTA_MEDICO, usuario, request.args.get("fecha"), area,
                                           id_recurso=request.args.get("id_recurso"),
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