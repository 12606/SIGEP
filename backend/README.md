# SIGEP — Backend Django (primera etapa: autenticacion)

Este ZIP esta pensado para copiar la carpeta `backend` dentro del repositorio `SIGEP`. **No sobrescribas tus otros archivos sin revisar**. Los datos son para desarrollo local; no subir `.env` a GitHub.

## 1. Crear rama desde la raiz del repositorio
```powershell
cd C:\Users\Fercu\Documents\GitHub\SIGEP
git switch -c feature/backend-auth
```

## 2. Preparar VS Code y entorno virtual
Abre la carpeta `backend` en VS Code, y en la terminal PowerShell:
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```
Edita `.env` y sustituye las tres contrasenas/secretos de demostracion. Crea una SECRET_KEY segura con:
```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## 3. MariaDB en Docker
Abre Docker Desktop y ejecuta desde backend:
```powershell
docker compose up -d
docker compose ps
```
El host de la BD para Django es `127.0.0.1` y el puerto es `3307`, para no interferir con MariaDB instalado localmente en `3306`.

## 4. Migraciones y superusuario
```powershell
python manage.py makemigrations usuarios
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_roles
python manage.py runserver
```
En `createsuperuser`, elige un nombre de usuario, correo y contrasena. Django usa el nombre de usuario para iniciar sesion.

## 5. API
- `GET http://127.0.0.1:8000/api/health/`: prueba de conexion
- `POST http://127.0.0.1:8000/api/auth/login/`: `{ "username": "admin", "password": "..." }`
- `POST http://127.0.0.1:8000/api/auth/refresh/`: `{ "refresh": "..." }`
- `GET http://127.0.0.1:8000/api/usuarios/me/`: `Authorization: Bearer <access>`
- `GET/POST http://127.0.0.1:8000/api/usuarios/`: solo administradores Django (`is_staff=True`)
- `GET http://127.0.0.1:8000/admin/`: interfaz administrativa de Django

Para crear un usuario desde `/api/usuarios/` usa el token del superusuario. Ejemplo del cuerpo JSON:
```json
{
  "username": "cajero1", "email": "cajero1@example.com", "first_name": "Ana",
  "last_name": "Gomez", "telefono": "3312345678", "password": "ClaveSegura!2026", "rol_id": 2
}
```
Consulta los IDs reales en la vista `/admin/` > Roles; no des por hecho que VENTAS es el 2.

## 6. Pruebas automatizadas sin MariaDB (opcional)
```powershell
$env:DB_ENGINE="sqlite"
python manage.py test usuarios
Remove-Item Env:DB_ENGINE
```

## 7. Guardar la rama
Desde la carpeta raiz del repositorio:
```powershell
git status
git add backend
git commit -m "feat: base de API Django y login JWT con MariaDB"
git push -u origin feature/backend-auth
```

## Notas de seguridad
- Nunca subas `backend/.env`, `.venv` ni volumenes de bases de datos al repositorio.
- Solo administradores pueden crear cuentas. No hay registro publico.
- En esta version la autenticacion es por `username` y contrasena.
- `is_staff` habilita el acceso al admin de Django; `rol` es el rol funcional de SIGEP.
- Ejecuta la API solo en tu equipo durante desarrollo. Para produccion deberas configurar HTTPS, DEBUG=False, rotacion/revocacion de tokens y permisos estrictos.
