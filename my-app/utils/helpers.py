"""Funciones de apoyo: renderizado, paginacion, filtros de plantilla y datos de la peticion."""
import pprint
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from flask import current_app, render_template, render_template_string, request
from jinja2 import TemplateNotFound

_PENDIENTE = """{% extends "base.html" %}
{% block titulo %}Pantalla pendiente{% endblock %}
{% block contenido %}
<h1>Pantalla pendiente de diseño</h1>
<p>Plantilla: <code>{{ plantilla }}</code></p>
{% if datos %}<pre>{{ datos }}</pre>{% endif %}
{% endblock %}"""


def render_pagina(plantilla, **contexto):
    """render_template, pero si la plantilla aun esta vacia muestra un aviso (y los datos en modo desarrollo).

    Permite probar el backend antes de que el diseno de cada pantalla exista.
    """
    try:
        html = render_template(plantilla, **contexto)
    except TemplateNotFound:
        html = ""
    if html.strip():
        return html
    datos = pprint.pformat(contexto, width=100) if current_app.debug else None
    return render_template_string(_PENDIENTE, plantilla=plantilla, datos=datos)


# ---------- Datos de la peticion ----------
def ip_cliente():
    return (request.remote_addr or "0.0.0.0")[:45]


def navegador():
    return (request.headers.get("User-Agent") or "desconocido")[:255]


# ---------- Paginacion ----------
def pagina_actual(valor):
    try:
        return max(1, int(valor))
    except (TypeError, ValueError):
        return 1


def paginar(total, pagina, por_pagina=10):
    paginas = max(1, -(-total // por_pagina))
    pagina = min(max(1, pagina), paginas)
    desde = (pagina - 1) * por_pagina
    return {"pagina": pagina, "por_pagina": por_pagina, "total": total, "paginas": paginas,
            "offset": desde, "desde": desde + 1 if total else 0, "hasta": min(desde + por_pagina, total)}


# ---------- Filtros de plantilla ----------
def _filtro_hora(valor):
    if valor is None:
        return ""
    if isinstance(valor, timedelta):             # mysql-connector devuelve TIME como timedelta
        segundos = int(valor.total_seconds())
        return f"{segundos // 3600:02d}:{(segundos % 3600) // 60:02d}"
    if isinstance(valor, (time, datetime)):
        return valor.strftime("%H:%M")
    return str(valor)[:5]


def _filtro_fecha(valor):
    if isinstance(valor, (date, datetime)):
        return valor.strftime("%d/%m/%Y")
    return "" if valor is None else str(valor)


def _filtro_fechahora(valor):
    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y %H:%M")
    return _filtro_fecha(valor)


def _filtro_dinero(valor):
    if valor is None:
        return ""
    return f"$ {Decimal(valor):,.2f}"


def registrar_filtros(app):
    app.jinja_env.filters["hora"] = _filtro_hora
    app.jinja_env.filters["fecha"] = _filtro_fecha
    app.jinja_env.filters["fechahora"] = _filtro_fechahora
    app.jinja_env.filters["dinero"] = _filtro_dinero