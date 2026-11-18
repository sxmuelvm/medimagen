"""Horario de atencion de cada medico (turnos): reglas, pantallas del administrador y agendamiento."""
import datetime
import re

import pytest

from conexion.conexionBD import ejecutar, transaccion
from conftest import id_usuario, sql, sql_escribir, texto
from utils.errors import ErrorNegocio

CEDULA_TEMPORAL = "0000000099"
TODOS_LOS_DIAS = ["1", "2", "3", "4", "5"]


@pytest.fixture
def medico():
    """Medico temporal, sin turnos. Al terminar se borran sus citas y el medico (los turnos se borran con el)."""
    sql_escribir("""INSERT INTO medico (id_especialidad, cedula, nombres, apellidos, correo)
                    VALUES ('ESP-01', %s, 'Prueba', 'Temporal', 'prueba.temporal@medimagen.ec')""", (CEDULA_TEMPORAL,))
    yield sql("SELECT id_medico FROM medico WHERE cedula = %s", (CEDULA_TEMPORAL,), uno=True)["id_medico"]
    sql_escribir("""UPDATE cita c JOIN cita_consulta cc ON cc.id_cita = c.id_cita JOIN medico m ON m.id_medico = cc.id_medico
                    SET c.estado = 'cancelada' WHERE m.cedula = %s AND c.estado IN ('pendiente', 'confirmada')""",
                 (CEDULA_TEMPORAL,))
    sql_escribir("""DELETE c FROM cita c JOIN cita_consulta cc ON cc.id_cita = c.id_cita
                    JOIN medico m ON m.id_medico = cc.id_medico WHERE m.cedula = %s""", (CEDULA_TEMPORAL,))
    sql_escribir("DELETE FROM medico WHERE cedula = %s", (CEDULA_TEMPORAL,))


@pytest.fixture
def dia(fecha_laborable):
    return fecha_laborable(60)


@pytest.fixture
def paciente():
    return sql("SELECT cedula_paciente FROM paciente WHERE estado = 'activo' ORDER BY cedula_paciente LIMIT 1",
               uno=True)["cedula_paciente"]


def dia_semana(fecha):
    return datetime.date.fromisoformat(fecha).isoweekday()          # 1 = lunes ... 5 = viernes


def otro_dia_laborable(fecha):
    """Un dia de lunes a viernes distinto al de `fecha`, dentro de la misma semana."""
    d = datetime.date.fromisoformat(fecha)
    for delta in (1, 2, 3, 4, -1, -2, -3, -4):
        if 0 <= (d + datetime.timedelta(days=delta)).weekday() < 5 and (d + datetime.timedelta(days=delta)) != d:
            return (d + datetime.timedelta(days=delta)).isoformat()


def horas(cliente, fecha, id_medico):
    r = cliente.get(f"/citas/horarios?fecha={fecha}&id_area=1&id_medico={id_medico}")
    assert r.status_code == 200
    return [h["hora_inicio"] for h in r.get_json()["horarios"]]


def agregar(admin, id_medico, dias, inicio, fin):
    return admin.post(f"/medicos/{id_medico}/horario", {"dia": dias, "hora_inicio": inicio, "hora_fin": fin})


def turnos(id_medico):
    return sql("SELECT id_horario, dia_semana, hora_inicio, hora_fin FROM horario_medico WHERE id_medico = %s "
               "ORDER BY dia_semana, hora_inicio", (id_medico,))


def crear_consulta(cliente, cedula, id_medico, fecha, hora):
    r = cliente.post("/citas/nueva", {"cedula_paciente": cedula, "id_area": "1", "id_medico": str(id_medico),
                                      "fecha_cita": fecha, "hora_inicio": hora})
    coincide = re.search(r"/citas/(\d+)$", r.headers.get("Location", ""))
    return r, (int(coincide.group(1)) if coincide else None)


# ---------------------------------------------------------------------------
def test_turnos_de_ejemplo(entrar, dia):
    c = entrar("recepcion")
    assert horas(c, dia, 1) == ["07:00", "08:00", "09:00", "10:00", "11:00", "12:00", "15:00", "16:00", "17:00"]
    assert horas(c, dia, 7) == ["15:00", "16:00", "17:00"]                                 # solo en la tarde
    assert horas(c, dia, 8) == ["07:00", "08:00", "09:00", "10:00", "11:00", "12:00"]      # solo en la manana


def test_un_medico_sin_turnos_usa_el_horario_general(entrar, medico, dia):
    assert len(horas(entrar("recepcion"), dia, medico)) == 9


