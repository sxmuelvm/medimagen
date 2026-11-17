"""Catalogos del sistema (solo administrador): areas, recursos de atencion, tipos y subtipos de examen,
medicamentos y bloques horarios.

- Las 3 areas (consultas, imagenologia, laboratorio) las usa la logica de la base de datos: se editan, no se crean.
- Los bloques horarios son fijos (07:00 a 18:00): solo se consultan.
- El codigo de cada examen (RX-01, TAC-02...) lo asigna el trigger de MySQL.
"""
import re
from decimal import Decimal

from conexion.conexionBD import consultar, ejecutar
from utils import validators
from utils.constants import AREA_CONSULTAS, AREA_IMAGENOLOGIA, AREA_LABORATORIO, CUENTA_ADMINISTRADOR
from utils.errors import ErrorNegocio
from utils.helpers import pagina_actual, paginar, patron_like
from utils.logger import obtener_logger

log = obtener_logger("catalogos")

CUENTA = CUENTA_ADMINISTRADOR
ESTADOS = ("activo", "inactivo")
ESTADOS_RECURSO = ("activo", "inactivo", "mantenimiento")
TIPOS_RECURSO = ("consultorio", "equipo", "puesto_laboratorio")
POR_PAGINA = 10

# Tipo de recurso que corresponde a cada area
_RECURSO_DE_AREA = {AREA_CONSULTAS: "consultorio", AREA_IMAGENOLOGIA: "equipo", AREA_LABORATORIO: "puesto_laboratorio"}
_AREAS_EXAMEN = (AREA_IMAGENOLOGIA, AREA_LABORATORIO)
_ID_TIPO = re.compile(r"[A-Z0-9]{2,5}")
_ID_SUBTIPO = re.compile(r"[A-Z0-9]{2,5}-\d{2,}")
_PREFIJOS_RESERVADOS = ("ESP",)      # secuencia de las especialidades


def _donde(condiciones):
    return ("WHERE " + " AND ".join(condiciones)) if condiciones else ""


# ---------------------------------------------------------------------------
# Resumen
# ---------------------------------------------------------------------------
def resumen(administrador):
    fila = consultar(CUENTA, """
        SELECT (SELECT COUNT(*) FROM area) AS areas,
               (SELECT COUNT(*) FROM recurso_atencion) AS recursos,
               (SELECT COUNT(*) FROM tipo_procedimiento) AS tipos_examen,
               (SELECT COUNT(*) FROM subtipo_examen) AS subtipos_examen,
               (SELECT COUNT(*) FROM medicamento) AS medicamentos,
               (SELECT COUNT(*) FROM bloque_horario) AS bloques_horario""", id_usuario_app=administrador, uno=True)
    return {"resumen": fila}


# ---------------------------------------------------------------------------
# Areas
# ---------------------------------------------------------------------------
def listar_areas(administrador):
    return {"areas": consultar(CUENTA, """
        SELECT a.id_area, a.nombre, a.descripcion, a.estado,
               (SELECT COUNT(*) FROM recurso_atencion r WHERE r.id_area = a.id_area) AS recursos
        FROM area a ORDER BY a.id_area""", id_usuario_app=administrador)}


def obtener_area(id_area, administrador):
    fila = consultar(CUENTA, "SELECT id_area, nombre, descripcion, estado FROM area WHERE id_area = %s",
                     (id_area,), id_usuario_app=administrador, uno=True)
    if fila is None:
        raise ErrorNegocio("El área no existe.", 404)
    return fila


def actualizar_area(id_area, datos, administrador):
    obtener_area(id_area, administrador)
    nombre = validators.texto(datos.get("nombre"), "El nombre", maximo=50, minimo=3)
    descripcion = validators.texto(datos.get("descripcion"), "La descripción", maximo=255, obligatorio=False)
    estado = validators.opcion(datos.get("estado"), ESTADOS, "El estado")
    ejecutar(CUENTA, "UPDATE area SET nombre = %s, descripcion = %s, estado = %s WHERE id_area = %s",
             (nombre, descripcion, estado, id_area), id_usuario_app=administrador)
    log.info("Area %s modificada por el usuario %s", id_area, administrador)


