# Medimagen Cuenca

Sistema web para la gestión y el agendamiento de citas médicas de un centro de consultas, imagenología y laboratorio. Proyecto de la materia Gestión de Bases de Datos.

**Tecnología:** Flask + Jinja, HTML/CSS/JavaScript, MySQL 8 y Docker.
**Roles:** administrador, recepción, médico, imagenología, laboratorio y paciente.
**Base de datos:** `medimagen2` (17 tablas, 9 vistas, triggers, procedimientos y una cuenta de MySQL por rol).

## Instalación con Docker

Solo se necesita [Docker Desktop](https://www.docker.com/products/docker-desktop/) y Git. No hace falta instalar Python ni MySQL.

**1. Descargar el proyecto**
```
git clone https://github.com/sxmuelvm/medimagen.git
cd medimagen
git checkout medimagen2
```

**2. Crear el archivo `.env`** en la carpeta `medimagen` (junto a `docker-compose.yml`) con este contenido:
```
SECRET_KEY=cambia_esta_clave_por_una_larga_y_aleatoria
MYSQL_ROOT_PASSWORD=Root12345
DB_NAME=medimagen2
DB_PASS_LOGIN=uno234cinco
DB_PASS_ADMINISTRADOR=uno234cinco
DB_PASS_RECEPCION=uno234cinco
DB_PASS_MEDICO=uno234cinco
DB_PASS_IMAGENOLOGIA=uno234cinco
DB_PASS_LABORATORIO=uno234cinco
DB_PASS_PACIENTE=uno234cinco
```
Las claves `DB_PASS_*` deben ser `uno234cinco`, porque así se crean las cuentas de MySQL en `database/init/05_usuarios.sql`. El archivo `.env` no se sube a Git (tiene claves); por eso cada persona lo crea.

**3. Construir y encender**
```
docker compose up --build -d
```
La primera vez tarda unos minutos: descarga las imágenes y crea la base `medimagen2` ejecutando `database/init/01` a `05`.

**4. Comprobar** que los dos contenedores estén `healthy`:
```
docker compose ps
```

**5. Abrir** http://localhost:5001

| Para | Dirección |
|---|---|
| Aplicación | http://localhost:5001 |
| Desde un celular (mismo Wi-Fi) | `http://IP_DEL_PC:5001` (la IP sale con `ipconfig`; permitir el puerto 5001 en el Firewall de Windows) |
| MySQL Workbench | host `127.0.0.1`, puerto `3007`, usuario `root`, clave `MYSQL_ROOT_PASSWORD` |

**Comandos útiles**
```
docker compose logs -f web    registros de la aplicación
docker compose logs db        registros de la base de datos
docker compose down           apagar (los datos se conservan)
docker compose down -v        apagar y borrar la base (se recrea al volver a encender)
```

## Usuarios de ejemplo
Todos tienen la clave inicial `uno234cinco`. El sistema obliga a cambiarla al primer ingreso. El usuario se genera solo a partir del nombre; cuando hay homónimos se agrega un número (`cmarin`, `cmarin01`…).

| Rol | Usuario | Nombre | Cédula |
|---|---|---|---|
| Administrador | `admin` | Samuel Felipe Vallejo Morales | 0000000001 |
| Recepción | `ccriollo` | Christian David Criollo Lucero | 0000000002 |
| Recepción | `mvargas` | Mónica Vargas Ruiz | 0000000004 |
| Recepción | `mvargas01` | María Fernanda Vargas Salinas | 0000000057 |
| Recepción | `ecalle` | Esteban Calle Paredes | 0000000005 |
| Recepción | `jortega` | Juan Pablo Ortega Salas | 0000000058 |
| Médico | `cmarin` | Cristian Teodoro Marin Guachichullca | 0000000003 |
| Médico | `gmora` | Gabriela Mora Ullauri | 0000000014 |
| Médico | `mjaramillo` | Mónica Jaramillo Heredia | 0000000019 |
| Médico | `pcrespo` | Patricia Alejandra Crespo Vélez | 0000000012 |
| Médico | `mtello` | Marcelo Andrés Tello Bravo | 0000000016 |
| Imagenología | `mbajana` | Michael Jose Bajaña Espinoza | 0000000006 |
| Imagenología | `dochoa` | Diego Ochoa Brito | 0000000007 |
| Imagenología | `lparedes` | Lucas Paredes Soto | 0000000008 |
| Laboratorio | `asornoza` | Andrea Sornoza Viteri | 0000000009 |
| Laboratorio | `erojas` | Elena Rojas Cabrera | 0000000010 |
| Laboratorio | `ntapia` | Nelson Tapia Ullauri | 0000000011 |
| Laboratorio | `cmarin01` | Camila Andrea Marín Cuesta | 0000000059 |
| Paciente | `candrade` | Carlos Andrade Pinos | 0000000021 |
| Paciente | `mvintimilla` | María Vintimilla Cueva | 0000000022 |
| Paciente | `mvintimilla01` | María José Vintimilla Cueva | 0000000051 |
| Paciente | `acordero` | Ana Cordero Ríos | 0000000024 |
| Paciente | `acordero01` | Ana Lucía Cordero Ríos | 0000000053 |
| Paciente | `cmarin02` | Carlos Eduardo Marín Torres | 0000000049 |
| Paciente | `cmarin03` | Camila Fernanda Marín Loja | 0000000050 |
| Paciente | `jperez` | Juan Carlos Pérez Andrade | 0000000052 |

## Qué se hizo

**Base de datos**
- Una sola cédula por persona (`usuario.cedula`, única y validada con 10 dígitos); `paciente` y `medico` la comparten.
- Triggers y procedimientos que validan perfiles, impiden borrados incoherentes y mantienen los datos sincronizados.
- Usuario de acceso automático a partir del nombre (`cmarin`, `cmarin01`…).
- Citas con una columna generada (`activa`) para que un horario cancelado pueda volver a agendarse sin chocar con la restricción de unicidad.
- Roles `rol_*` y cuentas `usr_*` con privilegios mínimos por tipo de usuario.
- Datos de ejemplo con dos nombres y dos apellidos.

**Aplicación**
- **Citas:** agendar, reprogramar y cancelar; las canceladas se ven en el calendario. El equipo o puesto se asigna solo según el tipo de examen.
- **Médico:** busca pacientes por cédula o nombre, solicita y modifica exámenes, registra consultas y resultados.
- **Calendario semanal** y horarios disponibles por especialidad o equipo.
- **Seguridad:** sesiones con tiempo de inactividad, bloqueo por intentos fallidos, cambio de clave obligatorio, protección CSRF, política CSP estricta y validaciones tanto en la aplicación como en la base.

**Consultas SQL** (`database/extras/`)
- `06_consultas.sql`: consultas de gestión (CRUD).
- `08_consultas_avanzadas.sql`: 10 consultas de nivel medio-avanzado, solo `SELECT`.
- `07_verificacion.sql`: comprueba las reglas de la base.

**Docker**
- Dos contenedores: base de datos (con la base creada automáticamente) y aplicación (con gunicorn).
- Volúmenes para los datos, comprobaciones de salud y contenedor de la aplicación en modo solo lectura y sin privilegios extra.

## Instalación sin Docker (opcional)
1. En MySQL Workbench, con `root`, ejecutar en orden: `database/extras/00_limpieza.sql` y luego `database/init/01_tablas_vistas.sql`, `02_triggers.sql`, `03_datos.sql`, `04_roles.sql`, `05_usuarios.sql`.
2. En la carpeta del proyecto:
   ```
   python -m venv env
   env\Scripts\activate
   pip install -r requirements.txt
   cd my-app
   python run.py
   ```
   Se usa el mismo `.env`, pero con `DB_HOST=localhost`, `DB_PORT=3306` y `APP_PORT=5001`.

## Documentación
- `docs/estructura.md`: carpetas y archivos.
- `docs/diseno_pantallas.md`: diseño y pantallas por rol.
- `docs/seguridad_aplicacion.md` y `docs/justificacion_seguridad.md`: seguridad.
- `docs/despliegue_docker.md`: detalles del despliegue.
