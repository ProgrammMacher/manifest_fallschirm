import os
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.routes.billing import _finalize_invoice_for_billing, _assemble_split_preview_buckets
from app.services.billing_service import BillingService


@pytest.fixture()
def app_with_temp_db(tmp_path):
    runtime_home = tmp_path / "runtime"
    db_file = runtime_home / "manifest_test.db"
    runtime_home.mkdir(parents=True, exist_ok=True)

    os.environ["MANIFEST_RUNTIME_HOME"] = str(runtime_home)
    os.environ["MANIFEST_DB_PATH"] = str(db_file)
    os.environ["MANIFEST_ENV"] = "dev"
    os.environ["MANIFEST_AUTO_CREATE_DB"] = "1"

    from app import create_app, db
    from app.models.person import Person

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()

        person = Person(first_name="Test", last_name="Split", phone="123", email="test@example.org", weight_kg=80)
        db.session.add(person)
        db.session.flush()
        db.session.commit()

    yield app

    with app.app_context():
        db.session.remove()


def test_split_entries_for_invoice_output_groups_by_sign(monkeypatch):
    entries = [
        SimpleNamespace(id=1),
        SimpleNamespace(id=2),
        SimpleNamespace(id=3),
    ]

    def fake_get_jump_item_calculation(entry, **kwargs):
        if entry.id == 1:
            return {"effective_amount": Decimal("35.00")}
        if entry.id == 2:
            return {"effective_amount": Decimal("-75.00")}
        return {"effective_amount": Decimal("0.00")}

    monkeypatch.setattr(BillingService, "get_jump_item_calculation", fake_get_jump_item_calculation)

    grouped = BillingService._split_entries_for_invoice_output(entries)

    assert [e.id for e in grouped["negative"]] == [2]
    assert [e.id for e in grouped["positive"]] == [1, 3]


def test_split_mode_preserves_existing_drafts_for_same_person(app_with_temp_db, monkeypatch):
    from app import db
    from app.models.invoice import Invoice
    from app.models.person import Person

    app = app_with_temp_db
    with app.app_context():
        person = db.session.query(Person).one()

        def fake_build(invoice, entries, config, mark_billed=False):
            invoice.total_amount = Decimal("0.00")
            return None

        monkeypatch.setattr(BillingService, "_build_invoice_items", staticmethod(fake_build))
        monkeypatch.setattr(BillingService, "get_global_config", staticmethod(lambda: object()))
        monkeypatch.setattr(
            BillingService,
            "get_open_entries_for_person",
            staticmethod(lambda person_id: [SimpleNamespace(id=1)]),
        )

        first_invoice = BillingService.create_invoice_for_person(
            person.id,
            entries_override=[SimpleNamespace(id=1)],
            clear_existing_drafts=False,
        )
        second_invoice = BillingService.create_invoice_for_person(
            person.id,
            entries_override=[SimpleNamespace(id=2)],
            clear_existing_drafts=False,
        )

        assert first_invoice is not None
        assert second_invoice is not None
        assert first_invoice.id == 1
        assert second_invoice.id == 2
        assert db.session.get(Invoice, first_invoice.id) is not None
        assert db.session.get(Invoice, second_invoice.id) is not None
        assert [row[0] for row in db.session.query(Invoice.id).order_by(Invoice.id.asc()).all()] == [1, 2]


def test_finalize_invoice_helper_assigns_seq_and_marks_final(app_with_temp_db):
    from app import db
    from app.models.invoice import Invoice
    from app.models.person import Person

    app = app_with_temp_db
    with app.app_context():
        person = db.session.query(Person).one()
        invoice = Invoice(person_id=person.id, total_amount=Decimal("0.00"), stage="draft")
        db.session.add(invoice)
        db.session.flush()
        invoice_id = invoice.id

        _finalize_invoice_for_billing(invoice)
        db.session.commit()
        db.session.remove()

        with app.app_context():
            reloaded = db.session.get(Invoice, invoice_id)

        assert reloaded is not None
        assert reloaded.stage == "final"
        assert reloaded.seq_number is not None
        assert reloaded.seq_number >= 1


def test_assemble_split_preview_buckets_groups_entries_by_bucket(monkeypatch):
    entries = [
        SimpleNamespace(id=1),
        SimpleNamespace(id=2),
        SimpleNamespace(id=3),
    ]

    def fake_get_jump_item_calculation(entry, **kwargs):
        if entry.id == 1:
            return {"effective_amount": Decimal("35.00"), "net": Decimal("30.00"), "vat": Decimal("5.00"), "vat_rate": Decimal("16.67")}
        if entry.id == 2:
            return {"effective_amount": Decimal("-75.00"), "net": Decimal("-64.00"), "vat": Decimal("-11.00"), "vat_rate": Decimal("17.19")}
        return {"effective_amount": Decimal("0.00"), "net": Decimal("0.00"), "vat": Decimal("0.00"), "vat_rate": Decimal("0.00")}

    monkeypatch.setattr(BillingService, "get_jump_item_calculation", fake_get_jump_item_calculation)

    buckets = _assemble_split_preview_buckets(entries, preview_tandem_ku_enabled=False, preview_video_ku_enabled=False, preview_aff_teacher_ku_enabled=False)

    assert [row["entry"].id for row in buckets["buckets"]["negative"]] == [2]
    assert [row["entry"].id for row in buckets["buckets"]["positive"]] == [1, 3]
    assert buckets["totals"]["negative"] == Decimal("-75.00")
    assert buckets["totals"]["positive"] == Decimal("35.00")
