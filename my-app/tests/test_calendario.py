"""Calendario semanal: cada rol ve solo lo suyo, recepcion agenda desde el y el paciente solo ve y cancela."""
import json
import re

import pytest

from conftest import CEDULAS, USUARIOS, sql, texto

ROLES = ["admin", "recepcion", "medico", "imagenologia", "laboratorio", "paciente"]


@pytest.fixture
def cita_lab(entrar, limpiar_citas, fecha_laborable):
    """Una cita de laboratorio del paciente de ejemplo, en una fecha futura."""
    dia = fecha_laborable(12)
    r = entrar("recepcion").post("/citas/nueva", {
        "cedula_paciente": CEDULAS["paciente"], "id_area": "3", "id_medico_solicitante": "1",
        "id_subtipo": "LAB-03", "id_recurso": "", "fecha_cita": dia, "hora_inicio": "10:00"})
    assert r.status_code == 302, texto(r)[:300]
    id_cita = int(re.search(r"/citas/(\d+)$", r.headers["Location"]).group(1))
    limpiar_citas.append(id_cita)
    return id_cita, dia


def semana(cliente, dia, **filtros):
    q = "&".join(f"{k}={v}" for k, v in {"fecha": dia, **filtros}.items())
    r = cliente.get(f"/calendario/datos?{q}")
    assert r.status_code == 200, texto(r)[:300]
    return json.loads(r.get_data(as_text=True))


def test_la_semana_empieza_en_lunes_y_termina_en_viernes(entrar, fecha_laborable):
    datos = semana(entrar("recepcion"), fecha_laborable(12))
    assert datos["lunes"] < datos["viernes"] and datos["primera"] == 7 and datos["ultima"] == 17
    assert datos["anterior"] < datos["lunes"] < datos["siguiente"]


def test_una_fecha_invalida_muestra_la_semana_actual(entrar):
    r = entrar("paciente").get("/calendario/datos?fecha=no-es-fecha")
    assert r.status_code == 200 and json.loads(r.get_data(as_text=True))["hoy"]


@pytest.mark.parametrize("rol", ROLES)
def test_todos_los_roles_abren_el_calendario(entrar, rol, fecha_laborable):
    c = entrar(rol)
    assert c.get("/calendario/").status_code == 200
    assert "citas" in semana(c, fecha_laborable(12))


def test_sin_sesion_no_hay_calendario(anonimo):
    assert anonimo.get("/calendario/").status_code == 302
    assert anonimo.get("/calendario/datos").status_code == 302


def test_recepcion_ve_la_cita_con_paciente_y_medico(entrar, cita_lab):
    id_cita, dia = cita_lab
    citas = semana(entrar("recepcion"), dia)["citas"]
    c = next(x for x in citas if x["id_cita"] == id_cita)
    assert c["hora"] == "10:00" and c["hora_fin"] == "11:00" and c["area"] == 3
    assert c["cedula"] == CEDULAS["paciente"] and c["medico"] and c["paciente"]
    assert any(a["texto"] == "Ver detalle" for a in c["acciones"])
    assert not any(a.get("metodo") == "post" for a in c["acciones"])        # recepcion no cancela desde aqui


def test_el_paciente_solo_ve_sus_citas_y_puede_cancelar(entrar, cita_lab):
    id_cita, dia = cita_lab
    citas = semana(entrar("paciente"), dia)["citas"]
    assert id_cita in [x["id_cita"] for x in citas]
    assert {x["cedula"] for x in citas} == {CEDULAS["paciente"]}
    mia = next(x for x in citas if x["id_cita"] == id_cita)
    assert [a["texto"] for a in mia["acciones"]] == ["Cancelar mi cita"]


def test_otro_paciente_no_ve_la_cita_ajena(entrar, cita_lab):
    id_cita, dia = cita_lab
    citas = semana(entrar("paciente2"), dia)["citas"]
    assert id_cita not in [x["id_cita"] for x in citas]
    assert all(x["cedula"] == CEDULAS["paciente2"] for x in citas)


def test_cada_rol_solo_ve_su_area(entrar, cita_lab):
    id_cita, dia = cita_lab
    assert id_cita in [x["id_cita"] for x in semana(entrar("laboratorio"), dia)["citas"]]
    assert id_cita not in [x["id_cita"] for x in semana(entrar("imagenologia"), dia)["citas"]]
    assert all(x["area"] == 1 for x in semana(entrar("medico"), dia)["citas"])
    assert id_cita not in [x["id_cita"] for x in semana(entrar("medico"), dia)["citas"]]


