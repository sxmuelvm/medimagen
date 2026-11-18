"""Citas: agenda, horarios, reglas de negocio (almuerzo, fines de semana, choques), reprogramar y estados.

Todo lo que se crea aqui se cancela y se elimina al terminar cada prueba.
"""
import datetime
import re

import pytest

from conftest import id_usuario, sql, texto

MEDICOS = [1, 2, 3, 4, 5, 6]


def sabado_despues_de(dia):
    """El sabado de la semana de `dia` (AAAA-MM-DD)."""
    d = datetime.date.fromisoformat(dia)
    return (d + datetime.timedelta(days=5 - d.weekday())).isoformat()


@pytest.fixture
def pacientes():
    filas = sql("SELECT cedula_paciente FROM paciente WHERE estado = 'activo' ORDER BY cedula_paciente LIMIT 6")
    assert len(filas) >= 6, "Se necesitan al menos 6 pacientes activos de ejemplo"
    return [f["cedula_paciente"] for f in filas]


@pytest.fixture
def dia(fecha_laborable):
    return fecha_laborable(60)


def nueva(cliente, limpiar, **datos):
    """POST /citas/nueva; si se crea, registra el id para limpiarlo. Devuelve (respuesta, id_cita o None)."""
    r = cliente.post("/citas/nueva", datos)
    coincide = re.search(r"/citas/(\d+)$", r.headers.get("Location", ""))
    id_cita = int(coincide.group(1)) if coincide else None
    if id_cita:
        limpiar.append(id_cita)
    return r, id_cita


def consulta(cedula, dia, hora="09:00", medico=1, **extra):
    return {"cedula_paciente": cedula, "id_area": "1", "id_medico": str(medico), "fecha_cita": dia,
            "hora_inicio": hora, **extra}


def examen(cedula, dia, area, subtipo, hora="09:00", equipo="", medico=1):
    return {"cedula_paciente": cedula, "id_area": str(area), "id_medico_solicitante": str(medico),
            "id_subtipo": subtipo, "id_recurso": equipo, "fecha_cita": dia, "hora_inicio": hora}


# ---------------------------------------------------------------------------
def test_agenda_y_filtros(entrar):
    c = entrar("recepcion")
    assert c.get("/citas/").status_code == 200
    assert c.get("/citas/?estado=pendiente&id_area=2&desde=2026-01-01&hasta=2027-12-31&pagina=3").status_code == 200
    assert c.get("/citas/?q=%27%20OR%201%3D1%20--&desde=basura&id_area=zz").status_code == 200


def test_detalle_y_cita_inexistente(entrar):
    c = entrar("recepcion")
    assert c.get("/citas/1").status_code == 200
    assert c.get("/citas/99999999").status_code == 404


def test_horarios_en_json(entrar, dia, fecha_laborable):
    c = entrar("recepcion")
    r = c.get(f"/citas/horarios?fecha={dia}&id_area=1")
    horas = [h["hora_inicio"] for h in r.get_json()["horarios"]]
    assert r.status_code == 200 and "13:00" not in horas and "14:00" not in horas
    assert horas[0] == "07:00" and "12:00" in horas and "15:00" in horas and len(horas) == 9
    # el almuerzo vale para todas las areas
    for area in (2, 3):
        horas = [h["hora_inicio"] for h in c.get(f"/citas/horarios?fecha={dia}&id_area={area}").get_json()["horarios"]]
        assert "13:00" not in horas and "14:00" not in horas
    assert c.get("/citas/horarios?fecha=xx&id_area=1").status_code == 400
    assert c.get("/citas/horarios?fecha=2026-01-05&id_area=1").get_json()["horarios"] == []     # pasado
    sabado = sabado_despues_de(dia)
    assert c.get(f"/citas/horarios?fecha={sabado}&id_area=1").get_json()["horarios"] == []      # fin de semana


# ---------------------------------------------------------------------------
def test_crear_consulta(entrar, limpiar_citas, pacientes, dia):
    c = entrar("recepcion")
    r, id_cita = nueva(c, limpiar_citas, **consulta(pacientes[0], dia, observacion="control"))
    assert r.status_code == 302 and id_cita
    fila = sql("""SELECT c.estado, c.costo_aplicado, c.id_usuario_registra, c.hora_fin, e.costo_consulta
                  FROM cita c JOIN cita_consulta cc USING (id_cita) JOIN medico m ON m.id_medico = cc.id_medico
                  JOIN especialidad e ON e.id_especialidad = m.id_especialidad WHERE c.id_cita = %s""",
               (id_cita,), uno=True)
    assert fila["estado"] == "pendiente"
    assert fila["costo_aplicado"] == fila["costo_consulta"]                  # el costo lo pone la base de datos
    assert fila["id_usuario_registra"] == id_usuario("recepcion")
    assert str(fila["hora_fin"]) == "10:00:00"
    assert c.get(f"/citas/{id_cita}").status_code == 200


