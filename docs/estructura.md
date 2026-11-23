# Estructura del proyecto

```
medimagen/
├── backups/
│   └── medimagen_20261117_193211.sql
├── database/
│   ├── extras/
│   │   ├── 00_limpieza.sql
│   │   ├── 06_consultas.sql
│   │   ├── 07_verificacion.sql
│   │   └── 08_consultas_avanzadas.sql
│   ├── init/
│   │   ├── 01_tablas_vistas.sql
│   │   ├── 02_triggers.sql
│   │   ├── 03_datos.sql
│   │   ├── 04_roles.sql
│   │   └── 05_usuarios.sql
│   └── Dockerfile
├── docs/
│   ├── despliegue_docker.md
│   ├── diseno_pantallas.md
│   ├── estructura.md
│   ├── justificacion_seguridad.md
│   └── seguridad_aplicacion.md
├── my-app/
│   ├── conexion/
│   │   ├── __init__.py
│   │   └── conexionBD.py
│   ├── controllers/
│   │   ├── __init__.py
│   │   ├── auth_controller.py
│   │   ├── calendario_controller.py
│   │   ├── catalogos_controller.py
│   │   ├── citas_controller.py
│   │   ├── consultas_controller.py
│   │   ├── dashboard_controller.py
│   │   ├── especialidades_controller.py
│   │   ├── historial_controller.py
│   │   ├── imagenologia_controller.py
│   │   ├── laboratorio_controller.py
│   │   ├── medicos_controller.py
│   │   ├── pacientes_controller.py
│   │   ├── perfil_controller.py
│   │   ├── reportes_controller.py
│   │   ├── roles_controller.py
│   │   └── usuarios_controller.py
│   ├── logs/
│   │   └── .gitkeep
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── router_auth.py
│   │   ├── router_calendario.py
│   │   ├── router_catalogos.py
│   │   ├── router_citas.py
│   │   ├── router_consultas.py
│   │   ├── router_dashboard.py
│   │   ├── router_especialidades.py
│   │   ├── router_historial.py
│   │   ├── router_imagenologia.py
│   │   ├── router_laboratorio.py
│   │   ├── router_medicos.py
│   │   ├── router_pacientes.py
│   │   ├── router_perfil.py
│   │   ├── router_reportes.py
│   │   ├── router_roles.py
│   │   ├── router_salud.py
│   │   └── router_usuarios.py
│   ├── scripts/
│   │   ├── generar_hash.py
│   │   ├── probar_conexiones.py
│   │   └── respaldo_bd.py
│   ├── static/
│   │   ├── css/
│   │   │   ├── admin.css
│   │   │   ├── atencion.css
│   │   │   ├── base.css
│   │   │   ├── calendario.css
│   │   │   ├── citas.css
│   │   │   ├── clave.css
│   │   │   ├── components.css
│   │   │   ├── dashboard.css
│   │   │   ├── forms.css
│   │   │   ├── layout.css
│   │   │   ├── login.css
│   │   │   ├── print.css
│   │   │   ├── responsive.css
│   │   │   └── tables.css
│   │   ├── fonts/
│   │   │   ├── LICENSE-Figtree-OFL.txt
│   │   │   ├── figtree-latin-ext.woff2
│   │   │   └── figtree-latin.woff2
│   │   ├── img/
│   │   │   ├── acceso.jpg
│   │   │   └── logo.png
│   │   ├── js/
│   │   │   ├── core/
│   │   │   │   ├── http.js
│   │   │   │   ├── interfaz.js
│   │   │   │   ├── tablas.js
│   │   │   │   ├── ui.js
│   │   │   │   └── validaciones.js
│   │   │   └── modules/
│   │   │       ├── buscar_paciente.js
│   │   │       ├── calendario.js
│   │   │       ├── citas.js
│   │   │       ├── clave.js
│   │   │       ├── consultas.js
│   │   │       ├── imprimir.js
│   │   │       ├── login.js
│   │   │       └── usuarios.js
│   │   └── favicon.ico
│   ├── templates/
│   │   ├── components/
│   │   │   ├── _acciones.html
│   │   │   ├── _campo_formulario.html
│   │   │   ├── _estado_badge.html
│   │   │   ├── _filtros.html
│   │   │   ├── _icono.html
│   │   │   ├── _modal_confirmar.html
│   │   │   ├── _paginacion.html
│   │   │   └── _tabla.html
│   │   ├── errors/
│   │   │   ├── 400.html
│   │   │   ├── 403.html
│   │   │   ├── 404.html
│   │   │   ├── 429.html
│   │   │   ├── 500.html
│   │   │   └── _error.html
│   │   ├── layout/
│   │   │   ├── _footer.html
│   │   │   ├── _iconos.html
│   │   │   ├── _mensajes.html
│   │   │   ├── _navbar.html
│   │   │   └── _sidebar.html
│   │   ├── public/
│   │   │   ├── auth/
│   │   │   │   └── login.html
│   │   │   ├── calendario/
│   │   │   │   └── semana.html
│   │   │   ├── catalogos/
│   │   │   │   ├── _subnav.html
│   │   │   │   ├── areas.html
│   │   │   │   ├── index.html
│   │   │   │   ├── recursos.html
│   │   │   │   ├── subtipos_examen.html
│   │   │   │   └── tipos_examen.html
│   │   │   ├── citas/
│   │   │   │   ├── detalle.html
│   │   │   │   ├── nueva.html
│   │   │   │   └── reprogramar.html
│   │   │   ├── consultas/
│   │   │   │   ├── atender.html
│   │   │   │   ├── examenes_solicitados.html
│   │   │   │   ├── mi_agenda.html
│   │   │   │   ├── modificar_examen.html
│   │   │   │   ├── resultado_examen.html
│   │   │   │   └── solicitar_examen.html
│   │   │   ├── dashboard/
│   │   │   │   ├── administrador.html
│   │   │   │   ├── imagenologia.html
│   │   │   │   ├── laboratorio.html
│   │   │   │   ├── medico.html
│   │   │   │   ├── paciente.html
│   │   │   │   └── recepcion.html
│   │   │   ├── especialidades/
│   │   │   │   ├── formulario.html
│   │   │   │   └── lista.html
│   │   │   ├── historial/
│   │   │   │   ├── mi_historial.html
│   │   │   │   ├── mis_datos.html
│   │   │   │   ├── mis_recetas.html
│   │   │   │   └── mis_resultados.html
│   │   │   ├── imagenologia/
│   │   │   │   ├── agenda.html
│   │   │   │   └── registrar_realizacion.html
│   │   │   ├── laboratorio/
│   │   │   │   ├── agenda.html
│   │   │   │   └── registrar_resultado.html
│   │   │   ├── medicos/
│   │   │   │   ├── formulario.html
│   │   │   │   └── lista.html
│   │   │   ├── pacientes/
│   │   │   │   ├── ficha.html
│   │   │   │   ├── formulario.html
│   │   │   │   └── lista.html
│   │   │   ├── perfil/
│   │   │   │   ├── cambiar_clave.html
│   │   │   │   └── mi_perfil.html
│   │   │   ├── reportes/
│   │   │   │   └── ingresos.html
│   │   │   ├── roles/
│   │   │   │   ├── formulario.html
│   │   │   │   └── lista.html
│   │   │   └── usuarios/
│   │   │       ├── crear.html
│   │   │       ├── editar.html
│   │   │       ├── lista.html
│   │   │       └── restablecer_clave.html
│   │   └── base.html
├── .dockerignore
├── .env
├── .env.example
├── .gitignore
├── Dockerfile
├── README.md
├── docker-compose.yml
└── requirements.txt
```

