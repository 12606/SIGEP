# 02 · Git para SIGEP: ramas e integración SIN perder cambios

## Regla principal

**Las ramas pertenecen al repositorio SIGEP, NO a una carpeta.** Si te encuentras dentro de `SIGEP/frontend` y cambias de rama, cambias los archivos **de todo el proyecto**, incluido `backend`. No hay que mantener una rama activa para backend y otra activa para frontend en la misma copia del repositorio.

## Mapa de trabajo

```text
main  (versión estable)
 ├─ feature/backend-auth   (trabajo histórico: API y usuarios)
 ├─ feature/frontend-auth  (trabajo histórico: HTML y login)
 └─ feature/integracion-web (unificar y probar; esta guía)
        │
        └─ Pull Request → main
```

## A. ANTES DE EMPEZAR, guarda lo que ya cambiaste

Abre una terminal en la raíz del repo y averigua dónde estás:

```powershell
cd C:\Users\Fercu\Documents\GitHub\SIGEP
git branch --show-current
git status
```

Si `git status` muestra cambios sin guardar y quieres conservarlos, primero **haz un commit en la rama actual**:

```powershell
git add backend frontend
git status
# Revisa cuidadosamente los archivos listados: NO incluyas secretos .env ni .venv.
git commit -m "chore: respaldar avance actual antes de integrar SIGEP"
git push
```

Si `git push` dice que la rama no tiene upstream, ejecuta `git push -u origin NOMBRE-DE-TU-RAMA`. Si hay cambios fuera de backend/frontend, revísalos antes del commit.

No uses `git reset --hard`, `git clean -fd`, `git restore .` ni `git push --force` para resolver este proceso.

## B. Crear UNA rama para la integración (recomendado)

Cuando `git status` no tenga cambios:

```powershell
git fetch origin
git switch main
git pull --ff-only origin main
git switch -c feature/integracion-web
```

Si ya existía la rama de integración, utiliza `git switch feature/integracion-web` en lugar de crearla otra vez.

Integra primero el backend:

```powershell
git merge feature/backend-auth
```

Y luego el frontend (si ya existe y tiene commits que conservar):

```powershell
git merge feature/frontend-auth
```

Si alguna rama solo existe en remoto: `git merge origin/feature/backend-auth` o `git merge origin/feature/frontend-auth` después de `git fetch origin`.

Si Git dice `Already up to date`, no es error. Si aparece un conflicto, abre el panel **Source Control** de VS Code para resolverlo; después ejecuta `git add <archivo>` y `git commit`. No borres archivos indiscriminadamente.

**Si aún no creaste feature/frontend-auth**, omite su `git merge`. No necesitas crearla obligatoriamente; puedes trabajar directamente en la rama de integración.

## C. Copia el ZIP unificado al repo

Extrae el ZIP en una ubicación temporal; copia al directorio `SIGEP` los archivos y carpetas del ZIP. Conserva `backend/.env`, `.venv` y tus migraciones `usuarios/migrations/` (no vienen en ZIP). Esta acción actualiza el proyecto *después* de unir las ramas.

## D. Comprueba el sistema antes de subirlo

Abre `SIGEP.code-workspace` y realiza los pasos de `docs/01_INSTALACION_Y_PRUEBAS.md`. Verifica:

1. `python manage.py check` sin errores.
2. `python manage.py migrate` sin conflictos.
3. `python manage.py seed_roles` correcto.
4. http://127.0.0.1:8000/api/health/ responde OK.
5. http://127.0.0.1:8000/ muestra el login.
6. Login con superusuario y alta/login de un CLIENTE funcionan.
7. `python manage.py test usuarios` termina OK.

## E. Commit y push de integración

Desde la raíz SIGEP:

```powershell
git status
git add backend frontend docs README.md .gitignore .gitattributes SIGEP.code-workspace
git status
# Asegúrate de que NO aparezcan .env, .venv ni claves de acceso.
git commit -m "feat: integrar frontend web y backend Django de SIGEP"
git push -u origin feature/integracion-web
```

Si no hubo cambios, Git dirá `nothing to commit` y puedes continuar. En GitHub crea un **Pull Request** de `feature/integracion-web` → `main` y, una vez revisado, haz **Merge**.

## F. Después, una rama por funcionalidad

Con el PR integrado:

```powershell
git switch main
git pull --ff-only origin main
git switch -c feature/clientes
```

Al terminar clientes: commit, push, PR → main. Después `feature/productos`, etc.

### Mini glosario

- **main**: versión consolidada.
- **feature/...**: rama temporal para una funcionalidad.
- **commit**: guarda un conjunto de cambios en la rama actual.
- **push**: sube commits a GitHub, pero no modifica automáticamente `main`.
- **Pull Request**: petición de revisión para integrar una rama en `main`.
- **merge**: combina historiales de ramas.

## Nota sobre base de datos

Git no guarda los registros de MariaDB ni las claves de `.env`. Hacer merge entre ramas no migra tu BD; por eso debes ejecutar `python manage.py migrate` después de cambiar código que introduce migraciones.
