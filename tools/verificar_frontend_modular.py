#!/usr/bin/env python3
"""Valida la estructura y composición de las plantillas del frontend SIGEP."""
from html.parser import HTMLParser
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "frontend" / "templates"
STATIC = ROOT / "frontend" / "static"
INCLUDE_RE = re.compile(r"\{%\s*include\s+(['\"])([^'\"]+)\1\s*%\}")
STATIC_RE = re.compile(r"\{%\s*static\s+(['\"])([^'\"]+)\1\s*%\}")


class Ids(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.ids = []

    def handle_starttag(self, tag, attrs):
        for k, v in attrs:
            if k == "id":
                self.ids.append(v)


def render_include(path, stack=None):
    stack = stack or []
    real = (TEMPLATES / path).resolve()
    if TEMPLATES.resolve() not in real.parents:
        raise ValueError("Plantilla fuera de frontend/templates: " + path)
    if not real.is_file():
        raise ValueError("Falta plantilla: " + path)
    if path in stack:
        raise ValueError("Referencia circular entre plantillas: " + path)
    body = real.read_text(encoding="utf-8")
    return INCLUDE_RE.sub(lambda m: render_include(m.group(2), stack + [path]), body)


def main():
    settings = ROOT / "backend" / "config" / "settings.py"
    if not settings.is_file():
        raise ValueError("No se encontró backend/config/settings.py")
    cfg = settings.read_text(encoding="utf-8")
    if '"DIRS": [BASE_DIR.parent / "frontend" / "templates"]' not in cfg:
        raise ValueError("TEMPLATES.DIRS no apunta a frontend/templates")
    if 'STATICFILES_DIRS = [BASE_DIR.parent / "frontend" / "static"]' not in cfg:
        raise ValueError("STATICFILES_DIRS no apunta a frontend/static")
    if (ROOT / "frontend" / "index.html").exists():
        raise ValueError("Quedó un frontend/index.html en la ubicación antigua")
    html = render_include("index.html")
    ids = Ids()
    ids.feed(html)
    dup = sorted({x for x in ids.ids if ids.ids.count(x) > 1})
    if dup:
        raise ValueError("IDs duplicados en la página combinada: " + ", ".join(dup))
    required = [
        "auth-card", "login-form", "register-form", "session-panel", "perfil-panel",
        "catalogo-visitante-panel", "clientes-panel", "sigep-vista-clientes",
        "sigep-vista-usuarios", "sigep-vista-productos", "sigep-vista-pedidos",
        "sigep-vista-inventario", "sigep-vista-reportes",
    ]
    missing = [x for x in required if x not in ids.ids]
    if missing:
        raise ValueError("Faltan elementos de SIGEP: " + ", ".join(missing))
    refs = STATIC_RE.findall(html)
    for _, path in refs:
        if path.endswith((".css", ".js")):
            if not (STATIC / path).is_file():
                raise ValueError("Referencia {% static %} sin archivo: " + path)
    original_script = [p for p in (STATIC / "js").glob("*.js")]
    original_css = [p for p in (STATIC / "css").glob("*.css")]
    if len(original_script) < 6 or len(original_css) < 5:
        raise ValueError("Parece que faltan archivos JS o CSS")
    print("OK: todas las plantillas se incluyen correctamente desde Django.")
    print("OK: sin identificadores HTML duplicados.")
    print("OK: elementos de todos los módulos presentes.")
    print("OK:", len(refs), "referencias static verificadas.")
    print("OK:", len(original_script), "archivos JS y", len(original_css), "CSS organizados.")
    print("Nota: esto no sustituye las pruebas reales de Django ni el recorrido en navegador.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        sys.exit(1)
