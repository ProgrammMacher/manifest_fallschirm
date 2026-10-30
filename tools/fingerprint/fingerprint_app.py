"""MANIFeST OU – Rechner-Kennung (Werkzeug für Endanwender).

Erzeugt die Rechner-Kennung ausschließlich über
``app/security/hardware_fingerprint.py`` (``get_machine_fingerprint``),
damit der Wert identisch mit der Lizenzprüfung von MANIFeST OU ist.

Dieses Modul enthält keine eigene Fingerprint-Berechnung und öffnet
kein Mailprogramm. Es zeigt die Kennung an, kopiert sie in die
Zwischenablage und kann sie optional als Textdatei speichern.
"""

from __future__ import annotations

import importlib.util
import os
import platform
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog

APP_TITEL = "MANIFeST OU – Rechner-Kennung"
DATEINAME_TXT = "MANIFeST_Rechnerkennung.txt"
HINWEIS = (
    "Bitte antworten Sie auf die E-Mail des Entwicklers und "
    "fügen Sie die Kennung mit Strg+V ein."
)
STATUS_OK = "Ihre Rechner-Kennung wurde in die Zwischenablage kopiert."
STATUS_FEHLER = (
    "Die Rechner-Kennung konnte nicht ermittelt werden. "
    "Bitte wenden Sie sich an den Entwickler."
)

_HEX_ZEICHEN = set("0123456789abcdef")


def _fingerprint_modul_laden():
    """Lädt hardware_fingerprint.py als alleinige Quelle der Berechnung.

    Im PyInstaller-Build (--paths app/security) ist das Modul direkt
    importierbar. Im Entwicklungsmodus wird die Datei direkt geladen,
    ohne das app-Paket (und damit Flask) zu importieren.
    """
    try:
        import hardware_fingerprint  # noqa: PLC0415

        return hardware_fingerprint
    except ImportError:
        pass
    pfad = (
        Path(__file__).resolve().parents[2]
        / "app"
        / "security"
        / "hardware_fingerprint.py"
    )
    spec = importlib.util.spec_from_file_location("hardware_fingerprint", pfad)
    if spec is None or spec.loader is None:
        raise RuntimeError("hardware_fingerprint.py wurde nicht gefunden.")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


_hardware_fingerprint = _fingerprint_modul_laden()


def ermittle_kennung() -> str:
    """Liefert die Rechner-Kennung als 64-stelligen Hex-Text (klein)."""
    kennung = str(_hardware_fingerprint.get_machine_fingerprint()).strip().lower()
    if len(kennung) != 64 or any(zeichen not in _HEX_ZEICHEN for zeichen in kennung):
        raise ValueError("Die ermittelte Rechner-Kennung hat ein ungültiges Format.")
    return kennung


def erzeuge_textinhalt(
    kennung: str,
    computername: str | None = None,
    zeitstempel: str | None = None,
) -> str:
    """Erzeugt den Inhalt der Textdatei (UTF-8, Windows-Zeilenenden)."""
    if computername is None:
        computername = platform.node()
    if zeitstempel is None:
        zeitstempel = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    return (
        "MANIFeST OU - Rechner-Kennung\r\n"
        "=============================\r\n"
        f"Kennung: {kennung}\r\n"
        f"Computername: {computername}\r\n"
        f"Datum/Uhrzeit: {zeitstempel}\r\n"
    )


def speichere_textdatei(ziel: Path, inhalt: str) -> Path:
    """Schreibt den Inhalt als UTF-8-Textdatei. Wirft OSError bei Fehlern."""
    ziel = Path(ziel)
    ziel.write_text(inhalt, encoding="utf-8", newline="")
    return ziel


def desktop_pfad() -> Path:
    """Ermittelt den echten Desktop (auch bei OneDrive-Umleitung)."""
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes

            class _GUID(ctypes.Structure):
                _fields_ = [
                    ("Data1", wintypes.DWORD),
                    ("Data2", wintypes.WORD),
                    ("Data3", wintypes.WORD),
                    ("Data4", ctypes.c_ubyte * 8),
                ]

            # FOLDERID_Desktop = {754AC886-DF64-4CBA-86B5-F7FBF4FBCEF5}
            folder_id = _GUID(
                0x754AC886,
                0xDF64,
                0x4CBA,
                (ctypes.c_ubyte * 8)(0x86, 0xB5, 0xF7, 0xFB, 0xF4, 0xFB, 0xCE, 0xF5),
            )
            pfad_ptr = wintypes.LPWSTR()
            hr = ctypes.windll.shell32.SHGetKnownFolderPath(
                ctypes.byref(folder_id), 0, None, ctypes.byref(pfad_ptr)
            )
            if hr == 0 and pfad_ptr.value:
                try:
                    return Path(pfad_ptr.value)
                finally:
                    ctypes.windll.ole32.CoTaskMemFree(pfad_ptr)
        except Exception:
            pass
    return Path.home() / "Desktop"


_CF_UNICODETEXT = 13
_GMEM_MOVEABLE = 0x0002


