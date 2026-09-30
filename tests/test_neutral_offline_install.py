from __future__ import annotations

import re
import os
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import text


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _create_isolated_app(runtime_home: Path, monkeypatch, *, auto_upgrade: str = "0"):
    runtime_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("MANIFEST_RUNTIME_HOME", str(runtime_home))
    monkeypatch.setenv("MANIFEST_DB_PATH", str(runtime_home / "data" / "manifest.db"))
    monkeypatch.setenv(
        "MANIFEST_SECRETS_PATH",
        str(runtime_home / "secrets" / "auth_config.json"),
    )
    monkeypatch.setenv("MANIFEST_ENV", "dev")
    monkeypatch.setenv("MANIFEST_AUTO_DB_UPGRADE", auto_upgrade)
    monkeypatch.setenv("MANIFEST_AUTO_CREATE_DB", "1")

    from app import create_app

    app = create_app()
    app.config.update(TESTING=True)
    return app


def _parse_ps_array(script: str, array_name: str) -> list[str]:
    match = re.search(rf"\${array_name}\s*=\s*@\((.*?)\)", script, re.DOTALL)
    assert match is not None, f"${array_name} array not found"
    return re.findall(r"'([^']+)'", match.group(1))


@pytest.fixture()
def fresh_install_app(tmp_path, monkeypatch):
    app = _create_isolated_app(
        tmp_path / "fresh-install" / "ProgramData" / "ManifestFallschirm",
        monkeypatch,
        auto_upgrade="0",
    )
    yield app

    from app import db

    with app.app_context():
        db.session.remove()
        db.engine.dispose(close=True)


def test_fresh_install_has_only_neutral_master_data(fresh_install_app):
    from app import db
    from app.models.aircraft import Aircraft
    from app.models.billing_config import (
        BillingOrgaConfig,
        BillingConfig,
        BillingOrgaRule,
        BillingPrice,
        BillingPricePeriod,
    )
    from app.models.email_send_log import EmailSendLog
    from app.models.email_config import EmailConfig
    from app.models.flugplatz import Flugplatz
    from app.models.invoice import Invoice
    from app.models.invoice_item import InvoiceItem
    from app.models.load import Load
    from app.models.load_entry import LoadEntry
    from app.models.person import Person
    from app.models.mobile_person_intake_draft import MobilePersonIntakeDraft
    from app.models.sepa_config import SepaConfig
    from app.models.sepa_export import SepaExport, SepaExportInvoice
    from app.models.status_definition import StatusDefinition

    app = fresh_install_app
    with app.app_context():
        assert Flugplatz.query.count() == 6
        assert Aircraft.query.count() == 9
        assert BillingPricePeriod.query.count() == 1
        assert BillingPrice.query.count() == 70
        assert StatusDefinition.query.filter_by(is_active=True).count() == 24
        assert BillingOrgaConfig.query.count() == 1
        assert BillingOrgaRule.query.count() == 20
        assert {row.id for row in StatusDefinition.query.all()} == set(range(1, 25))
        assert {row.id for row in BillingPrice.query.all()} == set(range(1, 71))
        assert {row.id for row in BillingOrgaRule.query.all()} == set(range(1, 21))
        revisions = {
            row[0]
            for row in db.session.execute(text("SELECT version_num FROM alembic_version"))
        }
        assert revisions

        assert Person.query.count() == 0
        assert Load.query.count() == 0
        assert LoadEntry.query.count() == 0
        assert Invoice.query.count() == 0
        assert InvoiceItem.query.count() == 0
        assert BillingConfig.query.count() == 0
        assert EmailConfig.query.count() == 0
        assert SepaConfig.query.count() == 0
        assert SepaExport.query.count() == 0
        assert SepaExportInvoice.query.count() == 0
        assert EmailSendLog.query.count() == 0
        assert MobilePersonIntakeDraft.query.count() == 0

        period = BillingPricePeriod.query.one()
        assert period.id == 1
        assert period.valid_from == date(2026, 8, 1)
        assert period.valid_to is None
        assert Decimal(str(period.orga_fee_eur)) == Decimal("0.00")

        assert {row.name for row in Flugplatz.query.all()} == {
            "Dessau EDAD",
            "Zerbst EDUZ",
            "Mellenthin DE-0361",
            "Merseburg EDAM",
            "Roitzschjora EDAW",
            "Magdeburg EDBM",
        }
        assert {row.registration for row in Aircraft.query.all()} == {
            "D-EECH",
            "D-FAXI",
            "D-FWJK",
            "D-FALB",
            "ER-AFZ",
            "SE-GEE",
            "50+38",
            "D-EDMO",
            "D-FOJB",
        }
        assert sum(1 for row in Flugplatz.query.all() if row.active) == 2
        assert sum(1 for row in Aircraft.query.all() if row.active) == 1
        assert Flugplatz.query.filter_by(is_home_airfield=True).one().name == "Dessau EDAD"
        assert Aircraft.query.filter_by(registration="SE-GEE").one().default_height == 4000
        assert {row.id for row in Flugplatz.query.all()} == set(range(1, 7))
        assert {row.id for row in Aircraft.query.all()} == set(range(1, 10))
        assert not (Path(os.environ["MANIFEST_RUNTIME_HOME"]) / "secrets" / "auth_config.json").exists()
        assert not (Path(os.environ["MANIFEST_RUNTIME_HOME"]) / "data" / "app_settings.json").exists()

        db.session.remove()


