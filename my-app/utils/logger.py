"""Registro de eventos. Consola (docker logs) y archivo logs/medimagen.log si se puede escribir."""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

NOMBRE = "medimagen"


def configurar_logger(debug=False):
    logger = logging.getLogger(NOMBRE)
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.propagate = False
    formato = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    consola = logging.StreamHandler(sys.stdout)
    consola.setFormatter(formato)
    logger.addHandler(consola)

    try:
        carpeta = Path(__file__).resolve().parent.parent / "logs"
        carpeta.mkdir(exist_ok=True)
        archivo = RotatingFileHandler(carpeta / "medimagen.log", maxBytes=1_000_000,
                                      backupCount=5, encoding="utf-8")
        archivo.setFormatter(formato)
        logger.addHandler(archivo)
    except OSError:
        logger.warning("No se puede escribir en logs/: se registra solo en consola")
    return logger


def obtener_logger(nombre=None):
    return logging.getLogger(f"{NOMBRE}.{nombre}" if nombre else NOMBRE)