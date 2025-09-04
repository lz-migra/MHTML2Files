import email
from pathlib import Path
import sys
import re

# Mapear Content-Type → extensión
MIME_EXTENSIONS = {
    "text/html": ".html",
    "text/css": ".css",
    "application/javascript": ".js",
    "application/x-javascript": ".js",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/svg+xml": ".svg",
    "font/woff": ".woff",
    "font/woff2": ".woff2",
    "application/font-woff": ".woff",
}

def sanitize_filename(name: str, content_type: str, index: int) -> str:
    # Quitar "cid:" y "@mhtml.blink"
    if name.startswith("cid:"):
        name = name[4:]
    name = name.replace("@mhtml.blink", "")

    # Reemplazar caracteres inválidos
    name = re.sub(r'[<>:"/\\|?*]', "_", name)

    # Forzar extensión correcta según Content-Type
    ext = MIME_EXTENSIONS.get(content_type)
    if ext and not name.endswith(ext):
        name = f"{name}{ext}"

    # Si no queda nada válido, inventar uno
    if not name.strip():
        name = f"recurso_{index}{ext or ''}"

    return name.strip()

def extract_mhtml(mhtml_path, output_dir=None):
    mhtml_file = Path(mhtml_path)

    if not mhtml_file.exists():
        print(f"❌ No se encontró el archivo: {mhtml_file}")
        return

    if not output_dir:
        output_dir = mhtml_file.parent / (mhtml_file.stem + "_extraido")

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(mhtml_file, "rb") as f:
        msg = email.message_from_binary_file(f)

    mapping = {}  # content-location → nuevo nombre
    count = 0

    for i, part in enumerate(msg.walk()):
        payload = part.get_payload(decode=True)
        if not payload:
            continue

        content_type = part.get_content_type()
        content_location = part.get("Content-Location")

        filename = None
        if content_location:
            filename = Path(content_location).name
        else:
            filename = part.get_filename()

        filename = sanitize_filename(filename or "", content_type, i)

        out_path = output_dir / filename
        with open(out_path, "wb") as out_file:
            out_file.write(payload)

        if content_location:
            mapping[content_location] = filename

        count += 1
        print(f"✅ Extraído: {out_path}")

    # 🔄 Corregir rutas en archivos HTML
    for html_file in output_dir.glob("*.html"):
        text = html_file.read_text(encoding="utf-8", errors="ignore")
        for old, new in mapping.items():
            if old in text:
                text = text.replace(old, new)
        html_file.write_text(text, encoding="utf-8")
        print(f"🔗 Rutas corregidas en: {html_file}")

    print(f"\n🎉 Listo, se extrajeron {count} recursos en: {output_dir}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python extract_mhtml.py archivo.mhtml [carpeta_salida]")
    else:
        extract_mhtml(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
