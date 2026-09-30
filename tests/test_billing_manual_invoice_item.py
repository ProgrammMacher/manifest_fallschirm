from decimal import Decimal

import pytest


@pytest.fixture()
def app_with_temp_db(tmp_path, monkeypatch):
    runtime_home = tmp_path / "runtime"
    db_file = runtime_home / "manifest_test.db"
    runtime_home.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("MANIFEST_RUNTIME_HOME", str(runtime_home))
    monkeypatch.setenv("MANIFEST_DB_PATH", str(db_file))
    monkeypatch.setenv("MANIFEST_SECRETS_PATH", str(runtime_home / "secrets" / "auth_config.json"))
    monkeypatch.setenv("MANIFEST_ENV", "dev")
    monkeypatch.setenv("MANIFEST_AUTO_DB_UPGRADE", "0")
    monkeypatch.setenv("MANIFEST_AUTO_CREATE_DB", "1")

    from app import create_app, db

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        db.session.remove()
        db.engine.dispose(close=True)
        db.drop_all()
        db.create_all()

    yield app

    with app.app_context():
        db.session.remove()


def _make_person(db, Person, name="Max Muster"):
    first, last = name.split(" ", 1)
    person = Person(first_name=first, last_name=last, phone="0123456789", weight_kg=80)
    db.session.add(person)
    db.session.commit()
    return person


def _make_manual_only_draft(db, Invoice, InvoiceItem, person_id):
    """Reine manuelle Entwurfsrechnung (analog BillingService.create_manual_invoice)."""
    from datetime import date

    invoice = Invoice(
        person_id=person_id,
        stage="draft",
        service_date=date.today(),
        manual_title="Manuelle Positionen",
        total_amount=Decimal("0.00"),
    )
    db.session.add(invoice)
    db.session.flush()

    item = InvoiceItem(
        invoice_id=invoice.id,
        load_entry_id=None,
        amount=Decimal("100.00"),
        vat_rate=Decimal("19.00"),
        net_amount=Decimal("84.03"),
        vat_amount=Decimal("15.97"),
        description="Ausrüstungspaket",
        item_source="manual",
        quantity=Decimal("1.00"),
        unit_price_gross=Decimal("100.00"),
        manual_position_code="manual",
    )
    db.session.add(item)
    invoice.calculate_total()
    db.session.commit()
    return invoice


def _make_jump_draft_invoice(db, Invoice, InvoiceItem, Load, LoadEntry, Flugplatz, Aircraft, person_id):
    """Entwurfsrechnung mit einer echten Sprungposition (item_source='load')."""
    airfield = Flugplatz(name="Testplatz")
    aircraft = Aircraft(type="Cessna", registration="D-TEST", seats=4)
    db.session.add_all([airfield, aircraft])
    db.session.flush()

    load = Load(load_number=1, height_m=4000, airfield_id=airfield.id, aircraft_id=aircraft.id)
    db.session.add(load)
    db.session.flush()

    entry = LoadEntry(load_id=load.id, person_id=person_id, height_m=4000, status_code="Gast")
    db.session.add(entry)
    db.session.flush()

    invoice = Invoice(person_id=person_id, stage="draft", total_amount=Decimal("0.00"))
    db.session.add(invoice)
    db.session.flush()

    jump_item = InvoiceItem(
        invoice_id=invoice.id,
        load_entry_id=entry.id,
        amount=Decimal("50.00"),
        vat_rate=Decimal("19.00"),
        net_amount=Decimal("42.02"),
        vat_amount=Decimal("7.98"),
        description="Sprung",
        item_source="load",
    )
    db.session.add(jump_item)
    invoice.calculate_total()
    db.session.commit()
    return invoice


