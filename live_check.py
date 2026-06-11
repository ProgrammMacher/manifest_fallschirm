import sys
from flask import template_rendered
from app import create_app
import sqlite3

def test_waiver_selection():
    app = create_app()
    app.config['TESTING'] = True
    client = app.test_client()

    captured_contexts = {}

    def capture_template_context(sender, template, context, **extra):
        if template.name == 'person/waiver_pdf.html':
            person = context.get('person')
            if person:
                captured_contexts[person.id] = {
                    'is_tandem_guest': context.get('is_tandem_guest'),
                    'waiver_text': context.get('waiver_text')
                }

    template_rendered.connect(capture_template_context, app)

    # Database connection for expected texts
    conn = sqlite3.connect('data/manifest.db')
    c = conn.cursor()
    c.execute("SELECT waiver_text_tandem, waiver_text_skydiver FROM billing_config ORDER BY id DESC LIMIT 1")
    config = c.fetchone()
    expected_tandem_text = config[0] if config else None
    expected_skydiver_text = config[1] if config else None
    conn.close()

    tandem_id = 6
    skydiver_id = 1

    ids_to_check = [
        (tandem_id, True, expected_tandem_text, "TANDEM"),
        (skydiver_id, False, expected_skydiver_text, "SKYDIVER")
    ]

    print(f"TANDEM_ID={tandem_id}, SKYDIVER_ID={skydiver_id}")

    for pid, expected_tandem, expected_text, label in ids_to_check:
        response = client.get(f"/person/{pid}/waiver.pdf")
        status = response.status_code
        content_type = response.content_type
        print(f"/person/{pid}/waiver.pdf status={status} content_type={content_type}")

        if pid in captured_contexts:
            ctx = captured_contexts[pid]
            actual_is_tandem = ctx['is_tandem_guest']
            actual_text = ctx['waiver_text']

            # Selection check
            selection_pass = (actual_is_tandem == expected_tandem)
            
            # Text check
            text_pass = False
            reason = ""
            if not expected_text:
                text_pass = True
                reason = "Text leer aber Branch korrekt"
            elif actual_text == expected_text:
                text_pass = True
            else:
                reason = f"Text mismatch. Expected prefix: {str(expected_text)[:20]}..."

            if selection_pass and text_pass:
                print(f"{label}_SELECTION=PASS ({reason if reason else 'OK'})")
            else:
                fail_reason = []
                if not selection_pass: fail_reason.append(f"is_tandem_guest mismatch ({actual_is_tandem} != {expected_tandem})")
                if not text_pass: fail_reason.append(reason)
                print(f"{label}_SELECTION=FAIL ({', '.join(fail_reason)})")
        else:
            print(f"{label}_SELECTION=FAIL (Template not rendered or ID mismatch)")

if __name__ == "__main__":
    test_waiver_selection()
