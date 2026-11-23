# Diseño de pantallas

## 1. Identidad visual
- **Personalidad:** clínica, cercana y confiable. Es un sistema interno de trabajo: manda la claridad, no el adorno.
- **Logo:** `static/img/logo.png` (Medimagen Cuenca), centrado en la parte superior del menú lateral.
- **Colores** (definidos como variables en `static/css/base.css`):
  - Primario `#007c89` (turquesa oscuro) para botones y acciones principales; el blanco sobre este color cumple contraste 4.95:1.
  - Azul profundo `#0b2d5b` para títulos.
  - Celeste muy suave `#eaf6f7` para elementos activos y encabezados.
  - Fondo `#f5f7f9` y bordes grises claros.
  - Estados: éxito (verde), aviso (ámbar), error (rojo), información (azul), siempre con texto además del color.
- **Tipografía:** Figtree, alojada en el propio proyecto (`static/fonts`), con tipografías del sistema como respaldo. Escala de 13 a 18 px en textos y espaciado en múltiplos de 4 px.

## 2. Estructura de cada pantalla
- Menú lateral con el logo, las opciones del rol, "Mi perfil" y "Cerrar sesión".
- Cabecera con ruta de navegación (migas), título, subtítulo y, si aplica, el botón de acción principal.
- Contenido en paneles blancos con borde fino. Mensajes de éxito y error arriba, con ícono y texto.
- En el celular el menú se abre como panel a pantalla completa con botón de cerrar.

## 3. Pantallas por rol
| Rol | Menú |
|---|---|
| Administrador | Panel, Usuarios, Roles, Médicos, Pacientes, Especialidades, Catálogos, Calendario, Reportes |
| Recepción | Panel, Pacientes, Calendario, Nueva cita |
| Médico | Panel, Calendario, Mi agenda, Exámenes solicitados |
| Imagenología | Panel, Calendario, Agenda |
| Laboratorio | Panel, Calendario, Agenda |
| Paciente | Panel, Mis citas, Mi historial, Mis recetas, Mis resultados |

## 4. Pantallas principales
- **Ingreso:** foto, usuario y contraseña. Tras cambiar la clave obligatoria se entra al panel.
- **Panel:** resumen por rol (próximas citas, pendientes, conteos). El paciente solo ve el estado de una cita si fue cancelada.
- **Calendario semanal:** de lunes a viernes, de 07:00 a 18:00, en bloques de una hora. Cada área tiene su color (consulta, imagenología, laboratorio).
  - Recepción y administrador hacen clic en un horario libre para agendar, filtran por área y médico y pueden mostrar u ocultar las citas canceladas.
  - Al elegir una cita se abre un panel con sus datos y las acciones permitidas para el rol.
  - El paciente solo ve sus citas y puede cancelar las que aún no empiezan.
- **Nueva cita:** paso 1 busca al paciente por cédula (10 dígitos) o por nombre con sugerencias; paso 2 elige el tipo de atención; paso 3 el médico o examen; paso 4 la fecha y las horas libres. El consultorio, equipo o puesto se asigna solo.
- **Solicitar examen (médico):** misma búsqueda de paciente y los mismos horarios libres.
- **Atender consulta:** motivo, diagnóstico, observaciones y receta con varios medicamentos.
- **Imagenología y laboratorio:** agenda del área y registro de la realización o del resultado.
- **Usuarios:** lista con búsqueda, creación con la cédula (el nombre de usuario se genera y se muestra al terminar), cambio de estado y restablecimiento de clave.
- **Historial del paciente:** consultas, recetas y resultados, solo de lectura.

## 5. Accesibilidad y adaptación a pantallas
- Funciona desde 320 px (celular) hasta pantallas grandes: el calendario muestra un día a la vez en el celular y la semana completa en computador.
- Todo se puede usar con teclado, con foco visible y áreas táctiles de al menos 44 px.
- Cada campo tiene su etiqueta; los avisos usan regiones `aria-live`.
- Las animaciones son mínimas y respetan `prefers-reduced-motion`.
- Sin JavaScript, los formularios siguen funcionando (por ejemplo, el botón "Buscar paciente" reaparece).
