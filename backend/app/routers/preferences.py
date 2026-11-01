from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.models import User
from app.schemas import PreferencesOut, PreferencesUpdate
from app.deps import get_current_user
from app import services

router = APIRouter(tags=["preferences"])


@router.get("/preferences", response_model=PreferencesOut)
def get_preferences(db: DBSession = Depends(get_db), user: User = Depends(get_current_user)):
    return services.get_preferences(db, user.id)


@router.patch("/preferences", response_model=PreferencesOut)
def update_preferences(payload: PreferencesUpdate, db: DBSession = Depends(get_db), user: User = Depends(get_current_user)):
    prefs = services.get_preferences(db, user.id)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(prefs, key, value)
    db.commit()
    db.refresh(prefs)
    return prefs
