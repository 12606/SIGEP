# SIGEP · Backend Django REST API — Fase 1 completa

Esta version amplia el backend original **sin cambiar los modelos Rol/Usuario**. Incluye login JWT, refresco con rotacion, logout, perfil, gestion de usuarios y permisos, y pruebas automatizadas.

## Lo que trae
- `POST /api/auth/login/` – `username` + `password` → `access` y `refresh`.
- `POST /api/auth/refresh/` – rota el `refresh`; guarda el **nuevo** token que devuelve.
- `POST /api/auth/logout/` – requiere `Authorization: Bearer <access>` y `{"refresh":"..."}`. Revoca el refresh proporcionado.
- `GET /api/usuarios/me/` – obtiene perfil del token.
- `GET /api/roles/` – muestra roles, solo ADMIN.
- `GET /api/usuarios/` – lista empleados, solo ADMIN.
- `POST /api/usuarios/` – crea empleado, solo ADMIN.
- `GET /api/usuarios/<id>/` – detalle, solo ADMIN.
- `PATCH /api/usuarios/<id>/` – modifica datos, rol y/o contraseña, solo ADMIN.
- `PATCH /api/usuarios/<id>/estado/` – activa o desactiva, solo ADMIN.
- `GET /api/health/` – prueba API y conexión SQL.
- `GET /admin/` – panel Django (requiere `is_staff`).

**Importante:** no se implementa registro publico, eliminacion fisica de usuarios, ni reseteo de contraseña por email. El access token sigue vigente hasta que caduque (15 min) tras logout; solo se revoca el refresh. Para roles funcionales ADMIN se exige `rol=ADMIN` activo o `is_superuser`; `is_staff` por si solo no otorga permisos administrativos en la API.

## 1. Integracion con tu repositorio

1. Si aun no existe, crea rama desde la raiz `SIGEP`:
   ```powershell
   git switch -c feature/backend-auth
   ```
   Si ya existe, usa `git switch feature/backend-auth`; no intentes crearla dos veces.
2. **Haz copia de tu `backend` actual y no sobrescribas tu archivo `.env`**, ni tus migraciones `usuarios/migrations/0001_initial.py` si ya las generaste. Puedes copiar los archivos del ZIP del directorio `backend/` al de tu repositorio conservando `.env`, `.venv` y las migraciones ya aplicadas.
3. Abre `backend` en VS Code y activa `.venv`:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```
4. Si aun no tienes `.env`, ejecuta `Copy-Item .env.example .env` y edita variables. Genera una nueva clave secreta de Django:
   ```powershell
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

## 2. MariaDB local (HeidiSQL)

Se adapta a tu conexion de Windows: BD `sigep`, host `127.0.0.1`, puerto `3306`. Si por ahora conectas como root, usa temporalmente `DB_USER=root` y tu contraseña real de MariaDB. Es mejor crear `sigep_app` con permisos exclusivamente sobre la BD `sigep`. No pongas contraseñas reales en GitHub ni mandes `.env` por chat.

Ejemplo sin secretos:
```dotenv
DB_ENGINE=mariadb
DB_NAME=sigep
DB_USER=sigep_app
DB_PASSWORD=TU_CONTRASENA_PRIVADA
DB_HOST=127.0.0.1
DB_PORT=3306
```

Docker/compose sigue disponible como **alternativa opcional**, en ese caso MariaDB queda publicado en `3307` y cambia `DB_PORT=3307`.

## 3. Migraciones: conserva tu base existente

Desde `backend` y con MariaDB disponible:
```powershell
python manage.py check
python manage.py makemigrations usuarios
python manage.py migrate
python manage.py seed_roles
python manage.py runserver
```

`makemigrations usuarios` no debe borrar tus usuarios. La instalacion del blacklist crea tablas adicionales mediante migraciones de SimpleJWT. Si Django detecta conflictos con migraciones ya existentes, NO borres tablas o migraciones sin revisar; comparte el error.

Si no creaste superusuario: `python manage.py createsuperuser`, luego `python manage.py seed_roles`.

## 4. Prueba rapida del login en PowerShell

Servidor encendido en otra terminal: `python manage.py runserver`.

```powershell
$base = "http://127.0.0.1:8000"
$login = Invoke-RestMethod -Uri "$base/api/auth/login/" -Method Post -ContentType "application/json" -Body (@{username="admin"; password="PON_AQUI_TU_CLAVE"} | ConvertTo-Json)
$headers = @{ Authorization = "Bearer $($login.access)" }
Invoke-RestMethod -Uri "$base/api/usuarios/me/" -Headers $headers
Invoke-RestMethod -Uri "$base/api/roles/" -Headers $headers
```

Crear un VENTAS (admin):
```powershell
$body = @{ username="empleado01"; email="empleado01@example.com"; first_name="Ana"; last_name="Lopez"; telefono="3312345678"; password="ClaveEmpleado!2026"; rol_codigo="VENTAS" } | ConvertTo-Json
Invoke-RestMethod -Uri "$base/api/usuarios/" -Method Post -ContentType "application/json" -Headers $headers -Body $body
```

Actualizar (sustituye `1` por el id del empleado):
```powershell
Invoke-RestMethod -Uri "$base/api/usuarios/1/" -Method Patch -ContentType "application/json" -Headers $headers -Body '{"telefono":"3311111111"}'
Invoke-RestMethod -Uri "$base/api/usuarios/1/estado/" -Method Patch -ContentType "application/json" -Headers $headers -Body '{"activo":false}'
```

Cerrar sesion (usar ultimo refresh, tras cualquier llamada a refresh):
```powershell
Invoke-RestMethod -Uri "$base/api/auth/logout/" -Method Post -ContentType "application/json" -Headers $headers -Body (@{refresh=$login.refresh} | ConvertTo-Json)
```

## 5. Pruebas automatizadas sin tocar MariaDB

Con tu `.env` local intacto, el siguiente comando utiliza una BD SQLite temporal y se borra al finalizar las pruebas:
```powershell
$env:DB_ENGINE="sqlite"
python manage.py test usuarios -v 2
Remove-Item Env:DB_ENGINE
```

En SQLite, Django crea automaticamente la BD de test y luego la elimina. Comprueba que todos los tests terminen en `OK`.

## 6. Guardar y subir a tu rama

Desde raiz del repositorio:
```powershell
git status
git add backend
git commit -m "feat: cerrar primera fase de autenticacion y CRUD de usuarios"
git push -u origin feature/backend-auth
```

`git status` no debe mostrar `.env`, `.venv`, credenciales ni la BD real.

## 7. Seguridad y limites de la fase

- Los hashes de contrasena se crean con `create_user` y `set_password` (Django).
- Los cambios de rol solo los hace un ADMIN de SIGEP.
- La baja es logica (`is_active=False`), no borra historiales.
- No se puede desactivar el usuario actual ni un superusuario por la API de estado.
- Token `access` 15 min; token `refresh` 7 dias, con rotacion y blacklist.
- El refresh usado en login **no sirve despues** de llamar a refresh; reemplazalo por el nuevo.
- Este backend se destina a desarrollo local. Para produccion usar HTTPS, DEBUG=False, control de acceso al servicio, proteccion anti brute-force/rate limiting y gestion de secretos.