def test_el_filtro_de_area_de_recepcion(entrar, cita_lab):
    id_cita, dia = cita_lab
    c = entrar("recepcion")
    assert id_cita in [x["id_cita"] for x in semana(c, dia, id_area=3)["citas"]]
    assert id_cita not in [x["id_cita"] for x in semana(c, dia, id_area=1)["citas"]]


def test_el_medico_solo_ve_sus_consultas(entrar, limpiar_citas, fecha_laborable):
    dia = fecha_laborable(13)
    mi_medico = sql("""SELECT m.id_medico FROM usuario u JOIN medico m ON m.cedula = u.cedula
                       WHERE u.nombre_usuario = %s""", (USUARIOS["medico"],), uno=True)["id_medico"]
    otro = sql("SELECT id_medico FROM medico WHERE id_medico <> %s AND estado = 'activo' LIMIT 1", (mi_medico,), uno=True)["id_medico"]
    for medico, hora in ((mi_medico, "08:00"), (otro, "09:00")):
        r = entrar("recepcion").post("/citas/nueva", {"cedula_paciente": CEDULAS["paciente2"], "id_area": "1",
                                                      "id_medico": str(medico), "fecha_cita": dia, "hora_inicio": hora})
        assert r.status_code == 302, texto(r)[:300]
        limpiar_citas.append(int(re.search(r"/citas/(\d+)$", r.headers["Location"]).group(1)))
    citas = semana(entrar("medico"), dia)["citas"]
    assert citas and all(x["id_medico"] == mi_medico for x in citas)
    assert any(a["texto"] == "Atender consulta" for x in citas for a in x["acciones"])


def test_agendar_desde_el_calendario_llena_el_formulario(entrar, fecha_laborable):
    dia = fecha_laborable(20)
    r = entrar("recepcion").get(f"/citas/nueva?cedula={CEDULAS['paciente']}&fecha_cita={dia}&hora_inicio=15:00&id_area=1&id_medico=1")
    html = texto(r)
    assert r.status_code == 200 and f'value="{dia}"' in html and 'value="15:00" selected' in html
    # al buscar al paciente primero, lo elegido en el calendario se conserva
    sin_paciente = texto(entrar("recepcion").get(f"/citas/nueva?fecha_cita={dia}&hora_inicio=15:00"))
    assert f'name="fecha_cita" value="{dia}"' in sin_paciente


def test_el_paciente_no_puede_agendar(entrar, fecha_laborable):
    c = entrar("paciente")
    assert c.get("/citas/nueva").status_code == 403
    assert c.post("/citas/nueva", {"cedula_paciente": CEDULAS["paciente"], "id_area": "1", "id_medico": "1",
                                   "fecha_cita": fecha_laborable(30), "hora_inicio": "08:00"}).status_code == 403


def test_mis_citas_del_paciente_lleva_al_calendario(entrar):
    r = entrar("paciente").get("/historial/citas")
    assert r.status_code == 302 and "/calendario" in r.headers["Location"]
    assert entrar("recepcion").get("/historial/citas").status_code == 403


def test_el_menu_de_cada_rol_apunta_al_calendario(entrar):
    for rol in ROLES:
        assert "/calendario/" in texto(entrar(rol).get("/inicio")), rol


def test_la_cita_nace_confirmada_y_no_hay_boton_de_confirmar(entrar, cita_lab):
    id_cita, _ = cita_lab
    assert sql("SELECT estado FROM cita WHERE id_cita = %s", (id_cita,), uno=True)["estado"] == "confirmada"
    html = texto(entrar("recepcion").get(f"/citas/{id_cita}"))
    assert "Confirmar cita" not in html and "Cancelar cita" in html


def test_el_calendario_ya_no_ofrece_ver_como_lista(entrar):
    html = texto(entrar("recepcion").get("/calendario/"))
    assert "Ver como lista" not in html and "Nueva cita" in html
    r = entrar("recepcion").get("/citas/")
    assert r.status_code == 302 and "/calendario" in r.headers["Location"]
    assert entrar("paciente").get("/citas/").status_code == 403


# --- Busqueda de pacientes por cedula o nombre (recepcion) ---
def _buscar(cliente, q):
    r = cliente.get("/citas/pacientes?q=" + q)
    assert r.status_code == 200
    return json.loads(r.get_data(as_text=True))["pacientes"]


