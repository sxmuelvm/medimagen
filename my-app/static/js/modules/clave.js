/* Medimagen Cuenca · botón de "ojo" para ver u ocultar la contraseña.
   Se aplica a todos los campos de contraseña de la página (inicio de sesión y cambio de contraseña).
   Mejora progresiva: sin JavaScript el campo sigue siendo una contraseña normal.
   El botón es accesible: tiene nombre, indica su estado con aria-pressed y se maneja con teclado.
   Por seguridad la contraseña se vuelve a ocultar sola al enviar el formulario o al salir de la página. */
(function () {
  "use strict";

  var NS = "http://www.w3.org/2000/svg";
  var OJO = ["M2 12s3.6-6.5 10-6.5S22 12 22 12s-3.6 6.5-10 6.5S2 12 2 12z"];
  var TACHADO = ["M3 3l18 18", "M10.6 5.6A10.5 10.5 0 0 1 12 5.5c6.4 0 10 6.5 10 6.5a17 17 0 0 1-3.2 3.9M6.4 7.4A17 17 0 0 0 2 12s3.6 6.5 10 6.5a10 10 0 0 0 4-.8"];

  function dibujar(svg, trazos, conPupila) {
    while (svg.firstChild) { svg.removeChild(svg.firstChild); }
    trazos.forEach(function (d) {
      var p = document.createElementNS(NS, "path");
      p.setAttribute("d", d);
      svg.appendChild(p);
    });
    if (conPupila) {
      var c = document.createElementNS(NS, "circle");
      c.setAttribute("cx", "12"); c.setAttribute("cy", "12"); c.setAttribute("r", "3");
      svg.appendChild(c);
    }
  }

  Array.prototype.forEach.call(document.querySelectorAll("input[type='password']"), function (campo) {
    if (campo.closest(".campo__clave")) { return; }

    var envoltorio = document.createElement("div");
    envoltorio.className = "campo__clave";
    campo.parentNode.insertBefore(envoltorio, campo);
    envoltorio.appendChild(campo);

    var boton = document.createElement("button");
    boton.type = "button";
    boton.className = "campo__ojo";
    boton.setAttribute("aria-pressed", "false");
    boton.setAttribute("aria-label", "Mostrar contraseña");
    boton.setAttribute("title", "Mostrar contraseña");
    boton.setAttribute("data-sin-bloqueo", "");

    var svg = document.createElementNS(NS, "svg");
    svg.setAttribute("class", "icono");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("focusable", "false");
    dibujar(svg, OJO, true);
    boton.appendChild(svg);
    envoltorio.appendChild(boton);

    function mostrar(visible) {
      campo.type = visible ? "text" : "password";
      boton.setAttribute("aria-pressed", visible ? "true" : "false");
      var texto = visible ? "Ocultar contraseña" : "Mostrar contraseña";
      boton.setAttribute("aria-label", texto);
      boton.setAttribute("title", texto);
      dibujar(svg, visible ? TACHADO : OJO, !visible);
    }

    boton.addEventListener("click", function () {
      mostrar(campo.type === "password");
      campo.focus();
    });

    if (campo.form) { campo.form.addEventListener("submit", function () { mostrar(false); }); }
    window.addEventListener("pagehide", function () { mostrar(false); });
  });
}());
