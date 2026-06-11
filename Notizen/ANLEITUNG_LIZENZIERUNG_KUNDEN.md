# 📋 Anleitung: Maschinenbindung & Lizenzierung für Manifest Fallschirm

**Gesamtablauf:**

```
👤 KUNDE:     Erzeugt Fingerprint (mit get_machine_fingerprint.bat)
                    ↓
💻 DU:        Generierst Lizenzschlüssel (Web-UI oder Kommandozeile)
                    ↓
💻 DU:        Schickst Installer + Lizenzschlüssel an Kunde
                    ↓
👤 KUNDE:     Installiert mit Lizenzschlüssel
```

---

# 🟢 EMPFOHLEN: Web-UI (License Generator)

Eine benutzerfreundliche Browseroberfläche zum Generieren von Lizenzschlüsseln.

## 🚀 Schnellstart der Web-UI

### **Schritt 1: Anwendung starten**

#### **Methode A: Mit Batch-Datei (Einfachste Methode – EMPFOHLEN)**

Doppelklick auf diese Datei:
```
C:\manifest_fallschirm\start_license_generator.bat
```

Der Browser öffnet sich automatisch auf: **http://localhost:5555**

#### **Methode B: Mit PowerShell**

Öffne PowerShell und führe aus:
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\manifest_fallschirm\start_license_generator.ps1
```

Der Browser öffnet sich automatisch.

#### **Methode C: Manuell (Kommandozeile)**

```powershell
cd C:\manifest_fallschirm
.\venv\Scripts\Activate.ps1
python admin_license_generator.py
```

Öffne dann im Browser: **http://localhost:5555**

---

### **Schritt 2: Web-UI verwenden**

Die Seite zeigt ein einfaches Formular mit 3 Feldern:

#### **Feld 1: Kundenname**
- **Was eingeben:** Name des Sprungplatzes oder der Organisation
- **Beispiel:** `Sprungplatz Berlin` oder `Fallschirmclub München`

#### **Feld 2: Fingerprint**
- **Was eingeben:** Der 64-stellige Code vom Kunden
- **Wo bekommt man ihn:** Kunde führt `get_machine_fingerprint.bat` aus
- **Beispiel:**
  ```
  853fcf3de5dac271a32155e0b8fd68cd72b4f3d812144f5db52a758c5ec547dd
  ```

#### **Feld 3: Lizenzstufe**
Wähle eine der folgenden Optionen:
- **🔵 3 Monate (90 Tage)** → Trial/Test-Lizenz
- **🟡 12 Monate (365 Tage)** → Standard-Lizenz
- **🟢 Unbegrenzt** → Premium-Lizenz (läuft nie ab)

---

### **Schritt 3: Lizenzschlüssel generieren**

1. Alle 3 Felder ausfüllen
2. Button klicken: **"🔑 Lizenzschlüssel Generieren"**
3. Warten (< 1 Sekunde)

**Ergebnis:** Die Web-UI zeigt den generierten Lizenzschlüssel

---

### **Schritt 4: Lizenzschlüssel kopieren**

Im Ergebnis-Bereich erscheinen mehrere Informationen:

| Info | Beschreibung |
|------|-------------|
| **Lizenzschlüssel** | Der lange Code (mit "MFS1." am Anfang) – **Kopieren Button klicken!** |
| **Kundenname** | Der eingegebene Name (zur Kontrolle) |
| **Gültig bis** | Ablaufdatum der Lizenz |
| **Fingerprint** | Der Fingerprint des Kunden (zur Kontrolle) |
| **Generiert am** | Zeitstempel |

**Kopieren:**
- Klick auf den **"Kopieren"** Button neben dem Lizenzschlüssel
- Der Schlüssel ist jetzt in der Zwischenablage

---

### **Schritt 5: An Kunden versenden**

Schreibe eine E-Mail mit:

1. **Installer-Datei (als Anhang):**
   ```
  C:\manifest_fallschirm\build\installer\manifest_ou_1_2.exe
   ```

2. **Lizenzschlüssel (im Body oder als Textdatei):**
   - Kopierte Lizenzschlüssel-Zeichenfolge einfügen
   - Oder: In Textdatei speichern (z.B. `lizenzschluessel.txt`) und als Anhang mitschicken

**E-Mail-Vorlage:**

> **Betreff:** Manifest Fallschirm – Installation & Lizenzschlüssel
>
> ---
>
> Hallo,
>
> anbei finden Sie:
> - `manifest_ou_1_2.exe` – Der Installer für Manifest Fallschirm
> - `lizenzschluessel.txt` – Ihr persönlicher Lizenzschlüssel
>
> **Installationsschritte:**
> 1. Doppelklick auf `manifest_ou_1_2.exe`
> 2. Im Installationswizard: Lizenzschlüssel einfügen (aus lizenzschluessel.txt)
> 3. Admin-Passwort setzen
> 4. Installation abschließen
>
> Nach der Installation starten Sie die App und sehen Ihre Lizenzstufe in der Sidebar (unten rechts).
>
> Bei Fragen: Kontaktieren Sie uns gerne.

---

## 📊 Dateipfade für Web-UI

| Aktion | Datei | Pfad |
|--------|-------|------|
| **Anwendung starten** | `start_license_generator.bat` | `C:\manifest_fallschirm\start_license_generator.bat` |
| **Alternative (PowerShell)** | `start_license_generator.ps1` | `C:\manifest_fallschirm\start_license_generator.ps1` |
| **Backend-Code** | `admin_license_generator.py` | `C:\manifest_fallschirm\admin_license_generator.py` |
| **Frontend (UI)** | `license_generator.html` | `C:\manifest_fallschirm\templates\license_generator.html` |
| **Browser-Adresse** | – | **http://localhost:5555** |
| **Installer für Kunde** | `manifest_ou_1_2.exe` | `C:\manifest_fallschirm\build\installer\manifest_ou_1_2.exe` |
| **Fingerprint-Skript für Kunde** | `get_machine_fingerprint.bat` | `C:\manifest_fallschirm\tools\license\get_machine_fingerprint.bat` |

---

---

# 🟠 ALTERNATIV: Kommandozeile (Manuell)

Wenn du die Web-UI nicht verwenden möchtest, kannst du Lizenzschlüssel auch per PowerShell generieren.

## Schritt 1: PowerShell öffnen

```powershell
cd C:\manifest_fallschirm
.\venv\Scripts\Activate.ps1
```

## Schritt 2: Lizenzschlüssel generieren

Nachdem Kunde den Fingerprint geschickt hat, führe einen dieser Befehle aus:

### **3-Monate Lizenz (Trial)**
```powershell
python.exe tools\license\generate_license_key.py `
  --customer "Sprungplatz XYZ" `
  --tier 3m `
  --fingerprint 853fcf3de5dac271a32155e0b8fd68cd72b4f3d812144f5db52a758c5ec547dd
```

