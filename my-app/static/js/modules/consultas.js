/* Medimagen Cuenca · pantallas del médico.
   1) Atender consulta: agregar y quitar filas de diagnósticos y de medicamentos.
   2) Solicitar examen: según el examen elegido se muestran los equipos o puestos de su área, se calcula el
      costo estimado y se consultan los horarios libres (necesita core/http.js).
   Sin JavaScript el formulario sigue funcionando: se ven todas las filas y todas las opciones, y el servidor valida. */
(function () {
  "use strict";

  /* ---------- 1) Filas repetibles ---------- */
  Array.prototype.forEach.call(document.querySelectorAll("[data-lista-filas]"), function (bloque) {
    var lista = bloque.querySelector("[data-filas]");
    var plantilla = bloque.querySelector("template[data-plantilla-fila]");
    var agregar = bloque.querySelector("[data-agregar-fila]");
    var maximo = parseInt(bloque.getAttribute("data-maximo"), 10) || 20;
    if (!lista || !plantilla || !agregar) { return; }
    var contador = lista.children.length;

    function filas() { return Array.prototype.slice.call(lista.querySelectorAll("[data-fila]")); }

    function actualizar() {
      var todas = filas();
      todas.forEach(function (fila, i) {
        var titulo = fila.querySelector("[data-numero-fila]");
        if (titulo) { titulo.textContent = titulo.getAttribute("data-prefijo") + " " + (i + 1); }
        var quitar = fila.querySelector("[data-quitar-fila]");
        if (quitar) { quitar.hidden = todas.length <= 1; }
      });
      agregar.hidden = false;
      agregar.disabled = todas.length >= maximo;
    }

    function nueva() {
      contador += 1;
      var fila = plantilla.content.firstElementChild.cloneNode(true);
      Array.prototype.forEach.call(fila.querySelectorAll("[id], [for]"), function (el) {
        if (el.id) { el.id = el.id.replace(/-N$/, "-" + contador); }
        if (el.htmlFor) { el.htmlFor = el.htmlFor.replace(/-N$/, "-" + contador); }
      });
      return fila;
    }

    agregar.addEventListener("click", function () {
      if (filas().length >= maximo) { return; }
      var fila = nueva();
      lista.appendChild(fila);
      actualizar();
      var primero = fila.querySelector("input, select, textarea");
      if (primero) { primero.focus(); }
    });

    lista.addEventListener("click", function (e) {
      var boton = e.target.closest("[data-quitar-fila]");
      if (!boton) { return; }
      var fila = boton.closest("[data-fila]");
      var anterior = fila.previousElementSibling || fila.nextElementSibling;
      lista.removeChild(fila);
      actualizar();
      if (anterior) {
        var campo = anterior.querySelector("input, select, textarea");
        if (campo) { campo.focus(); }
      }
    });

    actualizar();
  });

  /* ---------- 2) Solicitar examen ---------- */
  var formulario = document.querySelector("[data-formulario-examen]");
  if (!formulario) { return; }

  var url = formulario.getAttribute("data-url-horarios");
  var campoExamen = formulario.querySelector("[data-campo-examen]");
  var campoRecurso = formulario.querySelector("[data-campo-recurso]");
  var campoFecha = formulario.querySelector("input[name='fecha_cita']");
  var campoHora = formulario.querySelector("[data-campo-hora]");
  var estado = formulario.querySelector("[data-estado-horarios]");
  var resumen = formulario.querySelector("[data-resumen-costo]");
  var valorCosto = formulario.querySelector("[data-costo-valor]");
  var paciente = formulario.getAttribute("data-paciente") || "";
  var temporizador = null;
  var solicitud = 0;

  var opcionesRecurso = Array.prototype.slice.call(campoRecurso.options);

  function opcionExamen() {
    return campoExamen.selectedIndex > 0 ? campoExamen.options[campoExamen.selectedIndex] : null;
  }

  function areaActual() {
    var o = opcionExamen();
    return o ? o.getAttribute("data-area") : "";
  }

  function mensaje(texto, vacio) {
    estado.textContent = texto;
    estado.classList.toggle("horarios-estado--vacio", !!vacio);
  }

  function filtrarRecursos() {
    var area = areaActual();
    var previo = campoRecurso.value;
    while (campoRecurso.firstChild) { campoRecurso.removeChild(campoRecurso.firstChild); }
    opcionesRecurso.forEach(function (o) {
      var esFijo = o.hasAttribute("data-fijo");
      if ((esFijo && area !== "2") || (!esFijo && area && o.getAttribute("data-area") === area)) { campoRecurso.appendChild(o); }
    });
    /* En imagenología el equipo es obligatorio (cada uno hace estudios distintos): no hay "asignar automáticamente". */
    var esImagen = area === "2";
    if (esImagen) {
      var elegir = document.createElement("option");
      elegir.value = "";
      elegir.textContent = "Elige el equipo…";
      campoRecurso.insertBefore(elegir, campoRecurso.firstChild);
    }
    campoRecurso.required = esImagen;
    var existe = Array.prototype.some.call(campoRecurso.options, function (o) { return o.value === previo; });
    campoRecurso.value = existe ? previo : "";
  }

  function mostrarCosto() {
    var o = opcionExamen();
    var costo = o ? parseFloat(o.getAttribute("data-costo")) : NaN;
    if (isNaN(costo)) { resumen.hidden = true; return; }
    valorCosto.textContent = "$ " + costo.toFixed(2);
    resumen.hidden = false;
  }

  function llenarHoras(lista) {
    var previa = campoHora.value;
    while (campoHora.firstChild) { campoHora.removeChild(campoHora.firstChild); }
    var inicial = document.createElement("option");
    inicial.value = "";
    inicial.textContent = lista.length ? "Elige una hora…" : "Sin horarios libres";
    campoHora.appendChild(inicial);
    lista.forEach(function (h) {
      var op = document.createElement("option");
      op.value = h.hora_inicio;
      op.textContent = h.hora_inicio + " – " + h.hora_fin;
      campoHora.appendChild(op);
    });
    campoHora.value = lista.some(function (h) { return h.hora_inicio === previa; }) ? previa : "";
  }

  function esFinDeSemana(valor) {
    var p = valor.split("-");
    var dia = new Date(+p[0], +p[1] - 1, +p[2]).getDay();
    return dia === 0 || dia === 6;
  }

  function consultarHorarios() {
    var fecha = campoFecha.value;
    var area = areaActual();
    if (!area) { mensaje("Elige primero el examen.", false); return; }
    if (!fecha) { return; }
    if (esFinDeSemana(fecha)) {
      llenarHoras([]);
      mensaje("No se atiende los sábados ni los domingos. Elige un día de lunes a viernes.", true);
      return;
    }
    if (!window.Medimagen || !window.Medimagen.http) { return; }
    var numero = ++solicitud;
    mensaje("Buscando horarios libres…", false);
    window.Medimagen.http.json(url, { parametros: { fecha: fecha, id_area: area, id_recurso: campoRecurso.value, cedula_paciente: paciente } })
      .then(function (r) {
        if (numero !== solicitud) { return; }
        if (!r.ok) { mensaje(r.error, true); return; }
        var lista = r.datos.horarios || [];
        llenarHoras(lista);
        mensaje(lista.length
          ? lista.length + (lista.length === 1 ? " horario libre" : " horarios libres") + " ese día."
          : "No quedan horarios libres ese día. Prueba con otra fecha u otro equipo.", !lista.length);
      })
      .catch(function () {
        if (numero !== solicitud) { return; }
        mensaje("No se pudo comprobar la disponibilidad. Puedes elegir una hora y el sistema la validará al guardar.", true);
      });
  }

  function pedirHorarios() {
    window.clearTimeout(temporizador);
    temporizador = window.setTimeout(consultarHorarios, 250);
  }

  if (!campoFecha.min) {
    var hoy = new Date();
    campoFecha.min = hoy.getFullYear() + "-" + ("0" + (hoy.getMonth() + 1)).slice(-2) + "-" + ("0" + hoy.getDate()).slice(-2);
  }

  campoExamen.addEventListener("change", function () { filtrarRecursos(); mostrarCosto(); pedirHorarios(); });
  campoRecurso.addEventListener("change", pedirHorarios);
  campoFecha.addEventListener("change", pedirHorarios);
  campoFecha.addEventListener("input", pedirHorarios);

  filtrarRecursos();
  mostrarCosto();
  if (campoFecha.value && areaActual()) { pedirHorarios(); }
}());
