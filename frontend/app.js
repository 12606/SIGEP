/* SIGEP · Dulce Encanto. Autenticación JWT con restauración por pestaña.
   sessionStorage conserva los tokens al recargar, pero no al cerrar la pestaña.
   En producción conviene reemplazarlo por refresh token en cookie HttpOnly,
   HTTPS y protección CSRF. Nunca guardes contraseñas en el navegador. */
(() => {
  "use strict";

  // La web se abre desde Django en http://127.0.0.1:8000/.
  // Usar ruta relativa evita errores CORS o puertos inconsistentes.
  const API_BASE = "/api";
  const CLAVE_TOKENS = "sigep.jwt.session.v1";
  const $ = (id) => document.getElementById(id);
  let sesion = null;
  let renovacionPendiente = null;
  let temporizadorRenovacion = null;
  let origenCatalogo = null;

  // Solo persiste los JWT; nombres y permisos siempre se consultan en Django.
  function guardarTokens() {
    if (!sesion?.access || !sesion?.refresh) return;
    try {
      sessionStorage.setItem(CLAVE_TOKENS, JSON.stringify({
        access: sesion.access, refresh: sesion.refresh
      }));
    } catch (error) {
      console.warn("El navegador no permite conservar la sesión:", error);
    }
  }

  function leerTokens() {
    try {
      const guardados = sessionStorage.getItem(CLAVE_TOKENS);
      if (!guardados) return null;
      const tokens = JSON.parse(guardados);
      if (typeof tokens?.access === "string" && tokens.access &&
          typeof tokens?.refresh === "string" && tokens.refresh) {
        return { access: tokens.access, refresh: tokens.refresh };
      }
    } catch (error) {
      console.warn("No se pudo leer la sesión guardada:", error);
    }
    borrarTokens();
    return null;
  }

  function borrarTokens() {
    try { sessionStorage.removeItem(CLAVE_TOKENS); } catch { /* Almacenamiento no disponible. */ }
  }

  // Solo se usa la fecha de vencimiento del JWT para PROGRAMAR su renovación.
  // La autorización real siempre la valida Django en cada petición.
  function vencimientoAccess(access) {
    try {
      const parte = access.split(".")[1];
      if (!parte) return null;
      const base64 = parte.replace(/-/g, "+").replace(/_/g, "/");
      const exp = JSON.parse(atob(base64)).exp;
      return Number.isFinite(exp) ? exp * 1000 : null;
    } catch { return null; }
  }

  function programarRenovacion() {
    if (temporizadorRenovacion !== null) clearTimeout(temporizadorRenovacion);
    temporizadorRenovacion = null;
    if (!sesion?.access || !sesion?.refresh) return;
    const vence = vencimientoAccess(sesion.access);
    if (vence === null) return; // Si no se puede leer, el HTTP 401 activa el refresh.
    const demora = Math.max(1000, Math.min(vence - Date.now() - 60_000, 2_147_000_000));
    temporizadorRenovacion = setTimeout(() => {
      temporizadorRenovacion = null;
      renovarSesion().catch(error => console.warn("Renovación JWT:", error.message));
    }, demora);
  }
  let origenPerfil = "session-panel";

  function aviso(id, texto, exito = false) {
    const elemento = $(id);
    elemento.textContent = texto;
    elemento.className = `text-sm rounded-xl px-4 py-3 ${exito
      ? "bg-green-50 text-green-800 border border-green-200"
      : "bg-red-50 text-red-800 border border-red-200"}`;
  }

  function limpiarAviso(id) {
    $(id).textContent = "";
    $(id).classList.add("hidden");
  }

  function enEspera(id, bloqueado, textoOcupado, textoNormal) {
    const boton = $(id);
    boton.disabled = bloqueado;
    boton.textContent = bloqueado ? textoOcupado : textoNormal;
    boton.classList.toggle("opacity-60", bloqueado);
    boton.classList.toggle("cursor-not-allowed", bloqueado);
  }

  // Solicitudes de la API en el mismo origen; reintenta una vez tras renovar JWT.
  async function peticion(ruta, metodo = "GET", datos = null, access = null, reintentar = true) {
    const headers = { "Accept": "application/json" };
    const esFormulario = typeof FormData !== "undefined" && datos instanceof FormData;
    if (datos !== null && !esFormulario) headers["Content-Type"] = "application/json";
    if (access) headers.Authorization = `Bearer ${access}`;

    let response;
    try {
      response = await fetch(`${API_BASE}${ruta}`, {
        method: metodo, headers,
        body: datos !== null ? (esFormulario ? datos : JSON.stringify(datos)) : undefined,
        credentials: "omit", cache: "no-store"
      });
    } catch (err) {
      throw new Error("No se pudo conectar a SIGEP. Ejecuta Django y abre http://127.0.0.1:8000/.");
    }

    if (response.status === 401 && access && sesion?.refresh && reintentar) {
      await renovarSesion();
      return peticion(ruta, metodo, datos, sesion.access, false);
    }

    let payload = null;
    const tipo = response.headers.get("content-type") || "";
    if (tipo.includes("application/json")) {
      try { payload = await response.json(); } catch { payload = null; }
    }
    if (!response.ok) {
      const partes = [];
      if (payload && typeof payload === "object") {
        for (const [campo, valor] of Object.entries(payload)) {
          const txt = Array.isArray(valor) ? valor.join(" ") : String(valor);
          partes.push(["detail", "non_field_errors"].includes(campo) ? txt : `${campo}: ${txt}`);
        }
      }
      const error = new Error(partes.join(" · ") || `La solicitud falló (HTTP ${response.status}).`);
      error.status = response.status;
      throw error;
    }
    return payload;
  }

  async function renovarSesion() {
    if (!sesion?.refresh) throw new Error("Inicia sesión nuevamente.");
    if (!renovacionPendiente) {
      renovacionPendiente = (async () => {
        const sesionOriginal = sesion;
        const refreshAnterior = sesionOriginal.refresh;
        const nuevos = await peticion("/auth/refresh/", "POST", { refresh: refreshAnterior }, null, false);
        if (!nuevos?.access) throw new Error("No fue posible renovar la sesión.");
        // Si el usuario cerró sesión mientras llegaba la respuesta, no la restauramos.
        if (sesion !== sesionOriginal) return;
        sesion.access = nuevos.access;
        sesion.refresh = nuevos.refresh || refreshAnterior;
        // Con ROTATE_REFRESH_TOKENS el anterior se invalida: guardar el nuevo.
        guardarTokens();
        programarRenovacion();
      })().catch((error) => {
        // Un problema de red no debe destruir la sesión guardada.
        if ([400, 401, 403].includes(error.status)) cerrarSesionLocal();
        throw error;
      }).finally(() => { renovacionPendiente = null; });
    }
    return renovacionPendiente;
  }

  function peticionAutenticada(ruta, metodo = "GET", datos = null) {
    if (!sesion?.access) return Promise.reject(new Error("Inicia sesión para continuar."));
    return peticion(ruta, metodo, datos, sesion.access);
  }

  function mostrarSesion(usuario) {
    $("auth-card").classList.add("hidden");
    $("session-panel").classList.add("hidden");
    $("clientes-panel").classList.add("hidden");
    $("catalogo-visitante-panel").classList.add("hidden");
    $("session-panel").classList.remove("catalogo-sesion-activa");
    $("catalogo-en-sesion").classList.add("hidden");
    $("catalogo-abrir-sesion").classList.add("hidden");
    $("perfil-panel").classList.add("hidden");
    $("pedidos-cliente-panel").hidden = true;
    $("pedidos-produccion-panel").hidden = true;
    $("inventario-repostero-panel").hidden = true;
    $("session-panel").classList.remove("pedidos-sesion-ancha");
    const nombre = [usuario.first_name, usuario.last_name].filter(Boolean).join(" ");
    $("session-name").textContent = nombre || usuario.username;
    $("session-role").textContent = `Usuario: ${usuario.username} · Rol: ${usuario.rol?.nombre || "Sin rol"}`;

    const rol = usuario.rol?.codigo;
    const administrador = rol === "ADMIN" || usuario.is_superuser === true;
    window.SIGEPPerfil?.iniciar({ usuario, request: peticionAutenticada, alActualizar: actualizarSesionPerfil });
    if (administrador || rol === "VENTAS" || rol === "ALMACEN") {
      $("clientes-panel").classList.remove("hidden");
      $("clientes-usuario").textContent = `${usuario.first_name || usuario.username} · ${usuario.rol?.nombre || "Personal"}`;
      $("sigep-admin-tabs").hidden = false;
      $("sigep-tab-clientes").hidden = rol === "ALMACEN";
      $("sigep-tab-usuarios").hidden = !administrador;
      $("sigep-tab-productos").hidden = rol === "ALMACEN";
      $("sigep-tab-pedidos").hidden = rol === "ALMACEN";
      $("sigep-tab-inventario").hidden = !administrador && rol !== "ALMACEN";
      if (administrador || rol === "VENTAS") {
        window.SIGEPClientes?.iniciar({ usuario, request: peticionAutenticada });
        window.SIGEPProductos?.iniciar({ usuario, request: peticionAutenticada });
        window.SIGEPPedidos?.iniciar({ usuario, request: peticionAutenticada });
      }
      if (administrador) window.SIGEPUsuarios?.iniciar({ usuario, request: peticionAutenticada });
      if (administrador || rol === "ALMACEN") window.SIGEPInventario?.iniciar({ usuario, request: peticionAutenticada });
      cambiarVistaSIGEP(rol === "ALMACEN" ? "inventario" : "clientes");
      return;
    }

    $("session-panel").classList.remove("hidden");
    if (rol === "CLIENTE" || rol === "REPOSTERO") {
      window.SIGEPPedidos?.iniciar({ usuario, request: peticionAutenticada });
    }
    if (rol === "REPOSTERO") window.SIGEPInventario?.iniciar({ usuario, request: peticionAutenticada });
    if (rol === "CLIENTE") {
      $("session-panel").classList.add("catalogo-sesion-activa");
      $("catalogo-en-sesion").classList.remove("hidden");
      window.SIGEPCatalogo?.mostrar("catalogo-en-sesion");
    } else {
      $("catalogo-abrir-sesion").classList.remove("hidden");
    }
  }

  function actualizarSesionPerfil(datos) {
    if (!sesion?.usuario) return;
    Object.assign(sesion.usuario, datos);
    const nombre = [sesion.usuario.first_name, sesion.usuario.last_name].filter(Boolean).join(" ");
    $("session-name").textContent = nombre || sesion.usuario.username;
    $("session-role").textContent = `Usuario: ${sesion.usuario.username} · Rol: ${sesion.usuario.rol?.nombre || "Sin rol"}`;
    $("clientes-usuario").textContent = `${sesion.usuario.first_name || sesion.usuario.username} · ${sesion.usuario.rol?.nombre || "Personal"}`;
    // Refrescar datos del directorio si estaba abierto en administración.
    if (sesion.usuario.rol?.codigo === "ADMIN") window.SIGEPClientes?.actualizar();
  }

  function abrirPerfil(origen) {
    if (!sesion) return;
    origenPerfil = origen;
    for (const id of ["session-panel", "clientes-panel", "catalogo-visitante-panel", "auth-card"]) $(id).classList.add("hidden");
    $("perfil-panel").classList.remove("hidden");
    window.SIGEPPerfil?.mostrar();
  }

  function volverPerfil() {
    $("perfil-panel").classList.add("hidden");
    $(origenPerfil).classList.remove("hidden");
    origenPerfil = "session-panel";
  }

  $("perfil-abrir-sesion").addEventListener("click", () => abrirPerfil("session-panel"));
  $("perfil-abrir-personal").addEventListener("click", () => abrirPerfil("clientes-panel"));
  $("perfil-volver").addEventListener("click", volverPerfil);

  function cambiarVistaSIGEP(vista) {
    $("sigep-vista-clientes").hidden = vista !== "clientes";
    $("sigep-vista-usuarios").hidden = vista !== "usuarios";
    $("sigep-vista-productos").hidden = vista !== "productos";
    $("sigep-vista-pedidos").hidden = vista !== "pedidos";
    $("sigep-vista-inventario").hidden = vista !== "inventario";
    for (const nombre of ["clientes", "usuarios", "productos", "pedidos", "inventario"]) {
      const boton = $(`sigep-tab-${nombre}`);
      boton.classList.toggle("sigep-tab-active", vista === nombre);
      boton.setAttribute("aria-selected", String(vista === nombre));
    }
    if (vista === "usuarios") window.SIGEPUsuarios?.actualizar();
    if (vista === "productos") window.SIGEPProductos?.actualizar();
    if (vista === "pedidos") window.SIGEPPedidos?.actualizar();
    if (vista === "inventario") window.SIGEPInventario?.actualizar();
  }

  $("sigep-tab-clientes").addEventListener("click", () => cambiarVistaSIGEP("clientes"));
  $("sigep-tab-usuarios").addEventListener("click", () => cambiarVistaSIGEP("usuarios"));
  $("sigep-tab-productos").addEventListener("click", () => cambiarVistaSIGEP("productos"));
  $("sigep-tab-pedidos").addEventListener("click", () => cambiarVistaSIGEP("pedidos"));
  $("sigep-tab-inventario").addEventListener("click", () => cambiarVistaSIGEP("inventario"));

  function abrirCatalogo(origen) {
    origenCatalogo = origen;
    for (const id of ["auth-card", "session-panel", "clientes-panel"]) $(id).classList.add("hidden");
    $("catalogo-visitante-panel").classList.remove("hidden");
    $("catalogo-logout").hidden = !sesion;
    $("catalogo-volver").textContent = origen === "invitado" ? "Iniciar sesión" : "Volver al panel";
    window.SIGEPCatalogo?.mostrar("catalogo-visitante-contenido");
  }

  function volverCatalogo() {
    window.SIGEPCatalogo?.cerrarDetalle();
    $("catalogo-visitante-panel").classList.add("hidden");
    if (!sesion || origenCatalogo === "invitado") $("auth-card").classList.remove("hidden");
    else if (origenCatalogo === "administracion") $("clientes-panel").classList.remove("hidden");
    else {
      $("session-panel").classList.remove("hidden");
      if (sesion.usuario?.rol?.codigo === "CLIENTE") window.SIGEPCatalogo?.mostrar("catalogo-en-sesion");
    }
    origenCatalogo = null;
  }

  $("catalogo-abrir-visitante").addEventListener("click", () => abrirCatalogo("invitado"));
  $("catalogo-abrir-panel").addEventListener("click", () => abrirCatalogo("administracion"));
  $("catalogo-abrir-sesion").addEventListener("click", () => abrirCatalogo("sesion"));
  $("catalogo-volver").addEventListener("click", volverCatalogo);

  function cerrarSesionLocal() {
    sesion = null;
    borrarTokens();
    if (temporizadorRenovacion !== null) clearTimeout(temporizadorRenovacion);
    temporizadorRenovacion = null;
    window.SIGEPPerfil?.detener();
    window.SIGEPClientes?.detener();
    window.SIGEPUsuarios?.detener();
    window.SIGEPProductos?.detener();
    window.SIGEPPedidos?.detener();
    window.SIGEPInventario?.detener();
    window.SIGEPCatalogo?.cerrarDetalle();
    origenCatalogo = null;
    $("catalogo-visitante-panel").classList.add("hidden");
    $("session-panel").classList.remove("catalogo-sesion-activa");
    $("catalogo-en-sesion").classList.add("hidden");
    $("clientes-panel").classList.add("hidden");
    $("perfil-panel").classList.add("hidden");
    $("session-panel").classList.add("hidden");
    $("auth-card").classList.remove("hidden");
    $("login-password").value = "";
  }

  $("login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    limpiarAviso("login-message");
    const username = $("login-email").value.trim();
    const password = $("login-password").value;
    if (!username || !password) return aviso("login-message", "Ingresa tu correo/usuario y contraseña.");

    enEspera("login-submit", true, "Verificando...", "Iniciar sesión");
    try {
      const tokens = await peticion("/auth/login/", "POST", { username, password });
      if (!tokens?.access || !tokens?.refresh) throw new Error("La API no devolvió los tokens esperados.");
      const perfil = await peticion("/usuarios/me/", "GET", null, tokens.access);
      sesion = { access: tokens.access, refresh: tokens.refresh, usuario: perfil };
      guardarTokens();
      programarRenovacion();
      $("login-password").value = "";
      mostrarSesion(perfil);
    } catch (error) {
      aviso("login-message", error.message);
    } finally {
      enEspera("login-submit", false, "Verificando...", "Iniciar sesión");
    }
  });

  $("register-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    limpiarAviso("register-message");

    const password = $("register-password").value;
    const password_confirm = $("register-password-confirm").value;
    if (password !== password_confirm) {
      return aviso("register-message", "Las contraseñas no coinciden.");
    }

    const datos = {
      first_name: $("register-name").value.trim(),
      last_name: $("register-lastname").value.trim(),
      username: $("register-username").value.trim(),
      email: $("register-email").value.trim(),
      telefono: $("register-phone").value.trim(),
      direccion: $("register-address").value.trim(),
      password,
      password_confirm
    };

    enEspera("register-submit", true, "Creando cuenta...", "Crear cuenta");
    try {
      await peticion("/auth/register/", "POST", datos);
      $("register-form").reset();
      showLogin();
      $("login-email").value = datos.email;
      aviso("login-message", "Cuenta de cliente creada. Ya puedes iniciar sesión.", true);
    } catch (error) {
      aviso("register-message", error.message);
    } finally {
      enEspera("register-submit", false, "Creando cuenta...", "Crear cuenta");
    }
  });

  async function cerrarSesion(boton) {
    if (!sesion) return cerrarSesionLocal();
    boton.disabled = true;
    try {
      // Si el access expiró, se renueva ANTES del logout para revocar
      // el refresh más reciente (con ROTATE_REFRESH_TOKENS activado).
      const vence = vencimientoAccess(sesion.access);
      if (vence !== null && vence <= Date.now()) await renovarSesion();
      if (sesion) {
        const { access, refresh } = sesion;
        await peticion("/auth/logout/", "POST", { refresh }, access, false);
      }
    } catch (error) {
      console.warn("No fue posible revocar el refresh token:", error.message);
    } finally {
      boton.disabled = false;
      cerrarSesionLocal();
    }
  }
  $("logout-button").addEventListener("click", () => cerrarSesion($("logout-button")));
  $("clientes-logout-button").addEventListener("click", () => cerrarSesion($("clientes-logout-button")));
  $("catalogo-logout").addEventListener("click", () => cerrarSesion($("catalogo-logout")));

  $("forgot-password").addEventListener("click", (event) => {
    event.preventDefault();
    aviso("login-message", "La recuperación de contraseña todavía no está implementada. Contacta al administrador.");
  });

  // Recuperar la sesión al refrescar F5 o Ctrl+F5. No confiar en datos de rol guardados.
  async function restaurarSesion() {
    const tokens = leerTokens();
    if (!tokens) return;
    $("auth-card").classList.add("hidden");
    sesion = { ...tokens, usuario: null };
    try {
      // Si el access venció, peticion() renueva JWT automáticamente al recibir 401.
      const perfil = await peticionAutenticada("/usuarios/me/");
      if (!sesion) return; // Puede haberse invalidado la sesión durante el refresh.
      sesion.usuario = perfil;
      guardarTokens();
      programarRenovacion();
      mostrarSesion(perfil);
    } catch (error) {
      if ([400, 401, 403].includes(error.status) || !sesion) {
        cerrarSesionLocal();
        aviso("login-message", "La sesión expiró o fue revocada. Inicia sesión nuevamente.");
      } else {
        // Mantener tokens si se cortó Internet; el usuario puede recargar y reintentar.
        sesion = null;
        $("auth-card").classList.remove("hidden");
        aviso("login-message", "No se pudo verificar la sesión. Revisa la conexión y recarga la página.");
      }
    }
  }

  void restaurarSesion();
})();
