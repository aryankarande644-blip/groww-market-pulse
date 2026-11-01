"""
Authentication primitives: password hashing and server-side session tokens.

Sessions -- not JWTs, not localStorage -- are the source of truth. A session
row in Postgres can be revoked instantly (logout, security incident) which a
stateless JWT cannot. At this scale (10k users) the extra DB lookup per
request is negligible and the simplicity/safety tradeoff is worth it.
"""
import secrets
from datetime import datetime, timedelta, timezone

from passlib.context import CryptContext
from sqlalchemy.orm import Session as DBSession

from app.config import get_settings
from app.models import Session as SessionModel, User

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_session(db: DBSession, user: User) -> SessionModel:
    token = secrets.token_urlsafe(settings.SESSION_TOKEN_BYTES)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.SESSION_TTL_HOURS)
    session = SessionModel(token=token, user_id=user.id, expires_at=expires_at)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_valid_session(db: DBSession, token: str) -> SessionModel | None:
    if not token:
        return None
    session = db.query(SessionModel).filter(SessionModel.token == token).first()
    if not session or session.revoked:
        return None
    if session.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        return None
    return session


def revoke_session(db: DBSession, token: str) -> None:
    session = db.query(SessionModel).filter(SessionModel.token == token).first()
    if session:
        session.revoked = True
        db.commit()
