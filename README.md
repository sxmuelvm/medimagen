# Medimagen Cuenca

Sistema de gestión y agendamiento de citas médicas para un centro de consultas, imagenología y laboratorio. Proyecto de la materia Gestión de Bases de Datos.

- **Tecnología:** Flask + Jinja, HTML/CSS/JavaScript simples, MySQL 8.
- **Roles:** administrador, recepción, médico, personal de imagenología, personal de laboratorio y paciente.
- **Base de datos:** `medimagen2` (17 tablas, 9 vistas, triggers, roles y cuentas de MySQL por rol).

## Base de datos
Ejecutar con `root` en MySQL Workbench, en este orden:
1. `database/extras/00_limpieza.sql` (borra la base anterior)
2. `database/init/01_tablas_vistas.sql`
3. `database/init/02_triggers.sql`
4. `database/init/03_datos.sql`
5. `database/init/04_roles.sql`
6. `database/init/05_usuarios.sql`

Las consultas del proyecto están en `database/extras/06_consultas.sql` (CRUD) y `08_consultas_avanzadas.sql` (análisis). `07_verificacion.sql` comprueba las reglas de la base.

## Local
```
python -m venv env
env\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      (y completar las claves)
cd my-app
python run.py
```
Aplicación: http://localhost:5001

Usuarios de ejemplo (clave inicial `uno234cinco`, se debe cambiar al entrar): `admin`, `ccriollo` (recepción), `cmarin` (médico), `mbajana` (imagenología), `asornoza` (laboratorio), `candrade` (paciente).

Pruebas: `cd my-app` y `pytest`.

## Docker
```
docker compose up --build
```
Aplicación: http://localhost:5001 · Workbench: 127.0.0.1 puerto 3007, usuario root. Detalles en `docs/despliegue_docker.md`.

## Documentación
- `docs/estructura.md`: carpetas y archivos del proyecto.
- `docs/diseno_pantallas.md`: diseño y pantallas por rol.
- `docs/seguridad_aplicacion.md` y `docs/justificacion_seguridad.md`: seguridad.
- `docs/despliegue_docker.md`: despliegue con Docker.
