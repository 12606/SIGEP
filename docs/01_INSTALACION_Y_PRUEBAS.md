# 01 · Instalar SIGEP unificado en Windows

## 0. Haz respaldo antes de copiar

Cierra Django. En el Explorador de archivos, copia `C:\Users\Fercu\Documents\GitHub\SIGEP` a una carpeta de respaldo, **fuera del repositorio**. No copies `.venv` si ocupa demasiado, pero conserva `backend/.env` y `backend/usuarios/migrations/`.

Extrae el ZIP en una carpeta temporal (por ejemplo Descargas). El ZIP tiene `backend`, `frontend`, `docs`, `README.md`, `.gitignore` y `SIGEP.code-workspace` en su raíz. **Copia esos elementos** a tu repositorio ya existente `SIGEP`, combinando carpetas. No copies la carpeta extraída como `SIGEP/SIGEP`.

Si Windows pide reemplazar `.env`, `.venv` o los archivos de `usuarios/migrations`, **no lo hagas**. De hecho, el ZIP no contiene esos archivos privados ni migraciones numeradas.

## 1. Abre VS Code

Abre `SIGEP.code-workspace`. Verás las carpetas backend y frontend al mismo tiempo.

## 2. Activa entorno Python

Terminal dentro de `backend`:

```powershell
cd C:\Users\Fercu\Documents\GitHub\SIGEP\backend
.\.venv\Scripts\Activate.ps1
python --version
python -m pip install -r requirements.txt
```

Si no existe `.venv`:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## 3. Configura MariaDB (HeidiSQL)

Copia `.env.example` a `.env` solo si no tenías uno:

```powershell
Copy-Item .env.example .env
```

Abre `.env` y establece **tu propia** contraseña de MariaDB. `DB_HOST=127.0.0.1`, `DB_PORT=3306`, `DB_NAME=sigep` si corresponde con tu sesión real de HeidiSQL. No confundas nombre de sesión HeidiSQL con nombre de base de datos.

Genera `DJANGO_SECRET_KEY` con:

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## 4. Tablas y roles

```powershell
python manage.py check
python manage.py makemigrations usuarios
python manage.py migrate
python manage.py seed_roles
```

Si ya tenías migraciones, revisa que `makemigrations` diga «No changes detected». Si Django propone operaciones inesperadas o hay conflictos, NO borres la base de datos: detente y revisa las migraciones existentes.

Si no tienes superusuario:

```powershell
python manage.py createsuperuser
python manage.py seed_roles
```

## 5. Ejecuta TODO con Django (una sola terminal de servidor)

```powershell
python manage.py runserver 127.0.0.1:8000
```

En navegador abre:

- **Web:** http://127.0.0.1:8000/
- **Prueba API + BD:** http://127.0.0.1:8000/api/health/
- **Panel admin:** http://127.0.0.1:8000/admin/

**IMPORTANTE:** NO uses `http://127.0.0.1:5500/` ni abras `frontend/index.html` con `file://` para esta versión. Ahora `index.html` es un template Django y su `app.js` se sirve desde `/static/app.js`.

## 6. Prueba de login

Usa usuario/contraseña de superusuario o registra una cuenta CLIENTE desde el formulario.

Si falla, abre F12 > Red / Network y anota el código HTTP y la ruta. Si la web carga pero login falla, la solicitud es `POST /api/auth/login/`. Si `/api/health/` no abre, revisa la terminal Django y MariaDB.

## 7. Prueba automática sin tocar MariaDB

En otra terminal dentro de `backend` con venv activo:

```powershell
$env:DB_ENGINE="sqlite"
python manage.py test usuarios -v 2
Remove-Item Env:DB_ENGINE
```

## 8. Problemas frecuentes

- `OperationalError 2002 ... (10061)`: comprueba servicio MariaDB y `Test-NetConnection 127.0.0.1 -Port 3306`.
- `Access denied for user`: usuario o contraseña de MariaDB equivocada.
- `Unknown database 'sigep'`: crea la BD en HeidiSQL o corrige DB_NAME.
- `404 /`: faltó copiar `frontend/index.html` o `config/urls.py` del ZIP.
- `TemplateDoesNotExist index.html`: deben existir `SIGEP/backend` y `SIGEP/frontend` como carpetas **hermanas**.
- `404 /static/app.js`: revisa la línea STATICFILES_DIRS en settings y que exista frontend/app.js.
- `401 /api/auth/login/`: credenciales erróneas o usuario inactivo.
- `400 /api/auth/register/`: puede ser correo repetido, campos incorrectos, contraseña débil.
- `503 /api/auth/register/`: ejecuta `python manage.py seed_roles` para crear CLIENTE.

## 9. Alcance

Aún no hay módulos de pedidos, catálogo, facturación ni recuperación real de contraseña. Solo portal de acceso y gestión de usuarios (API).
