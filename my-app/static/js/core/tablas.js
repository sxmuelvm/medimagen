/* Medimagen Cuenca · listados con filtros.
   En los formularios de filtro con `data-filtros-auto`, al cambiar una lista o una fecha se aplica el filtro
   sin pulsar "Filtrar". El buscador de texto sigue usando Enter o el botón. Sin JavaScript todo funciona con
   el botón "Filtrar", que se queda visible siempre. */
(function () {
  "use strict";

  Array.prototype.forEach.call(document.querySelectorAll("form[data-filtros-auto]"), function (formulario) {
    var temporizador = null;

    formulario.addEventListener("change", function (e) {
      var campo = e.target;
      if (!campo.matches || !campo.matches("select, input[type='date']")) { return; }
      if (campo.type === "date" && campo.value && !campo.validity.valid) { return; }
      window.clearTimeout(temporizador);
      /* Pequeña espera: si la persona cambia dos filtros seguidos solo se envía el último. */
      temporizador = window.setTimeout(function () {
        if (typeof formulario.requestSubmit === "function") { formulario.requestSubmit(); }
        else { formulario.submit(); }
      }, 300);
    });
  });
}());