# ---------------------------------------------------------------------------
# Recursos de atencion (consultorios, equipos, puestos de laboratorio)
# ---------------------------------------------------------------------------
def areas_para_formulario(administrador):
    return consultar(CUENTA, "SELECT id_area, nombre FROM area ORDER BY id_area", id_usuario_app=administrador)


def listar_recursos(administrador, id_area=None, estado=None):
    condiciones, parametros = [], []
    if id_area:
        condiciones.append("r.id_area = %s")
        parametros.append(id_area)
    if estado in ESTADOS_RECURSO:
        condiciones.append("r.estado = %s")
        parametros.append(estado)
    filas = consultar(CUENTA, f"""
        SELECT r.id_recurso, r.id_area, a.nombre AS area, r.nombre_recurso, r.tipo_recurso, r.descripcion, r.estado
        FROM recurso_atencion r JOIN area a ON a.id_area = r.id_area
        {_donde(condiciones)} ORDER BY r.id_area, r.nombre_recurso""", parametros, id_usuario_app=administrador)
    return {"recursos": filas, "areas": areas_para_formulario(administrador),
            "filtros": {"id_area": id_area or "", "estado": estado or ""}}


def obtener_recurso(id_recurso, administrador):
    fila = consultar(CUENTA, """
        SELECT id_recurso, id_area, nombre_recurso, tipo_recurso, descripcion, estado
        FROM recurso_atencion WHERE id_recurso = %s""", (id_recurso,), id_usuario_app=administrador, uno=True)
    if fila is None:
        raise ErrorNegocio("El recurso no existe.", 404)
    return fila


def crear_recurso(datos, administrador):
    id_area = validators.entero(datos.get("id_area"), "El área", minimo=1)
    obtener_area(id_area, administrador)
    tipo = validators.opcion(datos.get("tipo_recurso"), TIPOS_RECURSO, "El tipo de recurso")
    if _RECURSO_DE_AREA.get(id_area) != tipo:
        raise ErrorNegocio("El tipo de recurso no corresponde al área elegida.")
    nombre = validators.texto(datos.get("nombre_recurso"), "El nombre", maximo=80, minimo=2)
    descripcion = validators.texto(datos.get("descripcion"), "La descripción", maximo=255, obligatorio=False)
    resultado = ejecutar(CUENTA, """
        INSERT INTO recurso_atencion (id_area, nombre_recurso, tipo_recurso, descripcion) VALUES (%s, %s, %s, %s)""",
                         (id_area, nombre, tipo, descripcion), id_usuario_app=administrador)
    log.info("Recurso %s creado por el usuario %s", nombre, administrador)
    return resultado["id"]


def actualizar_recurso(id_recurso, datos, administrador):
    """El area y el tipo no cambian: las citas ya agendadas dependen de ellos."""
    obtener_recurso(id_recurso, administrador)
    nombre = validators.texto(datos.get("nombre_recurso"), "El nombre", maximo=80, minimo=2)
    descripcion = validators.texto(datos.get("descripcion"), "La descripción", maximo=255, obligatorio=False)
    estado = validators.opcion(datos.get("estado"), ESTADOS_RECURSO, "El estado")
    ejecutar(CUENTA, "UPDATE recurso_atencion SET nombre_recurso = %s, descripcion = %s, estado = %s "
                     "WHERE id_recurso = %s", (nombre, descripcion, estado, id_recurso), id_usuario_app=administrador)
    log.info("Recurso %s modificado por el usuario %s", id_recurso, administrador)


def eliminar_recurso(id_recurso, administrador):
    obtener_recurso(id_recurso, administrador)
    citas = consultar(CUENTA, "SELECT COUNT(*) AS total FROM cita WHERE id_recurso = %s", (id_recurso,),
                      id_usuario_app=administrador, uno=True)["total"]
    if citas:
        raise ErrorNegocio("Tiene citas registradas. Ponlo en mantenimiento o inactivo en lugar de eliminarlo.")
    ejecutar(CUENTA, "DELETE FROM recurso_atencion WHERE id_recurso = %s", (id_recurso,), id_usuario_app=administrador)
    log.info("Recurso %s eliminado por el usuario %s", id_recurso, administrador)