@pytest.mark.parametrize("hora", ["13:00", "14:00"])
@pytest.mark.parametrize("area,extra", [(1, {}), (2, {"equipo": "7"}), (3, {})])
def test_no_se_agenda_en_el_almuerzo(entrar, limpiar_citas, pacientes, dia, area, extra, hora):
    c = entrar("recepcion")
    if area == 1:
        datos = consulta(pacientes[0], dia, hora)
    else:
        datos = examen(pacientes[0], dia, area, "RM-02" if area == 2 else "LAB-01", hora, extra.get("equipo", ""))
    r, id_cita = nueva(c, limpiar_citas, **datos)
    assert r.status_code == 400 and id_cita is None and "almuerzo" in texto(r)


@pytest.mark.parametrize("hora", ["06:00", "07:30", "18:00", "xx", ""])
def test_horas_invalidas(entrar, limpiar_citas, pacientes, dia, hora):
    r, _ = nueva(entrar("recepcion"), limpiar_citas, **consulta(pacientes[0], dia, hora))
    assert r.status_code == 400


def test_fin_de_semana_y_fechas_pasadas(entrar, limpiar_citas, pacientes, dia):
    c = entrar("recepcion")
    sabado = sabado_despues_de(dia)
    r, _ = nueva(c, limpiar_citas, **consulta(pacientes[0], sabado))
    assert r.status_code == 400 and "lunes a viernes" in texto(r)
    r, _ = nueva(c, limpiar_citas, **consulta(pacientes[0], "2026-01-05"))
    assert r.status_code == 400 and "futuras" in texto(r)


def test_paciente_o_medico_inexistente_o_inactivo(entrar, limpiar_citas, pacientes, dia):
    c = entrar("recepcion")
    for datos in (consulta("0999999999", dia), consulta("abc", dia), consulta(pacientes[0], dia, medico=99999),
                  consulta(pacientes[0], dia, medico="")):
        r, id_cita = nueva(c, limpiar_citas, **datos)
        assert r.status_code == 400 and id_cita is None


def test_medico_y_paciente_no_pueden_estar_en_dos_citas_a_la_vez(entrar, limpiar_citas, pacientes, dia):
    c = entrar("recepcion")
    _, primera = nueva(c, limpiar_citas, **consulta(pacientes[0], dia, "10:00", medico=1))
    assert primera
    r, _ = nueva(c, limpiar_citas, **consulta(pacientes[1], dia, "10:00", medico=1))          # mismo medico
    assert r.status_code == 400 and "médico" in texto(r)
    r, _ = nueva(c, limpiar_citas, **consulta(pacientes[0], dia, "10:00", medico=2))          # mismo paciente
    assert r.status_code == 400 and "paciente" in texto(r)
    r, otra = nueva(c, limpiar_citas, **consulta(pacientes[1], dia, "10:00", medico=2))        # otro paciente y medico: si
    assert r.status_code == 302 and otra


def test_se_acaban_los_consultorios(entrar, limpiar_citas, pacientes, dia):
    c = entrar("recepcion")
    libres = sql("SELECT COUNT(*) AS n FROM recurso_atencion WHERE id_area = 1 AND estado = 'activo'", uno=True)["n"]
    assert libres < len(pacientes)
    for i in range(libres):
        r, _ = nueva(c, limpiar_citas, **consulta(pacientes[i], dia, "11:00", medico=MEDICOS[i]))
        assert r.status_code == 302
    r, _ = nueva(c, limpiar_citas, **consulta(pacientes[libres], dia, "11:00", medico=MEDICOS[libres]))
    assert r.status_code == 400 and "consultorios libres" in texto(r)
    horas = [h["hora_inicio"] for h in c.get(f"/citas/horarios?fecha={dia}&id_area=1").get_json()["horarios"]]
    assert "11:00" not in horas


