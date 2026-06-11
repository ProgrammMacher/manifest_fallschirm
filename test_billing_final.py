from app import create_app; from app.routes.billing import _build_invoice_list_context; app = create_app(); ctx = None;
with app.app_context():
    ctx = _build_invoice_list_context(period="all", from_str="", to_str="", filters=None, delta_scope="all")
    print(f"sum_billable: {ctx['sum_billable']}")
    print(f"sum_open_invoices: {ctx['sum_open_invoices']}")
    print(f"delta: {ctx['delta']}")
    print(f"billable_rows count: {len(ctx['billable_rows'])}")
