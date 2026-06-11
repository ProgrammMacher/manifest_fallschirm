#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
find_unused_modules.py

Findet Python-Module (.py Dateien) in einem Projekt, die NICHT (statisch) über Imports
von definierten Entrypoints aus erreichbar sind.

- Baut ein Import-Graphen via ast.parse()
- Unterstützt: import x, import x as y, from x import y, from . import y, from ..x import y
- Markiert alle Module, die von Entrypoints aus transitiv importiert werden, als "used"
- Listet übrige .py Dateien als "unused candidates"

Einschränkungen:
- dynamische Imports (importlib, __import__) werden nicht erkannt
- Nutzung über Strings, Konfiguration, Reflection nicht erkannt
- Template-/Jinja-Nutzung von Python-Dateien zählt nicht als Import

Benutzung:
  python tools/find_unused_modules.py --root C:\\manifest_fallschirm --entry run.py
  python tools/find_unused_modules.py --root . --entry run.py --entry app/__init__.py
"""

import argparse
import ast
import os
import sys
from pathlib import Path
from typing import Dict, Set, List, Tuple, Optional

DEFAULT_EXCLUDE_DIRS = {
    "__pycache__", ".git", ".hg", ".svn", ".idea", ".vscode",
    "venv", ".venv", "env", ".env", "node_modules", "dist", "build",
    "migrations", "alembic",  # falls vorhanden
}

DEFAULT_EXCLUDE_FILE_PATTERNS = (
    ".pyc",
)

def is_excluded_dir(path: Path, exclude_dirs: Set[str]) -> bool:
    return any(part in exclude_dirs for part in path.parts)

def iter_py_files(root: Path, exclude_dirs: Set[str]) -> List[Path]:
    py_files = []
    for p in root.rglob("*.py"):
        if is_excluded_dir(p, exclude_dirs):
            continue
        # optional: skip cache-like or weird
        if any(str(p).endswith(suf) for suf in DEFAULT_EXCLUDE_FILE_PATTERNS):
            continue
        py_files.append(p)
    return py_files

def module_name_from_path(root: Path, file_path: Path) -> str:
    rel = file_path.relative_to(root)
    parts = list(rel.parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1][:-3]  # strip .py
    return ".".join(parts)

def build_module_index(root: Path, py_files: List[Path]) -> Tuple[Dict[str, Path], Dict[Path, str]]:
    mod2path: Dict[str, Path] = {}
    path2mod: Dict[Path, str] = {}
    for f in py_files:
        mod = module_name_from_path(root, f)
        mod2path[mod] = f
        path2mod[f] = mod
    return mod2path, path2mod

def safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1", errors="replace")
    except Exception:
        return ""

def parse_imports(file_path: Path) -> Optional[ast.AST]:
    src = safe_read_text(file_path)
    if not src.strip():
        return None
    try:
        return ast.parse(src, filename=str(file_path))
    except SyntaxError:
        # z.B. alte/kaputte Kopien
        return None

def resolve_relative(base_mod: str, level: int, module: Optional[str]) -> Optional[str]:
    """
    base_mod: z.B. app.models.invoice
    level: 0=absolut, 1=from . import x, 2=from .. import x, ...
    module: der Modulteil in from ...module import ...
    """
    if level == 0:
        return module

    base_parts = base_mod.split(".")
    # Wenn base_mod ein Paket-Modul ist, Imports passieren relativ zum Paket
    # Für eine Datei (nicht __init__), ist base_mod bereits Modul; relative Importe beziehen sich auf Package (Parent)
    # -> wir gehen mindestens 1 Ebene hoch in Richtung Paket.
    if len(base_parts) >= 1:
        # relative level 1 => parent package
        up = level
        if up > len(base_parts):
            return None
        prefix_parts = base_parts[:-up]
    else:
        return None

    if module:
        return ".".join(prefix_parts + module.split("."))
    return ".".join(prefix_parts) if prefix_parts else None

def extract_imported_modules(tree: ast.AST, base_mod: str) -> Set[str]:
    imported: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name:
                    imported.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            # node.module kann None sein bei "from . import x"
            resolved = resolve_relative(base_mod, node.level or 0, node.module)
            if resolved:
                imported.add(resolved)
            else:
                # Falls "from . import x": node.module=None, dann hängen die Namen dran
                # -> wir nehmen das Parent-Package und hängen alias.name an
                if (node.level or 0) > 0:
                    parent = resolve_relative(base_mod, node.level or 0, None)
                    if parent:
                        for alias in node.names:
                            if alias.name:
                                imported.add(parent + "." + alias.name)
    return imported

def best_match_to_project_module(import_name: str, mod2path: Dict[str, Path]) -> Optional[str]:
    """
    Mappt z.B.:
      - app.models.invoice_item -> genaues Modul
      - app.models -> Paket
      - models.invoice -> falls root so strukturiert ist
    Strategie:
      - exakter Treffer
      - sonst: kürze Suffixe (import x.y.z -> x.y)
      - sonst: None
    """
    if import_name in mod2path:
        return import_name

    parts = import_name.split(".")
    while len(parts) > 1:
        parts = parts[:-1]
        cand = ".".join(parts)
        if cand in mod2path:
            return cand
    return None

def build_import_graph(root: Path, py_files: List[Path], mod2path: Dict[str, Path], path2mod: Dict[Path, str]) -> Dict[str, Set[str]]:
    graph: Dict[str, Set[str]] = {m: set() for m in mod2path.keys()}

    for f in py_files:
        base_mod = path2mod[f]
        tree = parse_imports(f)
        if not tree:
            continue
        imports = extract_imported_modules(tree, base_mod)
        for imp in imports:
            target = best_match_to_project_module(imp, mod2path)
            if target:
                graph[base_mod].add(target)
    return graph

def reachable_from(entry_mods: List[str], graph: Dict[str, Set[str]]) -> Set[str]:
    seen: Set[str] = set()
    stack: List[str] = list(entry_mods)
    while stack:
        m = stack.pop()
        if m in seen:
            continue
        seen.add(m)
        for nxt in graph.get(m, ()):
            if nxt not in seen:
                stack.append(nxt)
    return seen

def normalize_entry(root: Path, entry: str, mod2path: Dict[str, Path]) -> Optional[str]:
    """
    entry kann sein:
      - run.py
      - app/__init__.py
      - app
      - app.models.invoice
    """
    p = Path(entry)
    if not p.is_absolute():
        p = (root / p).resolve()

    # Fall 1: Pfad zu .py Datei
    if p.exists() and p.is_file() and p.suffix == ".py":
        try:
            return module_name_from_path(root, p)
        except Exception:
            return None

    # Fall 2: Modulname
    entry_str = entry.replace("\\", ".").replace("/", ".")
    entry_str = entry_str[:-3] if entry_str.endswith(".py") else entry_str
    if entry_str in mod2path:
        return entry_str
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="Projekt-Root (z.B. C:\\manifest_fallschirm)")
    ap.add_argument("--entry", action="append", default=[], help="Entrypoint (mehrfach möglich), z.B. run.py")
    ap.add_argument("--exclude-dir", action="append", default=[], help="Zusätzliche auszuschließende Ordnernamen")
    ap.add_argument("--keep", action="append", default=[], help="Module, die immer als used gelten sollen (Modulname)")
    ap.add_argument("--show-used", action="store_true", help="Gibt auch used-Module aus")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"Root existiert nicht: {root}", file=sys.stderr)
        sys.exit(2)

    exclude_dirs = set(DEFAULT_EXCLUDE_DIRS) | set(args.exclude_dir)

    py_files = iter_py_files(root, exclude_dirs)
    mod2path, path2mod = build_module_index(root, py_files)
    graph = build_import_graph(root, py_files, mod2path, path2mod)

    # Default Entrypoints, falls keine angegeben (typisch Flask)
    entries = args.entry[:] if args.entry else ["run.py", "app/__init__.py"]

    entry_mods: List[str] = []
    for e in entries:
        m = normalize_entry(root, e, mod2path)
        if m:
            entry_mods.append(m)
        else:
            print(f"Warnung: Entrypoint nicht gefunden/auflösbar: {e}", file=sys.stderr)

    # Keep-Liste
    keep_mods = [k for k in args.keep if k in mod2path]
    entry_mods.extend(keep_mods)

    used = reachable_from(entry_mods, graph)

    # Alles im Projekt, was nicht reachable ist, ist Kandidat
    all_mods = set(mod2path.keys())
    unused = sorted(all_mods - used)

    print(f"Projekt: {root}")
    print(f"Python-Dateien gefunden: {len(py_files)}")
    print(f"Entrypoints: {', '.join(entry_mods) if entry_mods else '(keine)'}")
    print("-" * 80)

    if args.show_used:
        print("USED MODULES:")
        for m in sorted(used):
            print(f"  [USED]   {m}  ->  {mod2path[m]}")
        print("-" * 80)

    print("UNUSED CANDIDATES (statisch nicht importiert):")
    for m in unused:
        print(f"  [UNUSED] {m}  ->  {mod2path[m]}")

    print("-" * 80)
    print("Hinweis: Dynamische Imports/Reflection werden nicht erkannt. Vor dem Löschen prüfen.")

if __name__ == "__main__":
    main()