from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from .. import schemas
from ..services.demo_user import get_or_create_demo_user
from ..services.deck import build_deck

router = APIRouter(tags=["deck"])

@router.get("/deck", response_model=list[schemas.WordOut])
def get_deck(user_id: int, language_id: int, limit: int = 20, db: Session = Depends(get_db)):
    user = get_or_create_demo_user(db, user_id)
    return build_deck(db, user.id, language_id, limit)