### **12-Monate Lizenz (Standard)**
```powershell
python.exe tools\license\generate_license_key.py `
  --customer "Sprungplatz XYZ" `
  --tier 12m `
  --fingerprint 853fcf3de5dac271a32155e0b8fd68cd72b4f3d812144f5db52a758c5ec547dd
```

### **Unbegrenzte Lizenz (Premium)**
```powershell
python.exe tools\license\generate_license_key.py `
  --customer "Sprungplatz XYZ" `
  --tier unlimited `
  --fingerprint 853fcf3de5dac271a32155e0b8fd68cd72b4f3d812144f5db52a758c5ec547dd
```

### **Alle 3 auf einmal (Bundle)**
```powershell
python.exe tools\license\generate_license_bundle.py `
  --customer "Sprungplatz XYZ" `
  --fingerprint 853fcf3de5dac271a32155e0b8fd68cd72b4f3d812144f5db52a758c5ec547dd
```

**Ergebnis:** Die Kommandozeile zeigt den generierten Lizenzschlüssel (lange Zeichenfolge ab `MFS1.`)

## Schritt 3: Lizenzschlüssel kopieren & versenden

Wie im Web-UI Workflow: Kopieren und an Kunde versenden (mit `manifest_ou_1_2.exe`)

---

## 📊 Dateipfade für Kommandozeile

