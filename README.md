# SIGEP — Pastelería Dulce Encanto · Proyecto web integrado


## Archivos

```text
SIGEP/
  backend/
    config/                   # Configuración y URLs Django
    usuarios/                 # Rol, Usuario, registro, login, CRUD y pruebas
    pruebas/SIGEP_API.http    # Peticiones de ejemplo
    manage.py
    requirements.txt
    .env.example              # Plantilla, NO contiene claves reales
  frontend/
    index.html                # Diseño Dulce Encanto (Django template)
    app.js                    # Login, registro, perfil, logout
  SIGEP.code-workspace
  .gitignore
  README.md
```

## Ejecutar en tu equipo (resumen)

1. **Haz respaldo** de tu repositorio antes de copiar archivos, y conserva `backend/.env`, `backend/.venv` y `backend/usuarios/migrations/` si ya hiciste migraciones.
2. Abre el repo con `SIGEP.code-workspace` o desde la raíz en VS Code.
3. En una terminal PowerShell:

```powershell
cd C:\Users\Fercu\Documents\GitHub\SIGEP\backend
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py check
python manage.py makemigrations usuarios
python manage.py migrate
python manage.py seed_roles
python manage.py runserver
```

4. Entra a **http://127.0.0.1:8000/**. El login y el registro harán llamadas a `/api/...` en el mismo servidor.
5. Prueba `http://127.0.0.1:8000/api/health/` para verificar también MariaDB.

### Variables `.env` para MariaDB local

Copia `backend/.env.example` como `backend/.env`, **solo si todavía no tienes `.env`**. Para la base de datos local que muestras en HeidiSQL:

```dotenv
DB_ENGINE=mariadb
DB_NAME=sigep
DB_USER=root
DB_PASSWORD=TU_CONTRASENA_REAL
DB_HOST=127.0.0.1
DB_PORT=3306
```

El uso de `root` es solo una opción de desarrollo; es mejor crear `sigep_app` con acceso exclusivo a la BD. Define también una `DJANGO_SECRET_KEY` única. Nunca subas `.env` a Git. No ejecutes Docker si estás usando MariaDB local.


### Qué funciona

- `GET /` — página principal Dulce Encanto;
- `POST /api/auth/register/` — alta pública de cuentas **CLIENTE** (nunca ADMIN);
- `POST /api/auth/login/` — usuario/correo y contraseña, devuelve JWT;
- `GET /api/usuarios/me/` — perfil con access token;
- `POST /api/auth/refresh/` y `/api/auth/logout/` — refresco y revocación del refresh;
- `GET /api/usuarios/`, `POST /api/usuarios/`, `GET/PATCH /api/usuarios/<id>/`, `PATCH /api/usuarios/<id>/estado/` — empleados, solo ADMIN;
- `GET /api/roles/` — roles, solo ADMIN.

### Pruebas automáticas (SQLite temporal; no toca MariaDB)

```powershell
$env:DB_ENGINE="sqlite"
python manage.py test usuarios -v 2
Remove-Item Env:DB_ENGINE
```

El `access` JWT se conserva en memoria del navegador; recargar la página cierra la sesión visual. Esto es un **prototipo local**, no un despliegue de producción. En producción deben añadirse HTTPS, cookies HttpOnly/CSRF, validación de correo y mecanismos antiabuso. El enlace de contraseña olvidada es informativo, sin envío de correo todavía.