def test_existing_installation_update_does_not_reseed_or_clear_data(tmp_path, monkeypatch):
    from app import db
    from app.models.aircraft import Aircraft
    from app.models.billing_config import BillingPrice, BillingPricePeriod
    from app.models.flugplatz import Flugplatz
    from app.models.person import Person
    from app.models.sepa_config import SepaConfig

    runtime_home = tmp_path / "existing-install" / "ProgramData" / "ManifestFallschirm"
    first_app = _create_isolated_app(runtime_home, monkeypatch)
    with first_app.app_context():
        person = Person(
            first_name="Update",
            last_name="Sentinel",
            phone="0000000000",
            email="update@example.invalid",
            weight_kg=80,
        )
        db.session.add(person)
        db.session.commit()
        person_id = person.id
        initial_counts = (
            Flugplatz.query.count(),
            Aircraft.query.count(),
            BillingPricePeriod.query.count(),
            BillingPrice.query.count(),
        )
        db.session.remove()
        db.engine.dispose(close=True)

    updated_app = _create_isolated_app(runtime_home, monkeypatch, auto_upgrade="1")
    with updated_app.app_context():
        assert db.session.get(Person, person_id) is not None
        assert initial_counts == (
            Flugplatz.query.count(),
            Aircraft.query.count(),
            BillingPricePeriod.query.count(),
            BillingPrice.query.count(),
        )
        db.session.remove()
        db.engine.dispose(close=True)


