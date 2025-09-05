import os
import re
import sys
import mimetypes
import subprocess

# 👉 Intentar importar BeautifulSoup, instalar si no existe
try:
    from bs4 import BeautifulSoup
except ImportError:
    print("📦 BeautifulSoup no encontrado. Instalando automáticamente...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "beautifulsoup4"])
    from bs4 import BeautifulSoup


def sanitize_filename(filename: str) -> str:
    """Elimina caracteres no permitidos en nombres de archivo de Windows"""
    invalid_chars = r'<>:"/\\|?*'
    for c in invalid_chars:
        filename = filename.replace(c, "_")
    return filename


def beautify_html(content: bytes) -> str:
    """Formatea el HTML para hacerlo legible con indentación y saltos de línea ✨"""
    try:
        soup = BeautifulSoup(content, "html.parser")
        return soup.prettify()
    except Exception as e:
        print(f"⚠️ Error al formatear HTML: {e}")
        return content.decode("utf-8", errors="ignore")


def extract_mhtml(mhtml_file):
    from email import message_from_binary_file

    base_dir = os.path.splitext(mhtml_file)[0]
    os.makedirs(base_dir, exist_ok=True)

    with open(mhtml_file, "rb") as f:
        msg = message_from_binary_file(f)

    resources = {}
    html_file = None

    for part in msg.walk():
        content_id = part.get("Content-ID", "")
        content_location = part.get("Content-Location", "")
        content_type = part.get_content_type()
        payload = part.get_payload(decode=True)

        if not payload:
            continue

        # Determinar nombre base
        filename = content_location or content_id
        filename = re.sub(r"^cid:", "", filename)  # quitar "cid:"
        filename = filename.replace(":", "_")      # Windows no permite ":"
        filename = filename.replace("/", "_")

        # 👉 Sanear caracteres prohibidos en Windows
        filename = sanitize_filename(filename)

        # Obtener extensión según el tipo MIME
        ext = mimetypes.guess_extension(content_type)
        if not ext and "." in filename:
            ext = os.path.splitext(filename)[1]
        if not ext:
            ext = ".bin"

        if not filename.endswith(ext):
            filename += ext

        file_path = os.path.join(base_dir, filename)

        # Guardar HTML formateado
        if content_type == "text/html":
            html_file = file_path
            pretty_html = beautify_html(payload)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(pretty_html)
        else:
            with open(file_path, "wb") as f:
                f.write(payload)

        resources[content_id] = filename
        resources[content_location] = filename

    # Reemplazar rutas en el HTML
    if html_file:
        with open(html_file, "r", encoding="utf-8") as f:
            html_content = f.read()

        for key, value in resources.items():
            if not key:
                continue

            # Normalizar claves que pueden aparecer en el HTML
            patterns = [
                key,
                key.replace("cid:", ""),
                "cid:" + key,
                key.replace("@mhtml.blink", ""),
            ]

            for p in patterns:
                if p in html_content:
                    html_content = html_content.replace(p, value)

        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_content)

    print(f"✅ Archivos extraídos en: {base_dir}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python extract_mhtml.py archivo.mhtml")
        sys.exit(1)

    extract_mhtml(sys.argv[1])
