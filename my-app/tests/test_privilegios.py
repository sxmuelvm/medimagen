"""Privilegios CRUD por rol: recepcion desactiva/elimina pacientes, el administrador elimina usuarios, el medico
modifica y cancela los examenes que pidio, laboratorio elimina su resultado, imagenologia cancela examenes y el
paciente edita su contacto y cancela sus citas pendientes.

Todo lo que se crea aqui se limpia al terminar cada prueba.
"""
import datetime
import re

import pytest

from conexion.conexionBD import consultar
from conftest import CEDULAS, USUARIOS, id_usuario, sql, sql_escribir, texto
from utils.errors import ErrorNegocio

CEDULA_NUEVA = "0000000098"


def estado_cita(id_cita):
    return sql("""SELECT c.estado, COALESCE(ci.estado_procedimiento, cl.estado_examen) AS examen
                  FROM cita c LEFT JOIN cita_imagenologia ci USING (id_cita) LEFT JOIN cita_laboratorio cl USING (id_cita)
                  WHERE c.id_cita = %s""", (id_cita,), uno=True)


@pytest.fixture
def dia(fecha_laborable):
    return fecha_laborable(75)


@pytest.fixture
def paciente_nuevo():
    """Un paciente recien registrado (sin citas ni usuario). Se elimina al terminar."""
    sql_escribir("DELETE FROM usuario WHERE cedula = %s", (CEDULA_NUEVA,))
    sql_escribir("DELETE FROM paciente WHERE cedula_paciente = %s", (CEDULA_NUEVA,))
    sql_escribir("""INSERT INTO paciente (cedula_paciente, nombres, apellidos, fecha_nacimiento, sexo, telefono, correo)
                    VALUES (%s, 'Prueba', 'Privilegios', '1990-01-01', 'M', '0999999999', 'privilegios@prueba.ec')""",
                 (CEDULA_NUEVA,))
    yield CEDULA_NUEVA
    sql_escribir("DELETE FROM usuario WHERE cedula = %s", (CEDULA_NUEVA,))
    sql_escribir("DELETE FROM paciente WHERE cedula_paciente = %s", (CEDULA_NUEVA,))


@pytest.fixture
def examen_de(entrar, limpiar_citas, dia):
    """examen_de('recepcion', cedula, 'RM-02', medico=1, hora='08:00') -> id de una cita de examen nueva."""
    def _crear(rol, cedula, subtipo, medico=1, hora="08:00", equipo="7"):
        area = 3 if subtipo.startswith("LAB") else 2
        datos = {"cedula_paciente": cedula, "id_area": str(area), "id_medico_solicitante": str(medico),
                 "id_subtipo": subtipo, "id_recurso": "" if area == 3 else equipo,
                 "fecha_cita": dia, "hora_inicio": hora}
        if rol == "medico":         # el medico pide el examen por su propia pantalla (el solicitante es el)
            datos = {k: v for k, v in datos.items() if k not in ("id_area", "id_medico_solicitante")}
            r = entrar(rol).post("/consultas/examenes/nuevo", datos)
            id_cita = int(re.search(r"cita=(\d+)", r.headers.get("Location", "")).group(1))
        else:
            r = entrar(rol).post("/citas/nueva", datos)
            assert r.status_code == 302, texto(r)[:300]
            id_cita = int(re.search(r"/citas/(\d+)$", r.headers["Location"]).group(1))
        limpiar_citas.append(id_cita)
        return id_cita
    return _crear


# ---------------------------------------------------------------------------
# 1. Recepcion: desactivar y eliminar pacientes
# ---------------------------------------------------------------------------
def test_recepcion_desactiva_y_reactiva_un_paciente(entrar, paciente_nuevo):
    c = entrar("recepcion")
    assert c.post(f"/pacientes/{paciente_nuevo}/estado", {"estado": "inactivo"}).status_code == 302
    assert sql("SELECT estado FROM paciente WHERE cedula_paciente = %s", (paciente_nuevo,), uno=True)["estado"] == "inactivo"
    assert c.post(f"/pacientes/{paciente_nuevo}/estado", {"estado": "activo"}).status_code == 302
    assert sql("SELECT estado FROM paciente WHERE cedula_paciente = %s", (paciente_nuevo,), uno=True)["estado"] == "activo"
    assert "no es válido" in texto(c.post(f"/pacientes/{paciente_nuevo}/estado", {"estado": "xx"}, follow_redirects=True))