| Aktion | Datei | Pfad |
|--------|-------|------|
| **Arbeitsverzeichnis** | – | `C:\manifest_fallschirm` |
| **Lizenz-Generator (einzeln)** | `generate_license_key.py` | `C:\manifest_fallschirm\tools\license\generate_license_key.py` |
| **Lizenz-Bundle (alle 3)** | `generate_license_bundle.py` | `C:\manifest_fallschirm\tools\license\generate_license_bundle.py` |
| **Python venv** | `Activate.ps1` | `C:\manifest_fallschirm\venv\Scripts\Activate.ps1` |
| **Installer für Kunde** | `manifest_ou_1_2.exe` | `C:\manifest_fallschirm\build\installer\manifest_ou_1_2.exe` |

---

---

# 🔴 PHASE 1: KUNDE erzeugt Fingerprint

### Datei die du dem KUNDEN schickst

Schicke diese Datei per E-Mail an den Kunden:
```
C:\manifest_fallschirm\tools\license\get_machine_fingerprint.bat
```

Oder kopiere die Datei auf einen USB-Stick.

### 📧 E-Mail-Vorlage für Kunden

> **Betreff:** Fingerprint für Manifest Fallschirm erforderlich
>
> ---
>
> Hallo,
>
> um die Manifest-Fallschirm-App auf Ihrem Rechner zu installieren, benötige ich einen eindeutigen **Fingerprint** (eine Maschinen-Kennung). Dies ist notwendig, um die Lizenz an Ihren Rechner zu binden.
>
> **Bitte tun Sie folgendes:**
>
> 1. Speichern Sie die beigefügte Datei: `get_machine_fingerprint.bat` auf Ihren Desktop
> 2. Doppelklick auf die Datei
> 3. Ein schwarzes Fenster öffnet sich und zeigt eine lange Zeichenfolge (64 Zeichen)
> 4. **Die komplette Zeichenfolge markieren und kopieren (Strg+C)**
> 5. **Die Zeichenfolge per E-Mail zurückschicken**
>
> **Beispiel (so sieht Ihre Ausgabe aus):**
> ```
> 853fcf3de5dac271a32155e0b8fd68cd72b4f3d812144f5db52a758c5ec547dd
> ```
>
> ℹ️ **Wichtig:**
> - Die Datei können Sie danach löschen
> - Der Fingerprint ist eindeutig für Ihren Rechner
> - Er wird benötigt, um die Lizenz zu generieren
>
> Danke und bis bald!

### Was der Fingerprint ist
- **Eindeutig:** Jeder Rechner hat einen eigenen, unterschiedlichen Code
- **Hardware-basiert:** Wird berechnet aus CPU-ID, Motherboard, Festplatte, etc.
- **Unveränderlich:** Bleibt gleich, solange die Hardware nicht ausgetauscht wird
- **Sicher:** 64-stelliger SHA256-Hash, nicht umkehrbar
- **Sicherheitszweck:** Wird verwendet, um die Lizenz an diesen einen Rechner zu binden – kann nicht kopiert werden

---

---

# 🟡 PHASE 2: DU generierst Lizenzschlüssel

Nach Erhalt des Fingerprints vom Kunden:

### Option 1: Web-UI verwenden (EINFACHER ✨)

**Anwendung starten:**
```
Doppelklick auf: C:\manifest_fallschirm\start_license_generator.bat
```

**Dann:**
1. Browser öffnet sich automatisch
2. Kundenname eingeben
3. Fingerprint einfügen
4. Lizenzstufe wählen
5. "Lizenzschlüssel Generieren" klicken
6. Lizenzschlüssel kopieren

**Vorteil:** Schnell, fehlerfreundlich, übersichtlich

---

### Option 2: Kommandozeile verwenden (ALTERNATIV)

**PowerShell öffnen und ausführen:**

