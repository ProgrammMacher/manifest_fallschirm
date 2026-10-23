from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = PROJECT_ROOT / "tools" / "check_runtime_consistency.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_runtime_consistency", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _wheel(name: str, version: str) -> str:
    return f"{name}-{version}-py3-none-any.whl"


def _build_project(root: Path, requirements: list[str], wheels: list[str], dist_infos: list[str]):
    (root / "requirements.txt").write_text("\n".join(requirements) + "\n", encoding="utf-8")
    packages = root / "packages"
    packages.mkdir()
    for wheel in wheels:
        (packages / wheel).write_bytes(b"")
    site = root / "runtime" / "python" / "Lib" / "site-packages"
    site.mkdir(parents=True)
    for info in dist_infos:
        (site / f"{info}.dist-info").mkdir()
    return root


def _snapshot(root: Path) -> dict[str, tuple[int, int]]:
    return {
        str(p.relative_to(root)): (p.stat().st_size, p.stat().st_mtime_ns)
        for p in sorted(root.rglob("*"))
    }


@pytest.fixture()
def consistent_project(tmp_path):
    return _build_project(
        tmp_path,
        ["Flask==3.1.2", "typing_extensions==4.15.0"],
        [_wheel("flask", "3.1.2"), _wheel("typing_extensions", "4.15.0")],
        ["flask-3.1.2", "typing_extensions-4.15.0", "pip-25.3"],
    )


def test_consistent_project_returns_zero(consistent_project, capsys):
    module = _load_module()
    assert module.run(consistent_project) == 0
    assert "[OK]" in capsys.readouterr().out


def test_name_normalization_is_equivalent(tmp_path):
    root = _build_project(
        tmp_path,
        ["Flask-SQLAlchemy==3.1.1", "email_validator==2.1.1"],
        [_wheel("flask_sqlalchemy", "3.1.1"), _wheel("email_validator", "2.1.1")],
        ["flask_sqlalchemy-3.1.1", "email_validator-2.1.1"],
    )
    assert _load_module().run(root) == 0


def test_missing_runtime_package_is_critical(tmp_path, capsys):
    root = _build_project(
        tmp_path,
        ["Flask==3.1.2", "waitress==3.0.2"],
        [_wheel("flask", "3.1.2"), _wheel("waitress", "3.0.2")],
        ["flask-3.1.2"],
    )
    assert _load_module().run(root) == 1
    err = capsys.readouterr().err
    assert "Fehlt in runtime/python" in err
    assert "waitress==3.0.2" in err
    assert "pip install --no-index --find-links=packages -r requirements.txt" in err


def test_wrong_runtime_version_is_critical(tmp_path, capsys):
    root = _build_project(
        tmp_path,
        ["alembic==1.18.4"],
        [_wheel("alembic", "1.18.4")],
        ["alembic-1.18.3"],
    )
    assert _load_module().run(root) == 1
    err = capsys.readouterr().err
    assert "Falsche Version" in err
    assert "requirements.txt=1.18.4, runtime=1.18.3" in err


def test_missing_wheel_is_critical(tmp_path, capsys):
    root = _build_project(tmp_path, ["flask==3.1.2"], [], ["flask-3.1.2"])
    assert _load_module().run(root) == 1
    assert "Wheel fehlt in packages/" in capsys.readouterr().err


def test_wrong_wheel_version_is_critical(tmp_path):
    root = _build_project(
        tmp_path, ["flask==3.1.2"], [_wheel("flask", "3.1.1")], ["flask-3.1.2"]
    )
    assert _load_module().run(root) == 1


def test_extra_packages_and_wheels_only_warn(tmp_path, capsys):
    root = _build_project(
        tmp_path,
        ["flask==3.1.2"],
        [_wheel("flask", "3.1.2"), _wheel("extra_wheel", "1.0")],
        ["flask-3.1.2", "beautifulsoup4-4.14.3", "pip-25.3"],
    )
    assert _load_module().run(root) == 0
    out = capsys.readouterr().out
    assert "[WARNUNG]" in out
    assert "beautifulsoup4==4.14.3" in out
    assert "extra-wheel==1.0" in out
    assert "pip==" not in out


def test_structural_problems_are_critical(tmp_path, capsys):
    assert _load_module().run(tmp_path) == 1
    err = capsys.readouterr().err
    assert "requirements.txt fehlt" in err
    assert "packages-Ordner fehlt" in err
    assert "site-packages fehlt" in err


def test_unsupported_requirement_line_is_critical(tmp_path, capsys):
    root = _build_project(
        tmp_path, ["flask>=3.0"], [_wheel("flask", "3.1.2")], ["flask-3.1.2"]
    )
    assert _load_module().run(root) == 1
    assert "nicht unterstuetzt" in capsys.readouterr().err


def test_check_is_strictly_read_only(tmp_path):
    root = _build_project(
        tmp_path,
        ["Flask==3.1.2", "waitress==3.0.2"],
        [_wheel("flask", "3.1.2"), _wheel("stale", "1.0")],
        ["flask-3.1.1", "soupsieve-2.8.3"],
    )
    before = _snapshot(root)
    assert _load_module().run(root) == 1
    assert _snapshot(root) == before


def test_script_contains_no_install_download_or_write_code():
    source = SCRIPT.read_text(encoding="utf-8")
    code = source.split('"""', 2)[2]  # Modul-Docstring ausnehmen
    for forbidden in (
        "import subprocess",
        "import shutil",
        "import urllib",
        "import requests",
        "os.system",
        "write_text",
        "write_bytes",
        ".unlink(",
        ".mkdir(",
        ".rename(",
        ".touch(",
        "open(",
    ):
        assert forbidden not in code, forbidden


def test_cli_exit_codes(consistent_project, tmp_path_factory):
    ok = subprocess.run(
        [sys.executable, str(SCRIPT), "--project-root", str(consistent_project)],
        capture_output=True,
        text=True,
    )
    assert ok.returncode == 0

    broken = tmp_path_factory.mktemp("broken")
    _build_project(broken, ["flask==3.1.2"], [], [])
    bad = subprocess.run(
        [sys.executable, str(SCRIPT), "--project-root", str(broken)],
        capture_output=True,
        text=True,
    )
    assert bad.returncode == 1
    assert "Manuelle Reparatur" in bad.stderr
