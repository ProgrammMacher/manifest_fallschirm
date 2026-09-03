"""
Display Services für Load-Anzeige.
Extrahiert QR-Code und PDF-Rendering aus routes/load.py.
"""

from io import BytesIO
from typing import Optional
import qrcode
import socket
from urllib.parse import urlparse
from flask import request


def generate_qr_png_buffer(data: str, size: int = 150) -> BytesIO:
    """
    Generiert QR-Code als PNG-BytesIO Buffer.
    
    Args:
        data: QR-Daten (z.B. WiFi SSID)
        size: Pixel-Größe (64-1024, default 150)
    
    Returns:
        BytesIO mit PNG-Daten, ready für Flask send_file()
    """
    if size < 64:
        size = 64
    if size > 1024:
        size = 1024

    img = qrcode.make(data)
    
    # Pixel-genaue Skalierung (QR bleibt scharf)
    try:
        from PIL import Image
        img = img.resize((size, size), resample=Image.NEAREST)
    except Exception:
        try:
            img = img.resize((size, size))
        except Exception:
            pass

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def build_display_qr_url() -> tuple[bool, str]:
    """
    Baut QR-URL für Display-Anzeige.
    
    Returns:
        (qr_available, qr_url)
        qr_available=False wenn keine realistische IP (z.B. 127.0.0.1)
    """
    from app.helpers.app_settings import get_published_display

    published = get_published_display() or {}
    published_url = (published.get("url") or "").strip()
    if published_url:
        return True, published_url

    # Fallback: URL aus aktueller Request-Umgebung ableiten.
    host = (request.host or "").strip()
    scheme = request.scheme or "http"

    host_ip = ""
    host_port = ""
    if host:
        if ":" in host:
            host_ip, host_port = host.rsplit(":", 1)
        else:
            host_ip = host

    ip = (host_ip or "").strip()
    if not ip or ip in {"127.0.0.1", "localhost"}:
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            ip = ""

    if not ip or ip in {"127.0.0.1", "localhost"}:
        return False, ""

    port = (host_port or "5000").strip() or "5000"
    display_url = f"{scheme}://{ip}:{port}/loads/display"

    # Defensive normalize if caller accidentally stores absolute display path in published URL later.
    try:
        parsed = urlparse(display_url)
        if not parsed.scheme or not parsed.netloc:
            return False, ""
    except Exception:
        return False, ""

    return True, display_url


def build_local_qr_url(path: str) -> tuple[bool, str]:
    """Baut eine QR-Ziel-URL unter derselben LAN-Herkunft wie das Display."""
    qr_available, display_url = build_display_qr_url()
    if not qr_available or not display_url:
        return False, ""

    try:
        parsed = urlparse(display_url)
        normalized_path = "/" + path.lstrip("/")
        return True, f"{parsed.scheme}://{parsed.netloc}{normalized_path}"
    except Exception:
        return False, ""
