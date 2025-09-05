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
    # Eliminar “cid:” si existe (lo guardaremos en variantes)
    name = re.sub(r"^cid:", "", name, flags=re.IGNORECASE)
    # Quitar <> envolventes
    name = name.strip("<>")
    # Reemplazar caracteres no válidos
    invalid_chars = r'<>:"/\\|?*'
    for c in invalid_chars:
        name = name.replace(c, "_")
    # Evitar nombres vacíos
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
    # raw
    variants.add(k)
    # sin <>
    no_br = k.strip("<>")
    variants.add(no_br)
    # basename
    try:
        import ntpath
        basename = ntpath.basename(no_br)
    except Exception:
        basename = os.path.basename(no_br)
    variants.add(basename)
    # con y sin cid:
    if no_br.lower().startswith("cid:"):
        variants.add(no_br)                # cid:abc...
        variants.add(no_br[4:])            # abc...
    else:
        variants.add("cid:" + no_br)       # cid:abc...
        variants.add("cid:" + basename)    # cid:basename
    # con y sin @mhtml.blink
    if "@mhtml.blink" in no_br:
        variants.add(no_br)
        variants.add(no_br.replace("@mhtml.blink", ""))
        variants.add(basename)
        variants.add(basename.replace("@mhtml.blink", ""))
    else:
        variants.add(no_br + "@mhtml.blink")
        variants.add(basename + "@mhtml.blink")
    # percent-decoded simples (%40 -> @, %3A -> :)
    variants.add(no_br.replace("%40", "@").replace("%3A", ":"))
    # limpiar espacios
    cleaned = set(v.strip() for v in variants if v and len(v.strip())>0)
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

    # Leer todas las partes primero
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

    # 1) Crear nombres de archivo y mapa de variantes -> filename
    variant_map = {}   # variant_string -> filename
    entries = []       # lista de items con info para escribir
    for item in parts:
        idx = item["index"]
        ct = item["content_type"]
        cid = item["content_id"]
        cloc = item["content_location"]

        # Nombre base preferido: content_location > content_id > recurso_idx
        raw_name = cloc or cid or f"resource_{idx}"
        raw_name = str(raw_name)
        # quitar "cid:" si tiene, quitar <>
        base_name = re.sub(r"^cid:", "", raw_name, flags=re.IGNORECASE)
        base_name = base_name.strip("<> ")
        base_name = sanitize_filename(base_name)

        # determinar extension
        ext = guess_ext(ct, base_name)
        if not base_name.lower().endswith(ext.lower()):
            filename = base_name + ext
        else:
            filename = base_name

        # asegurarnos único
        filename = ensure_unique(base_dir, filename)

        # generar variantes tanto para content_location como content_id
        keys = set()
        keys.update(generate_variants(cloc))
        keys.update(generate_variants(cid))
        # además mappear la propia base_name y basename sin extensión
        keys.add(base_name)
        keys.add(os.path.basename(base_name))
        # almacenar en map
        for k in keys:
            if k:  # evitar vacíos
                # preferir la primera aparición (no sobrescribir si existe)
                if k not in variant_map:
                    variant_map[k] = filename

        entries.append({
            "filename": filename,
            "content_type": ct,
            "payload_bytes": item["payload_bytes"],
            "is_html": "html" in ct.lower(),
            "part_obj": item["part_obj"],
        })

    # 2) Escribir archivos: para HTML, primero aplicar reemplazos en texto y luego formatear
    # ordenamos variantes por longitud descendente para evitar reemplazos parciales antes de los largos
    variants_sorted = sorted(variant_map.keys(), key=lambda s: -len(s))

    for entry in entries:
        out_path = os.path.join(base_dir, entry["filename"])
        if entry["is_html"]:
            # decodificar a texto con charset si está disponible
            part = entry["part_obj"]
            html_text = decode_payload_text(part)
            # aplicar reemplazos: cada variante -> filename
            for var in variants_sorted:
                target = variant_map[var]
                # reemplazar exactamente la variante y también su forma con "cid:" si no la tiene
                try:
                    html_text = html_text.replace(var, target)
                    # también reemplazar "cid:var" -> target (si aún aparece)
                    if not var.lower().startswith("cid:"):
                        html_text = html_text.replace("cid:" + var, target)
                except Exception:
                    pass
            # beautify
            pretty = beautify_html_text(html_text)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(pretty)
            print(f"✅ HTML guardado: {out_path}")
        else:
            # binario u otros
            with open(out_path, "wb") as f:
                f.write(entry["payload_bytes"])
            print(f"✅ Recurso guardado: {out_path}")

    print("\n🎉 Extracción completada en:", base_dir)
    print("🔎 Nota: si alguna referencia sigue apuntando a 'cid:' en el HTML, dime un ejemplo exacto y lo afinamos.")

# -------------------------
# CLI
# -------------------------
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python extract_mhtml.py archivo.mhtml")
        sys.exit(1)
    extract_mhtml(sys.argv[1])
