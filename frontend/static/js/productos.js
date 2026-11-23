/* SIGEP · Fase 3. Catálogo visual. No almacena claves ni contraseñas. */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  let request = null;
  let conectado = false;
  let esAdmin = false;
  let productos = [];
  let categorias = [];
  let editandoProducto = null;
  let editandoCategoria = null;
  let secuencia = 0;
  let buscarTimer = null;
  let urlVistaPrevia = null;
  let seleccionImagen = 0;
  const FORMATOS_IMAGEN = new Set(["image/jpeg", "image/png", "image/webp"]);
  const EXTENSIONES_IMAGEN = /\.(jpe?g|png|webp)$/i;
  const MAX_IMAGEN = 3 * 1024 * 1024;

  function mensaje(id, texto, error = false) {
    const elemento = $(id);
    elemento.textContent = texto;
    elemento.className = `sigep-feedback ${error ? "sigep-feedback-error" : "sigep-feedback-ok"}`;
    elemento.hidden = !texto;
  }

  function errorModal(id, texto) {
    $(id).textContent = texto;
    $(id).hidden = !texto;
  }

  function td(tr, valor) {
    const c = document.createElement("td");
    c.textContent = valor === "" || valor === null || valor === undefined ? "—" : String(valor);
    tr.appendChild(c);
    return c;
  }

  function accion(texto, callback) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "sigep-action sigep-action-edit";
    b.textContent = texto;
    b.addEventListener("click", callback);
    return b;
  }

  const dinero = valor => Number(valor).toLocaleString("es-MX", { style: "currency", currency: "MXN" });

  function liberarPreview() {
    if (urlVistaPrevia) URL.revokeObjectURL(urlVistaPrevia);
    urlVistaPrevia = null;
    $("producto-imagen-preview").removeAttribute("src");
    $("producto-imagen-preview").hidden = true;
    $("producto-imagen-nota").textContent = "Sin imagen seleccionada.";
  }

  function imagenSegura(ruta) {
    if (!ruta) return null;
    try {
      const url = new URL(ruta, location.origin);
      return ["https:", "http:"].includes(url.protocol) ? url.href : null;
    } catch { return null; }
  }

  function mostrarPreviewGuardada(ruta) {
    liberarPreview();
    const segura = imagenSegura(ruta);
    if (segura) {
      $("producto-imagen-preview").src = segura;
      $("producto-imagen-preview").hidden = false;
      $("producto-imagen-nota").textContent = "Imagen actual. Elige otra para reemplazarla.";
    }
  }

  function comprobarImagen(archivo) {
    if (!archivo) return Promise.resolve();
    if (archivo.size > MAX_IMAGEN) return Promise.reject(new Error("La imagen no debe superar 3 MB."));
    if (!EXTENSIONES_IMAGEN.test(archivo.name) || (archivo.type && !FORMATOS_IMAGEN.has(archivo.type))) {
      return Promise.reject(new Error("Selecciona un archivo JPG, PNG o WebP."));
    }
    return new Promise((resolve, reject) => {
      const url = URL.createObjectURL(archivo);
      const foto = new Image();
      foto.onload = () => {
        const valido = foto.naturalWidth >= 100 && foto.naturalWidth <= 4096
          && foto.naturalHeight >= 100 && foto.naturalHeight <= 4096;
        URL.revokeObjectURL(url);
        valido ? resolve() : reject(new Error("La imagen debe medir entre 100 y 4096 píxeles por lado."));
      };
      foto.onerror = () => { URL.revokeObjectURL(url); reject(new Error("El archivo no es una imagen legible.")); };
      foto.src = url;
    });
  }

  async function imagenSeleccionada() {
    const turno = ++seleccionImagen;
    const archivo = $("producto-imagen-archivo").files[0];
    liberarPreview();
    if (!archivo) return;
    try {
      await comprobarImagen(archivo);
      if (turno !== seleccionImagen) return;
      urlVistaPrevia = URL.createObjectURL(archivo);
      $("producto-imagen-preview").src = urlVistaPrevia;
      $("producto-imagen-preview").hidden = false;
      $("producto-imagen-nota").textContent = `${archivo.name} · ${(archivo.size / 1024 / 1024).toFixed(2)} MB`;
      errorModal("producto-error", "");
    } catch (e) {
      if (turno !== seleccionImagen) return;
      $("producto-imagen-archivo").value = "";
      errorModal("producto-error", e.message);
      if (editandoProducto) mostrarPreviewGuardada(editandoProducto.imagen_url);
    }
  }

  function rellenarCategorias() {
    const filtro = $("productos-filtro-categoria");
    const anterior = filtro.value;
    filtro.replaceChildren(new Option("Todas", ""));
    for (const categoria of categorias) {
      filtro.add(new Option(categoria.nombre + (!categoria.activo ? " (inactiva)" : ""), String(categoria.id)));
    }
    if ([...filtro.options].some(o => o.value === anterior)) filtro.value = anterior;
  }

  function dibujarProductos() {
    const tbody = $("productos-tbody");
    tbody.replaceChildren();
    $("productos-total").textContent = productos.length;
    $("productos-activos").textContent = productos.filter(p => p.activo).length;
    $("productos-categorias-total").textContent = categorias.length;
    $("productos-vacio").hidden = productos.length > 0;

    for (const producto of productos) {
      const tr = document.createElement("tr");
      const nombre = document.createElement("td");
      const contenedor = document.createElement("div");
      contenedor.className = "sigep-producto-titulo";
      const url = imagenSegura(producto.imagen_url);
      if (url) {
        const img = document.createElement("img");
        img.src = url;
        img.alt = "";
        img.loading = "lazy";
        img.referrerPolicy = "no-referrer";
        img.className = "sigep-producto-miniatura";
        contenedor.appendChild(img);
      } else {
        const placeholder = document.createElement("span");
        placeholder.className = "sigep-producto-miniatura sigep-producto-sin-imagen";
        placeholder.textContent = "🧁";
        contenedor.appendChild(placeholder);
      }
      const detalles = document.createElement("span");
      const titulo = document.createElement("strong");
      titulo.textContent = producto.nombre;
      const descripcion = document.createElement("small");
      descripcion.textContent = producto.descripcion || "Sin descripción";
      detalles.append(titulo, descripcion);
      contenedor.appendChild(detalles);
      nombre.appendChild(contenedor);
      tr.appendChild(nombre);
      td(tr, producto.categoria_nombre);
      td(tr, dinero(producto.precio_base));
      td(tr, { PIEZA: "Pieza", CAJA: "Caja", PORCION: "Porción", KG: "Kg" }[producto.unidad_venta] || producto.unidad_venta);
      const estado = document.createElement("td");
      const insignia = document.createElement("span");
      insignia.className = `sigep-status ${producto.activo ? "sigep-status-on" : "sigep-status-off"}`;
      insignia.textContent = producto.activo ? "Activo" : "Inactivo";
      estado.appendChild(insignia);
      tr.appendChild(estado);
      const acciones = document.createElement("td");
      if (esAdmin) {
        const grupo = document.createElement("div");
        grupo.className = "sigep-row-actions";
        grupo.appendChild(accion("Editar", () => abrirProducto(producto)));
        grupo.appendChild(accion(producto.activo ? "Desactivar" : "Activar", () => estadoProducto(producto)));
        acciones.appendChild(grupo);
      } else {
        acciones.textContent = "Solo lectura";
      }
      tr.appendChild(acciones);
      tbody.appendChild(tr);
    }
  }

  function dibujarCategorias() {
    const tbody = $("categorias-tbody");
    tbody.replaceChildren();
    $("categorias-vacio").hidden = categorias.length > 0;
    for (const categoria of categorias) {
      const tr = document.createElement("tr");
      td(tr, categoria.nombre).className = "sigep-cell-name";
      td(tr, categoria.descripcion);
      td(tr, categoria.activo ? "Activa" : "Inactiva");
      const acciones = document.createElement("td");
      if (esAdmin) {
        const grupo = document.createElement("div");
        grupo.className = "sigep-row-actions";
        grupo.appendChild(accion("Editar", () => abrirCategoria(categoria)));
        grupo.appendChild(accion(categoria.activo ? "Desactivar" : "Activar", () => estadoCategoria(categoria)));
        acciones.appendChild(grupo);
      } else {
        acciones.textContent = "Solo lectura";
      }
      tr.appendChild(acciones);
      tbody.appendChild(tr);
    }
  }

  async function cargar() {
    if (!conectado || !request) return;
    const numero = ++secuencia;
    $("productos-refrescar").disabled = true;
    mensaje("productos-feedback", "Consultando catálogo...");
    try {
      const params = new URLSearchParams();
      const buscar = $("productos-buscar").value.trim();
      const categoria = $("productos-filtro-categoria").value;
      const activo = $("productos-filtro-estado").value;
      if (buscar) params.set("buscar", buscar);
      if (categoria) params.set("categoria", categoria);
      if (activo) params.set("activo", activo);
      const ruta = `/productos/${params.toString() ? "?" + params : ""}`;
      const [categoriasApi, productosApi] = await Promise.all([request("/categorias/"), request(ruta)]);
      if (!conectado || numero !== secuencia) return;
      categorias = Array.isArray(categoriasApi) ? categoriasApi : (categoriasApi?.results || []);
      productos = Array.isArray(productosApi) ? productosApi : (productosApi?.results || []);
      rellenarCategorias();
      dibujarProductos();
      dibujarCategorias();
      mensaje("productos-feedback", "");
      mensaje("categorias-feedback", "");
    } catch (e) {
      if (numero !== secuencia || !conectado) return;
      productos = [];
      categorias = [];
      dibujarProductos();
      dibujarCategorias();
      mensaje("productos-feedback", `No fue posible consultar productos: ${e.message}`, true);
    } finally {
      if (numero === secuencia) $("productos-refrescar").disabled = false;
    }
  }

  function selectCategorias(idActual) {
    const select = $("producto-categoria");
    select.replaceChildren(new Option("Selecciona una categoría", ""));
    for (const c of categorias.filter(c => c.activo || c.id === idActual)) {
      select.add(new Option(c.nombre + (!c.activo ? " (inactiva)" : ""), String(c.id)));
    }
  }

  function abrirProducto(producto = null) {
    if (!esAdmin) return;
    editandoProducto = producto;
    $("producto-form").reset();
    selectCategorias(producto?.categoria);
    $("producto-dialog-title").textContent = producto ? `Editar producto #${producto.id}` : "Nuevo producto";
    $("producto-nombre").value = producto?.nombre || "";
    $("producto-categoria").value = producto ? String(producto.categoria) : "";
    $("producto-precio").value = producto?.precio_base || "";
    $("producto-unidad").value = producto?.unidad_venta || "PIEZA";
    ++seleccionImagen;
    mostrarPreviewGuardada(producto?.imagen_url);
    $("producto-descripcion").value = producto?.descripcion || "";
    errorModal("producto-error", "");
    $("producto-dialog").showModal();
    $("producto-nombre").focus();
  }

  async function guardarProducto(event) {
    event.preventDefault();
    if (!esAdmin || !request || !$("producto-form").reportValidity()) return;
    const datos = {
      nombre: $("producto-nombre").value.trim(),
      categoria_id: Number($("producto-categoria").value),
      precio_base: $("producto-precio").value,
      unidad_venta: $("producto-unidad").value,
      descripcion: $("producto-descripcion").value.trim(),
    };
    if (!datos.categoria_id || Number(datos.precio_base) <= 0) {
      return errorModal("producto-error", "Selecciona una categoría y un precio positivo.");
    }
    const archivo = $("producto-imagen-archivo").files[0];
    const boton = $("producto-guardar");
    boton.disabled = true;
    errorModal("producto-error", "");
    try {
      let cuerpo = datos;
      if (archivo) {
        await comprobarImagen(archivo);
        cuerpo = new FormData();
        for (const [clave, valor] of Object.entries(datos)) cuerpo.append(clave, String(valor));
        cuerpo.append("imagen", archivo);
      }
      if (editandoProducto) await request(`/productos/${editandoProducto.id}/`, "PATCH", cuerpo);
      else await request("/productos/", "POST", cuerpo);
      if (!conectado) return;
      $("producto-dialog").close();
      liberarPreview();
      await cargar();
      mensaje("productos-feedback", "Producto guardado correctamente.");
    } catch (e) {
      errorModal("producto-error", e.message);
    } finally { boton.disabled = false; }
  }

  async function estadoProducto(producto) {
    if (!esAdmin || !confirm(`¿${producto.activo ? "Desactivar" : "Activar"} ${producto.nombre}?`)) return;
    try {
      await request(`/productos/${producto.id}/estado/`, "PATCH", { activo: !producto.activo });
      await cargar();
      mensaje("productos-feedback", "Estado del producto actualizado.");
    } catch (e) { mensaje("productos-feedback", e.message, true); }
  }

  function abrirCategoria(categoria = null) {
    if (!esAdmin) return;
    editandoCategoria = categoria;
    $("categoria-form").reset();
    $("categoria-dialog-title").textContent = categoria ? `Editar categoría #${categoria.id}` : "Nueva categoría";
    $("categoria-nombre").value = categoria?.nombre || "";
    $("categoria-descripcion").value = categoria?.descripcion || "";
    errorModal("categoria-error", "");
    $("categoria-dialog").showModal();
    $("categoria-nombre").focus();
  }

  async function guardarCategoria(event) {
    event.preventDefault();
    if (!esAdmin || !request || !$("categoria-form").reportValidity()) return;
    const datos = { nombre: $("categoria-nombre").value.trim(), descripcion: $("categoria-descripcion").value.trim() };
    const boton = $("categoria-guardar");
    boton.disabled = true;
    errorModal("categoria-error", "");
    try {
      if (editandoCategoria) await request(`/categorias/${editandoCategoria.id}/`, "PATCH", datos);
      else await request("/categorias/", "POST", datos);
      if (!conectado) return;
      $("categoria-dialog").close();
      await cargar();
      mensaje("categorias-feedback", "Categoría guardada correctamente.");
    } catch (e) {
      errorModal("categoria-error", e.message);
    } finally { boton.disabled = false; }
  }

  async function estadoCategoria(categoria) {
    if (!esAdmin || !confirm(`¿${categoria.activo ? "Desactivar" : "Activar"} la categoría ${categoria.nombre}?`)) return;
    try {
      await request(`/categorias/${categoria.id}/estado/`, "PATCH", { activo: !categoria.activo });
      await cargar();
      mensaje("categorias-feedback", "Estado de la categoría actualizado.");
    } catch (e) { mensaje("categorias-feedback", e.message, true); }
  }

  function iniciar({ usuario, request: autorizada }) {
    detener();
    request = autorizada;
    conectado = true;
    esAdmin = usuario.is_superuser === true || usuario.rol?.codigo === "ADMIN";
    $("productos-nuevo").hidden = !esAdmin;
    $("categorias-nueva").hidden = !esAdmin;
    $("productos-buscar").value = "";
    $("productos-filtro-estado").value = "";
    $("productos-filtro-categoria").value = "";
    productos = [];
    categorias = [];
  }

  function detener() {
    conectado = false;
    request = null;
    esAdmin = false;
    productos = [];
    categorias = [];
    secuencia++;
    clearTimeout(buscarTimer);
    if ($("producto-dialog").open) $("producto-dialog").close();
    ++seleccionImagen;
    liberarPreview();
    if ($("categoria-dialog").open) $("categoria-dialog").close();
  }

  $("productos-nuevo").addEventListener("click", () => abrirProducto());
  $("categorias-nueva").addEventListener("click", () => abrirCategoria());
  $("productos-refrescar").addEventListener("click", cargar);
  $("productos-filtro-estado").addEventListener("change", cargar);
  $("productos-filtro-categoria").addEventListener("change", cargar);
  $("productos-buscar").addEventListener("input", () => {
    clearTimeout(buscarTimer);
    buscarTimer = setTimeout(cargar, 280);
  });
  $("producto-form").addEventListener("submit", guardarProducto);
  $("producto-imagen-archivo").addEventListener("change", imagenSeleccionada);
  $("categoria-form").addEventListener("submit", guardarCategoria);
  for (const [id, dialogId] of [["producto-cancelar", "producto-dialog"], ["producto-cerrar", "producto-dialog"], ["categoria-cancelar", "categoria-dialog"], ["categoria-cerrar", "categoria-dialog"]]) {
    $(id).addEventListener("click", () => {
      $(dialogId).close();
      if (dialogId === "producto-dialog") { ++seleccionImagen; liberarPreview(); }
    });
  }
  window.SIGEPProductos = { iniciar, detener, actualizar: cargar };
})();
