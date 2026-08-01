from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from xml.sax.saxutils import escape as xml_escape

from app.models.billing_config import BillingConfig
from app.models.sepa_config import SepaConfig
from app.services.payment_data_service import build_payment_context


def _xml_text(value: object) -> str:
    return xml_escape(str(value or ""))


def normalize_iban(value: object) -> str:
    text = str(value or "")
    return "".join(ch for ch in text if not ch.isspace())


def build_pain_008_xml(
    export_code: str,
    created_at: datetime,
    rows: list[dict],
    sepa_config: SepaConfig,
    collection_date: date,
    billing_config: BillingConfig | None = None,
) -> bytes:
    if not sepa_config:
        raise ValueError("SEPA-Konfiguration fehlt")

    if not rows:
        raise ValueError("Keine SEPA-Transaktionen vorhanden")

    total_amount = sum(Decimal(str(r.get("amount", "0.00"))) for r in rows)
    total_amount_str = f"{total_amount:.2f}"
    transaction_count = len(rows)

    creditor_name = (getattr(billing_config, "company_name", None) or getattr(sepa_config, "creditor_name", None) or "").strip()
    creditor_iban = normalize_iban(getattr(billing_config, "iban", None) or getattr(sepa_config, "creditor_iban", None) or "")
    creditor_bic = (getattr(billing_config, "bic", None) or getattr(sepa_config, "creditor_bic", None) or "").strip()
    creditor_id = (getattr(billing_config, "creditor_id", None) or getattr(sepa_config, "creditor_id", None) or "").strip()
    pain_version = (getattr(billing_config, "pain_version", None) or getattr(sepa_config, "pain_version", None) or "pain.008.001.02").strip() or "pain.008.001.02"

    if not creditor_id:
        raise ValueError("Für den SEPA-Export ist keine Gläubiger-ID gepflegt. Bitte unter Rechnungssteller → Konfiguration eine Creditor-ID eintragen.")

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<Document xmlns="urn:iso:std:iso:20022:tech:xsd:{pain_version}">',
        "  <CstmrDrctDbtInitn>",
        "    <GrpHdr>",
        f"      <MsgId>{_xml_text(export_code)}</MsgId>",
        f"      <CreDtTm>{created_at.strftime('%Y-%m-%dT%H:%M:%S')}</CreDtTm>",
        f"      <NbOfTxs>{transaction_count}</NbOfTxs>",
        f"      <CtrlSum>{total_amount_str}</CtrlSum>",
        "      <InitgPty>",
        f"        <Nm>{_xml_text(creditor_name)}</Nm>",
        "      </InitgPty>",
        "    </GrpHdr>",
        "    <PmtInf>",
        f"      <PmtInfId>{_xml_text(export_code)}</PmtInfId>",
        "      <PmtMtd>DD</PmtMtd>",
        "      <BtchBookg>false</BtchBookg>",
        f"      <NbOfTxs>{transaction_count}</NbOfTxs>",
        f"      <CtrlSum>{total_amount_str}</CtrlSum>",
        "      <PmtTpInf>",
        "        <SvcLvl>",
        "          <Cd>SEPA</Cd>",
        "        </SvcLvl>",
        "        <LclInstrm>",
        "          <Cd>CORE</Cd>",
        "        </LclInstrm>",
        "        <SeqTp>FRST</SeqTp>",
        "      </PmtTpInf>",
        f"      <ReqdColltnDt>{collection_date.strftime('%Y-%m-%d')}</ReqdColltnDt>",
        "      <Cdtr>",
        f"        <Nm>{_xml_text(creditor_name)}</Nm>",
        "      </Cdtr>",
        "      <CdtrAcct>",
        "        <Id>",
        f"          <IBAN>{_xml_text(creditor_iban)}</IBAN>",
        "        </Id>",
        "      </CdtrAcct>",
        "      <CdtrSchmeId>",
        "        <Id>",
        "          <PrvtId>",
        "            <Othr>",
        f"              <Id>{_xml_text(creditor_id)}</Id>",
        "              <SchmeNm>",
        "                <Prtry>SEPA</Prtry>",
        "              </SchmeNm>",
        "            </Othr>",
        "          </PrvtId>",
        "        </Id>",
        "      </CdtrSchmeId>",
        "      <CdtrAgt>",
        "        <FinInstnId>",
        f"          <BIC>{_xml_text(creditor_bic)}</BIC>",
        "        </FinInstnId>",
        "      </CdtrAgt>",
        "      <ChrgBr>SLEV</ChrgBr>",
    ]

    for row in rows:
        sequence_type = (row.get("sequence_type") or "FRST").upper()
        remittance_information = (row.get("remittance_information") or row.get("invoice_number") or "").strip()
        lines.extend([
            "      <DrctDbtTxInf>",
            "        <PmtId>",
            f"          <InstrId>{_xml_text(row.get('invoice_number') or row.get('invoice_id') or '')}</InstrId>",
            f"          <EndToEndId>{_xml_text(row.get('end_to_end_id') or row.get('invoice_number') or row.get('invoice_id') or '')}</EndToEndId>",
            "        </PmtId>",
            f"        <InstdAmt Ccy=\"EUR\">{Decimal(str(row.get('amount', '0.00'))):.2f}</InstdAmt>",
            "        <DrctDbtTx>",
            "          <MndtRltdInf>",
            f"            <MndtId>{_xml_text(row.get('mandate_reference') or '')}</MndtId>",
            f"            <DtOfSgntr>{row.get('mandate_date').strftime('%Y-%m-%d') if row.get('mandate_date') else ''}</DtOfSgntr>",
            "          </MndtRltdInf>",
            "        </DrctDbtTx>",
            "        <DbtrAgt>",
            "          <FinInstnId>",
            f"            <BIC>{_xml_text(row.get('bic') or '')}</BIC>",
            "          </FinInstnId>",
            "        </DbtrAgt>",
            "        <Dbtr>",
            f"          <Nm>{_xml_text(row.get('debtor_name') or row.get('person_name') or '')}</Nm>",
            "        </Dbtr>",
            "        <DbtrAcct>",
            "          <Id>",
            f"            <IBAN>{_xml_text(normalize_iban(row.get('iban') or ''))}</IBAN>",
            "          </Id>",
            "        </DbtrAcct>",
            "        <RmtInf>",
            f"          <Ustrd>{_xml_text(remittance_information)}</Ustrd>",
            "        </RmtInf>",
            "      </DrctDbtTxInf>",
        ])

    lines.extend([
        "    </PmtInf>",
        "  </CstmrDrctDbtInitn>",
        "</Document>",
    ])
    return ("\n".join(lines) + "\n").encode("utf-8")
