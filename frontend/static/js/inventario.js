/* SIGEP fase 5: inventario. Las autorizaciones se verifican en Django. */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const crear = (tag, clase = "", texto = "") => {
    const el = document.createElement(tag);
    if (clase) el.className = clase;
    el.textContent = texto;
    return el;
  };
  const monto = n => Number(n || 0).toLocaleString("es-MX", {style:"currency",currency:"MXN"});
  const numero = n => Number(n || 0).toLocaleString("es-MX", {maximumFractionDigits:3});
  const fecha = n => n ? new Date(n).toLocaleString("es-MX",{dateStyle:"short",timeStyle:"short"}) : "—";
  const tipos = {ENTRADA:"Entrada", SALIDA:"Salida", MERMA:"Merma"};
  let request = null, rol = null, ingredientes = [], movimientos = [], seq = 0, editId = null;
  const gestiona = () => rol === "ADMIN" || rol === "ALMACEN";
  const esAdmin = () => rol === "ADMIN";

  function aviso(id, texto, error = false) {
    const e = $(id);
    e.textContent = texto || "";
    e.hidden = !texto;
    e.className = "inventario-aviso " + (error ? "inventario-aviso-error" : "inventario-aviso-ok");
  }

  async function iniciar({ usuario, request: servicio }) {
    request = servicio;
    rol = usuario.is_superuser ? "ADMIN" : usuario.rol?.codigo;
    $("inventario-repostero-panel").hidden = rol !== "REPOSTERO";
    if (rol === "REPOSTERO") $("session-panel").classList.add("inventario-sesion-ancha");
    await actualizar();
  }

  async function actualizar() {
    if (!request) return;
    const actual = ++seq;
    const buscador = gestiona() ? $("inventario-buscar").value.trim() : "";
    const estado = gestiona() ? $("inventario-filtro-estado").value : "";
    const params = new URLSearchParams();
    if (buscador) params.set("buscar", buscador);
    if (estado) params.set("activo", estado);
    try {
      const respuesta = await request("/inventario/ingredientes/" + (params.size ? "?" + params : ""));
      if (actual !== seq) return;
      ingredientes = Array.isArray(respuesta) ? respuesta : (respuesta.results || []);
      if (gestiona()) {
        const r = await request("/inventario/movimientos/");
        if (actual !== seq) return;
        movimientos = Array.isArray(r) ? r : (r.results || []);
        pintarAdmin();
      } else if (rol === "REPOSTERO") pintarRepostero();
    } catch (error) {
      if (actual !== seq) return;
      aviso(gestiona() ? "inventario-aviso" : "inventario-repostero-aviso", error.message, true);
    }
  }

  function boton(nombre, accion, clase="sigep-action sigep-action-edit") {
    const b = crear("button", clase, nombre);
    b.type = "button"; b.addEventListener("click", accion);
    return b;
  }
  function td(tr, valor) {
    const c = crear("td", "", valor == null || valor === "" ? "—" : String(valor));
    tr.appendChild(c);return c;
  }
  function pintarAdmin() {
    $("inventario-total").textContent = ingredientes.length;
    $("inventario-alertas-total").textContent = ingredientes.filter(i => i.stock_bajo).length;
    $("inventario-inactivos").textContent = ingredientes.filter(i => !i.activo).length;
    const tbody = $("inventario-tabla");tbody.replaceChildren();
    for (const ing of ingredientes) {
      const tr = crear("tr");
      td(tr, ing.nombre);
      td(tr, numero(ing.stock_actual) + " " + ing.unidad_medida);
      td(tr, numero(ing.stock_minimo) + " " + ing.unidad_medida);
      td(tr, monto(ing.costo_unitario));
      const estado = td(tr, ing.activo ? (ing.stock_bajo ? "Stock bajo" : "Disponible") : "Inactivo");
      estado.className = !ing.activo ? "inventario-inactivo" : ing.stock_bajo ? "inventario-alerta" : "inventario-correcto";
      const acciones = crear("td");
      const grupo = crear("div", "inventario-acciones");
      grupo.appendChild(boton("Editar", () => abrirIngrediente(ing)));
      if (ing.activo) grupo.appendChild(boton("Movimiento", () => abrirMovimiento(ing), "sigep-action sigep-action-toggle"));
      if (esAdmin()) grupo.appendChild(boton(ing.activo ? "Desactivar" : "Activar", () => cambiarEstado(ing)));
      acciones.appendChild(grupo);tr.appendChild(acciones);tbody.appendChild(tr);
    }
    $("inventario-vacio").hidden = ingredientes.length > 0;
    const hist = $("inventario-historial");hist.replaceChildren();
    for (const m of movimientos.slice(0, 40)) {
      const tr = crear("tr");
      td(tr, fecha(m.fecha_movimiento));td(tr, m.ingrediente_nombre);
      td(tr, tipos[m.tipo] || m.tipo);
      td(tr, numero(m.cantidad) + " " + m.unidad_medida);
      td(tr, m.usuario);td(tr, m.motivo);
      hist.appendChild(tr);
    }
    $("inventario-historial-vacio").hidden = movimientos.length > 0;
    aviso("inventario-aviso", "");
  }

  function pintarRepostero() {
    const lista = $("inventario-repostero-lista");lista.replaceChildren();
    for (const ing of ingredientes) {
      const articulo = crear("article", "inventario-repostero-item");
      articulo.appendChild(crear("strong", "", ing.nombre));
      articulo.appendChild(crear("span", "", `${numero(ing.stock_actual)} ${ing.unidad_medida} disponibles · Mínimo ${numero(ing.stock_minimo)} ${ing.unidad_medida}`));
      articulo.appendChild(crear("small", ing.stock_bajo ? "inventario-alerta" : "inventario-correcto", ing.stock_bajo ? "Reabastecimiento necesario" : "Existencia suficiente"));
      lista.appendChild(articulo);
    }
    if (!ingredientes.length) lista.appendChild(crear("p", "inventario-muted", "No hay ingredientes activos para mostrar."));
    aviso("inventario-repostero-aviso", "");
  }

  function abrirIngrediente(ingrediente=null) {
    if (!gestiona()) return;
    editId = ingrediente?.id || null;
    $("inventario-ingrediente-form").reset();
    $("inventario-ingrediente-titulo").textContent = editId ? "Editar ingrediente" : "Nuevo ingrediente";
    $("inventario-ingrediente-nombre").value = ingrediente?.nombre || "";
    $("inventario-ingrediente-descripcion").value = ingrediente?.descripcion || "";
    $("inventario-ingrediente-unidad").value = ingrediente?.unidad_medida || "KG";
    $("inventario-ingrediente-unidad").disabled = Boolean(editId && Number(ingrediente.stock_actual) !== 0);
    $("inventario-ingrediente-minimo").value = ingrediente?.stock_minimo || "0.000";
    $("inventario-ingrediente-costo").value = ingrediente?.costo_unitario || "0.00";
    aviso("inventario-ingrediente-aviso", "");
    $("inventario-ingrediente-dialog").showModal();
  }

  async function guardarIngrediente(ev) {
    ev.preventDefault();if (!gestiona()) return;
    const botonGuardar = $("inventario-ingrediente-guardar");botonGuardar.disabled = true;
    const datos = {
      nombre: $("inventario-ingrediente-nombre").value.trim(),
      descripcion: $("inventario-ingrediente-descripcion").value.trim(),
      stock_minimo: $("inventario-ingrediente-minimo").value,
      costo_unitario: $("inventario-ingrediente-costo").value,
    };
    if (!$("inventario-ingrediente-unidad").disabled) datos.unidad_medida = $("inventario-ingrediente-unidad").value;
    try {
      await request(editId ? `/inventario/ingredientes/${editId}/` : "/inventario/ingredientes/", editId ? "PATCH" : "POST", datos);
      $("inventario-ingrediente-dialog").close(); await actualizar();
    } catch (error) { aviso("inventario-ingrediente-aviso", error.message, true); }
    finally {botonGuardar.disabled = false;}
  }

  function abrirMovimiento(ingrediente) {
    if (!gestiona()) return;
    $("inventario-movimiento-form").reset();
    $("inventario-movimiento-id").value = ingrediente.id;
    $("inventario-movimiento-nombre").textContent = ingrediente.nombre + " · Stock actual: " + numero(ingrediente.stock_actual) + " " + ingrediente.unidad_medida;
    $("inventario-movimiento-cantidad").step = ingrediente.unidad_medida === "PIEZA" ? "1" : "0.001";
    aviso("inventario-movimiento-aviso", "");
    $("inventario-movimiento-dialog").showModal();
  }

  async function guardarMovimiento(ev) {
    ev.preventDefault(); if (!gestiona()) return;
    const botonGuardar = $("inventario-movimiento-guardar");botonGuardar.disabled = true;
    try {
      await request("/inventario/movimientos/", "POST", {
        ingrediente_id: Number($("inventario-movimiento-id").value),
        tipo: $("inventario-movimiento-tipo").value,
        cantidad: $("inventario-movimiento-cantidad").value,
        motivo: $("inventario-movimiento-motivo").value.trim(),
      });
      $("inventario-movimiento-dialog").close();await actualizar();
    } catch (error) {aviso("inventario-movimiento-aviso", error.message, true);}
    finally {botonGuardar.disabled=false;}
  }

  async function cambiarEstado(ingrediente) {
    if (!esAdmin()) return;
    const texto = ingrediente.activo ? "desactivar" : "reactivar";
    if (!window.confirm(`¿Quieres ${texto} el ingrediente «${ingrediente.nombre}»?`)) return;
    try {
      await request(`/inventario/ingredientes/${ingrediente.id}/estado/`, "PATCH", {activo: !ingrediente.activo});
      await actualizar();
    } catch (error) {aviso("inventario-aviso", error.message, true);}
  }

  function detener() {
    ++seq;request=null;rol=null;ingredientes=[];movimientos=[];editId=null;
    $("inventario-repostero-panel").hidden=true;
    $("session-panel").classList.remove("inventario-sesion-ancha");
    for (const id of ["inventario-ingrediente-dialog", "inventario-movimiento-dialog"]) {
      if ($(id).open) $(id).close();
    }
  }

  $("inventario-actualizar").addEventListener("click", actualizar);
  $("inventario-actualizar-repostero").addEventListener("click", actualizar);
  $("inventario-nuevo").addEventListener("click", () => abrirIngrediente());
  $("inventario-buscar").addEventListener("input", () => actualizar());
  $("inventario-filtro-estado").addEventListener("change", actualizar);
  $("inventario-ingrediente-form").addEventListener("submit", guardarIngrediente);
  $("inventario-movimiento-form").addEventListener("submit", guardarMovimiento);
  $("inventario-ingrediente-cerrar").addEventListener("click", () => $("inventario-ingrediente-dialog").close());
  $("inventario-movimiento-cerrar").addEventListener("click", () => $("inventario-movimiento-dialog").close());
  window.SIGEPInventario = {iniciar, actualizar, detener};
})();
