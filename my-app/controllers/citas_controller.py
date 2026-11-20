"""Citas: agenda, nueva cita, reprogramar, cambiar estado y eliminar.

Lo usan recepcion y el administrador, cada uno con su propia cuenta de MySQL (por eso todas las funciones reciben
`cuenta`). Las reglas de fondo las aplica la base de datos con sus triggers y restricciones: lunes a viernes, un
paciente no puede tener dos citas a la misma hora, un recurso (consultorio, equipo, puesto) ni un medico pueden
estar en dos citas a la vez, y el costo lo fija el trigger. Aqui se validan antes para dar mensajes claros.
"""
from conexion.conexionBD import consultar, ejecutar, transaccion
from utils import validators
from utils.constants import (AREA_CONSULTAS, AREA_IMAGENOLOGIA, AREA_LABORATORIO, CUENTA_ADMINISTRADOR,
                             ESTADOS_ACTIVOS_CITA, ESTADOS_CITA)
from utils.errors import ErrorNegocio
from utils.helpers import pagina_actual, paginar, patron_like
from utils.logger import obtener_logger

log = obtener_logger("citas")

POR_PAGINA = 15

_RECURSO_PLURAL = {AREA_CONSULTAS: "consultorios libres", AREA_IMAGENOLOGIA: "equipos libres",
                   AREA_LABORATORIO: "puestos de laboratorio libres"}

# Cambios de estado permitidos al personal administrativo. 'atendida' la marca quien atiende al paciente.
_TRANSICIONES = {
    "pendiente": ("confirmada", "cancelada", "no_asistio"),
    "confirmada": ("cancelada", "no_asistio"),
    "cancelada": ("pendiente",),
    "no_asistio": (),
    "atendida": (),
}

_SQL_CITA = """
    SELECT c.id_cita, c.fecha_cita, c.hora_inicio, c.hora_fin, c.estado, c.costo_aplicado, c.observacion,
           c.fecha_registro, c.cedula_paciente, CONCAT(p.nombres, ' ', p.apellidos) AS paciente,
           c.id_area, a.nombre AS area, c.id_recurso, r.nombre_recurso AS recurso,
           cc.id_medico, CONCAT(mc.nombres, ' ', mc.apellidos) AS medico, e.nombre AS especialidad,
           COALESCE(ci.id_subtipo, cl.id_subtipo) AS id_subtipo, COALESCE(si.nombre, sl.nombre) AS examen,
           COALESCE(ci.id_medico_solicitante, cl.id_medico_solicitante) AS id_medico_solicitante,
           CONCAT(ms.nombres, ' ', ms.apellidos) AS medico_solicitante,
           COALESCE(ci.estado_procedimiento, cl.estado_examen) AS estado_examen,
           COALESCE(e.nombre, si.nombre, sl.nombre) AS detalle,
           (TIMESTAMP(c.fecha_cita, c.hora_inicio) <= NOW()) AS ya_inicio
    FROM cita c
    JOIN paciente p ON p.cedula_paciente = c.cedula_paciente
    JOIN area a ON a.id_area = c.id_area
    JOIN recurso_atencion r ON r.id_recurso = c.id_recurso
    LEFT JOIN cita_consulta cc ON cc.id_cita = c.id_cita
    LEFT JOIN medico mc ON mc.id_medico = cc.id_medico
    LEFT JOIN especialidad e ON e.id_especialidad = mc.id_especialidad
    LEFT JOIN cita_imagenologia ci ON ci.id_cita = c.id_cita
    LEFT JOIN subtipo_examen si ON si.id_subtipo = ci.id_subtipo
    LEFT JOIN cita_laboratorio cl ON cl.id_cita = c.id_cita
    LEFT JOIN subtipo_examen sl ON sl.id_subtipo = cl.id_subtipo
    LEFT JOIN medico ms ON ms.id_medico = COALESCE(ci.id_medico_solicitante, cl.id_medico_solicitante)"""


# ---------------------------------------------------------------------------
# Apoyo
# ---------------------------------------------------------------------------
def _completar(fila):
    """Agrega lo que la pantalla necesita saber: si se puede modificar, eliminar y a que estados puede pasar."""
    fila["modificable"] = fila["estado"] in ESTADOS_ACTIVOS_CITA and fila["estado_examen"] != "realizado"
    fila["eliminable"] = fila["estado"] in ("pendiente", "cancelada")
    transiciones = list(_TRANSICIONES.get(fila["estado"], ()))
    if not fila["ya_inicio"] and "no_asistio" in transiciones:
        transiciones.remove("no_asistio")          # solo se marca "no asistio" cuando ya paso la hora de la cita
    if fila["estado_examen"] == "realizado":
        transiciones = []
    fila["transiciones"] = transiciones
    return fila


