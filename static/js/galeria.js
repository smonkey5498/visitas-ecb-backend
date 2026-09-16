async function buscarEvidencias() {
  const codigo = document.getElementById("pds").value.trim();
  const galeria = document.getElementById("galeria");
  const mensaje = document.getElementById("mensaje");

  galeria.innerHTML = "";
  mensaje.classList.add("oculto");

  if (!codigo) {
    mensaje.textContent = "Ingresa un código de PDS.";
    mensaje.classList.remove("oculto");
    return;
  }

  try {
    const resp = await fetch(`/pds/${encodeURIComponent(codigo)}/evidencias`);
    if (!resp.ok) {
      throw new Error(`Error ${resp.status} consultando las evidencias.`);
    }

    const evidencias = await resp.json();

    if (evidencias.length === 0) {
      mensaje.textContent = `El PDS ${codigo} todavía no tiene evidencias fotográficas guardadas.`;
      mensaje.classList.remove("oculto");
      return;
    }

    for (const ev of evidencias) {
      const tarjetaFoto = document.createElement("div");
      tarjetaFoto.className = "foto-card";

      const img = document.createElement("img");
      img.src = ev.url_publica;
      img.alt = ev.tipo || "Evidencia";
      img.loading = "lazy";

      const pie = document.createElement("div");
      pie.className = "foto-pie";
      pie.innerHTML = `
        <strong>${ev.tipo || "Sin tipo"}</strong><br/>
        Visita: ${ev.fecha_visita || "—"} (${ev.tipo_visita || "—"})<br/>
        Subida: ${ev.fecha ? new Date(ev.fecha).toLocaleString("es-CO") : "—"}
      `;

      tarjetaFoto.appendChild(img);
      tarjetaFoto.appendChild(pie);
      galeria.appendChild(tarjetaFoto);
    }
  } catch (err) {
    mensaje.textContent = err.message;
    mensaje.classList.remove("oculto");
  }
}
