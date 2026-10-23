"""
Prueft die Konsistenz von requirements.txt, packages/ und runtime/python/.

requirements.txt ist die einzige Quelle der Wahrheit.

Das Skript arbeitet AUSSCHLIESSLICH lesend:
- kein pip install, kein pip download, keine Netzwerkzugriffe
- es wird weder die Runtime-Python noch pip gestartet
- es werden keine Dateien geschrieben, geaendert oder geloescht
- keine automatische Reparatur

Gelesen werden nur Dateinamen:
- requirements.txt            (Zeilen im Format name==version)
- packages/*.whl              (Wheel-Dateinamen)
- runtime/python/Lib/site-packages/*.dist-info (Verzeichnisnamen)

Kritisch (Exit-Code 1):
- Paket aus requirements.txt fehlt in runtime/python
- Paket in runtime/python hat eine andere Version
- Wheel fuer name==version aus requirements.txt fehlt in packages/
- requirements.txt, packages/ oder runtime/python/Lib/site-packages fehlt
- Zeile in requirements.txt ist kein einfacher name==version-Pin

Warnung (Exit-Code 0):
- zusaetzliche Pakete in runtime/python, die nicht in requirements.txt stehen
- zusaetzliche Wheels in packages/, die nicht zu requirements.txt passen

Manuelle Reparatur (wird nur ausgegeben, nie ausgefuehrt):
    runtime\\python\\python.exe -m pip install --no-index --find-links=packages -r requirements.txt
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPAIR_COMMAND = (
    r"runtime\python\python.exe -m pip install --no-index "
    r"--find-links=packages -r requirements.txt"
)

# Werkzeuge, die zur Python-Installation gehoeren und nicht in
# requirements.txt stehen muessen (keine Warnung).
IGNORED_EXTRA_PACKAGES = frozenset({"pip", "setuptools", "wheel"})

_PIN_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([A-Za-z0-9][A-Za-z0-9._+!-]*)$")


def normalize_name(name: str) -> str:
    """PEP 503: Gross-/Kleinschreibung sowie '-', '_' und '.' sind gleichwertig."""
    return re.sub(r"[-_.]+", "-", name).strip().lower()


def normalize_version(version: str) -> str:
    return version.strip().lower()


def parse_requirements(path: Path) -> tuple[dict[str, tuple[str, str]], list[str]]:
    """Liefert {normalisierter Name: (Anzeigename, Version)} und Problemmeldungen."""
    pins: dict[str, tuple[str, str]] = {}
    problems: list[str] = []

    text = path.read_text(encoding="utf-8-sig")
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = re.split(r"\s+#", line, maxsplit=1)[0].strip()

        match = _PIN_RE.match(line)
        if not match:
            problems.append(
                f"Zeile {number}: nicht unterstuetzt (erwartet name==version): {raw.strip()}"
            )
            continue

        display, version = match.group(1), normalize_version(match.group(2))
        key = normalize_name(display)
        if key in pins and pins[key][1] != version:
            problems.append(f"Zeile {number}: {display} mehrfach mit unterschiedlicher Version")
            continue
        pins[key] = (display, version)

    return pins, problems


def read_installed(site_packages: Path) -> dict[str, set[str]]:
    """Liest installierte Distributionen aus den *.dist-info-Verzeichnisnamen."""
    installed: dict[str, set[str]] = {}
    for entry in site_packages.iterdir():
        if not entry.is_dir() or not entry.name.endswith(".dist-info"):
            continue
        stem = entry.name[: -len(".dist-info")]
        if "-" not in stem:
            continue
        name, version = stem.rsplit("-", 1)
        installed.setdefault(normalize_name(name), set()).add(normalize_version(version))
    return installed


def read_wheels(packages_dir: Path) -> dict[str, set[str]]:
    """Liest Name und Version aus den Wheel-Dateinamen (name-version-...-.whl)."""
    wheels: dict[str, set[str]] = {}
    for entry in packages_dir.iterdir():
        if not entry.is_file() or entry.suffix.lower() != ".whl":
            continue
        parts = entry.name[: -len(".whl")].split("-")
        if len(parts) < 5:
            continue
        wheels.setdefault(normalize_name(parts[0]), set()).add(normalize_version(parts[1]))
    return wheels


def compare(
    pins: dict[str, tuple[str, str]],
    installed: dict[str, set[str]],
    wheels: dict[str, set[str]],
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Vergleicht und liefert (kritische Abweichungen, Warnungen) nach Kategorie."""
    errors: dict[str, list[str]] = {
        "missing_runtime": [],
        "version_runtime": [],
        "missing_wheel": [],
    }
    warnings: dict[str, list[str]] = {"extra_runtime": [], "extra_wheels": []}

    for key in sorted(pins):
        display, version = pins[key]

        runtime_versions = installed.get(key)
        if not runtime_versions:
            errors["missing_runtime"].append(f"{display}=={version}")
        elif runtime_versions != {version}:
            found = ", ".join(sorted(runtime_versions))
            errors["version_runtime"].append(
                f"{display}: requirements.txt={version}, runtime={found}"
            )

        if version not in wheels.get(key, set()):
            errors["missing_wheel"].append(f"{display}=={version}")

    for key in sorted(installed):
        if key in IGNORED_EXTRA_PACKAGES or key in pins:
            continue
        for version in sorted(installed[key]):
            warnings["extra_runtime"].append(f"{key}=={version}")

    for key in sorted(wheels):
        for version in sorted(wheels[key]):
            if key not in pins or pins[key][1] != version:
                warnings["extra_wheels"].append(f"{key}=={version}")

    return errors, warnings


