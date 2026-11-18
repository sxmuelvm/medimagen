"""Inicio y cierre de sesion, bloqueo de cuentas y cambio obligatorio de contrasena."""
import pytest

from config import Config
from conftest import CLAVE, USUARIOS, sql, sql_escribir, texto

ROLES = ["admin", "recepcion", "medico", "imagenologia", "laboratorio", "paciente"]


@pytest.mark.parametrize("rol", ROLES)
def test_login_correcto_de_cada_rol(anonimo, rol):
    r = anonimo.login(USUARIOS[rol])
    assert r.status_code == 302 and r.headers["Location"].endswith("/inicio")
    assert anonimo.get("/inicio").status_code == 200


def test_clave_incorrecta_y_cedula_inexistente_dan_el_mismo_mensaje(anonimo):
    mala = anonimo.login(USUARIOS["paciente"], "clave-equivocada-1")
    inexistente = anonimo.login("0999999999", "clave-equivocada-1")
    assert mala.status_code == 401 and inexistente.status_code == 401
    assert "incorrectas" in texto(mala)
    # no se puede saber si la cedula existe: el aviso es identico
    aviso = lambda r: texto(r).split("incorrectas")[0][-40:]
    assert aviso(mala) == aviso(inexistente)


@pytest.mark.parametrize("cedula", ["", "abc", "12345", "' OR '1'='1", "0301100001'--", "03011000011", "030110000"])
def test_cedulas_mal_formadas_no_entran(anonimo, cedula):
    assert anonimo.login(cedula, CLAVE).status_code == 401


def test_clave_vacia_o_larguisima_no_entra(anonimo):
    assert anonimo.login(USUARIOS["paciente"], "").status_code == 401
    assert anonimo.login(USUARIOS["paciente"], "a" * 5000).status_code == 401


def test_login_sin_csrf_se_rechaza(anonimo):
    r = anonimo.post("/login", {"cedula": USUARIOS["paciente"], "clave": CLAVE}, csrf=False)
    assert r.status_code == 400


def test_login_registra_accesos_exitosos_y_fallidos(anonimo):
    antes = sql("SELECT COUNT(*) AS n FROM auditoria_acceso WHERE cedula_intento = %s", (USUARIOS["paciente"],), uno=True)["n"]
    anonimo.login(USUARIOS["paciente"], "mala-clave-9")
    anonimo.login(USUARIOS["paciente"])
    filas = sql("""SELECT resultado FROM auditoria_acceso WHERE cedula_intento = %s
                   ORDER BY id_acceso DESC LIMIT 2""", (USUARIOS["paciente"],))
    assert [f["resultado"] for f in filas] == ["exitoso", "fallido"]
    assert sql("SELECT COUNT(*) AS n FROM auditoria_acceso WHERE cedula_intento = %s", (USUARIOS["paciente"],), uno=True)["n"] == antes + 2


def test_logout(entrar):
    c = entrar("paciente")
    assert c.get("/logout").status_code == 405               # solo por POST
    r = c.post("/logout")
    assert r.status_code == 302 and "/login" in r.headers["Location"]
    assert c.get("/inicio").status_code == 302                # ya no hay sesion
    ultimo = sql("SELECT resultado FROM auditoria_acceso WHERE cedula_intento = %s ORDER BY id_acceso DESC LIMIT 1",
                 (USUARIOS["paciente"],), uno=True)
    assert ultimo["resultado"] == "cierre_sesion"


def test_logout_sin_csrf_se_rechaza(entrar):
    assert entrar("paciente").post("/logout", csrf=False).status_code == 400


def test_quien_ya_inicio_sesion_no_ve_el_login(entrar):
    r = entrar("paciente").get("/login")
    assert r.status_code == 302 and r.headers["Location"].endswith("/inicio")


def test_raiz_y_salud(anonimo):
    assert anonimo.get("/").status_code == 302
    r = anonimo.get("/salud")
    assert r.status_code == 200 and r.get_json() == {"estado": "ok"}


def test_bloqueo_tras_intentos_fallidos(anonimo, restablecer):
    cedula = USUARIOS["victima"]
    try:
        for _ in range(Config.MAX_INTENTOS):
            assert anonimo.login(cedula, "mala-clave-9").status_code == 401
        fila = sql("SELECT intentos_fallidos, bloqueado_hasta IS NOT NULL AS bloqueado FROM usuario WHERE cedula = %s",
                   (cedula,), uno=True)
        assert fila["bloqueado"] == 1
        # con la clave CORRECTA tampoco entra mientras dure el bloqueo (y el mensaje no lo delata)
        r = anonimo.login(cedula, CLAVE)
        assert r.status_code == 401 and "incorrectas" in texto(r)
        assert sql("SELECT resultado FROM auditoria_acceso WHERE cedula_intento = %s ORDER BY id_acceso DESC LIMIT 1",
                   (cedula,), uno=True)["resultado"] == "bloqueado"
    finally:
        restablecer("victima")