def test_al_desactivar_un_paciente_se_desactiva_su_usuario(entrar, restablecer):
    try:
        entrar("recepcion").post(f"/pacientes/{CEDULAS['victima']}/estado", {"estado": "inactivo"})
        assert sql("SELECT estado FROM usuario WHERE nombre_usuario = %s", (USUARIOS["victima"],), uno=True)["estado"] == "inactivo"
    finally:
        sql_escribir("UPDATE paciente SET estado = 'activo' WHERE cedula_paciente = %s", (CEDULAS["victima"],))
        restablecer("victima")


def test_recepcion_elimina_un_paciente_sin_citas(entrar, paciente_nuevo):
    r = entrar("recepcion").post(f"/pacientes/{paciente_nuevo}/eliminar")
    assert r.status_code == 302
    assert sql("SELECT 1 AS x FROM paciente WHERE cedula_paciente = %s", (paciente_nuevo,), uno=True) is None


def test_recepcion_no_elimina_pacientes_con_citas_ni_con_usuario(entrar):
    c = entrar("recepcion")
    r = c.post(f"/pacientes/{CEDULAS['paciente']}/eliminar", follow_redirects=True)      # tiene citas y usuario
    assert "Desactívalo" in texto(r)
    assert sql("SELECT 1 AS x FROM paciente WHERE cedula_paciente = %s", (CEDULAS["paciente"],), uno=True)


def test_recepcion_no_elimina_un_paciente_con_usuario_aunque_no_tenga_citas(entrar, paciente_nuevo):
    sql_escribir("""INSERT INTO usuario (id_rol, cedula, nombres, apellidos, nombre_usuario, correo,
                                         password)
                    SELECT id_rol, %s, 'Prueba', 'Privilegios', 'privprueba', 'privilegios@prueba.ec', 'x'
                    FROM rol WHERE nombre = 'paciente'""", (paciente_nuevo,))
    r = entrar("recepcion").post(f"/pacientes/{paciente_nuevo}/eliminar", follow_redirects=True)
    assert "usuario" in texto(r)
    assert sql("SELECT 1 AS x FROM paciente WHERE cedula_paciente = %s", (paciente_nuevo,), uno=True)


# ---------------------------------------------------------------------------
# 2. Administrador: eliminar usuarios
# ---------------------------------------------------------------------------
def test_admin_elimina_un_usuario_que_nunca_se_uso(entrar, paciente_nuevo):
    admin = entrar("admin")
    r = admin.post("/usuarios/nuevo", {"id_rol": str(sql("SELECT id_rol FROM rol WHERE nombre = 'paciente'", uno=True)["id_rol"]),
                                       "id_perfil": paciente_nuevo})
    assert r.status_code in (200, 302), texto(r)[:300]
    nuevo = sql("SELECT id_usuario FROM usuario WHERE cedula = %s", (paciente_nuevo,), uno=True)["id_usuario"]
    assert admin.post(f"/usuarios/{nuevo}/eliminar").status_code == 302
    assert sql("SELECT 1 AS x FROM usuario WHERE id_usuario = %s", (nuevo,), uno=True) is None


def test_admin_no_elimina_un_usuario_con_actividad_y_se_le_ofrece_desactivar(entrar):
    admin = entrar("admin")
    objetivo = id_usuario("recepcion")              # ya registro citas: la base impide eliminarlo
    r = admin.post(f"/usuarios/{objetivo}/eliminar", follow_redirects=True)
    assert "Desactívalo" in texto(r)
    assert sql("SELECT 1 AS x FROM usuario WHERE id_usuario = %s", (objetivo,), uno=True)


def test_admin_no_puede_eliminarse_a_si_mismo(entrar):
    admin = entrar("admin")
    r = admin.post(f"/usuarios/{id_usuario('admin')}/eliminar", follow_redirects=True)
    assert "No puedes eliminar tu propia cuenta" in texto(r)


def test_eliminar_un_usuario_inexistente_da_404(entrar):
    assert entrar("admin").post("/usuarios/999999/eliminar").status_code == 404


def test_el_admin_tiene_delete_sobre_usuario_pero_no_drop():
    from test_seguridad import privilegios_por_tabla
    p = privilegios_por_tabla("administrador")
    assert "DELETE" in p["usuario"] and "DROP" not in p["usuario"]