def test_agregar_un_turno_limita_los_horarios(entrar, medico, dia):
    admin, recepcion = entrar("admin"), entrar("recepcion")
    assert admin.get(f"/medicos/{medico}/horario").status_code == 200
    r = agregar(admin, medico, [str(dia_semana(dia))], "08:00", "11:00")
    assert r.status_code == 302
    assert horas(recepcion, dia, medico) == ["08:00", "09:00", "10:00"]
    assert horas(recepcion, otro_dia_laborable(dia), medico) == []          # tiene turnos, pero no ese dia


def test_un_turno_en_varios_dias_a_la_vez(entrar, medico):
    r = agregar(entrar("admin"), medico, ["1", "3", "5"], "07:00", "10:00")
    assert r.status_code == 302
    assert [t["dia_semana"] for t in turnos(medico)] == [1, 3, 5]


@pytest.mark.parametrize("dias,inicio,fin", [
    (["6"], "08:00", "10:00"),            # sabado
    (["0"], "08:00", "10:00"),
    ([""], "08:00", "10:00"),             # ningun dia
    (["abc"], "08:00", "10:00"),
    (["1"], "10:00", "10:00"),            # fin igual al inicio
    (["1"], "11:00", "09:00"),            # fin antes del inicio
    (["1"], "08:30", "10:00"),            # inicio que no es en punto
    (["1"], "08:00", "10:30"),            # fin que no es en punto
    (["1"], "06:00", "10:00"),            # antes de la primera hora
    (["1"], "08:00", "19:00"),            # despues de la ultima
    (["1"], "xx", "yy"),
])
def test_turnos_invalidos_no_se_guardan(entrar, medico, dias, inicio, fin):
    assert agregar(entrar("admin"), medico, dias, inicio, fin).status_code == 400
    assert turnos(medico) == []


def test_los_turnos_de_un_medico_no_se_solapan(entrar, medico):
    admin = entrar("admin")
    assert agregar(admin, medico, ["2"], "08:00", "11:00").status_code == 302
    r = agregar(admin, medico, ["2"], "10:00", "12:00")
    assert r.status_code == 400 and "cruza" in texto(r)
    assert agregar(admin, medico, ["2"], "08:00", "09:00").status_code == 400       # mismo inicio
    assert agregar(admin, medico, ["2"], "11:00", "12:00").status_code == 302       # seguido, sin cruzarse
    assert agregar(admin, medico, ["3"], "10:00", "12:00").status_code == 302       # otro dia: si
    assert len(turnos(medico)) == 3


def test_si_un_dia_falla_no_se_guarda_ninguno(entrar, medico):
    admin = entrar("admin")
    agregar(admin, medico, ["3"], "08:00", "10:00")
    assert agregar(admin, medico, ["2", "3"], "09:00", "11:00").status_code == 400      # el martes cabria, el miercoles no
    assert [t["dia_semana"] for t in turnos(medico)] == [3]


def test_la_base_impide_turnos_cruzados_aunque_no_pase_por_la_app(medico):
    ejecutar("administrador", "INSERT INTO horario_medico (id_medico, dia_semana, hora_inicio, hora_fin) "
                              "VALUES (%s, 1, '08:00:00', '11:00:00')", (medico,))
    with pytest.raises(ErrorNegocio):
        ejecutar("administrador", "INSERT INTO horario_medico (id_medico, dia_semana, hora_inicio, hora_fin) "
                                  "VALUES (%s, 1, '10:00:00', '12:00:00')", (medico,))
    with pytest.raises(ErrorNegocio):                                                    # el fin debe ser un bloque
        ejecutar("administrador", "INSERT INTO horario_medico (id_medico, dia_semana, hora_inicio, hora_fin) "
                                  "VALUES (%s, 2, '08:00:00', '10:30:00')", (medico,))
    with pytest.raises(ErrorNegocio):                                                    # el dia debe ser de lunes a viernes
        ejecutar("administrador", "INSERT INTO horario_medico (id_medico, dia_semana, hora_inicio, hora_fin) "
                                  "VALUES (%s, 6, '08:00:00', '10:00:00')", (medico,))


# ---------------------------------------------------------------------------
def test_no_se_agenda_fuera_del_turno(entrar, medico, dia, paciente):
    admin, recepcion = entrar("admin"), entrar("recepcion")
    agregar(admin, medico, TODOS_LOS_DIAS, "08:00", "11:00")
    for hora in ("07:00", "11:00", "12:00", "15:00"):
        r, id_cita = crear_consulta(recepcion, paciente, medico, dia, hora)
        assert r.status_code == 400 and id_cita is None, hora
    r, id_cita = crear_consulta(recepcion, paciente, medico, dia, "10:00")
    assert r.status_code == 302 and id_cita


