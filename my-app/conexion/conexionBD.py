"""Conexion con MySQL.

Una cuenta de MySQL por rol (usr_login, usr_administrador, usr_recepcion, ...). Cada cuenta tiene su propio
pool de conexiones. La persona que esta usando el sistema se identifica con la variable de sesion
@app_usuario, que leen los triggers de auditoria.

Uso desde los controladores:
    consultar("recepcion", "SELECT ...", (param,), id_usuario_app=5)
    with transaccion("medico", id_usuario_app=5) as cur:
        cur.execute("INSERT ...", (...))
"""
import threading
import time
from contextlib import contextmanager

import mysql.connector
from mysql.connector import pooling

from config import Config
from utils.errors import ErrorNegocio, traducir_error_mysql
from utils.logger import obtener_logger

log = obtener_logger("bd")

_pools = {}
_candado = threading.Lock()


def _obtener_pool(clave):
    pool = _pools.get(clave)
    if pool is not None:
        return pool
    with _candado:
        pool = _pools.get(clave)
        if pool is None:
            usuario, contrasena = Config.credenciales(clave)
            pool = pooling.MySQLConnectionPool(
                pool_name=f"medimagen_{clave}",
                pool_size=Config.BD_POOL,
                pool_reset_session=True,
                host=Config.BD_HOST,
                port=Config.BD_PUERTO,
                user=usuario,
                password=contrasena,
                database=Config.BD_NOMBRE,
                charset="utf8mb4",
                collation="utf8mb4_unicode_ci",
                connection_timeout=5,
            )
            _pools[clave] = pool
            log.info("Pool creado para la cuenta %s (%s conexiones)", usuario, Config.BD_POOL)
    return pool


def _tomar_del_pool(pool):
    """El pool de mysql-connector no espera: si no hay conexion libre falla al instante.
    Aqui se reintenta hasta 2 segundos, por si varias peticiones coinciden."""
    for _ in range(40):
        try:
            return pool.get_connection()
        except pooling.PoolError:
            time.sleep(0.05)
    return pool.get_connection()


def obtener_conexion(clave, id_usuario_app=None):
    """Toma una conexion del pool de la cuenta indicada y registra quien la usa (@app_usuario)."""
    try:
        conexion = _tomar_del_pool(_obtener_pool(clave))
        cursor = conexion.cursor()
        cursor.execute("SET @app_usuario = %s", (id_usuario_app,))
        cursor.close()
        return conexion
    except mysql.connector.Error as error:
        raise ErrorNegocio(traducir_error_mysql(error), 503) from error


def consultar(clave, sql, parametros=None, id_usuario_app=None, uno=False):
    """SELECT. Devuelve una lista de diccionarios (o un diccionario / None si uno=True)."""
    conexion = obtener_conexion(clave, id_usuario_app)
    cursor = conexion.cursor(dictionary=True)
    try:
        cursor.execute(sql, parametros or ())
        filas = cursor.fetchall()
    except mysql.connector.Error as error:
        raise ErrorNegocio(traducir_error_mysql(error)) from error
    finally:
        cursor.close()
        conexion.close()
    if uno:
        return filas[0] if filas else None
    return filas


@contextmanager
def transaccion(clave, id_usuario_app=None):
    """Bloque atomico: todo se confirma al terminar o se deshace si algo falla."""
    conexion = obtener_conexion(clave, id_usuario_app)
    cursor = conexion.cursor(dictionary=True)
    try:
        conexion.start_transaction()
        yield cursor
        conexion.commit()
    except mysql.connector.Error as error:
        _deshacer(conexion)
        raise ErrorNegocio(traducir_error_mysql(error)) from error
    except Exception:
        _deshacer(conexion)
        raise
    finally:
        cursor.close()
        conexion.close()


def _deshacer(conexion):
    try:
        conexion.rollback()
    except mysql.connector.Error:
        log.exception("No se pudo deshacer la transaccion")


def ejecutar(clave, sql, parametros=None, id_usuario_app=None):
    """INSERT / UPDATE / DELETE de una sentencia. Devuelve {'filas': filas afectadas, 'id': ultimo id}."""
    with transaccion(clave, id_usuario_app) as cursor:
        cursor.execute(sql, parametros or ())
        return {"filas": cursor.rowcount, "id": cursor.lastrowid}


def probar_conexion(clave):
    """Para scripts/probar_conexiones.py: devuelve la cuenta con la que MySQL reconocio la conexion."""
    return consultar(clave, "SELECT CURRENT_USER() AS cuenta, CURRENT_ROLE() AS rol", uno=True)