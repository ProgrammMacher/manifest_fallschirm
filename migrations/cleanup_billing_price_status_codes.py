import argparse
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.getcwd())

from app import create_app, db
from app.helpers.status_code import normalize_status_code
from app.models.billing_config import BillingPrice


def build_report(rows):
    groups = defaultdict(list)
    for row in rows:
        canon = normalize_status_code(getattr(row, "status_code", "") or "")
        if not canon:
            continue
        groups[(row.period_id, canon, int(row.height_m))].append(row)

    kept = []
    removed = []
    conflicts = []

    for (period_id, canon, height), items in sorted(groups.items()):
        literals = sorted({getattr(it, "status_code", "") or "" for it in items})
        if len(literals) <= 1:
            continue

        price_values = sorted({str(getattr(it, "price_eur", "") or "") for it in items})
        basis_values = sorted({str((getattr(it, "ku_credit_payout_basis", "") or "gross")).strip().lower() or "gross" for it in items})
        conflict = len(price_values) > 1 or len(basis_values) > 1

        preferred = None
        for it in items:
            if getattr(it, "status_code", "") == canon:
                preferred = it
                break
        if preferred is None:
            preferred = max(items, key=lambda it: it.id)

        if conflict:
            conflicts.append({
                "period_id": period_id,
                "canon": canon,
                "height": height,
                "literals": literals,
                "price_values": price_values,
                "basis_values": basis_values,
                "preferred_id": preferred.id if preferred else None,
            })
            continue

        for it in items:
            if it is preferred:
                continue
            removed.append({
                "period_id": period_id,
                "canon": canon,
                "height": height,
                "row_id": it.id,
                "literal": getattr(it, "status_code", "") or "",
                "price": str(getattr(it, "price_eur", "") or ""),
                "basis": str((getattr(it, "ku_credit_payout_basis", "") or "gross")).strip().lower() or "gross",
            })
        kept.append({
            "period_id": period_id,
            "canon": canon,
            "height": height,
            "row_id": preferred.id,
            "literal": getattr(preferred, "status_code", "") or "",
            "price": str(getattr(preferred, "price_eur", "") or ""),
            "basis": str((getattr(preferred, "ku_credit_payout_basis", "") or "gross")).strip().lower() or "gross",
        })

    return kept, removed, conflicts


def run_cleanup(dry_run: bool, report_path: Path | None = None):
    app = create_app()
    with app.app_context():
        rows = BillingPrice.query.order_by(BillingPrice.period_id.asc(), BillingPrice.height_m.asc(), BillingPrice.id.asc()).all()
        kept, removed, conflicts = build_report(rows)

        print(f"Analysierte Zeilen: {len(rows)}")
        print(f"Auto-bereinigt: {len(kept)} Gruppen")
        print(f"Entfernte Zeilen: {len(removed)}")
        print(f"Konflikte: {len(conflicts)}")

        if conflicts:
            print("Konflikte:")
            for c in conflicts:
                print(f"- Periode {c['period_id']} / {c['canon']} / Höhe {c['height']} m -> Literals={c['literals']} Preise={c['price_values']} Basis={c['basis_values']}")

        if dry_run:
            print("Dry-Run: keine Änderungen an der Datenbank.")
            return kept, removed, conflicts

        for item in removed:
            row = BillingPrice.query.get(item["row_id"])
            if row is not None:
                db.session.delete(row)
        db.session.commit()
        print("Änderungen gespeichert.")
        return kept, removed, conflicts


def main():
    parser = argparse.ArgumentParser(description="Konsolidiere historische Statuscodes in billing_price")
    parser.add_argument("--apply", action="store_true", help="Änderungen wirklich in die Datenbank schreiben")
    parser.add_argument("--report", type=str, default="Notizen/billing_price_status_cleanup_report.md", help="Pfad zur Markdown-Ausgabe")
    args = parser.parse_args()

    report_path = Path(args.report)
    dry_run = not args.apply
    kept, removed, conflicts = run_cleanup(dry_run=dry_run, report_path=report_path)

    lines = []
    lines.append("# billing_price Statuscode-Bereinigung")
    lines.append("")
    lines.append("## Zusammenfassung")
    lines.append(f"- Auto-bereinigt: {len(kept)} Gruppen")
    lines.append(f"- Entfernte Zeilen: {len(removed)}")
    lines.append(f"- Konflikte (ohne automatische Überschreibung): {len(conflicts)}")
    lines.append("")
    lines.append("## Konflikte")
    for c in conflicts:
        lines.append(f"- Periode {c['period_id']} / {c['canon']} / Höhe {c['height']} m -> Literals={c['literals']} Preise={c['price_values']} Basis={c['basis_values']}")
    lines.append("")
    lines.append("## Automatisch bereinigte Gruppen")
    for item in kept:
        lines.append(f"- Periode {item['period_id']} / {item['canon']} / Höhe {item['height']} m -> beibehalten ID {item['row_id']} ({item['literal']}, Preis {item['price']}, Basis {item['basis']})")

    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"Bericht geschrieben: {report_path}")


if __name__ == "__main__":
    main()
