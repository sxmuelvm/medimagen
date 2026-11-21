/* Medimagen Cuenca · pantalla de acceso: cédula solo con dígitos y aviso de Bloq Mayús.
   (El ojo para ver la contraseña lo pone js/modules/clave.js.) Sin JavaScript el formulario funciona igual. */
(function () {
  "use strict";

  var cedula = document.getElementById("cedula");
  var clave = document.getElementById("clave");

  if (cedula) {
    cedula.addEventListener("input", function () {
      var limpio = cedula.value.replace(/\D/g, "").slice(0, 10);
      if (limpio !== cedula.value) { cedula.value = limpio; }
    });
  }

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
