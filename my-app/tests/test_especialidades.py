"""Varios medicos por especialidad: atencion simultanea, cobertura continua y jornada sin hora de almuerzo."""
import re

import pytest

from conexion.conexionBD import ejecutar
from conftest import sql, texto
from utils.errors import ErrorNegocio

JORNADA = [f"{h:02d}:00" for h in range(7, 18)]          # 07:00 a 17:00: el ultimo turno termina a las 18:00


def nueva(cliente, limpiar, **datos):
    r = cliente.post("/citas/nueva", datos)
    coincide = re.search(r"/citas/(\d+)$", r.headers.get("Location", ""))
    id_cita = int(coincide.group(1)) if coincide else None
    if id_cita:
        limpiar.append(id_cita)
    return r, id_cita


def consulta(cedula, dia, hora, medico):
    return {"cedula_paciente": cedula, "id_area": "1", "id_medico": str(medico), "fecha_cita": dia, "hora_inicio": hora}


@pytest.fixture
def pacientes():
    filas = sql("SELECT cedula_paciente FROM paciente WHERE estado = 'activo' ORDER BY cedula_paciente LIMIT 6")
    return [f["cedula_paciente"] for f in filas]


@pytest.fixture
def dia(fecha_laborable):
    return fecha_laborable(75)


def medicos_de(especialidad):
    return [f["id_medico"] for f in sql("SELECT id_medico FROM medico WHERE id_especialidad = %s AND estado = 'activo' "
                                        "ORDER BY id_medico", (especialidad,))]


# ---------------------------------------------------------------------------
def test_varios_medicos_de_la_misma_especialidad_atienden_a_la_vez(entrar, limpiar_citas, pacientes, dia):
    recepcion = entrar("recepcion")
    medicos = medicos_de("ESP-01")
    assert len(medicos) >= 3
    ids = []
    for medico, paciente in zip(medicos[:3], pacientes):                 # misma fecha y misma hora
        r, id_cita = nueva(recepcion, limpiar_citas, **consulta(paciente, dia, "10:00", medico))
        assert r.status_code == 302 and id_cita, texto(r)
        ids.append(id_cita)
    filas = sql("SELECT c.id_recurso, cc.id_medico FROM cita c JOIN cita_consulta cc USING (id_cita) "
                "WHERE c.id_cita IN (%s, %s, %s)", tuple(ids))
    assert len({f["id_recurso"] for f in filas}) == 3                    # cada uno en un consultorio distinto
    assert len({f["id_medico"] for f in filas}) == 3


def test_un_mismo_medico_no_atiende_a_dos_pacientes_a_la_vez(entrar, limpiar_citas, pacientes, dia):
    recepcion = entrar("recepcion")
    r, id_cita = nueva(recepcion, limpiar_citas, **consulta(pacientes[0], dia, "10:00", 1))
    assert r.status_code == 302 and id_cita
    r, id_cita = nueva(recepcion, limpiar_citas, **consulta(pacientes[1], dia, "10:00", 1))
    assert r.status_code == 400 and id_cita is None


def test_los_cuatro_consultorios_se_llenan_y_el_quinto_paciente_no_entra(entrar, limpiar_citas, pacientes, dia):
    recepcion = entrar("recepcion")
    medicos = [m for m in range(1, 11)]
    for medico, paciente in zip(medicos[:4], pacientes):
        r, id_cita = nueva(recepcion, limpiar_citas, **consulta(paciente, dia, "11:00", medico))
        assert r.status_code == 302 and id_cita, texto(r)
    r, id_cita = nueva(recepcion, limpiar_citas, **consulta(pacientes[4], dia, "11:00", medicos[4]))
    assert r.status_code == 400 and id_cita is None


def test_cada_especialidad_activa_tiene_medico_y_cobertura_continua():
    sin_medico = sql("""SELECT e.id_especialidad FROM especialidad e WHERE e.estado = 'activo'
                        AND NOT EXISTS (SELECT 1 FROM medico m WHERE m.id_especialidad = e.id_especialidad
                                        AND m.estado = 'activo')""")
    assert sin_medico == []


