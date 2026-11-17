"""Aplicacion Flask de Medimagen (fabrica de la aplicacion).

Local : python run.py
Docker: gunicorn app:app
"""
import importlib
import pkgutil

from flask import Flask

import routers
from config import Config
from extensions import csrf, limiter
from utils.context import registrar_contexto
from utils.errors import registrar_manejadores_errores
from utils.helpers import registrar_filtros
from utils.logger import configurar_logger
from utils.security import registrar_seguridad


def _registrar_rutas(app, log):
    """Registra todo router_*.py que defina un Blueprint llamado `bp` (los archivos vacios se omiten)."""
    for modulo in sorted(pkgutil.iter_modules(routers.__path__), key=lambda m: m.name):
        if not modulo.name.startswith("router_"):
            continue
        router = importlib.import_module(f"routers.{modulo.name}")
        bp = getattr(router, "bp", None)
        if bp is None:
            log.info("Router omitido (sin Blueprint): %s", modulo.name)
            continue
        app.register_blueprint(bp)


def crear_app():
    Config.validar()
    log = configurar_logger(Config.DEBUG)

    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(Config)
    app.url_map.strict_slashes = False

    csrf.init_app(app)
    limiter.init_app(app)

    registrar_filtros(app)
    registrar_contexto(app)
    registrar_seguridad(app)
    registrar_manejadores_errores(app)
    _registrar_rutas(app, log)

    log.info("Medimagen iniciado (entorno: %s, base: %s:%s)", Config.ENTORNO, Config.BD_HOST, Config.BD_PUERTO)
    return app


app = crear_app()