# ---------------------------------------------------------------------------
# 3. Medico: modificar y cancelar los examenes que pidio
# ---------------------------------------------------------------------------
def test_el_medico_reprograma_un_examen_pendiente_que_pidio(entrar, examen_de, fecha_laborable):
    id_cita = examen_de("medico", CEDULAS["paciente"], "RM-02", medico=1)
    nueva_fecha = fecha_laborable(80)
    r = entrar("medico").post(f"/consultas/examenes/{id_cita}/editar",
                              {"fecha_cita": nueva_fecha, "hora_inicio": "10:00", "observacion": "cambio"})
    assert r.status_code == 302, texto(r)[:300]
    fila = sql("SELECT fecha_cita, hora_inicio, observacion FROM cita WHERE id_cita = %s", (id_cita,), uno=True)
    assert fila["fecha_cita"].isoformat() == nueva_fecha and fila["observacion"] == "cambio"
    assert str(fila["hora_inicio"]) == "10:00:00"


def test_el_medico_cancela_un_examen_pendiente_y_ya_no_lo_puede_tocar(entrar, examen_de):
    id_cita = examen_de("medico", CEDULAS["paciente"], "LAB-03", medico=1)
    medico = entrar("medico")
    assert medico.post(f"/consultas/examenes/{id_cita}/cancelar").status_code == 302
    assert estado_cita(id_cita) == {"estado": "cancelada", "examen": "cancelado"}
    r = medico.post(f"/consultas/examenes/{id_cita}/cancelar", follow_redirects=True)
    assert "ya no se puede cancelar" in texto(r)
    r = medico.post(f"/consultas/examenes/{id_cita}/editar", {"fecha_cita": "2099-01-05", "hora_inicio": "09:00"})
    assert r.status_code == 400


def test_el_medico_no_toca_examenes_de_otro_medico_ni_consultas(entrar, examen_de):
    ajeno = examen_de("recepcion", CEDULAS["paciente"], "LAB-03", medico=2)
    medico = entrar("medico")
    assert medico.post(f"/consultas/examenes/{ajeno}/cancelar").status_code == 404
    assert medico.get(f"/consultas/examenes/{ajeno}/editar").status_code == 404
    assert estado_cita(ajeno)["estado"] == "confirmada"
    consulta = sql("SELECT id_cita FROM cita_consulta LIMIT 1", uno=True)["id_cita"]
    assert medico.post(f"/consultas/examenes/{consulta}/cancelar").status_code == 404


def test_el_medico_no_cancela_un_examen_ya_realizado(entrar):
    hecho = sql("""SELECT cl.id_cita FROM cita_laboratorio cl JOIN medico m ON m.id_medico = cl.id_medico_solicitante
                   WHERE cl.estado_examen = 'realizado' AND m.cedula = %s LIMIT 1""", ("0000000003",), uno=True)
    if hecho is None:
        pytest.skip("El medico de ejemplo no tiene examenes realizados")
    r = entrar("medico").post(f"/consultas/examenes/{hecho['id_cita']}/cancelar", follow_redirects=True)
    assert "ya no se puede cancelar" in texto(r)


# ---------------------------------------------------------------------------
# 4. Laboratorio: eliminar un resultado propio
# ---------------------------------------------------------------------------
@pytest.fixture
def examen_de_hoy():
    """Un examen de laboratorio cuya fecha ya llego (un dia habil pasado), listo para registrarle un resultado."""
    dia = datetime.date.today() - datetime.timedelta(days=20)
    while dia.weekday() >= 5:
        dia -= datetime.timedelta(days=1)
    fila = sql_escribir("""INSERT INTO cita (cedula_paciente, id_area, id_recurso, id_usuario_registra, fecha_cita,
                                             hora_inicio, hora_fin)
                           VALUES (%s, 3, 9, %s, %s, '11:00:00', '12:00:00')""",
                        (CEDULAS["paciente"], id_usuario("admin"), dia))
    id_cita = fila["id"]
    sql_escribir("INSERT INTO cita_laboratorio (id_cita, id_medico_solicitante, id_subtipo) VALUES (%s, 1, 'LAB-03')",
                 (id_cita,))
    yield id_cita
    sql_escribir("DELETE FROM resultado_laboratorio WHERE id_cita = %s", (id_cita,))
    sql_escribir("UPDATE cita SET estado = 'cancelada' WHERE id_cita = %s", (id_cita,))
    sql_escribir("DELETE FROM cita WHERE id_cita = %s", (id_cita,))