def test_add_manual_item_to_jump_draft_invoice_updates_total(app_with_temp_db):
    from app import db
    from app.models.person import Person
    from app.models.invoice import Invoice
    from app.models.invoice_item import InvoiceItem
    from app.models.load import Load
    from app.models.load_entry import LoadEntry
    from app.models.flugplatz import Flugplatz
    from app.models.aircraft import Aircraft

    app = app_with_temp_db
    with app.app_context():
        person = _make_person(db, Person)
        invoice = _make_jump_draft_invoice(
            db, Invoice, InvoiceItem, Load, LoadEntry, Flugplatz, Aircraft, person.id
        )
        invoice_id = invoice.id
        assert Decimal(str(invoice.total_amount)) == Decimal("50.00")

    client = app.test_client()
    response = client.post(
        f"/billing/invoice/{invoice_id}/manual_item/add",
        data={
            "manual_item_description": "Theoriekurs",
            "manual_item_quantity": "2,00",
            "manual_item_unit": "Stück",
            "manual_item_unit_price_gross": "25,00",
            "manual_item_vat_rate": "19,00",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        invoice = Invoice.query.get(invoice_id)
        manual_items = [it for it in invoice.items if it.item_source == "manual"]
        load_items = [it for it in invoice.items if it.item_source == "load"]

        assert len(manual_items) == 1
        assert manual_items[0].description == "Theoriekurs"
        assert Decimal(str(manual_items[0].amount)) == Decimal("50.00")
        assert len(load_items) == 1  # automatische Sprungposition bleibt erhalten

        # Gesamtsumme = Sprungposition (50,00) + manuelle Position (50,00)
        assert Decimal(str(invoice.total_amount)) == Decimal("100.00")


def test_manual_item_persists_after_reload(app_with_temp_db):
    from app import db
    from app.models.person import Person
    from app.models.invoice import Invoice
    from app.models.invoice_item import InvoiceItem

    app = app_with_temp_db
    with app.app_context():
        person = _make_person(db, Person)
        invoice = _make_manual_only_draft(db, Invoice, InvoiceItem, person.id)
        invoice_id = invoice.id

    client = app.test_client()
    client.post(
        f"/billing/invoice/{invoice_id}/manual_item/add",
        data={
            "manual_item_description": "Übernachtung",
            "manual_item_quantity": "1,00",
            "manual_item_unit_price_gross": "60,00",
            "manual_item_vat_rate": "7,00",
        },
    )

    # Reload über GET-Aufruf der Detailseite simulieren
    with app.app_context():
        db.session.remove()
        invoice = Invoice.query.get(invoice_id)
        descriptions = sorted((it.description or "") for it in invoice.items)
        assert "Übernachtung" in descriptions
        assert len(invoice.items) == 2


def test_manual_item_add_rejected_for_finalized_invoice(app_with_temp_db):
    from app import db
    from app.models.person import Person
    from app.models.invoice import Invoice
    from app.models.invoice_item import InvoiceItem

    app = app_with_temp_db
    with app.app_context():
        person = _make_person(db, Person)
        invoice = _make_manual_only_draft(db, Invoice, InvoiceItem, person.id)
        invoice.stage = "final"
        invoice.seq_number = 1
        db.session.commit()
        invoice_id = invoice.id
        item_count_before = len(invoice.items)

    client = app.test_client()
    client.post(
        f"/billing/invoice/{invoice_id}/manual_item/add",
        data={
            "manual_item_description": "Sollte nicht gespeichert werden",
            "manual_item_quantity": "1,00",
            "manual_item_unit_price_gross": "10,00",
            "manual_item_vat_rate": "19,00",
        },
    )

    with app.app_context():
        invoice = Invoice.query.get(invoice_id)
        assert len(invoice.items) == item_count_before


def test_manual_item_delete_only_removes_manual_items(app_with_temp_db):
    from app import db
    from app.models.person import Person
    from app.models.invoice import Invoice
    from app.models.invoice_item import InvoiceItem
    from app.models.load import Load
    from app.models.load_entry import LoadEntry
    from app.models.flugplatz import Flugplatz
    from app.models.aircraft import Aircraft

    app = app_with_temp_db
    with app.app_context():
        person = _make_person(db, Person)
        invoice = _make_jump_draft_invoice(
            db, Invoice, InvoiceItem, Load, LoadEntry, Flugplatz, Aircraft, person.id
        )
        invoice_id = invoice.id
        load_item_id = invoice.items[0].id

    client = app.test_client()
    # Versuch, die automatische Sprungposition über den manuellen Löschendpunkt zu entfernen -> muss fehlschlagen
    client.post(f"/billing/invoice/{invoice_id}/manual_item/{load_item_id}/delete")

    with app.app_context():
        invoice = Invoice.query.get(invoice_id)
        assert len(invoice.items) == 1
        assert invoice.items[0].item_source == "load"

    # Manuelle Position hinzufügen und anschließend gezielt entfernen
    client.post(
        f"/billing/invoice/{invoice_id}/manual_item/add",
        data={
            "manual_item_description": "Essen",
            "manual_item_quantity": "1,00",
            "manual_item_unit_price_gross": "12,00",
            "manual_item_vat_rate": "19,00",
        },
    )

    with app.app_context():
        invoice = Invoice.query.get(invoice_id)
        manual_item_id = next(it.id for it in invoice.items if it.item_source == "manual")

    client.post(f"/billing/invoice/{invoice_id}/manual_item/{manual_item_id}/delete")

    with app.app_context():
        invoice = Invoice.query.get(invoice_id)
        assert len(invoice.items) == 1
        assert invoice.items[0].item_source == "load"
        assert Decimal(str(invoice.total_amount)) == Decimal("50.00")


def test_full_manual_edit_form_blocked_for_mixed_invoice(app_with_temp_db):
    from app import db
    from app.models.person import Person
    from app.models.invoice import Invoice
    from app.models.invoice_item import InvoiceItem
    from app.models.load import Load
    from app.models.load_entry import LoadEntry
    from app.models.flugplatz import Flugplatz
    from app.models.aircraft import Aircraft

    app = app_with_temp_db
    with app.app_context():
        person = _make_person(db, Person)
        invoice = _make_jump_draft_invoice(
            db, Invoice, InvoiceItem, Load, LoadEntry, Flugplatz, Aircraft, person.id
        )
        invoice_id = invoice.id

    client = app.test_client()
    client.post(
        f"/billing/invoice/{invoice_id}/manual_item/add",
        data={
            "manual_item_description": "Essen",
            "manual_item_quantity": "1,00",
            "manual_item_unit_price_gross": "12,00",
            "manual_item_vat_rate": "19,00",
        },
    )

    # Voller Bearbeitungsdialog (/billing/manual/new) darf gemischte Rechnung
    # NICHT ersetzen (würde sonst die Sprungposition löschen) -> Redirect zurück zur Detailseite.
    response = client.get(
        f"/billing/manual/new?draft_invoice_id={invoice_id}",
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert f"/billing/invoice/{invoice_id}" in response.headers.get("Location", "")

    with app.app_context():
        invoice = Invoice.query.get(invoice_id)
        assert len(invoice.items) == 2  # nichts wurde gelöscht


def test_manual_invoice_new_still_works_for_pure_manual_draft(app_with_temp_db):
    from app import db
    from app.models.person import Person
    from app.models.invoice import Invoice
    from app.models.invoice_item import InvoiceItem

    app = app_with_temp_db
    with app.app_context():
        person = _make_person(db, Person)
        invoice = _make_manual_only_draft(db, Invoice, InvoiceItem, person.id)
        invoice_id = invoice.id

    client = app.test_client()
    response = client.get(f"/billing/manual/new?draft_invoice_id={invoice_id}")
    assert response.status_code == 200
    assert "Entwurf geladen" in response.get_data(as_text=True)


def test_persons_overview_still_reachable(app_with_temp_db):
    app = app_with_temp_db
    client = app.test_client()
    response = client.get("/billing/persons")
    assert response.status_code == 200
