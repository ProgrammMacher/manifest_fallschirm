"""
Email sending progress tracking using threading and session storage.
"""
import threading
from typing import Dict, Optional

# In-memory storage for progress (keyed by invoice_id)
# In production, use Redis instead
_progress_store: Dict[int, Dict] = {}
_progress_lock = threading.Lock()


def set_progress(invoice_id: int, step: str, percent: int, status: str = 'processing'):
    """Store progress information for an invoice email send."""
    with _progress_lock:
        _progress_store[invoice_id] = {
            'step': step,
            'percent': percent,
            'status': status,
        }


def get_progress(invoice_id: int) -> Optional[Dict]:
    """Get current progress for an invoice email send."""
    with _progress_lock:
        return _progress_store.get(invoice_id, None)


def clear_progress(invoice_id: int):
    """Clear progress after send is complete."""
    with _progress_lock:
        _progress_store.pop(invoice_id, None)


def mark_complete(invoice_id: int):
    """Mark send as complete."""
    set_progress(invoice_id, 'E-Mail versendet', 100, 'completed')


def get_active_job_ids() -> list[int]:
    """Return IDs of invoices currently being processed (status=processing)."""
    with _progress_lock:
        return [
            inv_id
            for inv_id, data in _progress_store.items()
            if data.get("status") == "processing"
        ]
