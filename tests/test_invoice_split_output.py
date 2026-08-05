import os
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.routes.billing import (
    _finalize_invoice_for_billing,
    _assemble_split_preview_buckets,
    _sort_invoices_for_list,
    _invoice_matches_filters,
    _split_output_entries_and_allowed,
)
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


def test_split_output_entries_and_allowed_requires_positive_and_negative(monkeypatch):
    entries = [SimpleNamespace(id=1), SimpleNamespace(id=2)]

    def fake_get_jump_item_calculation(entry, **kwargs):
        if entry.id == 1:
            return {"effective_amount": Decimal("15.00")}
        return {"effective_amount": Decimal("0.00")}

    monkeypatch.setattr(BillingService, "get_jump_item_calculation", fake_get_jump_item_calculation)

    grouped, allowed = _split_output_entries_and_allowed(
        entries,
        is_tandem_kleinunternehmer=False,
        is_video_kleinunternehmer=False,
        is_aff_teacher_kleinunternehmer=False,
    )

    assert allowed is False
    assert grouped["negative"] == []
    assert [e.id for e in grouped["positive"]] == [1, 2]


def test_create_invoice_route_falls_back_to_single_invoice_when_split_not_allowed(app_with_temp_db, monkeypatch):
    from app import db
    from app.models.person import Person

    app = app_with_temp_db
    with app.app_context():
        person = db.session.query(Person).one()

    fake_entries = [SimpleNamespace(id=1)]
    monkeypatch.setattr(
        BillingService,
        "get_open_entries_for_person",
        staticmethod(lambda person_id: fake_entries),
    )
    monkeypatch.setattr(
        BillingService,
        "_split_entries_for_invoice_output",
        staticmethod(lambda entries, **kwargs: {"negative": [], "positive": list(entries or [])}),
    )

    calls = []

    def fake_create_invoice_for_person(person_id, **kwargs):
        calls.append(kwargs.get("entries_override"))
        return SimpleNamespace(
            id=42,
            seq_number=42,
            payment_method="cash",
            person=SimpleNamespace(
                is_tandem_guest=False,
                sepa_enabled=False,
                iban=None,
                account_holder=None,
                sepa_mandate_date=None,
            ),
            items=[],
            total_amount=Decimal("10.00"),
            stage="draft",
        )

    monkeypatch.setattr(BillingService, "create_invoice_for_person", staticmethod(fake_create_invoice_for_person))

    with app.test_client() as client:
        response = client.post(
            f"/billing/person/{person.id}/create_invoice",
            data={"split_output": "1"},
            follow_redirects=False,
        )

    assert response.status_code in (302, 303)
    assert calls == [None]


def test_invoice_number_sort_uses_visible_display_number():
    inv_a = SimpleNamespace(id=100, seq_number=5, created_at=None, payment_method=None, person=None)
    inv_b = SimpleNamespace(id=10, seq_number=50, created_at=None, payment_method=None, person=None)
    inv_c = SimpleNamespace(id=70, seq_number=12, created_at=None, payment_method=None, person=None)

    asc = _sort_invoices_for_list([inv_a, inv_b, inv_c], "inv_asc")
    desc = _sort_invoices_for_list([inv_a, inv_b, inv_c], "inv_desc")

    assert [inv.seq_number for inv in asc] == [5, 12, 50]
    assert [inv.seq_number for inv in desc] == [50, 12, 5]


def test_invoice_list_person_filter_uses_billing_recipient_name():
    inv = SimpleNamespace(
        person_id=17,
        person=SimpleNamespace(full_name="Tandemmaster Gewerbe-Umsatzsteuer"),
        billing_address_name="Fallschirmsportverein Zerbst",
        items=[],
        payment_method=None,
        email_last_attempt_at=None,
        email_sent_ok=False,
        email_last_error=None,
        email_sent_at=None,
        email_delivery_confirmed_at=None,
    )

    filters = {
        "invoice_source": "all",
        "person_id": 999,
        "person": "Fallschirmsportverein Zerbst",
        "text": "",
        "status": "",
        "payment": "",
        "email": "",
        "content_status": "",
    }

    assert _invoice_matches_filters(inv, filters)


def test_invoice_list_person_sort_prefers_billing_recipient_name():
    inv_a = SimpleNamespace(
        id=1,
        seq_number=1,
        created_at=None,
        payment_method=None,
        person=SimpleNamespace(first_name="A", last_name="Person", full_name="A Person"),
        billing_address_name="B Empfaenger",
    )
    inv_b = SimpleNamespace(
        id=2,
        seq_number=2,
        created_at=None,
        payment_method=None,
        person=SimpleNamespace(first_name="Z", last_name="Person", full_name="Z Person"),
        billing_address_name="A Empfaenger",
    )

    asc = _sort_invoices_for_list([inv_a, inv_b], "person_asc")
    desc = _sort_invoices_for_list([inv_a, inv_b], "person_desc")

    assert [inv.id for inv in asc] == [2, 1]
    assert [inv.id for inv in desc] == [1, 2]
