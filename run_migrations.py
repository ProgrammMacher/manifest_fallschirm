from app import create_app, db
from flask_migrate import upgrade, Migrate
import os

app = create_app()
# Sicherstellen, dass Migrate initialisiert ist, falls app.extensions['migrate'] fehlt
if 'migrate' not in app.extensions:
    Migrate(app, db)

with app.app_context():
    try:
        # Multi-head-safe: in diesem Projekt koennen parallel mehrere Heads existieren.
        upgrade(directory='migrations', revision='heads')
        print('MIGRATION_OK')
    except Exception as e:
        print(f'MIGRATION_ERROR: {e}')
