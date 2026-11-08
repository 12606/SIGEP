/* SIGEP · Administración de usuarios y roles. Únicamente para ADMIN.
   El backend valida todos los permisos; ocultar botones NO es seguridad. */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  let request = null;
  let conectado = false;
  let yo = null;
  let usuarios = [];
  let roles = [];
  let seleccionado = null;
  let secuencia = 0;

  function aviso(texto, error = false) {
    const nodo = $("usuarios-feedback");
    nodo.textContent = texto;
    nodo.className = `sigep-feedback ${error ? "sigep-feedback-error" : "sigep-feedback-ok"}`;
    nodo.hidden = !texto;
  }

  function errorModal(texto) {
    const nodo = $("usuario-rol-error");
    nodo.textContent = texto;
    nodo.hidden = !texto;
  }

  function columna(fila, texto) {
    const nodo = document.createElement("td");
    nodo.textContent = texto == null || texto === "" ? "—" : String(texto);
    fila.appendChild(nodo);
    return nodo;
  }

  function boton(texto, fn, desactivado = false, titulo = "") {
    const nodo = document.createElement("button");
    nodo.type = "button";
    nodo.className = "sigep-action sigep-action-edit";
    nodo.textContent = texto;
    nodo.disabled = desactivado;
    if (titulo) nodo.title = titulo;
    nodo.addEventListener("click", fn);
    return nodo;
  }

  function dibujar() {
    const tbody = $("usuarios-tbody");
    tbody.replaceChildren();
    const buscar = $("usuarios-buscar").value.trim().toLocaleLowerCase("es");
    const estadoFiltro = $("usuarios-filtro").value;
    const filtrados = usuarios.filter(u => {
      if (estadoFiltro && String(u.is_active) !== estadoFiltro) return false;
      return [u.username, u.email, u.first_name, u.last_name]
        .some(v => (v || "").toLocaleLowerCase("es").includes(buscar));
    });
    $("usuarios-vacio").hidden = filtrados.length > 0;
    for (const u of filtrados) {
      const tr = document.createElement("tr");
      const n = columna(tr, u.username);
      n.className = "sigep-cell-name";
      if (u.first_name || u.last_name) {
        const detalle = document.createElement("small");
        detalle.textContent = [u.first_name, u.last_name].filter(Boolean).join(" ");
        n.appendChild(detalle);
      }
      columna(tr, u.email);
      columna(tr, u.rol?.nombre || "Sin rol");
      const estado = document.createElement("td");
      const insignia = document.createElement("span");
      insignia.className = `sigep-status ${u.is_active ? "sigep-status-on" : "sigep-status-off"}`;
      insignia.textContent = u.is_active ? "Activa" : "Inactiva";
      estado.appendChild(insignia);
      tr.appendChild(estado);
      const tdAcciones = document.createElement("td");
      const acciones = document.createElement("div");
      acciones.className = "sigep-row-actions";
      const protegido = u.is_superuser || u.id === yo?.id;
      acciones.appendChild(boton("Cambiar rol", () => editarRol(u), protegido,
        u.is_superuser ? "El rol del superusuario está protegido" : (u.id === yo?.id ? "No puedes cambiar tu propio rol" : "")));
      acciones.appendChild(boton(u.is_active ? "Desactivar" : "Activar", () => cambiarEstado(u),
        u.is_superuser || u.id === yo?.id,
        "No puedes desactivar al superusuario ni a tu propia cuenta"));
      tdAcciones.appendChild(acciones);
      tr.appendChild(tdAcciones);
      tbody.appendChild(tr);
    }
  }

  async function cargarDatos() {
    if (!conectado || !request) return;
    const num = ++secuencia;
    $("usuarios-refrescar").disabled = true;
    aviso("Consultando usuarios y roles...");
    try {
      const [lista, rolesApi] = await Promise.all([request("/usuarios/"), request("/roles/")]);
      if (!conectado || num !== secuencia) return;
      usuarios = Array.isArray(lista) ? lista : (lista?.results || []);
      roles = (Array.isArray(rolesApi) ? rolesApi : (rolesApi?.results || [])).filter(r => r.activo);
      dibujar();
      aviso("");
    } catch (e) {
      if (!conectado || num !== secuencia) return;
      usuarios = [];
      dibujar();
      aviso(`No fue posible consultar cuentas: ${e.message}`, true);
    } finally {
      if (num === secuencia) $("usuarios-refrescar").disabled = false;
    }
  }

  async function abrirEditarId(idUsuario) {
    if (!conectado) return;
    if (!usuarios.length || !roles.length) await cargarDatos();
    const usuario = usuarios.find(u => u.id === idUsuario);
    if (!usuario) return aviso("No se encontró la cuenta vinculada. Pulsa Actualizar.", true);
    editarRol(usuario);
  }

  function editarRol(usuario) {
    if (!conectado || usuario.is_superuser || usuario.id === yo?.id) return;
    seleccionado = usuario;
    $("usuario-rol-resumen").textContent = `${usuario.username} (${usuario.email}) · Rol actual: ${usuario.rol?.nombre || "Sin rol"}`;
    const select = $("usuario-rol-select");
    select.replaceChildren();
    for (const rol of roles) {
      const opcion = document.createElement("option");
      opcion.value = rol.codigo;
      opcion.textContent = `${rol.nombre} (${rol.codigo})`;
      select.appendChild(opcion);
    }
    select.value = usuario.rol?.codigo || "CLIENTE";
    errorModal("");
    $("usuario-rol-dialog").showModal();
    select.focus();
  }

  async function guardarRol(e) {
    e.preventDefault();
    if (!conectado || !request || !seleccionado) return;
    const rolNuevo = $("usuario-rol-select").value;
    if (!rolNuevo) return errorModal("Selecciona un rol.");
    if (rolNuevo === seleccionado.rol?.codigo) {
      $("usuario-rol-dialog").close();
      return;
    }
    if (!confirm(`¿Cambiar el rol de ${seleccionado.username} a ${rolNuevo}? Sus permisos cambiarán.`)) return;
    const botonGuardar = $("usuario-rol-guardar");
    botonGuardar.disabled = true;
    errorModal("");
    try {
      await request(`/usuarios/${seleccionado.id}/`, "PATCH", { rol_codigo: rolNuevo });
      $("usuario-rol-dialog").close();
      await cargarDatos();
      if (window.SIGEPClientes) await window.SIGEPClientes.actualizar();
      aviso("Rol actualizado. La cuenta deberá volver a iniciar sesión para actualizar su pantalla.");
    } catch (err) {
      errorModal(err.message);
    } finally {
      botonGuardar.disabled = false;
    }
  }

  async function cambiarEstado(u) {
    if (!conectado || u.is_superuser || u.id === yo?.id) return;
    const proximo = !u.is_active;
    if (!confirm(`¿Deseas ${proximo ? "activar" : "desactivar"} la cuenta ${u.username}?`)) return;
    try {
      await request(`/usuarios/${u.id}/estado/`, "PATCH", { activo: proximo });
      await cargarDatos();
      aviso(`La cuenta ${u.username} fue ${proximo ? "activada" : "desactivada"}.`);
    } catch (err) {
      aviso(err.message, true);
    }
  }

  function iniciar({usuario, request: peticionAutorizada}) {
    detener();
    yo = usuario;
    request = peticionAutorizada;
    conectado = true;
    $("usuarios-buscar").value = "";
    $("usuarios-filtro").value = "";
  }

  function detener() {
    conectado = false;
    request = null;
    yo = null;
    usuarios = [];
    roles = [];
    seleccionado = null;
    secuencia++;
    if ($("usuario-rol-dialog").open) $("usuario-rol-dialog").close();
  }

  $("usuarios-refrescar").addEventListener("click", cargarDatos);
  $("usuarios-buscar").addEventListener("input", dibujar);
  $("usuarios-filtro").addEventListener("change", dibujar);
  $("usuario-rol-form").addEventListener("submit", guardarRol);
  $("usuario-rol-cerrar").addEventListener("click", () => $("usuario-rol-dialog").close());
  $("usuario-rol-cancelar").addEventListener("click", () => $("usuario-rol-dialog").close());

  window.SIGEPUsuarios = { iniciar, detener, actualizar: cargarDatos, abrirEditarId };
})();
