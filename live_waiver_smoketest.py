import sqlite3
from contextlib import contextmanager
from flask import template_rendered
from app import create_app

DB_PATH = 'data/manifest.db'

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute('SELECT id FROM person WHERE is_tandem_guest = 1 ORDER BY id ASC LIMIT 1')
row_t = cur.fetchone()
cur.execute('SELECT id FROM person WHERE is_tandem_guest = 0 ORDER BY id ASC LIMIT 1')
row_s = cur.fetchone()
conn.close()

if not row_t or not row_s:
    print('ERROR: Could not find tandem/non-tandem IDs')
    raise SystemExit(1)

tandem_id = int(row_t[0])
skydiver_id = int(row_s[0])

app = create_app()

@contextmanager
def captured_templates(flask_app):
    recorded = []
    def record(sender, template, context, **extra):
        recorded.append((template, context))
    template_rendered.connect(record, flask_app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, flask_app)


def check_person(pid, expect_tandem):
    with app.app_context():
        client = app.test_client()
        with captured_templates(app) as templates:
            resp = client.get(f'/persons/{pid}/waiver.pdf')

        status = resp.status_code
        ctype = resp.content_type or ''

        tpl_name = ''
        ctx = None
        for tpl, context in templates:
            if getattr(tpl, 'name', '') == 'person/waiver_pdf.html':
                tpl_name = tpl.name
                ctx = context
                break

        template_ok = (tpl_name == 'person/waiver_pdf.html')
        branch_ok = False
        text_ok = False
        text_reason = ''

        if ctx is not None:
            is_tandem_guest_ctx = bool(ctx.get('is_tandem_guest'))
            branch_ok = (is_tandem_guest_ctx == expect_tandem)

            cfg = ctx.get('billing_config')
            waiver_text = (ctx.get('waiver_text') or '')
            if cfg is None:
                text_reason = 'no billing_config in context'
                text_ok = False
            else:
                expected_text = (cfg.waiver_text_tandem if expect_tandem else cfg.waiver_text_skydiver) or ''
                if expected_text == '':
                    text_ok = True
                    text_reason = 'Text leer aber Branch korrekt'
                else:
                    text_ok = (waiver_text == expected_text)
                    text_reason = 'exact match' if text_ok else 'waiver_text differs from expected config field'
        else:
            text_reason = 'template context not captured'

        return {
            'pid': pid,
            'url': f'/persons/{pid}/waiver.pdf',
            'status': status,
            'ctype': ctype,
            'template_ok': template_ok,
            'branch_ok': branch_ok,
            'text_ok': text_ok,
            'text_reason': text_reason,
        }

res_t = check_person(tandem_id, True)
res_s = check_person(skydiver_id, False)

overall = (
    res_t['status'] == 200 and 'application/pdf' in res_t['ctype'] and res_t['template_ok'] and res_t['branch_ok'] and res_t['text_ok']
    and
    res_s['status'] == 200 and 'application/pdf' in res_s['ctype'] and res_s['template_ok'] and res_s['branch_ok'] and res_s['text_ok']
)

print(f"TANDEM_ID={tandem_id}, SKYDIVER_ID={skydiver_id}")
print(
    f"TANDEM_URL={res_t['url']} status={res_t['status']} content_type={res_t['ctype']} "
    f"template={'PASS' if res_t['template_ok'] else 'FAIL'} branch={'PASS' if res_t['branch_ok'] else 'FAIL'} "
    f"text={'PASS' if res_t['text_ok'] else 'FAIL'}({res_t['text_reason']})"
)
print(
    f"SKYDIVER_URL={res_s['url']} status={res_s['status']} content_type={res_s['ctype']} "
    f"template={'PASS' if res_s['template_ok'] else 'FAIL'} branch={'PASS' if res_s['branch_ok'] else 'FAIL'} "
    f"text={'PASS' if res_s['text_ok'] else 'FAIL'}({res_s['text_reason']})"
)
print(f"OVERALL_SELECTION={'PASS' if overall else 'FAIL'}")
