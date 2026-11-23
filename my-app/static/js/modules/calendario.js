/* Medimagen Cuenca · calendario semanal de citas.
   Pide /calendario/datos?fecha=...&id_area=...&id_medico=... y dibuja lunes a viernes, de 07:00 a 18:00.
   Todo el texto entra con textContent (nada de innerHTML con datos del servidor). */
(function () {
  "use strict";

  var raiz = document.querySelector("[data-calendario]");
  if (!raiz || !window.Medimagen || !Medimagen.http) { return; }

  var DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie"];
  var MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
  var AREAS = { 1: "Consulta", 2: "Imagenología", 3: "Laboratorio" };
  var ESTADOS = { pendiente: "Pendiente", confirmada: "Confirmada", atendida: "Atendida", cancelada: "Cancelada", no_asistio: "No asistió" };

  var rejilla = raiz.querySelector("[data-cal-rejilla]");
  var rango = raiz.querySelector("[data-cal-rango]");
  var estado = raiz.querySelector("[data-cal-estado]");
  var barraDias = raiz.querySelector("[data-cal-dias]");
  var panel = raiz.querySelector("[data-cal-detalle]");
  var selArea = raiz.querySelector("[data-cal-area]");
  var selMedico = raiz.querySelector("[data-cal-medico]");
  var verCanceladas = raiz.querySelector("[data-cal-canceladas]");   // recepción y administrador: por defecto no se ven, el horario queda libre
  var puedeAgendar = raiz.getAttribute("data-puede-agendar") === "si";
  var soloCancelada = raiz.getAttribute("data-solo-cancelada") === "si";   // el paciente solo ve el estado si la cita fue cancelada
  var urlNueva = raiz.getAttribute("data-url-nueva");
  var urlDatos = raiz.getAttribute("data-url-datos");

  var fecha = "";       // cualquier dia de la semana mostrada (vacio = la semana de hoy)
  var datos = null;
  var diaActivo = 1;
  var origenFoco = null;

  function el(etiqueta, clase, texto) {
    var nodo = document.createElement(etiqueta);
    if (clase) { nodo.className = clase; }
    if (texto !== undefined && texto !== null) { nodo.textContent = texto; }
    return nodo;
  }

  function partes(iso) { var p = iso.split("-"); return { a: +p[0], m: +p[1], d: +p[2] }; }
  function sumar(iso, dias) {
    var p = partes(iso);
    var f = new Date(Date.UTC(p.a, p.m - 1, p.d + dias));
    return f.toISOString().slice(0, 10);
  }
  function corta(iso) { var p = partes(iso); return p.d + " " + MESES[p.m - 1]; }

  function avisar(texto, error) {
    estado.textContent = texto || "";
    estado.classList.toggle("cal__estado--error", !!error);
  }

  function cargar() {
    avisar("Cargando…");
    Medimagen.http.json(urlDatos, {
      parametros: { fecha: fecha, id_area: selArea ? selArea.value : "", id_medico: selMedico ? selMedico.value : "" }
    }).then(function (r) {
      if (!r.ok) { avisar(r.error, true); return; }
      datos = r.datos;
      fecha = datos.lunes;
      dibujar();
    }, function () { avisar("No hay conexión con el servidor. Revisa tu red e inténtalo de nuevo.", true); });
  }

  function visible(c) {
    if (!verCanceladas || verCanceladas.checked) { return true; }
    return c.estado !== "cancelada" && c.estado !== "no_asistio";
  }

  function esPasado(iso, hora) { return (iso + " " + hora) <= datos.ahora; }

  function enlaceLibre(iso, hora) {
    var p = { fecha_cita: iso, hora_inicio: hora };
    if (selArea && selArea.value) { p.id_area = selArea.value; }
    if (selMedico && selMedico.value) { p.id_area = "1"; p.id_medico = selMedico.value; }
    var a = el("a", "cal__libre", "+ Agendar");
    a.href = urlNueva + Medimagen.http.consulta(p);
    a.setAttribute("aria-label", "Agendar el " + corta(iso) + " a las " + hora);
    return a;
  }

  function tarjeta(c) {
    var b = el("button", "cal__cita cal__cita--a" + c.area + " cal__cita--" + c.estado);
    b.type = "button";
    var marca = soloCancelada ? (c.estado === "cancelada" ? "Cancelada · " : "") : (c.estado === "atendida" ? "✓ " : "");
    var titulo = marca + c.hora + " · " + (c.area === 1 ? (c.medico || "") : (c.detalle || ""));
    var sub = puedeAgendar ? c.paciente : (c.area === 1 ? c.detalle : c.medico && ("Solicita: " + c.medico));
    b.appendChild(el("span", "cal__cita-t", titulo));
    if (sub) { b.appendChild(el("span", "cal__cita-s", sub)); }
    b.setAttribute("aria-label", c.hora + ", " + AREAS[c.area] + (!soloCancelada || c.estado === "cancelada" ? ", " + (ESTADOS[c.estado] || c.estado) : "") + ". Ver detalle");
    b.addEventListener("click", function () { abrir(c, b); });
    return b;
  }

  function dibujar() {
    var primera = datos.primera, ultima = datos.ultima;
    rejilla.textContent = "";
    barraDias.textContent = "";
    rango.textContent = corta(datos.lunes) + " – " + corta(datos.viernes) + " " + partes(datos.viernes).a;

    var hoyDia = 0;
    if (datos.hoy >= datos.lunes && datos.hoy <= datos.viernes) {
      hoyDia = new Date(datos.hoy + "T00:00:00Z").getUTCDay();
      hoyDia = hoyDia === 0 ? 7 : hoyDia;
    }
    if (!diaActivo || diaActivo < 1 || diaActivo > 5) { diaActivo = 1; }
    if (hoyDia && !raiz.dataset.visto) { diaActivo = hoyDia; raiz.dataset.visto = "1"; }

    rejilla.appendChild(el("div", "cal__cab"));
    for (var d = 1; d <= 5; d++) {
      var iso = sumar(datos.lunes, d - 1);
      var cab = el("div", "cal__cab" + (d === hoyDia ? " cal__cab--hoy" : "") + (d === diaActivo ? " es-activo" : ""));
      cab.setAttribute("data-dia", d);
      cab.setAttribute("role", "columnheader");
      cab.appendChild(document.createTextNode(DIAS[d - 1]));
      cab.appendChild(el("strong", "", String(partes(iso).d)));
      rejilla.appendChild(cab);

      var tab = el("button", "cal__dia-boton", DIAS[d - 1] + " " + partes(iso).d);
      tab.type = "button";
      tab.setAttribute("role", "tab");
      tab.setAttribute("aria-selected", d === diaActivo ? "true" : "false");
      (function (n) { tab.addEventListener("click", function () { diaActivo = n; dibujar(); }); }(d));
      barraDias.appendChild(tab);
    }

    for (var h = primera; h <= ultima; h++) {
      var hora = (h < 10 ? "0" : "") + h + ":00";
      rejilla.appendChild(el("div", "cal__hora", hora));
      for (var dia = 1; dia <= 5; dia++) {
        var fechaCelda = sumar(datos.lunes, dia - 1);
        var pasada = esPasado(fechaCelda, hora);
        var celda = el("div", "cal__celda" + (pasada ? " cal__celda--pasada" : "") + (dia === hoyDia ? " cal__celda--hoy" : "") + (dia === diaActivo ? " es-activo" : ""));
        celda.setAttribute("data-dia", dia);
        celda.setAttribute("role", "gridcell");
        datos.citas.forEach(function (c) {
          if (c.dia === dia && c.hora === hora && visible(c)) { celda.appendChild(tarjeta(c)); }
        });
        if (puedeAgendar && !pasada) { celda.appendChild(enlaceLibre(fechaCelda, hora)); }
        rejilla.appendChild(celda);
      }
    }
    avisar(datos.citas.some(visible) ? "" : "No hay citas esta semana.");
  }

  function fila(lista, etiqueta, valor) {
    if (!valor) { return; }
    var f = el("div");
    f.appendChild(el("dt", "", etiqueta));
    f.appendChild(el("dd", "", valor));
    lista.appendChild(f);
  }

  function abrir(c, boton) {
    origenFoco = boton;
    raiz.querySelectorAll(".cal__cita--elegida").forEach(function (n) { n.classList.remove("cal__cita--elegida"); });
    boton.classList.add("cal__cita--elegida");
    panel.querySelector("[data-cal-d-titulo]").textContent = AREAS[c.area] + " · " + c.hora + " – " + c.hora_fin;
    var lista = panel.querySelector("[data-cal-d-lista]");
    lista.textContent = "";
    var p = partes(c.fecha);
    fila(lista, "Fecha", DIAS[c.dia - 1] + " " + p.d + " " + MESES[p.m - 1] + " " + p.a);
    if (puedeAgendar) { fila(lista, "Paciente", c.paciente + " (" + c.cedula + ")"); }
    fila(lista, c.area === 1 ? "Médico" : "Solicita", c.medico);
    fila(lista, c.area === 1 ? "Especialidad" : "Examen", c.detalle);
    fila(lista, "Lugar", c.lugar);
    if (!soloCancelada || c.estado === "cancelada") { fila(lista, "Estado", ESTADOS[c.estado] || c.estado); }

    var acciones = panel.querySelector("[data-cal-d-acciones]");
    acciones.textContent = "";
    c.acciones.forEach(function (a) {
      if (a.metodo === "post") {
        var f = el("form");
        f.method = "post";
        f.action = a.url;
        var t = document.createElement("input");
        t.type = "hidden"; t.name = "csrf_token";
        t.value = (document.querySelector('input[name="csrf_token"]') || {}).value || "";
        f.appendChild(t);
        var pedir = el("button", "boton boton--peligro", a.texto);
        pedir.type = "button";
        var aviso = el("p", "cal__confirmar", "¿Seguro que quieres cancelar esta cita?");
        var si = el("button", "boton boton--peligro", "Sí, cancelar");
        si.type = "submit";
        var no = el("button", "boton boton--secundario", "No");
        no.type = "button";
        aviso.hidden = si.hidden = no.hidden = true;
        pedir.addEventListener("click", function () { pedir.hidden = true; aviso.hidden = si.hidden = no.hidden = false; si.focus(); });
        no.addEventListener("click", function () { pedir.hidden = false; aviso.hidden = si.hidden = no.hidden = true; pedir.focus(); });
        [pedir, aviso, si, no].forEach(function (n) { f.appendChild(n); });
        acciones.appendChild(f);
      } else {
        var enlace = el("a", "boton boton--primario", a.texto);
        enlace.href = a.url;
        acciones.appendChild(enlace);
      }
    });
    panel.hidden = false;
    panel.querySelector("[data-cal-cerrar]").focus();
  }

  function cerrar() {
    panel.hidden = true;
    raiz.querySelectorAll(".cal__cita--elegida").forEach(function (n) { n.classList.remove("cal__cita--elegida"); });
    if (origenFoco && document.body.contains(origenFoco)) { origenFoco.focus(); }
  }

  raiz.querySelector("[data-cal-anterior]").addEventListener("click", function () { fecha = datos.anterior; cargar(); });
  raiz.querySelector("[data-cal-siguiente]").addEventListener("click", function () { fecha = datos.siguiente; cargar(); });
  raiz.querySelector("[data-cal-hoy]").addEventListener("click", function () { fecha = ""; raiz.dataset.visto = ""; cargar(); });
  raiz.querySelector("[data-cal-cerrar]").addEventListener("click", cerrar);
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !panel.hidden) { cerrar(); } });
  if (verCanceladas) { verCanceladas.addEventListener("change", function () { if (datos) { dibujar(); } }); }
  if (selArea) { selArea.addEventListener("change", cargar); }
  if (selMedico) { selMedico.addEventListener("change", function () { if (selMedico.value && selArea) { selArea.value = "1"; } cargar(); }); }

  cargar();
}());
