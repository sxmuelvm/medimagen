# Medimagen Cuenca

Sistema de gestión y agendamiento de citas médicas para un centro de consultas, imagenología y laboratorio. Proyecto de la materia Gestión de Bases de Datos.

- **Tecnología:** Flask + Jinja, HTML/CSS/JavaScript simples, MySQL 8, Docker.
- **Roles:** administrador, recepción, médico, personal de imagenología, personal de laboratorio y paciente.
- **Base de datos:** `medimagen2` (17 tablas, 9 vistas, triggers, procedimientos, roles y cuentas de MySQL por rol).

## Qué incluye el sistema
- **Usuarios:** una sola cédula por persona (`usuario.cedula`, única). El usuario de acceso se genera solo (`cmarin`, `cmarin01`…). Cada rol de la aplicación tiene su rol y cuenta propia en MySQL (`rol_*` / `usr_*`) con privilegios mínimos.
- **Citas:** agendar, reprogramar y cancelar. Se puede volver a agendar un horario cancelado y las canceladas se ven en el calendario. El equipo/puesto del examen se asigna automáticamente según el tipo de examen.
- **Médico:** busca pacientes (por cédula o nombre), solicita exámenes, registra consultas y resultados.
- **Calendario semanal** por rol y reportes de gestión.
- **Seguridad:** sesiones, bloqueo por intentos fallidos, cambio de clave obligatorio, CSRF, CSP estricta, validaciones en la base (triggers y restricciones) y en la aplicación.
- **Consultas SQL:** `database/extras/06_consultas.sql` (CRUD), `08_consultas_avanzadas.sql` (10 consultas de nivel medio-avanzado, solo SELECT) y `07_verificacion.sql` (comprueba las reglas de la base).
- **Docker:** dos contenedores (base de datos y aplicación) con volúmenes, healthchecks y la base creada automáticamente.

## Instalación con Docker (recomendada)
Requisitos: Docker Desktop (o Docker + Compose) y Git.

1. Clonar el proyecto y entrar a la carpeta:
   ```
   git clone https://github.com/sxmuelvm/medimagen.git
   cd medimagen
   git checkout medimagen2
   ```
2. Crear el archivo `.env` a partir del ejemplo (`copy .env.example .env` en Windows, `cp .env.example .env` en Linux/Mac) y completarlo:
   ```
   SECRET_KEY=una_clave_larga_y_aleatoria
   MYSQL_ROOT_PASSWORD=clave_del_root
   DB_PASS_LOGIN=uno234cinco
   DB_PASS_ADMINISTRADOR=uno234cinco
   DB_PASS_RECEPCION=uno234cinco
   DB_PASS_MEDICO=uno234cinco
   DB_PASS_IMAGENOLOGIA=uno234cinco
   DB_PASS_LABORATORIO=uno234cinco
   DB_PASS_PACIENTE=uno234cinco
   ```
   Las claves `DB_PASS_*` deben ser iguales a las de `database/init/05_usuarios.sql` (`uno234cinco`).
3. Construir y levantar:
   ```
   docker compose up --build -d
   ```
   La primera vez crea la base `medimagen2` ejecutando `database/init/01` a `05` (tarda ~1 minuto).
4. Comprobar que ambos contenedores estén `healthy`:
   ```
   docker compose ps
   ```
5. Abrir la aplicación: **http://localhost:5001**

**Desde un celular (misma red Wi-Fi):** averiguar la IPv4 del computador con `ipconfig` y abrir `http://IP:5001`. Si no carga, permitir el puerto 5001 en el Firewall de Windows.
**MySQL Workbench:** host `127.0.0.1`, puerto `3007`, usuario `root` (solo accesible desde el mismo computador).

Comandos útiles:
```
docker compose logs -f web      ver los registros de la aplicación
docker compose logs db          ver los registros de la base
docker compose down             detener (los datos se conservan)
docker compose down -v          detener y borrar la base (se recrea al volver a levantar)
```

## Usuarios de ejemplo
Clave inicial `uno234cinco` (se debe cambiar al entrar): `admin`, `ccriollo` (recepción), `cmarin` (médico), `mbajana` (imagenología), `asornoza` (laboratorio), `candrade` (paciente).

## Instalación manual (sin Docker)
Base de datos: ejecutar con `root` en MySQL Workbench, en este orden:
1. `database/extras/00_limpieza.sql` (borra la base anterior)
2. `database/init/01_tablas_vistas.sql`
3. `database/init/02_triggers.sql`
4. `database/init/03_datos.sql`
5. `database/init/04_roles.sql`
6. `database/init/05_usuarios.sql`

Aplicación (en `.env` usar `DB_HOST=localhost` y `DB_PORT=3306`, o 3007 si la base está en Docker):
```
python -m venv env
env\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env
cd my-app
python run.py
```
Aplicación: http://localhost:5001 · Pruebas automáticas (solo local, no van a Docker): `cd my-app` y `pytest`.

## Documentación
- `docs/estructura.md`: carpetas y archivos del proyecto.
- `docs/diseno_pantallas.md`: diseño y pantallas por rol.
- `docs/seguridad_aplicacion.md` y `docs/justificacion_seguridad.md`: seguridad.
- `docs/despliegue_docker.md`: despliegue con Docker.
