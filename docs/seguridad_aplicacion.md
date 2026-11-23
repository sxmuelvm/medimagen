# Seguridad de la aplicación

Resumen de lo que protege a Medimagen Cuenca desde el código Flask. La justificación de cada decisión está en `justificacion_seguridad.md`.

## 1. Inicio de sesión y claves
- Las claves se guardan con hash `pbkdf2:sha256` (werkzeug). Nunca en texto.
- Política de claves nuevas: de 8 a 128 caracteres, con letras y números, distinta de la cédula y del nombre de usuario.
- Bloqueo de cuenta: 5 intentos fallidos seguidos bloquean la cuenta 15 minutos (`MAX_INTENTOS`, `MINUTOS_BLOQUEO`). El administrador puede desbloquearla.
- Límite de intentos por IP en el login (10 por minuto y 60 por hora, contando solo los fallidos) y en el cambio de clave (5 por minuto).
- Si el usuario no existe se compara contra un hash de relleno, para que la respuesta tarde igual y no se pueda saber qué usuarios existen. El mensaje de error es el mismo en todos los casos.
- Las cuentas de ejemplo y las creadas por el administrador nacen con `cambio_clave_obligatorio`: hasta que la persona cambie su clave solo puede ir a esa pantalla o cerrar sesión.
- La sesión se cierra por inactividad a los 60 minutos (`SESION_INACTIVIDAD_MIN`).
- En cada petición se comprueba en la base que el usuario siga activo y con el mismo rol. Si se desactiva o cambia de rol, la sesión se invalida.

## 2. Nombres de usuario y cédula
- El nombre de usuario lo genera MySQL (inicial del nombre + primer apellido, por ejemplo `cmarin`; si existe, `cmarin01`, `cmarin02`…). Nadie lo escribe a mano, salvo `admin`, y no se puede cambiar después.
- Cada persona se identifica con una sola `cedula` (única) en la tabla `usuario`. La base comprueba que un usuario médico o paciente tenga su ficha.

## 3. Permisos por rol
- Cada ruta declara qué roles pueden entrar (`roles_permitidos`). Ocultar un botón en pantalla es solo comodidad: el permiso real lo aplica el servidor.
- El paciente solo ve y cancela sus propias citas (la cédula sale de la sesión, nunca de un formulario). Solo puede cambiar su teléfono, su correo y su contraseña.
- El médico solo ve sus consultas y los exámenes que solicitó. Si pide la cita de otro médico, la respuesta es "no existe".
- Recepción y administrador agendan; imagenología y laboratorio solo ven y registran lo de su área.

## 4. Base de datos
- La aplicación no se conecta como `root`. Usa siete cuentas de MySQL, una por rol (`usr_login`, `usr_administrador`, `usr_recepcion`, `usr_medico`, `usr_imagenologia`, `usr_laboratorio`, `usr_paciente`).
- Cada cuenta tiene solo los permisos de su rol (ver `database/init/04_roles.sql`). `usr_login` solo lee las columnas necesarias para autenticar.
- Todas las consultas llevan parámetros (`%s`). Nunca se arma SQL con texto del usuario.
- Los triggers validan reglas que ni siquiera el código puede saltarse: citas de lunes a viernes de 07:00 a 18:00, un solo médico y un solo paciente por horario, perfil correcto por rol.
- Los usuarios no se eliminan si ya tienen actividad (llaves foráneas); se desactivan.

## 5. Formularios y navegador
- Todos los formularios y peticiones que cambian datos llevan token CSRF (Flask-WTF).
- Cabeceras en todas las respuestas: `Content-Security-Policy` estricta (sin scripts ni estilos en línea), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin` y `Permissions-Policy`.
- Cookie de sesión `HttpOnly` y `SameSite=Lax`.
- Jinja escapa todo por defecto. El JavaScript escribe con `textContent`, nunca con `innerHTML`.
- Tamaño máximo de petición: 1 MB.

## 6. Validación de datos
- Cada dato se valida en el servidor (cédula de 10 dígitos, correo, teléfono, fechas laborables, horas en bloques de una hora) y los mensajes de error se muestran sin detalles técnicos.
- Los errores de MySQL se traducen a mensajes claros; el detalle técnico solo queda en el registro (`my-app/logs`).

## 7. Registro
- Se registran inicios y cierres de sesión, fallos, bloqueos y cambios importantes, sin guardar nunca claves. Los registros quedan en `my-app/logs` (o en el volumen `app_logs` de Docker).

## 8. Pendientes conocidos
- `SESSION_COOKIE_SECURE` está en `False` porque aún no hay HTTPS. Debe pasar a `True` cuando se publique detrás de un certificado.
- El limitador de intentos cuenta por proceso (`memory://`). Con varios workers de gunicorn el límite real es mayor; para producción se usaría Redis.
