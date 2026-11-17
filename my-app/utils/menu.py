"""Menu lateral segun el rol. Solo muestra las pantallas que ya existen."""
from flask import current_app, request, url_for

from utils.constants import MENU


def menu_para(cuenta):
    items = []
    for titulo, endpoint in MENU.get(cuenta, []):
        if endpoint in current_app.view_functions:
            items.append({"titulo": titulo, "url": url_for(endpoint), "endpoint": endpoint,
                          "activo": request.endpoint == endpoint})
    return items