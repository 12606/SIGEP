# Backend SIGEP (Django REST Framework)

**Empieza por el README en la raíz del repositorio**: `../README.md` y `../docs/01_INSTALACION_Y_PRUEBAS.md`.

Sirve la API en `/api/` y la web en `/`. La conexión con MariaDB se toma desde el `.env` **local**, que no debe subirse a Git.

Para iniciar:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py check
python manage.py makemigrations usuarios
python manage.py migrate
python manage.py seed_roles
python manage.py runserver
```

URL de inicio: http://127.0.0.1:8000/

Pruebas de Django con SQLite de prueba:

```powershell
$env:DB_ENGINE="sqlite"
python manage.py test usuarios -v 2
Remove-Item Env:DB_ENGINE
```

Modelos: `Rol`, `Usuario` (Django AbstractUser). JWT con SimpleJWT. Las cuentas públicas se crean solo con rol CLIENTE; los demás roles requieren administrador.
