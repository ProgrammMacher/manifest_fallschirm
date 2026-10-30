from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools" / "fingerprint"))

import fingerprint_app  # noqa: E402
from app.security import hardware_fingerprint  # noqa: E402

APP_QUELLE = (PROJECT_ROOT / "tools" / "fingerprint" / "fingerprint_app.py").read_text(
    encoding="utf-8"
)


def test_ermittle_kennung_gleicht_hardware_fingerprint():
    erwarteter_wert = hardware_fingerprint.get_machine_fingerprint().strip().lower()
    kennung = fingerprint_app.ermittle_kennung()
    assert kennung == erwarteter_wert
    assert len(kennung) == 64
    assert all(zeichen in "0123456789abcdef" for zeichen in kennung)


def test_ermittle_kennung_uebernimmt_modulwert_und_kleinbuchstaben(monkeypatch):
    monkeypatch.setattr(
        fingerprint_app._hardware_fingerprint,
        "get_machine_fingerprint",
        lambda: "AB" * 32,
    )
    assert fingerprint_app.ermittle_kennung() == "ab" * 32


def test_ermittle_kennung_lehnt_ungueltiges_format_ab(monkeypatch):
    monkeypatch.setattr(
        fingerprint_app._hardware_fingerprint,
        "get_machine_fingerprint",
        lambda: "xyz",
    )
    with pytest.raises(ValueError):
        fingerprint_app.ermittle_kennung()


def test_app_implementiert_keine_eigene_fingerprint_berechnung():
    quelle = APP_QUELLE.lower()
    for verboten in (
        "hashlib",
        "sha256",
        "sha-256",
        "machineguid",
        "getvolumeinformation",
        "processor_identifier",
        "winreg",
        "wmic",
    ):
        assert verboten not in quelle, verboten


def test_app_importiert_kein_flask_und_kein_app_paket():
    code = (
        "import sys;"
        f"sys.path.insert(0, {str(PROJECT_ROOT / 'tools' / 'fingerprint')!r});"
        "import fingerprint_app;"
        "assert 'flask' not in sys.modules;"
        "assert 'app' not in sys.modules;"
        "print('OK')"
    )
    ergebnis = subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert ergebnis.returncode == 0, ergebnis.stderr
    assert "OK" in ergebnis.stdout


def test_app_enthält_kein_mail_und_keine_signierfunktion():
    quelle = APP_QUELLE.lower()
    for verboten in (
        "mailto",
        "smtp",
        "outlook",
        "qrcode",
        "private_key",
        "private key",
        "signing_secret",
        "generate_license",
    ):
        assert verboten not in quelle, verboten


def test_erzeuge_textinhalt_mit_allen_feldern():
    inhalt = fingerprint_app.erzeuge_textinhalt(
        "a" * 64, computername="PC-TEST", zeitstempel="01.02.2026 10:00:00"
    )
    assert "a" * 64 in inhalt
    assert "PC-TEST" in inhalt
    assert "01.02.2026 10:00:00" in inhalt
    assert "\r\n" in inhalt


def test_erzeuge_textinhalt_verwendet_standardwerte():
    inhalt = fingerprint_app.erzeuge_textinhalt("b" * 64)
    assert "b" * 64 in inhalt
    assert "Computername:" in inhalt
    assert "Datum/Uhrzeit:" in inhalt


def test_speichere_textdatei_schreibt_utf8(tmp_path):
    ziel = tmp_path / "MANIFeST_Rechnerkennung.txt"
    inhalt = fingerprint_app.erzeuge_textinhalt("c" * 64, computername="PC-ÄÖÜ")
    rueckgabe = fingerprint_app.speichere_textdatei(ziel, inhalt)
    assert rueckgabe == ziel
    assert ziel.read_bytes() == inhalt.encode("utf-8")
    assert "PC-ÄÖÜ" in ziel.read_text(encoding="utf-8")


def test_speichere_textdatei_wirft_oserror_bei_fehlendem_ordner(tmp_path):
    ziel = tmp_path / "fehlt" / "datei.txt"
    with pytest.raises(OSError):
        fingerprint_app.speichere_textdatei(ziel, "inhalt")


def test_desktop_pfad_liefert_path():
    pfad = fingerprint_app.desktop_pfad()
    assert isinstance(pfad, Path)
    assert pfad.is_absolute()


def test_oeffentliche_schnittstelle_vorhanden():
    for name in (
        "ermittle_kennung",
        "erzeuge_textinhalt",
        "speichere_textdatei",
        "desktop_pfad",
        "kopiere_in_zwischenablage",
        "main",
    ):
        assert callable(getattr(fingerprint_app, name))


BUILD_PS1 = (PROJECT_ROOT / "tools" / "fingerprint" / "build_fingerprint_exe.ps1").read_text(
    encoding="utf-8"
)
BUILD_BAT = (
    PROJECT_ROOT / "tools" / "fingerprint" / "Fingerprint EXE bauen.bat"
).read_text(encoding="utf-8")


def test_buildskript_baut_eine_fensterlose_einzel_exe_mit_64bit_pruefung():
    quelle = BUILD_PS1.lower()
    assert "--onefile" in quelle
    assert "--windowed" in quelle
    assert "--paths" in quelle
    assert "app\\security" in BUILD_PS1 or "app/security" in BUILD_PS1
    assert "calcsize" in quelle  # 64-Bit-Pruefung
    assert "'64'" in quelle or '"64"' in quelle
    assert "fingerprint_app.py" in BUILD_PS1
    assert "manifest_ou.ico" in BUILD_PS1


def test_buildskript_beruehrt_nicht_projekt_abhaengigkeiten():
    quelle = BUILD_PS1.lower()
    assert "requirements.txt" not in quelle
    assert "packages" not in quelle
    assert "runtime\\python" not in quelle
    assert "build\\fingerprint\\venv" in quelle  # eigene Build-Umgebung


def test_build_bat_ruft_build_ps1_auf():
    assert "build_fingerprint_exe.ps1" in BUILD_BAT