def _set_clipboard_win32(text: str) -> bool:
    """Setzt die Zwischenablage über die Windows-API.

    OpenClipboard(None) übergibt den Inhalt an das System, sodass die
    Zwischenablage auch nach dem Beenden der Anwendung gefüllt bleibt.
    """
    import ctypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    if not user32.OpenClipboard(None):
        return False
    try:
        user32.EmptyClipboard()
        daten = (text + "\0").encode("utf-16-le")
        handle = kernel32.GlobalAlloc(_GMEM_MOVEABLE, len(daten))
        if not handle:
            return False
        zeiger = kernel32.GlobalLock(handle)
        if not zeiger:
            kernel32.GlobalFree(handle)
            return False
        ctypes.memmove(zeiger, daten, len(daten))
        kernel32.GlobalUnlock(handle)
        if not user32.SetClipboardData(_CF_UNICODETEXT, handle):
            kernel32.GlobalFree(handle)
            return False
        return True
    finally:
        user32.CloseClipboard()


def kopiere_in_zwischenablage(text: str, root: tk.Misc | None = None) -> bool:
    """Kopiert den Text in die Zwischenablage. True bei Erfolg."""
    if os.name == "nt":
        try:
            if _set_clipboard_win32(text):
                return True
        except Exception:
            pass
    if root is not None:
        try:
            root.clipboard_clear()
            root.clipboard_append(text)
            root.update()
            return True
        except tk.TclError:
            return False
    return False


def _set_dpi_aware() -> None:
    if os.name != "nt":
        return
    import ctypes

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def main() -> int:
    try:
        _set_dpi_aware()
    except Exception:
        pass

    root = tk.Tk()
    root.title(APP_TITEL)
    root.resizable(False, False)

    try:
        kennung = ermittle_kennung()
    except Exception:
        kennung = ""
    ok = bool(kennung)
    if ok:
        kopiere_in_zwischenablage(kennung, root)

    rahmen = tk.Frame(root, padx=14, pady=12)
    rahmen.pack(fill="both", expand=True)

    tk.Label(
        rahmen,
        text=STATUS_OK if ok else STATUS_FEHLER,
        fg="#1a7f37" if ok else "#b02a37",
        font=("Segoe UI", 10, "bold"),
        wraplength=520,
        justify="left",
    ).pack(anchor="w")

    eingabe = tk.Entry(
        rahmen,
        font=("Consolas", 11),
        width=66,
        justify="center",
        state="readonly",
        readonlybackground="#f6f8fa",
    )
    if ok:
        eingabe.configure(state="normal")
        eingabe.insert(0, kennung)
        eingabe.configure(state="readonly")
    eingabe.pack(anchor="w", pady=(8, 0))

    tk.Label(
        rahmen,
        text=HINWEIS,
        wraplength=520,
        justify="left",
        font=("Segoe UI", 10),
    ).pack(anchor="w", pady=(10, 0))

    status_zeile = tk.Label(rahmen, text="", fg="#555555", font=("Segoe UI", 9))
    status_zeile.pack(anchor="w", pady=(10, 0))

    def setze_status(text: str) -> None:
        status_zeile.configure(text=text)

    def on_erneut_kopieren() -> None:
        if kopiere_in_zwischenablage(kennung, root):
            setze_status("Kopiert.")
        else:
            setze_status(
                "Kopieren nicht möglich – bitte Kennung markieren und manuell kopieren."
            )

    def on_speichern() -> None:
        inhalt = erzeuge_textinhalt(kennung)
        ziel = desktop_pfad() / DATEINAME_TXT
        try:
            speichere_textdatei(ziel, inhalt)
        except OSError:
            wahl = filedialog.asksaveasfilename(
                title="Textdatei speichern",
                defaultextension=".txt",
                initialfile=DATEINAME_TXT,
                filetypes=[("Textdateien", "*.txt"), ("Alle Dateien", "*.*")],
            )
            if not wahl:
                setze_status("Speichern abgebrochen.")
                return
            ziel = Path(wahl)
            speichere_textdatei(ziel, inhalt)
        setze_status(f"Gespeichert: {ziel}")

    schaltflaechen = tk.Frame(rahmen)
    schaltflaechen.pack(anchor="w", pady=(12, 0))

    tk.Button(
        schaltflaechen,
        text="Erneut kopieren",
        command=on_erneut_kopieren,
        state="normal" if ok else "disabled",
    ).pack(side="left", padx=(0, 8))
    tk.Button(
        schaltflaechen,
        text="Textdatei speichern",
        command=on_speichern,
        state="normal" if ok else "disabled",
    ).pack(side="left", padx=(0, 8))
    tk.Button(schaltflaechen, text="Schließen", command=root.destroy).pack(side="left")

    root.update_idletasks()
    breite = root.winfo_reqwidth()
    hoehe = root.winfo_reqheight()
    root.geometry(
        f"{breite}x{hoehe}"
        f"+{(root.winfo_screenwidth() - breite) // 2}"
        f"+{(root.winfo_screenheight() - hoehe) // 2}"
    )

    root.mainloop()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
