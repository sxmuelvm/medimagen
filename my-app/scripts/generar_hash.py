"""Genera el hash de una contrasena para guardarlo en usuario.password_hash.

Uso (desde la carpeta my-app):  python scripts/generar_hash.py
"""
import getpass
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.security import hashear_clave  # noqa: E402

if __name__ == "__main__":
    clave = getpass.getpass("Contraseña: ")
    if not clave:
        sys.exit("No escribiste ninguna contraseña.")
    print(hashear_clave(clave))