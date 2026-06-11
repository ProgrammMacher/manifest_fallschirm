import os
from datetime import date
from werkzeug.utils import secure_filename

def build_person_filename(person, kind, original_filename):
    """
    Erzeugt einen sicheren Dateinamen für Personen-Uploads.
    kind: 'Lizenz' oder 'Versicherung'
    """
    today = date.today().isoformat()  # z.B. 2026-02-05
    base_name = f"{kind}_{person.first_name}_{person.last_name}_{today}"
    base_name = secure_filename(base_name)

    # Dateiendung übernehmen (pdf, jpg, jpeg, png ...)
    ext = os.path.splitext(original_filename)[1].lower()
    return base_name + ext
