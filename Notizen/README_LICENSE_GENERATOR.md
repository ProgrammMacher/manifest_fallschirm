# 🔐 License Key Generator UI

Eine einfache Web-Oberfläche zum Generieren von maschinenbindung Lizenzschlüsseln für Manifest Fallschirm.

## 🚀 Schnelleinstieg

### Methode 1: Mit Batch-Datei (Einfach)
```
Doppelklick auf: start_license_generator.bat
```

Browser öffnet sich automatisch auf: **http://localhost:5555**

### Methode 2: Mit PowerShell (Mit Browser Auto-Start)
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File start_license_generator.ps1
```

Browser öffnet sich automatisch.

### Methode 3: Manuell
```powershell
cd C:\manifest_fallschirm
.\venv\Scripts\Activate.ps1
python admin_license_generator.py
```

Dann öffne: **http://localhost:5555**

---

## 📋 Anleitung

### Schritt 1: Daten eintragen
1. **Kundenname:** Name des Sprungplatzes oder der Organisation
2. **Fingerprint:** Der 64-stellige Code vom Kunden (via `get_machine_fingerprint.bat`)
3. **Lizenzstufe:** Wähle aus:
   - 🔵 **3 Monate** (90 Tage) – Trial/Test
   - 🟡 **12 Monate** (365 Tage) – Standard
   - 🟢 **Unbegrenzt** – Premium

### Schritt 2: Generieren
- Klick auf **"🔑 Lizenzschlüssel Generieren"** Button
- Die UI prüft die Eingaben
- Lizenzschlüssel wird erzeugt

### Schritt 3: Kopieren & Versenden
- Der Lizenzschlüssel erscheint im Ergebnis-Bereich
- **"Kopieren"** Button klicken → in Zwischenablage
- In Textdatei speichern, z.B. `lizenzschluessel.txt`
- Mit `manifest_ou_1_1.exe` Installer an Kunden versenden

---

## 📊 Beispiel

**Eingaben:**
- Kundenname: `Sprungplatz Berlin`
- Fingerprint: `853fcf3de5dac271a32155e0b8fd68cd72b4f3d812144f5db52a758c5ec547dd`
- Lizenzstufe: `12 Monate`

**Ergebnis:**
```
MFS1.eyJjdXN0b21lciI6ICJTcHJ1bmdwbGF0eiBCZXJsaW4iLCAibmJmIjogMTcxOTU3NTAwMCwgImlzc3VlZF9hdCI6IDE3MTk1NzUwMDAsICJleHAiOiAxNzI3MzUxMDAwLCAiaHdmcCI6ICI4NTNmY2YzZGU1ZGFjMjcxYTMyMTU1ZTBiOGZkNjhjZDcyYjRmM2Q4MTIxNDRmNWRiNTJhNzU4YzVlYzU0N2RkIiwgInRpZXIiOiAiMTJtIn0.a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

✅ Ergebnis-Box zeigt:
- Lizenzschlüssel (kopierbar)
- Kundenname
- Gültig bis: 24.04.2027
- Fingerprint
- Zeitstempel

---

## ⚙️ Technische Details

### Dateistruktur
```
C:\manifest_fallschirm\
├── admin_license_generator.py      (Flask-Backend)
├── start_license_generator.bat     (Windows Starter)
├── start_license_generator.ps1     (PowerShell Starter)
├── templates\
│   └── license_generator.html      (Web-UI)
└── tools\license\
    └── generate_license_key.py     (Lizenz-Logik)
```

### Port
- **Lokal:** http://127.0.0.1:5555
- Nur auf diesem Rechner erreichbar (für Sicherheit)

### Browser-Kompatibilität
- ✅ Chrome / Edge / Firefox / Safari
- ✅ Responsive Design (auch auf Tablets)
- ✅ Modern JavaScript (keine Abhängigkeiten)

---

## 🔒 Sicherheit

- ❌ **Keine Authentifizierung** – Nur auf vertrauenswürdigen Netzwerken verwenden
- ✅ Server läuft nur auf **localhost** (nicht im Internet erreichbar)
- ✅ Lizenzschlüssel sind kryptographisch signiert (HMAC-SHA256)
- ✅ Fingerprints bleiben unverändert (nie gehackt/manipuliert)

---

## ❓ Troubleshooting

### "Python nicht gefunden"
```powershell
# Stelle sicher, dass Python installiert ist
python --version
```

### "Port 5555 bereits in Verwendung"
Die App läuft bereits in einem anderen Fenster. Beende es oder ändere den Port in `admin_license_generator.py`:
```python
app.run(host='127.0.0.1', port=5556, debug=False)  # Neuer Port
```

### "Fingerprint ist ungültig"
- Muss genau **64 Zeichen** lang sein
- Muss nur Hexadezimal-Zeichen (0-9, a-f) enthalten
- Leerzeichen am Anfang/Ende entfernen

---

## 📝 Workflow-Beispiel

```
WOCHE 1: Kunde anfragen
┌─────────────────────────────────────┐
│ Du → Kunde:                         │
│ "Bitte schick mir deinen Fingerprint│
│  (via get_machine_fingerprint.bat)" │
└─────────────────────────────────────┘
         ↓
WOCHE 2: Fingerprint erhalten + Lizenz generieren
┌─────────────────────────────────────┐
│ Kunde → Du:                         │
│ "Hier ist mein Fingerprint:         │
│  853fcf3de5dac271a32155e0b..."      │
└─────────────────────────────────────┘
         ↓
         DU:
         1. License Generator UI starten
         2. Fingerprint einfügen
         3. Kundenname + Lizenzstufe wählen
         4. Generieren
         5. Lizenzschlüssel kopieren
         ↓
┌─────────────────────────────────────┐
│ Du → Kunde:                         │
│ [Anhang] manifest_ou_1_1.exe        │
│ [Anhang] lizenzschluessel.txt       │
│ (mit Installationsanleitung)        │
└─────────────────────────────────────┘
         ↓
         Kunde installiert + gibt Lizenzschlüssel ein
         ↓
         ✅ App läuft mit Lizenz
```

---

## 🎯 Nächste Schritte

Nach Generierung des Lizenzschlüssels:

1. **Speichern** – In Textdatei oder E-Mail-Vorlage
2. **Versenden** – Mit `manifest_ou_1_1.exe` Installer
3. **Dokumentieren** – Notiere Kundenname + Ablaufdatum für deine Unterlagen

---

Viel Erfolg! 🚀
