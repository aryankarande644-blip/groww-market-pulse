"""
Shared test fixtures.

Tests run against an in-memory SQLite database rather than Postgres so the
suite has zero external dependencies and runs anywhere. SQLite is a close
enough substitute here because nothing in the app relies on Postgres-only
behaviour (no native arrays, no partial indexes, JSON columns work on both).
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.deps import get_market_data_provider
from app.market_data.mock_provider import MockMarketDataProvider


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session):
    def _get_db_override():
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    app.dependency_overrides[get_market_data_provider] = lambda: MockMarketDataProvider()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def seeded_instrument(db_session):
    from app.models import Instrument
    inst = Instrument(symbol="RELIANCE", name="Reliance Industries Ltd", exchange="NSE", sector="Energy", base_price=1421.0)
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)
    return inst


@pytest.fixture()
def registered_user(client):
    resp = client.post("/auth/register", json={
        "email": "trader@example.com", "password": "SuperSecret123", "display_name": "Trader",
    })
    assert resp.status_code == 201
    return resp.json()
