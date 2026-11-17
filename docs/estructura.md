medimagen/
│
├── .env
├── .env.example
├── .gitignore
├── .dockerignore
├── README.md
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
│
├── database/
│   ├── init/
│   │   ├── 01_tablas_vistas.sql
│   │   ├── 02_triggers.sql
│   │   ├── 03_datos.sql
│   │   ├── 04_roles.sql
│   │   └── 05_usuarios.sql
│   ├── extras/
│   │   ├── 00_limpieza.sql
│   │   ├── 06_consultas.sql
│   │   └── 07_verificacion.sql
│   ├── migrations/
│   │   └── .gitkeep
│   └── backups/
│       └── .gitkeep
│
├── docs/
│   ├── justificacion_seguridad.md
│   ├── seguridad_aplicacion.md
│   ├── despliegue_docker.md
│   └── diseno_pantallas.md
│
└── my-app/
    ├── app.py
    ├── run.py
    ├── config.py
    ├── extensions.py
    ├── pytest.ini
    │
    ├── conexion/
    │   ├── __init__.py
    │   └── conexionBD.py
    │
    ├── controllers/
    │   ├── __init__.py
    │   ├── auth_controller.py
    │   ├── dashboard_controller.py
    │   ├── perfil_controller.py
    │   ├── usuarios_controller.py
    │   ├── roles_controller.py
    │   ├── personal_controller.py
    │   ├── medicos_controller.py
    │   ├── pacientes_controller.py
    │   ├── especialidades_controller.py
    │   ├── catalogos_controller.py
    │   ├── citas_controller.py
    │   ├── consultas_controller.py
    │   ├── imagenologia_controller.py
    │   ├── laboratorio_controller.py
    │   ├── historial_controller.py
    │   ├── reportes_controller.py
    │   └── auditoria_controller.py
    │
    ├── routers/
    │   ├── __init__.py
    │   ├── router_auth.py
    │   ├── router_dashboard.py
    │   ├── router_perfil.py
    │   ├── router_usuarios.py
    │   ├── router_roles.py
    │   ├── router_personal.py
    │   ├── router_medicos.py
    │   ├── router_pacientes.py
    │   ├── router_especialidades.py
    │   ├── router_catalogos.py
    │   ├── router_citas.py
    │   ├── router_consultas.py
    │   ├── router_imagenologia.py
    │   ├── router_laboratorio.py
    │   ├── router_historial.py
    │   ├── router_reportes.py
    │   ├── router_auditoria.py
    │   └── router_salud.py
    │
    ├── utils/
    │   ├── __init__.py
    │   ├── constants.py
    │   ├── security.py
    │   ├── decorators.py
    │   ├── context.py
    │   ├── menu.py
    │   ├── errors.py
    │   ├── validators.py
    │   ├── helpers.py
    │   └── logger.py
    │
    ├── templates/
    │   ├── base.html
    │   ├── layout/
    │   │   ├── _navbar.html
    │   │   ├── _sidebar.html
    │   │   ├── _footer.html
    │   │   └── _mensajes.html
    │   ├── components/
    │   │   ├── _tabla.html
    │   │   ├── _paginacion.html
    │   │   ├── _campo_formulario.html
    │   │   ├── _modal_confirmar.html
    │   │   └── _estado_badge.html
    │   ├── errors/
    │   │   ├── 400.html
    │   │   ├── 403.html
    │   │   ├── 404.html
    │   │   ├── 429.html
    │   │   └── 500.html
    │   └── public/
    │       ├── auth/
    │       │   └── login.html
    │       ├── perfil/
    │       │   ├── mi_perfil.html
    │       │   └── cambiar_clave.html
    │       ├── dashboard/
    │       │   ├── administrador.html
    │       │   ├── recepcion.html
    │       │   ├── medico.html
    │       │   ├── imagenologia.html
    │       │   ├── laboratorio.html
    │       │   └── paciente.html
    │       ├── usuarios/
    │       │   ├── lista.html
    │       │   ├── crear.html
    │       │   ├── editar.html
    │       │   └── restablecer_clave.html
    │       ├── roles/
    │       │   ├── lista.html
    │       │   └── formulario.html
    │       ├── personal/
    │       │   ├── lista.html
    │       │   └── formulario.html
    │       ├── medicos/
    │       │   ├── lista.html
    │       │   └── formulario.html
    │       ├── pacientes/
    │       │   ├── lista.html
    │       │   ├── formulario.html
    │       │   └── ficha.html
    │       ├── especialidades/
    │       │   ├── lista.html
    │       │   └── formulario.html
    │       ├── catalogos/
    │       │   ├── index.html
    │       │   ├── areas.html
    │       │   ├── recursos.html
    │       │   ├── tipos_examen.html
    │       │   ├── subtipos_examen.html
    │       │   ├── medicamentos.html
    │       │   └── bloques_horario.html
    │       ├── citas/
    │       │   ├── agenda.html
    │       │   ├── nueva.html
    │       │   ├── reprogramar.html
    │       │   └── detalle.html
    │       ├── consultas/
    │       │   ├── mi_agenda.html
    │       │   ├── atender.html
    │       │   ├── solicitar_examen.html
    │       │   └── examenes_solicitados.html
    │       ├── imagenologia/
    │       │   ├── agenda.html
    │       │   └── registrar_realizacion.html
    │       ├── laboratorio/
    │       │   ├── agenda.html
    │       │   └── registrar_resultado.html
    │       ├── historial/
    │       │   ├── mis_citas.html
    │       │   ├── mi_historial.html
    │       │   ├── mis_recetas.html
    │       │   └── mis_resultados.html
    │       ├── reportes/
    │       │   └── ingresos.html
    │       └── auditoria/
    │           ├── lista.html
    │           └── accesos.html
    │
    ├── static/
    │   ├── css/
    │   │   ├── base.css
    │   │   ├── layout.css
    │   │   ├── components.css
    │   │   ├── forms.css
    │   │   ├── tables.css
    │   │   ├── login.css
    │   │   └── responsive.css
    │   ├── js/
    │   │   ├── core/
    │   │   │   ├── http.js
    │   │   │   ├── ui.js
    │   │   │   ├── validaciones.js
    │   │   │   └── tablas.js
    │   │   └── modules/
    │   │       ├── login.js
    │   │       ├── usuarios.js
    │   │       ├── citas.js
    │   │       └── consultas.js
    │   └── img/
    │       └── .gitkeep
    │
    ├── scripts/
    │   ├── generar_hash.py
    │   ├── probar_conexiones.py
    │   └── respaldo_bd.py
    │
    ├── logs/
    │   └── .gitkeep
    │
    └── tests/
        ├── conftest.py
        ├── test_auth.py
        ├── test_permisos.py
        ├── test_usuarios.py
        ├── test_citas.py
        ├── test_historial.py
        └── test_seguridad.py