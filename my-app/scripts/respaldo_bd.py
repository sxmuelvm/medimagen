"""Respaldo de la base de datos de Medimagen con mysqldump.

Usa la cuenta usr_respaldo (solo lectura, ver 04_roles.sql). La contrasena se toma del .env (DB_PASS_RESPALDO) y se
pasa a mysqldump por variable de entorno, nunca en la linea de comandos (asi no aparece en la lista de procesos).

Uso (desde la carpeta my-app):
    python scripts/respaldo_bd.py              # crea backups/medimagen_AAAAMMDD_HHMMSS.sql
    python scripts/respaldo_bd.py --guardar 10 # ademas conserva solo los 10 respaldos mas recientes
    python scripts/respaldo_bd.py --verificar  # al terminar, comprueba que el archivo tenga tablas, vistas y triggers

Si mysqldump no esta en el PATH (en Windows suele estar en C:\\Program Files\\MySQL\\MySQL Server 8.0\\bin), define
MYSQLDUMP_RUTA en el .env con la ruta completa al programa.
Para restaurar:  mysql -u root -p medimagen < backups/medimagen_AAAAMMDD_HHMMSS.sql
"""
import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

RAIZ_APP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ_APP))

from config import Config  # noqa: E402  (carga el .env)

CUENTA = "usr_respaldo"
CARPETA = RAIZ_APP.parent / "backups"
RUTAS_WINDOWS = [r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe",
                 r"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqldump.exe",
                 r"C:\Program Files (x86)\MySQL\MySQL Server 8.0\bin\mysqldump.exe"]


def buscar_mysqldump():
    ruta = os.getenv("MYSQLDUMP_RUTA")
    if ruta:
        return ruta if Path(ruta).exists() else None
    encontrado = shutil.which("mysqldump")
    if encontrado:
        return encontrado
    return next((r for r in RUTAS_WINDOWS if Path(r).exists()), None)


def respaldar():
    contrasena = os.getenv("DB_PASS_RESPALDO")
    if not contrasena:
        sys.exit("Falta DB_PASS_RESPALDO en el .env (la contrasena de la cuenta usr_respaldo).")
    programa = buscar_mysqldump()
    if not programa:
        sys.exit("No se encontro mysqldump. Agregalo al PATH o define MYSQLDUMP_RUTA en el .env.")

    CARPETA.mkdir(exist_ok=True)
    destino = CARPETA / f"{Config.BD_NOMBRE}_{datetime.now():%Y%m%d_%H%M%S}.sql"
    comando = [programa, f"--host={Config.BD_HOST}", f"--port={Config.BD_PUERTO}", f"--user={CUENTA}",
               "--single-transaction",        # copia consistente sin bloquear la aplicacion
               "--routines", "--triggers", "--events",
               "--default-character-set=utf8mb4", "--no-tablespaces",
               f"--result-file={destino}", Config.BD_NOMBRE]
    entorno = {**os.environ, "MYSQL_PWD": contrasena}
    resultado = subprocess.run(comando, env=entorno, capture_output=True, text=True)
    if resultado.returncode != 0:
        destino.unlink(missing_ok=True)
        sys.exit(f"mysqldump fallo ({resultado.returncode}): {resultado.stderr.strip() or 'sin detalle'}")
    return destino


def conservar(cantidad):
    """Borra los respaldos mas viejos y deja solo los `cantidad` mas recientes."""
    archivos = sorted(CARPETA.glob(f"{Config.BD_NOMBRE}_*.sql"))
    sobran = archivos[:-cantidad] if cantidad > 0 else []
    for archivo in sobran:
        archivo.unlink()
    return len(sobran)


def verificar(archivo):
    """Comprobacion minima: el respaldo contiene tablas, vistas, triggers y datos."""
    texto = archivo.read_text(encoding="utf8", errors="replace")
    pendientes = {"tablas": texto.count("CREATE TABLE"), "vistas": texto.count("VIEW `v_"),
                  "triggers": texto.count("CREATE*/") + texto.count("TRIGGER `trg_"),
                  "datos": texto.count("INSERT INTO")}
    faltan = [nombre for nombre, cantidad in pendientes.items() if cantidad == 0]
    return pendientes, faltan


def main():
    parser = argparse.ArgumentParser(description="Respaldo de la base de datos de Medimagen")
    parser.add_argument("--guardar", type=int, default=0, metavar="N", help="conservar solo los N respaldos mas recientes")
    parser.add_argument("--verificar", action="store_true", help="comprobar el contenido del respaldo creado")
    argumentos = parser.parse_args()

    archivo = respaldar()
    kilobytes = archivo.stat().st_size / 1024
    print(f"Respaldo creado: {archivo}  ({kilobytes:.0f} KB)")

    if argumentos.verificar:
        conteo, faltan = verificar(archivo)
        print("Contenido:", ", ".join(f"{n} {c}" for n, c in conteo.items()))
        if faltan:
            sys.exit(f"El respaldo parece incompleto: no tiene {', '.join(faltan)}.")
        print("Verificacion correcta.")
    if argumentos.guardar:
        print(f"Respaldos antiguos eliminados: {conservar(argumentos.guardar)}")


if __name__ == "__main__":
    main()