def test_un_acierto_reinicia_los_intentos_fallidos(anonimo, restablecer):
    cedula = USUARIOS["victima"]
    try:
        anonimo.login(cedula, "mala-clave-9")
        anonimo.login(cedula, "mala-clave-8")
        assert sql("SELECT intentos_fallidos AS n FROM usuario WHERE cedula = %s", (cedula,), uno=True)["n"] == 2
        assert anonimo.login(cedula).status_code == 302
        assert sql("SELECT intentos_fallidos AS n FROM usuario WHERE cedula = %s", (cedula,), uno=True)["n"] == 0
    finally:
        restablecer("victima")


def test_usuario_inactivo_no_entra(anonimo, restablecer):
    cedula = USUARIOS["victima"]
    try:
        sql_escribir("UPDATE usuario SET estado = 'inactivo' WHERE cedula = %s", (cedula,))
        r = anonimo.login(cedula)
        assert r.status_code == 401 and "inactiva" in texto(r)
    finally:
        restablecer("victima")


def test_sesion_abierta_se_invalida_si_desactivan_al_usuario(entrar, restablecer):
    c = entrar("victima")
    assert c.get("/inicio").status_code == 200
    try:
        sql_escribir("UPDATE usuario SET estado = 'inactivo' WHERE cedula = %s", (USUARIOS["victima"],))
        r = c.get("/inicio")
        assert r.status_code == 302 and "/login" in r.headers["Location"]
    finally:
        restablecer("victima")


def test_cambio_de_clave_obligatorio(anonimo, restablecer):
    cedula = USUARIOS["victima"]
    try:
        sql_escribir("UPDATE usuario SET cambio_clave_obligatorio = 1 WHERE cedula = %s", (cedula,))
        r = anonimo.login(cedula)
        assert r.status_code == 302 and r.headers["Location"].endswith("/perfil/clave")
        # mientras no cambie la clave, todo lo demas lo devuelve a esa pantalla
        for url in ("/inicio", "/historial/", "/perfil/"):
            asalto = anonimo.get(url)
            assert asalto.status_code == 302 and asalto.headers["Location"].endswith("/perfil/clave")
        assert anonimo.get("/perfil/clave").status_code == 200

        def cambiar(actual, nueva, conf=None):
            return anonimo.post("/perfil/clave", {"clave_actual": actual, "clave_nueva": nueva,
                                                  "clave_confirmacion": nueva if conf is None else conf})

        assert cambiar("otra-clave-1", "NuevaClave2026").status_code == 400          # actual incorrecta
        assert cambiar(CLAVE, "NuevaClave2026", "distinta1").status_code == 400         # confirmacion distinta
        assert cambiar(CLAVE, "corta1").status_code == 400                              # muy corta
        assert cambiar(CLAVE, "sololetrasaqui").status_code == 400                      # sin numeros
        assert cambiar(CLAVE, "12345678901").status_code == 400                         # sin letras
        assert cambiar(CLAVE, CLAVE).status_code == 400                                 # igual a la actual
        assert cambiar(CLAVE, cedula).status_code == 400                                # igual a la cedula
        ok = cambiar(CLAVE, "NuevaClave2026")
        assert ok.status_code == 302 and ok.headers["Location"].endswith("/inicio")
        assert anonimo.get("/inicio").status_code == 200
        # la clave vieja ya no sirve y la nueva si
        otro = type(anonimo)(anonimo.c.application)
        assert otro.login(cedula, CLAVE).status_code == 401
        assert otro.login(cedula, "NuevaClave2026").status_code == 302
        assert sql("SELECT cambio_clave_obligatorio AS c FROM usuario WHERE cedula = %s", (cedula,), uno=True)["c"] == 0
        assert sql("SELECT password_hash FROM usuario WHERE cedula = %s", (cedula,), uno=True)["password_hash"].startswith("pbkdf2:sha256:")
    finally:
        restablecer("victima")


def test_cambiar_clave_sin_csrf_se_rechaza(entrar):
    c = entrar("victima")
    r = c.post("/perfil/clave", {"clave_actual": CLAVE, "clave_nueva": "NuevaClave2026",
                                 "clave_confirmacion": "NuevaClave2026"}, csrf=False)
    assert r.status_code == 400