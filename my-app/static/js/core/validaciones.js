/* Medimagen Cuenca · ayuda de validación en el navegador para los formularios con `data-validar`.
   El servidor es quien decide: esto solo avisa antes y en el campo correcto. Los mensajes y las reglas
   (cédula de 10 dígitos, teléfono de 7 a 15 dígitos, correo) son las mismas que aplica el backend.
   Sin JavaScript el formulario se envía igual y el servidor responde con sus propios mensajes. */
(function () {
  "use strict";

  var Medimagen = window.Medimagen = window.Medimagen || {};

  var REGLAS = {
    cedula: { patron: /^\d{10}$/, mensaje: "La cédula debe tener exactamente 10 dígitos." },
    telefono: { patron: /^\d{7,15}$/, mensaje: "El teléfono debe tener entre 7 y 15 dígitos." },
    correo: { patron: /^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$/, mensaje: "El correo no es válido." }
  };

  function reglaDe(campo) {
    var nombre = campo.name;
    if (nombre === "cedula" || nombre === "cedula_paciente") { return REGLAS.cedula; }
    if (nombre === "telefono") { return REGLAS.telefono; }
    if (nombre === "correo") { return REGLAS.correo; }
    return null;
  }

  function mensajeDe(campo) {
    var valor = campo.value.trim();
    if (campo.required && !valor) { return "Este campo es obligatorio."; }
    if (!valor) { return ""; }
    var regla = reglaDe(campo);
    if (regla && !regla.patron.test(valor)) { return regla.mensaje; }
    if (campo.maxLength > 0 && valor.length > campo.maxLength) { return "Escribe como máximo " + campo.maxLength + " caracteres."; }
    return "";
  }

  function marcar(campo, mensaje) {
    var contenedor = campo.closest(".campo");
    var id = (campo.id || campo.name) + "-error";
    var error = document.getElementById(id);
    var base = (campo.getAttribute("data-descripcion-base") || "");
    if (campo.getAttribute("data-descripcion-base") === null) {
      base = (campo.getAttribute("aria-describedby") || "").replace(id, "").trim();
      campo.setAttribute("data-descripcion-base", base);
    }
    if (mensaje) {
      if (!error) {
        error = document.createElement("p");
        error.className = "campo__error";
        error.id = id;
        (contenedor || campo.parentNode).appendChild(error);
      }
      error.textContent = mensaje;
      campo.setAttribute("aria-invalid", "true");
      campo.setAttribute("aria-describedby", (base + " " + id).trim());
      if (contenedor) { contenedor.classList.add("campo--error"); }
    } else {
      if (error) { error.parentNode.removeChild(error); }
      campo.removeAttribute("aria-invalid");
      if (base) { campo.setAttribute("aria-describedby", base); } else { campo.removeAttribute("aria-describedby"); }
      if (contenedor) { contenedor.classList.remove("campo--error"); }
    }
  }

  function validarCampo(campo) {
    var mensaje = mensajeDe(campo);
    marcar(campo, mensaje);
    return mensaje === "";
  }

  Array.prototype.forEach.call(document.querySelectorAll("form[data-validar]"), function (formulario) {
    var campos = Array.prototype.slice.call(formulario.querySelectorAll("input.campo__control, textarea.campo__control, select.campo__control"));

    campos.forEach(function (campo) {
      campo.addEventListener("blur", function () { validarCampo(campo); });
      campo.addEventListener("input", function () {
        if (campo.getAttribute("aria-invalid") === "true") { validarCampo(campo); }
      });
    });

    formulario.addEventListener("submit", function (e) {
      var primero = null;
      campos.forEach(function (campo) {
        if (campo.disabled) { return; }
        if (!validarCampo(campo) && !primero) { primero = campo; }
      });
      if (primero) {
        e.preventDefault();
        primero.focus();
      }
    });
  });

  Medimagen.validaciones = {
    cedula: function (v) { return REGLAS.cedula.patron.test(String(v || "").trim()); },
    telefono: function (v) { return REGLAS.telefono.patron.test(String(v || "").trim()); },
    correo: function (v) { return REGLAS.correo.patron.test(String(v || "").trim()); }
  };
}());
