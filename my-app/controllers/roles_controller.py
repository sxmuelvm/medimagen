"""Roles del sistema (solo administrador).

Cada rol de la aplicacion corresponde a un rol de MySQL con sus privilegios (04_roles.sql), por eso aqui solo se
puede editar la descripcion y activar o desactivar el rol. El nombre no cambia y los roles nuevos los define el DBA.
"""
from config import Config
from conexion.conexionBD import consultar, ejecutar
from utils import validators
from utils.constants import CUENTA_ADMINISTRADOR, ROL_BD_A_CUENTA
from utils.errors import ErrorNegocio
from utils.logger import obtener_logger

log = obtener_logger("roles")

CUENTA = CUENTA_ADMINISTRADOR
ESTADOS = ("activo", "inactivo")


def _enriquecer(fila):
    cuenta = ROL_BD_A_CUENTA.get(fila["nombre"])
    fila["cuenta_mysql"] = Config.CUENTAS_BD[cuenta][0] if cuenta else None
    fila["rol_mysql"] = f"rol_{cuenta}" if cuenta else None
    return fila


def listar(administrador):
    filas = consultar(CUENTA, """
        SELECT r.id_rol, r.nombre, r.descripcion, r.estado,
               COUNT(u.id_usuario) AS usuarios,
               COALESCE(SUM(u.estado = 'activo'), 0) AS usuarios_activos
        FROM rol r
        LEFT JOIN usuario u ON u.id_rol = r.id_rol
        GROUP BY r.id_rol, r.nombre, r.descripcion, r.estado
        ORDER BY r.id_rol""", id_usuario_app=administrador)
    return {"roles": [_enriquecer(f) for f in filas]}


def obtener(id_rol, administrador):
    fila = consultar(CUENTA, "SELECT id_rol, nombre, descripcion, estado FROM rol WHERE id_rol = %s", (id_rol,),
                     id_usuario_app=administrador, uno=True)
    if fila is None:
        raise ErrorNegocio("El rol no existe.", 404)
    return _enriquecer(fila)


def actualizar(id_rol, datos, administrador):
    actual = obtener(id_rol, administrador)
    descripcion = validators.texto(datos.get("descripcion"), "La descripción", maximo=255, obligatorio=False)
    estado = validators.opcion(datos.get("estado", actual["estado"]), ESTADOS, "El estado")
    if actual["nombre"] == "administrador" and estado != "activo":
        raise ErrorNegocio("El rol administrador no se puede desactivar.")
    ejecutar(CUENTA, "UPDATE rol SET descripcion = %s, estado = %s WHERE id_rol = %s",
             (descripcion, estado, id_rol), id_usuario_app=administrador)
    log.info("Rol %s modificado por el usuario %s (estado: %s)", actual["nombre"], administrador, estado)