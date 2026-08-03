from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import io
import re
import pytest


def _q2(value: Decimal | str | int | float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _split_gross(gross: Decimal, vat_rate: Decimal) -> tuple[Decimal, Decimal]:
    gross = _q2(gross)
    vat_rate = _q2(vat_rate)
    if vat_rate <= 0:
        return gross, Decimal("0.00")
    factor = Decimal("1.00") + (vat_rate / Decimal("100.00"))
    net = _q2(gross / factor)
    vat = _q2(gross - net)
    return net, vat


@pytest.fixture(scope="module")
def seeded_app(tmp_path_factory):
    runtime_home = tmp_path_factory.mktemp("ku_runtime")
    db_file = runtime_home / "manifest_test.db"

    import os

    os.environ["MANIFEST_RUNTIME_HOME"] = str(runtime_home)
    os.environ["MANIFEST_DB_PATH"] = str(db_file)
    os.environ["MANIFEST_ENV"] = "dev"
    os.environ["MANIFEST_AUTO_CREATE_DB"] = "1"
    os.environ["MANIFEST_AUTO_DB_UPGRADE"] = "0"

    from app import create_app, db
    from app.models.aircraft import Aircraft
    from app.models.billing_config import BillingPrice, BillingPricePeriod
    from app.models.flugplatz import Flugplatz
    from app.models.invoice import Invoice
    from app.models.invoice_item import InvoiceItem
    from app.models.load import Load
    from app.models.load_entry import LoadEntry
    from app.models.person import Person
    from app.models.status_definition import StatusDefinition
    from app.services.billing_service import BillingService

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        db.drop_all()
        db.create_all()

        airfield = Flugplatz(name="Testplatz", color="#123456", active=True)
        aircraft = Aircraft(type="Cessna", registration="D-TEST", seats=4, default_height=4000, active=True)
        db.session.add_all([airfield, aircraft])

        sd_td = StatusDefinition(
            code="TD",
            label="Tandemmaster",
            sort_order=10,
            vat_rate=Decimal("19.00"),
            is_active=True,
            valid_from=datetime.utcnow(),
        )
        sd_verein = StatusDefinition(
            code="Verein",
            label="Verein",
            sort_order=20,
            vat_rate=Decimal("19.00"),
            is_active=True,
            valid_from=datetime.utcnow(),
        )
        sd_video = StatusDefinition(
            code="Video",
            label="Video",
            sort_order=30,
            vat_rate=Decimal("19.00"),
            is_active=True,
            valid_from=datetime.utcnow(),
        )
        sd_gast7 = StatusDefinition(
            code="Gast-7",
            label="Gast 7%",
            sort_order=40,
            vat_rate=Decimal("7.00"),
            is_active=True,
            valid_from=datetime.utcnow(),
        )
        sd_aff = StatusDefinition(
            code="Aff-Lehrer",
            label="AFF-Lehrer",
            sort_order=35,
            vat_rate=Decimal("19.00"),
            is_active=True,
            valid_from=datetime.utcnow(),
        )
        db.session.add_all([sd_td, sd_verein, sd_video, sd_gast7, sd_aff])

        p1 = Person(first_name="Case1", last_name="Regel", phone="111", email="c1@example.org", weight_kg=80, is_tandemmaster=True)
        p2 = Person(
            first_name="Case2",
            last_name="KU",
            phone="222",
            email="c2@example.org",
            weight_kg=81,
            is_tandemmaster=True,
            is_tandem_kleinunternehmer=True,
        )
        p3 = Person(first_name="Case3", last_name="Gemischt", phone="333", email="c3@example.org", weight_kg=82, is_tandemmaster=True)
        p4 = Person(first_name="Case4", last_name="Nachtraeglich", phone="444", email="c4@example.org", weight_kg=83, is_tandemmaster=True)
        p5 = Person(first_name="Case5", last_name="VideoRegel", phone="555", email="c5@example.org", weight_kg=84, is_video=True)
        p6 = Person(
            first_name="Case6",
            last_name="VideoKU",
            phone="666",
            email="c6@example.org",
            weight_kg=85,
            is_video=True,
            is_video_kleinunternehmer=True,
        )
        p7 = Person(
            first_name="Case7",
            last_name="MixTDVideo",
            phone="777",
            email="c7@example.org",
            weight_kg=86,
            is_tandemmaster=True,
            is_video=True,
            is_tandem_kleinunternehmer=True,
            is_video_kleinunternehmer=True,
        )
        p8 = Person(first_name="Case8", last_name="VideoNachtraeglich", phone="888", email="c8@example.org", weight_kg=87, is_video=True)
        p9 = Person(first_name="Case9", last_name="Mixed7", phone="999", email="c9@example.org", weight_kg=88, is_tandemmaster=True)
        p10 = Person(
            first_name="Case10",
            last_name="AFFKU",
            phone="1010",
            email="c10@example.org",
            weight_kg=89,
            is_aff_teacher=True,
            is_aff_teacher_kleinunternehmer=True,
        )
        db.session.add_all([p1, p2, p3, p4, p5, p6, p7, p8, p9, p10])
        db.session.flush()

        def add_load_entry(person: Person, status_code: str, status_def: StatusDefinition, load_no: int) -> LoadEntry:
            load = Load(
                load_number=load_no,
                height_m=4000,
                status="completed",
                created_at=datetime.utcnow(),
                scheduled_time=datetime.utcnow(),
                actual_time=datetime.utcnow(),
                fuel_required=False,
                airfield_id=airfield.id,
                aircraft_id=aircraft.id,
            )
            db.session.add(load)
            db.session.flush()

            entry = LoadEntry(
                load_id=load.id,
                person_id=person.id,
                status_definition_id=status_def.id,
                seat=1,
                height_m=4000,
                status_code=status_code,
                billed=True,
                billed_at=datetime.utcnow(),
            )
            db.session.add(entry)
            db.session.flush()
            return entry

        e1 = add_load_entry(p1, "TD", sd_td, 101)
        e2 = add_load_entry(p2, "TD", sd_td, 102)
        e3_td = add_load_entry(p3, "TD", sd_td, 103)
        e3_norm = add_load_entry(p3, "Verein", sd_verein, 104)
        e4 = add_load_entry(p4, "TD", sd_td, 105)
        e5 = add_load_entry(p5, "Video", sd_video, 106)
        e6 = add_load_entry(p6, "Video", sd_video, 107)
        e7_td = add_load_entry(p7, "TD", sd_td, 108)
        e7_video = add_load_entry(p7, "Video", sd_video, 109)
        e8 = add_load_entry(p8, "Video", sd_video, 110)
        e9_td = add_load_entry(p9, "TD", sd_td, 111)
        e9_gast7 = add_load_entry(p9, "Gast-7", sd_gast7, 112)
        e10_aff = add_load_entry(p10, "Aff-Lehrer", sd_aff, 113)

        # Offene Einträge für /billing/person/{id} Vorschau-Tests
        preview_e1 = add_load_entry(p1, "TD", sd_td, 201)
        preview_e2 = add_load_entry(p2, "TD", sd_td, 202)
        preview_e6 = add_load_entry(p6, "Video", sd_video, 203)
        preview_e10 = add_load_entry(p10, "Aff-Lehrer", sd_aff, 204)
        preview_e1.billed = False
        preview_e1.billed_at = None
        preview_e2.billed = False
        preview_e2.billed_at = None
        preview_e6.billed = False
        preview_e6.billed_at = None
        preview_e10.billed = False
        preview_e10.billed_at = None

        def add_invoice(
            *,
            person: Person,
            seq: int,
            ku: bool,
            entries_with_amounts: list[tuple[LoadEntry, Decimal]],
            created_at: datetime,
        ) -> Invoice:
            inv = Invoice(
                person_id=person.id,
                created_at=created_at,
                stage="final",
                seq_number=seq,
                is_tandem_kleinunternehmer=ku,
                is_paid=False,
                is_deleted=False,
            )
            db.session.add(inv)
            db.session.flush()

            for entry, gross in entries_with_amounts:
                vat_rate = Decimal(str(BillingService.get_entry_vat_rate(entry) or "0.00"))
                net, vat = _split_gross(gross, vat_rate)
                item = InvoiceItem(
                    invoice_id=inv.id,
                    load_entry_id=entry.id,
                    amount=_q2(gross),
                    vat_rate=vat_rate,
                    net_amount=net,
                    vat_amount=vat,
                    description=f"Sprung {entry.height_m} m - {entry.status_code}",
                    item_source="load",
                )
                db.session.add(item)

            db.session.flush()
            BillingService.recalculate_invoice_tandemmaster_tax(inv)
            inv.calculate_total()
            db.session.flush()
            return inv

        inv1 = add_invoice(person=p1, seq=7001, ku=False, entries_with_amounts=[(e1, Decimal("119.00"))], created_at=datetime(2026, 7, 1, 10, 0, 0))
        inv2 = add_invoice(person=p2, seq=7002, ku=True, entries_with_amounts=[(e2, Decimal("119.00"))], created_at=datetime(2026, 7, 1, 11, 0, 0))
        inv3 = add_invoice(
            person=p3,
            seq=7003,
            ku=True,
            entries_with_amounts=[(e3_td, Decimal("-119.00")), (e3_norm, Decimal("-119.00"))],
            created_at=datetime(2026, 7, 1, 12, 0, 0),
        )
        inv4 = add_invoice(person=p4, seq=7004, ku=False, entries_with_amounts=[(e4, Decimal("119.00"))], created_at=datetime(2026, 7, 1, 13, 0, 0))

        inv5 = add_invoice(person=p5, seq=7005, ku=False, entries_with_amounts=[(e5, Decimal("119.00"))], created_at=datetime(2026, 7, 1, 14, 0, 0))
        inv5.is_video_kleinunternehmer = False

        inv6 = add_invoice(person=p6, seq=7006, ku=False, entries_with_amounts=[(e6, Decimal("119.00"))], created_at=datetime(2026, 7, 1, 15, 0, 0))
        inv6.is_video_kleinunternehmer = True
        BillingService.recalculate_invoice_ku_tax(inv6)
        inv6.calculate_total()

        inv7 = add_invoice(
            person=p7,
            seq=7007,
            ku=True,
            entries_with_amounts=[(e7_td, Decimal("119.00")), (e7_video, Decimal("119.00"))],
            created_at=datetime(2026, 7, 1, 16, 0, 0),
        )
        inv7.is_video_kleinunternehmer = True
        BillingService.recalculate_invoice_ku_tax(inv7)
        inv7.calculate_total()

        inv8 = add_invoice(person=p8, seq=7008, ku=False, entries_with_amounts=[(e8, Decimal("119.00"))], created_at=datetime(2026, 7, 1, 17, 0, 0))
        inv8.is_video_kleinunternehmer = False

        inv9 = add_invoice(
            person=p9,
            seq=7009,
            ku=True,
            entries_with_amounts=[(e9_td, Decimal("-75.00")), (e9_gast7, Decimal("35.00"))],
            created_at=datetime(2026, 7, 1, 18, 0, 0),
        )
        inv10 = add_invoice(
            person=p10,
            seq=7010,
            ku=False,
            entries_with_amounts=[(e10_aff, Decimal("119.00"))],
            created_at=datetime(2026, 7, 1, 19, 0, 0),
        )
        inv10.is_aff_teacher_kleinunternehmer = True
        BillingService.recalculate_invoice_ku_tax(inv10)
        inv10.calculate_total()

        db.session.commit()

        with app.test_client() as client:
            yield {
                "app": app,
                "client": client,
                "db": db,
                "models": {
                    "Invoice": Invoice,
                    "InvoiceItem": InvoiceItem,
                    "Person": Person,
                },
                "ids": {
                    "case1": {"person_id": p1.id, "invoice_id": inv1.id, "seq": inv1.seq_number},
                    "case2": {"person_id": p2.id, "invoice_id": inv2.id, "seq": inv2.seq_number},
                    "case3": {"person_id": p3.id, "invoice_id": inv3.id, "seq": inv3.seq_number},
                    "case4": {"person_id": p4.id, "invoice_id": inv4.id, "seq": inv4.seq_number},
                    "case5": {"person_id": p5.id, "invoice_id": inv5.id, "seq": inv5.seq_number},
                    "case6": {"person_id": p6.id, "invoice_id": inv6.id, "seq": inv6.seq_number},
                    "case7": {"person_id": p7.id, "invoice_id": inv7.id, "seq": inv7.seq_number},
                    "case8": {"person_id": p8.id, "invoice_id": inv8.id, "seq": inv8.seq_number},
                    "case9": {"person_id": p9.id, "invoice_id": inv9.id, "seq": inv9.seq_number},
                    "case10": {"person_id": p10.id, "invoice_id": inv10.id, "seq": inv10.seq_number},
                },
            }


def test_ku_credit_payout_basis_is_taken_from_price_matrix_status_setting(seeded_app):
    app = seeded_app["app"]
    db = seeded_app["db"]
    Invoice = seeded_app["models"]["Invoice"]
    InvoiceItem = seeded_app["models"]["InvoiceItem"]
    entry = db.session.get("app.models.load_entry.LoadEntry", 2) if False else None

    with app.app_context():
        from app.models.load_entry import LoadEntry
        from app.models.billing_config import BillingPricePeriod, BillingPrice
        from app.services.billing_service import BillingService

        entry = db.session.query(LoadEntry).filter_by(id=2).first()
        assert entry is not None

        period = BillingPricePeriod(
            name="Test-Periode KU-Basis",
            valid_from=datetime(2026, 1, 1),
            valid_to=None,
        )
        db.session.add(period)
        db.session.flush()

        db.session.add(
            BillingPrice(
                period_id=period.id,
                status_code="TD",
                height_m=4000,
                price_eur=Decimal("119.00"),
                ku_credit_payout_basis="net",
            )
        )
        db.session.flush()

        entry.load.pricing_model_id = period.id
        db.session.flush()

        invoice = Invoice(person_id=entry.person_id, created_at=datetime.utcnow(), stage="draft")
        invoice.is_tandem_kleinunternehmer = True
        db.session.add(invoice)
        db.session.flush()

        BillingService._add_jump_items(invoice, [entry], mark_billed=False)
        db.session.flush()

        item = db.session.query(InvoiceItem).filter_by(invoice_id=invoice.id).first()
        assert item is not None
        assert item.amount == Decimal("100.00")
        assert item.net_amount == Decimal("100.00")
        assert item.vat_amount == Decimal("0.00")
        assert item.vat_rate == Decimal("0.00")
        assert item.price_source_eur == Decimal("119.00")
        assert item.price_source_vat_rate == Decimal("19.00")
        assert item.ku_credit_payout_basis == "net"
        assert item.ku_credit_payout_amount == Decimal("100.00")


def test_case_10_aff_teacher_ku_recalc_uses_zero_vat_and_payout_basis(seeded_app):
    app = seeded_app["app"]
    Invoice = seeded_app["models"]["Invoice"]
    case = seeded_app["ids"]["case10"]

    with app.app_context():
        inv = Invoice.query.get(case["invoice_id"])
        assert inv is not None
        assert inv.is_aff_teacher_kleinunternehmer is True
        item = inv.items[0]
        assert _q2(item.amount) == Decimal("119.00")
        assert _q2(item.net_amount) == Decimal("119.00")
        assert _q2(item.vat_amount) == Decimal("0.00")
        assert _q2(item.vat_rate) == Decimal("0.00")
        assert item.ku_credit_payout_basis == "gross"


def test_preview_aff_teacher_toggle_is_available_and_updates_rows(seeded_app):
    client = seeded_app["client"]
    case = seeded_app["ids"]["case10"]

    r = client.get(f"/billing/person/{case['person_id']}")
    assert r.status_code == 200
    html = r.data.decode("utf-8", errors="ignore")

    assert 'id="invoice_is_aff_teacher_kleinunternehmer"' in html
    assert 'data-is-aff-teacher="' in html
    assert 'const affTeacherKuSelect = document.getElementById("invoice_is_aff_teacher_kleinunternehmer");' in html


def test_aff_teacher_vat_lookup_uses_normalized_status_code(seeded_app):
    app = seeded_app["app"]
    db = seeded_app["db"]

    with app.app_context():
        from app.models.load_entry import LoadEntry
        from app.models.status_definition import StatusDefinition
        from app.services.billing_service import BillingService

        entry = db.session.query(LoadEntry).filter_by(status_code="Aff-Lehrer").first()
        assert entry is not None

        entry.status_definition_id = None
        entry.status_definition = None
        db.session.flush()

        sd_upper = StatusDefinition(
            code="AFF-LEHRER",
            label="AFF-LEHRER",
            sort_order=35,
            vat_rate=Decimal("19.00"),
            is_active=True,
            valid_from=datetime.utcnow(),
        )
        db.session.add(sd_upper)
        db.session.flush()

        vat_rate = BillingService.get_entry_vat_rate(entry)
        assert vat_rate == Decimal("19.00")


def test_aff_teacher_vat_lookup_falls_back_to_case_insensitive_status_definition(seeded_app):
    app = seeded_app["app"]
    db = seeded_app["db"]

    with app.app_context():
        from app.models.load_entry import LoadEntry
        from app.models.status_definition import StatusDefinition
        from app.services.billing_service import BillingService

        entry = db.session.query(LoadEntry).filter_by(status_code="Aff-Lehrer").first()
        assert entry is not None

        entry.status_definition_id = None
        entry.status_definition = None
        db.session.flush()

        for existing in db.session.query(StatusDefinition).filter(StatusDefinition.code == "Aff-Lehrer").all():
            db.session.delete(existing)

        sd_upper = StatusDefinition(
            code="AFF-LEHRER",
            label="AFF-LEHRER",
            sort_order=35,
            vat_rate=Decimal("19.00"),
            is_active=True,
            valid_from=datetime.utcnow(),
        )
        db.session.add(sd_upper)
        db.session.flush()

        vat_rate = BillingService.get_entry_vat_rate(entry)
        assert vat_rate == Decimal("19.00")


def test_get_jump_item_calculation_keeps_negative_gross_for_ku_payout(seeded_app):
    app = seeded_app["app"]
    db = seeded_app["db"]

    with app.app_context():
        from app.models.billing_config import BillingPrice, BillingPricePeriod
        from app.models.load_entry import LoadEntry
        from app.services.billing_service import BillingService

        entry = db.session.query(LoadEntry).filter_by(status_code="TD").first()
        assert entry is not None

        period = BillingPricePeriod(
            name="Test-Periode Negativ-Gross",
            valid_from=datetime(2026, 1, 1),
            valid_to=None,
        )
        db.session.add(period)
        db.session.flush()

        db.session.add(
            BillingPrice(
                period_id=period.id,
                status_code="TD",
                height_m=4000,
                price_eur=Decimal("-89.25"),
                ku_credit_payout_basis="net",
            )
        )
        entry.load.pricing_model_id = period.id
        db.session.flush()

        calc = BillingService.get_jump_item_calculation(
            entry=entry,
            ku_active_for_entry=True,
            fallback_gross=Decimal("-63.03"),
        )

        assert calc["gross"] == Decimal("-89.25")
        assert calc["effective_amount"] == Decimal("-75.00")
        assert calc["net"] == Decimal("-75.00")
        assert calc["vat"] == Decimal("0.00")
        assert calc["vat_rate"] == Decimal("0.00")
        assert calc["payout_basis"] == "net"
        assert calc["payout_amount"] == Decimal("-75.00")


def test_preview_aff_teacher_ku_uses_payout_basis_for_aff_teacher_rows(seeded_app):
    app = seeded_app["app"]
    db = seeded_app["db"]
    case = seeded_app["ids"]["case10"]

    with app.app_context():
        from app.models.billing_config import BillingPrice, BillingPricePeriod
        from app.models.load_entry import LoadEntry

        entry = db.session.query(LoadEntry).filter_by(person_id=case["person_id"], status_code="Aff-Lehrer").order_by(LoadEntry.id.desc()).first()
        assert entry is not None

        period = BillingPricePeriod(
            name="Test-Periode AFF-Preview",
            valid_from=datetime(2026, 1, 1),
            valid_to=None,
        )
        db.session.add(period)
        db.session.flush()

        db.session.add(
            BillingPrice(
                period_id=period.id,
                status_code="Aff-Lehrer",
                height_m=4000,
                price_eur=Decimal("119.00"),
                ku_credit_payout_basis="net",
            )
        )
        entry.load.pricing_model_id = period.id
        db.session.flush()
        db.session.commit()

        client = app.test_client()
        r = client.get(f"/billing/person/{case['person_id']}")
        assert r.status_code == 200
        html = r.data.decode("utf-8", errors="ignore")
        assert "100,00" in html


def test_persons_overview_aff_teacher_uses_preview_payout_amount(seeded_app):
    app = seeded_app["app"]
    db = seeded_app["db"]
    case = seeded_app["ids"]["case10"]

    with app.app_context():
        from app.models.billing_config import BillingPrice, BillingPricePeriod
        from app.models.load_entry import LoadEntry

        entry = db.session.query(LoadEntry).filter_by(person_id=case["person_id"], status_code="Aff-Lehrer").order_by(LoadEntry.id.desc()).first()
        assert entry is not None

        period = BillingPricePeriod(
            name="Test-Periode AFF-Overview",
            valid_from=datetime(2026, 1, 1),
            valid_to=None,
        )
        db.session.add(period)
        db.session.flush()

        db.session.add(
            BillingPrice(
                period_id=period.id,
                status_code="Aff-Lehrer",
                height_m=4000,
                price_eur=Decimal("119.00"),
                ku_credit_payout_basis="net",
            )
        )
        entry.load.pricing_model_id = period.id
        db.session.flush()
        db.session.commit()

    client = app.test_client()
    r = client.get("/billing/persons")
    assert r.status_code == 200
    html = r.data.decode("utf-8", errors="ignore")
    assert "100,00" in html


def test_invoice_detail_aff_teacher_toggle_supports_recalc(seeded_app):
    client = seeded_app["client"]
    case = seeded_app["ids"]["case10"]

    r = client.get(f"/billing/invoice/{case['seq']}")
    assert r.status_code == 200
    html = r.data.decode("utf-8", errors="ignore")

    assert 'id="invoiceIsAffTeacherKleinunternehmer"' in html
    assert "const affTeacherKuSelect = document.getElementById('invoiceIsAffTeacherKleinunternehmer') || document.getElementById('draftInvoiceIsAffTeacherKleinunternehmer');" in html


def _assert_common_endpoints(client, person_id: int, seq: int) -> None:
    r_detail = client.get(f"/billing/invoice/{seq}")
    assert r_detail.status_code == 200

    r_list = client.get(f"/billing/invoices?person_id={person_id}")
    assert r_list.status_code == 200

    r_stats = client.get(f"/loads/statistics?person_id={person_id}")
    assert r_stats.status_code == 200

    r_billing_pdf = client.get(f"/billing/invoices/pdf?person_id={person_id}")
    assert r_billing_pdf.status_code == 200
    assert r_billing_pdf.headers.get("Content-Type", "").startswith("application/pdf")
    assert r_billing_pdf.data.startswith(b"%PDF")

    r_stats_pdf = client.get(f"/loads/statistics/report.pdf?person_id={person_id}")
    assert r_stats_pdf.status_code == 200
    assert r_stats_pdf.headers.get("Content-Type", "").startswith("application/pdf")
    assert r_stats_pdf.data.startswith(b"%PDF")

    r_billing_csv = client.get(f"/billing/invoices/export/csv?person_id={person_id}")
    assert r_billing_csv.status_code == 200
    text_billing_csv = r_billing_csv.data.decode("utf-8-sig", errors="ignore")
    assert "Netto (EUR)" in text_billing_csv
    assert "MwSt (EUR)" in text_billing_csv

    r_stats_csv = client.get(f"/loads/statistics/export.csv?person_id={person_id}")
    assert r_stats_csv.status_code == 200
    text_stats_csv = r_stats_csv.data.decode("utf-8", errors="ignore")
    assert "Netto" in text_stats_csv
    assert "MwSt" in text_stats_csv

    r_billing_xlsx = client.get(f"/billing/invoices/export/xlsx?person_id={person_id}")
    assert r_billing_xlsx.status_code == 200
    assert r_billing_xlsx.headers.get("Content-Type", "").startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    r_stats_xlsx = client.get(f"/loads/statistics/export.xlsx?person_id={person_id}")
    assert r_stats_xlsx.status_code == 200
    assert r_stats_xlsx.headers.get("Content-Type", "").startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


def test_case_1_regelbesteuerter_tandemmaster(seeded_app):
    app = seeded_app["app"]
    client = seeded_app["client"]
    Invoice = seeded_app["models"]["Invoice"]
    case = seeded_app["ids"]["case1"]

    with app.app_context():
        inv = Invoice.query.get(case["invoice_id"])
        assert inv is not None
        assert inv.is_tandem_kleinunternehmer is False
        item = inv.items[0]
        assert _q2(item.amount) == Decimal("119.00")
        assert _q2(item.net_amount) == Decimal("100.00")
        assert _q2(item.vat_amount) == Decimal("19.00")
        assert _q2(item.vat_rate) == Decimal("19.00")

    _assert_common_endpoints(client, case["person_id"], case["seq"])



def test_case_2_kleinunternehmer_tandemmaster(seeded_app):
    app = seeded_app["app"]
    client = seeded_app["client"]
    Invoice = seeded_app["models"]["Invoice"]
    case = seeded_app["ids"]["case2"]

    with app.app_context():
        inv = Invoice.query.get(case["invoice_id"])
        assert inv is not None
        assert inv.is_tandem_kleinunternehmer is True
        item = inv.items[0]
        assert _q2(item.amount) == Decimal("119.00")
        assert _q2(item.net_amount) == Decimal("119.00")
        assert _q2(item.vat_amount) == Decimal("0.00")
        assert _q2(item.vat_rate) == Decimal("0.00")

    _assert_common_endpoints(client, case["person_id"], case["seq"])



def test_case_3_gemischte_gutschrift_ku_und_normal(seeded_app):
    app = seeded_app["app"]
    client = seeded_app["client"]
    Invoice = seeded_app["models"]["Invoice"]
    case = seeded_app["ids"]["case3"]

    with app.app_context():
        inv = Invoice.query.get(case["invoice_id"])
        assert inv is not None
        assert inv.is_tandem_kleinunternehmer is True
        assert len(inv.items) == 2

        td_item = next(i for i in inv.items if "TD" in (i.description or ""))
        normal_item = next(i for i in inv.items if "Verein" in (i.description or ""))

        assert _q2(td_item.amount) == Decimal("-119.00")
        assert _q2(td_item.net_amount) == Decimal("-119.00")
        assert _q2(td_item.vat_amount) == Decimal("0.00")
        assert _q2(td_item.vat_rate) == Decimal("0.00")

        assert _q2(normal_item.amount) == Decimal("-119.00")
        assert _q2(normal_item.net_amount) == Decimal("-100.00")
        assert _q2(normal_item.vat_amount) == Decimal("-19.00")
        assert _q2(normal_item.vat_rate) == Decimal("19.00")

    _assert_common_endpoints(client, case["person_id"], case["seq"])



def test_case_4_nachtraegliche_ku_aenderung_bei_unversandter_gutschrift(seeded_app):
    app = seeded_app["app"]
    client = seeded_app["client"]
    Invoice = seeded_app["models"]["Invoice"]
    case = seeded_app["ids"]["case4"]

    with app.app_context():
        inv_before = Invoice.query.get(case["invoice_id"])
        assert inv_before is not None
        assert inv_before.email_sent_ok is False
        assert inv_before.is_tandem_kleinunternehmer is False
        item_before = inv_before.items[0]
        assert _q2(item_before.vat_rate) == Decimal("19.00")
        assert _q2(item_before.vat_amount) == Decimal("19.00")

    r = client.post(
        f"/billing/invoice/{case['invoice_id']}/set_tandem_kleinunternehmer",
        data={"invoice_is_tandem_kleinunternehmer": "true"},
        follow_redirects=True,
    )
    assert r.status_code == 200

    with app.app_context():
        inv_after = Invoice.query.get(case["invoice_id"])
        assert inv_after is not None
        assert inv_after.is_tandem_kleinunternehmer is True
        item_after = inv_after.items[0]
        assert _q2(item_after.amount) == Decimal("119.00")
        assert _q2(item_after.net_amount) == Decimal("119.00")
        assert _q2(item_after.vat_amount) == Decimal("0.00")
        assert _q2(item_after.vat_rate) == Decimal("0.00")

    _assert_common_endpoints(client, case["person_id"], case["seq"])


def test_preview_initial_ku_from_master_data_shows_0_percent(seeded_app):
    client = seeded_app["client"]
    case = seeded_app["ids"]["case2"]

    r = client.get(f"/billing/person/{case['person_id']}")
    assert r.status_code == 200
    html = r.data.decode("utf-8", errors="ignore")

    assert 'id="invoice_is_tandem_kleinunternehmer"' in html
    assert 'option value="true" selected' in html
    assert 'js-ku-position-note is-visible' in html
    assert '>0.00<' in html
    assert 'data-is-tm="1"' in html


def test_preview_initial_regular_tax_from_master_data_shows_19_percent(seeded_app):
    client = seeded_app["client"]
    case = seeded_app["ids"]["case1"]

    r = client.get(f"/billing/person/{case['person_id']}")
    assert r.status_code == 200
    html = r.data.decode("utf-8", errors="ignore")

    assert 'id="invoice_is_tandem_kleinunternehmer"' in html
    assert 'option value="false" selected' in html
    assert 'js-ku-position-note is-visible' not in html
    assert '>19.00<' in html


def test_preview_live_update_hooks_present_for_ku_toggle(seeded_app):
    client = seeded_app["client"]
    case = seeded_app["ids"]["case2"]

    r = client.get(f"/billing/person/{case['person_id']}")
    assert r.status_code == 200
    html = r.data.decode("utf-8", errors="ignore")

    assert 'tandemKuSelect.addEventListener("change", recalculatePreview);' in html
    assert 'recalculatePreview();' in html
    assert 'id="previewTotalNet"' in html
    assert 'id="previewTotalVat"' in html
    assert 'class="js-entry-net-val"' in html
    assert 'class="js-entry-vat-val"' in html
    assert 'class="js-entry-vatrate-val"' in html


def test_created_invoice_uses_same_ku_default_as_preview(seeded_app):
    app = seeded_app["app"]
    client = seeded_app["client"]
    Invoice = seeded_app["models"]["Invoice"]
    case = seeded_app["ids"]["case2"]

    # Ohne expliziten KU-Formwert -> muss Stammdaten-Voreinstellung verwenden.
    r = client.post(
        f"/billing/person/{case['person_id']}/create_invoice",
        data={},
        follow_redirects=True,
    )
    assert r.status_code == 200

    with app.app_context():
        created = (
            Invoice.query
            .filter(Invoice.person_id == case["person_id"], Invoice.stage == "draft")
            .order_by(Invoice.id.desc())
            .first()
        )
        assert created is not None
        assert created.is_tandem_kleinunternehmer is True

        td_items = [
            item for item in list(created.items or [])
            if "Sprung" in (item.description or "") and "TD" in (item.description or "")
        ]
        assert td_items
        for item in td_items:
            assert _q2(item.vat_rate) == Decimal("0.00")
            assert _q2(item.vat_amount) == Decimal("0.00")


def test_invoice_detail_contains_live_ku_recalc_hooks(seeded_app):
    client = seeded_app["client"]
    case = seeded_app["ids"]["case4"]

    r = client.get(f"/billing/invoice/{case['seq']}")
    assert r.status_code == 200
    html = r.data.decode("utf-8", errors="ignore")

    assert 'function recalculateInvoiceKuView()' in html
    assert 'function bindInvoiceKuToggleRecalc()' in html
    assert 'id="invoiceJumpSumNet"' in html
    assert 'id="invoiceJumpSumVat"' in html
    assert 'id="invoiceSummaryNet"' in html
    assert 'id="invoiceSummaryVat"' in html
    assert 'class="js-invoice-jump-row"' in html
    assert 'class="js-invoice-row-net"' in html
    assert 'class="js-invoice-row-vat"' in html
    assert 'class="js-invoice-row-vat-rate"' in html


def test_invoice_detail_ku_position_notice_and_rates_rendered(seeded_app):
    client = seeded_app["client"]
    case_ku = seeded_app["ids"]["case2"]
    case_regular = seeded_app["ids"]["case1"]

    r_ku = client.get(f"/billing/invoice/{case_ku['seq']}")
    assert r_ku.status_code == 200
    html_ku = r_ku.data.decode("utf-8", errors="ignore")
    assert 'Kleinunternehmerregelung gem. § 19 UStG' in html_ku
    assert 'data-ku-eligible="1"' in html_ku
    assert 'data-base-vat-rate="19.00"' in html_ku
    assert '>0.00</span>%' in html_ku

    r_regular = client.get(f"/billing/invoice/{case_regular['seq']}")
    assert r_regular.status_code == 200
    html_regular = r_regular.data.decode("utf-8", errors="ignore")
    assert 'data-ku-eligible="1"' in html_regular
    assert 'data-base-vat-rate="19.00"' in html_regular
    # Bei Regelbesteuerung bleibt der Hinweis initial ausgeblendet.
    assert 'js-invoice-ku-note d-none' in html_regular


def test_case_5_regelbesteuertes_video(seeded_app):
    app = seeded_app["app"]
    client = seeded_app["client"]
    Invoice = seeded_app["models"]["Invoice"]
    case = seeded_app["ids"]["case5"]

    with app.app_context():
        inv = Invoice.query.get(case["invoice_id"])
        assert inv is not None
        assert inv.is_video_kleinunternehmer is False
        item = inv.items[0]
        assert _q2(item.amount) == Decimal("119.00")
        assert _q2(item.net_amount) == Decimal("100.00")
        assert _q2(item.vat_amount) == Decimal("19.00")
        assert _q2(item.vat_rate) == Decimal("19.00")

    _assert_common_endpoints(client, case["person_id"], case["seq"])


def test_case_6_kleinunternehmer_video(seeded_app):
    app = seeded_app["app"]
    client = seeded_app["client"]
    Invoice = seeded_app["models"]["Invoice"]
    case = seeded_app["ids"]["case6"]

    with app.app_context():
        inv = Invoice.query.get(case["invoice_id"])
        assert inv is not None
        assert inv.is_video_kleinunternehmer is True
        item = inv.items[0]
        assert _q2(item.amount) == Decimal("119.00")
        assert _q2(item.net_amount) == Decimal("119.00")
        assert _q2(item.vat_amount) == Decimal("0.00")
        assert _q2(item.vat_rate) == Decimal("0.00")

    _assert_common_endpoints(client, case["person_id"], case["seq"])


def test_case_7_gemischte_rechnung_tandem_und_video_ku(seeded_app):
    app = seeded_app["app"]
    client = seeded_app["client"]
    Invoice = seeded_app["models"]["Invoice"]
    case = seeded_app["ids"]["case7"]

    with app.app_context():
        inv = Invoice.query.get(case["invoice_id"])
        assert inv is not None
        assert inv.is_tandem_kleinunternehmer is True
        assert inv.is_video_kleinunternehmer is True
        assert len(inv.items) == 2

        td_item = next(i for i in inv.items if "TD" in (i.description or ""))
        video_item = next(i for i in inv.items if "Video" in (i.description or ""))

        assert _q2(td_item.amount) == Decimal("119.00")
        assert _q2(td_item.net_amount) == Decimal("119.00")
        assert _q2(td_item.vat_amount) == Decimal("0.00")
        assert _q2(td_item.vat_rate) == Decimal("0.00")

        assert _q2(video_item.amount) == Decimal("119.00")
        assert _q2(video_item.net_amount) == Decimal("119.00")
        assert _q2(video_item.vat_amount) == Decimal("0.00")
        assert _q2(video_item.vat_rate) == Decimal("0.00")

    _assert_common_endpoints(client, case["person_id"], case["seq"])


def test_preview_initial_ku_from_video_master_data_shows_0_percent(seeded_app):
    client = seeded_app["client"]
    case = seeded_app["ids"]["case6"]

    r = client.get(f"/billing/person/{case['person_id']}")
    assert r.status_code == 200
    html = r.data.decode("utf-8", errors="ignore")

    assert 'id="invoice_is_video_kleinunternehmer"' in html
    assert 'option value="true" selected' in html
    assert 'js-ku-position-note is-visible' in html
    assert '>0.00<' in html
    assert 'data-is-video="1"' in html


def test_invoice_detail_contains_live_ku_recalc_hooks_for_video(seeded_app):
    client = seeded_app["client"]
    case = seeded_app["ids"]["case8"]

    r = client.get(f"/billing/invoice/{case['seq']}")
    assert r.status_code == 200
    html = r.data.decode("utf-8", errors="ignore")

    assert 'id="invoiceIsVideoKleinunternehmer"' in html
    assert 'function recalculateInvoiceKuView()' in html
    assert 'function bindInvoiceKuToggleRecalc()' in html


def test_case_8_nachtraegliche_video_ku_aenderung_bei_unversandter_rechnung(seeded_app):
    app = seeded_app["app"]
    client = seeded_app["client"]
    Invoice = seeded_app["models"]["Invoice"]
    case = seeded_app["ids"]["case8"]

    with app.app_context():
        inv_before = Invoice.query.get(case["invoice_id"])
        assert inv_before is not None
        assert inv_before.email_sent_ok is False
        assert inv_before.is_video_kleinunternehmer is False
        item_before = inv_before.items[0]
        assert _q2(item_before.vat_rate) == Decimal("19.00")
        assert _q2(item_before.vat_amount) == Decimal("19.00")

    r = client.post(
        f"/billing/invoice/{case['invoice_id']}/set_tandem_kleinunternehmer",
        data={
            "invoice_is_tandem_kleinunternehmer": "false",
            "invoice_is_video_kleinunternehmer": "true",
        },
        follow_redirects=True,
    )
    assert r.status_code == 200

    with app.app_context():
        inv_after = Invoice.query.get(case["invoice_id"])
        assert inv_after is not None
        assert inv_after.is_video_kleinunternehmer is True
        item_after = inv_after.items[0]
        assert _q2(item_after.amount) == Decimal("119.00")
        assert _q2(item_after.net_amount) == Decimal("119.00")
        assert _q2(item_after.vat_amount) == Decimal("0.00")
        assert _q2(item_after.vat_rate) == Decimal("0.00")

    _assert_common_endpoints(client, case["person_id"], case["seq"])


def test_case_9_mixed_credit_ku_and_7pct_footer_matches_positions_and_exports(seeded_app):
    app = seeded_app["app"]
    client = seeded_app["client"]
    Invoice = seeded_app["models"]["Invoice"]
    case = seeded_app["ids"]["case9"]

    with app.app_context():
        inv = Invoice.query.get(case["invoice_id"])
        assert inv is not None
        assert inv.is_tandem_kleinunternehmer is True
        assert len(inv.items) == 2

        td_item = next(i for i in inv.items if "TD" in (i.description or ""))
        normal_item = next(i for i in inv.items if "Gast-7" in (i.description or ""))

        assert _q2(td_item.amount) == Decimal("-75.00")
        assert _q2(td_item.net_amount) == Decimal("-75.00")
        assert _q2(td_item.vat_amount) == Decimal("0.00")
        assert _q2(td_item.vat_rate) == Decimal("0.00")

        assert _q2(normal_item.amount) == Decimal("35.00")
        assert _q2(normal_item.net_amount) == Decimal("32.71")
        assert _q2(normal_item.vat_amount) == Decimal("2.29")
        assert _q2(normal_item.vat_rate) == Decimal("7.00")

    r_detail = client.get(f"/billing/invoice/{case['seq']}")
    assert r_detail.status_code == 200
    html = r_detail.data.decode("utf-8", errors="ignore")

    jump_net_match = re.search(r'id="invoiceJumpSumNet">\s*([\-0-9\.,]+)', html)
    jump_vat_match = re.search(r'id="invoiceJumpSumVat">\s*([\-0-9\.,]+)', html)
    summary_net_match = re.search(r'id="invoiceSummaryNet">\s*([\-0-9\.,]+)', html)
    summary_vat_match = re.search(r'id="invoiceSummaryVat">\s*([\-0-9\.,]+)', html)

    assert jump_net_match and jump_net_match.group(1) == "-42,29"
    assert jump_vat_match and jump_vat_match.group(1) == "2,29"
    assert summary_net_match and summary_net_match.group(1) == "-42,29"
    assert summary_vat_match and summary_vat_match.group(1) == "2,29"

    # JS-Recalc-Basis: reine Sprungrechnung -> fixer Anteil muss 0 sein (keine Doppelzählung)
    fixed_net_match = re.search(r'const fixedNet = parseDataNumber\("([^\"]+)"\)', html)
    fixed_vat_match = re.search(r'const fixedVat = parseDataNumber\("([^\"]+)"\)', html)
    assert fixed_net_match is not None
    assert fixed_vat_match is not None
    assert _q2(fixed_net_match.group(1)) == Decimal("0.00")
    assert _q2(fixed_vat_match.group(1)) == Decimal("0.00")

    r_csv = client.get(f"/billing/invoices/export/csv?person_id={case['person_id']}")
    assert r_csv.status_code == 200
    csv_text = r_csv.data.decode("utf-8-sig", errors="ignore")
    assert '"7009"' in csv_text
    assert '"-42,29"' in csv_text
    assert '"2,29"' in csv_text
    assert '"-40,00"' in csv_text

    openpyxl = pytest.importorskip("openpyxl")
    r_xlsx = client.get(f"/billing/invoices/export/xlsx?person_id={case['person_id']}")
    assert r_xlsx.status_code == 200

    wb = openpyxl.load_workbook(io.BytesIO(r_xlsx.data), data_only=True)
    ws = wb.active
    row_found = False
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] == 7009:
            row_found = True
            assert _q2(row[3]) == Decimal("-42.29")
            assert _q2(row[4]) == Decimal("2.29")
            assert _q2(row[5]) == Decimal("-40.00")
            break
    assert row_found, "Rechnung 7009 nicht im XLSX-Export gefunden"

    _assert_common_endpoints(client, case["person_id"], case["seq"])
