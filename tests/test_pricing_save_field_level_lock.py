from __future__ import annotations

import os
from datetime import date, datetime
from decimal import Decimal

import pytest


@pytest.fixture()
def app_with_pricing_db(tmp_path):
    runtime_home = tmp_path / "runtime"
    db_file = runtime_home / "manifest_test.db"
    runtime_home.mkdir(parents=True, exist_ok=True)

    os.environ["MANIFEST_RUNTIME_HOME"] = str(runtime_home)
    os.environ["MANIFEST_DB_PATH"] = str(db_file)
    os.environ["MANIFEST_ENV"] = "dev"
    os.environ["MANIFEST_AUTO_CREATE_DB"] = "1"

    from app import create_app, db
    from app.models.aircraft import Aircraft
    from app.models.billing_config import BillingConfig, BillingPrice, BillingPricePeriod
    from app.models.flugplatz import Flugplatz
    from app.models.invoice import Invoice
    from app.models.invoice_item import InvoiceItem
    from app.models.load import Load
    from app.models.load_entry import LoadEntry
    from app.models.person import Person
    from app.models.status_definition import StatusDefinition

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()

        config = BillingConfig(
            company_name="Test GmbH",
            street="Testweg 1",
            zip_code="12345",
            city="Dessau",
            canopy_rent_member_eur=Decimal("15.00"),
            canopy_rent_member_max_count=3,
            canopy_rent_member_vat_rate=Decimal("7.00"),
            canopy_rent_partner_member_eur=Decimal("15.00"),
            canopy_rent_partner_member_max_count=3,
            canopy_rent_partner_member_vat_rate=Decimal("7.00"),
            canopy_rent_guest_eur=Decimal("20.00"),
            canopy_rent_guest_max_count=3,
            canopy_rent_guest_vat_rate=Decimal("7.00"),
            canopy_rent_tm_eur=Decimal("25.00"),
            canopy_rent_tm_max_count=50,
            canopy_rent_tm_vat_rate=Decimal("19.00"),
        )
        db.session.add(config)

        period = BillingPricePeriod(
            name="P1",
            valid_from=date(2026, 1, 1),
            valid_to=None,
            orga_fee_eur=Decimal("10.00"),
            orga_fee_mode="period",
            orga_fee_vat_strategy="max_status",
        )
        db.session.add(period)
        db.session.flush()

        sd_td = StatusDefinition(
            code="TD",
            label="Tandemmaster",
            sort_order=10,
            vat_rate=Decimal("19.00"),
            is_active=True,
            valid_from=datetime.utcnow(),
        )
        sd_aff = StatusDefinition(
            code="Aff-Lehrer",
            label="AFF-Lehrer",
            sort_order=20,
            vat_rate=Decimal("19.00"),
            is_active=True,
            valid_from=datetime.utcnow(),
        )
        db.session.add_all([sd_td, sd_aff])

        for code, p1500, p3000, p4000 in [
            ("TD", "50.00", "60.00", "70.00"),
            ("Aff-Lehrer", "80.00", "90.00", "100.00"),
        ]:
            db.session.add(
                BillingPrice(
                    period_id=period.id,
                    status_code=code,
                    height_m=1500,
                    price_eur=Decimal(p1500),
                    ku_credit_payout_basis="gross",
                )
            )
            db.session.add(
                BillingPrice(
                    period_id=period.id,
                    status_code=code,
                    height_m=3000,
                    price_eur=Decimal(p3000),
                    ku_credit_payout_basis="gross",
                )
            )
            db.session.add(
                BillingPrice(
                    period_id=period.id,
                    status_code=code,
                    height_m=4000,
                    price_eur=Decimal(p4000),
                    ku_credit_payout_basis="gross",
                )
            )

        airfield = Flugplatz(name="Testplatz", color="#123456", active=True)
        aircraft = Aircraft(type="Cessna", registration="D-TEST", seats=4, default_height=4000, active=True)
        person = Person(first_name="Max", last_name="Mustermann", phone="123", email="max@example.org", weight_kg=80)
        db.session.add_all([airfield, aircraft, person])
        db.session.flush()

        load = Load(
            load_number=1,
            height_m=4000,
            status="completed",
            created_at=datetime.utcnow(),
            scheduled_time=datetime.utcnow(),
            actual_time=datetime.utcnow(),
            fuel_required=False,
            airfield_id=airfield.id,
            aircraft_id=aircraft.id,
            pricing_model_id=period.id,
        )
        db.session.add(load)
        db.session.flush()

        entry = LoadEntry(
            load_id=load.id,
            person_id=person.id,
            status_definition_id=sd_td.id,
            seat=1,
            height_m=4000,
            status_code="TD",
            billed=True,
            billed_at=datetime.utcnow(),
        )
        db.session.add(entry)
        db.session.flush()

        invoice = Invoice(person_id=person.id, stage="final", is_deleted=False, total_amount=Decimal("70.00"))
        db.session.add(invoice)
        db.session.flush()

        db.session.add(
            InvoiceItem(
                invoice_id=invoice.id,
                load_entry_id=entry.id,
                amount=Decimal("70.00"),
                vat_rate=Decimal("19.00"),
                net_amount=Decimal("58.82"),
                vat_amount=Decimal("11.18"),
                description="Sprung 4000 m - Tandemmaster",
            )
        )

        db.session.commit()

    yield app

    with app.app_context():
        db.session.remove()


