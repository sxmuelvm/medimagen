/* Medimagen Cuenca · utilidad para pedir JSON al servidor (fetch con manejo de errores).
   Uso:
     Medimagen.http.json("/ruta", { parametros: { fecha: "2026-11-20" } })
       .then(function (r) { r.ok, r.estado, r.datos });
   - Siempre devuelve una promesa que se resuelve con { ok, estado, datos, error }; solo se rechaza si no hay red.
   - Los métodos que modifican datos envían el token CSRF (campo oculto "csrf_token" de la página).
   - Nunca guarda ni escribe URLs, claves ni datos fijos: todo viene de quien la llama. */
(function () {
  "use strict";

  var Medimagen = window.Medimagen = window.Medimagen || {};

  function consulta(parametros) {
    var partes = [];
    Object.keys(parametros || {}).forEach(function (clave) {
      var valor = parametros[clave];
      if (valor === undefined || valor === null || valor === "") { return; }
      partes.push(encodeURIComponent(clave) + "=" + encodeURIComponent(valor));
    });
    return partes.length ? "?" + partes.join("&") : "";
  }

  function tokenCsrf() {
    var campo = document.querySelector('input[name="csrf_token"]');
    return campo ? campo.value : "";
  }

  var MENSAJES = {
    400: "La solicitud no es válida.",
    401: "Tu sesión terminó. Vuelve a iniciar sesión.",
    403: "No tienes permiso para hacer esto.",
    404: "No se encontró lo que buscabas.",
    409: "Ese dato ya cambió. Actualiza la página e inténtalo de nuevo.",
    429: "Hiciste muchas solicitudes seguidas. Espera un momento.",
    500: "El servidor tuvo un problema. Inténtalo de nuevo en unos minutos."
  };

  function json(url, opciones) {
    opciones = opciones || {};
    var metodo = (opciones.metodo || "GET").toUpperCase();
    var cabeceras = { "Accept": "application/json" };
    var cuerpo;
    if (metodo !== "GET") {
      cabeceras["X-CSRFToken"] = tokenCsrf();
      if (opciones.datos) {
        cabeceras["Content-Type"] = "application/json";
        cuerpo = JSON.stringify(opciones.datos);
      }
    }
    var direccion = url + (metodo === "GET" ? consulta(opciones.parametros) : "");

    return fetch(direccion, { method: metodo, headers: cabeceras, body: cuerpo, credentials: "same-origin" })
      .then(function (respuesta) {
        return respuesta.json().catch(function () { return {}; }).then(function (datos) {
          var error = "";
          if (!respuesta.ok) { error = (datos && datos.error) || MENSAJES[respuesta.status] || "No se pudo completar la solicitud."; }
          return { ok: respuesta.ok, estado: respuesta.status, datos: datos || {}, error: error };
        });
      });
  }

  Medimagen.http = { json: json, consulta: consulta };
}());
