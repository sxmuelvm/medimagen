"""Especialidades medicas y el costo de su consulta (solo administrador).

El codigo (ESP-01, ESP-02...) lo asigna el trigger de MySQL al insertar.
"""
import re
from decimal import Decimal

from conexion.conexionBD import consultar, ejecutar
from utils import validators
from utils.constants import CUENTA_ADMINISTRADOR
from utils.errors import ErrorNegocio
from utils.helpers import pagina_actual, paginar, patron_like
from utils.logger import obtener_logger

log = obtener_logger("especialidades")

CUENTA = CUENTA_ADMINISTRADOR
ESTADOS = ("activo", "inactivo")
POR_PAGINA = 10
_CODIGO = re.compile(r"ESP-\d{2,}")


def _codigo(valor):
    codigo = str(valor or "").strip().upper()
    if not _CODIGO.fullmatch(codigo):
        raise ErrorNegocio("La especialidad no existe.", 404)
    return codigo


def listar(administrador, q=None, estado=None, pagina=1):
    condiciones, parametros = [], []
    patron = patron_like(q)
    if patron:
        condiciones.append("(e.id_especialidad LIKE %s OR e.nombre LIKE %s)")
        parametros += [patron] * 2
    if estado in ESTADOS:
        condiciones.append("e.estado = %s")
        parametros.append(estado)
    donde = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""

    total = consultar(CUENTA, f"SELECT COUNT(*) AS total FROM especialidad e {donde}", parametros,
                      id_usuario_app=administrador, uno=True)["total"]
    pag = paginar(total, pagina_actual(pagina), POR_PAGINA)
    filas = consultar(CUENTA, f"""
        SELECT e.id_especialidad, e.nombre, e.descripcion, e.costo_consulta, e.estado,
               COUNT(m.id_medico) AS medicos
        FROM especialidad e
        LEFT JOIN medico m ON m.id_especialidad = e.id_especialidad
        {donde}
        GROUP BY e.id_especialidad, e.nombre, e.descripcion, e.costo_consulta, e.estado
        ORDER BY e.id_especialidad LIMIT %s OFFSET %s""",
                      parametros + [pag["por_pagina"], pag["offset"]], id_usuario_app=administrador)
    return {"especialidades": filas, "paginacion": pag, "filtros": {"q": q or "", "estado": estado or ""}}


def obtener(codigo, administrador):
    codigo = _codigo(codigo)
    fila = consultar(CUENTA, """
        SELECT e.id_especialidad, e.nombre, e.descripcion, e.costo_consulta, e.estado,
               (SELECT COUNT(*) FROM medico m WHERE m.id_especialidad = e.id_especialidad) AS medicos
        FROM especialidad e WHERE e.id_especialidad = %s""", (codigo,), id_usuario_app=administrador, uno=True)
    if fila is None:
        raise ErrorNegocio("La especialidad no existe.", 404)
    return fila


def _validar(datos):
    return {
        "nombre": validators.texto(datos.get("nombre"), "El nombre", maximo=80, minimo=3),
        "descripcion": validators.texto(datos.get("descripcion"), "La descripción", maximo=255, obligatorio=False),
        "costo": validators.decimal(datos.get("costo_consulta"), "El costo de la consulta",
                                    maximo=Decimal("9999.99")),
    }


def crear(datos, administrador):
    v = _validar(datos)
    ejecutar(CUENTA, "INSERT INTO especialidad (nombre, descripcion, costo_consulta) VALUES (%s, %s, %s)",
             (v["nombre"], v["descripcion"], v["costo"]), id_usuario_app=administrador)
    fila = consultar(CUENTA, "SELECT id_especialidad FROM especialidad WHERE nombre = %s", (v["nombre"],),
                     id_usuario_app=administrador, uno=True)
    log.info("Especialidad %s creada por el usuario %s", fila["id_especialidad"], administrador)
    return fila["id_especialidad"]


def actualizar(codigo, datos, administrador):
    """El nuevo costo se aplica a las citas que se registren desde ahora. Las ya registradas conservan el suyo."""
    actual = obtener(codigo, administrador)
    v = _validar(datos)
    ejecutar(CUENTA, "UPDATE especialidad SET nombre = %s, descripcion = %s, costo_consulta = %s "
                     "WHERE id_especialidad = %s",
             (v["nombre"], v["descripcion"], v["costo"], actual["id_especialidad"]), id_usuario_app=administrador)
    log.info("Especialidad %s modificada por el usuario %s", actual["id_especialidad"], administrador)


def cambiar_estado(codigo, estado, administrador):
    estado = validators.opcion(estado, ESTADOS, "El estado")
    actual = obtener(codigo, administrador)
    ejecutar(CUENTA, "UPDATE especialidad SET estado = %s WHERE id_especialidad = %s",
             (estado, actual["id_especialidad"]), id_usuario_app=administrador)
    log.info("Especialidad %s pasa a %s (por el usuario %s)", actual["id_especialidad"], estado, administrador)


def eliminar(codigo, administrador):
    actual = obtener(codigo, administrador)
    if actual["medicos"]:
        raise ErrorNegocio("Tiene médicos asignados. Desactívala en lugar de eliminarla.")
    ejecutar(CUENTA, "DELETE FROM especialidad WHERE id_especialidad = %s", (actual["id_especialidad"],),
             id_usuario_app=administrador)
    log.info("Especialidad %s eliminada por el usuario %s", actual["id_especialidad"], administrador)