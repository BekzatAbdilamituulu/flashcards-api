from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..database import get_db
from .. import crud, schemas
from ..deps import get_current_user


router = APIRouter(prefix="/decks", tags=["decks"])


@router.get("", response_model=list[schemas.DeckOut])
def list_my_decks(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return crud.get_user_decks(db, user.id)


@router.post("", response_model=schemas.DeckOut, status_code=status.HTTP_201_CREATED)
def create_deck(payload: schemas.DeckCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return crud.create_deck(
        db,
        name=payload.name,
        owner_id=user.id,
        source_language_id=payload.source_language_id,
        target_language_id=payload.target_language_id,
    )


@router.get("/{deck_id}", response_model=schemas.DeckOut)
def get_deck(deck_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    deck = crud.get_deck(db, deck_id, user.id)
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found or no access")
    return deck


@router.delete("/{deck_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_deck(deck_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    ok = crud.delete_deck(db, deck_id, user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Deck not found or not owner")
    return


@router.get("/{deck_id}/cards", response_model=list[schemas.CardOut])
def list_cards(deck_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return crud.list_deck_cards(db, deck_id, user.id)


@router.post("/{deck_id}/cards", response_model=schemas.CardOut, status_code=status.HTTP_201_CREATED)
def create_card(deck_id: int, payload: schemas.CardCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    # path deck_id wins
    return crud.create_card(db, deck_id=deck_id, user_id=user.id, front=payload.front, back=payload.back, example_sentence=payload.example_sentence)


@router.post("/{deck_id}/share-link", response_model=schemas.DeckOut)
def create_share_link(deck_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    # short, unique code
    code = uuid4().hex[:10]
    try:
        deck = crud.set_deck_share_code(db, deck_id, user.id, code)
    except IntegrityError:
        # retry once with a new code
        code = uuid4().hex[:12]
        deck = crud.set_deck_share_code(db, deck_id, user.id, code)

    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found or not owner")
    return deck


@router.post("/join/{shared_code}", status_code=status.HTTP_201_CREATED)
def join_deck(shared_code: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    access = crud.join_deck_by_code(db, user.id, shared_code)
    if not access:
        raise HTTPException(status_code=404, detail="Invalid share code")
    return {"deck_id": access.deck_id, "role": access.role.value}