def test_la_jornada_es_continua_de_7_a_18(entrar, dia):
    horas = [h["hora_inicio"] for h in entrar("recepcion").get(f"/citas/horarios?fecha={dia}&id_area=1").get_json()["horarios"]]
    assert horas == JORNADA and "13:00" in horas and "14:00" in horas


# ---------------------------------------------------------------------------
def test_cada_especialidad_tiene_cuatro_medicos():
    filas = sql("SELECT id_especialidad, COUNT(*) AS n FROM medico WHERE estado = 'activo' GROUP BY id_especialidad")
    assert len(filas) == 7 and all(f["n"] == 4 for f in filas)


def test_cuatro_medicos_de_la_misma_especialidad_atienden_a_la_vez(entrar, limpiar_citas, pacientes, dia):
    recepcion = entrar("recepcion")
    medicos = medicos_de("ESP-07")
    assert len(medicos) == 4
    for medico, paciente in zip(medicos, pacientes):                      # misma fecha y misma hora
        r, id_cita = nueva(recepcion, limpiar_citas, **consulta(paciente, dia, "09:00", medico))
        assert r.status_code == 302 and id_cita, texto(r)


def test_no_se_desactiva_al_ultimo_medico_activo_de_una_especialidad(entrar):
    admin = entrar("admin")
    *otros, ultimo = medicos_de("ESP-02")
    try:
        for medico in otros:                                              # mientras quede otro, si se puede
            assert admin.post(f"/medicos/{medico}/estado", {"estado": "inactivo"}).status_code == 302
        r = admin.post(f"/medicos/{ultimo}/estado", {"estado": "inactivo"}, follow_redirects=True)  # ya es el unico
        assert "único médico activo" in texto(r)
        assert sql("SELECT estado FROM medico WHERE id_medico = %s", (ultimo,), uno=True)["estado"] == "activo"
    finally:
        for medico in otros:
            ejecutar("administrador", "UPDATE medico SET estado = 'activo' WHERE id_medico = %s", (medico,))


def test_la_base_impide_dejar_una_especialidad_sin_medico():
    *otros, ultimo = medicos_de("ESP-03")
    try:
        for medico in otros:
            ejecutar("administrador", "UPDATE medico SET estado = 'inactivo' WHERE id_medico = %s", (medico,))
        with pytest.raises(ErrorNegocio):
            ejecutar("administrador", "UPDATE medico SET estado = 'inactivo' WHERE id_medico = %s", (ultimo,))
        with pytest.raises(ErrorNegocio):
            ejecutar("administrador", "UPDATE medico SET id_especialidad = 'ESP-01' WHERE id_medico = %s", (ultimo,))
        with pytest.raises(ErrorNegocio):
            ejecutar("administrador", "DELETE FROM medico WHERE id_medico = %s", (ultimo,))
        assert sql("SELECT estado, id_especialidad FROM medico WHERE id_medico = %s", (ultimo,), uno=True) == \
            {"estado": "activo", "id_especialidad": "ESP-03"}
    finally:
        for medico in otros:
            ejecutar("administrador", "UPDATE medico SET estado = 'activo' WHERE id_medico = %s", (medico,))


def test_si_hay_otro_medico_si_se_puede_desactivar_y_reactivar(entrar):
    admin = entrar("admin")
    medico = medicos_de("ESP-07")[1]
    try:
        r = admin.post(f"/medicos/{medico}/estado", {"estado": "inactivo"})
        assert r.status_code == 302
        assert sql("SELECT estado FROM medico WHERE id_medico = %s", (medico,), uno=True)["estado"] == "inactivo"
    finally:
        ejecutar("administrador", "UPDATE medico SET estado = 'activo' WHERE id_medico = %s", (medico,))
