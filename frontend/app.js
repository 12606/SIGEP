/* SIGEP · Dulce Encanto. Integración inicial con Django REST Framework.
   Los tokens JWT permanecen solo en memoria y se pierden al recargar la pestaña.
   Para producción: autenticación con cookies HttpOnly, HTTPS y protección CSRF. */
(() => {
  "use strict";

  // La web se abre desde Django en http://127.0.0.1:8000/.
  // Usar ruta relativa evita errores CORS o puertos inconsistentes.
  const API_BASE = "/api";
  const $ = (id) => document.getElementById(id);
  let sesion = null;

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

  async function peticion(ruta, metodo = "GET", datos = null, access = null) {
    const headers = { "Accept": "application/json" };
    if (datos !== null) headers["Content-Type"] = "application/json";
    if (access) headers.Authorization = `Bearer ${access}`;

    let response;
    try {
      response = await fetch(`${API_BASE}${ruta}`, {
        method: metodo,
        headers,
        body: datos !== null ? JSON.stringify(datos) : undefined,
        credentials: "omit",
        cache: "no-store"
      });
    } catch (err) {
      throw new Error("No se pudo conectar a SIGEP. Abre la web desde http://127.0.0.1:8000/ y verifica que Django esté encendido.");
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
      throw new Error(partes.join(" · ") || `La solicitud falló (HTTP ${response.status}).`);
    }
    return payload;
  }

  function mostrarSesion(usuario) {
    $("auth-card").classList.add("hidden");
    $("session-panel").classList.remove("hidden");
    const nombre = [usuario.first_name, usuario.last_name].filter(Boolean).join(" ");
    $("session-name").textContent = nombre || usuario.username;
    $("session-role").textContent = `Usuario: ${usuario.username} · Rol: ${usuario.rol?.nombre || "Sin rol"}`;
  }

  function cerrarSesionLocal() {
    sesion = null;
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
      sesion = { access: tokens.access, refresh: tokens.refresh };
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

  $("logout-button").addEventListener("click", async () => {
    if (!sesion) return cerrarSesionLocal();
    const { access, refresh } = sesion;
    $("logout-button").disabled = true;
    try {
      await peticion("/auth/logout/", "POST", { refresh }, access);
    } catch (error) {
      // Aunque falle la revocación, borramos la sesión local.
      // Si el access expiró, el refresh puede seguir válido en el servidor.
      console.warn("No fue posible revocar el token de renovación:", error.message);
    } finally {
      $("logout-button").disabled = false;
      cerrarSesionLocal();
    }
  });

  $("forgot-password").addEventListener("click", (event) => {
    event.preventDefault();
    aviso("login-message", "La recuperación de contraseña todavía no está implementada. Contacta al administrador.");
  });
})();