def test_full_backup_restore_replaces_seed_with_complete_operating_database(
    tmp_path,
    monkeypatch,
):
    from app import db
    from app.helpers.db_operations import create_database_backup
    from app.models.aircraft import Aircraft
    from app.models.billing_config import BillingConfig, BillingPricePeriod
    from app.models.email_config import EmailConfig
    from app.models.flugplatz import Flugplatz
    from app.models.invoice import Invoice
    from app.models.invoice_item import InvoiceItem
    from app.models.load import Load
    from app.models.load_entry import LoadEntry
    from app.models.person import Person
    from app.models.sepa_config import SepaConfig
    from app.models.status_definition import StatusDefinition

    source_home = tmp_path / "backup-source" / "ProgramData" / "ManifestFallschirm"
    source_app = _create_isolated_app(source_home, monkeypatch)
    with source_app.app_context():
        airfield = Flugplatz.query.filter_by(is_home_airfield=True).one()
        aircraft = Aircraft.query.filter_by(active=True).one()
        status = StatusDefinition.query.filter_by(code="Gast", is_active=True).first()
        period = BillingPricePeriod.query.one()
        person = Person(
            first_name="Restore",
            last_name="Fixture",
            phone="0000000001",
            email="restore@example.invalid",
            weight_kg=75,
        )
        db.session.add(person)
        db.session.flush()

        load = Load(
            load_number=77,
            height_m=4000,
            airfield_id=airfield.id,
            aircraft_id=aircraft.id,
            pricing_model_id=period.id,
        )
        db.session.add(load)
        db.session.flush()
        entry = LoadEntry(
            load_id=load.id,
            person_id=person.id,
            status_definition_id=status.id if status else None,
            seat=1,
            height_m=4000,
            status_code="Gast",
        )
        db.session.add(entry)
        db.session.flush()

        invoice = Invoice(
            person_id=person.id,
            stage="final",
            seq_number=70001,
            total_amount=Decimal("100.00"),
            payment_method="cash",
            payment_state="paid",
            is_paid=True,
            paid_at=datetime(2026, 9, 30, 12, 0, 0),
        )
        db.session.add(invoice)
        db.session.flush()
        db.session.add(
            InvoiceItem(
                invoice_id=invoice.id,
                load_entry_id=entry.id,
                amount=Decimal("100.00"),
                vat_rate=Decimal("19.00"),
                net_amount=Decimal("84.03"),
                vat_amount=Decimal("15.97"),
                description="Synthetischer Restore-Test",
                item_source="load",
            )
        )

        billing_config = BillingConfig(
            company_name="Restore-Test GmbH",
            street="Teststraße 1",
            zip_code="00000",
            city="Teststadt",
            tax_number="TEST-TAX-NUMBER",
            bank_name="Testbank",
            iban="TEST-IBAN-NOT-REAL",
            smtp_server="smtp.example.invalid",
            smtp_username="test-user",
        )
        email_config = EmailConfig(
            company_name="Restore-Test Mail",
            smtp_server="smtp.example.invalid",
            smtp_port=2525,
            smtp_username="test-user",
        )
        sepa_config = SepaConfig(
            creditor_id="TEST-CREDITOR",
            creditor_name="Restore-Test",
            creditor_iban="DE00000000000000000000",
            creditor_bic="TESTDEFFXXX",
        )
        db.session.add_all([billing_config, email_config, sepa_config])
        db.session.commit()
        person_id = person.id
        load_id = load.id
        invoice_id = invoice.id
        backup_path = create_database_backup(created_by="test")
        db.session.remove()
        db.engine.dispose(close=True)

    target_home = tmp_path / "backup-target" / "ProgramData" / "ManifestFallschirm"
    target_app = _create_isolated_app(target_home, monkeypatch)
    client = target_app.test_client()
    with client.session_transaction() as session:
        session["is_db_admin"] = True

    with Path(backup_path).open("rb") as backup_file:
        response = client.post(
            "/admin/database/import",
            data={"db_file": (backup_file, "complete-test-backup.db")},
            content_type="multipart/form-data",
            follow_redirects=False,
        )
    assert response.status_code == 302

    with target_app.app_context():
        db.session.remove()
        person = db.session.get(Person, person_id)
        load = db.session.get(Load, load_id)
        invoice = db.session.get(Invoice, invoice_id)
        billing_config = BillingConfig.query.one()
        email_config = EmailConfig.query.one()
        sepa_config = SepaConfig.query.one()

        assert person is not None and person.first_name == "Restore"
        assert load is not None and load.entries[0].status_code == "Gast"
        assert invoice is not None and invoice.items[0].description == "Synthetischer Restore-Test"
        assert invoice.is_paid is True and invoice.payment_state == "paid"
        assert invoice.payment_method == "cash"
        assert billing_config.company_name == "Restore-Test GmbH"
        assert billing_config.iban == "TEST-IBAN-NOT-REAL"
        assert billing_config.smtp_server == "smtp.example.invalid"
        assert email_config.smtp_username == "test-user"
        assert sepa_config.creditor_name == "Restore-Test"
        db.session.remove()
        db.engine.dispose(close=True)


