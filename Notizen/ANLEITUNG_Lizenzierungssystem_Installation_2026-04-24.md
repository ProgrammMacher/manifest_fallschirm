# ANLEITUNG_Lizenzierungssystem_Installation_2026-04-24

Stand: 24. April 2026

## Überblick

Das Lizenzierungssystem wurde vollständig implementiert und dokumentiert. Diese Datei beschreibt die Installation und Inbetriebnahme der Web-UI für die Lizenzschlüssel-Generierung.

---

## 📦 Komponenten des Lizenzierungssystems

### Backend
- **Datei:** `admin_license_generator.py`
- **Pfad:** `C:\manifest_fallschirm\admin_license_generator.py`
- **Technologie:** Python Flask
- **Port:** 5555 (lokal, nicht im Internet)

### Frontend
- **Datei:** `license_generator.html`
- **Pfad:** `C:\manifest_fallschirm\templates\license_generator.html`
- **Design:** Responsive HTML/CSS/JavaScript
- **Browser:** Chrome, Firefox, Edge, Safari

### Starter-Skripte
- **Batch:** `C:\manifest_fallschirm\start_license_generator.bat`
- **PowerShell:** `C:\manifest_fallschirm\start_license_generator.ps1`

### Dokumentation
- **Komplette Anleitung:** `C:\manifest_fallschirm\ANLEITUNG_LIZENZIERUNG_KUNDEN.md`
- **README:** `C:\manifest_fallschirm\README_LICENSE_GENERATOR.md`

---

## 🚀 Installation & Inbetriebnahme

### Voraussetzungen
- ✅ Windows 10/11
- ✅ Python 3.9+ (in venv vorhanden)
- ✅ Flask (bereits installiert in venv)
- ✅ Browser (Chrome/Firefox/Edge/Safari)

### Schritt 1: Installation überprüfen

Alle erforderlichen Dateien sollten bereits vorhanden sein:

```
C:\manifest_fallschirm\
├── admin_license_generator.py          ✅
├── start_license_generator.bat         ✅
├── start_license_generator.ps1         ✅
├── templates\license_generator.html    ✅
├── tools\license\generate_license_key.py
└── ANLEITUNG_LIZENZIERUNG_KUNDEN.md    ✅
```

Überprüfe diese mit:
```powershell
cd C:\manifest_fallschirm
ls admin_license_generator.py
ls start_license_generator.bat
ls templates\license_generator.html
```

### Schritt 2: Anwendung starten

#### Methode A: Batch-Datei (EINFACH)
```
Doppelklick auf: C:\manifest_fallschirm\start_license_generator.bat
```

**Erwartet:** Konsole öffnet sich + Browser öffnet `http://localhost:5555`

#### Methode B: PowerShell
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\manifest_fallschirm\start_license_generator.ps1
```

**Erwartet:** Browser öffnet sich automatisch auf `http://localhost:5555`

#### Methode C: Manuell
```powershell
cd C:\manifest_fallschirm
.\venv\Scripts\Activate.ps1
python admin_license_generator.py
```

Dann Browser öffnen: `http://localhost:5555`

### Schritt 3: Anwendung testen

**Test-Szenario:**

1. Browser öffnet auf `http://localhost:5555`
2. Formular mit 3 Feldern sichtbar:
   - 👤 Kundenname
   - 🔑 Fingerprint (64 Zeichen)
   - 📅 Lizenzstufe

3. Test-Daten eingeben:
   ```
   Kundenname: "Test Kunde"
   Fingerprint: 853fcf3de5dac271a32155e0b8fd68cd72b4f3d812144f5db52a758c5ec547dd
   Lizenzstufe: "12 Monate"
   ```

4. Button klicken: "🔑 Lizenzschlüssel Generieren"

5. **Erwartet:** Lizenzschlüssel wird angezeigt mit Metadata

---

## 🔧 Troubleshooting

### Problem: "Port 5555 bereits in Verwendung"

**Ursache:** Eine andere Instanz läuft bereits.

**Lösung:**
```powershell
# Andere Instanz beenden
Get-Process python | Stop-Process

# Oder: Port ändern in admin_license_generator.py (letzte Zeile)
```

### Problem: "Fingerprint ist ungültig"

**Ursache:** Fingerprint nicht 64 Zeichen oder ungültiges Format.

