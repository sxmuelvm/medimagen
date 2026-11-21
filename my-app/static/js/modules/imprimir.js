/* Medimagen Cuenca · botón "Imprimir" (cualquier elemento con data-imprimir).
   Los botones llevan `hidden` y solo se muestran si hay JavaScript, porque sin él no harían nada. */
(function () {
  "use strict";
  Array.prototype.forEach.call(document.querySelectorAll("[data-imprimir][hidden]"), function (b) { b.hidden = false; });
  document.addEventListener("click", function (e) {
    var boton = e.target.closest("[data-imprimir]");
    if (boton) { window.print(); }
  });
})();
