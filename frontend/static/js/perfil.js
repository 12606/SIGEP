/* Mi perfil: datos propios, sin acceso a roles, estados ni contraseñas. */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  let usuario = null;
  let request = null;
  let alActualizar = null;
  let activo = false;
  let version = 0;

  function aviso(texto, error = false) {
    const nodo = $("perfil-feedback");
    nodo.textContent = texto;
    nodo.hidden = !texto;
    nodo.className = `sigep-feedback ${error ? "sigep-feedback-error" : "sigep-feedback-ok"}`;
  }

  function esCliente() {
    return usuario?.rol?.codigo === "CLIENTE" && usuario?.is_superuser !== true;
  }

  async function mostrar() {
    if (!activo || !request) return;
    const id = ++version;
    aviso("Consultando tu información...");
    $("perfil-guardar").disabled = true;
    const cliente = esCliente();
    $("perfil-direccion-contenedor").hidden = !cliente;
    try {
      const data = await request(cliente ? "/clientes/me/" : "/usuarios/me/");
      if (!activo || id !== version) return;
      $("perfil-nombre").value = cliente ? data.nombre : data.first_name;
      $("perfil-apellidos").value = cliente ? data.apellidos : data.last_name;
      $("perfil-correo").value = data.correo ?? data.email ?? "";
      $("perfil-telefono").value = data.telefono || "";
      $("perfil-direccion").value = cliente ? data.direccion || "" : "";
      $("perfil-usuario").textContent = usuario.username;
      $("perfil-rol").textContent = usuario.rol?.nombre || "Sin rol";
      aviso("");
      $("perfil-guardar").disabled = false;
    } catch (err) {
      if (activo && id === version) aviso(err.message, true);
    }
  }

  async function guardar(event) {
    event.preventDefault();
    if (!activo || !request) return;
    if (!$("perfil-form").reportValidity()) return;
    const cliente = esCliente();
    const nombre = $("perfil-nombre").value.trim();
    const apellidos = $("perfil-apellidos").value.trim();
    const correo = $("perfil-correo").value.trim();
    const telefono = $("perfil-telefono").value.trim();
    if (!nombre || !apellidos || !correo) return aviso("Completa nombre, apellidos y correo.", true);
    const digitos = telefono.replace(/\D/g, "");
    if (telefono && (digitos.length < 10 || digitos.length > 15)) return aviso("El teléfono debe tener entre 10 y 15 dígitos.", true);
    const payload = cliente
      ? { nombre, apellidos, correo, telefono, direccion: $("perfil-direccion").value.trim() }
      : { first_name: nombre, last_name: apellidos, email: correo, telefono };
    const boton = $("perfil-guardar");
    boton.disabled = true;
    try {
      const data = await request(cliente ? "/clientes/me/" : "/usuarios/me/", "PATCH", payload);
      if (!activo) return;
      const cambios = cliente
        ? { first_name: data.nombre, last_name: data.apellidos, email: data.correo, telefono: data.telefono }
        : { first_name: data.first_name, last_name: data.last_name, email: data.email, telefono: data.telefono };
      Object.assign(usuario, cambios);
      alActualizar?.(cambios);
      aviso("Tus datos fueron actualizados correctamente.");
    } catch (err) {
      aviso(err.message, true);
    } finally {
      boton.disabled = false;
    }
  }

  function iniciar({ usuario: perfil, request: solicitar, alActualizar: notificar }) {
    detener();
    usuario = perfil;
    request = solicitar;
    alActualizar = notificar;
    activo = true;
  }

  function detener() {
    activo = false;
    version++;
    usuario = null;
    request = null;
    alActualizar = null;
    aviso("");
    $("perfil-form").reset();
  }

  $("perfil-form").addEventListener("submit", guardar);
  window.SIGEPPerfil = { iniciar, mostrar, detener };
})();
