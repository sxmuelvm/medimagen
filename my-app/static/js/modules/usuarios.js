/* Medimagen · formulario de nuevo usuario: según el rol elegido solo se muestra (y se envía) la lista de
   perfiles que le corresponde (médico, paciente o personal). Sin JavaScript se ven las tres listas. */
(function () {
  "use strict";

  var formulario = document.querySelector("[data-formulario-usuario]");
  if (!formulario) { return; }

  var selector = formulario.querySelector("[data-selector-rol]");
  var grupos = Array.prototype.slice.call(formulario.querySelectorAll("[data-grupo-perfil]"));

  function actualizar() {
    var opcion = selector.options[selector.selectedIndex];
    var tipo = opcion ? opcion.getAttribute("data-tipo") : "";
    grupos.forEach(function (grupo) {
      var activo = grupo.getAttribute("data-grupo-perfil") === tipo;
      grupo.hidden = !activo;
      grupo.disabled = !activo;           /* un fieldset deshabilitado no envía sus campos */
      Array.prototype.forEach.call(grupo.querySelectorAll("select, input"), function (campo) {
        campo.required = activo;
      });
    });
  }

  selector.addEventListener("change", actualizar);
  actualizar();
}());
