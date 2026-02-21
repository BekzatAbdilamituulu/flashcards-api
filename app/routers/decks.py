from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..database import get_db
from .. import crud, schemas
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

@router.patch("/{deck_id}", response_model=schemas.DeckOut)
def patch_deck(deck_id: int, payload: schemas.DeckUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        return crud.update_deck(db, deck_id=deck_id, user_id=user.id, name=payload.name, is_public=payload.is_public)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except LookupError:
        raise HTTPException(status_code=404, detail="Deck not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{deck_id}/publish", response_model=schemas.DeckPublishOut)
def publish(deck_id: int, make_public: bool = False, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        d = crud.publish_deck(db, deck_id=deck_id, user_id=user.id, make_public=make_public)
        return {"deck_id": d.id, "status": d.status.value, "is_public": d.is_public, "shared_code": d.shared_code}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except LookupError:
        raise HTTPException(status_code=404, detail="Deck not found")


@router.post("/{deck_id}/unpublish", response_model=schemas.DeckPublishOut)
def unpublish(deck_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        d = crud.unpublish_deck(db, deck_id=deck_id, user_id=user.id)
        return {"deck_id": d.id, "status": d.status.value, "is_public": d.is_public, "shared_code": d.shared_code}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except LookupError:
        raise HTTPException(status_code=404, detail="Deck not found")


@router.post("/{deck_id}/unshare", response_model=schemas.DeckPublishOut)
def unshare(deck_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        d = crud.unshare_deck(db, deck_id=deck_id, user_id=user.id)
        return {"deck_id": d.id, "status": d.status.value, "is_public": d.is_public, "shared_code": d.shared_code}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except LookupError:
        raise HTTPException(status_code=404, detail="Deck not found")

@router.delete("/{deck_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_deck(deck_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    ok = crud.delete_deck(db, deck_id, user.id)
    if not ok:
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
