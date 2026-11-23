# Despliegue con Docker

La aplicación corre en dos contenedores: `medimagen_db` (MySQL 8 con la base ya cargada) y `medimagen_web` (Flask con gunicorn).

## 1. Archivos
| Archivo | Función |
|---|---|
| `Dockerfile` | Imagen de la aplicación: Python 3.12 slim, usuario sin privilegios, `gunicorn` con 3 workers y chequeo de salud en `/salud`. |
| `database/Dockerfile` | Imagen de MySQL que incluye los scripts `database/init` (01 a 05) y los deja con saltos de línea de Linux. |
| `docker-compose.yml` | Define los dos servicios, la red, los volúmenes y las medidas de seguridad. |
| `.dockerignore` | Deja fuera de la imagen `env`, `.env`, `.git`, pruebas, registros, documentos y scripts de base de datos. |
| `requirements.txt` | Dependencias de la aplicación (lo que instala Docker). |
| `.env` | Claves y configuración. No se sube a Git; el modelo es `.env.example`. |

## 2. Cómo funciona
- **Base de datos:** la primera vez que se crea el volumen `mysql_data`, MySQL ejecuta en orden `01` a `05`: tablas, triggers, datos de ejemplo, roles y cuentas. Mientras el volumen exista, no se vuelven a ejecutar. Para recrear la base: `docker compose down -v` y levantar otra vez. La carpeta `database/extras` no entra en la imagen.
- **Contraseñas:** las cuentas `usr_*` se crean en `05_usuarios.sql` con la clave `uno234cinco`. Las variables `DB_PASS_*` del `.env` deben tener ese mismo valor (si cambias una en MySQL, cámbiala también en el `.env`).
- **Aplicación:** espera a que MySQL esté sano y se conecta a `db:3306` con las cuentas `usr_*`, nunca con `root`.
- **Seguridad del contenedor:** sistema de archivos de solo lectura (solo `/tmp` y `/app/logs` se pueden escribir), sin capacidades de Linux (`cap_drop: ALL`), `no-new-privileges` y 512 MB de memoria máxima.
- **Puertos:** aplicación en `127.0.0.1:5001` y MySQL en `127.0.0.1:3007` (solo para Workbench), accesibles únicamente desde este computador.
- **Datos que se conservan:** la base en el volumen `mysql_data` y los registros en `app_logs`. Se mantienen aunque se detengan o reconstruyan los contenedores.

## 3. Pasos
1. En la raíz del proyecto, revisa el `.env`: `SECRET_KEY` de al menos 32 caracteres, `MYSQL_ROOT_PASSWORD`, las `DB_PASS_*` y `DB_NAME=medimagen2`. (`DB_HOST` y `FLASK_ENV` no importan: Docker los reemplaza.)
2. Abre Docker Desktop y espera a que diga que está en ejecución.
3. Construir y levantar: `docker compose up --build -d`. La primera vez tarda unos minutos.
4. Ver el estado: `docker compose ps`. Ambos deben decir `healthy`.
5. Abrir `http://localhost:5001` e ingresar (por ejemplo `admin` con `uno234cinco`; pide cambiar la clave).
6. Workbench: host `127.0.0.1`, puerto `3007`, usuario `root` con `MYSQL_ROOT_PASSWORD`.
7. Registros: `docker compose logs -f web`.
8. Detener: `docker compose down`. Detener y borrar la base: `docker compose down -v`.

## 4. Probar desde el celular
En `docker-compose.yml`, cambia `"127.0.0.1:5001:5001"` por `"5001:5001"`, ejecuta `docker compose up -d` y abre `http://IP-DEL-COMPUTADOR:5001` desde el celular conectado a la misma red Wi-Fi (la IP se ve con `ipconfig`). Puede ser necesario permitir el puerto 5001 en el Firewall de Windows. Vuelve al valor original cuando termines.

## 5. Respaldo y restauración
- Respaldo: `docker compose exec db mysqldump -uroot -p medimagen2 --routines --triggers > backups/medimagen_docker.sql`
- Restaurar: `docker compose exec -T db mysql -uroot -p medimagen2 < backups/medimagen_docker.sql`

## 6. Si algo falla
| Síntoma | Qué revisar |
|---|---|
| `falta SECRET_KEY en .env` (o similar) | Falta esa variable en el `.env`. |
| `medimagen_db` no llega a `healthy` | `docker compose logs db`. Casi siempre es un error en algún script de `database/init`. Corrígelo y repite con `docker compose down -v` y `up --build`. |
| La app no conecta a la base | Las `DB_PASS_*` del `.env` no coinciden con las de `05_usuarios.sql`, o `DB_NAME` no es `medimagen2`. |
| Cambié un `.sql` y no se refleja | Los scripts solo se ejecutan con un volumen nuevo: `docker compose down -v` y `docker compose up --build -d`. |
| El puerto 5001 o 3007 está ocupado | Cierra el `python run.py` local o cambia el puerto de la izquierda en `docker-compose.yml`. |

## 7. Comprobaciones antes de entregar
- [ ] `docker compose up --build -d` termina sin errores y los dos contenedores quedan `healthy`.
- [ ] En Workbench (puerto 3007) están las 17 tablas, las vistas, los triggers, los roles y las cuentas.
- [ ] Se puede entrar con cada rol y agendar una cita.
- [ ] `docker compose down -v` y volver a levantar reconstruye todo desde cero.