def test_laboratorio_elimina_su_resultado_y_el_examen_queda_pendiente(entrar, examen_de_hoy):
    lab = entrar("laboratorio")
    r = lab.post(f"/laboratorio/{examen_de_hoy}/resultado", {"resultado": "Valores normales"})
    assert r.status_code == 302, texto(r)[:300]
    assert estado_cita(examen_de_hoy) == {"estado": "atendida", "examen": "realizado"}
    assert lab.post(f"/laboratorio/{examen_de_hoy}/resultado/eliminar").status_code == 302
    assert estado_cita(examen_de_hoy) == {"estado": "pendiente", "examen": "pendiente"}
    assert sql("SELECT 1 AS x FROM resultado_laboratorio WHERE id_cita = %s", (examen_de_hoy,), uno=True) is None
    assert lab.post(f"/laboratorio/{examen_de_hoy}/resultado", {"resultado": "Corregido"}).status_code == 302


def test_laboratorio_no_elimina_resultados_de_otra_persona(entrar, examen_de_hoy):
    sql_escribir("UPDATE cita SET estado = 'atendida' WHERE id_cita = %s", (examen_de_hoy,))
    sql_escribir("UPDATE cita_laboratorio SET estado_examen = 'realizado', fecha_realizacion = CURDATE() WHERE id_cita = %s", (examen_de_hoy,))
    sql_escribir("""INSERT INTO resultado_laboratorio (id_cita, registrado_por, fecha_resultado, resultado)
                    VALUES (%s, %s, CURDATE(), 'Ajeno')""", (examen_de_hoy, id_usuario("admin")))
    try:
        r = entrar("laboratorio").post(f"/laboratorio/{examen_de_hoy}/resultado/eliminar", follow_redirects=True)
        assert "tú registraste" in texto(r)
        assert sql("SELECT 1 AS x FROM resultado_laboratorio WHERE id_cita = %s", (examen_de_hoy,), uno=True)
    finally:
        sql_escribir("DELETE FROM resultado_laboratorio WHERE id_cita = %s", (examen_de_hoy,))


def test_eliminar_un_resultado_que_no_existe(entrar, examen_de_hoy):
    r = entrar("laboratorio").post(f"/laboratorio/{examen_de_hoy}/resultado/eliminar", follow_redirects=True)
    assert "no tiene resultado" in texto(r)


# ---------------------------------------------------------------------------
# 5. Imagenologia: cancelar un examen pendiente
# ---------------------------------------------------------------------------
def test_imagenologia_cancela_un_examen_pendiente(entrar, examen_de):
    id_cita = examen_de("recepcion", CEDULAS["paciente"], "RX-01", equipo="5", hora="09:00")
    img = entrar("imagenologia")
    assert img.post(f"/imagenologia/{id_cita}/cancelar").status_code == 302
    assert estado_cita(id_cita) == {"estado": "cancelada", "examen": "cancelado"}
    assert "ya no se puede cancelar" in texto(img.post(f"/imagenologia/{id_cita}/cancelar", follow_redirects=True))


def test_imagenologia_no_cancela_examenes_realizados_ni_de_otras_areas(entrar):
    img = entrar("imagenologia")
    hecho = sql("SELECT id_cita FROM cita_imagenologia WHERE estado_procedimiento = 'realizado' LIMIT 1", uno=True)
    assert "ya no se puede cancelar" in texto(img.post(f"/imagenologia/{hecho['id_cita']}/cancelar", follow_redirects=True))
    consulta = sql("SELECT id_cita FROM cita_consulta LIMIT 1", uno=True)["id_cita"]
    assert img.post(f"/imagenologia/{consulta}/cancelar").status_code == 404


# ---------------------------------------------------------------------------
# 6. Paciente: editar su contacto y cancelar sus citas
# ---------------------------------------------------------------------------
@pytest.fixture
def contacto_original():
    cedula = CEDULAS["paciente"]
    antes = sql("SELECT telefono, correo, direccion FROM paciente WHERE cedula_paciente = %s", (cedula,), uno=True)
    yield antes
    sql_escribir("UPDATE paciente SET telefono = %s, correo = %s, direccion = %s WHERE cedula_paciente = %s",
                 (antes["telefono"], antes["correo"], antes["direccion"], cedula))


