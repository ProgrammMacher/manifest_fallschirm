# app/security/admin.py

from functools import wraps
from flask import session, abort


def is_admin() -> bool:
    """
    Zentrale Admin-Prüfung.
    """
    return bool(session.get("is_admin", False))


def admin_required(func):
    """
    Decorator für Admin-only-Routen.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not is_admin():
            abort(403)
        return func(*args, **kwargs)
    return wrapper