def test_la_base_impide_agendar_fuera_del_turno_aunque_no_pase_por_la_app(medico, dia, paciente):
    ejecutar("administrador", "INSERT INTO horario_medico (id_medico, dia_semana, hora_inicio, hora_fin) "
                              "VALUES (%s, %s, '08:00:00', '10:00:00')", (medico, dia_semana(dia)))
    with pytest.raises(ErrorNegocio) as error:
        with transaccion("administrador", id_usuario("admin")) as cursor:
            cursor.execute("""INSERT INTO cita (cedula_paciente, id_area, id_recurso, id_usuario_registra, fecha_cita,
                                                hora_inicio, hora_fin)
                              VALUES (%s, 1, 1, %s, %s, '15:00:00', '16:00:00')""",
                           (paciente, id_usuario("admin"), dia))
            cursor.execute("INSERT INTO cita_consulta (id_cita, id_medico) VALUES (LAST_INSERT_ID(), %s)", (medico,))
    assert "no atiende" in error.value.mensaje


def test_reprogramar_respeta_el_turno(entrar, medico, dia, paciente):
    admin, recepcion = entrar("admin"), entrar("recepcion")
    agregar(admin, medico, TODOS_LOS_DIAS, "08:00", "11:00")
    _, id_cita = crear_consulta(recepcion, paciente, medico, dia, "09:00")
    assert id_cita
    assert recepcion.post(f"/citas/{id_cita}/reprogramar", {"fecha_cita": dia, "hora_inicio": "15:00"}).status_code == 400
    assert recepcion.post(f"/citas/{id_cita}/reprogramar", {"fecha_cita": dia, "hora_inicio": "10:00"}).status_code == 302


def test_no_se_quita_un_turno_con_citas_activas(entrar, medico, dia, paciente):
    admin, recepcion = entrar("admin"), entrar("recepcion")
    agregar(admin, medico, TODOS_LOS_DIAS, "08:00", "11:00")
    _, id_cita = crear_consulta(recepcion, paciente, medico, dia, "09:00")
    turno = next(t for t in turnos(medico) if t["dia_semana"] == dia_semana(dia))
    r = admin.post(f"/medicos/{medico}/horario/{turno['id_horario']}/eliminar", follow_redirects=True)
    assert "cita(s) activa(s)" in texto(r)
    assert len(turnos(medico)) == 5
    recepcion.post(f"/citas/{id_cita}/estado", {"estado": "cancelada"})
    assert admin.post(f"/medicos/{medico}/horario/{turno['id_horario']}/eliminar").status_code == 302
    assert len(turnos(medico)) == 4


def test_sin_turnos_se_vuelve_al_horario_general(entrar, medico, dia):
    admin, recepcion = entrar("admin"), entrar("recepcion")
    agregar(admin, medico, TODOS_LOS_DIAS, "08:00", "10:00")
    assert len(horas(recepcion, dia, medico)) == 2
    for t in turnos(medico):
        assert admin.post(f"/medicos/{medico}/horario/{t['id_horario']}/eliminar").status_code == 302
    assert len(horas(recepcion, dia, medico)) == 9


def test_eliminar_el_turno_de_otro_medico_no_funciona(entrar, medico):
    admin = entrar("admin")
    agregar(admin, medico, ["1"], "08:00", "10:00")
    del_otro = sql("SELECT id_horario FROM horario_medico WHERE id_medico = 1 LIMIT 1", uno=True)["id_horario"]
    assert admin.post(f"/medicos/{medico}/horario/{del_otro}/eliminar").status_code == 404
    assert sql("SELECT COUNT(*) AS n FROM horario_medico WHERE id_horario = %s", (del_otro,), uno=True)["n"] == 1


def test_medico_inexistente(entrar):
    admin = entrar("admin")
    assert admin.get("/medicos/99999/horario").status_code == 404
    assert agregar(admin, 99999, ["1"], "08:00", "10:00").status_code == 404


def test_al_borrar_un_medico_se_borran_sus_turnos(entrar, medico):
    agregar(entrar("admin"), medico, TODOS_LOS_DIAS, "08:00", "10:00")
    assert len(turnos(medico)) == 5
    sql_escribir("DELETE FROM medico WHERE id_medico = %s", (medico,))
    assert turnos(medico) == []