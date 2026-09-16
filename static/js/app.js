async function consultarPds() {
  const codigo = document.getElementById("pds").value.trim();
  const resultado = document.getElementById("resultado");
  const errorBox = document.getElementById("error");

  resultado.classList.add("oculto");
  errorBox.classList.add("oculto");

  if (!codigo) {
    errorBox.textContent = "Ingresa un código de PDS.";
    errorBox.classList.remove("oculto");
    return;
  }

  try {
    const resp = await fetch(`/pds/${encodeURIComponent(codigo)}`);
    if (!resp.ok) {
      const detalle = await resp.json().catch(() => ({}));
      throw new Error(detalle.detail || `Error ${resp.status}`);
    }

    const datos = await resp.json();
    document.getElementById("r_pds").textContent = datos.pds ?? "";
    document.getElementById("r_titular").textContent = datos.titular ?? "";
    document.getElementById("r_establecimiento").textContent = datos.establecimiento ?? "";
    document.getElementById("r_direccion").textContent = datos.direccion ?? "";
    document.getElementById("r_telefono").textContent = datos.telefono ?? "";
    document.getElementById("r_correo").textContent = datos.correo ?? "";
    document.getElementById("r_gestor").textContent = datos.gestor ?? "";

    resultado.classList.remove("oculto");
  } catch (err) {
    errorBox.textContent = err.message;
    errorBox.classList.remove("oculto");
  }
}
