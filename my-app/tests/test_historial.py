"""Historial del paciente: cada paciente ve solo lo suyo."""
import pytest

from conftest import USUARIOS, id_usuario, sql, texto
from controllers import historial_controller as his

A, B = "paciente", "paciente2"
URLS = ["/historial/", "/historial/citas", "/historial/recetas", "/historial/resultados"]


def cuantas(cedula):
    return sum(sql(f"""SELECT COUNT(*) AS n FROM cita c JOIN {t} d USING (id_cita)
                       WHERE c.cedula_paciente = %s""", (cedula,), uno=True)["n"]
               for t in ("cita_consulta", "cita_imagenologia", "cita_laboratorio"))


@pytest.mark.parametrize("nombre", [A, B])
def test_cantidad_de_citas_es_la_del_paciente(nombre):
    cedula = USUARIOS[nombre]
    assert his.mis_citas(id_usuario(nombre), cedula)["paginacion"]["total"] == cuantas(cedula)


@pytest.mark.parametrize("nombre", [A, B])
def test_citas_paginadas_sin_repetir_ni_mezclar(nombre):
    cedula, uid = USUARIOS[nombre], id_usuario(nombre)
    ids, pagina = [], 1
    while True:
        r = his.mis_citas(uid, cedula, pagina=pagina)
        ids += [(x["area"], x["id_cita"]) for x in r["citas"]]
        if pagina >= r["paginacion"]["paginas"]:
            break
        pagina += 1
    assert len(ids) == len(set(ids)) == cuantas(cedula)
    ajenas = {f["id_cita"] for f in sql("SELECT id_cita FROM cita WHERE cedula_paciente <> %s", (cedula,))}
    assert not ({i for _, i in ids} & ajenas)


def test_citas_mas_recientes_primero_y_proximas_activas():
    r = his.mis_citas(id_usuario(A), USUARIOS[A])
    fechas = [x["fecha_cita"] for x in r["citas"]]
    assert fechas == sorted(fechas, reverse=True)
    assert all(x["estado"] in ("pendiente", "confirmada") for x in r["proximas"])


def test_filtros_de_citas():
    uid, ced = id_usuario(A), USUARIOS[A]
    assert all(x["estado"] == "atendida" for x in his.mis_citas(uid, ced, estado="atendida")["citas"])
    assert his.mis_citas(uid, ced, estado="' OR 1=1 --")["paginacion"]["total"] == cuantas(ced)     # se ignora
    assert his.mis_citas(uid, ced, desde="2099-01-01")["citas"] == []


def test_historial_de_consultas_agrupa_diagnosticos():
    uid, ced = id_usuario(A), USUARIOS[A]
    esperadas = sql("""SELECT COUNT(*) AS n FROM consulta_medica cm JOIN cita c USING (id_cita)
                       WHERE c.cedula_paciente = %s""", (ced,), uno=True)["n"]
    r = his.mi_historial(uid, ced)
    assert r["paginacion"]["total"] == esperadas
    assert len({c["id_consulta"] for c in r["consultas"]}) == len(r["consultas"])
    assert all(isinstance(c["diagnosticos"], list) and c["medico"] and c["motivo_consulta"] for c in r["consultas"])


def test_recetas_con_sus_medicamentos():
    uid, ced = id_usuario(A), USUARIOS[A]
    r = his.mis_recetas(uid, ced)
    esperadas = sql("""SELECT COUNT(*) AS n FROM prescripcion p JOIN consulta_medica cm USING (id_consulta)
                       JOIN cita c USING (id_cita) WHERE c.cedula_paciente = %s""", (ced,), uno=True)["n"]
    assert r["paginacion"]["total"] == esperadas
    assert all(x["medicamentos"] and x["medico"] for x in r["recetas"])


def test_resultados_son_del_paciente():
    uid, ced = id_usuario(B), USUARIOS[B]
    r = his.mis_resultados(uid, ced)
    esperados = sql("""SELECT COUNT(*) AS n FROM resultado_laboratorio rl JOIN cita c USING (id_cita)
                       WHERE c.cedula_paciente = %s""", (ced,), uno=True)["n"]
    assert r["paginacion"]["total"] == esperados
    for x in r["laboratorio"] + r["imagenologia"]:
        assert sql("SELECT cedula_paciente FROM cita WHERE id_cita = %s", (x["id_cita"],), uno=True)["cedula_paciente"] == ced


def test_cedula_sin_datos_devuelve_listas_vacias():
    assert his.mis_citas(1, "0999999999")["citas"] == []
    assert his.mi_historial(1, "0999999999")["consultas"] == []
    assert his.mis_recetas(1, "0999999999")["recetas"] == []
    assert his.mis_resultados(1, "0999999999")["laboratorio"] == []


@pytest.mark.parametrize("url", URLS)
def test_las_pantallas_responden_y_no_muestran_datos_de_otro_paciente(entrar, url):
    pagina = texto(entrar(A).get(url))
    assert "Cordero" not in pagina and USUARIOS[B] not in pagina


@pytest.mark.parametrize("url", URLS)
def test_el_parametro_cedula_de_la_url_se_ignora(entrar, url):
    normal = texto(entrar(A).get(url))
    manipulada = texto(entrar(A).get(f"{url}?cedula={USUARIOS[B]}&cedula_paciente={USUARIOS[B]}"))
    assert USUARIOS[B] not in manipulada and "Cordero" not in manipulada
    assert len(normal) > 0 and len(manipulada) > 0


@pytest.mark.parametrize("url", URLS)
def test_otros_roles_no_entran(entrar, url):
    for rol in ("admin", "recepcion", "medico", "imagenologia", "laboratorio"):
        assert entrar(rol).get(url).status_code == 403


def test_la_cuenta_mysql_del_paciente_solo_lee_vistas():
    from conexion.conexionBD import consultar
    from utils.errors import ErrorNegocio
    for tabla in ("cita", "paciente", "usuario", "consulta_medica", "resultado_laboratorio", "auditoria_acceso"):
        with pytest.raises(ErrorNegocio):
            consultar("paciente", f"SELECT * FROM {tabla} LIMIT 1")
    assert consultar("paciente", "SELECT COUNT(*) AS n FROM v_historial_paciente", uno=True) is not None