"""Constantes del sistema: roles, estados y menu por rol."""

# Cuenta de MySQL que usa cada rol (clave de Config.CUENTAS_BD)
CUENTA_ADMINISTRADOR = "administrador"
CUENTA_RECEPCION = "recepcion"
CUENTA_MEDICO = "medico"
CUENTA_IMAGENOLOGIA = "imagenologia"
CUENTA_LABORATORIO = "laboratorio"
CUENTA_PACIENTE = "paciente"

CUENTAS = (CUENTA_ADMINISTRADOR, CUENTA_RECEPCION, CUENTA_MEDICO,
           CUENTA_IMAGENOLOGIA, CUENTA_LABORATORIO, CUENTA_PACIENTE)

# rol.nombre (tabla rol) -> cuenta de MySQL. Un rol que no este aqui no puede entrar al sistema.
ROL_BD_A_CUENTA = {
    "administrador": CUENTA_ADMINISTRADOR,
    "recepcion": CUENTA_RECEPCION,
    "medico": CUENTA_MEDICO,
    "personal_imagenologia": CUENTA_IMAGENOLOGIA,
    "personal_laboratorio": CUENTA_LABORATORIO,
    "paciente": CUENTA_PACIENTE,
}

ETIQUETA_CUENTA = {
    CUENTA_ADMINISTRADOR: "Administrador",
    CUENTA_RECEPCION: "Recepción",
    CUENTA_MEDICO: "Médico",
    CUENTA_IMAGENOLOGIA: "Personal de imagenología",
    CUENTA_LABORATORIO: "Personal de laboratorio",
    CUENTA_PACIENTE: "Paciente",
}

ESTADOS_CITA = ("pendiente", "confirmada", "atendida", "cancelada", "no_asistio")
ESTADOS_ACTIVOS_CITA = ("pendiente", "confirmada")
ESTADOS_EXAMEN = ("pendiente", "realizado", "cancelado")

# Areas (area.id_area)
AREA_CONSULTAS = 1
AREA_IMAGENOLOGIA = 2
AREA_LABORATORIO = 3
HORAS_ALMUERZO = ("13:00:00", "14:00:00")

# Menu por cuenta: (titulo, endpoint). Los endpoints que aun no existen no se muestran.
MENU = {
    CUENTA_ADMINISTRADOR: [
        ("Panel", "dashboard.inicio"),
        ("Usuarios", "usuarios.lista"),
        ("Roles", "roles.lista"),
        ("Personal", "personal.lista"),
        ("Médicos", "medicos.lista"),
        ("Pacientes", "pacientes.lista"),
        ("Especialidades", "especialidades.lista"),
        ("Catálogos", "catalogos.index"),
        ("Citas", "citas.agenda"),
        ("Reportes", "reportes.ingresos"),
        ("Auditoría de citas", "auditoria.lista"),
        ("Accesos", "auditoria.accesos"),
    ],
    CUENTA_RECEPCION: [
        ("Panel", "dashboard.inicio"),
        ("Pacientes", "pacientes.lista"),
        ("Agenda", "citas.agenda"),
        ("Nueva cita", "citas.nueva"),
    ],
    CUENTA_MEDICO: [
        ("Panel", "dashboard.inicio"),
        ("Mi agenda", "consultas.mi_agenda"),
        ("Exámenes solicitados", "consultas.examenes_solicitados"),
    ],
    CUENTA_IMAGENOLOGIA: [
        ("Panel", "dashboard.inicio"),
        ("Agenda", "imagenologia.agenda"),
    ],
    CUENTA_LABORATORIO: [
        ("Panel", "dashboard.inicio"),
        ("Agenda", "laboratorio.agenda"),
    ],
    CUENTA_PACIENTE: [
        ("Panel", "dashboard.inicio"),
        ("Mis citas", "historial.mis_citas"),
        ("Mi historial", "historial.mi_historial"),
        ("Mis recetas", "historial.mis_recetas"),
        ("Mis resultados", "historial.mis_resultados"),
    ],
}