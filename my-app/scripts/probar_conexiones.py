"""Prueba la conexion de las 7 cuentas de MySQL que usa la aplicacion.

Uso (desde la carpeta my-app):  python scripts/probar_conexiones.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config  # noqa: E402
from conexion.conexionBD import probar_conexion  # noqa: E402
from utils.errors import ErrorNegocio  # noqa: E402

print(f"Servidor: {Config.BD_HOST}:{Config.BD_PUERTO}  Base: {Config.BD_NOMBRE}\n")
fallos = 0
for clave in Config.CUENTAS_BD:
    try:
        fila = probar_conexion(clave)
        print(f"  OK     {clave:<14} -> {fila['cuenta']}  rol activo: {fila['rol']}")
    except (ErrorNegocio, RuntimeError) as error:
        fallos += 1
        print(f"  FALLO  {clave:<14} -> {error}")

print("\nTodas las conexiones funcionan." if not fallos else f"\n{fallos} conexion(es) con problemas.")
sys.exit(1 if fallos else 0)