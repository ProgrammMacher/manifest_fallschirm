from __future__ import annotations

from app import db


class SepaConfig(db.Model):
    __tablename__ = "sepa_config"

    id = db.Column(db.Integer, primary_key=True)
    creditor_id = db.Column(db.String(35), nullable=False, default="", server_default="")
    creditor_name = db.Column(db.String(140), nullable=False, default="", server_default="")
    creditor_iban = db.Column(db.String(34), nullable=False, default="", server_default="")
    creditor_bic = db.Column(db.String(11), nullable=False, default="", server_default="")
    creditor_country = db.Column(db.String(2), nullable=False, default="DE", server_default="DE")
    pain_version = db.Column(db.String(30), nullable=False, default="pain.008.001.02", server_default="pain.008.001.02")
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.now(), server_default=db.func.now())
    updated_at = db.Column(db.DateTime, nullable=False, default=db.func.now(), server_default=db.func.now())
