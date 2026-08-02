from app.helpers.status_code import is_ku_credit_payout_applicable_status, normalize_status_code


def test_td_vereins_schirm_status_is_normalized_and_treated_as_applicable():
    assert normalize_status_code("Td-Vereins-Schirm") == "TD-Vereins-Schirm"
    assert is_ku_credit_payout_applicable_status("Td-Vereins-Schirm") is True