def test_el_paciente_edita_solo_su_telefono_y_correo(entrar, contacto_original):
    c = entrar("paciente")
    assert c.get("/historial/mis-datos").status_code == 200
    r = c.post("/historial/mis-datos", {"telefono": "0988776655", "correo": "Nuevo.Correo@Prueba.ec",
                                        "direccion": "Av. Nueva 123"})  # la dirección se ignora
    assert r.status_code == 302, texto(r)[:300]
    fila = sql("SELECT telefono, correo, direccion FROM paciente WHERE cedula_paciente = %s",
               (CEDULAS["paciente"],), uno=True)
    assert fila["telefono"] == "0988776655" and fila["correo"] == "nuevo.correo@prueba.ec"
    assert fila["direccion"] == contacto_original["direccion"]      # la dirección no la cambia el paciente


def test_el_paciente_solo_cambia_sus_propios_datos(entrar, contacto_original):
    otro = sql("SELECT nombres, telefono FROM paciente WHERE cedula_paciente = %s", (CEDULAS["paciente2"],), uno=True)
    r = entrar("paciente").post("/historial/mis-datos", {"cedula_paciente": CEDULAS["paciente2"], "nombres": "Hackeado",
                                                         "telefono": "0911111111", "correo": "", "direccion": ""})
    assert r.status_code == 302
    assert sql("SELECT nombres, telefono FROM paciente WHERE cedula_paciente = %s", (CEDULAS["paciente2"],),
               uno=True) == otro
    assert sql("SELECT nombres FROM paciente WHERE cedula_paciente = %s", (CEDULAS["paciente"],), uno=True)["nombres"] != "Hackeado"


@pytest.mark.parametrize("datos", [
    {"telefono": "abc", "correo": "", "direccion": ""},
    {"telefono": "0999999999", "correo": "no-es-correo", "direccion": ""},
])
def test_contacto_invalido_se_rechaza(entrar, contacto_original, datos):
    antes = sql("SELECT telefono, correo FROM paciente WHERE cedula_paciente = %s", (CEDULAS["paciente"],), uno=True)
    assert entrar("paciente").post("/historial/mis-datos", datos).status_code == 400
    assert sql("SELECT telefono, correo FROM paciente WHERE cedula_paciente = %s", (CEDULAS["paciente"],), uno=True) == antes


def test_el_correo_de_otro_paciente_no_se_puede_usar(entrar, contacto_original):
    ajeno = sql("SELECT correo FROM paciente WHERE cedula_paciente = %s AND correo IS NOT NULL", (CEDULAS["paciente2"],), uno=True)
    r = entrar("paciente").post("/historial/mis-datos", {"telefono": "", "correo": ajeno["correo"], "direccion": ""})
    assert r.status_code == 400 and "ya está registrado" in texto(r)


def test_el_paciente_cancela_su_cita_pendiente(entrar, examen_de):
    id_cita = examen_de("recepcion", CEDULAS["paciente"], "LAB-03", hora="09:00")
    c = entrar("paciente")
    assert c.post(f"/historial/citas/{id_cita}/cancelar").status_code == 302
    assert estado_cita(id_cita) == {"estado": "cancelada", "examen": "cancelado"}
    assert "Solo puedes cancelar" in texto(c.post(f"/historial/citas/{id_cita}/cancelar", follow_redirects=True))


def test_el_paciente_no_cancela_citas_ajenas_ni_atendidas(entrar, examen_de):
    ajena = examen_de("recepcion", CEDULAS["paciente2"], "LAB-03", hora="10:00")
    c = entrar("paciente")
    assert "no existe" in texto(c.post(f"/historial/citas/{ajena}/cancelar", follow_redirects=True))
    assert estado_cita(ajena)["estado"] == "confirmada"
    atendida = sql("SELECT id_cita FROM cita WHERE cedula_paciente = %s AND estado = 'atendida' LIMIT 1",
                   (CEDULAS["paciente"],), uno=True)["id_cita"]
    assert "Solo puedes cancelar" in texto(c.post(f"/historial/citas/{atendida}/cancelar", follow_redirects=True))
    assert estado_cita(atendida)["estado"] == "atendida"


def test_el_paciente_sigue_sin_poder_agendar_ni_tocar_tablas():
    for sentencia in ("UPDATE paciente SET nombres = 'x' WHERE 1 = 0", "DELETE FROM cita WHERE 1 = 0",
                      "INSERT INTO cita (cedula_paciente) SELECT '0000000021' FROM DUAL WHERE 1 = 0"):
        with pytest.raises(ErrorNegocio):
            from conexion.conexionBD import ejecutar
            ejecutar("paciente", sentencia)
    assert consultar("paciente", "SELECT COUNT(*) AS n FROM v_contacto_paciente", uno=True)["n"] > 0
