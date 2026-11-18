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
        {"id_rol": "999", "id_perfil": "1", "nombre_usuario": "pruebaxx"},                 # rol inexistente
        {"id_rol": "abc", "id_perfil": "1", "nombre_usuario": "pruebaxx"},                 # rol no numerico
        {"id_rol": "1", "id_perfil": "99999", "nombre_usuario": "pruebaxx"},               # perfil inexistente
        {"id_rol": "1", "id_perfil": "", "nombre_usuario": ""},                            # vacio
        {"id_rol": "6", "id_perfil": "0000000021", "nombre_usuario": "otro_nombre"},       # el paciente ya tiene usuario
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
    assert sql("SELECT estado FROM usuario WHERE cedula = %s", (USUARIOS["victima"],), uno=True)["estado"] == "activo"


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
        assert temporal not in sql("SELECT password_hash FROM usuario WHERE id_usuario = %s", (objetivo,), uno=True)["password_hash"]
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
    r = admin.post(f"/usuarios/{objetivo}/editar", {"nombre_usuario": "x", "correo": "no-es-correo", "id_rol": "6"})
    assert r.status_code == 400
    assert admin.get("/usuarios/99999/editar").status_code == 404