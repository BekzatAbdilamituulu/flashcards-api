from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from .. import schemas, crud
from ..deps import get_current_user

router = APIRouter(prefix="/decks", tags=["decks"])


@router.get("", response_model=list[schemas.DecksOut])
def list_decks(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return crud.get_decks(db, user.id)


@router.post("", response_model=schemas.DecksOut)
def create_deck(
    payload: schemas.DecksCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        return crud.create_deck(db, payload, user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{deck_id}", response_model=schemas.DecksOut)
def get_deck(
    deck_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    deck = crud.get_deck(db, deck_id, user.id)
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    return deck


@router.post("/{deck_id}/words", response_model=schemas.WordOut)
def create_word_in_deck(
    deck_id: int,
    payload: schemas.WordCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    # Force deck_id from path
    payload.deck_id = deck_id
    try:
        return crud.create_word(db, payload, user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{deck_id}", status_code=204)
def delete_deck(
    deck_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    ok = crud.delete_deck(db, deck_id, user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Deck not found")
    return None