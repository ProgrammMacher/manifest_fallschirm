import json
from datetime import datetime

from app import db


class EmailSendLog(db.Model):
    """
    Protokoll jedes E-Mail-/Newsletter-Versands.
    Analog zu Invoice-Audit, aber für freie E-Mails.
    """
    __tablename__ = "email_send_log"

    id = db.Column(db.Integer, primary_key=True)
    sent_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=db.func.now(),
    )
    subject = db.Column(db.String(500), nullable=True)
    body_preview = db.Column(db.Text, nullable=True)  # erste 500 Zeichen
    recipient_count = db.Column(db.Integer, nullable=True, default=0)
    recipient_list = db.Column(db.Text, nullable=True)  # JSON-Array von E-Mail-Adressen
    mail_type = db.Column(
        db.String(20), nullable=True, default="email"
    )  # "email" | "newsletter"
    status = db.Column(
        db.String(20), nullable=True, default="ok"
    )  # "ok" | "partial" | "error"
    error_detail = db.Column(db.Text, nullable=True)

    def get_recipients(self) -> list[str]:
        try:
            return json.loads(self.recipient_list or "[]")
        except Exception:
            return []

    def set_recipients(self, recipients: list[str]) -> None:
        self.recipient_list = json.dumps(recipients)
        self.recipient_count = len(recipients)

    def __repr__(self) -> str:
        return (
            f"<EmailSendLog id={self.id} "
            f"type={self.mail_type} "
            f"recipients={self.recipient_count} "
            f"status={self.status}>"
        )
