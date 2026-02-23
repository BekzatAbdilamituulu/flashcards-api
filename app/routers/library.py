from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, require_admin
from .. import crud, schemas


router = APIRouter(prefix="/library", tags=["library"])


@router.get("/decks", response_model=list[schemas.LibraryDeckOut])
def library_decks(
    source_language_id: int | None = Query(default=None),
    target_language_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    decks = crud.list_library_decks(
        db,
        source_language_id=source_language_id,
        target_language_id=target_language_id,
    )

    out: list[dict] = []
    for d in decks:
        out.append(
            {
                "id": d.id,
                "name": d.name,
                "source_language_id": d.source_language_id,
                "target_language_id": d.target_language_id,
                "deck_type": d.deck_type,
                "cards_count": crud.count_cards_in_deck(db, d.id),
            }
        )
    return out


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
        return crud.import_library_card_to_user_deck(
            db,
            user_id=current_user.id,
            library_card_id=card_id,
            target_deck_id=payload.target_deck_id,
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
    )
    deck.deck_type = "library"
    deck.is_public = True
    db.commit()
    db.refresh(deck)
    return deck