# ---------------------------------------------------------------------------
# Tipos de examen (RX, TAC, RM, DO, LAB)
# ---------------------------------------------------------------------------
def listar_tipos(administrador):
    filas = consultar(CUENTA, """
        SELECT t.id_tipo, t.id_area, a.nombre AS area, t.nombre, COUNT(s.id_subtipo) AS examenes
        FROM tipo_procedimiento t
        JOIN area a ON a.id_area = t.id_area
        LEFT JOIN subtipo_examen s ON s.id_tipo = t.id_tipo
        GROUP BY t.id_tipo, t.id_area, a.nombre, t.nombre
        ORDER BY t.id_area, t.id_tipo""", id_usuario_app=administrador)
    areas = [a for a in areas_para_formulario(administrador) if a["id_area"] in _AREAS_EXAMEN]
    return {"tipos": filas, "areas": areas}


def _codigo_tipo(valor):
    codigo = str(valor or "").strip().upper()
    if not _ID_TIPO.fullmatch(codigo):
        raise ErrorNegocio("El código debe tener de 2 a 5 letras o números (por ejemplo RX o TAC).")
    if codigo in _PREFIJOS_RESERVADOS:
        raise ErrorNegocio("Ese código está reservado por el sistema.")
    return codigo


def obtener_tipo(id_tipo, administrador):
    codigo = str(id_tipo or "").strip().upper()
    fila = consultar(CUENTA, "SELECT id_tipo, id_area, nombre FROM tipo_procedimiento WHERE id_tipo = %s",
                     (codigo,), id_usuario_app=administrador, uno=True)
    if fila is None:
        raise ErrorNegocio("El tipo de examen no existe.", 404)
    return fila


def crear_tipo(datos, administrador):
    codigo = _codigo_tipo(datos.get("id_tipo"))
    id_area = validators.entero(datos.get("id_area"), "El área", minimo=1)
    if id_area not in _AREAS_EXAMEN:
        raise ErrorNegocio("El área debe ser imagenología o laboratorio.")
    nombre = validators.texto(datos.get("nombre"), "El nombre", maximo=80, minimo=3)
    ejecutar(CUENTA, "INSERT INTO tipo_procedimiento (id_tipo, id_area, nombre) VALUES (%s, %s, %s)",
             (codigo, id_area, nombre), id_usuario_app=administrador)
    log.info("Tipo de examen %s creado por el usuario %s", codigo, administrador)
    return codigo


def actualizar_tipo(id_tipo, datos, administrador):
    """Solo cambia el nombre: el codigo y el area ya los usan los examenes."""
    actual = obtener_tipo(id_tipo, administrador)
    nombre = validators.texto(datos.get("nombre"), "El nombre", maximo=80, minimo=3)
    ejecutar(CUENTA, "UPDATE tipo_procedimiento SET nombre = %s WHERE id_tipo = %s", (nombre, actual["id_tipo"]),
             id_usuario_app=administrador)
    log.info("Tipo de examen %s modificado por el usuario %s", actual["id_tipo"], administrador)


def eliminar_tipo(id_tipo, administrador):
    actual = obtener_tipo(id_tipo, administrador)
    examenes = consultar(CUENTA, "SELECT COUNT(*) AS total FROM subtipo_examen WHERE id_tipo = %s",
                         (actual["id_tipo"],), id_usuario_app=administrador, uno=True)["total"]
    if examenes:
        raise ErrorNegocio("Tiene exámenes registrados. No se puede eliminar.")
    ejecutar(CUENTA, "DELETE FROM tipo_procedimiento WHERE id_tipo = %s", (actual["id_tipo"],),
             id_usuario_app=administrador)
    log.info("Tipo de examen %s eliminado por el usuario %s", actual["id_tipo"], administrador)


