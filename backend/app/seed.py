"""
Seed the database with:
  - the full instrument universe (searchable)
  - a demo user (demo@growwpulse.app / Demo@12345)
  - one watchlist containing the 12 demo symbols with the exact attention mix
    described in the challenge brief
  - an initial checkpoint representing "last checked 10:14 AM"
  - one advanced market tick so the dashboard shows real, pre-baked changes
    the moment you log in -- no manual clicking required before the demo
    story is visible.

Safe to re-run: it no-ops on anything that already exists.
"""
from datetime import datetime, timedelta, timezone

from app.database import SessionLocal, engine, Base
from app.models import User, Instrument, Watchlist, WatchlistItem, UserPreference
from app.auth import hash_password, create_session
from app.market_data.mock_provider import MockMarketDataProvider, INSTRUMENT_UNIVERSE, SCENARIOS
from app import services

DEMO_EMAIL = "demo@growwpulse.app"
DEMO_PASSWORD = "Demo@12345"

# The 12 demo symbols map 1:1 onto the SCENARIOS in mock_provider.py, which
# gives exactly: 3 high, 2 moderate, 2 low, 3 unchanged, 1 stale, 1 delayed.
DEMO_WATCHLIST_SYMBOLS = [
    "RELIANCE", "ADANIENT", "TATAMOTORS",   # high attention
    "ICICIBANK", "BHARTIARTL",              # moderate
    "SBIN", "WIPRO",                        # low
    "TCS", "INFY", "LT",                    # unchanged
    "ITC",                                  # stale
    "MARUTI",                               # delayed
]


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # --- Instruments -----------------------------------------------------
        for symbol, (name, sector, base_price) in INSTRUMENT_UNIVERSE.items():
            existing = db.query(Instrument).filter(Instrument.symbol == symbol).first()
            if not existing:
                db.add(Instrument(symbol=symbol, name=name, exchange="NSE", sector=sector, base_price=base_price))
        db.commit()

        # --- Demo user ---------------------------------------------------------
        user = db.query(User).filter(User.email == DEMO_EMAIL).first()
        if not user:
            user = User(email=DEMO_EMAIL, password_hash=hash_password(DEMO_PASSWORD), display_name="Demo Trader", onboarded=True)
            db.add(user)
            db.commit()
            db.refresh(user)

        prefs = db.query(UserPreference).filter(UserPreference.user_id == user.id).first()
        if not prefs:
            db.add(UserPreference(user_id=user.id))
            db.commit()

        # --- Demo watchlist ------------------------------------------------
        wl = db.query(Watchlist).filter(Watchlist.user_id == user.id).first()
        if not wl:
            wl = Watchlist(user_id=user.id, name="My Watchlist")
            db.add(wl)
            db.commit()
            db.refresh(wl)

        symbol_to_instrument = {i.symbol: i for i in db.query(Instrument).all()}
        for symbol in DEMO_WATCHLIST_SYMBOLS:
            instrument = symbol_to_instrument[symbol]
            exists = db.query(WatchlistItem).filter(
                WatchlistItem.watchlist_id == wl.id, WatchlistItem.instrument_id == instrument.id
            ).first()
            if not exists:
                db.add(WatchlistItem(watchlist_id=wl.id, instrument_id=instrument.id))
        db.commit()

        already_seeded = services.get_last_checkpoint(db, wl.id) is not None
        if already_seeded:
            print("Demo data already present -- skipping snapshot/checkpoint seeding.")
            return

        provider = MockMarketDataProvider()
        instruments = [symbol_to_instrument[s] for s in DEMO_WATCHLIST_SYMBOLS]

        # Step 0: the state as it was when the user "last checked" at 10:14 AM.
        step0 = services.refresh_snapshots(db, provider, instruments)

        # Backdate that first snapshot's timestamps to look like this morning,
        # and write the checkpoint at that backdated time.
        checked_at = datetime.now(timezone.utc).replace(hour=10, minute=14, second=0, microsecond=0)
        if checked_at > datetime.now(timezone.utc):
            checked_at -= timedelta(days=1)
        for snap in step0.values():
            snap.market_timestamp = checked_at
            snap.received_at = checked_at
        db.commit()

        refs = {symbol: step0[symbol].id for symbol in DEMO_WATCHLIST_SYMBOLS}
        checkpoint = services.write_checkpoint(db, user.id, wl.id, refs)
        checkpoint.checked_at = checked_at
        db.commit()

        # Step 1: advance the mock market so real, meaningful differences
        # exist between the checkpoint and "now" -- this is what makes
        # "You Were Away" show real content on first login.
        services.refresh_snapshots(db, provider, instruments)

        print(f"Seed complete. Demo login: {DEMO_EMAIL} / {DEMO_PASSWORD}")
        print(f"Demo watchlist id: {wl.id}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
