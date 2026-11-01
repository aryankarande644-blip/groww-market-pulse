#!/usr/bin/env bash
# Local (non-Docker) dev bootstrap for the backend.
# Assumes a local Postgres is already running and DATABASE_URL is exported
# (or a .env file exists alongside backend/).
set -euo pipefail

cd "$(dirname "$0")/../backend"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate

pip install -r requirements.txt

echo "Running migrations..."
alembic upgrade head

echo "Seeding demo data..."
python -m app.seed

echo "Starting API on http://localhost:8000 ..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