# ---------------------------------------------------------------------------
# Subtipos de examen (Craneo, Biometria hematica, ...)
# ---------------------------------------------------------------------------
def listar_subtipos(administrador, q=None, id_tipo=None, estado=None, pagina=1):
    condiciones, parametros = [], []
    patron = patron_like(q)
    if patron:
        condiciones.append("(s.id_subtipo LIKE %s OR s.nombre LIKE %s)")
        parametros += [patron] * 2
    if id_tipo:
        condiciones.append("s.id_tipo = %s")
        parametros.append(str(id_tipo).upper())
    if estado in ESTADOS:
        condiciones.append("s.estado = %s")
        parametros.append(estado)
    donde = _donde(condiciones)

    total = consultar(CUENTA, f"SELECT COUNT(*) AS total FROM subtipo_examen s {donde}", parametros,
                      id_usuario_app=administrador, uno=True)["total"]
    pag = paginar(total, pagina_actual(pagina), POR_PAGINA)
    filas = consultar(CUENTA, f"""
        SELECT s.id_subtipo, s.id_tipo, t.nombre AS tipo, a.nombre AS area, s.nombre, s.costo, s.estado
        FROM subtipo_examen s
        JOIN tipo_procedimiento t ON t.id_tipo = s.id_tipo
        JOIN area a ON a.id_area = t.id_area
        {donde} ORDER BY s.id_tipo, s.id_subtipo LIMIT %s OFFSET %s""",
                      parametros + [pag["por_pagina"], pag["offset"]], id_usuario_app=administrador)
    tipos = consultar(CUENTA, "SELECT id_tipo, nombre FROM tipo_procedimiento ORDER BY id_area, id_tipo",
                      id_usuario_app=administrador)
    return {"subtipos": filas, "paginacion": pag, "tipos": tipos,
            "filtros": {"q": q or "", "id_tipo": id_tipo or "", "estado": estado or ""}}


def obtener_subtipo(id_subtipo, administrador):
    codigo = str(id_subtipo or "").strip().upper()
    if not _ID_SUBTIPO.fullmatch(codigo):
        raise ErrorNegocio("El examen no existe.", 404)
    fila = consultar(CUENTA, "SELECT id_subtipo, id_tipo, nombre, costo, estado FROM subtipo_examen "
                             "WHERE id_subtipo = %s", (codigo,), id_usuario_app=administrador, uno=True)
    if fila is None:
        raise ErrorNegocio("El examen no existe.", 404)
    return fila


def _costo(valor):
    return validators.decimal(valor, "El costo", maximo=Decimal("99999.99"))


def crear_subtipo(datos, administrador):
    id_tipo = obtener_tipo(datos.get("id_tipo"), administrador)["id_tipo"]
    nombre = validators.texto(datos.get("nombre"), "El nombre", maximo=100, minimo=3)
    costo = _costo(datos.get("costo"))
    ejecutar(CUENTA, "INSERT INTO subtipo_examen (id_tipo, nombre, costo) VALUES (%s, %s, %s)",
             (id_tipo, nombre, costo), id_usuario_app=administrador)
    fila = consultar(CUENTA, "SELECT id_subtipo FROM subtipo_examen WHERE id_tipo = %s AND nombre = %s",
                     (id_tipo, nombre), id_usuario_app=administrador, uno=True)
    log.info("Examen %s creado por el usuario %s", fila["id_subtipo"], administrador)
    return fila["id_subtipo"]


def actualizar_subtipo(id_subtipo, datos, administrador):
    """El tipo no cambia. El nuevo costo se aplica a las citas que se registren desde ahora."""
    actual = obtener_subtipo(id_subtipo, administrador)
    nombre = validators.texto(datos.get("nombre"), "El nombre", maximo=100, minimo=3)
    costo = _costo(datos.get("costo"))
    estado = validators.opcion(datos.get("estado"), ESTADOS, "El estado")
    ejecutar(CUENTA, "UPDATE subtipo_examen SET nombre = %s, costo = %s, estado = %s WHERE id_subtipo = %s",
             (nombre, costo, estado, actual["id_subtipo"]), id_usuario_app=administrador)
    log.info("Examen %s modificado por el usuario %s", actual["id_subtipo"], administrador)


def eliminar_subtipo(id_subtipo, administrador):
    actual = obtener_subtipo(id_subtipo, administrador)
    usos = consultar(CUENTA, """
        SELECT (SELECT COUNT(*) FROM cita_imagenologia WHERE id_subtipo = %(s)s)
             + (SELECT COUNT(*) FROM cita_laboratorio WHERE id_subtipo = %(s)s) AS total""",
                     {"s": actual["id_subtipo"]}, id_usuario_app=administrador, uno=True)["total"]
    if usos:
        raise ErrorNegocio("Ya se usó en citas. Desactívalo en lugar de eliminarlo.")
    ejecutar(CUENTA, "DELETE FROM subtipo_examen WHERE id_subtipo = %s", (actual["id_subtipo"],),
             id_usuario_app=administrador)
    log.info("Examen %s eliminado por el usuario %s", actual["id_subtipo"], administrador)


