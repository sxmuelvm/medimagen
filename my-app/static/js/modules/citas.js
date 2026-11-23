/* Medimagen Cuenca · formularios de nueva cita y de reprogramar.
   - Muestra solo los campos del área elegida (consulta, imagenología o laboratorio).
   - Consulta /citas/horarios y deja en la lista únicamente las horas libres.
   - Muestra el costo estimado según el médico o el examen elegido.
   Sin JavaScript el formulario sigue funcionando: se ven todos los campos y las 11 horas posibles,
   y el servidor valida todo. */
(function () {
  "use strict";

  var formulario = document.querySelector("[data-formulario-cita]");
  if (!formulario) { return; }

  var url = formulario.getAttribute("data-url-horarios");
  var excluir = formulario.getAttribute("data-excluir") || "";
  var campoFecha = formulario.querySelector("[data-campo-fecha], input[name='fecha_cita']");
  var campoHora = formulario.querySelector("[data-campo-hora]");
  var estado = formulario.querySelector("[data-estado-horarios]");
  var radios = Array.prototype.slice.call(formulario.querySelectorAll("[data-campo-area]"));
  var grupos = Array.prototype.slice.call(formulario.querySelectorAll("[data-grupo-area]"));
  var porArea = Array.prototype.slice.call(formulario.querySelectorAll("select[data-por-area]"));
  var resumen = formulario.querySelector("[data-resumen-costo]");
  var valorCosto = formulario.querySelector("[data-costo-valor]");
  var avisoSinJs = formulario.querySelector("[data-solo-sin-js]");
  var temporizador = null;
  var solicitud = 0;

  /* Se guardan los grupos de opciones originales para poder reconstruir la lista según el área. */
  var originales = porArea.map(function (select) {
    return {
      select: select,
      inicial: select.options[0],
      grupos: Array.prototype.slice.call(select.querySelectorAll("optgroup"))
    };
  });

  function areaActual() {
    var marcado = radios.filter(function (r) { return r.checked; })[0];
    return marcado ? marcado.value : (formulario.getAttribute("data-area") || "");
  }

  function medicoActual() {
    var fijo = formulario.getAttribute("data-medico");
    if (fijo) { return fijo; }
    var selector = formulario.querySelector("[data-campo-medico]");
    return selector ? selector.value : "";
  }

  function cedulaActual() {
    var oculto = formulario.querySelector("input[name='cedula_paciente']");
    return oculto ? oculto.value : (formulario.getAttribute("data-paciente") || "");
  }

  function recursoActual() {
    var selector = formulario.querySelector("[data-campo-recurso]");
    return selector ? selector.value : "";
  }

  /* El equipo de imagenología lo decide el examen: se manda el examen y el servidor busca su equipo. */
  function subtipoActual() {
    var selector = formulario.querySelector("select[name='id_subtipo']");
    return selector ? selector.value : "";
  }

  function mostrarGrupos(area) {
    grupos.forEach(function (grupo) {
      var areas = grupo.getAttribute("data-grupo-area").split(" ");
      var activo = areas.indexOf(area) !== -1;
      grupo.hidden = !activo;
      Array.prototype.forEach.call(grupo.querySelectorAll("select, input, textarea"), function (campo) {
        campo.disabled = !activo;
      });
    });
    if (avisoSinJs) { avisoSinJs.hidden = true; }
  }

  function reconstruirListas(area) {
    originales.forEach(function (o) {
      var previo = o.select.value;
      while (o.select.firstChild) { o.select.removeChild(o.select.firstChild); }
      o.select.appendChild(o.inicial);
      o.grupos.forEach(function (g) {
        if (g.getAttribute("data-area") === area) { o.select.appendChild(g); }
      });
      var existe = Array.prototype.some.call(o.select.options, function (op) { return op.value === previo; });
      o.select.value = existe ? previo : "";
    });
  }

  function mostrarCosto() {
    if (!resumen) { return; }
    var area = areaActual();
    var origen = area === "1"
      ? formulario.querySelector("[data-campo-medico]")
      : formulario.querySelector("select[name='id_subtipo']");
    var opcion = origen && origen.selectedIndex > 0 ? origen.options[origen.selectedIndex] : null;
    var costo = opcion ? parseFloat(opcion.getAttribute("data-costo")) : NaN;
    if (isNaN(costo)) { resumen.hidden = true; return; }
    valorCosto.textContent = "$ " + costo.toFixed(2);
    resumen.hidden = false;
  }

  function mensaje(texto, vacio) {
    if (!estado) { return; }
    estado.textContent = texto;
    estado.classList.toggle("horarios-estado--vacio", !!vacio);
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
    var sigue = lista.some(function (h) { return h.hora_inicio === previa; });
    campoHora.value = sigue ? previa : "";
  }

  function esFinDeSemana(valor) {
    var partes = valor.split("-");
    var dia = new Date(+partes[0], +partes[1] - 1, +partes[2]).getDay();
    return dia === 0 || dia === 6;
  }

  function consultarHorarios() {
    var fecha = campoFecha.value;
    var area = areaActual();
    if (!fecha || !area || !campoHora) { return; }
    if (esFinDeSemana(fecha)) {
      llenarHoras([]);
      mensaje("No se atiende los sábados ni los domingos. Elige un día de lunes a viernes.", true);
      return;
    }
    var parametros = ["fecha=" + encodeURIComponent(fecha), "id_area=" + encodeURIComponent(area)];
    var medico = medicoActual();
    var recurso = recursoActual();
    var paciente = cedulaActual();
    if (area === "1" && medico) { parametros.push("id_medico=" + encodeURIComponent(medico)); }
    if (recurso) { parametros.push("id_recurso=" + encodeURIComponent(recurso)); }
    if (area === "2" && subtipoActual()) { parametros.push("id_subtipo=" + encodeURIComponent(subtipoActual())); }
    if (paciente) { parametros.push("cedula_paciente=" + encodeURIComponent(paciente)); }
    if (excluir) { parametros.push("excluir_cita=" + encodeURIComponent(excluir)); }

    var numero = ++solicitud;
    mensaje("Buscando horarios libres…", false);
    fetch(url + "?" + parametros.join("&"), { headers: { "Accept": "application/json" }, credentials: "same-origin" })
      .then(function (respuesta) {
        return respuesta.json().then(function (datos) { return { ok: respuesta.ok, datos: datos }; });
      })
      .then(function (r) {
        if (numero !== solicitud) { return; }       /* llegó una respuesta más nueva */
        if (!r.ok) {
          mensaje(r.datos.error || "No se pudieron consultar los horarios.", true);
          return;
        }
        var lista = r.datos.horarios || [];
        llenarHoras(lista);
        if (lista.length) {
          mensaje(lista.length + (lista.length === 1 ? " horario libre" : " horarios libres") + " ese día.", false);
        } else {
          mensaje("No quedan horarios libres ese día. Prueba con otra fecha" +
                  (area === "1" ? " u otro médico." : "."), true);
        }
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

  function alCambiarArea() {
    var area = areaActual();
    mostrarGrupos(area);
    reconstruirListas(area);
    mostrarCosto();
    pedirHorarios();
  }

  /* Fecha mínima: hoy (hora local del navegador; el servidor valida de todos modos). */
  if (campoFecha && !campoFecha.min) {
    var hoy = new Date();
    campoFecha.min = hoy.getFullYear() + "-" + ("0" + (hoy.getMonth() + 1)).slice(-2) + "-" + ("0" + hoy.getDate()).slice(-2);
  }

  radios.forEach(function (r) { r.addEventListener("change", alCambiarArea); });
  if (campoFecha) {
    campoFecha.addEventListener("change", pedirHorarios);
    campoFecha.addEventListener("input", pedirHorarios);
  }
  Array.prototype.forEach.call(formulario.querySelectorAll("[data-campo-medico], [data-campo-recurso]"), function (c) {
    c.addEventListener("change", pedirHorarios);
  });
  Array.prototype.forEach.call(formulario.querySelectorAll("[data-origen-costo]"), function (c) {
    c.addEventListener("change", mostrarCosto);
    c.addEventListener("change", pedirHorarios);
  });

  if (radios.length) {
    alCambiarArea();
  } else if (campoFecha && campoFecha.value) {
    pedirHorarios();
  }
}());
