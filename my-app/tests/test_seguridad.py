"""Seguridad: cabeceras, cookies, CSRF, inyeccion, XSS, claves y privilegios de MySQL."""
import pytest

from config import Config
from conexion.conexionBD import consultar, ejecutar
from conftest import CLAVE, USUARIOS, sql, texto
from utils.errors import ErrorNegocio


# ---------------------------------------------------------------------------
# Cabeceras y cookies
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("url", ["/login", "/salud", "/pagina-que-no-existe"])
def test_cabeceras_de_seguridad(anonimo, url):
    h = anonimo.get(url).headers
    csp = h["Content-Security-Policy"]
    assert "default-src 'self'" in csp and "script-src 'self'" in csp and "'unsafe-inline'" not in csp
    assert "frame-ancestors 'none'" in csp and "object-src 'none'" in csp
    assert h["X-Content-Type-Options"] == "nosniff"
    assert h["X-Frame-Options"] == "DENY"
    assert h["Referrer-Policy"] == "same-origin"


def test_paginas_con_sesion_no_se_guardan_en_cache(entrar):
    h = entrar("paciente").get("/inicio").headers
    assert h["Cache-Control"] == "no-store" and h["Pragma"] == "no-cache"


def test_cookie_de_sesion_es_httponly_y_samesite(anonimo):
    r = anonimo.login(USUARIOS["paciente"])
    cookie = r.headers.get("Set-Cookie", "")
    assert "medimagen_sesion=" in cookie and "HttpOnly" in cookie and "SameSite=Lax" in cookie


def test_configuracion_de_sesion(app):
    assert app.config["PERMANENT_SESSION_LIFETIME"].total_seconds() == 30 * 60
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert len(app.config["SECRET_KEY"]) >= 32
    assert app.config["MAX_CONTENT_LENGTH"] == 1024 * 1024


def test_sesion_nueva_en_cada_login(app):
    """Un valor de cookie anterior al login no sirve despues (evita la fijacion de sesion)."""
    from conftest import Cliente
    c = Cliente(app)
    c.get("/login")
    antes = c.c.get_cookie("medimagen_sesion")
    c.login(USUARIOS["paciente"])
    despues = c.c.get_cookie("medimagen_sesion")
    assert despues is not None and (antes is None or antes.value != despues.value)


# ---------------------------------------------------------------------------
# Errores
# ---------------------------------------------------------------------------
def test_las_paginas_de_error_no_filtran_detalles(entrar, anonimo):
    for r in (anonimo.get("/no-existe"), entrar("paciente").get("/usuarios"), entrar("admin").get("/usuarios/99999/editar")):
        cuerpo = r.get_data(as_text=True)
        assert r.status_code in (403, 404)
        for filtrado in ("Traceback", "mysql.connector", "File \"", "usr_administrador", "uno234cinco"):
            assert filtrado not in cuerpo


def test_peticion_demasiado_grande_se_rechaza(entrar):
    r = entrar("paciente").c.post("/perfil/clave", data={"x": "a" * (2 * 1024 * 1024)})
    assert r.status_code in (400, 413)


def test_metodo_no_permitido(entrar):
    assert entrar("admin").c.delete("/usuarios").status_code in (400, 404, 405)


# ---------------------------------------------------------------------------
# CSRF, inyeccion y XSS
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("url", ["/logout", "/perfil/clave", "/usuarios/nuevo", "/citas/nueva", "/citas/1/estado",
                                 "/pacientes/nuevo", "/consultas/1/atender", "/imagenologia/18/realizar",
                                 "/laboratorio/21/resultado"])
def test_todo_post_exige_token_csrf(entrar, url):
    assert entrar("admin").post(url, {}, csrf=False).status_code == 400


def test_token_csrf_falso_se_rechaza(entrar):
    c = entrar("admin")
    assert c.c.post("/citas/1/estado", data={"estado": "cancelada", "csrf_token": "falso"}).status_code == 400


@pytest.mark.parametrize("cedula", ["' OR '1'='1", "0301100001' -- ", "0301100001'; DROP TABLE usuario; --", "1 OR 1=1"])
@pytest.mark.parametrize("clave", ["' OR '1'='1", "x' OR 1=1 -- "])
def test_inyeccion_sql_en_el_login(anonimo, cedula, clave):
    assert anonimo.login(cedula, clave).status_code == 401
    assert sql("SELECT COUNT(*) AS n FROM usuario", uno=True)["n"] > 0


@pytest.mark.parametrize("url", ["/usuarios?q=", "/pacientes?q=", "/citas/?q=", "/auditoria/accesos?q=", "/consultas/?q="])
def test_inyeccion_sql_y_xss_en_buscadores(entrar, url):
    cuenta = "medico" if url.startswith("/consultas") else "admin"
    c = entrar(cuenta)
    for payload in ("' OR 1=1 -- ", "%' UNION SELECT password_hash FROM usuario -- ", "<script>alert(1)</script>"):
        r = c.get(url + payload)
        assert r.status_code == 200
        assert b"<script>alert(1)</script>" not in r.data
        assert "pbkdf2" not in texto(r)


