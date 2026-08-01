from flask import Flask, make_response

from app.routes.billing import _build_invoice_list_redirect_response, _set_no_store_headers


def test_set_no_store_headers_adds_cache_control_and_pragma():
    app = Flask(__name__)
    with app.test_request_context():
        response = make_response("ok")

        _set_no_store_headers(response)

        cache_control = response.headers.get("Cache-Control", "")
        assert "no-store" in cache_control.lower()
        assert response.headers.get("Pragma") == "no-cache"


def test_build_invoice_list_redirect_response_includes_download_query_param():
    app = Flask(__name__)
    with app.test_request_context():
        response = _build_invoice_list_redirect_response(export_id=42)

        assert response.status_code == 302
        assert "sepa_download_export_id=42" in response.location
