from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..database import get_db
from .. import crud, schemas, models
from ..deps import get_current_user


router = APIRouter(prefix="/decks", tags=["decks"])


@router.get("", response_model=schemas.Page[schemas.DeckOut])
def list_my_decks(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    items, total = crud.get_user_decks(db, user.id, limit=limit, offset=offset)

    return {
        "items": items,
        "meta": {
            "limit": limit,
            "offset": offset,
            "total": total,
            "has_more": offset + len(items) < total,
        },
    }


@router.post("", response_model=schemas.DeckOut, status_code=201)
def create_user_deck(
    payload: schemas.DeckCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if payload.deck_type != "users":
        raise HTTPException(status_code=400, detail="Only 'users' decks can be created manually")

    pair = crud.get_default_learning_pair(db, user.id)
    if not pair:
        raise HTTPException(status_code=400, detail="Default learning pair not set")

    # create a storage deck for the default pair
    return crud.create_deck(
        db,
        name=payload.name,
        owner_id=user.id,
        source_language_id=pair.source_language_id,
        target_language_id=pair.target_language_id,
        deck_type="users",
    )


@router.get("/{deck_id}", response_model=schemas.DeckOut)
def get_deck(deck_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    deck = crud.get_deck(db, deck_id, user.id)
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found or no access")
    return deck

@router.patch("/{deck_id}", response_model=schemas.DeckOut)
def patch_deck(
    deck_id: int,
    payload: schemas.DeckUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    deck = crud.get_deck(db, deck_id, user.id)
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found or no access")

    if deck.deck_type != "users":
        raise HTTPException(status_code=400, detail="Only 'users' decks can be updated")

    try:
        return crud.update_deck(
            db,
            deck_id=deck_id,
            user_id=user.id,
            name=payload.name,
            is_public=payload.is_public,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except LookupError:
        raise HTTPException(status_code=404, detail="Deck not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        

@router.delete("/{deck_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_deck(deck_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    deck = crud.get_deck(db, deck_id, user.id)
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found or no access")

    # Only users decks can be deleted by user
    if deck.deck_type != "users":
        raise HTTPException(status_code=403, detail="You cannot delete this deck type")

    ok = crud.delete_deck(db, deck_id, user.id)
    if not ok:
        # crud.delete_deck should enforce owner check; if it returns False => not owner
        raise HTTPException(status_code=404, detail="Deck not found or not owner")
    return

@router.get("/{deck_id}/cards", response_model=schemas.Page[schemas.CardOut])
def list_cards(
    deck_id: int,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    limit = max(1, min(limit, 200))
    offset = max(0, offset)

    items, total = crud.list_deck_cards(
        db,
        deck_id,
        user.id,
        limit=limit,
        offset=offset,
    )

    return {
        "items": items,
        "meta": {
            "limit": limit,
            "offset": offset,
            "total": total,
            "has_more": offset + len(items) < total,
        },
    }



@router.post("/{deck_id}/cards", response_model=schemas.CardOut, status_code=status.HTTP_201_CREATED)
def create_card(
    deck_id: int,
    payload: schemas.CardCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        return crud.create_card(
            db,
            deck_id=deck_id,
            user_id=user.id,
            front=payload.front,
            back=payload.back,
            example_sentence=payload.example_sentence,
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="No permission to edit deck")
    except LookupError:
        raise HTTPException(status_code=404, detail="Deck not found")
    except ValueError as e:
        # This covers: "Duplicate word in this deck"
        # and any validation error you raise from crud
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{deck_id}/cards/{card_id}", response_model=schemas.CardOut)
def update_card(
    deck_id: int,
    card_id: int,
    payload: schemas.CardUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        return crud.update_card(
            db,
            deck_id=deck_id,
            card_id=card_id,
            user_id=user.id,
            front=payload.front,
            back=payload.back,
            example_sentence=payload.example_sentence,
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="No permission to edit deck")
    except LookupError:
        raise HTTPException(status_code=404, detail="Card not found")
    except ValueError as e:
        # includes "Duplicate word in this deck" and "Front is required"
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{deck_id}/cards/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_card(
    deck_id: int,
    card_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        ok = crud.delete_card(db, deck_id=deck_id, card_id=card_id, user_id=user.id)
    except PermissionError:
        raise HTTPException(status_code=403, detail="No permission to edit deck")

    if not ok:
        raise HTTPException(status_code=404, detail="Card not found")
    return



