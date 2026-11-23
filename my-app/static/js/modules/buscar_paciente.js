/* Medimagen Cuenca · busqueda de paciente por cedula o nombre con sugerencias mientras se escribe.
   Pide /citas/pacientes?q=... y muestra hasta 8 opciones; al elegir una se abre la nueva cita de ese paciente,
   conservando la fecha, hora y medico que llegaron del calendario. Sin JavaScript, el formulario sigue buscando
   en el servidor (el boton "Buscar paciente" solo se oculta cuando JavaScript funciona). Una cedula completa que
   existe abre directo al paciente; Enter elige la opcion marcada o la unica que hay. El texto entra con textContent. */
(function () {
  "use strict";

  var formulario = document.querySelector("[data-buscar-paciente]");
  if (!formulario || !window.Medimagen || !Medimagen.http) { return; }

  var campo = formulario.querySelector("[data-campo-busqueda]");
  var lista = formulario.querySelector("[data-sugerencias]");
  var urlSugerencias = formulario.getAttribute("data-url-sugerencias");
  var urlNueva = formulario.getAttribute("data-url-nueva");
  var temporizador = null;
  var pedido = 0;
  var activa = -1;
  var opciones = [];

  function destino(cedula) {
    var p = { cedula: cedula };
    formulario.querySelectorAll("[data-previo]").forEach(function (c) { p[c.name] = c.value; });
    return urlNueva + Medimagen.http.consulta(p);
  }

  function cerrar() {
    lista.hidden = true;
    lista.textContent = "";
    opciones = [];
    activa = -1;
    campo.setAttribute("aria-expanded", "false");
    campo.removeAttribute("aria-activedescendant");
  }

  function marcar(indice) {
    opciones.forEach(function (o, i) { o.setAttribute("aria-selected", i === indice ? "true" : "false"); });
    activa = indice;
    if (indice >= 0) {
      campo.setAttribute("aria-activedescendant", opciones[indice].id);
      opciones[indice].scrollIntoView({ block: "nearest" });
    } else {
      campo.removeAttribute("aria-activedescendant");
    }
  }

  function mostrar(pacientes, texto) {
    lista.textContent = "";
    opciones = [];
    activa = -1;
    if (!pacientes.length) {
      var vacio = document.createElement("li");
      vacio.className = "sugerencias__vacio";
      vacio.textContent = "No hay pacientes con «" + texto + "».";
      lista.appendChild(vacio);
    }
    pacientes.forEach(function (p, i) {
      var li = document.createElement("li");
      li.id = "sugerencia-" + i;
      li.className = "sugerencias__opcion";
      li.setAttribute("role", "option");
      li.setAttribute("aria-selected", "false");
      var nombre = document.createElement("span");
      nombre.className = "sugerencias__nombre";
      nombre.textContent = p.nombre;
      var dato = document.createElement("span");
      dato.className = "sugerencias__dato";
      dato.textContent = "Cédula " + p.cedula_paciente + " · " + p.edad + " años" + (p.estado !== "activo" ? " · Inactivo" : "");
      li.appendChild(nombre);
      li.appendChild(dato);
      li.addEventListener("mousedown", function (e) { e.preventDefault(); });   // no pierde el foco antes del clic
      li.addEventListener("click", function () { window.location.href = destino(p.cedula_paciente); });
      lista.appendChild(li);
      opciones.push(li);
    });
    lista.hidden = false;
    campo.setAttribute("aria-expanded", "true");
  }

  function buscar() {
    var texto = campo.value.replace(/\s+/g, " ").trim();
    if (texto.length < 2) { cerrar(); return; }
    var mio = ++pedido;
    Medimagen.http.json(urlSugerencias, { parametros: { q: texto } }).then(function (r) {
      if (mio !== pedido) { return; }                       // llego tarde: ya se escribio otra cosa
      if (!r.ok) { cerrar(); return; }
      var encontrados = r.datos.pacientes || [];
      // Cedula completa (10 digitos) que existe: se abre ese paciente sin hacer mas
      if (/^\d{10}$/.test(texto) && encontrados.length === 1 && encontrados[0].cedula_paciente === texto) {
        window.location.href = destino(texto);
        return;
      }
      mostrar(encontrados, texto);
    }, cerrar);
  }

  campo.addEventListener("input", function () {
    // Solo numeros = cedula: maximo 10 digitos. En cuanto hay una letra se escribe libremente (nombre y apellido).
    if (/^\d+$/.test(campo.value) && campo.value.length > 10) { campo.value = campo.value.slice(0, 10); }
    window.clearTimeout(temporizador);
    temporizador = window.setTimeout(buscar, 250);
  });

  campo.addEventListener("keydown", function (e) {
    if (e.key === "Escape") { cerrar(); return; }
    if (!opciones.length) { return; }
    if (e.key === "ArrowDown") { e.preventDefault(); marcar((activa + 1) % opciones.length); }
    else if (e.key === "ArrowUp") { e.preventDefault(); marcar(activa <= 0 ? opciones.length - 1 : activa - 1); }
    else if (e.key === "Enter" && activa >= 0) { e.preventDefault(); opciones[activa].click(); }
    else if (e.key === "Enter" && opciones.length === 1) { e.preventDefault(); opciones[0].click(); }   // una sola opcion
  });

  document.addEventListener("click", function (e) { if (!formulario.contains(e.target)) { cerrar(); } });
}());