```powershell
cd C:\manifest_fallschirm
.\venv\Scripts\Activate.ps1

python.exe tools\license\generate_license_key.py `
  --customer "Sprungplatz XYZ" `
  --tier 12m `
  --fingerprint 853fcf3de5dac271a32155e0b8fd68cd72b4f3d812144f5db52a758c5ec547dd
```

**Ergebnis:** Lizenzschlüssel wird angezeigt

---

### Lizenzschlüssel Speichern

Der Schlüssel sieht so aus:
```
MFS1.eyJjdXN0b21lciI6ICJTcHJ1bmdwbGF0eiBCZXJsaW4iLCAibmJmIjogMTcxOTU3NTAwMCwgImlzc3VlZF9hdCI6IDE3MTk1NzUwMDAsICJleHAiOiAxNzI3MzUxMDAwLCAiaHdmcCI6ICI4NTNmY2YzZGU1ZGFjMjcxYTMyMTU1ZTBiOGZkNjhjZDcyYjRmM2Q4MTIxNDRmNWRiNTJhNzU4YzVlYzU0N2RkIiwgInRpZXIiOiAiMTJtIn0.a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

**In Textdatei speichern:**
1. Notepad öffnen
2. Schlüssel einfügen (Strg+V)
3. Speichern als: `lizenzschluessel.txt`

---

---

# 🟢 PHASE 3: DU schickst Installer + Lizenzschlüssel

### Dateien vorbereiten

**Installer:**
```
C:\manifest_fallschirm\build\installer\manifest_ou_1_2.exe
```

**Lizenzschlüssel-Datei:**
```
lizenzschluessel.txt
(mit dem in Phase 2 generierten Schlüssel)
```

### E-Mail an Kunden

Schreibe eine neue E-Mail mit **2 Anhängen**:

> **Betreff:** Manifest Fallschirm – Installation & Lizenzschlüssel
>
> ---
>
> Hallo,
>
> anbei finden Sie alles, was Sie zum Installieren benötigen:
>
> **Anhänge:**
> - `manifest_ou_1_2.exe` – Der Installer
> - `lizenzschluessel.txt` – Ihr persönlicher Lizenzschlüssel
>
> **Installationsschritte:**
>
> 1. Speichern Sie beide Dateien in einen Ordner (z.B. Desktop)
> 2. Öffnen Sie `lizenzschluessel.txt` und **kopieren Sie den kompletten Lizenzschlüssel** (alles von `MFS1.` bis zum letzten Zeichen)
> 3. Doppelklick auf `manifest_ou_1_2.exe`
> 4. Der Installationswizard öffnet sich
> 5. Im Feld "Lizenzschlüssel" die kopierte Zeichenfolge einfügen
> 6. **Admin-Passwort** setzen (für App-Verwaltung)
> 7. **DB-Admin-Passwort** setzen (für Datenbank)
> 8. Installation fertigstellen
>
> Nach der Installation:
> - Die App startet automatisch
> - In der Sidebar (unten rechts) sehen Sie Ihre Lizenzstufe und das Ablaufdatum
>
> **Wichtig:**
> - Der Lizenzschlüssel ist an **Ihren Rechner gebunden** und funktioniert nur dort
> - Falls Sie die Hardware wechseln, ist ein neuer Lizenzschlüssel erforderlich
> - Teilen Sie den Lizenzschlüssel nicht mit anderen – er funktioniert nur auf Ihrem Rechner
>
> Bei Fragen oder Problemen kontaktieren Sie uns gerne.

---

---

# 🔵 PHASE 4: KUNDE installiert

### Kunde führt aus

**Schritt 1: Dateien speichern**
- `manifest_ou_1_2.exe`
- `lizenzschluessel.txt`

**Schritt 2: Lizenzschlüssel vorbereiten**
- `lizenzschluessel.txt` öffnen
- Kompletten Lizenzschlüssel kopieren (von `MFS1.` bis Ende)

**Schritt 3: Installer starten**
- Doppelklick auf `manifest_ou_1_2.exe`
- Installationswizard öffnet sich

