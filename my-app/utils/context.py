"""Variables disponibles en todas las plantillas: usuario, menu y anio."""
from datetime import date

from flask import session

from utils.constants import ETIQUETA_CUENTA
from utils.menu import menu_para


def registrar_contexto(app):
    @app.context_processor
    def _contexto():
        if not session.get("id_usuario"):
            return {"usuario": None, "menu": [], "anio": date.today().year}
        cuenta = session.get("cuenta")
        usuario = {
            "id": session["id_usuario"],
            "cedula": session.get("cedula"),
            "nombres": session.get("nombres"),
            "apellidos": session.get("apellidos"),
            "nombre_usuario": session.get("nombre_usuario"),
            "cuenta": cuenta,
            "rol": ETIQUETA_CUENTA.get(cuenta, cuenta),
        }
        return {"usuario": usuario, "menu": menu_para(cuenta), "anio": date.today().year}