# ---------------------------------------------------------------------------
# Medicamentos
# ---------------------------------------------------------------------------
def listar_medicamentos(administrador, q=None, estado=None, pagina=1):
    condiciones, parametros = [], []
    patron = patron_like(q)
    if patron:
        condiciones.append("(nombre LIKE %s OR presentacion LIKE %s OR concentracion LIKE %s)")
        parametros += [patron] * 3
    if estado in ESTADOS:
        condiciones.append("estado = %s")
        parametros.append(estado)
    donde = _donde(condiciones)

    total = consultar(CUENTA, f"SELECT COUNT(*) AS total FROM medicamento {donde}", parametros,
                      id_usuario_app=administrador, uno=True)["total"]
    pag = paginar(total, pagina_actual(pagina), POR_PAGINA)
    filas = consultar(CUENTA, f"""
        SELECT id_medicamento, nombre, presentacion, concentracion, estado FROM medicamento
        {donde} ORDER BY nombre, presentacion LIMIT %s OFFSET %s""",
                      parametros + [pag["por_pagina"], pag["offset"]], id_usuario_app=administrador)
    return {"medicamentos": filas, "paginacion": pag, "filtros": {"q": q or "", "estado": estado or ""}}


def obtener_medicamento(id_medicamento, administrador):
    fila = consultar(CUENTA, """SELECT id_medicamento, nombre, presentacion, concentracion, estado
                                FROM medicamento WHERE id_medicamento = %s""", (id_medicamento,),
                     id_usuario_app=administrador, uno=True)
    if fila is None:
        raise ErrorNegocio("El medicamento no existe.", 404)
    return fila


def _validar_medicamento(datos):
    return (validators.texto(datos.get("nombre"), "El nombre", maximo=120, minimo=2),
            validators.texto(datos.get("presentacion"), "La presentación", maximo=100, obligatorio=False),
            validators.texto(datos.get("concentracion"), "La concentración", maximo=80, obligatorio=False))


def crear_medicamento(datos, administrador):
    nombre, presentacion, concentracion = _validar_medicamento(datos)
    resultado = ejecutar(CUENTA, "INSERT INTO medicamento (nombre, presentacion, concentracion) VALUES (%s, %s, %s)",
                         (nombre, presentacion, concentracion), id_usuario_app=administrador)
    log.info("Medicamento %s creado por el usuario %s", nombre, administrador)
    return resultado["id"]


def actualizar_medicamento(id_medicamento, datos, administrador):
    obtener_medicamento(id_medicamento, administrador)
    nombre, presentacion, concentracion = _validar_medicamento(datos)
    estado = validators.opcion(datos.get("estado"), ESTADOS, "El estado")
    ejecutar(CUENTA, """UPDATE medicamento SET nombre = %s, presentacion = %s, concentracion = %s, estado = %s
                        WHERE id_medicamento = %s""",
             (nombre, presentacion, concentracion, estado, id_medicamento), id_usuario_app=administrador)
    log.info("Medicamento %s modificado por el usuario %s", id_medicamento, administrador)


def eliminar_medicamento(id_medicamento, administrador):
    obtener_medicamento(id_medicamento, administrador)
    usos = consultar(CUENTA, "SELECT COUNT(*) AS total FROM detalle_prescripcion WHERE id_medicamento = %s",
                     (id_medicamento,), id_usuario_app=administrador, uno=True)["total"]
    if usos:
        raise ErrorNegocio("Ya se recetó. Desactívalo en lugar de eliminarlo.")
    ejecutar(CUENTA, "DELETE FROM medicamento WHERE id_medicamento = %s", (id_medicamento,),
             id_usuario_app=administrador)
    log.info("Medicamento %s eliminado por el usuario %s", id_medicamento, administrador)


# ---------------------------------------------------------------------------
# Bloques horarios (solo lectura)
# ---------------------------------------------------------------------------
def listar_bloques(administrador):
    return {"bloques": consultar(CUENTA, "SELECT hora_inicio, hora_fin FROM bloque_horario ORDER BY hora_inicio",
                                 id_usuario_app=administrador)}