# Manual: setup_start_manifest.bat

Dieses Dokument beschreibt die Funktionsweise von [setup_start_manifest.bat](setup_start_manifest.bat).

## Ziel

Mit einem einzigen Doppelklick soll die Anwendung auf einem neuen Rechner startbar sein, ohne Internet, ohne externe Paketquellen und ohne lokale System-Python-Abhaengigkeit.

Hinweis fuer Release-Erstellung:
Fuer den Bau eines verteilbaren Offline-Installer-ZIP siehe
[MANUAL_build_offline_installer_zip.md](MANUAL_build_offline_installer_zip.md).

Ablauf des Skripts:

1. Projektordner setzen
2. Lokale Python-Runtime pruefen
3. venv verwenden, falls bereits vorhanden
4. requirements strikt offline aus packages installieren
5. Kernmodule pruefen (Preflight)
6. PDF-Runtime offline selbstheilen und pruefen
7. App starten

## Voraussetzungen

1. Das Projekt liegt komplett in einem Ordner (z. B. C:\manifest_fallschirm).
2. Die lokale Runtime ist vorhanden: [runtime/python/python.exe](runtime/python/python.exe).
3. Die Datei [requirements.txt](requirements.txt) ist vorhanden.
4. Der Ordner [packages](packages) mit allen passenden .whl-Dateien ist vorhanden.
5. Fuer PDF-Export sollte zusaetzlich eine GTK-Runtime lokal vorliegen:
	- bevorzugt im Projekt unter [runtime/gtk](runtime/gtk) oder
	- als Archiv [runtime/gtk-runtime-win64.zip](runtime/gtk-runtime-win64.zip)

## Bedienung

1. Datei [setup_start_manifest.bat](setup_start_manifest.bat) per Doppelklick starten.
2. Beim ersten Start dauert es laenger, da eine vorhandene venv benutzt und Pakete bei Bedarf aktualisiert werden.
3. Danach startet die App automatisch ueber [manifest_launcher.py](manifest_launcher.py).

## Interner Ablauf im Detail

### 1) Projektordner

Das Skript wechselt mit cd /d "%~dp0" in den Ordner, in dem die .bat liegt.
Dadurch funktionieren alle relativen Pfade unabhaengig vom aktuellen Arbeitsverzeichnis.

### 2) Lokale Python-Runtime

Das Skript verwendet ausschliesslich [runtime/python/python.exe](runtime/python/python.exe).
Wenn diese Datei fehlt, wird abgebrochen.

### 3) Virtuelle Umgebung

Wenn [venv/Scripts/python.exe](venv/Scripts/python.exe) fehlt, bricht das Skript ab.
Die lokale Runtime kann in dieser Kopie keine neue venv erzeugen; fuer einen portablen Start muss die venv mitkopiert werden.
Wenn die venv schon existiert, wird sie wiederverwendet.

### 4) Abhaengigkeiten

Das Skript installiert alle Pakete aus [requirements.txt](requirements.txt) strikt offline:

"venv\Scripts\python.exe" -m pip install --no-index --find-links packages -r requirements.txt

Wenn dieser Schritt fehlschlaegt, wird abgebrochen, damit keine halbfertige Installation startet.

### 5) Kernmodule-Preflight

Vor dem Start prueft das Skript, ob die Kernpakete importierbar sind:

flask, sqlalchemy, requests, waitress

Wenn eines davon fehlt, bricht das Skript mit klarer Fehlermeldung ab.
So wird verhindert, dass die App mit unklaren Importfehlern startet.

### 6) Start der App

Vor dem Start versucht das Skript automatisch, eine fehlende PDF-Runtime offline bereitzustellen.
Die Logik liegt in [app/helpers/pdf_runtime.py](app/helpers/pdf_runtime.py) und arbeitet in dieser Reihenfolge:

1. Vorhandene [runtime/gtk/bin](runtime/gtk/bin) verwenden
2. Lokales ZIP-Archiv (z. B. [runtime/gtk-runtime-win64.zip](runtime/gtk-runtime-win64.zip)) nach runtime/gtk entpacken
3. Falls vorhanden: lokale GTK-Installation vom Rechner in runtime/gtk kopieren

Danach prueft setup_start_manifest.bat aktiv den PDF-Stack mit einem echten WeasyPrint-Test.

### 7) Start der App

Gestartet wird mit:

"venv\Scripts\python.exe" "manifest_launcher.py"

Das Skript wartet im gleichen Fenster, bis die App beendet wird, und zeigt danach den Exit-Code.

## PDF-Runtime fuer Offline-Verteilung erstellen

Zum Erstellen eines portablen GTK-Bundles auf dem Entwicklungsrechner:

1. [tools/build_offline_pdf_runtime.bat](tools/build_offline_pdf_runtime.bat) starten.
2. Das Skript kopiert eine lokal installierte GTK3-Runtime nach [runtime/gtk](runtime/gtk).
3. Zusaetzlich wird (falls moeglich) [runtime/gtk-runtime-win64.zip](runtime/gtk-runtime-win64.zip) erzeugt.

Beides kann anschliessend zusammen mit dem Projektordner auf den Zielrechner kopiert werden.

## PDF-Runtime Diagnose

Fuer eine detaillierte Analyse auf Zielrechnern gibt es nun den separaten Starter
[diagnose_pdf_runtime.bat](diagnose_pdf_runtime.bat).

Der Starter schreibt den Status in
[logs/pdf_runtime_diagnose.log](logs/pdf_runtime_diagnose.log) und prueft:

1. gefundene lokale GTK-Archive
2. vorhandene lokale GTK-Verzeichnisse
3. DLL-Status (libcairo-2.dll, libpango-1.0-0.dll, libgobject-2.0-0.dll)
4. systemweite DLL-Aufloesung via where.exe
5. finalen WeasyPrint-PDF-Test

Zusaetzlich wird vor dem finalen Test einmal die Offline-Selbstheilung
(ensure_weasyprint_pdf_runtime) ausgefuehrt.

## Fehlerbehebung

1. Meldung "Lokale Python-Runtime fehlt":
Pruefen, ob [runtime/python/python.exe](runtime/python/python.exe) im Projektordner vorhanden ist.

2. Fehler bei Paketinstallation:
Pruefen, ob der Ordner [packages](packages) komplett ist und passende Wheels fuer die Zielplattform enthaelt.

3. App startet, aber Browser oeffnet nicht:
Im Fenster auf Hinweise achten. Manuell im Browser aufrufen: http://localhost:5000/pwa

## Empfehlung fuer neue Rechner

1. Gesamten Projektordner kopieren.
2. Die venv mitkopieren; ohne sie kann der Start in der reinen Kopie nicht bootstrappen.
3. Den lokalen Wheel-Ordner [packages](packages) immer mitkopieren.
4. Direkt [setup_start_manifest.bat](setup_start_manifest.bat) starten.

## Hinweis zur Python-Laufzeit

Die Python-Laufzeit ist im Projektordner enthalten.
Es wird keine externe Python-Installation auf dem Zielrechner benoetigt.
