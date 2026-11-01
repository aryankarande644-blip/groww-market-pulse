# Database

Market Pulse uses a single PostgreSQL database (modular monolith — no
per-service databases).

- **Schema / ORM models**: `../backend/app/models.py`
- **Migrations**: `../backend/alembic/` (run via `alembic upgrade head`
  from inside `backend/`, or automatically on `docker compose up`)
- **Seed data**: `../backend/app/seed.py` (creates the instrument universe,
  the demo user, and the pre-baked demo watchlist described in the README)

This folder exists to keep the top-level project layout close to the
brief's requested structure; the actual schema/migration code lives next to
the application code that owns it, which is the more conventional layout
for a FastAPI + Alembic project and avoids import-path gymnastics.