def test_imagenologia_y_laboratorio(entrar, limpiar_citas, pacientes, dia):
    c = entrar("recepcion")
    r, sin_equipo = nueva(c, limpiar_citas, **examen(pacientes[0], dia, 2, "RM-02", "08:00", equipo=""))
    assert r.status_code == 400 and "equipo" in texto(r)
    r, id_rm = nueva(c, limpiar_citas, **examen(pacientes[0], dia, 2, "RM-02", "08:00", equipo="7"))
    assert r.status_code == 302
    fila = sql("""SELECT c.costo_aplicado, s.costo, ci.estado_procedimiento FROM cita c
                  JOIN cita_imagenologia ci USING (id_cita) JOIN subtipo_examen s ON s.id_subtipo = ci.id_subtipo
                  WHERE c.id_cita = %s""", (id_rm,), uno=True)
    assert fila["costo_aplicado"] == fila["costo"] and fila["estado_procedimiento"] == "pendiente"
    r, _ = nueva(c, limpiar_citas, **examen(pacientes[1], dia, 2, "RM-02", "08:00", equipo="7"))    # equipo ocupado
    assert r.status_code == 400 and "ocupado" in texto(r)
    r, _ = nueva(c, limpiar_citas, **examen(pacientes[1], dia, 2, "LAB-01", "09:00", equipo="7"))   # examen de otra area
    assert r.status_code == 400
    r, id_lab = nueva(c, limpiar_citas, **examen(pacientes[1], dia, 3, "LAB-03", "09:00"))
    assert r.status_code == 302
    assert sql("SELECT id_recurso FROM cita WHERE id_cita = %s", (id_lab,), uno=True)["id_recurso"] in (9, 10)


# ---------------------------------------------------------------------------
def test_reprogramar(entrar, limpiar_citas, pacientes, dia, fecha_laborable):
    c = entrar("recepcion")
    _, id_cita = nueva(c, limpiar_citas, **consulta(pacientes[0], dia, "09:00"))
    nuevo_dia = fecha_laborable(61)
    assert c.get(f"/citas/{id_cita}/reprogramar").status_code == 200
    r = c.post(f"/citas/{id_cita}/reprogramar", {"fecha_cita": nuevo_dia, "hora_inicio": "15:00", "observacion": "movida"})
    assert r.status_code == 302
    fila = sql("SELECT fecha_cita, hora_inicio, observacion FROM cita WHERE id_cita = %s", (id_cita,), uno=True)
    assert fila["fecha_cita"].isoformat() == nuevo_dia and str(fila["hora_inicio"]) == "15:00:00" and fila["observacion"] == "movida"
    assert c.post(f"/citas/{id_cita}/reprogramar", {"fecha_cita": nuevo_dia, "hora_inicio": "14:00"}).status_code == 400   # almuerzo
    assert c.post(f"/citas/{id_cita}/reprogramar", {"fecha_cita": "2026-01-05", "hora_inicio": "10:00"}).status_code == 400
    # choque con otra cita del mismo paciente
    _, otra = nueva(c, limpiar_citas, **consulta(pacientes[0], nuevo_dia, "16:00", medico=2))
    assert otra
    assert c.post(f"/citas/{id_cita}/reprogramar", {"fecha_cita": nuevo_dia, "hora_inicio": "16:00"}).status_code == 400


def test_una_cita_atendida_no_se_modifica_ni_se_elimina(entrar, fecha_laborable):
    c = entrar("recepcion")
    atendida = sql("SELECT id_cita FROM cita WHERE estado = 'atendida' LIMIT 1", uno=True)["id_cita"]
    assert c.post(f"/citas/{atendida}/reprogramar", {"fecha_cita": fecha_laborable(60), "hora_inicio": "10:00"}).status_code == 400
    r = c.post(f"/citas/{atendida}/estado", {"estado": "cancelada"}, follow_redirects=True)
    assert "No se puede pasar" in texto(r)
    r = c.post(f"/citas/{atendida}/eliminar", follow_redirects=True)
    assert "Solo se pueden eliminar" in texto(r)
    assert sql("SELECT estado FROM cita WHERE id_cita = %s", (atendida,), uno=True)["estado"] == "atendida"