## Qué hace cada parte

| Carpeta / archivo | Función |
|---|---|
| `database/init` | Scripts que crean la base `medimagen2`: tablas y vistas (01), triggers y procedimientos (02), datos de ejemplo (03), roles de MySQL (04) y cuentas (05). Son los que ejecuta Docker. |
| `database/Dockerfile` | Imagen de MySQL para Docker: copia `database/init` para que se ejecute al crear el volumen. |
| `database/extras` | Scripts de apoyo que no ejecuta Docker: limpieza (00), consultas del proyecto (06), verificación de reglas (07) y consultas avanzadas (08). |
| `backups` | Destino de `scripts/respaldo_bd.py`. Los respaldos nuevos (`.sql`) no se suben a Git. |
| `Dockerfile`, `docker-compose.yml`, `.dockerignore` | Despliegue con Docker (ver `docs/despliegue_docker.md`). |
| `requirements.txt` | Dependencias de la aplicación. |
| `docs` | Documentación del proyecto. |
| `my-app/app.py`, `run.py`, `config.py`, `extensions.py` | Fábrica de la aplicación Flask, arranque local, configuración (lee `.env`) y extensiones (CSRF, limitador). |
| `my-app/conexion` | Conexión a MySQL con una reserva de conexiones por cuenta (`usr_*`). |
| `my-app/routers` | Rutas (URL) de cada módulo. Cada `router_*.py` se registra solo al arrancar. |
| `my-app/controllers` | Lógica de cada módulo: validaciones, consultas SQL y reglas. Los routers solo reciben la petición y devuelven la respuesta. |
| `my-app/utils` | Piezas compartidas: constantes y menús por rol, seguridad (hash, cabeceras), decoradores de permisos, validaciones, errores, registro. |
| `my-app/templates` | Páginas Jinja. `layout` y `components` son piezas reutilizables; `public/<módulo>` tiene las pantallas; `dashboard/<rol>.html` y `errors/<código>.html` se eligen por nombre al responder. |
| `my-app/static` | CSS, JavaScript (`core` comparte funciones; `modules` es por pantalla), fuentes, logo e imagen de ingreso. Sin estilos ni scripts en línea (lo exige la política de seguridad). |
| `my-app/scripts` | Herramientas de apoyo: generar un hash de clave, probar las conexiones y hacer respaldos. |
| `my-app/logs` | Registro de la aplicación (no se sube a Git). |
| `env/` | Entorno virtual de Python (solo local, no se sube a Git). |

## Módulos de la aplicación
`auth`, `dashboard`, `perfil`, `usuarios`, `roles`, `medicos`, `pacientes`, `especialidades`, `catalogos`, `calendario`, `citas`, `consultas`, `imagenologia`, `laboratorio`, `historial`, `reportes` y `salud`. Cada uno tiene su `router_*.py` y su `*_controller.py` (salvo `salud`, que solo responde si la aplicación está viva).

## Cambios respecto a versiones anteriores
- El calendario semanal reemplaza las listas de citas de todos los roles.
- Se eliminó el módulo de auditoría, el de personal (ahora el personal es un usuario más), los catálogos de medicamentos y bloques de horario, y las carpetas vacías `database/backups` y `database/migrations`.
