/* SIGEP – Fase 2 frontend: clientes. El backend aplica los permisos reales. */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  let request = null;
  let conectado = false;
  let lista = [];
  let solicitudActual = 0;
  let temporizadorBusqueda = null;
  let editandoId = null;
  let esAdmin = false;

  function mostrarAviso(texto, error = false) {
    const aviso = $("clientes-feedback");
    aviso.textContent = texto;
    aviso.className = `sigep-feedback ${error ? "sigep-feedback-error" : "sigep-feedback-ok"}`;
    aviso.hidden = !texto;
  }

  function mostrarErrorFormulario(texto) {
    const elemento = $("cliente-form-error");
    elemento.textContent = texto;
    elemento.hidden = !texto;
  }

  function celda(fila, valor, clase = "") {
    const td = document.createElement("td");
    td.textContent = valor == null || valor === "" ? "—" : String(valor);
    if (clase) td.className = clase;
    fila.appendChild(td);
    return td;
  }

  function accion(etiqueta, clase, callback) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = `sigep-action ${clase}`;
    b.textContent = etiqueta;
    b.addEventListener("click", callback);
    return b;
  }

  function dibujarFilas() {
    const tbody = $("clientes-tbody");
    tbody.replaceChildren();
    $("clientes-total").textContent = lista.length;
    $("clientes-activos").textContent = lista.filter(c => c.activo).length;
    $("clientes-inactivos").textContent = lista.filter(c => !c.activo).length;
    $("clientes-vacio").hidden = lista.length > 0;

    for (const cliente of lista) {
      const tr = document.createElement("tr");
      const nombre = celda(tr, [cliente.nombre, cliente.apellidos].filter(Boolean).join(" "));
      nombre.className = "sigep-cell-name";
      const contacto = document.createElement("td");
      const telefono = document.createElement("div");
      telefono.textContent = cliente.telefono || "Sin teléfono";
      const correo = document.createElement("small");
      correo.textContent = cliente.correo || "Sin correo";
      contacto.append(telefono, correo);
      tr.appendChild(contacto);
      celda(tr, cliente.direccion);
      const columnaCuenta = document.createElement("td");
      if (cliente.cuenta) {
        const usuario = document.createElement("div");
        usuario.textContent = cliente.cuenta.username;
        const rol = document.createElement("small");
        rol.textContent = `Rol: ${cliente.cuenta.rol_nombre || cliente.cuenta.rol_codigo || "Sin rol"}`;
        columnaCuenta.append(usuario, rol);
      } else {
        columnaCuenta.textContent = cliente.usuario != null ? "Vinculada" : "Mostrador";
      }
      tr.appendChild(columnaCuenta);
      const estado = document.createElement("td");
      const insignia = document.createElement("span");
      insignia.className = `sigep-status ${cliente.activo ? "sigep-status-on" : "sigep-status-off"}`;
      insignia.textContent = cliente.activo ? "Activo" : "Inactivo";
      estado.appendChild(insignia);
      tr.appendChild(estado);
      const botones = document.createElement("td");
      const grupo = document.createElement("div");
      grupo.className = "sigep-row-actions";
      grupo.appendChild(accion("Editar", "sigep-action-edit", () => abrirEditar(cliente)));
      grupo.appendChild(accion(cliente.activo ? "Desactivar" : "Activar", "sigep-action-toggle", () => cambiarEstado(cliente)));
      if (esAdmin && cliente.usuario != null) {
        grupo.appendChild(accion("Cambiar rol", "sigep-action-edit", () => window.SIGEPUsuarios?.abrirEditarId(cliente.usuario)));
      }
      botones.appendChild(grupo);
      tr.appendChild(botones);
      tbody.appendChild(tr);
    }
  }

  async function cargar() {
    if (!conectado || !request) return;
    const num = ++solicitudActual;
    const buscar = $("clientes-buscar").value.trim();
    const activo = $("clientes-estado-filtro").value;
    const params = new URLSearchParams();
    if (buscar) params.set("buscar", buscar);
    if (activo) params.set("activo", activo);
    $("clientes-refrescar").disabled = true;
    $("clientes-vacio").hidden = true;
    mostrarAviso("Consultando clientes...");
    try {
      const payload = await request(`/clientes/${params.size ? `?${params}` : ""}`);
      if (num !== solicitudActual || !conectado) return;
      lista = Array.isArray(payload) ? payload : (Array.isArray(payload?.results) ? payload.results : []);
      dibujarFilas();
      mostrarAviso("");
    } catch (error) {
      if (num !== solicitudActual || !conectado) return;
      lista = [];
      dibujarFilas();
      mostrarAviso(`No fue posible cargar los clientes: ${error.message}`, true);
    } finally {
      if (num === solicitudActual) $("clientes-refrescar").disabled = false;
    }
  }

  function abrirNuevo() {
    editandoId = null;
    $("cliente-form").reset();
    $("cliente-dialog-title").textContent = "Registrar nuevo cliente";
    $("cliente-guardar").textContent = "Guardar cliente";
    mostrarErrorFormulario("");
    $("cliente-dialog").showModal();
    $("cliente-nombre").focus();
  }

  function abrirEditar(cliente) {
    editandoId = cliente.id;
    for (const campo of ["nombre", "apellidos", "telefono", "correo", "direccion", "observaciones"]) {
      $("cliente-" + campo).value = cliente[campo] || "";
    }
    $("cliente-dialog-title").textContent = `Editar cliente #${cliente.id}`;
    $("cliente-guardar").textContent = "Guardar cambios";
    mostrarErrorFormulario("");
    $("cliente-dialog").showModal();
  }

  async function guardar(e) {
    e.preventDefault();
    if (!conectado || !request) return;
    const formulario = $("cliente-form");
    if (!formulario.reportValidity()) return;
    const datos = {};
    for (const campo of ["nombre", "apellidos", "telefono", "correo", "direccion", "observaciones"]) {
      datos[campo] = $("cliente-" + campo).value.trim();
    }
    if (!datos.nombre || !datos.apellidos) {
      return mostrarErrorFormulario("El nombre y los apellidos son obligatorios.");
    }
    const boton = $("cliente-guardar");
    boton.disabled = true;
    mostrarErrorFormulario("");
    try {
      if (editandoId == null) {
        await request("/clientes/", "POST", datos);
      } else {
        await request(`/clientes/${editandoId}/`, "PATCH", datos);
      }
      if (!conectado) return;
      const texto = editandoId == null ? "Cliente registrado correctamente." : "Datos del cliente actualizados.";
      $("cliente-dialog").close();
      await cargar();
      mostrarAviso(texto);
    } catch (error) {
      mostrarErrorFormulario(error.message);
    } finally {
      boton.disabled = false;
    }
  }

  async function cambiarEstado(cliente) {
    const nuevo = !cliente.activo;
    if (!confirm(`¿Deseas ${nuevo ? "activar" : "desactivar"} a ${cliente.nombre} ${cliente.apellidos}?`)) return;
    try {
      await request(`/clientes/${cliente.id}/estado/`, "PATCH", { activo: nuevo });
      if (!conectado) return;
      await cargar();
      mostrarAviso(`Cliente ${nuevo ? "activado" : "desactivado"} correctamente.`);
    } catch (error) {
      mostrarAviso(`No se pudo cambiar el estado: ${error.message}`, true);
    }
  }

  function iniciar({ usuario, request: fetchAutorizado }) {
    detener();
    request = fetchAutorizado;
    conectado = true;
    esAdmin = usuario.rol?.codigo === "ADMIN" || usuario.is_superuser === true;
    $("clientes-buscar").value = "";
    $("clientes-estado-filtro").value = "";
    $("clientes-usuario").textContent = `${usuario.first_name || usuario.username} · ${usuario.rol?.nombre || "Personal"}`;
    cargar();
  }

  function detener() {
    conectado = false;
    esAdmin = false;
    solicitudActual++;
    request = null;
    lista = [];
    clearTimeout(temporizadorBusqueda);
    if ($("cliente-dialog").open) $("cliente-dialog").close();
  }

  $("clientes-nuevo").addEventListener("click", abrirNuevo);
  $("clientes-refrescar").addEventListener("click", cargar);
  $("cliente-form").addEventListener("submit", guardar);
  $("cliente-cancelar").addEventListener("click", () => $("cliente-dialog").close());
  $("cliente-cerrar").addEventListener("click", () => $("cliente-dialog").close());
  $("clientes-estado-filtro").addEventListener("change", cargar);
  $("clientes-buscar").addEventListener("input", () => {
    clearTimeout(temporizadorBusqueda);
    temporizadorBusqueda = setTimeout(cargar, 300);
  });

  window.SIGEPClientes = { iniciar, detener, actualizar: cargar };
})();
