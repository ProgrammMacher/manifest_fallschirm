from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_installer_build_always_sources_live_app_folder_fresh():
    """Architekturvorgabe: tools/Installer bauen.bat -> build_inno_offline_setup.ps1
    muss bei JEDEM Lauf ein frisches compiled ZIP aus dem aktuellen app-Stand
    erzeugen (kein Wiederverwenden/Ueberspringen eines vorhandenen ZIPs), und
    build_offline_compiled_installer_zip.ps1 muss sein Staging-Verzeichnis vor
    dem Kopieren leeren/neu anlegen statt eine alte Kopie wiederzuverwenden."""
    orchestrator = (
        PROJECT_ROOT / "tools/build_inno_offline_setup.ps1"
    ).read_text(encoding="utf-8")

    # Der ZIP-Builder muss unconditional (nicht hinter einem "wenn Datei
    # fehlt"-Guard) bei jedem Lauf erneut aufgerufen werden.
    call_line = "& (Join-Path $ProjectRoot 'tools\\build_offline_compiled_installer_zip.ps1')"
    assert call_line in orchestrator
    call_index = orchestrator.index(call_line)
    preceding = orchestrator[:call_index]
    # Direkt davor darf kein offener "if (-not (Test-Path ... zip))" stehen,
    # der den Aufruf uebersprungen haette.
    last_if = preceding.rfind("if (")
    assert "compiledZip" not in preceding[last_if:] or "Get-LatestReadableCompiledZip" not in preceding[last_if:call_index]

    zip_builder = (
        PROJECT_ROOT / "tools/build_offline_compiled_installer_zip.ps1"
    ).read_text(encoding="utf-8")
    assert "$packageName = \"manifest_offline_compiled_installer_$timestamp\"" in zip_builder
    assert "if (Test-Path -LiteralPath $stagingRoot) {" in zip_builder
    assert "Remove-Item -LiteralPath $stagingRoot -Recurse -Force" in zip_builder
    assert "'app'," in zip_builder  # sourced directly, not a second vendored copy

    bauen_bat = (PROJECT_ROOT / "tools/Installer bauen.bat").read_text(encoding="utf-8")
    assert "build_inno_offline_setup.ps1" in bauen_bat
