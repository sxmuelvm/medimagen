"""Panel de inicio: cada rol ve su propio panel."""
from flask import Blueprint, abort, session

from controllers import dashboard_controller
from utils.constants import CUENTAS
from utils.decorators import login_requerido
from utils.helpers import render_pagina

bp = Blueprint("dashboard", __name__)


@bp.get("/inicio")
@login_requerido
def inicio():
    cuenta = session.get("cuenta")
    if cuenta not in CUENTAS:
        abort(403)
    datos = dashboard_controller.resumen(session)
    return render_pagina(f"public/dashboard/{cuenta}.html", datos=datos)