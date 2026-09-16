/*
 * Lógica del acta de visita en un solo flujo (sin recargar la página):
 * buscar PDS -> elegir tipo de visita y gestor -> iniciar (GPS) ->
 * responder preguntas una por una -> subir evidencia -> cerrar acta.
 */
const Acta = (() => {
  const TIPOS_VISITA = ["Prospección", "Seguimiento", "Oficina"];

  // Secciones que, solo para un cliente ya vinculado (visita de Seguimiento),
  // se pueden omitir porque casi no cambian. El resto siempre se responde
  // completo, y en Prospección/Oficina no hay opción de omitir.
  const SECCIONES_OMITIBLES_SEGUIMIENTO = new Set(["1", "2"]);

  // Secciones que, en una visita de Seguimiento, solo aplican si se
  // solicitó aumento de cupo (pregunta P048). En Prospección siempre
  // aplican (no hay corresponsalía previa que renovar). Esto no es una
  // elección del gestor (como el omitir arriba): se salta automático
  // según la respuesta.
  const SECCIONES_CONDICIONADAS_A_CUPO = new Set(["4", "8"]);
  const PREGUNTA_AUMENTO_CUPO = "P048";

  // Pregunta que usa el buscador de códigos CIIU (catálogo oficial DIAN,
  // Resolución 000114 de 2020) en vez de texto libre.
  const PREGUNTA_CIIU = "P024";
  let CIIU_DATA = [];

  // -------------------------------------------------------------- sesión
  // Cada gestor entra con usuario+clave (se la asigna quien administra el
  // backend, el gestor no la puede cambiar). El token queda en este
  // celular hasta que venza (lo decide el servidor, SESION_DIAS) o hasta
  // que el gestor cierre sesión a mano.
  const CLAVE_TOKEN = "acta_token";
  const CLAVE_GESTOR = "acta_gestor";

  function guardarSesion(token, nombre) {
    try {
      localStorage.setItem(CLAVE_TOKEN, token);
      localStorage.setItem(CLAVE_GESTOR, nombre);
    } catch (err) { /* almacenamiento no disponible, la sesión no persiste */ }
  }

  function sesionGuardada() {
    try {
      return { token: localStorage.getItem(CLAVE_TOKEN), gestor: localStorage.getItem(CLAVE_GESTOR) };
    } catch (err) {
      return { token: null, gestor: null };
    }
  }

  function borrarSesion() {
    try {
      localStorage.removeItem(CLAVE_TOKEN);
      localStorage.removeItem(CLAVE_GESTOR);
    } catch (err) { /* nada que borrar */ }
  }

  function encabezadosAuth() {
    const { token } = sesionGuardada();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  // Si el servidor responde 401 (sesión vencida o inválida), se cierra
  // la sesión local y se manda al gestor de vuelta al login.
  function esNoAutorizado(resp) {
    if (resp.status === 401) {
      borrarSesion();
      state.gestor = null;
      mostrarMensaje("login-mensaje", "Tu sesión venció. Vuelve a ingresar tu usuario y clave.");
      mostrarPantalla("login");
      return true;
    }
    return false;
  }

  function normalizar(s) {
    return (s || "")
      .toString()
      .toLowerCase()
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "");
  }

  async function cargarCiiu() {
    try {
      const resp = await fetch("/static/data/ciiu.json");
      CIIU_DATA = await resp.json();
    } catch (err) {
      CIIU_DATA = [];
    }
  }

  const SECCION_TITULOS = {
    "1": "Información del cliente",
    "2": "Información del negocio",
    "3": "Infraestructura y atención del corresponsal",
    "4": "Dinámica de ingresos",
    "8": "Concepto y cierre de la visita",
    "OF": "Visita de oficina",
  };

  // Campos de la sección 4 que se calculan solos a partir de otras
  // respuestas, en vez de escribirse a mano.
  const CALCULOS = {
    P072: () => numerica("P069") - numerica("P070"), // Utilidad bruta = Ventas - Costos de ventas
    P073: () => numerica("P072") - numerica("P071"), // Utilidad neta = Utilidad bruta - Gastos operacionales
    P086: () => // TOTAL ACTIVOS
      ["P076", "P077", "P078", "P079", "P080", "P082", "P084"].reduce((s, id) => s + numerica(id), 0),
    P089: () => numerica("P087") + numerica("P088"), // TOTAL PASIVO
  };

  // ¿Aplica esta sección tal como está la visita ahora mismo? (independiente
  // de si el gestor decidió omitirla en el "portón" de actualizar/omitir).
  function seccionActiva(seccion) {
    if (SECCIONES_CONDICIONADAS_A_CUPO.has(seccion) && state.tipoVisita === "Seguimiento") {
      const r = state.respuestas[PREGUNTA_AUMENTO_CUPO];
      return !!r && r.respuesta === "Si";
    }
    return true;
  }

  // ¿Debe mostrarse esta pregunta puntual, dado su "DependeDe"
  // (formato "ID_Pregunta=Valor1|Valor2")?
  function dependenciaCumplida(p) {
    if (!p.depende_de) return true;
    const [idDep, valoresStr] = p.depende_de.split("=");
    const valores = (valoresStr || "").split("|").map((v) => v.trim());
    const r = state.respuestas[(idDep || "").trim()];
    return !!r && valores.includes((r.respuesta || "").trim());
  }

  // Combina todo lo anterior: ¿esta pregunta se debe presentar ahora mismo?
  function preguntaActiva(p) {
    if (!seccionActiva(p.seccion)) return false;
    if (state.seccionesOmitidas.has(p.seccion)) return false;
    if (!dependenciaCumplida(p)) return false;
    return true;
  }

  function numerica(idPregunta) {
    const r = state.respuestas[idPregunta];
    if (!r || !r.respuesta) return 0;
    const limpio = String(r.respuesta).replace(/[^0-9-]/g, "");
    const val = parseInt(limpio, 10);
    return isNaN(val) ? 0 : val;
  }

  function formatoMoneda(valor) {
    return valor.toLocaleString("es-CO");
  }

  const state = {
    pds: null,
    pdsInfo: null,
    esProspecto: false,
    nombreProspecto: "",
    tipoVisita: null,
    gestor: null,
    idActa: null,
    distanciaPds: null,
    preguntas: [],
    indice: 0,
    respuestas: {}, // id_pregunta -> { respuesta, observacion, _esAnterior? }
    respuestasAnteriores: {}, // id_pregunta -> respuesta de la última visita completa a este PDS
    misPds: [], // PDS asignados al gestor logueado (para Seguimiento)
    fotos: [],
    seccionesOmitidas: new Set(),
    seccionesDecididas: new Set(),
    seccionEnGate: null,
    indicePrimeraDeSeccionGate: null,
    pantalla: "pds",
    subpaso: "tipo", // dentro de la pantalla "pds": tipo -> datos -> gestor
  };

  function el(id) { return document.getElementById(id); }

  function mostrarMensaje(idEl, texto) {
    const caja = el(idEl);
    caja.textContent = texto;
    caja.classList.remove("oculto");
  }

  function ocultarMensaje(idEl) {
    el(idEl).classList.add("oculto");
  }

  // -------------------------------------------------------------- pantallas

  function mostrarPantalla(nombre) {
    state.pantalla = nombre;
    document.querySelectorAll(".pantalla").forEach((s) => s.classList.add("oculto"));
    el(`pantalla-${nombre}`).classList.remove("oculto");

    const titulos = {
      login: "Acta de visita",
      pds: "Acta de visita",
      pregunta: "Acta de visita",
      "seccion-gate": "Acta de visita",
      evidencia: "Evidencia fotográfica",
      cierre: "Cerrar visita",
      exito: "Listo",
    };
    el("titulo-pantalla").textContent = titulos[nombre] || "Acta de visita";

    actualizarBotonAtras();

    if (state.tipoVisita && nombre !== "pds" && nombre !== "exito" && nombre !== "login") {
      el("badge-tipo").textContent = state.tipoVisita;
      el("badge-tipo").classList.remove("oculto");
    } else {
      el("badge-tipo").classList.add("oculto");
    }

    el("btn-logout").classList.toggle("oculto", nombre === "login");
  }

  function actualizarBotonAtras() {
    const ocultar =
      state.pantalla === "login" ||
      state.pantalla === "exito" ||
      (state.pantalla === "pds" && state.subpaso === "tipo");
    el("btn-atras").classList.toggle("oculto", ocultar);
  }

  // dentro de la pantalla "pds": tipo -> datos (pds, prospecto u oficina) -> gestor
  function mostrarSubpaso(paso) {
    state.subpaso = paso;
    if (paso === "tipo") renderPillsTipo();

    el("card-tipo").classList.toggle("oculto", paso !== "tipo");
    el("card-pds").classList.toggle("oculto", !(paso === "datos" && state.tipoVisita === "Seguimiento"));
    el("card-prospecto").classList.toggle("oculto", !(paso === "datos" && state.esProspecto));
    el("card-oficina").classList.toggle("oculto", !(paso === "datos" && state.tipoVisita === "Oficina"));
    el("card-tipo-gestor").classList.toggle("oculto", paso !== "gestor");

    actualizarBotonAtras();
  }

  function atras() {
    if (state.pantalla === "pds") {
      if (state.subpaso === "gestor") {
        mostrarSubpaso("datos");
      } else if (state.subpaso === "datos") {
        mostrarSubpaso("tipo");
      }
    } else if (state.pantalla === "seccion-gate") {
      retrocederDesde(state.indicePrimeraDeSeccionGate - 1);
    } else if (state.pantalla === "pregunta") {
      guardarRespuestaActual();
      retrocederDesde(state.indice - 1);
    } else if (state.pantalla === "evidencia") {
      retrocederDesde(state.preguntas.length - 1);
    } else if (state.pantalla === "cierre") {
      mostrarPantalla("evidencia");
    }
  }

  // -------------------------------------------------------------- navegación por secciones

  // Lista {pregunta, respuesta} con lo que ya se sabía de esta sección
  // (de la última visita completa a este PDS), para mostrarlo en el
  // portón de Actualizar/Omitir — así la decisión no es a ciegas.
  function resumenSeccion(seccion) {
    return state.preguntas
      .filter((p) => p.seccion === seccion)
      .map((p) => ({ pregunta: p.pregunta, respuesta: state.respuestasAnteriores[p.id_pregunta] }))
      .filter((r) => r.respuesta);
  }

  function seccionTieneDatosAnteriores(seccion) {
    return resumenSeccion(seccion).length > 0;
  }

  function seccionRequiereGate(seccion) {
    // Si nunca se ha respondido nada de esta sección para este PDS, no
    // hay nada que "actualizar u omitir" — se pregunta directo, como en
    // una Prospección.
    return (
      state.tipoVisita === "Seguimiento" &&
      SECCIONES_OMITIBLES_SEGUIMIENTO.has(seccion) &&
      !state.seccionesDecididas.has(seccion) &&
      seccionTieneDatosAnteriores(seccion)
    );
  }

  // Avanza desde `indice`, saltando preguntas que no aplican ahora mismo
  // (sección omitida, sección condicionada a cupo que no aplica, o
  // "DependeDe" no cumplida), y mostrando el portón de una sección
  // omitible que aún no se ha decidido.
  function presentarDesde(indice) {
    while (indice < state.preguntas.length && !preguntaActiva(state.preguntas[indice])) {
      indice++;
    }
    if (indice >= state.preguntas.length) {
      mostrarPantalla("evidencia");
      return;
    }
    state.indice = indice;
    const seccion = state.preguntas[indice].seccion;
    if (seccionRequiereGate(seccion)) {
      mostrarGateSeccion(seccion, indice);
    } else {
      mostrarPantalla("pregunta");
      renderPregunta();
    }
  }

  // Igual que presentarDesde pero hacia atrás (para el botón ←).
  function retrocederDesde(indice) {
    while (indice >= 0 && !preguntaActiva(state.preguntas[indice])) {
      indice--;
    }
    if (indice < 0) {
      mostrarPantalla("pds");
      mostrarSubpaso("gestor");
      return;
    }
    state.indice = indice;
    mostrarPantalla("pregunta");
    renderPregunta();
  }

  function mostrarGateSeccion(seccion, indicePrimeraPregunta) {
    state.seccionEnGate = seccion;
    state.indicePrimeraDeSeccionGate = indicePrimeraPregunta;
    el("gate-titulo").textContent = SECCION_TITULOS[seccion] || `Sección ${seccion}`;

    const cont = el("gate-resumen");
    cont.innerHTML = resumenSeccion(seccion)
      .map((r) => `<div class="gate-item"><span>${r.pregunta}</span><strong>${r.respuesta}</strong></div>`)
      .join("");

    mostrarPantalla("seccion-gate");
  }

  function elegirActualizarSeccion() {
    state.seccionesDecididas.add(state.seccionEnGate);
    presentarDesde(state.indice);
  }

  function elegirOmitirSeccion() {
    state.seccionesDecididas.add(state.seccionEnGate);
    state.seccionesOmitidas.add(state.seccionEnGate);
    presentarDesde(state.indice);
  }

  // -------------------------------------------------------------- paso 1: tipo -> datos

  function renderPillsTipo() {
    const cont = el("pills-tipo-inicial");
    cont.innerHTML = "";
    TIPOS_VISITA.forEach((tipo) => {
      const pill = document.createElement("div");
      pill.className = "pill" + (state.tipoVisita === tipo ? " activa" : "");
      pill.textContent = tipo;
      pill.onclick = () => elegirTipo(tipo);
      cont.appendChild(pill);
    });
  }

  function elegirTipo(tipo) {
    state.tipoVisita = tipo;
    state.esProspecto = tipo === "Prospección";
    mostrarSubpaso("datos");
    if (tipo === "Seguimiento") cargarMisPds();
  }

  async function cargarMisPds() {
    state.misPds = [];
    if (!state.gestor) return;
    try {
      const resp = await fetch(`/gestores/${encodeURIComponent(state.gestor)}/pds`, {
        headers: encabezadosAuth(),
      });
      if (resp.ok) state.misPds = await resp.json();
    } catch (err) {
      state.misPds = [];
    }
  }

  // Lista filtrable de los PDS asignados al gestor (para no tener que
  // saber el código de memoria) — sigue existiendo la búsqueda directa
  // por código como respaldo.
  function renderMisPds(filtro) {
    const cont = el("mispds-resultados");
    if (!cont) return;
    const q = normalizar(filtro).trim();
    const lista = q.length
      ? state.misPds.filter(
          (p) => normalizar(p.pds).includes(q) || normalizar(p.establecimiento).includes(q)
        )
      : state.misPds;

    cont.innerHTML = "";
    if (!lista.length) {
      cont.classList.add("oculto");
      return;
    }
    lista.slice(0, 30).forEach((p) => {
      const fila = document.createElement("div");
      fila.className = "ciiu-item";
      fila.innerHTML = `<strong>${p.pds}</strong> ${p.establecimiento || "(sin nombre)"}<br/><span style="color:var(--texto-tenue);font-size:12px">${p.direccion || ""}</span>`;
      fila.onclick = () => {
        el("in-pds").value = p.pds;
        cont.classList.add("oculto");
        buscarPds();
      };
      cont.appendChild(fila);
    });
    cont.classList.remove("oculto");
  }

  async function buscarPds() {
    const codigo = el("in-pds").value.trim();
    ocultarMensaje("pds-mensaje");
    el("pds-resultado").classList.add("oculto");
    const listaEl = el("mispds-resultados");
    if (listaEl) listaEl.classList.add("oculto");

    if (!codigo) {
      mostrarMensaje("pds-mensaje", "Ingresa un código de PDS.");
      return;
    }

    state.pds = codigo;
    state.pdsInfo = null;

    try {
      const resp = await fetch(`/pds/${encodeURIComponent(codigo)}`);
      if (resp.status === 404) {
        mostrarMensaje(
          "pds-mensaje",
          "Este PDS no está en el portafolio. Revisa el código, o si es un cliente nuevo, pulsa ← y elige 'Prospección'."
        );
        return;
      } else if (!resp.ok) {
        mostrarMensaje("pds-mensaje", `Error ${resp.status} consultando el PDS.`);
        return;
      }

      const datos = await resp.json();
      state.pdsInfo = datos;
      el("pds-resultado").innerHTML = `
        <strong>${datos.establecimiento || "(sin nombre)"}</strong><br/>
        ${datos.direccion || ""}<br/>
        Gestor asignado: ${datos.gestor || "—"}
      `;
      el("pds-resultado").classList.remove("oculto");

      irAGestor();
    } catch (err) {
      mostrarMensaje("pds-mensaje", "No se pudo conectar con el servidor.");
    }
  }

  function confirmarProspecto() {
    ocultarMensaje("prospecto-mensaje");
    const identificacion = el("in-identificacion").value.trim();
    if (!identificacion) {
      mostrarMensaje("prospecto-mensaje", "Ingresa el número de identificación del cliente.");
      return;
    }
    state.pds = identificacion;
    state.pdsInfo = null;
    state.nombreProspecto = el("in-nombre-prospecto").value.trim();
    irAGestor();
  }

  function confirmarOficina() {
    ocultarMensaje("oficina-mensaje");
    const nombre = el("in-nombre-oficina").value.trim();
    if (!nombre) {
      mostrarMensaje("oficina-mensaje", "Ingresa el nombre de la oficina.");
      return;
    }
    state.pds = nombre;
    state.pdsInfo = null;
    irAGestor();
  }

  function irAGestor() {
    mostrarSubpaso("gestor");
    el("gestor-actual").textContent = state.gestor || "—";
  }

  function obtenerGps() {
    return new Promise((resolve) => {
      if (!navigator.geolocation) {
        resolve({ latitud: null, longitud: null, precision_gps: null });
        return;
      }
      navigator.geolocation.getCurrentPosition(
        (pos) => resolve({
          latitud: pos.coords.latitude,
          longitud: pos.coords.longitude,
          precision_gps: pos.coords.accuracy,
        }),
        () => resolve({ latitud: null, longitud: null, precision_gps: null }),
        { enableHighAccuracy: true, timeout: 10000 }
      );
    });
  }

  async function iniciarVisita() {
    ocultarMensaje("gestor-mensaje");
    if (!state.gestor) {
      mostrarMensaje("gestor-mensaje", "Tu sesión no es válida, vuelve a ingresar.");
      cerrarSesion();
      return;
    }

    const boton = event.target;
    boton.textContent = "Obteniendo ubicación...";
    boton.disabled = true;

    const gps = await obtenerGps();

    try {
      const resp = await fetch("/visitas/iniciar", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...encabezadosAuth() },
        body: JSON.stringify({
          pds: state.pds,
          gestor: state.gestor,
          tipo_visita: state.tipoVisita,
          ...gps,
        }),
      });
      if (esNoAutorizado(resp)) return;
      if (!resp.ok) throw new Error(`Error ${resp.status} iniciando la visita.`);
      const datos = await resp.json();
      state.idActa = datos.id_acta;
      state.distanciaPds = datos.distancia_pds;

      await cargarPreguntas();
    } catch (err) {
      mostrarMensaje("gestor-mensaje", err.message);
    } finally {
      boton.textContent = "Iniciar visita (captura GPS)";
      boton.disabled = false;
    }
  }

  // -------------------------------------------------------------- paso 2: preguntas

  async function cargarPreguntas() {
    const resp = await fetch(`/preguntas?tipo_visita=${encodeURIComponent(state.tipoVisita)}`);
    state.preguntas = await resp.json();
    state.indice = 0;
    state.seccionesOmitidas = new Set();
    state.seccionesDecididas = new Set();
    state.respuestasAnteriores = {};

    // En Seguimiento, trae lo que se respondió en la última visita completa
    // a este PDS, para no arrancar en blanco sin saber qué datos ya tiene.
    if (state.tipoVisita === "Seguimiento") {
      try {
        const respAnt = await fetch(`/pds/${encodeURIComponent(state.pds)}/ultimas-respuestas`, {
          headers: encabezadosAuth(),
        });
        if (esNoAutorizado(respAnt)) return;
        if (respAnt.ok) state.respuestasAnteriores = await respAnt.json();
      } catch (err) {
        state.respuestasAnteriores = {};
      }
    }

    if (state.distanciaPds !== null && state.distanciaPds !== undefined) {
      el("gps-banner").textContent = `Ubicación confirmada — ${Math.round(state.distanciaPds)} m del punto registrado`;
    } else {
      el("gps-banner").textContent = "Ubicación GPS capturada";
    }

    presentarDesde(0);
  }

  // Buscador de código CIIU: el gestor escribe (código o parte del nombre de
  // la actividad) y elige de una lista; al elegir se guarda "CÓDIGO -
  // Descripción" como respuesta (código y nombre en un solo campo).
  function renderBuscadorCiiu(p, guardado) {
    const wrap = document.createElement("div");
    wrap.className = "ciiu-buscador";

    const input = document.createElement("input");
    input.type = "text";
    input.placeholder = "Escribe el código o la actividad (ej: panadería, 4711...)";
    input.value = guardado.respuesta || "";
    input.autocomplete = "off";

    const resultados = document.createElement("div");
    resultados.className = "ciiu-resultados oculto";

    function elegir(item) {
      guardado.respuesta = `${item.codigo} - ${item.descripcion}`;
      delete guardado._esAnterior;
      state.respuestas[p.id_pregunta] = guardado;
      input.value = guardado.respuesta;
      resultados.classList.add("oculto");
      resultados.innerHTML = "";
    }

    function buscar() {
      const q = normalizar(input.value).trim();
      guardado.respuesta = input.value;
      delete guardado._esAnterior;
      state.respuestas[p.id_pregunta] = guardado;

      resultados.innerHTML = "";
      if (q.length < 2 || !CIIU_DATA.length) {
        resultados.classList.add("oculto");
        return;
      }
      const coincidencias = CIIU_DATA
        .filter((item) => normalizar(item.codigo).includes(q) || normalizar(item.descripcion).includes(q))
        .slice(0, 8);

      if (!coincidencias.length) {
        resultados.classList.add("oculto");
        return;
      }
      coincidencias.forEach((item) => {
        const fila = document.createElement("div");
        fila.className = "ciiu-item";
        fila.innerHTML = `<strong>${item.codigo}</strong> ${item.descripcion}`;
        fila.onclick = () => elegir(item);
        resultados.appendChild(fila);
      });
      resultados.classList.remove("oculto");
    }

    input.oninput = buscar;
    input.onfocus = buscar;

    wrap.appendChild(input);
    wrap.appendChild(resultados);
    return wrap;
  }

  function renderPregunta() {
    const p = state.preguntas[state.indice];
    ocultarMensaje("preg-mensaje");

    el("prog-texto").textContent = `PREGUNTA ${state.indice + 1} DE ${state.preguntas.length}`;
    el("prog-fill").style.width = `${((state.indice + 1) / state.preguntas.length) * 100}%`;

    el("preg-seccion").textContent = SECCION_TITULOS[p.seccion] || `Sección ${p.seccion}`;
    el("preg-texto").textContent = p.pregunta;

    // Si esta pregunta no se había tocado en esta visita y hay un dato de
    // la última visita completa a este PDS, se precarga (y se cuenta como
    // respondida) en vez de arrancar en blanco.
    let guardado = state.respuestas[p.id_pregunta];
    if (!guardado) {
      // Los campos calculados siempre se recalculan solos, no tiene
      // sentido precargarles un valor viejo.
      const anterior = CALCULOS[p.id_pregunta] ? null : state.respuestasAnteriores[p.id_pregunta];
      guardado = anterior
        ? { respuesta: anterior, observacion: "", _esAnterior: true }
        : { respuesta: "", observacion: "" };
      state.respuestas[p.id_pregunta] = guardado;
    }
    const eraAnterior = !!guardado._esAnterior;
    el("preg-observacion").value = guardado.observacion || "";

    const cont = el("preg-respuesta");
    cont.innerHTML = "";

    if (eraAnterior) {
      const nota = document.createElement("div");
      nota.className = "dato-anterior";
      nota.textContent = "↺ Dato de tu visita anterior a este PDS — confírmalo o corrígelo";
      cont.appendChild(nota);
    }

    if (CALCULOS[p.id_pregunta]) {
      const valor = CALCULOS[p.id_pregunta]();
      guardado.respuesta = String(valor);
      state.respuestas[p.id_pregunta] = guardado;

      const calculado = document.createElement("div");
      calculado.className = "calculado";
      calculado.innerHTML = `$ ${formatoMoneda(valor)} <span>(calculado automáticamente)</span>`;
      cont.appendChild(calculado);
    } else if (p.id_pregunta === PREGUNTA_CIIU) {
      cont.appendChild(renderBuscadorCiiu(p, guardado));
    } else if (p.tiporespuesta === "calendario" || (p.tiporespuesta === "Texto" && /fecha/i.test(p.pregunta))) {
      // Preguntas de fecha -> calendario nativo, para que no escriban
      // formatos libres ("ayer", "15 de julio", etc.)
      const input = document.createElement("input");
      input.type = "date";
      input.value = guardado.respuesta || "";
      input.oninput = () => {
        guardado.respuesta = input.value;
        delete guardado._esAnterior;
        state.respuestas[p.id_pregunta] = guardado;
      };
      cont.appendChild(input);
    } else if (p.tiporespuesta === "Si/No") {
      const fila = document.createElement("div");
      fila.className = "pillRow";
      ["Si", "No"].forEach((valor) => {
        const pill = document.createElement("div");
        pill.className = "pill" + (guardado.respuesta === valor ? " activa" : "");
        pill.textContent = valor === "Si" ? "Sí" : "No";
        pill.onclick = () => {
          guardado.respuesta = valor;
          delete guardado._esAnterior;
          state.respuestas[p.id_pregunta] = guardado;
          renderPregunta();
        };
        fila.appendChild(pill);
      });
      cont.appendChild(fila);
    } else if (p.tiporespuesta === "Texto largo") {
      const area = document.createElement("textarea");
      area.value = guardado.respuesta || "";
      area.placeholder = "Escribe la respuesta...";
      area.oninput = () => {
        guardado.respuesta = area.value;
        delete guardado._esAnterior;
        state.respuestas[p.id_pregunta] = guardado;
      };
      cont.appendChild(area);
    } else if (p.tiporespuesta === "Opcion multiple" || p.tiporespuesta === "Seleccion multiple") {
      const opciones = (p.opciones || "").split("|").map((o) => o.trim()).filter(Boolean);
      const multiple = p.tiporespuesta === "Seleccion multiple";

      // Si había un detalle de "Otro" guardado ("Otro: lo que sea"), lo
      // separamos: la pastilla queda marcada como "Otro" y el texto va
      // en el campo aparte.
      const partesGuardadas = (guardado.respuesta || "").split(",").map((s) => s.trim()).filter(Boolean);
      const parteOtro = partesGuardadas.find((s) => /^Otro:/i.test(s));
      const detalleInicial = parteOtro ? parteOtro.replace(/^Otro:\s*/i, "") : "";
      const seleccionadas = new Set(
        partesGuardadas.map((s) => (/^Otro:/i.test(s) ? "Otro" : s))
      );

      function guardarSeleccion(detalleOtro) {
        const partes = Array.from(seleccionadas).map((op) =>
          op === "Otro" ? `Otro: ${(detalleOtro || "").trim()}`.trim() : op
        );
        guardado.respuesta = partes.join(", ");
        delete guardado._esAnterior;
        state.respuestas[p.id_pregunta] = guardado;
      }

      const fila = document.createElement("div");
      fila.className = "pillRow";
      opciones.forEach((op) => {
        const pill = document.createElement("div");
        pill.className = "pill" + (seleccionadas.has(op) ? " activa" : "");
        pill.textContent = op;
        pill.onclick = () => {
          if (multiple) {
            if (seleccionadas.has(op)) seleccionadas.delete(op); else seleccionadas.add(op);
          } else {
            seleccionadas.clear();
            seleccionadas.add(op);
          }
          guardarSeleccion(detalleInicial);
          renderPregunta();
        };
        fila.appendChild(pill);
      });
      cont.appendChild(fila);

      guardarSeleccion(detalleInicial);

      if (seleccionadas.has("Otro")) {
        const inputOtro = document.createElement("input");
        inputOtro.type = "text";
        inputOtro.placeholder = "Especifica cuál...";
        inputOtro.style.marginTop = "10px";
        inputOtro.value = detalleInicial;
        inputOtro.oninput = () => guardarSeleccion(inputOtro.value);
        cont.appendChild(inputOtro);
      }
    } else {
      // "Texto" y cualquier otro tipo no contemplado -> campo simple
      const input = document.createElement("input");
      input.type = "text";
      input.value = guardado.respuesta || "";
      input.placeholder = "Escribe la respuesta...";
      input.oninput = () => {
        guardado.respuesta = input.value;
        delete guardado._esAnterior;
        state.respuestas[p.id_pregunta] = guardado;
      };
      cont.appendChild(input);
    }
  }

  function guardarRespuestaActual() {
    const p = state.preguntas[state.indice];
    if (!p) return;
    const guardado = state.respuestas[p.id_pregunta] || { respuesta: "", observacion: "" };
    guardado.observacion = el("preg-observacion").value;
    state.respuestas[p.id_pregunta] = guardado;
  }

  function siguientePregunta() {
    const p = state.preguntas[state.indice];
    guardarRespuestaActual();

    const respuesta = (state.respuestas[p.id_pregunta] || {}).respuesta;
    if (p.obligatoria === "Si" && !respuesta) {
      mostrarMensaje("preg-mensaje", "Esta pregunta es obligatoria.");
      return;
    }

    presentarDesde(state.indice + 1);
  }

  // -------------------------------------------------------------- paso 3: evidencia

  async function subirFoto() {
    const archivo = el("in-foto").files[0];
    ocultarMensaje("fotos-mensaje");

    if (!archivo) {
      mostrarMensaje("fotos-mensaje", "Elige o toma una foto primero.");
      return;
    }

    const gps = await obtenerGps();
    const datos = new FormData();
    datos.append("id_acta", state.idActa);
    datos.append("pds", state.pds);
    datos.append("tipo", el("in-tipo-foto").value);
    if (gps.latitud !== null) datos.append("latitud", gps.latitud);
    if (gps.longitud !== null) datos.append("longitud", gps.longitud);
    datos.append("archivo", archivo);

    try {
      const resp = await fetch("/evidencias", { method: "POST", headers: encabezadosAuth(), body: datos });
      if (esNoAutorizado(resp)) return;
      if (!resp.ok) throw new Error(`Error ${resp.status} subiendo la foto.`);
      const fila = await resp.json();
      state.fotos.push(fila);

      const img = document.createElement("img");
      img.className = "thumb";
      img.src = fila.url_publica;
      el("fotos-subidas").appendChild(img);

      el("in-foto").value = "";
    } catch (err) {
      mostrarMensaje("fotos-mensaje", err.message);
    }
  }

  function irACierre() {
    mostrarPantalla("cierre");
  }

  // -------------------------------------------------------------- paso 4: cierre

  async function guardarTodo() {
    ocultarMensaje("cierre-mensaje");
    const boton = event.target;
    boton.disabled = true;
    boton.textContent = "Guardando...";

    try {
      const respuestas = Object.entries(state.respuestas).map(([id_pregunta, r]) => ({
        id_pregunta,
        respuesta: r.respuesta || null,
        observacion: r.observacion || null,
      }));

      const respGuardar = await fetch("/respuestas", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...encabezadosAuth() },
        body: JSON.stringify({ id_acta: state.idActa, respuestas }),
      });
      if (esNoAutorizado(respGuardar)) return;
      if (!respGuardar.ok) throw new Error(`Error ${respGuardar.status} guardando las respuestas.`);

      let observacionesFinales = el("in-observaciones-finales").value || "";
      if (state.esProspecto && state.nombreProspecto) {
        observacionesFinales = `Prospecto: ${state.nombreProspecto}. ${observacionesFinales}`.trim();
      }

      const respCerrar = await fetch(`/visitas/${state.idActa}/cerrar`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...encabezadosAuth() },
        body: JSON.stringify({ observaciones: observacionesFinales || null }),
      });
      if (esNoAutorizado(respCerrar)) return;
      if (!respCerrar.ok) throw new Error(`Error ${respCerrar.status} cerrando el acta.`);

      el("exito-detalle").innerHTML = `
        PDS <strong>${state.pds}</strong> — ${state.tipoVisita}<br/>
        Acta #${state.idActa} · ${respuestas.length} respuestas · ${state.fotos.length} fotos
      `;
      mostrarPantalla("exito");
    } catch (err) {
      mostrarMensaje("cierre-mensaje", err.message);
      boton.disabled = false;
      boton.textContent = "Guardar y cerrar acta";
    }
  }

  function nuevaVisita() {
    // Nota: state.gestor NO se limpia aquí a propósito — la sesión sigue
    // abierta entre una visita y otra, solo se resetean los datos propios
    // de la visita que se acaba de cerrar.
    state.pds = null;
    state.pdsInfo = null;
    state.esProspecto = false;
    state.nombreProspecto = "";
    state.tipoVisita = null;
    state.idActa = null;
    state.distanciaPds = null;
    state.preguntas = [];
    state.indice = 0;
    state.respuestas = {};
    state.respuestasAnteriores = {};
    state.fotos = [];
    state.seccionesOmitidas = new Set();
    state.seccionesDecididas = new Set();
    state.seccionEnGate = null;

    el("in-pds").value = "";
    el("in-identificacion").value = "";
    el("in-nombre-prospecto").value = "";
    el("in-nombre-oficina").value = "";
    el("pds-resultado").classList.add("oculto");
    el("fotos-subidas").innerHTML = "";
    el("in-observaciones-finales").value = "";
    ocultarMensaje("pds-mensaje");
    ocultarMensaje("prospecto-mensaje");
    ocultarMensaje("oficina-mensaje");
    ocultarMensaje("gestor-mensaje");

    mostrarPantalla("pds");
    mostrarSubpaso("tipo");
  }

  // -------------------------------------------------------------- login

  async function iniciarSesion() {
    ocultarMensaje("login-mensaje");
    const usuario = el("in-usuario").value.trim();
    const clave = el("in-clave").value;
    if (!usuario || !clave) {
      mostrarMensaje("login-mensaje", "Ingresa tu usuario y tu clave.");
      return;
    }

    const boton = event.target;
    boton.disabled = true;
    boton.textContent = "Ingresando...";

    try {
      const resp = await fetch("/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ usuario, clave }),
      });
      if (!resp.ok) {
        mostrarMensaje("login-mensaje", "Usuario o clave incorrectos.");
        return;
      }
      const datos = await resp.json();
      guardarSesion(datos.token, datos.gestor);
      state.gestor = datos.gestor;
      el("in-clave").value = "";
      mostrarPantalla("pds");
      mostrarSubpaso("tipo");
    } catch (err) {
      mostrarMensaje("login-mensaje", "No se pudo conectar con el servidor.");
    } finally {
      boton.disabled = false;
      boton.textContent = "Iniciar sesión";
    }
  }

  function cerrarSesion() {
    borrarSesion();
    state.gestor = null;
    el("in-usuario").value = "";
    el("in-clave").value = "";
    ocultarMensaje("login-mensaje");
    mostrarPantalla("login");
  }

  function init() {
    cargarCiiu();

    const inPds = el("in-pds");
    if (inPds) {
      inPds.oninput = () => renderMisPds(inPds.value);
      inPds.onfocus = () => renderMisPds(inPds.value);
    }

    const { token, gestor } = sesionGuardada();
    if (token && gestor) {
      state.gestor = gestor;
      mostrarPantalla("pds");
      mostrarSubpaso("tipo");
    } else {
      mostrarPantalla("login");
    }
  }

  return {
    init, iniciarSesion, cerrarSesion,
    elegirTipo, buscarPds, confirmarProspecto, confirmarOficina, iniciarVisita,
    siguientePregunta, atras, subirFoto, irACierre, guardarTodo, nuevaVisita,
    elegirActualizarSeccion, elegirOmitirSeccion,
  };
})();

document.addEventListener("DOMContentLoaded", Acta.init);
