"""Allowlisted, non-customer data for a brand-new installation only."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from app import db
from app.models.aircraft import Aircraft
from app.models.billing_config import (
    BillingOrgaConfig,
    BillingOrgaRule,
    BillingPrice,
    BillingPricePeriod,
)
from app.models.flugplatz import Flugplatz
from app.models.status_definition import StatusDefinition


_SEED_PERIOD_NAME = "Standardpreisliste ab 01.08.2026"
_SEED_VALID_FROM = date(2026, 8, 1)
_SEED_VALID_FROM_DATETIME = datetime(2026, 8, 1)

# This is an explicit allowlist. Never load seed content from the live database.
_AIRFIELDS = (
    {"id": 1, "name": "Dessau EDAD", "color": "#007bff", "is_home_airfield": True, "active": True},
    {"id": 2, "name": "Zerbst EDUZ", "color": "#007bff", "is_home_airfield": False, "active": False},
    {"id": 3, "name": "Mellenthin DE-0361", "color": "#007bff", "is_home_airfield": False, "active": False},
    {"id": 4, "name": "Merseburg EDAM", "color": "#007bff", "is_home_airfield": False, "active": False},
    {"id": 5, "name": "Roitzschjora EDAW", "color": "#007bff", "is_home_airfield": False, "active": False},
    {"id": 6, "name": "Magdeburg EDBM", "color": "#007bff", "is_home_airfield": False, "active": True},
)

_AIRCRAFT = (
    {
        "id": 1,
        "active": False,
        "type": "Cessna 182 Skylane",
        "registration": "D-EECH",
        "seats": 4,
        "default_height": 3000,
    },
    {
        "id": 2,
        "active": False,
        "type": "PC-6 Pilatus Porter",
        "registration": "D-FAXI",
        "seats": 10,
        "default_height": 4000,
    },
    {
        "id": 3,
        "active": False,
        "type": "AN-2",
        "registration": "D-FWJK",
        "seats": 12,
        "default_height": 3000,
    },
    {
        "id": 4,
        "active": False,
        "type": "C-208 Cessna Grand Caravan",
        "registration": "D-FALB",
        "seats": 18,
        "default_height": 4000,
    },
    {
        "id": 5,
        "active": False,
        "type": "AN-72",
        "registration": "ER-AFZ",
        "seats": 66,
        "default_height": 4000,
    },
    {
        "id": 6,
        "active": True,
        "type": "DHC-6 Twin Otter",
        "registration": "SE-GEE",
        "seats": 20,
        "default_height": 4000,
    },
    {
        "id": 7,
        "active": False,
        "type": "C-160 Tranall",
        "registration": "50+38",
        "seats": 64,
        "default_height": 4000,
    },
    {
        "id": 8,
        "active": False,
        "type": "C-182 Skylane Magdeburg",
        "registration": "D-EDMO",
        "seats": 4,
        "default_height": 3000,
    },
    {
        "id": 9,
        "active": False,
        "type": "AN-2",
        "registration": "D-FOJB",
        "seats": 12,
        "default_height": 3000,
    },
)

# code, label, sort order, VAT rate
_STATUS_DEFINITIONS = (
    ("Verein", "Vereinsmitglied", 10, "7.00"),
    ("Partner-Verein", "Partner-Verein", 15, "7.00"),
    ("Gast", "Fallschirmspringer Gast", 20, "7.00"),
    ("Lehrer", "Fallschirmsprunglehrer", 25, "0.00"),
    ("Schüler", "Sprungschüler Ticket", 30, "0.00"),
    ("Auffüller Partner-Verein", "Auffüller Partner-Verein", 31, "7.00"),
    ("Schüler Ek 1", "Sprungschüler Kurs 1", 31, "0.00"),
    ("Schüler Ek 2", "Sprungschüler Kurs 2", 32, "0.00"),
    ("Schüler GK 6", "Sprungschüler Kurs 6", 33, "0.00"),
    ("G-TD", "Tandemgast", 40, "19.00"),
    ("AFF-LEHRER", "AFF-Lehrer", 41, "19.00"),
    ("G-TD-Video", "Tandemgast (Video)", 50, "19.00"),
    ("TD", "Tandemmaster", 60, "19.00"),
    ("SCHUELER-AFF-2", "Schüler-AFF-2-Lehrer", 61, "19.00"),
    ("TD-Vereins-Schirm", "Tandemmaster (Vereins-Schirm)", 61, "19.00"),
    ("SCHUELER-AFF-1", "Schüler-AFF-1-Lehrer", 62, "19.00"),
    ("Video", "Videomann", 70, "19.00"),
    ("Mitflieger", "Mitflieger", 80, "19.00"),
    ("Auffüller Verein", "Auffüller Verein", 85, "7.00"),
    ("Auffüller Gast", "Auffüller Gast", 86, "7.00"),
    ("Miete Gast", "Miete Fallschirm Gast", 100, "7.00"),
    ("Miete Tandemmaster", "Miete Fallschirm Tandemmaster", 100, "19.00"),
    ("Miete Verein", "Miete Fallschirm Verein", 100, "7.00"),
    ("Orga", "Organisationspauschale", 100, "7.00"),
)

# code, height in metres, amount, payout basis
_PRICES = (
    ("Aff-Lehrer", 1500, "0.00", "net"),
    ("Aff-Lehrer", 3000, "-53.55", "net"),
    ("Aff-Lehrer", 4000, "-53.55", "net"),
    ("Auffüller Gast", 1500, "25.00", "gross"),
    ("Auffüller Gast", 3000, "25.00", "gross"),
    ("Auffüller Gast", 4000, "28.00", "gross"),
    ("Auffüller Partner-Verein", 1500, "22.00", "gross"),
    ("Auffüller Partner-Verein", 3000, "22.00", "gross"),
    ("Auffüller Partner-Verein", 4000, "25.00", "gross"),
    ("Auffüller Verein", 1500, "22.00", "gross"),
    ("Auffüller Verein", 3000, "22.00", "gross"),
    ("Auffüller Verein", 4000, "25.00", "gross"),
    ("G-TD", 1500, "220.00", "gross"),
    ("G-TD", 3000, "220.00", "gross"),
    ("G-TD", 4000, "220.00", "gross"),
    ("G-TD-Video", 1500, "310.00", "gross"),
    ("G-TD-Video", 3000, "310.00", "gross"),
    ("G-TD-Video", 4000, "310.00", "gross"),
    ("Gast", 1500, "25.00", "gross"),
    ("Gast", 3000, "35.00", "gross"),
    ("Gast", 4000, "39.00", "gross"),
    ("Lehrer", 1500, "0.00", "gross"),
    ("Lehrer", 3000, "0.00", "gross"),
    ("Lehrer", 4000, "0.00", "gross"),
    ("Mitflieger", 1500, "60.00", "gross"),
    ("Mitflieger", 3000, "60.00", "gross"),
    ("Mitflieger", 4000, "60.00", "gross"),
    ("Orga", 0, "0.00", "gross"),
    ("Partner-Verein", 1500, "22.00", "gross"),
    ("Partner-Verein", 3000, "32.00", "gross"),
    ("Partner-Verein", 4000, "37.00", "gross"),
    ("Schueler-Aff-1", 1500, "0.00", "gross"),
    ("Schueler-Aff-1", 3000, "130.00", "gross"),
    ("Schueler-Aff-1", 4000, "130.00", "gross"),
    ("Schueler-Aff-2", 1500, "0.00", "gross"),
    ("Schueler-Aff-2", 3000, "210.00", "gross"),
    ("Schueler-Aff-2", 4000, "210.00", "gross"),
    ("Schueler_Ek1", 1500, "0.00", "gross"),
    ("Schueler_Ek1", 3000, "0.00", "gross"),
    ("Schueler_Ek1", 4000, "0.00", "gross"),
    ("Schueler_Ek2", 1500, "0.00", "gross"),
    ("Schueler_Ek2", 3000, "0.00", "gross"),
    ("Schueler_Ek2", 4000, "0.00", "gross"),
    ("Schueler_Gk6", 1500, "0.00", "gross"),
    ("Schueler_Gk6", 3000, "0.00", "gross"),
    ("Schueler_Gk6", 4000, "0.00", "gross"),
    ("Schüler", 1500, "59.00", "gross"),
    ("Schüler", 3000, "79.00", "gross"),
    ("Schüler", 4000, "89.00", "gross"),
    ("Schüler Ek 1", 1500, "0.00", "gross"),
    ("Schüler Ek 1", 3000, "0.00", "gross"),
    ("Schüler Ek 1", 4000, "0.00", "gross"),
    ("Schüler Ek 2", 1500, "0.00", "gross"),
    ("Schüler Ek 2", 3000, "0.00", "gross"),
    ("Schüler Ek 2", 4000, "0.00", "gross"),
    ("Schüler GK 6", 1500, "0.00", "gross"),
    ("Schüler GK 6", 3000, "0.00", "gross"),
    ("Schüler GK 6", 4000, "0.00", "gross"),
    ("TD", 1500, "-89.25", "net"),
    ("TD", 3000, "-89.25", "net"),
    ("TD", 4000, "-89.25", "net"),
    ("TD-Vereins-Schirm", 1500, "-59.25", "net"),
    ("TD-Vereins-Schirm", 3000, "-59.25", "net"),
    ("TD-Vereins-Schirm", 4000, "-59.25", "net"),
    ("Verein", 1500, "22.00", "gross"),
    ("Verein", 3000, "32.00", "gross"),
    ("Verein", 4000, "37.00", "gross"),
    ("Video", 1500, "-41.65", "net"),
    ("Video", 3000, "-41.65", "net"),
    ("Video", 4000, "-41.65", "net"),
)

_ORGARULE_STATUSES = (
    "Aff-Lehrer", "Auffüller Gast", "Auffüller Partner-Verein", "Auffüller Verein",
    "G-TD", "G-TD-Video", "Gast", "Lehrer", "Mitflieger", "Partner-Verein",
    "Schueler-Aff-1", "Schueler-Aff-2", "Schüler", "Schüler Ek 1", "Schüler Ek 2",
    "Schüler GK 6", "TD", "TD-Vereins-Schirm", "Verein", "Video",
)


def seed_neutral_installation() -> bool:
    """Create allowlisted starter masters; never copy from an existing DB."""
    if (
        Flugplatz.query.first()
        or Aircraft.query.first()
        or BillingPricePeriod.query.first()
        or BillingPrice.query.first()
    ):
        return False

    try:
        db.session.add_all(Flugplatz(**row) for row in _AIRFIELDS)
        db.session.add_all(Aircraft(**row) for row in _AIRCRAFT)

        now = datetime.utcnow()
        active_codes = {
            row.code
            for row in StatusDefinition.query.filter_by(is_active=True).all()
            if row.valid_from <= now and (row.valid_to is None or row.valid_to >= now)
        }
        db.session.add_all(
            StatusDefinition(
                id=status_id,
                code=code,
                label=label,
                sort_order=sort_order,
                vat_rate=Decimal(vat_rate),
                valid_from=_SEED_VALID_FROM_DATETIME,
                is_active=True,
            )
            for status_id, (code, label, sort_order, vat_rate) in enumerate(_STATUS_DEFINITIONS, start=1)
            if code not in active_codes
        )

        period = BillingPricePeriod(
            id=1,
            name=_SEED_PERIOD_NAME,
            valid_from=_SEED_VALID_FROM,
            valid_to=None,
            orga_fee_eur=Decimal("0.00"),
            orga_fee_mode="period",
            orga_fee_vat_strategy="max_status",
            is_homebase_default=False,
        )
        db.session.add(period)
        db.session.flush()

        db.session.add_all(
            BillingPrice(
                id=price_id,
                period_id=period.id,
                status_code=status_code,
                height_m=height_m,
                price_eur=Decimal(price_eur),
                ku_credit_payout_basis=payout_basis,
            )
            for price_id, (status_code, height_m, price_eur, payout_basis) in enumerate(_PRICES, start=1)
        )
        db.session.add(
            BillingOrgaConfig(
                id=1,
                period_id=period.id,
                orga_fee_eur=Decimal("0.00"),
                orga_fee_mode="period",
                orga_fee_vat_strategy="max_status",
            )
        )
        db.session.add_all(
            BillingOrgaRule(id=rule_id, period_id=period.id, status_code=code, apply_orga=False)
            for rule_id, code in enumerate(_ORGARULE_STATUSES, start=1)
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return True