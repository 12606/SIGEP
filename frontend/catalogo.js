/* SIGEP: catálogo de solo lectura para visitantes y clientes.
   Los datos se obtienen del backend. El DOM se crea sin insertar HTML de productos. */
(() => {
  "use strict";

  const api = "/api/catalogo/";
  const $ = (id) => document.getElementById(id);
  const currency = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" });
  let root = null;
  let disponibles = [];
  let categorias = [];
  let modal = null;
  let anteriorFoco = null;
  let cargaPendiente = null;

  function nodo(tag, clase = "", texto = "") {
    const e = document.createElement(tag);
    if (clase) e.className = clase;
    if (texto) e.textContent = texto;
    return e;
  }

  async function obtener(ruta) {
    const respuesta = await fetch(api + ruta, { headers: { Accept: "application/json" }, cache: "no-store" });
    if (!respuesta.ok) throw new Error(`La API del catálogo respondió HTTP ${respuesta.status}.`);
    const datos = await respuesta.json();
    if (!Array.isArray(datos)) throw new Error("Respuesta inesperada del catálogo.");
    return datos;
  }

  function imagenSegura(url) {
    if (!url || typeof url !== "string") return null;
    try {
      const ruta = new URL(url, window.location.origin);
      return ["http:", "https:"].includes(ruta.protocol) ? ruta.href : null;
    } catch { return null; }
  }

  function fotoDe(producto) {
    const caja = nodo("div", "catalogo-photo");
    const url = imagenSegura(producto.imagen_url);
    const placeholder = () => {
      caja.replaceChildren(nodo("span", "catalogo-photo-placeholder", "🧁"));
    };
    if (!url) { placeholder(); return caja; }
    const imagen = document.createElement("img");
    imagen.src = url;
    imagen.alt = `Fotografía de ${producto.nombre}`;
    imagen.loading = "lazy";
    imagen.addEventListener("error", placeholder, { once: true });
    caja.append(imagen);
    return caja;
  }

  function precio(valor) {
    const numero = Number(valor);
    return Number.isFinite(numero) ? currency.format(numero) : "Consultar precio";
  }

  function cerrarDetalle() {
    if (!modal) return;
    modal.hidden = true;
    modal.replaceChildren();
    if (anteriorFoco?.isConnected) anteriorFoco.focus();
    anteriorFoco = null;
  }

  function detalle(producto) {
    anteriorFoco = document.activeElement;
    modal.replaceChildren();
    const tarjeta = nodo("div", "catalogo-modal-card");
    tarjeta.setAttribute("role", "document");
    const cerrar = nodo("button", "catalogo-button catalogo-modal-close", "Cerrar ✕");
    cerrar.type = "button";
    cerrar.addEventListener("click", cerrarDetalle);
    tarjeta.append(cerrar, fotoDe(producto));
    tarjeta.append(nodo("div", "catalogo-category", producto.categoria_nombre || "Producto"));
    tarjeta.append(nodo("h2", "", producto.nombre));
    tarjeta.append(nodo("p", "", producto.descripcion || "Sin descripción disponible."));
    const pie = nodo("div", "catalogo-card-footer");
    const importe = nodo("div", "catalogo-price", precio(producto.precio_base));
    importe.append(nodo("span", "catalogo-unit", producto.unidad_venta || "PIEZA"));
    pie.append(importe);
    tarjeta.append(pie);
    modal.append(tarjeta);
    modal.hidden = false;
    cerrar.focus();
  }

  function dibujar() {
    if (!root) return;
    const buscar = root.querySelector("[data-buscar]").value.trim().toLocaleLowerCase("es");
    const categoria = root.querySelector("[data-categoria]").value;
    const lista = disponibles.filter(p => {
      const texto = `${p.nombre || ""} ${p.descripcion || ""} ${p.categoria_nombre || ""}`.toLocaleLowerCase("es");
      return (!buscar || texto.includes(buscar)) && (!categoria || String(p.categoria) === categoria);
    });
    const contenedor = root.querySelector("[data-grid]");
    contenedor.replaceChildren();
    root.querySelector("[data-cuenta]").textContent = `${lista.length} producto${lista.length === 1 ? "" : "s"} disponible${lista.length === 1 ? "" : "s"}`;
    if (!lista.length) {
      contenedor.append(nodo("div", "catalogo-empty", "No encontramos productos con esos filtros. Prueba con otra búsqueda."));
      return;
    }
    for (const p of lista) {
      const card = nodo("article", "catalogo-card");
      card.append(fotoDe(p));
      const body = nodo("div", "catalogo-card-body");
      body.append(nodo("div", "catalogo-category", p.categoria_nombre || "Producto"));
      body.append(nodo("h3", "", p.nombre));
      body.append(nodo("p", "catalogo-desc", p.descripcion || "Delicioso postre de nuestra pastelería."));
      const footer = nodo("div", "catalogo-card-footer");
      const importe = nodo("div", "catalogo-price", precio(p.precio_base));
      importe.append(nodo("span", "catalogo-unit", p.unidad_venta || "PIEZA"));
      const boton = nodo("button", "catalogo-button", "Ver detalles");
      boton.type = "button";
      boton.addEventListener("click", () => detalle(p));
      footer.append(importe, boton);
      body.append(footer);
      card.append(body);
      contenedor.append(card);
    }
  }

  function plantilla() {
    const panel = nodo("div", "catalogo-root");
    panel.innerHTML = `
      <div class="catalogo-hero">
        <div class="catalogo-hero-kicker">DULCE ENCANTO · CATÁLOGO</div>
        <h2>Elige tu próximo antojo</h2>
        <p>Explora nuestros pasteles y postres, mira sus fotografías y conoce los precios. Los pedidos estarán disponibles próximamente.</p>
      </div>
      <div class="catalogo-controls">
        <label class="catalogo-field">Buscar producto<input data-buscar type="search" maxlength="120" placeholder="Pastel, chocolate, cupcake..."></label>
        <label class="catalogo-field">Categoría<select data-categoria><option value="">Todas las categorías</option></select></label>
        <button data-limpiar type="button" class="catalogo-button">Limpiar filtros</button>
      </div>
      <p data-cuenta class="catalogo-count" role="status" aria-live="polite">Cargando catálogo...</p>
      <div data-error class="catalogo-error" hidden role="alert"></div>
      <div data-grid class="catalogo-grid" aria-live="polite"></div>`;
    panel.querySelector("[data-buscar]").addEventListener("input", dibujar);
    panel.querySelector("[data-categoria]").addEventListener("change", dibujar);
    panel.querySelector("[data-limpiar]").addEventListener("click", () => {
      panel.querySelector("[data-buscar]").value = "";
      panel.querySelector("[data-categoria]").value = "";
      dibujar();
    });
    return panel;
  }

  async function actualizar() {
    if (!root) return;
    if (cargaPendiente) return cargaPendiente;
    const error = root.querySelector("[data-error]");
    error.hidden = true;
    root.querySelector("[data-cuenta]").textContent = "Cargando catálogo...";
    cargaPendiente = Promise.all([obtener("categorias/"), obtener("productos/")])
      .then(([cats, prods]) => {
        categorias = cats;
        disponibles = prods;
        const filtro = root.querySelector("[data-categoria]");
        const anterior = filtro.value;
        filtro.replaceChildren();
        const todas = document.createElement("option");
        todas.value = "";
        todas.textContent = "Todas las categorías";
        filtro.append(todas);
        for (const cat of categorias) {
          const opcion = document.createElement("option");
          opcion.value = String(cat.id);
          opcion.textContent = cat.nombre;
          filtro.append(opcion);
        }
        filtro.value = anterior;
        dibujar();
      })
      .catch(err => {
        disponibles = [];
        root.querySelector("[data-grid]").replaceChildren();
        root.querySelector("[data-cuenta]").textContent = "No se pudo cargar el catálogo.";
        error.textContent = err.message + " Revisa que Django esté ejecutándose.";
        error.hidden = false;
      })
      .finally(() => { cargaPendiente = null; });
    return cargaPendiente;
  }

  function mostrar(contenedorId) {
    const contenedor = $(contenedorId);
    if (!contenedor) return;
    if (!root) root = plantilla();
    contenedor.append(root);
    if (!modal) {
      modal = nodo("div", "catalogo-modal");
      modal.hidden = true;
      modal.setAttribute("role", "dialog");
      modal.setAttribute("aria-modal", "true");
      modal.setAttribute("aria-label", "Detalles del producto");
      modal.addEventListener("click", e => { if (e.target === modal) cerrarDetalle(); });
      document.addEventListener("keydown", e => { if (e.key === "Escape") cerrarDetalle(); });
      document.body.append(modal);
    }
    cerrarDetalle();
    actualizar();
  }

  window.SIGEPCatalogo = { mostrar, actualizar, cerrarDetalle };
})();
