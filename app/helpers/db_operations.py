from __future__ import annotations

import shutil
from pathlib import Path
from datetime import datetime
from typing import List
from flask import current_app

from app import db
from app.helpers.app_settings import (
    record_database_backup,
    record_database_archive,
    record_import_result,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _runtime_paths() -> tuple[Path, Path, Path, Path, Path]:
    db_uri = str(current_app.config.get("SQLALCHEMY_DATABASE_URI", ""))
    if db_uri.startswith("sqlite:///"):
        active_db = Path(db_uri[len("sqlite:///"):])
    else:
        active_db = PROJECT_ROOT / "data" / "manifest.db"

    data_dir = active_db.parent
    backup_dir = data_dir / "backup"
    archive_dir = data_dir / "archive"
    temp_dir = data_dir / "temp"

    return active_db, data_dir, backup_dir, archive_dir, temp_dir


def _local_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


# -------------------------------------------------
# 1. Backup
# -------------------------------------------------

def create_database_backup(created_by: str = "admin") -> Path:
    active_db, _data_dir, backup_dir, _archive_dir, _temp_dir = _runtime_paths()
    backup_dir.mkdir(parents=True, exist_ok=True)

    target = backup_dir / f"manifest_{_local_stamp()}.db"
    shutil.copy2(active_db, target)

    record_database_backup(str(target), created_by=created_by)
    return target


# -------------------------------------------------
# 2. Neue Arbeitsdatenbank (nur Stammdaten)
# -------------------------------------------------

def create_new_working_database(created_by: str = "admin") -> Path:
    active_db, _data_dir, _backup_dir, archive_dir, temp_dir = _runtime_paths()
    temp_dir.mkdir(parents=True, exist_ok=True)
    archive_dir.mkdir(parents=True, exist_ok=True)

    new_db = temp_dir / "manifest_new.db"
    if new_db.exists():
        new_db.unlink()

    # Neue leere DB anlegen
    new_engine = db.create_engine(f"sqlite:///{new_db}")
    db.metadata.create_all(bind=new_engine)

    # Stammdaten kopieren
    with db.session.begin():
        for table in [
            "status_definition",
            "flugplatz",
            "aircraft",
            "person",
            "pricing",
            "price_audit_log",
        ]:
            db.session.execute(
                f"INSERT INTO {table} SELECT * FROM main.{table}"
            )

    # Alte DB archivieren
    archive_target = archive_dir / f"manifest_until_{_local_stamp()}.db"
    shutil.move(active_db, archive_target)

    shutil.move(new_db, active_db)
    record_database_archive(year=0, file_path=str(archive_target), created_by=created_by)

    return active_db


# -------------------------------------------------
# 3. Jahresarchiv
# -------------------------------------------------

def create_year_archive(year: int, created_by: str = "admin") -> Path:
    active_db, _data_dir, _backup_dir, archive_dir, _temp_dir = _runtime_paths()
    archive_dir.mkdir(parents=True, exist_ok=True)

    target = archive_dir / f"manifest_{year}.db"
    if target.exists():
        raise RuntimeError("Archiv für dieses Jahr existiert bereits")

    shutil.copy2(active_db, target)

    record_database_archive(year=year, file_path=str(target), created_by=created_by)
    return target


# -------------------------------------------------
# 4. Multi-DB Merge (Analyse)
# -------------------------------------------------

def merge_loads_from_databases(
    source_dbs: List[Path],
    created_by: str = "admin",
) -> Path:
    _active_db, _data_dir, _backup_dir, _archive_dir, temp_dir = _runtime_paths()
    temp_dir.mkdir(parents=True, exist_ok=True)
    analysis_db = temp_dir / f"manifest_analysis_{_local_stamp()}.db"

    engine = db.create_engine(f"sqlite:///{analysis_db}")
    db.metadata.create_all(bind=engine)

    imported = 0
    skipped = 0

    for src in source_dbs:
        try:
            db.session.execute(f"ATTACH DATABASE '{src}' AS src")

            db.session.execute("""
                INSERT OR IGNORE INTO load
                SELECT * FROM src.load
            """)
            imported += db.session.rowcount or 0

            db.session.execute("DETACH DATABASE src")
        except Exception:
            skipped += 1

    record_import_result(
        import_id=_local_stamp(),
        status="partial_success" if skipped else "success",
        mode="multi_db_merge",
        sources=[str(p) for p in source_dbs],
        created_by=created_by,
    )

    return analysis_db