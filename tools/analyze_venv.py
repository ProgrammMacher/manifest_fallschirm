#!/usr/bin/env python3
"""
Analyse-Script für eine Python Virtual Environment (venv)

Zeigt:
- installierte Pakete
- ungefähre Größe pro Paket
- bekannte "Heavy Packages"
- Verschlankungspotential

Nur lesend, KEINE Änderungen.
"""

import site
from pathlib import Path
from collections import defaultdict

# ------------------------------------------------------------
# Konfiguration
# ------------------------------------------------------------

HEAVY_KEYWORDS = {
    "numpy",
    "pandas",
    "scipy",
    "sklearn",
    "matplotlib",
    "tensorflow",
    "torch",
    "opencv",
    "cv2",
    "pillow",
}

DEV_KEYWORDS = {
    "pytest",
    "black",
    "flake8",
    "mypy",
    "ipython",
    "jupyter",
}

# ------------------------------------------------------------
# Hilfsfunktionen
# ------------------------------------------------------------

def folder_size(path: Path) -> int:
    return sum(
        f.stat().st_size
        for f in path.rglob("*")
        if f.is_file()
    )

def human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"

# ------------------------------------------------------------
# Site-packages finden
# ------------------------------------------------------------

site_packages = None
for p in site.getsitepackages():
    if "site-packages" in p:
        site_packages = Path(p)
        break

if not site_packages or not site_packages.exists():
    print("❌ site-packages nicht gefunden")
    exit(1)

# ------------------------------------------------------------
# Pakete sammeln
# ------------------------------------------------------------

packages = defaultdict(int)

for item in site_packages.iterdir():
    if item.name.endswith(".dist-info"):
        pkg_name = item.name.split("-")[0].lower()
        packages[pkg_name] += folder_size(item)
    elif item.is_dir():
        packages[item.name.lower()] += folder_size(item)

# ------------------------------------------------------------
# Ausgabe
# ------------------------------------------------------------

print("\n📦 VENV-Paketanalyse")
print("=" * 60)

total_size = sum(packages.values())

print(f"📂 site-packages: {site_packages}")
print(f"📏 Gesamtgröße: {human(total_size)}")
print("-" * 60)

sorted_pkgs = sorted(packages.items(), key=lambda x: x[1], reverse=True)

for name, size in sorted_pkgs:
    flags = []

    if name in HEAVY_KEYWORDS:
        flags.append("HEAVY")
    if name in DEV_KEYWORDS:
        flags.append("DEV")

    flag_text = f"  <-- {', '.join(flags)}" if flags else ""
    print(f"{name:30} {human(size):>10}{flag_text}")

print("=" * 60)

# ------------------------------------------------------------
# Bewertung
# ------------------------------------------------------------

print("\n🔍 Bewertung & Hinweise")

heavy_found = [n for n in packages if n in HEAVY_KEYWORDS]
dev_found = [n for n in packages if n in DEV_KEYWORDS]

if heavy_found:
    print("⚠️ Große Pakete gefunden (prüfen, ob wirklich nötig):")
    for n in heavy_found:
        print(f"  - {n}")
else:
    print("✅ Keine typischen Heavy-Packages gefunden")

if dev_found:
    print("\n⚠️ Dev-Tools in der venv (für Produktion meist unnötig):")
    for n in dev_found:
        print(f"  - {n}")
else:
    print("\n✅ Keine Dev-Tools in der venv")

print("\n✅ Analyse abgeschlossen (keine Änderungen vorgenommen)")