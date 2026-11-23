# Despliegue con Docker

> Estado: los archivos están preparados (`Dockerfile`, `docker-compose.yml`, `.dockerignore`), pero el despliegue se prueba al final, cuando el software esté completamente verificado. Esta guía describe cómo está armado y cómo se usará.

## 1. Qué contiene
| Archivo | Función |
|---|---|
| `Dockerfile` | Imagen de la aplicación: Python 3.12 slim, usuario sin privilegios, `gunicorn` con 3 workers y chequeo de salud en `/salud`. |
| `docker-compose.yml` | Dos servicios: `db` (MySQL 8) y `web` (la aplicación). |
| `.dockerignore` | Deja fuera `env`, `.env`, `.git`, pruebas, registros y documentos. |
| `.env` | Claves y configuración (no se sube a Git; el modelo es `.env.example`). |

## 2. Cómo funciona
- **Base de datos:** al crearse el contenedor por primera vez, MySQL ejecuta en orden los archivos de `database/init` (`01` a `05`): tablas, triggers, datos de ejemplo, roles y cuentas. Si el volumen `mysql_data` ya existe, no se vuelven a ejecutar; para empezar de cero hay que borrar el volumen (`docker compose down -v`). La carpeta `database/extras` no se ejecuta en Docker.
- **Aplicación:** se construye desde `my-app/`, espera a que MySQL esté sano y se conecta con las cuentas `usr_*` (nunca con `root`). Las contraseñas de esas cuentas deben coincidir con las de `database/init/05_usuarios.sql`.
- **Seguridad del contenedor:** sistema de archivos de solo lectura (solo `logs` y `/tmp` se pueden escribir), sin capacidades de Linux (`cap_drop: ALL`), `no-new-privileges` y 512 MB de memoria máxima.
- **Puertos:** aplicación en `127.0.0.1:5001` y MySQL en `127.0.0.1:3007`, ambos solo accesibles desde el mismo computador.

## 3. Pasos
1. Copia `.env.example` a `.env` y completa los valores (clave secreta de al menos 32 caracteres, las contraseñas de las cuentas de MySQL y la del `root`). Para Docker, `DB_NAME` debe ser `medimagen2`.
2. Desde la raíz del proyecto: `docker compose up --build`.
3. Abre `http://localhost:5001` e ingresa con un usuario de ejemplo (clave `uno234cinco`, que se debe cambiar en el primer ingreso).
4. Para conectar Workbench: `127.0.0.1`, puerto `3007`, usuario `root`.
5. Detener: `docker compose down`. Detener y borrar la base: `docker compose down -v`.

## 3.1 Comprobaciones antes de entregar
- [ ] `docker compose up --build` termina sin errores y `medimagen_web` aparece como `healthy`.
- [ ] Las 17 tablas, las vistas, triggers, roles y cuentas existen en el contenedor `db`.
- [ ] Se puede entrar con cada rol y agendar una cita.
- [ ] Las contraseñas del `.env` coinciden con las de `05_usuarios.sql`.
- [ ] `docker compose down -v` y volver a levantar reconstruye todo desde cero.

## 4. Respaldo
`python my-app/scripts/respaldo_bd.py` genera un respaldo en `backups/` (carpeta raíz) usando la cuenta de respaldo. Para restaurar: `mysql -u root -p medimagen2 < backups/<archivo>.sql`.
