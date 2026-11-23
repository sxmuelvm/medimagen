# Justificación de las decisiones de seguridad

El sistema maneja datos de salud (diagnósticos, recetas, resultados) y datos personales. Por eso la seguridad se resolvió en tres capas que se refuerzan entre sí: la base de datos, la aplicación y el navegador.

## 1. ¿Por qué roles de MySQL y una cuenta por rol?
- Conectar la aplicación como `root` significaría que cualquier error de código podría borrar o leer todo. Con una cuenta por rol, aunque haya un error en la aplicación, MySQL sigue negando lo que ese rol no puede hacer.
- Los permisos se escriben una sola vez en un rol (`rol_recepcion`, `rol_medico`, …) y las cuentas `usr_*` solo reciben el rol (`GRANT rol TO usuario`). Así no se dan privilegios uno por uno a cada cuenta, y cambiar un permiso es cambiar una línea.
- Excepciones controladas: `usr_login` (solo lectura de lo necesario para autenticar) y `usr_reportes` (solo lectura de una vista de ingresos).
- Los datos clínicos están separados: recepción no puede leer diagnósticos ni recetas; el paciente solo ve vistas filtradas.

## 2. ¿Por qué triggers y restricciones en la base?
Las reglas de negocio importantes (no doble reserva, horario de atención, perfil correcto por rol) están en MySQL y no solo en Python. Si mañana otra aplicación o una persona con Workbench escribe en la base, las reglas se cumplen igual. Una cita cancelada libera el horario porque la restricción única usa la columna `activa`, que vale `NULL` en citas canceladas.

## 3. ¿Por qué una sola cédula en `usuario`?
Antes la tabla tenía una columna para el médico y otra para el paciente, lo que repetía información y permitía estados incoherentes. Una sola `cedula` única es más simple; un trigger comprueba que exista en la ficha que corresponde al rol y copia los nombres para que no se contradigan.

## 4. ¿Por qué nombres de usuario automáticos?
Evita que dos personas elijan el mismo nombre, que se usen nombres adivinables o inventados y que haya errores de escritura. La regla es conocida y predecible (`cmarin`, `cmarin01`…), y como el administrador no los escribe, se reducen los errores.

## 5. ¿Por qué `pbkdf2:sha256`?
Es un hash lento y con sal, incluido en Werkzeug, que dificulta los ataques de fuerza bruta si se filtra la base. No se guarda ni se muestra nunca una clave. Las claves temporales se muestran una sola vez y obligan a cambiarlas.

## 6. ¿Por qué bloqueo y límite de intentos?
Con 5 intentos fallidos la cuenta se bloquea 15 minutos, y además hay un tope de intentos por IP. Detiene la adivinación de claves sin dejar la cuenta bloqueada para siempre.

## 7. ¿Por qué CSP estricta y sin scripts en línea?
La política `script-src 'self'; style-src 'self'` bloquea cualquier script o estilo inyectado, que es la forma más común de robar sesiones (XSS). Por eso todo el JavaScript y CSS vive en archivos propios y los estilos dinámicos se aplican con clases.

## 8. ¿Por qué el servidor decide los permisos?
Esconder un botón no protege nada: cualquiera puede escribir la dirección a mano. Cada ruta comprueba el rol y, cuando hay datos de una persona (paciente, médico), el dato sale de la sesión y no de lo que mande el formulario.

## 9. ¿Por qué CSRF y cookies `HttpOnly`/`SameSite`?
Impiden que otra página haga acciones en nombre de un usuario conectado y que un script lea la cookie de sesión.

## 10. ¿Por qué se desactiva en lugar de eliminar?
Las citas, consultas y resultados son un historial médico. Se conserva: un usuario, médico o paciente con actividad no se elimina, se desactiva. Solo se puede eliminar un registro creado por error y nunca usado.
