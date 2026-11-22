/* SIGEP Fase 6 · Reportes administrativos, sin dependencias externas.
   La API decide los permisos. Nunca confiar en controles ocultos del navegador. */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const NS = "http://www.w3.org/2000/svg";
  const moneda = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" });
  const entero = new Intl.NumberFormat("es-MX");
  let solicitar = null;
  let activo = false;
  let cargando = false;
  let secuencia = 0;

  const fechaLocal = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

  function aviso(mensaje, error = false) {
    const elemento = $("reportes-aviso");
    elemento.hidden = !mensaje;
    elemento.textContent = mensaje || "";
    elemento.classList.toggle("reportes-aviso-error", error);
  }

  function crear(tag, clase, contenido = null) {
    const nodo = document.createElement(tag);
    if (clase) nodo.className = clase;
    if (contenido !== null) nodo.textContent = String(contenido);
    return nodo;
  }

  function parametros(tipo = null) {
    const query = new URLSearchParams({
      desde: $("reportes-desde").value,
      hasta: $("reportes-hasta").value,
    });
    if (tipo) query.set("tipo", tipo);
    return `?${query.toString()}`;
  }

  function validarFechas() {
    const desde = $("reportes-desde").value;
    const hasta = $("reportes-hasta").value;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(desde) || !/^\d{4}-\d{2}-\d{2}$/.test(hasta)) {
      throw new Error("Selecciona ambas fechas.");
    }
    if (hasta < desde) throw new Error("La fecha final debe ser igual o posterior a la inicial.");
  }

  function tarjeta(id, valor, tipo = "numero") {
    $(id).textContent = tipo === "dinero" ? moneda.format(Number(valor) || 0) : entero.format(Number(valor) || 0);
  }

  function dibujoSVG(tag, atributos = {}) {
    const nodo = document.createElementNS(NS, tag);
    for (const [nombre, valor] of Object.entries(atributos)) nodo.setAttribute(nombre, String(valor));
    return nodo;
  }

  function renderGrafica(serie) {
    const contenedor = $("reportes-grafica");
    contenedor.replaceChildren();
    if (!serie?.length) {
      contenedor.append(crear("p", "reportes-vacio", "No hay información para este período."));
      return;
    }
    // Se agrupan hasta 14 intervalos para que la gráfica sea legible en escritorio y móvil.
    const tamano = Math.max(1, Math.ceil(serie.length / 14));
    const grupos = [];
    for (let i = 0; i < serie.length; i += tamano) {
      const trozo = serie.slice(i, i + tamano);
      grupos.push({
        inicio: trozo[0].fecha,
        fin: trozo[trozo.length - 1].fecha,
        cobros: trozo.reduce((sum, f) => sum + Number(f.cobros), 0),
        pedidos: trozo.reduce((sum, f) => sum + Number(f.pedidos), 0),
      });
    }
    const max = Math.max(1, ...grupos.map(x => x.cobros));
    const svg = dibujoSVG("svg", {
      viewBox: "0 0 680 240", role: "img",
      "aria-label": "Gráfica de cobros registrados agrupados por fecha",
      preserveAspectRatio: "xMidYMid meet",
    });
    const titulo = dibujoSVG("title");
    titulo.textContent = "Cobros registrados (MXN)";
    svg.append(titulo);
    [0, 0.5, 1].forEach((fraccion) => {
      const y = 190 - fraccion * 156;
      svg.append(dibujoSVG("line", { x1: 65, y1: y, x2: 666, y2: y, stroke: "#eadbda", "stroke-width": 1 }));
      const txt = dibujoSVG("text", { x: 57, y: y + 4, "text-anchor": "end", "font-size": 11, fill: "#82665e" });
      txt.textContent = max * fraccion >= 1000 ? `${Math.round(max * fraccion / 1000)} mil` : Math.round(max * fraccion).toLocaleString("es-MX");
      svg.append(txt);
    });
    const paso = 590 / grupos.length;
    grupos.forEach((grupo, i) => {
      const alto = Math.max(0, grupo.cobros / max * 156);
      const x = 70 + paso * i + paso * 0.15;
      const rect = dibujoSVG("rect", {
        x, y: 190 - alto, width: Math.max(4, paso * 0.65), height: alto,
        rx: 5, fill: "#e5779b",
      });
      const title = dibujoSVG("title");
      title.textContent = `${grupo.inicio} a ${grupo.fin}: ${moneda.format(grupo.cobros)} · ${grupo.pedidos} pedidos`;
      rect.append(title);
      svg.append(rect);
      if (i === 0 || i === grupos.length - 1 || i === Math.floor(grupos.length / 2)) {
        const label = dibujoSVG("text", { x: x + paso * 0.3, y: 215, "text-anchor": "middle", "font-size": 11, fill: "#82665e" });
        label.textContent = grupo.inicio.slice(5);
        svg.append(label);
      }
    });
    contenedor.append(svg);
    if (!grupos.some(x => x.cobros > 0)) {
      contenedor.append(crear("p", "reportes-vacio", "Todavía no hay cobros registrados en las fechas seleccionadas."));
    }
  }

  function estados(datos) {
    const root = $("reportes-estados");
    root.replaceChildren();
    const max = Math.max(1, ...datos.map(e => Number(e.cantidad)));
    for (const estado of datos) {
      const fila = crear("div", "reportes-estado");
      const cabecera = crear("div", "reportes-estado-titulo");
      cabecera.append(crear("span", null, estado.nombre), crear("strong", null, entero.format(estado.cantidad)));
      const fondo = crear("div", "reportes-barra-fondo");
      const barra = crear("div", "reportes-barra-progreso");
      barra.style.width = `${Math.max(0, Number(estado.cantidad) / max * 100)}%`;
      fondo.append(barra);
      fila.append(cabecera, fondo);
      root.append(fila);
    }
  }

  function tablaProductos(items) {
    const cuerpo = $("reportes-productos");
    cuerpo.replaceChildren();
    for (const producto of items) {
      const fila = document.createElement("tr");
      for (const dato of [producto.nombre, entero.format(producto.unidades), moneda.format(Number(producto.importe))]) {
        fila.append(crear("td", null, dato));
      }
      cuerpo.append(fila);
    }
    $("reportes-productos-vacio").hidden = items.length > 0;
  }

  function tablaAlertas(inventario) {
    const cuerpo = $("reportes-alertas");
    cuerpo.replaceChildren();
    for (const ingrediente of inventario.alertas) {
      const fila = document.createElement("tr");
      for (const dato of [ingrediente.nombre, `${ingrediente.existencia} ${ingrediente.unidad}`, `${ingrediente.minimo} ${ingrediente.unidad}`]) {
        fila.append(crear("td", null, dato));
      }
      cuerpo.append(fila);
    }
    $("reportes-alertas-vacio").hidden = inventario.alertas.length > 0;
    $("reportes-alertas-total").textContent = entero.format(inventario.ingredientes_bajo_minimo);
  }

  function mostrar(datos) {
    const k = datos.indicadores;
    tarjeta("reportes-pedidos-total", k.pedidos_registrados);
    tarjeta("reportes-importe", k.importe_pedidos, "dinero");
    tarjeta("reportes-cobros", k.cobros_registrados, "dinero");
    tarjeta("reportes-saldo", k.saldo_pedidos, "dinero");
    tarjeta("reportes-ticket", k.ticket_promedio, "dinero");
    tarjeta("reportes-clientes", k.clientes_nuevos);
    $("reportes-periodo").textContent = `${datos.periodo.desde} al ${datos.periodo.hasta}`;
    $("reportes-nota").textContent = datos.nota;
    renderGrafica(datos.serie);
    estados(datos.estados);
    tablaProductos(datos.productos);
    tablaAlertas(datos.inventario);
  }

  async function actualizar() {
    if (!activo || !solicitar || cargando || $("sigep-vista-reportes").hidden) return;
    const actual = ++secuencia;
    const boton = $("reportes-actualizar");
    try {
      validarFechas();
      aviso("");
      cargando = true;
      boton.disabled = true;
      boton.textContent = "Consultando...";
      const datos = await solicitar(`/reportes/dashboard/${parametros()}`);
      if (!activo || actual !== secuencia) return;
      mostrar(datos);
    } catch (error) {
      if (activo && actual === secuencia) aviso(error.message || "No se pudieron consultar los reportes.", true);
    } finally {
      cargando = false;
      boton.disabled = false;
      boton.textContent = "Actualizar";
    }
  }

  // Protege contra fórmulas al abrir CSV en Excel/LibreOffice, incluido texto externo.
  function csvCelda(valor) {
    let texto = String(valor ?? "");
    if (/^\s*[=+\-@\t\r]/.test(texto)) texto = `'${texto}`;
    return `"${texto.replaceAll('"', '""')}"`;
  }

  async function exportar(tipo, boton) {
    if (!activo || !solicitar) return;
    try {
      validarFechas();
      aviso("");
      boton.disabled = true;
      const datos = await solicitar(`/reportes/exportar/${parametros(tipo)}`);
      if (!activo) return;
      const filas = [datos.columnas, ...datos.filas];
      const csv = "\uFEFF" + filas.map(fila => fila.map(csvCelda).join(",")).join("\r\n") + "\r\n";
      const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = `SIGEP_${tipo}_${datos.periodo.desde}_${datos.periodo.hasta}.csv`;
      document.body.append(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      aviso(`Se generó el archivo con ${datos.total} ${tipo}.`);
    } catch (error) {
      aviso(error.message || "No se pudo generar el reporte CSV.", true);
    } finally {
      boton.disabled = false;
    }
  }

  function iniciar({ usuario, request }) {
    const admin = usuario?.is_superuser || usuario?.rol?.codigo === "ADMIN";
    if (!admin) return detener();
    solicitar = request;
    activo = true;
    aviso("");
  }

  function detener() {
    activo = false;
    solicitar = null;
    secuencia += 1;
    aviso("");
    $("reportes-productos").replaceChildren();
    $("reportes-alertas").replaceChildren();
    $("reportes-grafica").replaceChildren();
    $("reportes-estados").replaceChildren();
  }

  const hoy = new Date();
  const hace29 = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate() - 29);
  $("reportes-desde").value = fechaLocal(hace29);
  $("reportes-hasta").value = fechaLocal(hoy);
  $("reportes-actualizar").addEventListener("click", actualizar);
  $("reportes-exportar-pedidos").addEventListener("click", (e) => exportar("pedidos", e.currentTarget));
  $("reportes-exportar-pagos").addEventListener("click", (e) => exportar("pagos", e.currentTarget));

  window.SIGEPReportes = { iniciar, actualizar, detener };
})();
