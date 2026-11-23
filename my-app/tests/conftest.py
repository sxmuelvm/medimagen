"""Configuracion comun de las pruebas.

Las pruebas usan la base de datos real del .env (la misma de la aplicacion), con los datos de ejemplo cargados.
Para no depender de las contrasenas que cada quien haya cambiado, al empezar se guarda el estado de los usuarios
de prueba, se les pone una clave conocida y, al terminar, se restaura TODO como estaba.

Ejecutar desde la carpeta my-app:   pytest -v
"""
import datetime
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app as aplicacion  # noqa: E402
from conexion.conexionBD import consultar, ejecutar  # noqa: E402
from extensions import limiter  # noqa: E402
from utils.errors import ErrorNegocio  # noqa: E402
from utils.security import hashear_clave  # noqa: E402

CLAVE = "Prueba2026ok"          # clave conocida que se pone a los usuarios de prueba mientras dura la sesion

# nombre corto -> nombre_usuario del usuario de ejemplo
USUARIOS = {
    "admin": "admin",
    "recepcion": "ccriollo",
    "medico": "cmarin",
    "imagenologia": "mbajana",
    "laboratorio": "asornoza",
    "paciente": "candrade",         # Carlos Andrade
    "paciente2": "acordero",        # Ana Cordero
    "victima": "mvintimilla",       # paciente usado en pruebas que bloquean, desactivan o cambian la clave
}
# cedulas de los pacientes de ejemplo (el login ya no usa cedula, pero el historial y las citas si)
CEDULAS = {"paciente": "0000000021", "paciente2": "0000000024", "victima": "0000000022"}
COLUMNAS = "password, cambio_clave_obligatorio, intentos_fallidos, bloqueado_hasta, estado"


def sql(consulta, parametros=None, uno=False):
    """SELECT con la cuenta del administrador (para verificar lo que dejo la aplicacion en la base)."""
    return consultar("administrador", consulta, parametros, uno=uno)


def sql_escribir(consulta, parametros=None):
    return ejecutar("administrador", consulta, parametros)


def id_usuario(nombre):
    return sql("SELECT id_usuario FROM usuario WHERE nombre_usuario = %s", (USUARIOS[nombre],), uno=True)["id_usuario"]


def poner_clave_conocida(nombre_usuario):
    sql_escribir("""UPDATE usuario SET password = %s, cambio_clave_obligatorio = 0, intentos_fallidos = 0,
                    bloqueado_hasta = NULL, estado = 'activo' WHERE nombre_usuario = %s""", (HASH, nombre_usuario))


HASH = hashear_clave(CLAVE)


@pytest.fixture(scope="session", autouse=True)
def usuarios_de_prueba():
    """Guarda el estado de los usuarios de prueba, les pone clave conocida y al final lo restaura."""
    try:
        originales = {n: sql(f"SELECT {COLUMNAS} FROM usuario WHERE nombre_usuario = %s", (c,), uno=True)
                      for n, c in USUARIOS.items()}
    except ErrorNegocio as error:
        pytest.exit(f"No se pudo conectar con la base de datos: {error.mensaje}. "
                    "Revisa el .env y que MySQL este encendido.", returncode=2)
    faltan = [n for n, fila in originales.items() if fila is None]
    if faltan:
        pytest.exit(f"Faltan usuarios de ejemplo en la base: {faltan}. Carga los scripts de database/init.", returncode=2)
    for usuario in USUARIOS.values():
        poner_clave_conocida(usuario)
    yield
    for nombre, fila in originales.items():
        sql_escribir("""UPDATE usuario SET password = %s, cambio_clave_obligatorio = %s, intentos_fallidos = %s,
                         bloqueado_hasta = %s, estado = %s WHERE nombre_usuario = %s""",
                     (fila["password"], fila["cambio_clave_obligatorio"], fila["intentos_fallidos"],
                      fila["bloqueado_hasta"], fila["estado"], USUARIOS[nombre]))


@pytest.fixture(scope="session")
def app():
    aplicacion.config.update(TESTING=True)
    limiter.enabled = False
    return aplicacion


class Cliente:
    """Navegador de pruebas: mantiene la sesion y agrega solo el token CSRF a los POST."""

    def __init__(self, app):
        self.c = app.test_client()

    def token(self):
        pagina = self.c.get("/perfil/clave" if self._con_sesion() else "/login").get_data(as_text=True)
        coincide = re.search(r'name="csrf_token" value="([^"]+)"', pagina)
        return coincide.group(1) if coincide else ""

    def _con_sesion(self):
        with self.c.session_transaction() as sesion:
            return bool(sesion.get("id_usuario"))

    def login(self, nombre_usuario, clave=CLAVE):
        return self.c.post("/login", data={"nombre_usuario": nombre_usuario, "clave": clave, "csrf_token": self.token()})

    def get(self, url, **kw):
        return self.c.get(url, **kw)

    def post(self, url, datos=None, csrf=True, **kw):
        datos = dict(datos or {})
        if csrf:
            datos["csrf_token"] = self.token()
        return self.c.post(url, data=datos, **kw)


@pytest.fixture
def anonimo(app):
    return Cliente(app)


@pytest.fixture
def entrar(app):
    """entrar('admin') -> cliente con la sesion iniciada con ese usuario de ejemplo."""
    def _entrar(nombre):
        cliente = Cliente(app)
        respuesta = cliente.login(USUARIOS[nombre])
        assert respuesta.status_code == 302, f"No pudo iniciar sesion {nombre}: {respuesta.status_code}"
        return cliente
    return _entrar


@pytest.fixture
def restablecer():
    """restablecer('victima') -> deja ese usuario como al empezar la sesion de pruebas (clave conocida, activo)."""
    def _restablecer(nombre):
        poner_clave_conocida(USUARIOS[nombre])
    return _restablecer


def texto(respuesta):
    import html
    return html.unescape(respuesta.get_data(as_text=True))


@pytest.fixture
def fecha_laborable():
    """fecha_laborable(40) -> primer dia de lunes a viernes que cae a 40 dias o mas desde hoy (AAAA-MM-DD)."""
    def _fecha(dias):
        dia = datetime.date.today() + datetime.timedelta(days=dias)
        while dia.weekday() >= 5:
            dia += datetime.timedelta(days=1)
        return dia.isoformat()
    return _fecha


@pytest.fixture
def limpiar_citas():
    """Lista a la que se agregan los id de las citas que crea una prueba: al final se cancelan y se eliminan."""
    ids = []
    yield ids
    for id_cita in ids:
        sql_escribir("UPDATE cita SET estado = 'cancelada' WHERE id_cita = %s AND estado IN ('pendiente', 'confirmada')",
                     (id_cita,))
        sql_escribir("DELETE FROM cita WHERE id_cita = %s AND estado IN ('pendiente', 'cancelada')", (id_cita,))
