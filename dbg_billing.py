from app import create_app
from app.routes.billing import _build_invoice_list_context
app = create_app()
with app.app_context():
    res = _build_invoice_list_context(period="all", from_str="", to_str="", filters=None, delta_scope="all")
    rows = res.get("billable_rows", [])
    print(f"billable_rows count: {len(rows)}")
    for i, r in enumerate(rows):
        p = r.get("person")
        name = p.full_name if p else "Unknown"
        amount = r.get("amount")
        print(f"[{i}] {name}: {amount}")
