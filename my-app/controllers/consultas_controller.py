"""Medico: su agenda, atender consultas (diagnostico y receta) y solicitar examenes de imagenologia o laboratorio.

Todo se hace con la cuenta de MySQL del medico y siempre limitado a SUS citas: el id del medico sale de la sesion,
nunca del formulario.
"""
from conexion.conexionBD import consultar, transaccion
from controllers import citas_controller as citas
from utils import validators
from utils.constants import AREA_CONSULTAS, CUENTA_MEDICO, ESTADOS_ACTIVOS_CITA, ESTADOS_CITA
from utils.errors import ErrorNegocio
from utils.helpers import pagina_actual, paginar, patron_like
from utils.logger import obtener_logger

log = obtener_logger("consultas")

POR_PAGINA = 15

_SQL_CITA_PROPIA = """
    SELECT c.id_cita, c.fecha_cita, c.hora_inicio, c.hora_fin, c.estado, c.observacion, c.cedula_paciente,
           CONCAT(p.nombres, ' ', p.apellidos) AS paciente, TIMESTAMPDIFF(YEAR, p.fecha_nacimiento, CURDATE()) AS edad,
           r.nombre_recurso AS consultorio, cm.id_consulta,
           (c.fecha_cita <= CURDATE()) AS llego_el_dia
    FROM cita c
    JOIN cita_consulta cc ON cc.id_cita = c.id_cita
    JOIN paciente p ON p.cedula_paciente = c.cedula_paciente
    JOIN recurso_atencion r ON r.id_recurso = c.id_recurso
    LEFT JOIN consulta_medica cm ON cm.id_cita = c.id_cita"""


def _completar(fila):
    fila["puede_atender"] = fila["estado"] in ESTADOS_ACTIVOS_CITA and bool(fila["llego_el_dia"])
    return fila


def _fecha_o_none(valor):
    try:
        return validators.fecha(valor)
    except ErrorNegocio:
        return None


def _hoy(usuario):
    return consultar(CUENTA_MEDICO, "SELECT CURDATE() AS hoy", id_usuario_app=usuario, uno=True)["hoy"]


# ---------------------------------------------------------------------------
# Agenda y consulta
# ---------------------------------------------------------------------------
def mi_agenda(usuario, id_medico, q=None, estado=None, desde=None, hasta=None, pagina=1):
    """Citas del medico desde la fecha indicada (por defecto, desde hoy)."""
    desde_f = _fecha_o_none(desde) or _hoy(usuario)
    hasta_f = _fecha_o_none(hasta)
    condiciones, parametros = ["cc.id_medico = %s", "c.fecha_cita >= %s"], [id_medico, desde_f]
    if hasta_f:
        condiciones.append("c.fecha_cita <= %s")
        parametros.append(hasta_f)
    patron = patron_like(q)
    if patron:
        condiciones.append("(c.cedula_paciente LIKE %s OR CONCAT(p.nombres, ' ', p.apellidos) LIKE %s)")
        parametros += [patron, patron]
    if estado in ESTADOS_CITA:
        condiciones.append("c.estado = %s")
        parametros.append(estado)
    donde = "WHERE " + " AND ".join(condiciones)

    total = consultar(CUENTA_MEDICO, f"""
        SELECT COUNT(*) AS total FROM cita c JOIN cita_consulta cc ON cc.id_cita = c.id_cita
        JOIN paciente p ON p.cedula_paciente = c.cedula_paciente {donde}""",
                      parametros, id_usuario_app=usuario, uno=True)["total"]
    pag = paginar(total, pagina_actual(pagina), POR_PAGINA)
    filas = consultar(CUENTA_MEDICO, f"{_SQL_CITA_PROPIA} {donde} ORDER BY c.fecha_cita, c.hora_inicio LIMIT %s OFFSET %s",
                      parametros + [pag["por_pagina"], pag["offset"]], id_usuario_app=usuario)
    return {"citas": [_completar(f) for f in filas], "paginacion": pag, "estados": ESTADOS_CITA,
            "filtros": {"q": q or "", "estado": estado or "", "desde": desde_f.isoformat(),
                        "hasta": hasta_f.isoformat() if hasta_f else ""}}


def cita_propia(usuario, id_medico, id_cita):
    """Cita de consulta del medico. Si es de otro medico se responde 'no existe' (no se revela nada)."""
    fila = consultar(CUENTA_MEDICO, f"{_SQL_CITA_PROPIA} WHERE c.id_cita = %s AND cc.id_medico = %s",
                     (id_cita, id_medico), id_usuario_app=usuario, uno=True)
    if fila is None:
        raise ErrorNegocio("La cita no existe.", 404)
    return _completar(fila)