def _fecha_o_none(valor):
    try:
        return validators.fecha(valor)
    except ErrorNegocio:
        return None


def _hoy(cuenta, usuario):
    return consultar(cuenta, "SELECT CURDATE() AS hoy", id_usuario_app=usuario, uno=True)["hoy"]


def _hora_fin(hora):
    return f"{int(hora[:2]) + 1:02d}:00:00"


def _validar_futura(cuenta, usuario, fecha, hora):
    fila = consultar(cuenta, "SELECT TIMESTAMP(%s, %s) > NOW() AS futura", (fecha, hora),
                     id_usuario_app=usuario, uno=True)
    if not fila["futura"]:
        raise ErrorNegocio("La cita debe ser en una fecha y hora futuras.")


def _texto_estado(estado):
    return estado.replace("_", " ")


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------
def agenda(cuenta, usuario, q=None, id_area=None, estado=None, desde=None, hasta=None, pagina=1):
    """Lista de citas desde la fecha indicada (por defecto, desde hoy), de todas las areas."""
    desde_f = _fecha_o_none(desde) or _hoy(cuenta, usuario)
    hasta_f = _fecha_o_none(hasta)
    condiciones, parametros = ["c.fecha_cita >= %s"], [desde_f]
    if hasta_f:
        condiciones.append("c.fecha_cita <= %s")
        parametros.append(hasta_f)
    patron = patron_like(q)
    if patron:
        condiciones.append("(c.cedula_paciente LIKE %s OR p.nombres LIKE %s OR p.apellidos LIKE %s "
                           "OR CONCAT(p.nombres, ' ', p.apellidos) LIKE %s)")
        parametros += [patron] * 4
    area = None
    try:
        area = validators.entero(id_area, "El área", minimo=1, maximo=3) if id_area else None
    except ErrorNegocio:
        area = None
    if area:
        condiciones.append("c.id_area = %s")
        parametros.append(area)
    if estado in ESTADOS_CITA:
        condiciones.append("c.estado = %s")
        parametros.append(estado)
    donde = "WHERE " + " AND ".join(condiciones)

    total = consultar(cuenta, f"""SELECT COUNT(*) AS total FROM cita c
                                  JOIN paciente p ON p.cedula_paciente = c.cedula_paciente {donde}""",
                      parametros, id_usuario_app=usuario, uno=True)["total"]
    pag = paginar(total, pagina_actual(pagina), POR_PAGINA)
    filas = consultar(cuenta, f"{_SQL_CITA} {donde} ORDER BY c.fecha_cita, c.hora_inicio, c.id_cita LIMIT %s OFFSET %s",
                      parametros + [pag["por_pagina"], pag["offset"]], id_usuario_app=usuario)
    return {"citas": [_completar(f) for f in filas], "paginacion": pag,
            "areas": consultar(cuenta, "SELECT id_area, nombre FROM area ORDER BY id_area", id_usuario_app=usuario),
            "estados": ESTADOS_CITA,
            "filtros": {"q": q or "", "id_area": area or "", "estado": estado or "",
                        "desde": desde_f.isoformat(), "hasta": hasta_f.isoformat() if hasta_f else ""}}


def obtener(cuenta, usuario, id_cita):
    fila = consultar(cuenta, f"{_SQL_CITA} WHERE c.id_cita = %s", (id_cita,), id_usuario_app=usuario, uno=True)
    if fila is None:
        raise ErrorNegocio("La cita no existe.", 404)
    return _completar(fila)


def detalle(cuenta, usuario, id_cita):
    """La cita y, solo para el administrador, su historial de cambios (recepcion no puede leer la auditoria)."""
    cita = obtener(cuenta, usuario, id_cita)
    historial = []
    if cuenta == CUENTA_ADMINISTRADOR:
        historial = consultar(cuenta, """
            SELECT fecha_cambio, estado_anterior, estado_nuevo, fecha_anterior, fecha_nueva, hora_anterior,
                   hora_nueva, usuario_bd, id_usuario_app
            FROM auditoria_cita WHERE id_cita = %s ORDER BY fecha_cambio, id_auditoria""",
                              (id_cita,), id_usuario_app=usuario)
    return {"cita": cita, "historial": historial}