def _print_block(title: str, items: list[str], stream) -> None:
    if not items:
        return
    print(f"\n{title}", file=stream)
    for item in items:
        print(f"  - {item}", file=stream)


def run(project_root: Path) -> int:
    requirements_file = project_root / "requirements.txt"
    packages_dir = project_root / "packages"
    site_packages = project_root / "runtime" / "python" / "Lib" / "site-packages"

    print("[INFO] Pruefe Runtime-Konsistenz (nur lesend) ...")

    structural: list[str] = []
    if not requirements_file.is_file():
        structural.append(f"requirements.txt fehlt: {requirements_file}")
    if not packages_dir.is_dir():
        structural.append(f"packages-Ordner fehlt: {packages_dir}")
    if not site_packages.is_dir():
        structural.append(f"Runtime-site-packages fehlt: {site_packages}")

    if structural:
        print("\n[FEHLER] Pruefung nicht moeglich:", file=sys.stderr)
        for item in structural:
            print(f"  - {item}", file=sys.stderr)
        print(f"\nManuelle Reparatur:\n  {REPAIR_COMMAND}", file=sys.stderr)
        return 1

    pins, parse_problems = parse_requirements(requirements_file)
    installed = read_installed(site_packages)
    wheels = read_wheels(packages_dir)
    errors, warnings = compare(pins, installed, wheels)

    print(f"  requirements.txt : {len(pins)} Pakete")
    print(f"  packages/        : {sum(len(v) for v in wheels.values())} Wheels")
    print(f"  runtime/python   : {sum(len(v) for v in installed.values())} Distributionen")

    has_errors = bool(parse_problems) or any(errors.values())

    if has_errors:
        err = sys.stderr
        print("\n[FEHLER] Runtime-Drift erkannt - kritische Abweichungen:", file=err)
        _print_block("Ungueltige requirements.txt-Eintraege:", parse_problems, err)
        _print_block("Fehlt in runtime/python (laut requirements.txt):", errors["missing_runtime"], err)
        _print_block("Falsche Version in runtime/python:", errors["version_runtime"], err)
        _print_block("Wheel fehlt in packages/ (laut requirements.txt):", errors["missing_wheel"], err)

    warning_count = sum(len(v) for v in warnings.values())
    if warning_count:
        print(f"\n[WARNUNG] {warning_count} zusaetzliche Eintraege (blockiert nicht):")
        _print_block(
            "In runtime/python installiert, aber nicht in requirements.txt:",
            warnings["extra_runtime"],
            sys.stdout,
        )
        _print_block(
            "In packages/ vorhanden, aber nicht in requirements.txt:",
            warnings["extra_wheels"],
            sys.stdout,
        )

    if has_errors:
        print(
            "\nManuelle Reparatur (wird NICHT automatisch ausgefuehrt):\n"
            f"  {REPAIR_COMMAND}\n"
            "Fehlt ein Wheel in packages/, muss es zuerst ergaenzt werden. "
            "requirements.txt bleibt die Quelle der Wahrheit.",
            file=sys.stderr,
        )
        return 1

    print("\n[OK] requirements.txt, packages/ und runtime/python sind konsistent.")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Prueft (nur lesend) requirements.txt, packages/ und runtime/python "
            "auf Konsistenz. Exit-Code 0 = OK (auch bei Warnungen), "
            "1 = kritische Abweichung."
        )
    )
    parser.add_argument(
        "--project-root",
        default=str(Path(__file__).resolve().parent.parent),
        help="Projektwurzel (Standard: Elternordner von tools/)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return run(Path(args.project_root).resolve())


if __name__ == "__main__":
    raise SystemExit(main())

