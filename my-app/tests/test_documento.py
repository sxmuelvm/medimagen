"""La base y las reglas siguen el documento del proyecto (matriz de entidades y reglas de agendamiento)."""
import pytest
from conftest import sql, sql_escribir
from utils.errors import ErrorNegocio

TABLAS_DEL_DOCUMENTO = {"paciente", "medico", "especialidad", "usuario", "rol", "area", "recurso_atencion", "cita"}
TABLAS_EXTRA = {"tipo_procedimiento", "subtipo_examen", "cita_consulta", "cita_imagenologia", "cita_laboratorio",
                "consulta_medica", "prescripcion", "detalle_prescripcion", "resultado_laboratorio"}


def columnas(tabla):
    return [f["COLUMN_NAME"] for f in sql("""SELECT COLUMN_NAME FROM information_schema.COLUMNS
                                              WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
                                              ORDER BY ORDINAL_POSITION""", (tabla,))]


def test_solo_hay_las_tablas_del_documento_mas_las_minimas():
    tablas = {f["TABLE_NAME"] for f in sql("""SELECT TABLE_NAME FROM information_schema.TABLES
                                               WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE'""")}
    assert tablas == TABLAS_DEL_DOCUMENTO | TABLAS_EXTRA


@pytest.mark.parametrize("tabla,esperadas", [
    ("paciente", ["cedula_paciente", "nombres", "apellidos", "fecha_nacimiento", "sexo", "telefono", "correo",
                  "direccion", "fecha_registro", "estado"]),
    ("medico", ["id_medico", "id_especialidad", "cedula", "nombres", "apellidos", "telefono", "correo", "estado"]),
    ("especialidad", ["id_especialidad", "nombre", "descripcion", "costo_consulta", "estado"]),
    ("rol", ["id_rol", "nombre", "descripcion", "estado"]),
    ("area", ["id_area", "nombre", "descripcion", "estado"]),
    ("recurso_atencion", ["id_recurso", "id_area", "nombre_recurso", "tipo_recurso", "descripcion", "estado"]),
    ("cita", ["id_cita", "cedula_paciente", "id_area", "id_recurso", "id_usuario_registra", "fecha_cita",
              "hora_inicio", "hora_fin", "estado", "costo_aplicado", "observacion", "fecha_registro"]),
])
def test_las_columnas_de_la_matriz_estan_todas_y_en_orden(tabla, esperadas):
    assert columnas(tabla)[:len(esperadas)] == esperadas


def test_usuario_tiene_las_columnas_de_la_matriz():
    esperadas = ["id_usuario", "id_rol", "cedula", "nombres", "apellidos", "nombre_usuario",
                 "correo", "password", "estado", "fecha_creacion"]
    assert columnas("usuario")[:len(esperadas)] == esperadas
    assert "id_medico" not in columnas("usuario") and "cedula_paciente" not in columnas("usuario")


def test_los_codigos_de_especialidad_y_examen_los_genera_la_base():
    ids = [f["id_especialidad"] for f in sql("SELECT id_especialidad FROM especialidad ORDER BY id_especialidad")]
    assert ids == [f"ESP-0{i}" for i in range(1, 8)]
    assert {f["id_subtipo"] for f in sql("SELECT id_subtipo FROM subtipo_examen")} >= {"RX-01", "RX-09", "TAC-04", "RM-02",
                                                                                      "DO-02", "LAB-01", "LAB-03"}
    sql_escribir("INSERT INTO especialidad (nombre, descripcion, costo_consulta) VALUES ('Prueba codigo', 'x', 10)")
    try:
        assert sql("SELECT MAX(id_especialidad) AS m FROM especialidad", uno=True)["m"] == "ESP-08"
    finally:
        sql_escribir("DELETE FROM especialidad WHERE nombre = 'Prueba codigo'")


@pytest.mark.parametrize("inicio,fin", [("18:00:00", "19:00:00"), ("06:00:00", "07:00:00"),
                                        ("08:30:00", "09:30:00"), ("08:00:00", "09:30:00"), ("08:00:00", "08:30:00")])
def test_la_base_solo_acepta_turnos_de_60_minutos_en_la_jornada(inicio, fin):
    with pytest.raises(ErrorNegocio):
        sql_escribir("""INSERT INTO cita (cedula_paciente, id_area, id_recurso, id_usuario_registra, fecha_cita,
                                          hora_inicio, hora_fin)
                        VALUES ('0000000023', 1, 2, 2, '2030-01-07', %s, %s)""", (inicio, fin))


def test_la_base_no_acepta_citas_en_fin_de_semana():
    with pytest.raises(ErrorNegocio):
        sql_escribir("""INSERT INTO cita (cedula_paciente, id_area, id_recurso, id_usuario_registra, fecha_cita,
                                          hora_inicio, hora_fin)
                        VALUES ('0000000023', 1, 2, 2, '2030-01-05', '08:00:00', '09:00:00')""")
