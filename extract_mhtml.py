#!/usr/bin/env python3
"""
extract_mhtml.py
Extrae recursos de archivos .mhtml, corrige referencias (cid: / @mhtml.blink)
y formatea los HTML usando BeautifulSoup.

Uso:
    python extract_mhtml.py archivo.mhtml
"""
import os
import re
import sys
import mimetypes
import subprocess
from email import message_from_binary_file

# -------------------------
# Intentar importar BeautifulSoup (instalar si falta)
# -------------------------
try:
    from bs4 import BeautifulSoup
except ImportError:
    print("📦 beautifulsoup4 no encontrado. Instalando automáticamente...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "beautifulsoup4"])
    from bs4 import BeautifulSoup

# -------------------------
# Map básico MIME -> extensión
# -------------------------
MIME_EXTENSIONS = {
    "text/html": ".html",
    "text/css": ".css",
    "application/javascript": ".js",
    "application/x-javascript": ".js",
    "text/javascript": ".js",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/svg+xml": ".svg",
    "font/woff": ".woff",
    "font/woff2": ".woff2",
    "application/font-woff": ".woff",
}

# -------------------------
# Helpers
# -------------------------
def sanitize_filename(name: str) -> str:
    """Quita caracteres inválidos para Windows y espacios al inicio/fin 🧹"""
    if not name:
        return ""
    name = name.strip()
    name = re.sub(r"^cid:", "", name, flags=re.IGNORECASE)
    name = name.strip("<>")
    invalid_chars = r'<>:"/\\|?*'
    for c in invalid_chars:
        name = name.replace(c, "_")
    return name or "resource"

def ensure_unique(path_dir: str, filename: str) -> str:
    """Si filename ya existe en path_dir, añade _1, _2, ..."""
    base, ext = os.path.splitext(filename)
    candidate = filename
    n = 1
    while os.path.exists(os.path.join(path_dir, candidate)):
        candidate = f"{base}_{n}{ext}"
        n += 1
    return candidate

def guess_ext(content_type: str, fallback_name: str) -> str:
    """Intenta obtener extensión por MIME o por el nombre; si no, .bin"""
    if not content_type:
        return os.path.splitext(fallback_name)[1] or ".bin"
    ext = MIME_EXTENSIONS.get(content_type)
    if not ext:
        ext = mimetypes.guess_extension(content_type) or ""
    if not ext:
        ext = os.path.splitext(fallback_name)[1] or ".bin"
    return ext

def decode_payload_text(part) -> str:
    """Decodifica el payload de un part a texto usando el charset si existe."""
    payload = part.get_payload(decode=True)
    if payload is None:
        return ""
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except Exception:
        return payload.decode("utf-8", errors="replace")

def generate_variants(key: str):
    """Genera variantes razonables que pueden aparecer en el HTML para una llave dada."""
    variants = set()
    if not key:
        return variants
    k = str(key).strip()
    variants.add(k)
    no_br = k.strip("<>")
    variants.add(no_br)
    try:
        import ntpath
        basename = ntpath.basename(no_br)
    except Exception:
        basename = os.path.basename(no_br)
    variants.add(basename)
    if no_br.lower().startswith("cid:"):
        variants.add(no_br)
        variants.add(no_br[4:])
    else:
        variants.add("cid:" + no_br)
        variants.add("cid:" + basename)
    if "@mhtml.blink" in no_br:
        variants.add(no_br)
        variants.add(no_br.replace("@mhtml.blink", ""))
        variants.add(basename)
        variants.add(basename.replace("@mhtml.blink", ""))
    else:
        variants.add(no_br + "@mhtml.blink")
        variants.add(basename + "@mhtml.blink")
    variants.add(no_br.replace("%40", "@").replace("%3A", ":"))
    cleaned = set(v.strip() for v in variants if v and len(v.strip()) > 0)
    return cleaned

def beautify_html_text(html_text: str) -> str:
    try:
        soup = BeautifulSoup(html_text, "html.parser")
        return soup.prettify()
    except Exception as e:
        print(f"⚠️ Error beautify: {e}")
        return html_text

# -------------------------
# Main: extracción
# -------------------------
def extract_mhtml(mhtml_path):
    if not os.path.exists(mhtml_path):
        print("❌ Archivo no encontrado:", mhtml_path)
        return

    base_dir = os.path.splitext(mhtml_path)[0]
    os.makedirs(base_dir, exist_ok=True)

    parts = []
    with open(mhtml_path, "rb") as f:
        msg = message_from_binary_file(f)
    for i, part in enumerate(msg.walk()):
        payload = part.get_payload(decode=True)
        if not payload:
            continue
        parts.append({
            "index": i,
            "content_type": part.get_content_type(),
            "content_id": part.get("Content-ID", "") or "",
            "content_location": part.get("Content-Location", "") or "",
            "part_obj": part,
            "payload_bytes": payload,
        })

    variant_map = {}
    entries = []
    for item in parts:
        idx = item["index"]
        ct = item["content_type"]
        cid = item["content_id"]
        cloc = item["content_location"]
        raw_name = cloc or cid or f"resource_{idx}"
        raw_name = str(raw_name)
        
        base_name = re.sub(r"^cid:", "", raw_name, flags=re.IGNORECASE)
        base_name = base_name.strip("<> ")
        base_name = base_name.replace("@mhtml.blink", "")
        base_name = sanitize_filename(base_name)

        ext = guess_ext(ct, base_name)
        name_part, _ = os.path.splitext(base_name)
        filename = name_part + ext
        filename = ensure_unique(base_dir, filename)

        keys = set()
        keys.update(generate_variants(cloc))
        keys.update(generate_variants(cid))
        keys.add(base_name)
        keys.add(os.path.basename(base_name))

        for k in keys:
            if k and k not in variant_map:
                variant_map[k] = filename

        entries.append({
            "filename": filename,
            "content_type": ct,
            "payload_bytes": item["payload_bytes"],
            "is_html": "html" in ct.lower(),
            "part_obj": item["part_obj"],
        })

    # 2) Escribir archivos: para HTML, aplicar reemplazos en una sola pasada con regex

    # Crear un mapa de reemplazo que incluya las variantes "cid:"
    # Esto evita tener que hacer múltiples llamadas a .replace()
    master_replace_map = {}
    for var, target in variant_map.items():
        master_replace_map[var] = target
        if not var.lower().startswith("cid:"):
            master_replace_map["cid:" + var] = target

    # Ordenar las llaves por longitud descendente para que el regex
    # encuentre la más larga primero (ej: "img/1.png" antes que "img/1")
    sorted_keys = sorted(master_replace_map.keys(), key=len, reverse=True)
    
    # Crear el patrón de regex uniendo todas las llaves con "|"
    # re.escape() se asegura de que caracteres especiales no rompan el regex
    pattern = re.compile('|'.join(re.escape(key) for key in sorted_keys))

    # Función que será llamada por re.sub() para cada coincidencia
    def replacer(match):
        # Busca la cadena encontrada en nuestro mapa y devuelve el nombre de archivo final
        return master_replace_map.get(match.group(0), match.group(0))

    for entry in entries:
        out_path = os.path.join(base_dir, entry["filename"])
        if entry["is_html"]:
            part = entry["part_obj"]
            html_text = decode_payload_text(part)
            
            # Aplicar el reemplazo en una sola pasada
            html_text = pattern.sub(replacer, html_text)

            pretty = beautify_html_text(html_text)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(pretty)
            print(f"✅ HTML guardado: {out_path}")
        else:
            with open(out_path, "wb") as f:
                f.write(entry["payload_bytes"])
            print(f"✅ Recurso guardado: {out_path}")

    print("\n🎉 Extracción completada en:", base_dir)

# -------------------------
# CLI
# -------------------------
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python extract_mhtml.py archivo.mhtml")
        sys.exit(1)
    extract_mhtml(sys.argv[1])