def _post_matrix(client, data):
    with client.session_transaction() as sess:
        sess["is_admin"] = True
    return client.post("/pricing/save", data=data, follow_redirects=False)


def test_pricing_save_keeps_locked_fields_but_saves_canopy_rent(app_with_pricing_db):
    from app import db
    from app.models.billing_config import BillingConfig, BillingPrice
    from app.models.status_definition import StatusDefinition

    app = app_with_pricing_db
    client = app.test_client()

    response = _post_matrix(
        client,
        {
            "period_id": "1",
            "status_code": ["TD"],
            "vat_TD": "7.00",
            "price_TD_1500": "50.00",
            "price_TD_3000": "60.00",
            "price_TD_4000": "99.00",
            "ku_credit_basis_TD": "gross",
            "orga_TD": "1",
            "canopy_rent_verein_eur": "15.00",
            "canopy_rent_verein_max_count": "3",
            "canopy_rent_verein_vat_rate": "7.00",
            "canopy_rent_partner_verein_eur": "15.00",
            "canopy_rent_partner_verein_max_count": "3",
            "canopy_rent_partner_verein_vat_rate": "7.00",
            "canopy_rent_gast_eur": "31.00",
            "canopy_rent_gast_max_count": "3",
            "canopy_rent_gast_vat_rate": "7.00",
            "canopy_rent_tandemmaster_eur": "25.00",
            "canopy_rent_tandemmaster_max_count": "50",
            "canopy_rent_tandemmaster_vat_rate": "19.00",
            "orga_fee_eur": "10.00",
            "orga_fee_mode": "period",
            "orga_fee_vat_strategy": "max_status",
        },
    )

    assert response.status_code == 302

    with app.app_context():
        td = (
            StatusDefinition.query
            .filter_by(code="TD", is_active=True)
            .order_by(StatusDefinition.valid_from.desc())
            .first()
        )
        td_4000 = BillingPrice.query.filter_by(period_id=1, status_code="TD", height_m=4000).first()
        cfg = BillingConfig.query.first()

        assert td is not None
        assert td_4000 is not None
        assert cfg is not None

        assert Decimal(str(td.vat_rate)) == Decimal("19.00")
        assert Decimal(str(td_4000.price_eur)) == Decimal("70.00")
        assert Decimal(str(cfg.canopy_rent_guest_eur)) == Decimal("31.00")

    with client.session_transaction() as sess:
        flashes = sess.get("_flashes", [])
    messages = " | ".join(msg for _, msg in flashes)
    assert "wurden nicht gespeichert" in messages


def test_pricing_save_persists_unlocked_status_in_same_submit(app_with_pricing_db):
    from app import db
    from app.models.billing_config import BillingPrice

    app = app_with_pricing_db
    client = app.test_client()

    response = _post_matrix(
        client,
        {
            "period_id": "1",
            "status_code": ["TD", "Aff-Lehrer"],
            "vat_TD": "7.00",
            "price_TD_1500": "50.00",
            "price_TD_3000": "60.00",
            "price_TD_4000": "99.00",
            "ku_credit_basis_TD": "gross",
            "orga_TD": "1",
            "vat_Aff-Lehrer": "19.00",
            "price_Aff-Lehrer_1500": "80.00",
            "price_Aff-Lehrer_3000": "90.00",
            "price_Aff-Lehrer_4000": "123.00",
            "ku_credit_basis_Aff-Lehrer": "gross",
            "orga_Aff-Lehrer": "1",
            "canopy_rent_verein_eur": "15.00",
            "canopy_rent_verein_max_count": "3",
            "canopy_rent_verein_vat_rate": "7.00",
            "canopy_rent_partner_verein_eur": "15.00",
            "canopy_rent_partner_verein_max_count": "3",
            "canopy_rent_partner_verein_vat_rate": "7.00",
            "canopy_rent_gast_eur": "20.00",
            "canopy_rent_gast_max_count": "3",
            "canopy_rent_gast_vat_rate": "7.00",
            "canopy_rent_tandemmaster_eur": "25.00",
            "canopy_rent_tandemmaster_max_count": "50",
            "canopy_rent_tandemmaster_vat_rate": "19.00",
            "orga_fee_eur": "10.00",
            "orga_fee_mode": "period",
            "orga_fee_vat_strategy": "max_status",
        },
    )

    assert response.status_code == 302

    with app.app_context():
        td_4000 = BillingPrice.query.filter_by(period_id=1, status_code="TD", height_m=4000).first()
        aff_4000 = BillingPrice.query.filter_by(period_id=1, status_code="Aff-Lehrer", height_m=4000).first()

        assert td_4000 is not None
        assert aff_4000 is not None

        assert Decimal(str(td_4000.price_eur)) == Decimal("70.00")
        assert Decimal(str(aff_4000.price_eur)) == Decimal("123.00")
