from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.config import get_settings
from app.auth import get_valid_session
from app.models import User
from app.market_data.provider import MarketDataProvider
from app.market_data.mock_provider import MockMarketDataProvider

settings = get_settings()

# A single provider instance is shared across the process. Swapping to a real
# vendor later is a one-line change here -- nothing else in the app imports
# MockMarketDataProvider directly.
_provider: MarketDataProvider = MockMarketDataProvider()


def get_market_data_provider() -> MarketDataProvider:
    return _provider


def get_current_user(
    db: DBSession = Depends(get_db),
    mp_session: str | None = Cookie(default=None, alias="mp_session"),
) -> User:
    session = get_valid_session(db, mp_session or "")
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user