def test_ciclo_de_estados(entrar, limpiar_citas, pacientes, dia):
    c = entrar("recepcion")
    _, id_cita = nueva(c, limpiar_citas, **consulta(pacientes[0], dia, "10:00"))
    estado = lambda: sql("SELECT estado FROM cita WHERE id_cita = %s", (id_cita,), uno=True)["estado"]
    c.post(f"/citas/{id_cita}/estado", {"estado": "confirmada"})
    assert estado() == "confirmada"
    r = c.post(f"/citas/{id_cita}/estado", {"estado": "no_asistio"}, follow_redirects=True)
    assert "ya pasó la hora" in texto(r) and estado() == "confirmada"                # aun no llega la hora
    c.post(f"/citas/{id_cita}/estado", {"estado": "atendida"})
    assert estado() == "confirmada"                                                  # 'atendida' no la marca recepcion
    c.post(f"/citas/{id_cita}/estado", {"estado": "xx"})
    assert estado() == "confirmada"
    c.post(f"/citas/{id_cita}/estado", {"estado": "cancelada"})
    assert estado() == "cancelada"
    c.post(f"/citas/{id_cita}/estado", {"estado": "pendiente"})                       # reactivar
    assert estado() == "pendiente"


def test_cancelar_un_examen_actualiza_su_estado(entrar, limpiar_citas, pacientes, dia):
    c = entrar("recepcion")
    _, id_cita = nueva(c, limpiar_citas, **examen(pacientes[0], dia, 3, "LAB-02", "09:00"))
    c.post(f"/citas/{id_cita}/estado", {"estado": "cancelada"})
    assert sql("SELECT estado_examen FROM cita_laboratorio WHERE id_cita = %s", (id_cita,), uno=True)["estado_examen"] == "cancelado"
    c.post(f"/citas/{id_cita}/estado", {"estado": "pendiente"})
    assert sql("SELECT estado_examen FROM cita_laboratorio WHERE id_cita = %s", (id_cita,), uno=True)["estado_examen"] == "pendiente"


def test_eliminar_solo_pendientes_o_canceladas(entrar, limpiar_citas, pacientes, dia):
    c = entrar("recepcion")
    _, id_cita = nueva(c, limpiar_citas, **consulta(pacientes[0], dia, "10:00"))
    c.post(f"/citas/{id_cita}/estado", {"estado": "confirmada"})
    r = c.post(f"/citas/{id_cita}/eliminar", follow_redirects=True)
    assert "Solo se pueden eliminar" in texto(r)
    c.post(f"/citas/{id_cita}/estado", {"estado": "cancelada"})
    assert c.post(f"/citas/{id_cita}/eliminar").status_code == 302
    assert sql("SELECT COUNT(*) AS n FROM cita WHERE id_cita = %s", (id_cita,), uno=True)["n"] == 0
    assert c.post("/citas/99999999/eliminar").status_code == 404


def test_los_cambios_quedan_auditados_con_quien_los_hizo(entrar, limpiar_citas, pacientes, dia):
    c = entrar("recepcion")
    _, id_cita = nueva(c, limpiar_citas, **consulta(pacientes[0], dia, "10:00"))
    c.post(f"/citas/{id_cita}/estado", {"estado": "confirmada"})
    c.post(f"/citas/{id_cita}/estado", {"estado": "cancelada"})
    c.post(f"/citas/{id_cita}/eliminar")
    filas = sql("SELECT estado_nuevo, usuario_bd, id_usuario_app FROM auditoria_cita WHERE id_cita = %s ORDER BY id_auditoria",
                (id_cita,))
    assert [f["estado_nuevo"] for f in filas] == ["confirmada", "cancelada", "eliminada"]
    assert all(f["usuario_bd"].startswith("usr_recepcion") and f["id_usuario_app"] == id_usuario("recepcion") for f in filas)


def test_el_admin_ve_el_historial_de_la_cita_y_recepcion_no(entrar, limpiar_citas, pacientes, dia):
    c = entrar("recepcion")
    _, id_cita = nueva(c, limpiar_citas, **consulta(pacientes[0], dia, "10:00"))
    c.post(f"/citas/{id_cita}/estado", {"estado": "confirmada"})
    assert "usr_recepcion" not in texto(c.get(f"/citas/{id_cita}"))          # recepcion no puede leer la auditoria
    assert "usr_recepcion" in texto(entrar("admin").get(f"/citas/{id_cita}"))


def test_el_admin_tambien_agenda(entrar, limpiar_citas, pacientes, dia):
    r, id_cita = nueva(entrar("admin"), limpiar_citas, **consulta(pacientes[0], dia, "10:00"))
    assert r.status_code == 302
    assert sql("SELECT id_usuario_registra FROM cita WHERE id_cita = %s", (id_cita,), uno=True)["id_usuario_registra"] == id_usuario("admin")