# SIGEP · Frontend web (Dulce Encanto)

Se conserva el diseño HTML/Tailwind que proporcionaste y se conecta con la API Django.

## Ejecutar
1. Inicia Django en otra terminal: `cd backend`, activa `.venv`, `python manage.py runserver`.
2. En la carpeta `frontend`, ejecuta `py -m http.server 5500` (o `python -m http.server 5500`).
3. Abre `http://127.0.0.1:5500` en el navegador.
4. Asegúrate de tener Internet para Tailwind CDN y Google Fonts (solo en prototipo).

`app.js` define la dirección de la API (`http://127.0.0.1:8000/api`).

### Registro
El registro envía `username`, `email`, `first_name`, `last_name`, `password` y `password_confirm` a `POST /api/auth/register/`. La API asigna **CLIENTE** automáticamente. Un empleado ADMIN se crea solamente a través de un administrador autenticado.

### Login
Permite correo o nombre de usuario y contraseña. Si el login funciona, muestra una pantalla simple de bienvenida con el rol. El dashboard es una etapa posterior.

### Sesión
Los tokens JWT permanecen en memoria. Al recargar el navegador se termina la sesión local. Logout revoca el refresh si el access sigue vigente. **Producción:** utilizar HTTPS y cookies HttpOnly seguras, autenticación basada en cookies con CSRF y medidas adicionales de protección.

Nunca abras el HTML con doble clic (`file://`), porque la comunicación CORS está preparada para un servidor HTTP en el puerto 5500.
