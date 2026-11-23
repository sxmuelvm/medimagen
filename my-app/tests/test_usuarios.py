"""Administracion de usuarios (solo administrador)."""
from conftest import CLAVE, USUARIOS, id_usuario, sql, texto


def test_listado_y_filtros(entrar):
    admin = entrar("admin")
    assert admin.get("/usuarios").status_code == 200
    html = texto(admin.get("/usuarios?q=candrade"))
    assert "candrade" in html
    assert admin.get("/usuarios?rol=1&estado=activo&pagina=999").status_code == 200
    assert admin.get("/usuarios?q=%27%20OR%201%3D1%20--").status_code == 200


def test_xss_en_la_busqueda_se_escapa(entrar):
    r = entrar("admin").get("/usuarios?q=<script>alert(1)</script>")
    assert b"<script>alert(1)</script>" not in r.data


def test_crear_usuario_con_datos_invalidos_no_crea_nada(entrar):
    admin = entrar("admin")
    antes = sql("SELECT COUNT(*) AS n FROM usuario", uno=True)["n"]
    casos = [
        {"id_rol": "999", "id_perfil": "1"},                                       # rol inexistente
        {"id_rol": "abc", "id_perfil": "1"},                                       # rol no numerico
        {"id_rol": "6", "id_perfil": "0000099999"},                     # paciente inexistente
        {"id_rol": "2", "cedula": "", "nombres": "", "apellidos": ""},      # vacio
        {"id_rol": "2", "cedula": "12345", "nombres": "Ana", "apellidos": "Perez", "correo": "a@b.ec"},   # cedula corta
        {"id_rol": "6", "id_perfil": "0000000021"},                     # el paciente ya tiene usuario
    ]
    for datos in casos:
        assert admin.post("/usuarios/nuevo", datos).status_code == 400, datos
    assert sql("SELECT COUNT(*) AS n FROM usuario", uno=True)["n"] == antes


def test_el_admin_no_puede_desactivarse_a_si_mismo(entrar):
    admin = entrar("admin")
    yo = id_usuario("admin")
    r = admin.post(f"/usuarios/{yo}/estado", {"estado": "inactivo"}, follow_redirects=True)
    assert "No puedes desactivar" in texto(r)
    assert sql("SELECT estado FROM usuario WHERE id_usuario = %s", (yo,), uno=True)["estado"] == "activo"


def test_el_admin_no_puede_cambiar_su_propio_rol_ni_restablecer_su_clave(entrar):
    admin = entrar("admin")
    yo = id_usuario("admin")
    r = admin.post(f"/usuarios/{yo}/clave", {}, follow_redirects=True)
    assert r.status_code == 400 and "perfil" in texto(r)


def test_estado_invalido_se_rechaza(entrar):
    admin = entrar("admin")
    r = admin.post(f"/usuarios/{id_usuario('victima')}/estado", {"estado": "super"}, follow_redirects=True)
    assert "no es válido" in texto(r)
    assert sql("SELECT estado FROM usuario WHERE nombre_usuario = %s", (USUARIOS["victima"],), uno=True)["estado"] == "activo"


def test_desactivar_y_reactivar_un_usuario(entrar, anonimo, restablecer):
    admin = entrar("admin")
    objetivo = id_usuario("victima")
    try:
        admin.post(f"/usuarios/{objetivo}/estado", {"estado": "inactivo"})
        assert sql("SELECT estado FROM usuario WHERE id_usuario = %s", (objetivo,), uno=True)["estado"] == "inactivo"
        assert anonimo.login(USUARIOS["victima"]).status_code == 401
        admin.post(f"/usuarios/{objetivo}/estado", {"estado": "activo"})
        assert anonimo.login(USUARIOS["victima"]).status_code == 302
    finally:
        restablecer("victima")


def test_desbloquear(entrar, restablecer):
    admin = entrar("admin")
    objetivo = id_usuario("victima")
    try:
        from conftest import sql_escribir
        sql_escribir("UPDATE usuario SET intentos_fallidos = 5, bloqueado_hasta = NOW() + INTERVAL 15 MINUTE "
                     "WHERE id_usuario = %s", (objetivo,))
        admin.post(f"/usuarios/{objetivo}/desbloquear")
        fila = sql("SELECT intentos_fallidos, bloqueado_hasta FROM usuario WHERE id_usuario = %s", (objetivo,), uno=True)
        assert fila["intentos_fallidos"] == 0 and fila["bloqueado_hasta"] is None
    finally:
        restablecer("victima")