def test_busca_paciente_por_nombre_apellido_o_cedula(entrar):
    c = entrar("recepcion")
    nombre = sql("SELECT nombres, apellidos, cedula_paciente FROM paciente WHERE cedula_paciente = %s",
                 (CEDULAS["paciente"],), uno=True)
    primero = nombre["nombres"].split()[0]
    apellido = nombre["apellidos"].split()[0]
    for texto in (f"{primero} {apellido}", f"{apellido} {primero}", apellido.lower(), CEDULAS["paciente"][:6]):
        assert CEDULAS["paciente"] in [p["cedula_paciente"] for p in _buscar(c, texto.replace(" ", "%20"))], texto
    assert _buscar(c, "a") == []                                    # muy poco texto
    assert _buscar(c, "zzzzqqq") == []


def test_la_busqueda_de_pacientes_es_solo_para_recepcion_y_admin(entrar, anonimo):
    assert entrar("admin").get("/citas/pacientes?q=ca").status_code == 200
    for rol in ("medico", "imagenologia", "laboratorio", "paciente"):
        assert entrar(rol).get("/citas/pacientes?q=ca").status_code == 403, rol
    assert anonimo.get("/citas/pacientes?q=ca").status_code == 302


def test_la_busqueda_resiste_inyeccion_sql(entrar):
    c = entrar("recepcion")
    for payload in ("%27%20OR%201%3D1%20--", "%25", "_", "%3Cscript%3E"):
        assert c.get("/citas/pacientes?q=" + payload).status_code == 200


def test_nueva_cita_busca_por_nombre_sin_javascript(entrar, fecha_laborable):
    nombre = sql("SELECT apellidos FROM paciente WHERE cedula_paciente = %s", (CEDULAS["paciente"],), uno=True)
    apellido = nombre["apellidos"].split()[0]
    dia = fecha_laborable(20)
    html = texto(entrar("recepcion").get(f"/citas/nueva?q={apellido}&fecha_cita={dia}&hora_inicio=09:00"))
    assert f"cedula={CEDULAS['paciente']}" in html and f"fecha_cita={dia}" in html     # el enlace conserva la fecha elegida
    assert "No encontramos pacientes" in texto(entrar("recepcion").get("/citas/nueva?q=zzzzqqq"))
    # una cedula completa abre directo al paciente
    assert "Cambiar paciente" in texto(entrar("recepcion").get(f"/citas/nueva?q={CEDULAS['paciente']}"))


def test_numeros_son_cedula_de_maximo_10_digitos_y_letras_son_nombre(entrar):
    c = entrar("recepcion")
    cedula = CEDULAS["paciente"]
    # 13 digitos: solo cuentan los primeros 10, asi que igual aparece el paciente
    assert cedula in [p["cedula_paciente"] for p in _buscar(c, cedula + "999")]
    html = texto(c.get(f"/citas/nueva?q={cedula}123"))
    assert "Cambiar paciente" in html                                 # se recorto a la cedula de 10 digitos
    # con letras se busca por nombre
    apellido = sql("SELECT apellidos FROM paciente WHERE cedula_paciente = %s", (cedula,), uno=True)["apellidos"].split()[0]
    assert cedula in [p["cedula_paciente"] for p in _buscar(c, apellido)]


def test_el_boton_buscar_queda_como_respaldo_sin_javascript(entrar):
    html = texto(entrar("recepcion").get("/citas/nueva"))
    assert "buscar-paciente__boton" in html and "buscar-paciente__boton" in open("static/css/citas.css").read()


def test_el_paciente_solo_ve_el_estado_si_la_cita_esta_cancelada(entrar, cita_lab):
    id_cita, dia = cita_lab
    paciente = entrar("paciente")
    assert 'data-solo-cancelada="si"' in texto(paciente.get("/calendario/"))
    assert 'data-solo-cancelada="no"' in texto(entrar("recepcion").get("/calendario/"))
    # confirmada: el panel inicial del paciente no muestra ninguna insignia de estado
    inicio = texto(paciente.get("/inicio"))
    assert "Confirmada" not in inicio and "Pendiente" not in inicio
    # recepcion la cancela: ahora el paciente la ve como cancelada en su panel
    assert entrar("recepcion").post(f"/citas/{id_cita}/estado", {"estado": "cancelada"}).status_code == 302
    inicio = texto(paciente.get("/inicio"))
    assert "Cancelada" in inicio and "Confirmada" not in inicio
    assert "cancelada" in [c["estado"] for c in semana(paciente, dia)["citas"] if c["id_cita"] == id_cita]
