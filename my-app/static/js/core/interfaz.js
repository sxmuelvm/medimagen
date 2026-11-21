/* Medimagen · comportamiento común de la interfaz: menú móvil, avisos y confirmación de acciones.
   Mejora progresiva: sin este archivo todo funciona con enlaces y envíos normales del servidor. */
(function () {
  "use strict";

  var consultaEscritorio = window.matchMedia("(min-width: 56.25rem)");

  /* ---------- Menú lateral en móvil ---------- */
  var menu = document.querySelector("[data-menu]");
  var abrir = document.querySelector("[data-abrir-menu]");
  var cerrar = document.querySelector("[data-cerrar-menu]");

  function enfocables(raiz) {
    return Array.prototype.slice.call(
      raiz.querySelectorAll('a[href], button:not([disabled]), input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])')
    ).filter(function (el) { return el.offsetParent !== null; });
  }

  function menuAbierto() {
    return menu && menu.classList.contains("lateral--abierto");
  }

  function abrirMenu() {
    if (!menu) { return; }
    menu.classList.add("lateral--abierto");
    document.body.classList.add("sin-desplazamiento");
    if (abrir) { abrir.setAttribute("aria-expanded", "true"); }
    if (cerrar) { cerrar.focus(); }
  }

  function cerrarMenu(devolverFoco) {
    if (!menuAbierto()) { return; }
    menu.classList.remove("lateral--abierto");
    document.body.classList.remove("sin-desplazamiento");
    if (abrir) {
      abrir.setAttribute("aria-expanded", "false");
      if (devolverFoco) { abrir.focus(); }
    }
  }

  if (menu && abrir) {
    abrir.addEventListener("click", abrirMenu);
    if (cerrar) { cerrar.addEventListener("click", function () { cerrarMenu(true); }); }

    menu.addEventListener("click", function (e) {
      if (e.target.closest("a.menu__enlace")) { cerrarMenu(false); }
    });

    document.addEventListener("keydown", function (e) {
      if (!menuAbierto()) { return; }
      if (e.key === "Escape") { cerrarMenu(true); return; }
      if (e.key !== "Tab") { return; }
      var lista = enfocables(menu);
      if (!lista.length) { return; }
      var primero = lista[0];
      var ultimo = lista[lista.length - 1];
      if (e.shiftKey && document.activeElement === primero) { e.preventDefault(); ultimo.focus(); }
      else if (!e.shiftKey && document.activeElement === ultimo) { e.preventDefault(); primero.focus(); }
    });

    /* Al pasar a escritorio (girar la tableta, ensanchar la ventana) el panel deja de ser un overlay */
    var alCambiar = function () { if (consultaEscritorio.matches) { cerrarMenu(false); } };
    if (consultaEscritorio.addEventListener) { consultaEscritorio.addEventListener("change", alCambiar); }
    else if (consultaEscritorio.addListener) { consultaEscritorio.addListener(alCambiar); }
  }

  /* ---------- Avisos que se pueden cerrar ---------- */
  document.addEventListener("click", function (e) {
    var boton = e.target.closest("[data-cerrar-mensaje]");
    if (!boton) { return; }
    var aviso = boton.closest(".mensaje");
    var contenedor = aviso && aviso.parentNode;
    if (aviso) { aviso.remove(); }
    if (contenedor && !contenedor.querySelector(".mensaje")) { contenedor.remove(); }
  });

  /* ---------- Confirmación de acciones (form[data-confirmar="¿Texto?"]) ---------- */
  var dialogo = document.querySelector("[data-dialogo]");
  var soportaDialogo = dialogo && typeof dialogo.showModal === "function";
  var formularioPendiente = null;
  var disparador = null;

  if (soportaDialogo) {
    var texto = dialogo.querySelector("[data-dialogo-texto]");
    var aceptar = dialogo.querySelector("[data-dialogo-aceptar]");

    document.addEventListener("submit", function (e) {
      var formulario = e.target;
      var mensaje = formulario.getAttribute && formulario.getAttribute("data-confirmar");
      if (!mensaje || formulario.getAttribute("data-confirmado") === "1") { return; }
      e.preventDefault();
      formularioPendiente = formulario;
      disparador = e.submitter || document.activeElement;
      texto.textContent = mensaje;
      aceptar.textContent = formulario.getAttribute("data-confirmar-boton") || "Confirmar";
      dialogo.showModal();
    });

    dialogo.addEventListener("close", function () {
      var formulario = formularioPendiente;
      formularioPendiente = null;
      if (dialogo.returnValue === "aceptar" && formulario) {
        formulario.setAttribute("data-confirmado", "1");
        if (typeof formulario.requestSubmit === "function") { formulario.requestSubmit(); }
        else { formulario.submit(); }
      } else if (disparador && disparador.focus) {
        disparador.focus();
      }
      dialogo.returnValue = "";
    });

    /* Cerrar al pulsar fuera del cuadro */
    dialogo.addEventListener("click", function (e) { if (e.target === dialogo) { dialogo.close("cancelar"); } });
  }

  /* ---------- Evitar doble envío ---------- */
  document.addEventListener("submit", function (e) {
    var formulario = e.target;
    if (e.defaultPrevented || !formulario.matches || !formulario.matches("form")) { return; }
    if (formulario.getAttribute("data-confirmar") && formulario.getAttribute("data-confirmado") !== "1") { return; }
    var botones = formulario.querySelectorAll('button[type="submit"]:not([data-sin-bloqueo])');
    window.setTimeout(function () {
      Array.prototype.forEach.call(botones, function (b) {
        b.classList.add("boton--cargando");
        b.setAttribute("aria-busy", "true");
        b.disabled = true;
      });
    }, 0);
  });

  /* Al volver con "atrás" el navegador puede restaurar la página con botones bloqueados */
  window.addEventListener("pageshow", function (e) {
    if (!e.persisted) { return; }
    Array.prototype.forEach.call(document.querySelectorAll(".boton--cargando"), function (b) {
      b.classList.remove("boton--cargando");
      b.removeAttribute("aria-busy");
      b.disabled = false;
    });
  });
}());