def detalle_consulta(usuario, id_consulta):
    consulta = consultar(CUENTA_MEDICO, """
        SELECT id_consulta, id_cita, fecha_hora_atencion, motivo_consulta, observaciones
        FROM consulta_medica WHERE id_consulta = %s""", (id_consulta,), id_usuario_app=usuario, uno=True)
    diagnosticos = consultar(CUENTA_MEDICO, """
        SELECT descripcion, observacion, fecha_registro FROM diagnostico WHERE id_consulta = %s
        ORDER BY id_diagnostico""", (id_consulta,), id_usuario_app=usuario)
    receta = consultar(CUENTA_MEDICO, """
        SELECT id_prescripcion, fecha_prescripcion, indicaciones_generales FROM prescripcion
        WHERE id_consulta = %s""", (id_consulta,), id_usuario_app=usuario, uno=True)
    medicamentos = []
    if receta:
        medicamentos = consultar(CUENTA_MEDICO, """
            SELECT m.nombre, m.presentacion, m.concentracion, d.dosis, d.frecuencia, d.duracion, d.indicaciones
            FROM detalle_prescripcion d JOIN medicamento m ON m.id_medicamento = d.id_medicamento
            WHERE d.id_prescripcion = %s ORDER BY d.id_detalle""", (receta["id_prescripcion"],),
                               id_usuario_app=usuario)
    return {"consulta": consulta, "diagnosticos": diagnosticos, "receta": receta, "medicamentos": medicamentos}


def historial_paciente(usuario, cedula, limite=5):
    """Ultimas consultas y recetas del paciente, para tener contexto al atenderlo."""
    consultas = consultar(CUENTA_MEDICO, """
        SELECT id_consulta, fecha_hora_atencion, medico, especialidad, motivo_consulta, diagnostico
        FROM v_historial_paciente WHERE cedula_paciente = %s
        ORDER BY fecha_hora_atencion DESC, id_consulta DESC LIMIT %s""", (cedula, limite), id_usuario_app=usuario)
    recetas = consultar(CUENTA_MEDICO, """
        SELECT fecha_prescripcion, medico, medicamento, concentracion, dosis, frecuencia, duracion
        FROM v_recetas WHERE cedula_paciente = %s
        ORDER BY fecha_prescripcion DESC, id_prescripcion DESC LIMIT %s""", (cedula, limite * 2),
                      id_usuario_app=usuario)
    return {"consultas": consultas, "recetas": recetas}


def preparar_atencion(usuario, id_medico, id_cita):
    """Todo lo que necesita la pantalla de atencion. Si la consulta ya se registro, incluye su detalle."""
    cita = cita_propia(usuario, id_medico, id_cita)
    datos = {"cita": cita,
             "medicamentos": consultar(CUENTA_MEDICO, """
                 SELECT id_medicamento, nombre, presentacion, concentracion FROM medicamento
                 WHERE estado = 'activo' ORDER BY nombre, concentracion""", id_usuario_app=usuario),
             "historial": historial_paciente(usuario, cita["cedula_paciente"])}
    datos["registrada"] = detalle_consulta(usuario, cita["id_consulta"]) if cita["id_consulta"] else None
    return datos


# ---------------------------------------------------------------------------
# Atender
# ---------------------------------------------------------------------------
def _limpiar_diagnosticos(diagnosticos):
    lista = []
    for fila in diagnosticos or []:
        descripcion = validators.texto(fila.get("descripcion"), "El diagnóstico", maximo=500, obligatorio=False)
        observacion = validators.texto(fila.get("observacion"), "La observación del diagnóstico", maximo=2000,
                                       obligatorio=False)
        if descripcion is None and observacion is None:
            continue                                   # fila vacia del formulario
        if descripcion is None:
            raise ErrorNegocio("Escribe el diagnóstico o quita la observación suelta.")
        lista.append((descripcion, observacion))
    if not lista:
        raise ErrorNegocio("Registra al menos un diagnóstico.")
    return lista