**Schritt 4: Lizenzschlüssel eingeben**
- Im Wizard beim Punkt "Lizenzschlüssel": Die kopierte Zeichenfolge einfügen
- Weiter

**Schritt 5: Passwörter setzen**
- Admin-Passwort wählen und eingeben
- DB-Admin-Passwort wählen und eingeben
- Weiter

**Schritt 6: Installation abschließen**
- Installation läuft (dauert ~1-2 Minuten)
- Danach startet die App automatisch

**Schritt 7: Lizenz überprüfen**
- App lädt
- **Sidebar unten rechts zeigt:**
  - Lizenzstufe (z.B. "12 Monate")
  - Ablaufdatum (z.B. "Gültig bis: 24.04.2027")

✅ **Fertig! App läuft mit Lizenz.**

---

---

# 📊 Komplette Dateipfad-Übersicht

## Für Web-UI (EMPFOHLEN)

| Verwendung | Datei | Pfad | Aktion |
|------------|-------|------|--------|
| **Starten** | `start_license_generator.bat` | `C:\manifest_fallschirm\start_license_generator.bat` | Doppelklick |
| **Starten (PS)** | `start_license_generator.ps1` | `C:\manifest_fallschirm\start_license_generator.ps1` | PowerShell ausführen |
| **Backend** | `admin_license_generator.py` | `C:\manifest_fallschirm\admin_license_generator.py` | Intern verwendet |
| **Frontend** | `license_generator.html` | `C:\manifest_fallschirm\templates\license_generator.html` | Intern verwendet |
| **Browser öffnen** | – | **http://localhost:5555** | Nach Start |

## Für Kommandozeile (ALTERNATIV)

| Verwendung | Datei | Pfad | Befehl |
|------------|-------|------|--------|
| **Einzelner Schlüssel** | `generate_license_key.py` | `C:\manifest_fallschirm\tools\license\generate_license_key.py` | `python.exe tools\license\generate_license_key.py --customer "..." --tier 12m --fingerprint "..."` |
| **Alle 3 Schlüssel** | `generate_license_bundle.py` | `C:\manifest_fallschirm\tools\license\generate_license_bundle.py` | `python.exe tools\license\generate_license_bundle.py --customer "..." --fingerprint "..."` |

## Für Kunden

| Verwendung | Datei | Pfad | Aktion |
|------------|-------|------|--------|
| **Fingerprint erzeugen** | `get_machine_fingerprint.bat` | `C:\manifest_fallschirm\tools\license\get_machine_fingerprint.bat` | Per E-Mail schicken |
| **Installer** | `manifest_ou_1_2.exe` | `C:\manifest_fallschirm\build\installer\manifest_ou_1_2.exe` | Per E-Mail schicken |

---

---

# 💡 Schritt-für-Schritt Workflow-Beispiel

### **Szenario: "Sprungplatz Berlin" möchte Lizenz**

**🗓️ Tag 1 – Anfrage**
```
Du schickst E-Mail an Kunde:
- get_machine_fingerprint.bat (Anhang)
- Anleitung (siehe oben)
```

**🗓️ Tag 2 – Fingerprint empfangen**
```
Kunde antwortet mit Fingerprint:
"853fcf3de5dac271a32155e0b8fd68cd72b4f3d812144f5db52a758c5ec547dd"
```

**🗓️ Tag 2 – Lizenzschlüssel generieren**
```
Du:
1. C:\manifest_fallschirm\start_license_generator.bat ausführen
2. Web-UI öffnet sich
3. Eingeben:
   - Kundenname: "Sprungplatz Berlin"
   - Fingerprint: "853fcf3de5dac271a32155e0b..."
   - Lizenzstufe: "12 Monate"
4. Klick: "Lizenzschlüssel Generieren"
5. Lizenzschlüssel kopieren
```

**🗓️ Tag 2/3 – An Kunde versenden**
```
Du schickst E-Mail mit:
- manifest_ou_1_2.exe (Anhang)
- lizenzschluessel.txt (Anhang)
- Installationsanleitung (Body)
```

