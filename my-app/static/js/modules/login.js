/* Medimagen Cuenca · pantalla de acceso: aviso de Bloq Mayús.
   (El ojo para ver la contraseña lo pone js/modules/clave.js.) Sin JavaScript el formulario funciona igual. */
(function () {
  "use strict";

  var clave = document.getElementById("clave");

  if (!clave) { return; }
  var campo = clave.closest(".campo");

  var aviso = document.createElement("p");
  aviso.className = "campo__ayuda";
  aviso.id = "aviso-mayusculas";
  aviso.setAttribute("role", "status");
  aviso.hidden = true;
  aviso.textContent = "Tienes el bloqueo de mayúsculas activado.";
  campo.appendChild(aviso);
  clave.setAttribute("aria-describedby", "aviso-mayusculas");

  function revisar(e) {
    if (e.getModifierState) { aviso.hidden = !e.getModifierState("CapsLock"); }
  }
  clave.addEventListener("keydown", revisar);
  clave.addEventListener("keyup", revisar);
  clave.addEventListener("blur", function () { aviso.hidden = true; });
}());
