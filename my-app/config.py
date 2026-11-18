"""Configuracion central de Medimagen.

Local : las variables se leen de ../.env (el .env esta en la raiz del proyecto).
Docker: no hay .env dentro de la imagen; docker-compose inyecta las variables.
"""
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")


def _entero(nombre, defecto):
    try:
        return int(os.getenv(nombre, defecto))
    except (TypeError, ValueError):
        return int(defecto)


class Config:
    # ---------- Aplicacion ----------
    ENTORNO = os.getenv("FLASK_ENV", "development")
    PRODUCCION = ENTORNO == "production"
    DEBUG = not PRODUCCION
    APP_PORT = _entero("APP_PORT", 5001)
    SECRET_KEY = os.getenv("SECRET_KEY")

    # ---------- Sesion y cookies ----------
    SESSION_COOKIE_NAME = "medimagen_sesion"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Solo se pone en True si algun dia hay HTTPS (proxy con certificado delante).
    SESSION_COOKIE_SECURE = False
    SESSION_REFRESH_EACH_REQUEST = True          # la sesion vence por inactividad
    # Cierre de sesion por inactividad: 60 minutos sin usar el sistema (se renueva con cada accion)
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=_entero("SESION_INACTIVIDAD_MIN", 60))
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024         # 1 MB por peticion

    # ---------- CSRF ----------
    WTF_CSRF_TIME_LIMIT = None                   # el token dura lo que dure la sesion

    # ---------- Limitador de intentos ----------
    # "memory://" cuenta por proceso: con 3 workers de gunicorn el limite real es mayor.
    RATELIMIT_STORAGE_URI = "memory://"
    RATELIMIT_HEADERS_ENABLED = False
    LIMITE_LOGIN = "10 per minute;60 per hour"   # solo cuentan los intentos fallidos
    LIMITE_CLAVE = "5 per minute"

    # ---------- Bloqueo de cuentas ----------
    MAX_INTENTOS = 5
    MINUTOS_BLOQUEO = 15

    # ---------- Base de datos ----------
    BD_HOST = os.getenv("DB_HOST", "localhost")
    BD_PUERTO = _entero("DB_PORT", 3306)         # 3306 en local y dentro de Docker
    BD_NOMBRE = os.getenv("DB_NAME", "medimagen")
    # 3 conexiones por cuenta y por worker: 3 workers x 3 = 9 (limite de MySQL: 10 o mas)
    BD_POOL = max(1, min(_entero("DB_POOL_SIZE", 3), 10))

    # clave interna -> (cuenta de MySQL, variable del .env con su contrasena)
    CUENTAS_BD = {
        "login": ("usr_login", "DB_PASS_LOGIN"),
        "administrador": ("usr_administrador", "DB_PASS_ADMINISTRADOR"),
        "recepcion": ("usr_recepcion", "DB_PASS_RECEPCION"),
        "medico": ("usr_medico", "DB_PASS_MEDICO"),
        "imagenologia": ("usr_imagenologia", "DB_PASS_IMAGENOLOGIA"),
        "laboratorio": ("usr_laboratorio", "DB_PASS_LABORATORIO"),
        "paciente": ("usr_paciente", "DB_PASS_PACIENTE"),
    }

    @classmethod
    def credenciales(cls, clave):
        """Devuelve (usuario, contrasena) de la cuenta de MySQL indicada."""
        if clave not in cls.CUENTAS_BD:
            raise RuntimeError(f"Cuenta de base de datos desconocida: {clave}")
        usuario, variable = cls.CUENTAS_BD[clave]
        contrasena = os.getenv(variable)
        if not contrasena:
            raise RuntimeError(f"Falta la variable {variable} en el .env")
        return usuario, contrasena

    @classmethod
    def validar(cls):
        if not cls.SECRET_KEY or len(cls.SECRET_KEY) < 32:
            raise RuntimeError("SECRET_KEY falta o es muy corta (minimo 32 caracteres). Revisa el .env")