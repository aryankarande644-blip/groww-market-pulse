#!/usr/bin/env bash
# Drops and recreates all tables, then reseeds. Useful when iterating on the
# schema locally without writing a new Alembic revision each time.
set -euo pipefail
cd "$(dirname "$0")/../backend"
source .venv/bin/activate 2>/dev/null || true

python -c "
from app.database import Base, engine
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
print('Schema reset.')
"
python -m app.seed