def buscar_paciente(cuenta, usuario, cedula):
    """Paciente por cedula (para el formulario de nueva cita). None si no existe o la cedula no es valida."""
    try:
        cedula = validators.cedula(cedula)
    except ErrorNegocio:
        return None
    return consultar(cuenta, """
        SELECT cedula_paciente, nombres, apellidos, estado, TIMESTAMPDIFF(YEAR, fecha_nacimiento, CURDATE()) AS edad
        FROM paciente WHERE cedula_paciente = %s""", (cedula,), id_usuario_app=usuario, uno=True)


def opciones_nueva(cuenta, usuario, cedula=None):
    """Listas para el formulario de nueva cita y para reprogramar."""
    return {
        "paciente": buscar_paciente(cuenta, usuario, cedula) if cedula else None,
        "areas": consultar(cuenta, "SELECT id_area, nombre FROM area WHERE estado = 'activo' ORDER BY id_area",
                           id_usuario_app=usuario),
        "medicos": consultar(cuenta, """
            SELECT m.id_medico, CONCAT(m.nombres, ' ', m.apellidos) AS nombre, e.nombre AS especialidad,
                   e.costo_consulta
            FROM medico m JOIN especialidad e ON e.id_especialidad = m.id_especialidad
            WHERE m.estado = 'activo' AND e.estado = 'activo'
            ORDER BY m.apellidos, m.nombres""", id_usuario_app=usuario),
        "recursos": consultar(cuenta, """
            SELECT id_recurso, id_area, nombre_recurso, tipo_recurso FROM recurso_atencion
            WHERE estado = 'activo' ORDER BY id_area, nombre_recurso""", id_usuario_app=usuario),
        "examenes": consultar(cuenta, """
            SELECT s.id_subtipo, s.nombre, s.costo, t.id_tipo, t.nombre AS tipo, t.id_area
            FROM subtipo_examen s JOIN tipo_procedimiento t ON t.id_tipo = s.id_tipo
            WHERE s.estado = 'activo' ORDER BY t.id_area, t.id_tipo, s.nombre""", id_usuario_app=usuario),
    }


def horarios_disponibles(cuenta, usuario, fecha, id_area, id_medico=None, id_recurso=None,
                         cedula_paciente=None, excluir_cita=None):
    """Bloques de una hora libres en una fecha. Un bloque esta libre si hay un recurso activo del area sin cita
    en ese horario y, segun lo que se indique, el medico (dentro de sus turnos) y el paciente tampoco tienen
    otra cita a esa hora."""
    dia = validators.fecha(fecha, "La fecha")
    area = validators.entero(id_area, "El área", minimo=1, maximo=3)
    if dia.weekday() >= 5:
        return []

    p = {"f": dia, "a": area, "x": validators.entero(excluir_cita, "La cita", minimo=1) if excluir_cita else 0}
    recurso_extra = ""
    if id_recurso:
        p["r"] = validators.entero(id_recurso, "El recurso", minimo=1)
        recurso_extra = " AND r.id_recurso = %(r)s"
    medico_extra = ""
    if id_medico and area == AREA_CONSULTAS:
        p["m"] = validators.entero(id_medico, "El médico", minimo=1)
        medico_extra = """
          AND NOT EXISTS (SELECT 1 FROM cita c JOIN cita_consulta cc ON cc.id_cita = c.id_cita
                          WHERE cc.id_medico = %(m)s AND c.fecha_cita = %(f)s AND c.hora_inicio = b.hora_inicio
                            AND c.activa = 1 AND c.id_cita <> %(x)s)
          AND (NOT EXISTS (SELECT 1 FROM horario_medico h0 WHERE h0.id_medico = %(m)s)
               OR EXISTS (SELECT 1 FROM horario_medico h
                          WHERE h.id_medico = %(m)s AND h.dia_semana = WEEKDAY(%(f)s) + 1
                            AND h.hora_inicio <= b.hora_inicio AND b.hora_fin <= h.hora_fin))"""
    paciente_extra = ""
    if cedula_paciente:
        p["p"] = validators.cedula(cedula_paciente, "La cédula del paciente")
        paciente_extra = """
          AND NOT EXISTS (SELECT 1 FROM cita c WHERE c.cedula_paciente = %(p)s AND c.fecha_cita = %(f)s
                            AND c.hora_inicio = b.hora_inicio AND c.activa = 1 AND c.id_cita <> %(x)s)"""

    filas = consultar(cuenta, f"""
        SELECT b.hora_inicio, b.hora_fin
        FROM bloque_horario b
        WHERE TIMESTAMP(%(f)s, b.hora_inicio) > NOW()
          AND EXISTS (SELECT 1 FROM recurso_atencion r
                      WHERE r.id_area = %(a)s AND r.estado = 'activo'{recurso_extra}
                        AND NOT EXISTS (SELECT 1 FROM cita c WHERE c.id_recurso = r.id_recurso
                                          AND c.fecha_cita = %(f)s AND c.hora_inicio = b.hora_inicio
                                          AND c.activa = 1 AND c.id_cita <> %(x)s)){medico_extra}{paciente_extra}
        ORDER BY b.hora_inicio""", p, id_usuario_app=usuario)

    def _hm(valor):
        segundos = int(valor.total_seconds())
        return f"{segundos // 3600:02d}:{(segundos % 3600) // 60:02d}"

    return [{"hora_inicio": _hm(f["hora_inicio"]), "hora_fin": _hm(f["hora_fin"])} for f in filas]


