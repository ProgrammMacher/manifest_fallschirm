# C:\manifest_fallschirm\app\models\aircraft.py
from __future__ import annotations

from datetime import datetime
from typing import Optional

from app import db


class Aircraft(db.Model):
    __tablename__ = "aircraft"

    id = db.Column(db.Integer, primary_key=True)

    type = db.Column(db.String(120), nullable=False)
    registration = db.Column(db.String(50), nullable=False, unique=True)

    # Anzahl Standardsitze
    seats = db.Column(db.Integer, nullable=False)

    # Standard-Absprunghöhe (Load-Voreinstellung)
    default_height = db.Column(
        db.Integer,
        nullable=False,
        default=3000,
        server_default="3000",
    )

    # Aktiv/Inaktiv (UI-Auswahl, ohne Daten zu löschen)
    active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )

    # Softdelete (Archivieren)
    deleted_at = db.Column(db.DateTime, nullable=True)
    deleted_reason = db.Column(db.String(255), nullable=True)

    # Beziehung zu Loads
    #
    # WICHTIG (inkrementelle Stabilität):
    # - KEIN delete-orphan / KEIN "all" Cascade
    #   => verhindert versehentliches Löschen historischer Loads (Rechnung/Archiv)
    #
    # In deiner gelieferten Version war cascade="all, delete-orphan". [1](https://onedrive.live.com/?id=fb583e43-f47f-40ee-b5f1-0188e23fb4c0&cid=222cf049bc54ff98&web=1)
    # Das ist für produktive Daten riskant. Wir reduzieren Cascade bewusst auf sichere Varianten,
    # ohne Funktionalität zu verlieren (Loads werden ohnehin über eigene Routen/Regeln verwaltet).
    loads = db.relationship(
        "Load",
        back_populates="aircraft",
        cascade="save-update, merge",
        passive_deletes=False,
        lazy="selectin",
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=db.func.now(),
    )

    # -----------------------------
    # Convenience / Status-Helper
    # -----------------------------
    @property
    def is_archived(self) -> bool:
        return self.deleted_at is not None

    @property
    def is_active(self) -> bool:
        """
        Logische Aktivität für UI/Selektion:
        - muss nicht archiviert sein
        - und active == True
        """
        return (self.deleted_at is None) and bool(self.active)

    def archive(self, reason: Optional[str] = None) -> None:
        """
        Softdelete / Archivierung.
        Das Objekt bleibt in DB, wird aber als archiviert markiert.
        """
        if self.deleted_at is None:
            self.deleted_at = datetime.utcnow()
        self.deleted_reason = (reason or "archived")

    def restore(self) -> None:
        """Archivierung rückgängig machen."""
        self.deleted_at = None
        self.deleted_reason = None

    def can_hard_delete(self) -> bool:
        """
        Harddelete nur, wenn es keine relevanten Daten gibt.

        Streng defensiv:
        - Wenn irgendein Load dieses Aircraft referenziert -> False
        - Zusätzlich: Wenn irgendein LoadEntry paid/billed existiert -> False
          (doppelte Absicherung, selbst wenn irgendwann Constraints/Cascades anders wären)

        Hinweis:
        Diese Methode entscheidet nur über "darf"; der tatsächliche Admin-Delete
        muss serverseitig weiter geprüft werden.
        """
        try:
            from app.models.load import Load  # lokale Imports vermeiden Zyklen
            from app.models.load_entry import LoadEntry

            # 1) Keine Loads überhaupt
            load_count = Load.query.filter_by(aircraft_id=self.id).count()
            if load_count != 0:
                return False

            # 2) Zusätzliche Sicherheitsprüfung: keine paid/billed Entries (sollte bei load_count==0 ohnehin 0 sein)
            paid_or_billed = (
                db.session.query(LoadEntry.id)
                .join(Load, LoadEntry.load_id == Load.id)
                .filter(Load.aircraft_id == self.id)
                .filter((LoadEntry.paid.is_(True)) | (LoadEntry.billed.is_(True)))
                .limit(1)
                .all()
            )
            return len(paid_or_billed) == 0
        except Exception:
            # Wenn irgendwas schief geht, lieber NICHT hard-delete erlauben
            return False

    def __repr__(self) -> str:
        return f"<Aircraft {self.registration}>"

# EOF