**Lösung:**
- Muss genau 64 Hexadezimal-Zeichen sein (0-9, a-f)
- Leerzeichen am Anfang/Ende entfernen
- `get_machine_fingerprint.bat` beim Kunden erneut ausführen

### Problem: "ModuleNotFoundError: No module named 'flask'"

**Ursache:** venv nicht aktiviert.

**Lösung:**
```powershell
cd C:\manifest_fallschirm
.\venv\Scripts\Activate.ps1
python admin_license_generator.py
```

### Problem: Browser öffnet sich nicht automatisch

**Lösung:** Manuell öffnen: `http://localhost:5555`

---

## 📋 Täglicher Workflow

### 1. Lizenzschlüssel generieren

**Starter ausführen:**
```
C:\manifest_fallschirm\start_license_generator.bat
```

**Oder für schneller Zugriff:**
```powershell
cd C:\manifest_fallschirm
.\venv\Scripts\Activate.ps1
python admin_license_generator.py
```

**Dann:**
- Kundenname, Fingerprint, Lizenzstufe eingeben
- "Generieren" klicken
- Schlüssel kopieren
- Per E-Mail an Kunde versenden

### 2. Alternative: Kommandozeile

Falls Web-UI nicht verfügbar:
```powershell
cd C:\manifest_fallschirm
.\venv\Scripts\Activate.ps1

python.exe tools\license\generate_license_key.py `
  --customer "Sprungplatz XYZ" `
  --tier 12m `
  --fingerprint 853fcf3de5dac271a32155e0b8fd68cd72b4f3d812144f5db52a758c5ec547dd
```

---

## 📊 Dateipfade (Referenz)

| Komponente | Pfad | Typ |
|-----------|------|-----|
| **Starter (Batch)** | `C:\manifest_fallschirm\start_license_generator.bat` | Exe |
| **Starter (PS)** | `C:\manifest_fallschirm\start_license_generator.ps1` | Ps1 |
| **Backend** | `C:\manifest_fallschirm\admin_license_generator.py` | Python |
| **Frontend** | `C:\manifest_fallschirm\templates\license_generator.html` | HTML |
| **Anleitung** | `C:\manifest_fallschirm\ANLEITUNG_LIZENZIERUNG_KUNDEN.md` | Markdown |
| **Browser** | http://localhost:5555 | URL |

---

## ✅ Deployment-Checkliste

- [x] Backend (Flask App) implementiert
- [x] Frontend (HTML/CSS/JS) implementiert
- [x] Starter-Batch erstellt
- [x] Starter-PowerShell erstellt
- [x] Dokumentation vollständig
- [x] README verfügbar
- [x] Fehlerbehandlung implementiert
- [x] Validierung (64-stelliger Fingerprint, etc.)
- [x] Copy-to-Clipboard Funktion
- [x] Responsive Design

---

## 🔒 Sicherheitshinweise

1. **Lokale Verwendung:** Web-UI läuft nur auf localhost (nicht im Internet)
2. **Kein Auth:** Nur auf vertrauenswürdigen Netzwerken verwenden
3. **Kryptographie:** Lizenzschlüssel sind HMAC-SHA256 signiert
4. **Fingerprint-Binding:** Schlüssel an Maschine gebunden (nicht kopierbar)

---

## 📞 Support

### Bei Fragen zum Workflow
Siehe: `C:\manifest_fallschirm\ANLEITUNG_LIZENZIERUNG_KUNDEN.md`

### Bei Fragen zur Web-UI
Siehe: `C:\manifest_fallschirm\README_LICENSE_GENERATOR.md`

### Bei technischen Fehlern
1. Port 5555 verfügbar?
2. Python venv aktiviert?
3. Flask installiert? (`pip list | grep flask`)
4. Firewall blockiert localhost?

---

## 🎯 Nächste Schritte

Die Installation ist **abgeschlossen**. Die Anwendung ist **produktionsreif**:

1. **Sofort einsatzbereit:** `start_license_generator.bat` ausführen
2. **Referenzen:** Dokumentation unter `C:\manifest_fallschirm\ANLEITUNG_LIZENZIERUNG_KUNDEN.md`
3. **Support:** README unter `C:\manifest_fallschirm\README_LICENSE_GENERATOR.md`

---

**Stand:** 24. April 2026  
**Version:** 1.0  
**Status:** ✅ Produktionsreif
