# Betriebsnotiz: Installer-Rebuild und Bereinigung (2026-05-22)

## Ziel

Neue Offline-Installer-Datei erzeugen, die mit den aktuellen Pfadregeln arbeitet (projektlokale Laufzeitdaten, keine externen Quellen bei Installation), und danach den Projektordner bereinigen.

## Durchgefuehrte Arbeitsschritte

1. Offline-Build gestartet ueber:
   - tools/build_inno_offline_setup.ps1
2. Build-Fehler analysiert:
   - Inno-Fehler: Invalid prototype for ProgramDataSecretsPath
3. Fix in installer/inno/manifest_offline_setup.iss umgesetzt:
   - geaendert von
     function ProgramDataSecretsPath: String;
   - auf
     function ProgramDataSecretsPath(Param: String): String;
4. Offline-Build erneut gestartet ueber:
   - tools/build_inno_offline_setup.ps1
5. Erfolgreichen Build verifiziert:
   - build/installer/manifest_ou_1_2.exe
   - LastWriteTime: 22.05.2026 22:23:01
   - Length: 109975300 Bytes
6. Build-Bereinigung durchgefuehrt (temporaere Artefakte entfernt):
   - build/.inno_build.lock
   - build/manifest_offline_compiled_installer_20260522_215620_795/
   - build/manifest_offline_compiled_installer_20260522_215620_795.zip
   - build/manifest_offline_compiled_installer_20260522_220826_985/
   - build/manifest_offline_compiled_installer_20260522_220826_985.zip
7. Ergebnis-Groesse nach Bereinigung geprueft:
   - Gesamtgroesse Projektordner: 730.89 MB

## Wichtige Hinweise

- Installer-Flow bleibt offline und verwendet keine externen Paketquellen waehrend der Installation.
- Fachlich beibehalten: Lizenzschluessel, Admin-Passwort und DB-Admin-Passwort im Setup.
- Bewusster externer Pfad bleibt nur fuer Installer-Secrets (ProgramData), wie vorgesehen.
