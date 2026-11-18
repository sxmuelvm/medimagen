"""Quien puede entrar a que: cada pantalla se prueba con cada rol."""
import pytest

from conftest import sql

TODOS = {"admin", "recepcion", "medico", "imagenologia", "laboratorio", "paciente"}
ADMIN = {"admin"}
ADMIN_RECEP = {"admin", "recepcion"}

# URL -> roles que SI pueden entrar (todos los demas deben recibir 403)
PANTALLAS = {
    "/inicio": TODOS,
    "/perfil/": TODOS,
    "/perfil/clave": TODOS,
    "/usuarios": ADMIN,
    "/usuarios/nuevo": ADMIN,
    "/roles": ADMIN,
    "/personal": ADMIN,
    "/medicos": ADMIN,
    "/especialidades": ADMIN,
    "/catalogos": ADMIN,
    "/catalogos/areas": ADMIN,
    "/catalogos/recursos": ADMIN,
    "/catalogos/medicamentos": ADMIN,
    "/pacientes": ADMIN_RECEP,
    "/pacientes/nuevo": ADMIN_RECEP,
    "/citas/": ADMIN_RECEP,
    "/citas/nueva": ADMIN_RECEP,
    "/consultas/": {"medico"},
    "/consultas/examenes": {"medico"},
    "/consultas/examenes/nuevo": {"medico"},
    "/imagenologia/": {"imagenologia"},
    "/laboratorio/": {"laboratorio"},
    "/historial/": {"paciente"},
    "/historial/citas": {"paciente"},
    "/historial/recetas": {"paciente"},
    "/historial/resultados": {"paciente"},
    "/reportes/ingresos": ADMIN,
    "/auditoria/": ADMIN,
    "/auditoria/accesos": ADMIN,
}
CASOS = [(url, rol, rol in permitidos) for url, permitidos in PANTALLAS.items() for rol in sorted(TODOS)]


@pytest.mark.parametrize("url,rol,permitido", CASOS, ids=[f"{r}:{u}" for u, r, _ in CASOS])
def test_acceso_por_rol(entrar, url, rol, permitido):
    r = entrar(rol).get(url)
    assert r.status_code == (200 if permitido else 403)


@pytest.mark.parametrize("url", sorted(PANTALLAS))
def test_sin_sesion_se_va_al_login(anonimo, url):
    r = anonimo.get(url)
    assert r.status_code == 302 and "/login" in r.headers["Location"]


# acciones (POST) que solo pueden hacer ciertos roles: con el rol equivocado -> 403 aunque el CSRF sea valido
ACCIONES = [
    ("/usuarios/1/estado", {"estado": "activo"}, ["recepcion", "medico", "imagenologia", "laboratorio", "paciente"]),
    ("/usuarios/1/desbloquear", {}, ["recepcion", "medico", "paciente"]),
    ("/usuarios/nuevo", {}, ["recepcion", "medico", "paciente"]),
    ("/pacientes/0102030405/estado", {"estado": "inactivo"}, ["recepcion", "medico", "paciente"]),
    ("/pacientes/0102030405/eliminar", {}, ["recepcion", "medico", "paciente"]),
    ("/citas/1/estado", {"estado": "cancelada"}, ["medico", "imagenologia", "laboratorio", "paciente"]),
    ("/citas/1/eliminar", {}, ["medico", "imagenologia", "laboratorio", "paciente"]),
    ("/citas/nueva", {}, ["medico", "imagenologia", "laboratorio", "paciente"]),
    ("/consultas/1/atender", {}, ["admin", "recepcion", "imagenologia", "laboratorio", "paciente"]),
    ("/imagenologia/18/realizar", {}, ["admin", "recepcion", "medico", "laboratorio", "paciente"]),
    ("/laboratorio/21/resultado", {}, ["admin", "recepcion", "medico", "imagenologia", "paciente"]),
]
CASOS_POST = [(u, d, r) for u, d, roles in ACCIONES for r in roles]


@pytest.mark.parametrize("url,datos,rol", CASOS_POST, ids=[f"{r}:POST {u}" for u, _, r in CASOS_POST])
def test_acciones_con_el_rol_equivocado(entrar, url, datos, rol):
    assert entrar(rol).post(url, datos).status_code == 403


@pytest.mark.parametrize("url", [u for u, _, _ in ACCIONES])
def test_acciones_sin_csrf_se_rechazan(entrar, url):
    assert entrar("admin").post(url, {}, csrf=False).status_code in (400, 403)


def test_el_medico_no_ve_citas_de_otro_medico(entrar):
    otra = sql("""SELECT cc.id_cita FROM cita_consulta cc JOIN medico m ON m.id_medico = cc.id_medico
                  WHERE m.cedula <> '0301000001' LIMIT 1""", uno=True)
    assert entrar("medico").get(f"/consultas/{otra['id_cita']}/atender").status_code == 404


def test_menu_solo_muestra_lo_permitido(entrar):
    html = entrar("recepcion").get("/inicio").get_data(as_text=True)
    assert "/citas" in html and "/pacientes" in html
    assert "/usuarios" not in html and "/auditoria" not in html and "/reportes" not in html