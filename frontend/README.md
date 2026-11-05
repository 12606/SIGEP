# Frontend de SIGEP

Interfaz web de Dulce Encanto. `index.html` es una plantilla que Django sirve en `/` y `app.js` es un archivo estático servido en `/static/app.js`.

**Para abrir:** inicia `python manage.py runserver` dentro de `backend` y entra a http://127.0.0.1:8000/ . No abras este HTML directamente por `file://` ni utilices Live Server para la integración recomendada.

- `index.html`: diseño Tailwind + formularios de login y registro.
- `app.js`: peticiones relativas `/api/...` a Django (mismo origen).

Dependencia visual de CDN (Tailwind y Google Fonts): requiere Internet para verse con el estilo completo. Para producción, compilar CSS localmente.