# ---------------------------------------------------------------------------
# Validaciones de lo que se elige en el formulario
# ---------------------------------------------------------------------------
def _medico_activo(cuenta, usuario, valor, etiqueta, area):
    id_medico = validators.entero(valor, etiqueta, minimo=1)
    fila = consultar(cuenta, """
        SELECT m.estado, e.estado AS estado_especialidad
        FROM medico m JOIN especialidad e ON e.id_especialidad = m.id_especialidad
        WHERE m.id_medico = %s""", (id_medico,), id_usuario_app=usuario, uno=True)
    if fila is None:
        raise ErrorNegocio(f"{etiqueta} no existe.")
    if fila["estado"] != "activo":
        raise ErrorNegocio(f"{etiqueta} está inactivo.")
    if area == AREA_CONSULTAS and fila["estado_especialidad"] != "activo":
        raise ErrorNegocio("La especialidad de ese médico está inactiva.")
    return id_medico


def _subtipo_activo(cuenta, usuario, valor, area):
    codigo = str(valor or "").strip().upper()
    if not codigo:
        raise ErrorNegocio("Elige el examen.")
    fila = consultar(cuenta, """
        SELECT s.estado, t.id_area FROM subtipo_examen s JOIN tipo_procedimiento t ON t.id_tipo = s.id_tipo
        WHERE s.id_subtipo = %s""", (codigo,), id_usuario_app=usuario, uno=True)
    if fila is None:
        raise ErrorNegocio("El examen no existe.")
    if fila["estado"] != "activo":
        raise ErrorNegocio("El examen está inactivo.")
    if fila["id_area"] != area:
        raise ErrorNegocio("El examen no corresponde al área elegida.")
    return codigo


def _recurso_valido(cuenta, usuario, valor, area):
    id_recurso = validators.entero(valor, "El recurso", minimo=1)
    fila = consultar(cuenta, "SELECT id_area, estado FROM recurso_atencion WHERE id_recurso = %s", (id_recurso,),
                     id_usuario_app=usuario, uno=True)
    if fila is None or fila["id_area"] != area:
        raise ErrorNegocio("El consultorio, equipo o puesto elegido no corresponde al área.")
    if fila["estado"] != "activo":
        raise ErrorNegocio("Ese consultorio, equipo o puesto no está disponible (inactivo o en mantenimiento).")
    return id_recurso


def _recurso_libre(cursor, area, fecha, hora, preferido=None, excluir=None):
    """Primer recurso activo del area que este libre en ese horario (se prefiere `preferido` si esta libre)."""
    cursor.execute("""
        SELECT r.id_recurso FROM recurso_atencion r
        WHERE r.id_area = %s AND r.estado = 'activo'
          AND NOT EXISTS (SELECT 1 FROM cita c WHERE c.id_recurso = r.id_recurso AND c.fecha_cita = %s
                            AND c.hora_inicio = %s AND c.activa = 1 AND c.id_cita <> %s)
        ORDER BY (r.id_recurso = %s) DESC, r.id_recurso LIMIT 1""",
                   (area, fecha, hora, excluir or 0, preferido or 0))
    fila = cursor.fetchone()
    if fila is None:
        raise ErrorNegocio(f"No hay {_RECURSO_PLURAL[area]} en ese horario.")
    return fila["id_recurso"]


