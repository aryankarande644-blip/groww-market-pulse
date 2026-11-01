from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.config import get_settings
from app.models import User, UserPreference
from app.schemas import RegisterRequest, LoginRequest, UserOut
from app.auth import hash_password, verify_password, create_session, revoke_session
from app.deps import get_current_user

router = APIRouter(tags=["auth"])
settings = get_settings()


@router.post("/auth/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, response: Response, db: DBSession = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")

    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        display_name=payload.display_name or payload.email.split("@")[0],
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    db.add(UserPreference(user_id=user.id))
    db.commit()

    session = create_session(db, user)
    response.set_cookie(
        key=settings.COOKIE_NAME, value=session.token, httponly=True,
        secure=settings.COOKIE_SECURE, samesite="lax", max_age=settings.SESSION_TTL_HOURS * 3600,
    )
    return user


@router.post("/auth/login", response_model=UserOut)
def login(payload: LoginRequest, response: Response, db: DBSession = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    session = create_session(db, user)
    response.set_cookie(
        key=settings.COOKIE_NAME, value=session.token, httponly=True,
        secure=settings.COOKIE_SECURE, samesite="lax", max_age=settings.SESSION_TTL_HOURS * 3600,
    )
    return user


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    db: DBSession = Depends(get_db),
    mp_session: str | None = Cookie(default=None, alias="mp_session"),
):
    if mp_session:
        revoke_session(db, mp_session)
    response.delete_cookie(settings.COOKIE_NAME)
    return None


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/me/complete-onboarding", response_model=UserOut)
def complete_onboarding(user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    """Small, deliberate addition beyond the literal endpoint list: the
    Onboarding page needs somewhere to flip this flag once the user has
    created a watchlist and added their first stocks."""
    user.onboarded = True
    db.commit()
    db.refresh(user)
    return user
