from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from .. import schemas
from ..deps import get_current_user
from ..services.deck import build_deck_items

router = APIRouter(tags=["deck"])

@router.get("/deck", response_model=list[schemas.DeckItemOut])
def get_deck(
    language_id: int,
    limit: int = 20,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    return build_deck_items(db, user.id, language_id, limit)