**🗓️ Tag 3 – Installation beim Kunden**
```
Kunde:
1. Beide Dateien speichern
2. Lizenzschluessel.txt öffnen → Schlüssel kopieren
3. manifest_ou_1_2.exe doppelklicken
4. Im Wizard: Lizenzschlüssel einfügen
5. Passwörter setzen
6. Installation
7. App startet → Lizenz sichtbar ✅
```

---

---

# ❓ FAQ

**F: Welche Methode ist einfacher – Web-UI oder Kommandozeile?**  
A: Die **Web-UI ist deutlich einfacher** – kein Fehlerrisiko, übersichtlicher, schneller. Wir empfehlen: `start_license_generator.bat` ausführen.

**F: Wo finde ich den generierten Lizenzschlüssel?**  
A: 
- **Web-UI:** Im Browser sichtbar (mit Copy-Button)
- **Kommandozeile:** In der Konsole angezeigt

**F: Was passiert, wenn die Lizenz abläuft?**  
A: Die App startet nicht mehr. Kunde muss neuen Fingerprint liefern → Du generierst neuen Schlüssel.

**F: Kann ich einen Lizenzschlüssel mehrmals verwenden?**  
A: Nein. Er ist an den Fingerprint des Zielrechners gebunden. Auf anderen Rechnern funktioniert er nicht.

**F: Was, wenn Hardware wechselt?**  
A: Der Fingerprint ändert sich → Neuer Lizenzschlüssel erforderlich.

**F: Wie lange dauert die Generierung?**  
A: < 1 Sekunde.

**F: Kann der Lizenzschlüssel gehackt werden?**  
A: Nein. Er ist kryptographisch signiert (HMAC-SHA256).

**F: Ist die Web-UI sicher?**  
A: Ja. Sie läuft nur auf localhost (nicht im Internet erreichbar). Nur auf vertrauenswürdigen Netzwerken verwenden.

**F: Kann ich die Web-UI im Netzwerk freigeben?**  
A: Nicht empfohlen (Sicherheit). Sie ist für lokale Verwendung ausgelegt. Für mehrere Benutzer: Jeweils eine Instanz starten oder auf Port 5556+ konfigurieren.

---

---

# 🎯 Zusammenfassung: Was du wo findest

## Schnellstart
```
1. Hier klicken: C:\manifest_fallschirm\start_license_generator.bat
2. Warten bis Browser öffnet (http://localhost:5555)
3. Formular ausfüllen → Generieren → Kopieren → Versenden
```

## Wichtige Dateipfade
| Was | Pfad |
|-----|------|
| **Web-UI Starter (EMPFOHLEN)** | `C:\manifest_fallschirm\start_license_generator.bat` |
| **Web-UI Starter (PowerShell)** | `C:\manifest_fallschirm\start_license_generator.ps1` |
| **Installer für Kunde** | `C:\manifest_fallschirm\build\installer\manifest_ou_1_2.exe` |
| **Fingerprint Script** | `C:\manifest_fallschirm\tools\license\get_machine_fingerprint.bat` |
| **Kommandozeile (einzeln)** | `python.exe tools\license\generate_license_key.py` |
| **Kommandozeile (3er-Bundle)** | `python.exe tools\license\generate_license_bundle.py` |

## Browser-Adresse (nach Start)
```
http://localhost:5555
```

## Dateiverwaltung während des Workflows

| Phase | Datei | Wo | Aktion |
|-------|-------|----|----|
| **Phase 1** | `get_machine_fingerprint.bat` | Zu Kunde | Per E-Mail schicken |
| **Phase 2** | `start_license_generator.bat` | Bei dir | Ausführen → Lizenz generieren |
| **Phase 3** | `manifest_ou_1_2.exe` | Zu Kunde | Per E-Mail schicken |
| **Phase 3** | `lizenzschluessel.txt` | Zu Kunde | Per E-Mail schicken |
| **Phase 4** | – | Beim Kunden | Installation + Lizenzschlüssel eingeben |

---

**Viel Erfolg bei der Lizenzierung! 🚀**
