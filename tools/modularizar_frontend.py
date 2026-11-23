#!/usr/bin/env python3
"""Modulariza SIGEP sin reemplazar la lógica JS ni cambiar el API.

Uso (desde cualquier ubicación, después de copiar a SIGEP/tools/):
    python tools/modularizar_frontend.py --verificar
    python tools/modularizar_frontend.py --aplicar

Requiere TemplateView + TEMPLATES.DIRS apuntando a frontend/ (estado de SIGEP).
Genera frontend/templates/, frontend/static/css/, frontend/static/js/.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
import sys


VISTAS = {
    "auth-card": "acceso/acceso.html",
    "session-panel": "sesion/inicio.html",
    "perfil-panel": "perfil/mi_perfil.html",
    "catalogo-visitante-panel": "catalogo/catalogo_publico.html",
    "clientes-panel": "dashboard/panel.html",
}
VISTAS_DASHBOARD = {
    "sigep-vista-clientes": "modulos/clientes.html",
    "sigep-vista-usuarios": "modulos/usuarios.html",
    "sigep-vista-productos": "modulos/productos.html",
    "sigep-vista-pedidos": "modulos/pedidos.html",
    "sigep-vista-inventario": "modulos/inventario.html",
    "sigep-vista-reportes": "modulos/reportes.html",
}
VISTAS_SESION = {
    "pedidos-cliente-panel": "modulos/mis_pedidos.html",
    "pedidos-produccion-panel": "modulos/produccion.html",
    "inventario-repostero-panel": "modulos/existencias_repostero.html",
}


class HTMLRange(HTMLParser):
    """Localiza rangos exactos por id preservando el HTML original byte a byte."""

    def __init__(self, document: str, target_id: str):
        super().__init__(convert_charrefs=False)
        self.text = document
        self.target_id = target_id
        self.line_offsets = [0]
        self.line_offsets += [m.end() for m in re.finditer("\n", document)]
        self.tag = None
        self.depth = 0
        self.start = None
        self.end = None

    def pos(self):
        line, column = self.getpos()
        return self.line_offsets[line - 1] + column

    def handle_starttag(self, tag, attrs):
        if self.end is not None:
            return
        if self.start is None and dict(attrs).get("id") == self.target_id:
            self.start = self.pos()
            self.tag = tag
            self.depth = 1
        elif self.start is not None and tag == self.tag:
            self.depth += 1

    def handle_endtag(self, tag):
        if self.start is None or self.end is not None:
            return
        if tag == self.tag:
            self.depth -= 1
            if self.depth == 0:
                raw = self.text[self.pos():]
                close = re.match(r"</\s*" + re.escape(tag) + r"\s*>", raw, re.I)
                if not close:
                    raise ValueError(f"No se pudo cerrar <{tag}> para {self.target_id}")
                self.end = self.pos() + close.end()


def extract_by_id(html: str, element_id: str) -> tuple[str, str]:
    search = HTMLRange(html, element_id)
    search.feed(html)
    if search.start is None or search.end is None:
        raise ValueError(f"Falta un elemento con id={element_id!r} o su etiqueta está incompleta.")
    fragment = html[search.start:search.end]
    return fragment, html[:search.start] + "{% include 'partials/REEMPLAZAR' %}" + html[search.end:]


def split_component(html: str, element_id: str, name: str, templates: dict[str, str]):
    fragment, replaced = extract_by_id(html, element_id)
    templates[f"partials/{name}"] = fragment
    return replaced.replace("{% include 'partials/REEMPLAZAR' %}",
                            "{% include 'partials/" + name + "' %}", 1)


def get_dialog_ids(html: str) -> list[str]:
    find = re.compile(r'<dialog\b[^>]*\bid\s*=\s*["\']([^"\']+)["\']', re.I | re.S)
    ids = find.findall(html)
    if len(set(ids)) != len(ids):
        raise ValueError("Hay IDs de diálogo duplicados.")
    return ids


def fragmentar(html: str) -> dict[str, str]:
    templates = {}
    # El contenedor de gestión incluye sub-vistas, pero permanece siempre presente.
    dashboard, remaining = extract_by_id(html, "clientes-panel")
    for element_id, name in VISTAS_DASHBOARD.items():
        dashboard = split_component(dashboard, element_id, name, templates)
    templates["partials/dashboard/panel.html"] = dashboard
    html = remaining.replace("partials/REEMPLAZAR", "partials/dashboard/panel.html", 1)

    # División de la bienvenida por funcionalidades del rol.
    sesion, remaining = extract_by_id(html, "session-panel")
    for element_id, name in VISTAS_SESION.items():
        sesion = split_component(sesion, element_id, name, templates)
    templates["partials/sesion/inicio.html"] = sesion
    html = remaining.replace("partials/REEMPLAZAR", "partials/sesion/inicio.html", 1)

    for element_id, name in VISTAS.items():
        if element_id in {"clientes-panel", "session-panel"}:
            continue
        html = split_component(html, element_id, name, templates)

    for dialog_id in get_dialog_ids(html):
        # Evita que el ID se use directamente como una ruta arbitraria.
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", dialog_id, re.I):
            raise ValueError(f"ID de diálogo inesperado: {dialog_id}")
        html = split_component(html, dialog_id, f"modales/{dialog_id}.html", templates)

    # Funciones JS de login y registro que antes vivían dentro del HTML.
    scripts_extra = {}
    auth_script = re.compile(r"<script>\s*(?://[^\n]*\n\s*)?// Función para cambiar a la vista de Registro[\s\S]*?</script>")
    match = auth_script.search(html)
    if match:
        body = re.sub(r"\A<script>|</script>\Z", "", match.group(0)).strip() + "\n"
        scripts_extra["auth-ui.js"] = body
        html = html[:match.start()] + '<script src="{% static \'js/auth-ui.js\' %}" defer></script>' + html[match.end():]
    else:
        # Si cambia la definición de esa función, no romperla: dejar el script en index.
        pass

    # Estilos básicos de animaciones que no corresponden a un módulo específico.
    css_extra = {}
    pat = re.compile(r"<style>\s*/\* Animaciones personalizadas \*/[\s\S]*?</style>")
    match = pat.search(html)
    if match:
        css = match.group(0)[len("<style>"):-len("</style>")].strip() + "\n"
        css_extra["base.css"] = css
        html = html[:match.start()] + '<link rel="stylesheet" href="{% static \'css/base.css\' %}">' + html[match.end():]

    # Ajustar referencias a archivos estáticos existentes una vez reubicados.
    static_refs = re.compile(r"\{%\s*static\s+(['\"])([^'\"]+)\1\s*%\}")
    def change_static_ref(match):
        path = match.group(2)
        if "/" not in path and path.endswith(".js"):
            return "{% static 'js/" + path + "' %}"
        if "/" not in path and path.endswith(".css"):
            return "{% static 'css/" + path + "' %}"
        return match.group(0)
    html = static_refs.sub(change_static_ref, html)
    templates["index.html"] = html
    return {"templates": templates, "scripts_extra": scripts_extra, "css_extra": css_extra}


def actualizar_configuracion(settings_content: str) -> str:
    template_old = r'"DIRS": [BASE_DIR.parent / "frontend"]'
    template_new = r'"DIRS": [BASE_DIR.parent / "frontend" / "templates"]'
    static_old = 'STATICFILES_DIRS = [BASE_DIR.parent / "frontend"]'
    static_new = 'STATICFILES_DIRS = [BASE_DIR.parent / "frontend" / "static"]'
    if settings_content.count(template_old) != 1 or settings_content.count(static_old) != 1:
        raise ValueError("settings.py tiene una configuración distinta a la prevista. No se modificó nada.")
    return settings_content.replace(template_old, template_new).replace(static_old, static_new)


def ejecutar(root: Path, apply: bool):
    frontend = root / "frontend"
    settings = root / "backend" / "config" / "settings.py"
    original = frontend / "index.html"
    if not (original.is_file() and settings.is_file()):
        raise ValueError("No se encontró frontend/index.html o backend/config/settings.py. Copia el script a SIGEP/tools/.")
    if (frontend / "templates").exists() or (frontend / "static").exists():
        raise ValueError("frontend/templates o frontend/static ya existen. Evitamos sobrescribir cambios previos.")
    html = original.read_text(encoding="utf-8")
    if "{% include 'partials/" in html:
        raise ValueError("index.html ya parece modularizado.")
    settings_new = actualizar_configuracion(settings.read_text(encoding="utf-8"))
    parts = fragmentar(html)
    files = [p for p in frontend.iterdir() if p.is_file() and p.suffix in {".js", ".css"}]
    if not files:
        raise ValueError("No se encontraron los JS/CSS del frontend para mover.")
    # Las referencias relativas url() en CSS necesitan revisión antes de mover.
    for f in files:
        if f.suffix == ".css":
            for m in re.finditer(r"url\(\s*['\"]?([^'\")]+)", f.read_text(encoding="utf-8")):
                asset = m.group(1).strip()
                if not asset.startswith(("https://", "http://", "data:", "/", "#")):
                    raise ValueError(f"{f.name} usa url({asset}); hay que ajustar su ruta antes de moverlo.")
    # Sólo Django puede aplicar {% include %} en el servidor.
    urls = root / "backend" / "config" / "urls.py"
    if urls.exists() and "TemplateView" not in urls.read_text(encoding="utf-8"):
        raise ValueError("Las URLs ya no usan TemplateView; verifica la renderización Django antes de modificar.")
    # Las referencias estáticas deben ser resolubles (todas las fuentes están presentes).
    names = {p.name for p in files} | set(parts["scripts_extra"]) | set(parts["css_extra"])
    refs = re.findall(r"\{%\s*static\s+['\"](?:js|css)/([^'\"]+)['\"]\s*%\}", parts["templates"]["index.html"])
    faltantes = sorted(set(refs) - names)
    if faltantes:
        raise ValueError("Faltan archivos referenciados en index.html: " + ", ".join(faltantes))
    print("Se han identificado:")
    print(" -", len(parts["templates"]), "plantillas HTML (incluida index.html)")
    print(" -", sum(f.suffix == ".js" for f in files) + len(parts["scripts_extra"]), "archivos JavaScript")
    print(" -", sum(f.suffix == ".css" for f in files) + len(parts["css_extra"]), "archivos CSS")
    print(" - 1 ajuste de backend/config/settings.py (rutas de templates/static)")
    if not apply:
        print("\nComprobación correcta. Para aplicar: python tools/modularizar_frontend.py --aplicar")
        return

    # Backup fuera del repositorio para restaurar si algo falla.
    out_dir = root.parent / (root.name + "_respaldo_frontend_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    if out_dir.exists():
        raise ValueError("La carpeta de respaldo ya existe; repite el comando en unos segundos.")
    out_dir.mkdir()
    shutil.copy2(original, out_dir / "index.html")
    shutil.copy2(settings, out_dir / "settings.py")
    (out_dir / "assets").mkdir()
    for f in files:
        shutil.copy2(f, out_dir / "assets" / f.name)
    print("Respaldo creado en:", out_dir)

    templates_root = frontend / "templates"
    static_root = frontend / "static"
    for path, content in parts["templates"].items():
        dest = templates_root / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
    for f in files:
        dest = static_root / ("js" if f.suffix == ".js" else "css") / f.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(f), str(dest))
    for filename, content in parts["scripts_extra"].items():
        dest = static_root / "js" / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
    for filename, content in parts["css_extra"].items():
        dest = static_root / "css" / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
    settings.write_text(settings_new, encoding="utf-8")
    original.unlink()
    print("\nFrontend reorganizado. No se cambió ningún archivo de lógica de JavaScript.")
    print("Comprueba: python backend/manage.py check")
    print("Y después: python tools/verificar_frontend_modular.py")


def main():
    arg = argparse.ArgumentParser(description="SIGEP: separar frontend en plantillas parciales, CSS y JS")
    group = arg.add_mutually_exclusive_group(required=True)
    group.add_argument("--verificar", action="store_true", help="Analizar sin modificar archivos")
    group.add_argument("--aplicar", action="store_true", help="Aplicar cambios y crear respaldo")
    a = arg.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        ejecutar(root, a.aplicar)
    except (ValueError, OSError) as e:
        print("ERROR:", e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
