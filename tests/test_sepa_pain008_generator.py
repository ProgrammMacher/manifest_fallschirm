from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

from app.models.billing_config import BillingConfig
from app.models.sepa_config import SepaConfig
from app.services.payment_data_service import build_invoice_payment_purpose, build_payment_context
from app.services.sepa_export_service import build_pain_008_xml


def test_build_pain_008_xml_contains_required_pain_elements():
    config = SepaConfig(
        creditor_id="DE98ZZZ09999999999",
        creditor_name="Dessauer Fallschirmsportverein",
        creditor_iban="DE75512108001245126199",
        creditor_bic="DEUTDEFF500",
        creditor_country="DE",
        pain_version="pain.008.001.02",
    )

    rows = [
        {
            "invoice_id": 1,
            "invoice_number": "INV-1001",
            "amount": Decimal("60.00"),
            "person_name": "Max Mustermann",
            "iban": "DE75512108001245126199",
            "bic": "DEUTDEFF500",
            "mandate_reference": "MD-001",
            "mandate_date": date(2024, 1, 1),
            "sequence_type": "FRST",
            "remittance_information": "Rechnung INV-1001",
            "end_to_end_id": "ETO-1001",
            "debtor_name": "Max Mustermann",
            "debtor_country": "DE",
        }
    ]

    xml_bytes = build_pain_008_xml(
        export_code="2026-0001",
        created_at=datetime(2026, 8, 1, 10, 0, 0),
        rows=rows,
        sepa_config=config,
        collection_date=date(2026, 8, 10),
    )
    xml_text = xml_bytes.decode("utf-8")

    assert "<Document xmlns=\"urn:iso:std:iso:20022:tech:xsd:pain.008.001.02\"" in xml_text
    assert "<CstmrDrctDbtInitn>" in xml_text
    assert "<GrpHdr>" in xml_text
    assert "<PmtInf>" in xml_text
    assert "<DrctDbtTxInf>" in xml_text
    assert "<SeqTp>FRST</SeqTp>" in xml_text
    assert "<EndToEndId>ETO-1001</EndToEndId>" in xml_text
    assert "<MsgId>2026-0001</MsgId>" in xml_text
    assert "<CdtrSchmeId>" in xml_text
    assert "<Id>DE98ZZZ09999999999</Id>" in xml_text


def test_build_pain_008_xml_requires_creditor_id():
    config = SepaConfig(
        creditor_id="",
        creditor_name="Dessauer Fallschirmsportverein",
        creditor_iban="DE75512108001245126199",
        creditor_bic="DEUTDEFF500",
        creditor_country="DE",
        pain_version="pain.008.001.02",
    )

    rows = [
        {
            "invoice_id": 1,
            "invoice_number": "INV-1001",
            "amount": Decimal("60.00"),
            "person_name": "Max Mustermann",
            "iban": "DE85 8009 3574 0001 7163 60",
            "bic": "DEUTDEFF500",
            "mandate_reference": "MD-001",
            "mandate_date": date(2024, 1, 1),
            "sequence_type": "FRST",
            "remittance_information": "Rechnung INV-1001",
            "end_to_end_id": "ETO-1001",
            "debtor_name": "Max Mustermann",
            "debtor_country": "DE",
        }
    ]

    try:
        build_pain_008_xml(
            export_code="2026-0001",
            created_at=datetime(2026, 8, 1, 10, 0, 0),
            rows=rows,
            sepa_config=config,
            collection_date=date(2026, 8, 10),
        )
    except ValueError as exc:
        assert "Gläubiger-ID" in str(exc)
    else:
        raise AssertionError("Expected ValueError for missing creditor ID")


def test_build_pain_008_xml_uses_billing_config_for_creditor_fields():
    config = SepaConfig(
        creditor_id="DE98ZZZ09999999999",
        creditor_name="",
        creditor_iban="",
        creditor_bic="",
        creditor_country="DE",
        pain_version="pain.008.001.02",
    )
    billing_config = BillingConfig(
        company_name="Dessauer Fallschirmsportverein",
        iban="DE85 8009 3574 0001 7163 60",
        bic="DEUTDEFF500",
    )

    rows = [
        {
            "invoice_id": 1,
            "invoice_number": "INV-1001",
            "amount": Decimal("60.00"),
            "person_name": "Max Mustermann",
            "iban": "DE85 8009 3574 0001 7163 60",
            "bic": "DEUTDEFF500",
            "mandate_reference": "MD-001",
            "mandate_date": date(2024, 1, 1),
            "sequence_type": "FRST",
            "remittance_information": "Rechnung INV-1001",
            "end_to_end_id": "ETO-1001",
            "debtor_name": "Max Mustermann",
            "debtor_country": "DE",
        }
    ]

    xml_bytes = build_pain_008_xml(
        export_code="2026-0001",
        created_at=datetime(2026, 8, 1, 10, 0, 0),
        rows=rows,
        sepa_config=config,
        billing_config=billing_config,
        collection_date=date(2026, 8, 10),
    )
    xml_text = xml_bytes.decode("utf-8")

    assert xml_text.count("<Nm>Dessauer Fallschirmsportverein</Nm>") == 2
    assert xml_text.count("<IBAN>DE85800935740001716360</IBAN>") == 2
    assert "<BIC>DEUTDEFF500</BIC>" in xml_text


def test_payment_context_is_reused_for_qr_and_pain_008_remittance():
    invoice = SimpleNamespace(
        created_at=datetime(2026, 8, 1, 12, 0, 0),
        items=[],
        person=SimpleNamespace(full_name="Max Mustermann"),
        seq_number=7,
    )
    billing_config = BillingConfig(
        company_name="Dessauer Fallschirmsportverein",
        iban="DE75512108001245126199",
        bic="DEUTDEFF500",
    )

    purpose = build_invoice_payment_purpose(invoice, invoice_number=7)
    payment_context = build_payment_context(
        invoice=invoice,
        billing_config=billing_config,
        invoice_number=7,
        amount_eur=Decimal("60.00"),
    )

    assert payment_context["remittance_information"] == purpose
    assert "Dessauer Fallschirmsportverein" in payment_context["epc_payload"]
    assert purpose in payment_context["epc_payload"]