# ---------------------------------------------------------------------------
# Crear
# ---------------------------------------------------------------------------
def paciente_activo(cuenta, usuario, valor):
    """Valida la cedula y que el paciente exista y este activo. Devuelve la cedula."""
    cedula = validators.cedula(valor, "La cédula del paciente")
    paciente = consultar(cuenta, "SELECT estado FROM paciente WHERE cedula_paciente = %s", (cedula,),
                         id_usuario_app=usuario, uno=True)
    if paciente is None:
        raise ErrorNegocio("El paciente no está registrado. Regístralo primero.")
    if paciente["estado"] != "activo":
        raise ErrorNegocio("El paciente está inactivo.")
    return cedula


def crear(cuenta, usuario, datos):
    """Registra una cita de consulta, imagenologia o laboratorio. Devuelve {'id_cita', 'id_recurso'}."""
    cedula = paciente_activo(cuenta, usuario, datos.get("cedula_paciente"))
    area = validators.entero(datos.get("id_area"), "El área", minimo=1, maximo=3)
    fila_area = consultar(cuenta, "SELECT estado FROM area WHERE id_area = %s", (area,), id_usuario_app=usuario, uno=True)
    if fila_area is None or fila_area["estado"] != "activo":
        raise ErrorNegocio("El área seleccionada no está disponible.")
    return registrar_cita(cuenta, usuario, cedula, area, datos)