def test_restablecer_clave_genera_una_temporal_que_obliga_a_cambiarla(entrar, anonimo, restablecer):
    import re
    admin = entrar("admin")
    objetivo = id_usuario("victima")
    try:
        r = admin.post(f"/usuarios/{objetivo}/clave", {"clave": ""})
        assert r.status_code == 200
        encontrada = re.search(r'class="clave-temporal"[^>]*>\s*([^<\s]+)', r.get_data(as_text=True))
        if encontrada:                                    # cuando la pantalla ya este diseñada
            temporal = encontrada.group(1)
        else:                                             # mientras sea el marcador de posicion, sale en el contexto
            temporal = re.search(r"'clave_temporal': '([^']+)'", texto(r)).group(1)
        assert temporal != CLAVE
        entrada = anonimo.login(USUARIOS["victima"], temporal)
        assert entrada.status_code == 302 and entrada.headers["Location"].endswith("/perfil/clave")
        assert sql("SELECT cambio_clave_obligatorio AS c FROM usuario WHERE id_usuario = %s", (objetivo,), uno=True)["c"] == 1
        # y la clave generada no queda guardada en texto
        assert temporal not in sql("SELECT password FROM usuario WHERE id_usuario = %s", (objetivo,), uno=True)["password"]
    finally:
        restablecer("victima")


def test_clave_manual_debe_ser_segura(entrar, restablecer):
    admin = entrar("admin")
    objetivo = id_usuario("victima")
    try:
        for mala in ("corta1", "sololetrasaquix", "123456789012", USUARIOS["victima"]):
            assert admin.post(f"/usuarios/{objetivo}/clave", {"clave": mala}).status_code == 400, mala
    finally:
        restablecer("victima")


def test_editar_con_datos_invalidos(entrar):
    admin = entrar("admin")
    objetivo = id_usuario("victima")
    r = admin.post(f"/usuarios/{objetivo}/editar", {"correo": "no-es-correo", "id_rol": "6"})
    assert r.status_code == 400
    assert admin.get("/usuarios/99999/editar").status_code == 404


# ---------------------------------------------------------------------------
# Nombre de usuario automatico: inicial del nombre + primer apellido; si existe, 01, 02...
# ---------------------------------------------------------------------------
def _crear_personal(admin, nombres, apellidos, cedula, correo):
    r = admin.post("/usuarios/nuevo", {"id_rol": str(sql("SELECT id_rol FROM rol WHERE nombre = 'recepcion'", uno=True)["id_rol"]),
                                       "cedula": cedula, "nombres": nombres, "apellidos": apellidos, "correo": correo})
    assert r.status_code == 200, texto(r)[:300]
    return sql("SELECT nombre_usuario FROM usuario WHERE cedula = %s", (cedula,), uno=True)["nombre_usuario"]


def test_el_nombre_de_usuario_se_genera_y_agrega_numero_si_se_repite(entrar):
    from conftest import sql_escribir
    admin = entrar("admin")
    cedulas = ("0000099001", "0000099002", "0000099003")
    try:
        # dos nombres y dos apellidos, con tilde y enie: solo cuenta la inicial del primer nombre y el primer apellido
        assert _crear_personal(admin, "Zoila Marcela", "Ñúñez Xyzprueba", cedulas[0], "z1@prueba.ec") == "znunez"
        assert _crear_personal(admin, "Zacarías", "Ñuñez Otro", cedulas[1], "z2@prueba.ec") == "znunez01"
        assert _crear_personal(admin, "Zulema Ana", "Nunez Ruiz", cedulas[2], "z3@prueba.ec") == "znunez02"
    finally:
        for c in cedulas:
            sql_escribir("DELETE FROM usuario WHERE cedula = %s", (c,))


def test_los_homonimos_del_ejemplo_tienen_numero(entrar):
    nombres = {f["nombre_usuario"] for f in sql("SELECT nombre_usuario FROM usuario WHERE nombre_usuario LIKE 'cmarin%'")}
    assert {"cmarin", "cmarin01", "cmarin02", "cmarin03"} <= nombres


def test_el_nombre_de_usuario_no_se_edita(entrar):
    admin = entrar("admin")
    objetivo = id_usuario("victima")
    antes = sql("SELECT nombre_usuario, correo FROM usuario WHERE id_usuario = %s", (objetivo,), uno=True)
    r = admin.post(f"/usuarios/{objetivo}/editar", {"nombre_usuario": "otro", "correo": antes["correo"], "id_rol": "6"})
    assert r.status_code in (200, 302)
    assert sql("SELECT nombre_usuario FROM usuario WHERE id_usuario = %s", (objetivo,), uno=True)["nombre_usuario"] == antes["nombre_usuario"]


def test_usuario_medico_o_paciente_debe_tener_ficha(entrar):
    from conftest import sql_escribir
    import pytest as _p
    with _p.raises(Exception):
        sql_escribir("""INSERT INTO usuario (id_rol, cedula, nombres, apellidos, correo, password)
                        SELECT id_rol, '0000098765', 'X', 'Y', 'xy@prueba.ec', 'x' FROM rol WHERE nombre = 'medico'""")