def test_offline_build_allowlists_neutral_seed_but_not_local_runtime_files():
    sensitive_names = {
        "manifest.db",
        "app_settings.json",
        "auth_config.json",
        "split_verify_temp.db",
    }
    required_runtime_dirs = {"runtime/python", "runtime/gtk"}

    for relative_path in (
        "tools/build_offline_installer_zip.ps1",
        "tools/build_offline_compiled_installer_zip.ps1",
    ):
        text = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
        include_dirs = set(_parse_ps_array(text, "includeDirs"))
        include_files = set(_parse_ps_array(text, "includeFiles"))
        exclude_globs = set(_parse_ps_array(text, "excludeGlobs"))

        assert "data" not in include_dirs
        assert "runtime" not in include_dirs
        assert required_runtime_dirs.issubset(include_dirs)
        assert not any(Path(path).name in sensitive_names for path in include_files)
        assert "runtime/gtk/var/cache/**" in exclude_globs
        assert "data/backup/**" in exclude_globs

        seed_text = (PROJECT_ROOT / "app/services/neutral_install_seed.py").read_text(
            encoding="utf-8"
        )
        assert "data/manifest.db" not in seed_text
        assert "sqlite3" not in seed_text
        assert "MANIFEST_DB_PATH" not in seed_text

        seed_module = "app/services/neutral_install_seed.py"
        assert seed_module in include_dirs or "app" in include_dirs

    inno_builder = (PROJECT_ROOT / "tools/build_inno_offline_setup.ps1").read_text(
        encoding="utf-8"
    )
    assert 'Copy-IfExists "data"' not in inno_builder
    assert "Assert-InstallerStageSafe -StageRoot $stageDir" in inno_builder
    assert "app\\services\\neutral_install_seed.pyc" in inno_builder
    for forbidden in (
        "(^|/)data/",
        "\\.(db|sqlite|sqlite3)$",
        "app_settings",
        "auth_config",
        "noch_zu_loeschen",
        "runtime/gtk/var/cache",
    ):
        assert forbidden in inno_builder

    workflow = (PROJECT_ROOT / ".github/workflows/build-installer.yml").read_text(
        encoding="utf-8"
    )
    normalized_workflow = workflow.replace("\\", "/")
    assert workflow.startswith("name: Build Manifest Installer")
    assert "workflow_dispatch:" in workflow
    assert "actions/setup-python@v5" in workflow
    assert 'python-version: "3.14.2"' in workflow
    assert "tools/build_inno_offline_setup.ps1" in normalized_workflow
    assert "runtime/python/python.exe" in normalized_workflow
    assert "Lib/venv" in normalized_workflow
    assert "manifest-venv-probe" in workflow
    assert "manifest-installer-${{ github.run_number }}-${{ github.run_attempt }}" in workflow
    assert "softprops/action-gh-release" not in workflow
    assert "Create Release" not in workflow
    assert "pyinstaller" not in workflow.lower()
    assert "github.run_number" in workflow and "github.run_attempt" in workflow
    assert "app/services/neutral_install_seed.pyc" in workflow


_PS_ARRAY_PATTERN = re.compile(r"\$([A-Za-z]+)\s*=\s*@\((.*?)\)", re.DOTALL)


def _parse_ps_array(script: str, array_name: str) -> list[str]:
    arrays = {name: re.findall(r"'([^']+)'", body) for name, body in _PS_ARRAY_PATTERN.findall(script)}
    assert array_name in arrays, f"${array_name} array not found"
    return arrays[array_name]