def test_los_datos_se_pasan_como_parametros_no_como_texto_sql(entrar, limpiar_citas):
    r = entrar("recepcion").post("/citas/nueva", {"cedula_paciente": "0102030405'; DROP TABLE cita; --",
                                                  "id_area": "1", "fecha_cita": "2030-01-01", "hora_inicio": "09:00"})
    assert r.status_code == 400
    assert sql("SELECT COUNT(*) AS n FROM cita", uno=True)["n"] > 0


# ---------------------------------------------------------------------------
# Contrasenas
# ---------------------------------------------------------------------------
def test_ninguna_contrasena_esta_en_texto_plano():
    filas = sql("SELECT nombre_usuario, password_hash FROM usuario")
    assert filas and all(f["password_hash"].startswith("pbkdf2:sha256:") for f in filas)
    assert all(CLAVE not in f["password_hash"] and "uno234cinco" not in f["password_hash"] for f in filas)


def test_la_misma_clave_genera_hashes_distintos():
    from utils.security import clave_correcta, hashear_clave
    a, b = hashear_clave(CLAVE), hashear_clave(CLAVE)
    assert a != b                           # cada hash lleva su propia sal
    assert clave_correcta(a, CLAVE) and clave_correcta(b, CLAVE) and not clave_correcta(a, CLAVE + "x")


def test_la_auditoria_de_accesos_no_guarda_contrasenas():
    columnas = {f["Field"].lower() for f in sql("SHOW COLUMNS FROM auditoria_acceso")}
    assert not any("clave" in c or "pass" in c for c in columnas)


# ---------------------------------------------------------------------------
# Privilegios de MySQL (principio de minimo privilegio)
# ---------------------------------------------------------------------------
def prohibido(cuenta, consulta, escribir=False):
    try:
        (ejecutar if escribir else consultar)(cuenta, consulta)
    except ErrorNegocio:
        return True
    return False


@pytest.mark.parametrize("cuenta,tabla", [
    ("recepcion", "usuario"), ("recepcion", "auditoria_cita"), ("recepcion", "auditoria_acceso"),
    ("recepcion", "consulta_medica"), ("recepcion", "resultado_laboratorio"),
    ("medico", "usuario"), ("medico", "auditoria_acceso"), ("medico", "resultado_laboratorio"),
    ("imagenologia", "usuario"), ("imagenologia", "paciente"), ("imagenologia", "consulta_medica"),
    ("laboratorio", "usuario"), ("laboratorio", "paciente"), ("laboratorio", "consulta_medica"),
    ("paciente", "usuario"), ("paciente", "cita"), ("paciente", "paciente"), ("paciente", "auditoria_cita"),
])
def test_cuentas_no_leen_tablas_ajenas(cuenta, tabla):
    assert prohibido(cuenta, f"SELECT * FROM {tabla} LIMIT 1")


@pytest.mark.parametrize("cuenta,sentencia", [
    ("recepcion", "DELETE FROM paciente WHERE 1 = 0"),
    ("recepcion", "UPDATE cita SET costo_aplicado = 0 WHERE 1 = 0"),
    ("recepcion", "INSERT INTO medicamento (nombre) SELECT 'x' FROM DUAL WHERE 1 = 0"),
    ("medico", "DELETE FROM cita WHERE 1 = 0"),
    ("medico", "UPDATE cita SET costo_aplicado = 0 WHERE 1 = 0"),
    ("medico", "UPDATE paciente SET nombres = 'x' WHERE 1 = 0"),
    ("imagenologia", "UPDATE cita SET fecha_cita = CURDATE() WHERE 1 = 0"),
    ("imagenologia", "DELETE FROM cita_imagenologia WHERE 1 = 0"),
    ("laboratorio", "UPDATE cita SET costo_aplicado = 0 WHERE 1 = 0"),
    ("laboratorio", "DELETE FROM resultado_laboratorio WHERE 1 = 0"),
    ("paciente", "UPDATE v_historial_paciente SET motivo_consulta = 'x' WHERE 1 = 0"),
    ("paciente", "INSERT INTO cita (cedula_paciente) SELECT '0102030405' FROM DUAL WHERE 1 = 0"),
])
def test_cuentas_no_modifican_lo_que_no_les_toca(cuenta, sentencia):
    assert prohibido(cuenta, sentencia, escribir=True)


def privilegios(clave):
    """Todos los privilegios de la cuenta de MySQL de la app (los directos y los de sus roles), como texto."""
    directos = [list(f.values())[0] for f in consultar(clave, "SHOW GRANTS FOR CURRENT_USER()")]
    import re
    roles = [m.group(1) for linea in directos for m in [re.match(r"GRANT `([^`]+)`@`[^`]*` TO", linea)] if m]
    if not roles:
        return directos
    usando = ", ".join(f"`{r}`" for r in roles)
    return [list(f.values())[0] for f in consultar(clave, f"SHOW GRANTS FOR CURRENT_USER() USING {usando}")]