def _limpiar_receta(cuenta, usuario, medicamentos):
    lista, vistos = [], set()
    for fila in medicamentos or []:
        campos = [str(fila.get(k) or "").strip() for k in ("id_medicamento", "dosis", "frecuencia", "duracion", "indicaciones")]
        if not any(campos):
            continue                                   # fila vacia del formulario
        id_medicamento = validators.entero(fila.get("id_medicamento"), "El medicamento", minimo=1)
        if id_medicamento in vistos:
            raise ErrorNegocio("No repitas el mismo medicamento en la receta.")
        vistos.add(id_medicamento)
        existe = consultar(cuenta, "SELECT estado FROM medicamento WHERE id_medicamento = %s", (id_medicamento,),
                           id_usuario_app=usuario, uno=True)
        if existe is None:
            raise ErrorNegocio("El medicamento no existe.")
        if existe["estado"] != "activo":
            raise ErrorNegocio("Uno de los medicamentos está inactivo.")
        lista.append((id_medicamento,
                      validators.texto(fila.get("dosis"), "La dosis", maximo=100),
                      validators.texto(fila.get("frecuencia"), "La frecuencia", maximo=100),
                      validators.texto(fila.get("duracion"), "La duración", maximo=100),
                      validators.texto(fila.get("indicaciones"), "Las indicaciones del medicamento", maximo=1000,
                                       obligatorio=False)))
    return lista


def atender(usuario, id_medico, id_cita, datos, diagnosticos, medicamentos):
    """Registra la consulta (motivo, diagnosticos y receta opcional) y deja la cita como 'atendida'.

    La consulta solo se atiende desde el dia de la cita y una sola vez. Todo se guarda en una transaccion.
    """
    cita = cita_propia(usuario, id_medico, id_cita)
    if cita["estado"] not in ESTADOS_ACTIVOS_CITA or cita["id_consulta"]:
        raise ErrorNegocio("Esta cita ya no se puede atender.")
    if not cita["llego_el_dia"]:
        raise ErrorNegocio("La consulta se atiende el día de la cita, no antes.")

    motivo = validators.texto(datos.get("motivo_consulta"), "El motivo de consulta", maximo=255)
    observaciones = validators.texto(datos.get("observaciones"), "Las observaciones", maximo=5000, obligatorio=False)
    lista_dx = _limpiar_diagnosticos(diagnosticos)
    lista_rx = _limpiar_receta(CUENTA_MEDICO, usuario, medicamentos)
    indicaciones = validators.texto(datos.get("indicaciones_generales"), "Las indicaciones generales", maximo=2000,
                                    obligatorio=False)
    if indicaciones and not lista_rx:
        raise ErrorNegocio("Agrega al menos un medicamento a la receta o deja las indicaciones generales vacías.")

    with transaccion(CUENTA_MEDICO, usuario) as cursor:
        # Cambiar el estado primero sirve de candado: si otra pestana ya la atendio, no se modifica ninguna fila.
        cursor.execute("""UPDATE cita SET estado = 'atendida'
                          WHERE id_cita = %s AND estado IN ('pendiente', 'confirmada')""", (id_cita,))
        if cursor.rowcount != 1:
            raise ErrorNegocio("Esta cita ya no se puede atender.")
        cursor.execute("""INSERT INTO consulta_medica (id_cita, fecha_hora_atencion, motivo_consulta, observaciones)
                          VALUES (%s, NOW(), %s, %s)""", (id_cita, motivo, observaciones))
        id_consulta = cursor.lastrowid
        for descripcion, observacion in lista_dx:
            cursor.execute("INSERT INTO diagnostico (id_consulta, descripcion, observacion) VALUES (%s, %s, %s)",
                           (id_consulta, descripcion, observacion))
        if lista_rx:
            cursor.execute("INSERT INTO prescripcion (id_consulta, indicaciones_generales) VALUES (%s, %s)",
                           (id_consulta, indicaciones))
            id_prescripcion = cursor.lastrowid
            for fila in lista_rx:
                cursor.execute("""INSERT INTO detalle_prescripcion
                                  (id_prescripcion, id_medicamento, dosis, frecuencia, duracion, indicaciones)
                                  VALUES (%s, %s, %s, %s, %s, %s)""", (id_prescripcion, *fila))
    log.info("Consulta %s atendida por el medico %s (usuario %s): %s diagnosticos, %s medicamentos",
             id_cita, id_medico, usuario, len(lista_dx), len(lista_rx))
    return {"id_consulta": id_consulta}


# ---------------------------------------------------------------------------
# Examenes
# ---------------------------------------------------------------------------
def opciones_examen(usuario):
    """Listas para solicitar un examen: examenes y equipos/puestos activos."""
    return {
        "examenes": consultar(CUENTA_MEDICO, """
            SELECT s.id_subtipo, s.nombre, s.costo, t.nombre AS tipo, t.id_area
            FROM subtipo_examen s JOIN tipo_procedimiento t ON t.id_tipo = s.id_tipo
            WHERE s.estado = 'activo' AND t.id_area IN (2, 3) ORDER BY t.id_area, t.id_tipo, s.nombre""",
                              id_usuario_app=usuario),
        "recursos": consultar(CUENTA_MEDICO, """
            SELECT id_recurso, id_area, nombre_recurso, tipo_recurso FROM recurso_atencion
            WHERE estado = 'activo' AND id_area IN (2, 3) ORDER BY id_area, nombre_recurso""", id_usuario_app=usuario),
    }


