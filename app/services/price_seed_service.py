# app/services/price_seed_service.py
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional, Dict, Tuple

from app import db
from app.models.billing_config import BillingConfig, BillingPrice, BillingPricePeriod
from app.models.status_definition import StatusDefinition
from app.helpers.status_code import normalize_status_code


class PriceSeedService:
    """
    Stabiler Seed:
    - kanonisiert Statuscodes
    - idempotent (ergänzt fehlende Zeilen)
    - optional overwrite (überschreibt bestehende)
    """

    VALID_HEIGHTS = (1500, 3000, 4000)

    @staticmethod
    def _get_or_create_period(
        *, period_name: str, valid_from: date, valid_to: Optional[date],
        orga_fee: Optional[Decimal], is_homebase_default: bool
    ) -> BillingPricePeriod:
        period = (
            BillingPricePeriod.query
            .filter_by(name=period_name, valid_from=valid_from, valid_to=valid_to)
            .first()
        )
        if not period:
            period = BillingPricePeriod(
                name=period_name,
                valid_from=valid_from,
                valid_to=valid_to,
                orga_fee_eur=orga_fee,
                is_homebase_default=is_homebase_default,
            )
            db.session.add(period)
            db.session.flush()
        else:
            # optional: Orga Fee nachziehen
            if orga_fee is not None and period.orga_fee_eur is None:
                period.orga_fee_eur = orga_fee
        return period

    @staticmethod
    def seed_prices_for_period(
        *,
        period_name: str,
        valid_from: date,
        valid_to: Optional[date] = None,
        orga_fee: Optional[Decimal] = None,
        is_homebase_default: bool = False,
        overwrite: bool = False,
    ) -> Dict:
        """
        Legt/ergänzt BillingPrice-Zeilen für eine Preisperiode an.
        - kanonische Statuscodes
        - ergänzt fehlende Kombinationen
        - overwrite=True überschreibt bestehende Preise
        """
        period = PriceSeedService._get_or_create_period(
            period_name=period_name,
            valid_from=valid_from,
            valid_to=valid_to,
            orga_fee=orga_fee,
            is_homebase_default=is_homebase_default,
        )

        # ✅ Seed-Daten (könnt ihr später aus einer externen Vorlage/JSON laden)
        # Wichtig: Wir dürfen hier UPPERCASE/Underscore stehen lassen – wir normalisieren danach.
        PREISE_RAW = {
            "VEREIN": {1500: 22, 3000: 32, 4000: 35},
            "PARTNER_VEREIN": {1500: 22, 3000: 32, 4000: 35},
            "GAST": {1500: 25, 3000: 35, 4000: 38},
            "SCHUELER": {1500: 59, 3000: 79, 4000: 85},
            "SCHUELER_EK1": {1500: 0, 3000: 0, 4000: 0},
            "SCHUELER_EK2": {1500: 0, 3000: 0, 4000: 0},
            "SCHUELER_GK6": {1500: 0, 3000: 0, 4000: 0},
            "LEHRER": {1500: 0, 3000: 0, 4000: 0},
            "TD": {1500: -75, 3000: -75, 4000: -75},
            "TD_VEREINS_SCHIRM": {1500: -50, 3000: -50, 4000: -50},
            "VIDEO": {1500: -35, 3000: -35, 4000: -35},
            "G_TD": {1500: 220, 3000: 220, 4000: 220},
            "G_TD_VIDEO": {1500: 310, 3000: 310, 4000: 310},
            "AUFFUELLER_VEREIN": {1500: 22, 3000: 22, 4000: 25},
            "AUFFUELLER_GAST": {1500: 25, 3000: 25, 4000: 28},
            "AUFFUELLER_PARTNER_VEREIN": {1500: 22, 3000: 22, 4000: 25},
            "MITFLIEGER": {1500: 50, 3000: 50, 4000: 50},
        }

        # ✅ existierende Preise laden
        existing = (
            BillingPrice.query
            .filter_by(period_id=period.id)
            .all()
        )
        existing_map: Dict[Tuple[str, int], BillingPrice] = {
            (normalize_status_code(p.status_code), int(p.height_m)): p for p in existing
        }

        created = 0
        updated = 0
        with db.session.begin_nested():
            for raw_code, heights in PREISE_RAW.items():
                status_code = normalize_status_code(raw_code)  # ✅ canonical
                for h in PriceSeedService.VALID_HEIGHTS:
                    if h not in heights:
                        continue
                    key = (status_code, int(h))
                    price_dec = Decimal(str(heights[h]))

                    if key in existing_map:
                        if overwrite:
                            existing_map[key].price_eur = price_dec
                            updated += 1
                    else:
                        db.session.add(
                            BillingPrice(
                                period_id=period.id,
                                status_code=status_code,
                                height_m=int(h),
                                price_eur=price_dec,
                            )
                        )
                        created += 1

        db.session.commit()
        return {
            "period": period,
            "prices_created": created,
            "prices_updated": updated,
            "message": "Seed abgeschlossen (idempotent).",
        }

    # ---------------------------------------------------------
    # Reset: alle Preise eines Flugplatzes in einer Periode löschen
    # ---------------------------------------------------------
    @staticmethod
    def reset_prices_for_period(*, period_id: int) -> int:
        q = BillingPrice.query.filter_by(period_id=period_id)
        count = q.count()
        with db.session.begin_nested():
            q.delete(synchronize_session=False)
        db.session.commit()
        return count

    # ---------------------------------------------------------
    # Clone: Preise von einer Periode in eine andere übernehmen
    # ---------------------------------------------------------
    @staticmethod
    def clone_prices(
        *,
        source_period_id: int,
        target_period_id: int,
        overwrite: bool = False,
    ) -> Dict:
        src_prices = (
            BillingPrice.query
            .filter_by(period_id=source_period_id)
            .all()
        )

        existing = (
            BillingPrice.query
            .filter_by(period_id=target_period_id)
            .all()
        )
        existing_map = {(normalize_status_code(p.status_code), int(p.height_m)): p for p in existing}

        created = 0
        updated = 0
        with db.session.begin_nested():
            for p in src_prices:
                key = (normalize_status_code(p.status_code), int(p.height_m))
                if key in existing_map:
                    if overwrite:
                        existing_map[key].price_eur = p.price_eur
                        updated += 1
                else:
                    db.session.add(
                        BillingPrice(
                            period_id=target_period_id,
                            status_code=p.status_code,
                            height_m=int(p.height_m),
                            price_eur=p.price_eur,
                        )
                    )
                    created += 1
        db.session.commit()
        return {"created": created, "updated": updated}