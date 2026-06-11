from __future__ import annotations

import ctypes
import os
import shutil
import zipfile
from typing import Tuple


_REQUIRED_DLLS = (
    "libcairo-2.dll",
    "libpango-1.0-0.dll",
    "libgobject-2.0-0.dll",
)


def _project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _is_windows() -> bool:
    return os.name == "nt"


def _gtk_bin_exists(gtk_bin: str) -> bool:
    return all(os.path.exists(os.path.join(gtk_bin, dll)) for dll in _REQUIRED_DLLS)


def _find_gtk_bin(search_root: str) -> str:
    for root, _, files in os.walk(search_root):
        if "libcairo-2.dll" in files:
            return root
    return ""


def _activate_gtk_bin(gtk_bin: str) -> None:
    path = os.environ.get("PATH", "")
    parts = path.split(os.pathsep) if path else []
    if gtk_bin not in parts:
        os.environ["PATH"] = gtk_bin + os.pathsep + path

    os.environ["MANIFEST_GTK_BIN"] = gtk_bin

    add_dll_directory = getattr(os, "add_dll_directory", None)
    if callable(add_dll_directory):
        try:
            add_dll_directory(gtk_bin)
        except Exception:
            pass


def _runtime_dlls_loadable() -> bool:
    for dll in _REQUIRED_DLLS:
        try:
            ctypes.CDLL(dll)
        except Exception:
            return False
    return True


def _install_from_zip(project_root: str, target_root: str) -> Tuple[bool, str]:
    archives = [
        os.path.join(project_root, "runtime", "gtk-runtime-win64.zip"),
        os.path.join(project_root, "runtime", "gtk-runtime.zip"),
        os.path.join(project_root, "packages", "gtk-runtime-win64.zip"),
        os.path.join(project_root, "packages", "gtk-runtime.zip"),
        os.path.join(project_root, "third_party", "gtk-runtime-win64.zip"),
        os.path.join(project_root, "third_party", "gtk-runtime.zip"),
    ]

    archive = next((p for p in archives if os.path.isfile(p)), "")
    if not archive:
        return False, "Kein lokales GTK-Archiv gefunden"

    if os.path.isdir(target_root):
        shutil.rmtree(target_root, ignore_errors=True)
    os.makedirs(target_root, exist_ok=True)

    with zipfile.ZipFile(archive, "r") as zf:
        zf.extractall(target_root)

    gtk_bin = os.path.join(target_root, "bin")
    if not _gtk_bin_exists(gtk_bin):
        found = _find_gtk_bin(target_root)
        if found:
            gtk_bin = found

    if not _gtk_bin_exists(gtk_bin):
        return False, f"GTK-Archiv entpackt, aber keine brauchbare bin-Struktur gefunden: {archive}"

    _activate_gtk_bin(gtk_bin)
    return True, f"GTK-Runtime aus Archiv installiert: {archive}"


def ensure_weasyprint_pdf_runtime() -> Tuple[bool, str]:
    """
    Versucht unter Windows, fehlende WeasyPrint-Systembibliotheken offline bereitzustellen.

    Reihenfolge:
    1) Bereits vorhandene runtime/gtk/bin nutzen
    2) Lokales Projekt-Archiv (zip) nach runtime/gtk entpacken
    3) Lokale GTK-Installation vom Rechner in runtime/gtk kopieren
    """
    if not _is_windows():
        return False, "Automatische Runtime-Installation ist nur unter Windows erforderlich"

    project_root = _project_root()
    target_root = os.path.join(project_root, "runtime", "gtk")
    target_bin = os.path.join(target_root, "bin")

    if _gtk_bin_exists(target_bin):
        _activate_gtk_bin(target_bin)
        if _runtime_dlls_loadable():
            return True, "GTK-Runtime bereits vorhanden"

    ok, msg = _install_from_zip(project_root, target_root)
    if ok and _runtime_dlls_loadable():
        return True, msg

    return False, "GTK/Cairo/Pango konnten offline nicht bereitgestellt werden"