def registrar_cita(cuenta, usuario, cedula, area, datos):
    """Valida horario, medico, examen y recurso, y guarda la cita con su detalle en una sola transaccion.

    - Consulta: se elige el medico; el consultorio se asigna solo si no se indica.
    - Imagenologia: se elige el equipo, el examen y el medico que lo solicita.
    - Laboratorio: se elige el examen y el medico que lo solicita; el puesto se asigna solo si no se indica.
    Lo usan recepcion, el administrador y el medico (cuando solicita un examen).
    """
    fecha = validators.fecha_laborable(datos.get("fecha_cita"))
    hora = validators.hora_bloque(datos.get("hora_inicio"))
    _validar_futura(cuenta, usuario, fecha, hora)

    id_medico = id_subtipo = None
    if area == AREA_CONSULTAS:
        id_medico = _medico_activo(cuenta, usuario, datos.get("id_medico"), "El médico", area)
    else:
        id_medico = _medico_activo(cuenta, usuario, datos.get("id_medico_solicitante"), "El médico solicitante", area)
        id_subtipo = _subtipo_activo(cuenta, usuario, datos.get("id_subtipo"), area)

    id_recurso = None
    if datos.get("id_recurso"):
        id_recurso = _recurso_valido(cuenta, usuario, datos.get("id_recurso"), area)
    elif area == AREA_IMAGENOLOGIA:
        raise ErrorNegocio("Elige el equipo para el examen.")
    observacion = validators.texto(datos.get("observacion"), "La observación", maximo=255, obligatorio=False)

    with transaccion(cuenta, usuario) as cursor:
        if id_recurso is None:
            id_recurso = _recurso_libre(cursor, area, fecha, hora)
        cursor.execute("""
            INSERT INTO cita (cedula_paciente, id_area, id_recurso, id_usuario_registra, fecha_cita, hora_inicio,
                              hora_fin, observacion)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                       (cedula, area, id_recurso, usuario, fecha, hora, _hora_fin(hora), observacion))
        id_cita = cursor.lastrowid
        if area == AREA_CONSULTAS:
            cursor.execute("INSERT INTO cita_consulta (id_cita, id_medico) VALUES (%s, %s)", (id_cita, id_medico))
        elif area == AREA_IMAGENOLOGIA:
            cursor.execute("""INSERT INTO cita_imagenologia (id_cita, id_medico_solicitante, id_subtipo)
                              VALUES (%s, %s, %s)""", (id_cita, id_medico, id_subtipo))
        else:
            cursor.execute("""INSERT INTO cita_laboratorio (id_cita, id_medico_solicitante, id_subtipo)
                              VALUES (%s, %s, %s)""", (id_cita, id_medico, id_subtipo))
    log.info("Cita %s creada: paciente %s, area %s, %s %s (cuenta %s, usuario %s)",
             id_cita, cedula, area, fecha, hora, cuenta, usuario)
    return {"id_cita": id_cita, "id_recurso": id_recurso}


# ---------------------------------------------------------------------------
# Modificar
# ---------------------------------------------------------------------------
def reprogramar(cuenta, usuario, id_cita, datos):
    """Cambia fecha, hora, consultorio/equipo/puesto y observacion de una cita pendiente o confirmada.
    Para cambiar de medico o de examen se cancela la cita y se registra otra."""
    cita = obtener(cuenta, usuario, id_cita)
    if not cita["modificable"]:
        raise ErrorNegocio("Esta cita ya no se puede modificar.")
    area = cita["id_area"]

    fecha = validators.fecha_laborable(datos.get("fecha_cita"))
    hora = validators.hora_bloque(datos.get("hora_inicio"))
    _validar_futura(cuenta, usuario, fecha, hora)
    observacion = validators.texto(datos.get("observacion", cita["observacion"]), "La observación", maximo=255,
                                   obligatorio=False)

    pedido = _recurso_valido(cuenta, usuario, datos.get("id_recurso"), area) if datos.get("id_recurso") else None
    with transaccion(cuenta, usuario) as cursor:
        if pedido is not None:
            id_recurso = pedido
        elif area == AREA_IMAGENOLOGIA:
            id_recurso = cita["id_recurso"]            # cada equipo hace examenes distintos: no se cambia solo
        else:
            id_recurso = _recurso_libre(cursor, area, fecha, hora, preferido=cita["id_recurso"], excluir=id_cita)
        cursor.execute("""
            UPDATE cita SET fecha_cita = %s, hora_inicio = %s, hora_fin = %s, id_recurso = %s, observacion = %s
            WHERE id_cita = %s""", (fecha, hora, _hora_fin(hora), id_recurso, observacion, id_cita))
    log.info("Cita %s reprogramada a %s %s (cuenta %s, usuario %s)", id_cita, fecha, hora, cuenta, usuario)
    return {"id_cita": id_cita, "id_recurso": id_recurso}


def cambiar_estado(cuenta, usuario, id_cita, nuevo):
    """Confirma, cancela, marca 'no asistio' o reactiva (cancelada -> pendiente). 'atendida' no se marca aqui."""
    nuevo = validators.opcion(nuevo, ESTADOS_CITA, "El estado")
    cita = obtener(cuenta, usuario, id_cita)
    if nuevo not in cita["transiciones"]:
        if nuevo == "no_asistio" and cita["estado"] in ("pendiente", "confirmada") and not cita["ya_inicio"]:
            raise ErrorNegocio("Solo se marca 'no asistió' cuando ya pasó la hora de la cita.")
        raise ErrorNegocio(f"No se puede pasar una cita {_texto_estado(cita['estado'])} "
                           f"a {_texto_estado(nuevo)}.")
    if nuevo == "pendiente":
        _validar_futura(cuenta, usuario, cita["fecha_cita"], cita["hora_inicio"])

    estado_examen = "pendiente" if nuevo == "pendiente" else "cancelado"
    with transaccion(cuenta, usuario) as cursor:
        cursor.execute("UPDATE cita SET estado = %s WHERE id_cita = %s", (nuevo, id_cita))
        if nuevo != "confirmada":
            if cita["id_area"] == AREA_IMAGENOLOGIA:
                cursor.execute("UPDATE cita_imagenologia SET estado_procedimiento = %s WHERE id_cita = %s",
                               (estado_examen, id_cita))
            elif cita["id_area"] == AREA_LABORATORIO:
                cursor.execute("UPDATE cita_laboratorio SET estado_examen = %s WHERE id_cita = %s",
                               (estado_examen, id_cita))
    log.info("Cita %s pasa de %s a %s (cuenta %s, usuario %s)", id_cita, cita["estado"], nuevo, cuenta, usuario)


def eliminar(cuenta, usuario, id_cita):
    """Solo citas pendientes o canceladas (registradas por error). El resto queda en el historial."""
    cita = obtener(cuenta, usuario, id_cita)
    if not cita["eliminable"]:
        raise ErrorNegocio("Solo se pueden eliminar citas pendientes o canceladas.")
    ejecutar(cuenta, "DELETE FROM cita WHERE id_cita = %s", (id_cita,), id_usuario_app=usuario)
    log.info("Cita %s eliminada (cuenta %s, usuario %s)", id_cita, cuenta, usuario)