def solicitar_examen(usuario, id_medico, datos):
    """El medico agenda un examen de imagenologia o laboratorio para un paciente; queda como solicitante.

    El area se deduce del examen elegido. Se reutilizan las mismas reglas de la cita (dia habil, futuro,
    recurso libre, paciente sin otra cita a esa hora).
    """
    cedula = citas.paciente_activo(CUENTA_MEDICO, usuario, datos.get("cedula_paciente"))
    codigo = str(datos.get("id_subtipo") or "").strip().upper()
    if not codigo:
        raise ErrorNegocio("Elige el examen.")
    fila = consultar(CUENTA_MEDICO, """
        SELECT t.id_area FROM subtipo_examen s JOIN tipo_procedimiento t ON t.id_tipo = s.id_tipo
        WHERE s.id_subtipo = %s""", (codigo,), id_usuario_app=usuario, uno=True)
    if fila is None:
        raise ErrorNegocio("El examen no existe.")
    area = fila["id_area"]
    if area == AREA_CONSULTAS:
        raise ErrorNegocio("Ese no es un examen de imagenología ni de laboratorio.")
    pedido = {"fecha_cita": datos.get("fecha_cita"), "hora_inicio": datos.get("hora_inicio"),
              "id_recurso": datos.get("id_recurso"), "observacion": datos.get("observacion"),
              "id_subtipo": codigo, "id_medico_solicitante": id_medico}
    return citas.registrar_cita(CUENTA_MEDICO, usuario, cedula, area, pedido)


def examenes_solicitados(usuario, id_medico, estado=None, q=None, pagina=1):
    """Examenes que el medico solicito (imagenologia y laboratorio) con su estado y, si hay, el resultado."""
    condiciones, parametros = [], []
    if estado in ("pendiente", "realizado", "cancelado"):
        condiciones.append("estado_examen = %s")
        parametros.append(estado)
    patron = patron_like(q)
    if patron:
        condiciones.append("(cedula_paciente LIKE %s OR paciente LIKE %s)")
        parametros += [patron, patron]
    donde = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""
    union = """
        SELECT a.id_cita, 'imagenologia' AS area, a.fecha_cita, a.hora_inicio, a.estado, a.cedula_paciente,
               a.paciente, a.subtipo AS examen, a.estado_procedimiento AS estado_examen,
               a.fecha_realizacion, a.equipo AS lugar, NULL AS id_resultado
        FROM v_agenda_imagenologia a WHERE a.id_medico = %s
        UNION ALL
        SELECT l.id_cita, 'laboratorio', l.fecha_cita, l.hora_inicio, l.estado, l.cedula_paciente,
               l.paciente, l.examen, l.estado_examen, l.fecha_realizacion, l.puesto, rl.id_resultado
        FROM v_agenda_laboratorio l
        LEFT JOIN v_resultados_laboratorio rl ON rl.id_cita = l.id_cita
        WHERE l.id_medico = %s"""
    base = [id_medico, id_medico]
    total = consultar(CUENTA_MEDICO, f"SELECT COUNT(*) AS total FROM ({union}) t {donde}", base + parametros,
                      id_usuario_app=usuario, uno=True)["total"]
    pag = paginar(total, pagina_actual(pagina), POR_PAGINA)
    filas = consultar(CUENTA_MEDICO, f"""SELECT * FROM ({union}) t {donde}
                                         ORDER BY fecha_cita DESC, hora_inicio DESC, id_cita DESC LIMIT %s OFFSET %s""",
                      base + parametros + [pag["por_pagina"], pag["offset"]], id_usuario_app=usuario)
    return {"examenes": filas, "paginacion": pag, "filtros": {"estado": estado or "", "q": q or ""}}


def resultado_examen(usuario, id_medico, id_cita):
    """Resultado de un examen de laboratorio solicitado por este medico (None si aun no hay)."""
    propio = consultar(CUENTA_MEDICO, "SELECT 1 AS ok FROM v_agenda_laboratorio WHERE id_cita = %s AND id_medico = %s",
                       (id_cita, id_medico), id_usuario_app=usuario, uno=True)
    if propio is None:
        raise ErrorNegocio("El examen no existe.", 404)
    return consultar(CUENTA_MEDICO, """
        SELECT paciente, cedula_paciente, examen, fecha_realizacion, fecha_resultado, resultado, observaciones
        FROM v_resultados_laboratorio WHERE id_cita = %s""", (id_cita,), id_usuario_app=usuario, uno=True)