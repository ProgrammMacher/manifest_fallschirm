# C:\manifest_fallschirm\app\models\flugplatz.py

from app import db
from datetime import datetime

class Flugplatz(db.Model):
    __tablename__ = "flugplatz"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    color = db.Column(db.String(20))

    # Heimatflugplatz
    is_home_airfield = db.Column(db.Boolean, default=False)

    # ✅ Aktiv/Inaktiv (UI-Auswahl, ohne Daten zu löschen) – analog zu Aircraft.active
    active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )

    # Softdelete-Felder (Archiv)
    deleted_at = db.Column(db.DateTime, nullable=True)
    deleted_reason = db.Column(db.String(255), nullable=True)

    # Beziehung zu Load
    loads = db.relationship(
        "Load",
        back_populates="airfield",
        lazy="selectin"
    )


    # ---------------------------------------------------------
    # Properties
    # ---------------------------------------------------------
    @property
    def is_archived(self):
        return self.deleted_at is not None

    @property
    def is_active(self):
        """
        ⚠️ Rückwärtskompatibel:
        Bisher bedeutete is_active: nicht archiviert.
        Das behalten wir so, um keine bestehende Logik zu brechen.
        """
        return self.deleted_at is None

    @property
    def is_selectable(self):
        """
        ✅ Neue, eindeutige Semantik für UI/Selektion:
        Flugplatz ist auswählbar, wenn:
        - nicht archiviert
        - und active == True
        """
        return (self.deleted_at is None) and bool(self.active)

    # ---------------------------------------------------------
    # Softdelete
    # ---------------------------------------------------------
    def archive(self, reason="archived_via_ui"):
        self.deleted_at = datetime.utcnow()
        self.deleted_reason = reason

    def restore(self):
        self.deleted_at = None
        self.deleted_reason = None

    # ---------------------------------------------------------
    # Harddelete-Schutz
    # ---------------------------------------------------------
    def can_hard_delete(self):
        """
        Ein Flugplatz darf nur gelöscht werden, wenn:
        - keine Loads existieren
        """
        return len(self.loads) == 0


    def __repr__(self):
        return f"<Flugplatz {self.name}>"