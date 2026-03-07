from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db
from ..deps import get_current_user, require_admin

router = APIRouter(prefix="/library", tags=["library"])


@router.get("/decks", response_model=schemas.Page[schemas.DeckOut])
def list_library_decks(
    limit: int = 20,
    offset: int = 0,
    pair_id: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    try:
        items, total = crud.list_library_decks(
            db,
            current_user.id,
            limit=limit,
            offset=offset,
            pair_id=pair_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "items": items,
        "meta": {
            "limit": limit,
            "offset": offset,
            "total": total,
            "has_more": offset + len(items) < total,
        },
    }

@router.get("/decks/{deck_id}/cards", response_model=schemas.Page[schemas.CardOut])
def library_deck_cards(
    deck_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    items, total = crud.list_library_deck_cards(db, deck_id, limit=limit, offset=offset)

    return {
        "items": items,
        "meta": {
            "limit": limit,
            "offset": offset,
            "total": total,
            "has_more": (offset + limit) < total,
        },
    }


@router.post("/cards/{card_id}/import", response_model=schemas.ImportCardOut)
def import_library_card(
    card_id: int,
    payload: schemas.ImportCardIn,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        return crud.import_library_card_to_main_deck(
            db,
            user_id=current_user.id,
            library_card_id=card_id,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post(
    "/decks/{deck_id}/import-selected",
    response_model=schemas.ImportSelectedCardsOut,
)
def import_selected_cards(
    deck_id: int,
    payload: schemas.ImportSelectedCardsIn,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        return crud.import_selected_library_cards_to_main_deck(
            db,
            user_id=current_user.id,
            library_deck_id=deck_id,
            card_ids=payload.card_ids
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/admin/decks", dependencies=[Depends(require_admin)], response_model=schemas.DeckOut)
def admin_create_library_deck(
    payload: schemas.DeckCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Admin-only: create a deck marked as deck_type='library'.

    For MVP, admins can add cards using existing /decks/{deck_id}/cards endpoints
    because admin is the deck owner.
    """
    deck = crud.create_deck(
        db,
        name=payload.name,
        owner_id=current_user.id,
        source_language_id=payload.source_language_id,
        target_language_id=payload.target_language_id,
        deck_type="library",
    )
    deck.is_public = True
    db.commit()
    db.refresh(deck)
    return deck
