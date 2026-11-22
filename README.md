# SIGEP — Sistema Integral de Gestión para una Pastelería

**Dulce Encanto** es una aplicación web para organizar las operaciones de una pastelería: clientes, catálogo de productos, pedidos, pagos, inventario de ingredientes y reportes administrativos.

El proyecto está desarrollado con **Django REST Framework, MariaDB, HTML, CSS y JavaScript**, e incluye autenticación JWT y permisos según el rol del usuario. Está pensado como un proyecto académico y una base ampliable para un sistema de gestión real.

> **Estado:** versión funcional para pruebas locales. No se entrega una base de datos con información de clientes ni credenciales predeterminadas. Antes de publicarlo en Internet, revisa las recomendaciones de [seguridad y despliegue](#seguridad-y-despliegue).

## Contenido

- [Funcionalidades](#funcionalidades)
- [Tecnologías](#tecnologías)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Requisitos](#requisitos)
- [Instalación local en Windows](#instalación-local-en-windows)
- [Opcional: MariaDB con Docker](#opcional-mariadb-con-docker)
- [Primer acceso y prueba rápida](#primer-acceso-y-prueba-rápida)
- [Pruebas automatizadas](#pruebas-automatizadas)
- [Endpoints principales](#endpoints-principales)
- [Solución de problemas](#solución-de-problemas)
- [Seguridad y despliegue](#seguridad-y-despliegue)

## Funcionalidades

| Módulo | Funciones principales |
| --- | --- |
| **Autenticación y usuarios** | Inicio de sesión, registro público de clientes, JWT, renovación de sesión, perfiles y administración de roles. |
| **Clientes** | Registro, consulta y actualización de fichas; búsqueda y activación/desactivación según permisos. |
| **Productos y catálogo** | Categorías, productos, precios, disponibilidad y catálogo visible para visitantes y clientes. |
| **Pedidos y pagos** | Solicitudes con varios productos, seguimiento de estados, anticipos, pagos registrados y saldos pendientes. |
| **Inventario** | Ingredientes, movimientos de entrada/salida/merma y alertas de existencias mínimas. |
| **Dashboard y reportes** | Indicadores de pedidos, cobros, saldos, productos solicitados, alertas y exportación CSV. |

### Roles

- **ADMIN:** administración de usuarios, clientes, productos, pedidos, inventario y reportes.
- **VENTAS:** atención de clientes y pedidos, y registro de cobros; sin administración de roles ni desactivación de cuentas.
- **REPOSTERO:** consulta de producción, actualización de estados autorizados y consulta limitada de existencias.
- **ALMACEN:** gestión de ingredientes y movimientos de inventario conforme a sus permisos.
- **CLIENTE:** consulta del catálogo, gestión de su perfil y seguimiento de sus propios pedidos.

Las autorizaciones también se comprueban en la API: ocultar una opción en el navegador no sustituye los permisos del backend.

## Tecnologías

- **Backend:** Python, Django 5.2, Django REST Framework y SimpleJWT.
- **Base de datos:** MariaDB (a través del backend MySQL de Django).
- **Frontend:** HTML, CSS, JavaScript y Tailwind CSS en el prototipo de desarrollo.
- **Herramientas:** Git, VS Code, HeidiSQL (opcional) y Docker Compose (opcional para MariaDB).

## Estructura del proyecto

```text
SIGEP/
├── backend/
│   ├── config/              # Configuración principal de Django
│   ├── usuarios/            # Cuentas, roles y autenticación
│   ├── clientes/            # Gestión de clientes
│   ├── productos/           # Categorías, productos y catálogo
│   ├── pedidos/             # Pedidos y pagos
│   ├── inventario/          # Ingredientes y movimientos
│   ├── reportes/            # Indicadores y exportaciones
│   ├── manage.py
│   ├── requirements.txt
│   ├── .env.example
│   └── compose.yaml         # MariaDB opcional mediante Docker
├── frontend/                # Interfaz y archivos estáticos
├── docs/                    # Guías y manuales (si la fase 7 está integrada)
├── tools/                   # Validación y respaldos (fase 7)
├── SIGEP.code-workspace
└── README.md
```

**Importante:** en la instalación recomendada, **Django sirve tanto la interfaz como la API** desde `http://127.0.0.1:8000/`. No es necesario abrir `frontend/index.html` con `file://` ni iniciar Live Server.

## Requisitos

Para probar SIGEP de manera local:

1. **Python 3.12** recomendado (con `python` disponible en la terminal).
2. **Git**.
3. **MariaDB** en ejecución, local o mediante Docker.
4. Un navegador moderno y, opcionalmente, **VS Code** y **HeidiSQL**.
5. Acceso a Internet para instalar las dependencias y cargar algunos recursos visuales del prototipo.

Los comandos siguientes están pensados para **Windows con PowerShell**. Si usas Linux/macOS, consulta la nota [al final de la instalación](#nota-para-linux-o-macos).

## Instalación local en Windows

### 1. Clonar el repositorio

Abre PowerShell y ejecuta:

```powershell
git clone https://github.com/12606/SIGEP.git
cd SIGEP
```

Puedes abrir `SIGEP.code-workspace` en VS Code, si está disponible en la rama descargada.

### 2. Crear el entorno virtual e instalar dependencias

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Si PowerShell bloquea la activación, puedes habilitarla **solo para esa terminal** con:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Si `mysqlclient` no se instala en Windows, comprueba tu versión de Python y los requisitos de compilación del paquete. No elimines la dependencia ni cambies el motor de base de datos sin revisar primero el error.

### 3. Preparar MariaDB

**Opción A: MariaDB instalado localmente** (recomendada si ya lo usas con HeidiSQL).

Comprueba que el servicio esté iniciado y que escuche en `127.0.0.1:3306`. Con una cuenta administrativa de MariaDB, ejecuta este SQL **una sola vez**, cambiando la contraseña de ejemplo:

```sql
CREATE DATABASE IF NOT EXISTS sigep
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'sigep_app'@'127.0.0.1'
  IDENTIFIED BY 'CAMBIA_POR_UNA_CLAVE_SEGURA';

GRANT ALL PRIVILEGES ON sigep.* TO 'sigep_app'@'127.0.0.1';
```

Si el usuario `sigep_app` ya existe, comprueba su contraseña y permisos en lugar de suponer que el comando anterior los modificó.

**Opción B: Docker Compose.** Si prefieres no instalar MariaDB directamente, sigue [la opción Docker](#opcional-mariadb-con-docker) y utiliza el puerto `3307` en el `.env`.

### 4. Configurar variables de entorno

Desde la carpeta `backend/`, crea tu archivo privado de configuración:

```powershell
Copy-Item .env.example .env
```

Abre `backend/.env` y ajusta los valores a tu instalación. Ejemplo para **MariaDB local**:

```dotenv
DJANGO_SECRET_KEY=PEGA_AQUI_UN_SECRETO_GENERADO
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost

DB_ENGINE=mariadb
DB_NAME=sigep
DB_USER=sigep_app
DB_PASSWORD=TU_CONTRASENA_PRIVADA
DB_HOST=127.0.0.1
DB_PORT=3306
```

Genera una clave de Django con:

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copia el resultado en `DJANGO_SECRET_KEY`. **No subas `backend/.env` al repositorio ni publiques su contenido en capturas o incidencias.**

> **Atención a `DB_ENGINE`:** el valor `sqlite` se usa solo para pruebas. Si inicias el servidor con esa variable aún activa en PowerShell, podrías ver una base de datos vacía en lugar de tu MariaDB. Para desarrollo normal usa `mariadb` y comprueba la conexión antes de migrar.

### 5. Comprobar conexión y preparar las tablas

Con el entorno virtual activo y todavía en `backend/`:

```powershell
Remove-Item Env:DB_ENGINE -ErrorAction SilentlyContinue
python manage.py shell -c "from django.db import connection; d=connection.settings_dict; print('Motor:', d['ENGINE']); print('Base:', d['NAME']); print('Puerto:', d.get('PORT'))"
```

Para la opción local deberías obtener un motor `django.db.backends.mysql`, la base `sigep` y el puerto `3306`. **Verifica esos datos antes de migrar.**

```powershell
python manage.py check
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_roles
```

`migrate` crea o actualiza las tablas utilizando las migraciones incluidas. **No hace falta ejecutar `makemigrations` en una instalación limpia.** Si ya tienes información en una base existente, haz un respaldo antes de aplicar migraciones.

`createsuperuser` te pedirá los datos de la primera cuenta administrativa. `seed_roles` crea los roles de SIGEP y asigna `ADMIN` a superusuarios que aún no tienen rol. **No existe una contraseña de demostración predeterminada.**

### 6. Iniciar el servidor

```powershell
python manage.py runserver
```

Abre estas direcciones:

| Dirección | Uso |
| --- | --- |
| http://127.0.0.1:8000/ | Aplicación web Dulce Encanto |
| http://127.0.0.1:8000/admin/ | Panel administrativo de Django |
| http://127.0.0.1:8000/api/health/ | Comprobación de la API |

El frontend se conecta a `/api/` en el mismo servidor. Detén Django con `Ctrl+C` cuando termines.

### Nota para Linux o macOS

Los pasos de MariaDB y `.env` son los mismos, pero la creación y activación del entorno virtual cambia:

```bash
cd SIGEP/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Después continúa con `python manage.py migrate`, `python manage.py createsuperuser`, `python manage.py seed_roles` y `python manage.py runserver`, siempre verificando primero que la configuración apunte a la base correcta. Dependiendo del sistema, `mysqlclient` puede requerir paquetes de desarrollo de MariaDB/MySQL y un compilador C.

## Opcional: MariaDB con Docker

Este método sustituye **solo** la instalación local de MariaDB; Django sigue ejecutándose en el entorno virtual de Python.

1. Instala Docker Desktop y asegúrate de que esté iniciado.
2. Dentro de `backend/.env`, define las variables de base de datos y Docker:

```dotenv
DB_ENGINE=mariadb
DB_NAME=sigep
DB_USER=sigep_app
DB_PASSWORD=TU_CONTRASENA_PRIVADA
DB_HOST=127.0.0.1
DB_PORT=3307
DB_ROOT_PASSWORD=OTRA_CONTRASENA_PRIVADA
DOCKER_DB_PORT=3307
```

3. Desde `backend/`, inicia únicamente MariaDB:

```powershell
docker compose up -d db
```

4. Espera a que el servicio esté listo, y continúa con el **paso 5** de instalación (`check`, `migrate`, `createsuperuser` y `seed_roles`).

Docker expone MariaDB en `127.0.0.1:3307` para evitar conflictos con una instalación local en `3306`. **No inicies ambos métodos si no necesitas dos servidores de base de datos.** Los datos de Docker se conservan en un volumen; no uses `docker compose down -v` si deseas conservarlos.

## Primer acceso y prueba rápida

Al iniciar SIGEP por primera vez, los catálogos y pedidos pueden estar vacíos: **el repositorio no incluye datos reales ni cuentas demo**.

1. Entra con el superusuario creado y comprueba que tenga el rol `ADMIN`.
2. Desde el panel administrativo, crea una categoría y un producto.
3. Abre una sesión privada del navegador y registra una cuenta `CLIENTE` desde el formulario público.
4. Comprueba que el cliente puede consultar el catálogo y registrar un pedido.
5. Vuelve al panel administrativo para revisar el pedido y registrar un pago de prueba.
6. Registra un ingrediente y movimientos de inventario con un usuario autorizado.
7. Consulta el dashboard y los reportes desde una cuenta `ADMIN`.

El módulo de pagos **registra cobros y anticipos**; no debe confundirse con una pasarela para cobrar tarjetas en Internet. El inventario registra movimientos; el consumo automático por receta no forma parte de esta versión base.

La sesión JWT se puede recuperar al actualizar la **misma pestaña** cuando está integrado el ajuste de persistencia. Cerrar sesión elimina los tokens almacenados. No se garantiza que la sesión persista después de cerrar la pestaña.

## Pruebas automatizadas

**Las pruebas deben ejecutarse en una base temporal, no en tu base de desarrollo con datos.** Desde `backend/` con el entorno virtual activo:

```powershell
try {
    $env:DB_ENGINE = "sqlite"
    python manage.py test usuarios clientes productos pedidos inventario reportes config -v 2

    if ($LASTEXITCODE -ne 0) {
        throw "Fallaron las pruebas automatizadas"
    }
}
finally {
    Remove-Item Env:DB_ENGINE -ErrorAction SilentlyContinue
}
```

Django crea y destruye automáticamente su base de pruebas. El bloque `finally` evita que `DB_ENGINE=sqlite` permanezca activo después.

Si tienes integrado el material de la fase 7, desde la **raíz del repositorio** también puedes ejecutar:

```powershell
powershell -ExecutionPolicy Bypass -File tools/validacion_final.ps1
```

No supongas que un resultado `OK` de una prueba aislada valida todo el sistema; revisa la salida completa antes de fusionar cambios o desplegar.

## Endpoints principales

| Ruta | Función |
| --- | --- |
| `POST /api/auth/register/` | Registro público (rol CLIENTE) |
| `POST /api/auth/login/` | Inicio de sesión y emisión de JWT |
| `POST /api/auth/refresh/` | Renovación de access token |
| `POST /api/auth/logout/` | Cierre de sesión y revocación del refresh token |
| `GET /api/usuarios/me/` | Perfil del usuario autenticado |
| `GET /api/catalogo/productos/` | Catálogo público de productos activos |
| `/api/clientes/` | Gestión de clientes según permisos |
| `/api/productos/` | Administración de productos |
| `/api/pedidos/` | Gestión y consulta de pedidos |
| `/api/inventario/ingredientes/` | Ingredientes y existencias |
| `/api/inventario/movimientos/` | Entradas, salidas y mermas |
| `/api/reportes/dashboard/` | Indicadores administrativos (ADMIN) |
| `/api/reportes/exportar/` | Exportación de reportes (ADMIN) |

Las rutas protegidas requieren un JWT válido y los permisos correspondientes. El catálogo público solo expone los productos y categorías autorizados para consulta.

## Solución de problemas

| Problema | Qué revisar |
| --- | --- |
| `ModuleNotFoundError` | Entorno virtual activo, `pip install -r requirements.txt` y archivos de cada aplicación presentes. |
| `Can't connect to MySQL server` / error `2002` | Servicio MariaDB, host, puerto y firewall. Con Docker, comprueba `3307`. |
| `Access denied for user` | Usuario, contraseña y permisos configurados en MariaDB. |
| `Unknown database 'sigep'` | Crea la base o corrige `DB_NAME`. |
| `You have unapplied migrations` | Primero verifica qué base está seleccionada; después ejecuta `migrate` solo contra la base correcta. |
| Login responde `401` con usuarios que sí existen | Comprueba que Django no esté conectado a SQLite y verifica las credenciales. |
| `TemplateDoesNotExist: index.html` | `backend/` y `frontend/` deben ser carpetas hermanas. |
| `404 /static/app.js` o estilos ausentes | Comprueba `frontend/`, rutas estáticas y acceso a Internet para los recursos CDN de desarrollo. |
| Respuesta `429` durante pruebas | Hay limitación de solicitudes; revisa el aislamiento del throttling en las pruebas, sin desactivarlo globalmente. |
| Git muestra conflictos en un merge | Resuélvelos y ejecuta las pruebas antes de hacer `push` a `main`. |

Si ves una base vacía de repente, **no elimines tablas ni vuelvas a crear usuarios**. Primero ejecuta el comando de comprobación de conexión del paso 5 y confirma que Django usa MariaDB en lugar de la base SQLite de pruebas.

## Seguridad y despliegue

SIGEP se proporciona para **pruebas locales y evaluación académica**. Antes de publicarlo en un servidor accesible por Internet se requiere, como mínimo:

- Configurar `DJANGO_DEBUG=False`, un `DJANGO_SECRET_KEY` privado y hosts permitidos.
- Habilitar HTTPS, cookies seguras, un proxy correctamente configurado y revisar `python manage.py check --deploy`.
- Compilar Tailwind CSS para producción en lugar de depender del CDN de desarrollo.
- Revisar el almacenamiento de refresh tokens (preferir cookies `HttpOnly`, `Secure`, `SameSite` y protección CSRF), así como los permisos y la gestión de secretos.
- Configurar respaldos de MariaDB y de los archivos subidos, además de probar su restauración.
- Utilizar un servidor de aplicaciones y servir archivos estáticos y medios de manera apropiada; **no usar `runserver` en producción**.

Las guías de la fase 7, cuando están disponibles en tu rama, amplían estos temas:

- [`docs/13_MANUAL_USUARIO_SIGEP.md`](docs/13_MANUAL_USUARIO_SIGEP.md)
- [`docs/14_MANUAL_TECNICO_SIGEP.md`](docs/14_MANUAL_TECNICO_SIGEP.md)
- [`docs/16_RESPALDOS_Y_RESTAURACION.md`](docs/16_RESPALDOS_Y_RESTAURACION.md)
- [`docs/17_DESPLIEGUE_SIGEP.md`](docs/17_DESPLIEGUE_SIGEP.md)
- [`docs/19_CHECKLIST_ENTREGA.md`](docs/19_CHECKLIST_ENTREGA.md)

---

**Repositorio:** https://github.com/12606/SIGEP  
**Proyecto:** SIGEP · Pastelería Dulce Encanto