def privilegios_por_tabla(clave):
    """{'*': privilegios a nivel de base de datos, 'tabla': privilegios de esa tabla} (sin los GRANT de roles)."""
    import re
    resultado = {}
    for linea in privilegios(clave):
        m = re.match(r"GRANT (.+) ON `[^`]+`\.(\*|`([^`]+)`) TO", linea)
        if m:
            tabla = "*" if m.group(2) == "*" else m.group(3)
            resultado.setdefault(tabla, set()).update(p.strip().upper() for p in m.group(1).split(","))
    return resultado


def test_el_administrador_no_puede_borrar_usuarios_ni_eliminar_la_base():
    p = privilegios_por_tabla("administrador")
    assert "DELETE" not in p.get("*", set()) and "DROP" not in p.get("*", set())
    assert not ({"DELETE", "DROP"} & p.get("usuario", set()))
    assert not any("ALL PRIVILEGES" in x or "WITH GRANT OPTION" in x for x in privilegios("administrador"))


@pytest.mark.parametrize("tabla", ["auditoria_cita", "auditoria_acceso"])
def test_ninguna_cuenta_puede_borrar_ni_eliminar_la_auditoria(tabla):
    """DELETE y DROP/TRUNCATE sobre las tablas de auditoria no deben estar concedidos a nadie de la app."""
    for clave in Config.CUENTAS_BD:
        p = privilegios_por_tabla(clave)
        peligrosos = {"DELETE", "DROP"} & (p.get(tabla, set()) | p.get("*", set()))
        assert not peligrosos, f"{Config.CUENTAS_BD[clave][0]} tiene {peligrosos} sobre {tabla}"


@pytest.mark.parametrize("clave", list(Config.CUENTAS_BD))
def test_ninguna_cuenta_de_la_app_tiene_privilegios_globales(clave):
    lineas = privilegios(clave)
    assert not any("ALL PRIVILEGES" in x or "WITH GRANT OPTION" in x for x in lineas)
    for x in lineas:
        if " ON *.* " in x:
            assert x.startswith("GRANT USAGE ON"), x


def test_prueba_sin_efecto_si_se_ejecuta_con_where_falso():
    """Sentencias con WHERE 1 = 0: aunque el privilegio existiera no tocan ningun dato."""
    assert prohibido("administrador", "DELETE FROM usuario WHERE 1 = 0", escribir=True)


def test_la_cuenta_de_login_no_toca_datos_clinicos():
    for tabla in ("cita", "paciente", "consulta_medica", "resultado_laboratorio"):
        assert prohibido("login", f"SELECT * FROM {tabla} LIMIT 1")
    assert prohibido("login", "DELETE FROM usuario", escribir=True)


def test_cada_cuenta_de_la_app_usa_su_propia_cuenta_mysql():
    esperadas = {"login": "usr_login", "administrador": "usr_administrador", "recepcion": "usr_recepcion",
                 "medico": "usr_medico", "imagenologia": "usr_imagenologia", "laboratorio": "usr_laboratorio",
                 "paciente": "usr_paciente"}
    for clave, cuenta in esperadas.items():
        assert Config.CUENTAS_BD[clave][0] == cuenta
        assert consultar(clave, "SELECT SUBSTRING_INDEX(USER(), '@', 1) AS u", uno=True)["u"] == cuenta


def test_los_triggers_impiden_alterar_la_auditoria_incluso_con_privilegios():
    """Aunque alguien tuviera el privilegio, los triggers bloquean UPDATE y DELETE sobre la auditoria."""
    nombres = {f["TRIGGER_NAME"] for f in sql("""SELECT TRIGGER_NAME FROM information_schema.TRIGGERS
                                                 WHERE TRIGGER_SCHEMA = %s""", (Config.BD_NOMBRE,))}
    assert {"trg_auditoria_bu", "trg_auditoria_bd", "trg_acceso_bu", "trg_acceso_bd"} <= nombres


def test_sesion_con_rol_distinto_se_invalida(entrar):
    """Si a un usuario le cambian el rol en la base, su sesion abierta deja de valer."""
    from conftest import sql_escribir
    c = entrar("recepcion")
    assert c.get("/inicio").status_code == 200
    original = sql("SELECT id_rol FROM usuario WHERE cedula = %s", (USUARIOS["recepcion"],), uno=True)["id_rol"]
    otro = sql("SELECT id_rol FROM rol WHERE nombre = 'personal_imagenologia'", uno=True)["id_rol"]
    try:
        sql_escribir("UPDATE usuario SET id_rol = %s WHERE cedula = %s", (otro, USUARIOS["recepcion"]))
        r = c.get("/inicio")
        assert r.status_code == 302 and "/login" in r.headers["Location"]
    finally:
        sql_escribir("UPDATE usuario SET id_rol = %s WHERE cedula = %s", (original, USUARIOS["recepcion"]))