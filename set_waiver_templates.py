from app import create_app
from app import db
from app.models.billing_config import BillingConfig
from app.routes.billing import WAIVER_TEXT_SKYDIVER_DEFAULT, WAIVER_TEXT_TANDEM_DEFAULT

app = create_app()
with app.app_context():
    cfg = BillingConfig.query.first()
    if not cfg:
        cfg = BillingConfig(company_name='', street='', zip_code='', city='', country='Deutschland')
        db.session.add(cfg)
        db.session.flush()

    changed = []

    if not (cfg.waiver_text_skydiver or '').strip():
        cfg.waiver_text_skydiver = WAIVER_TEXT_SKYDIVER_DEFAULT
        changed.append('waiver_text_skydiver')

    if not (cfg.waiver_text_tandem or '').strip():
        cfg.waiver_text_tandem = WAIVER_TEXT_TANDEM_DEFAULT
        changed.append('waiver_text_tandem')

    if changed:
        db.session.commit()
        print('UPDATED_FIELDS=' + ','.join(changed))
    else:
        print('UPDATED_FIELDS=none (already set)')

    print('SKYDIVER_LEN=' + str(len(cfg.waiver_text_skydiver or '')))
    print('TANDEM_LEN=' + str(len(cfg.waiver_text_tandem or '')))
