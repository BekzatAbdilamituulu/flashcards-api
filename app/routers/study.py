from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..database import get_db
from ..deps import get_current_user
from ..services.srs import (
    _apply_review,
    build_next_batch,
    build_study_status,
)
from ..utils.time import bishkek_today

router = APIRouter(prefix="/study", tags=["study"])


@router.post("/{card_id}", response_model=schemas.UserCardProgressOut)
def study_card_me(
    card_id: int,
    payload: schemas.StudyAnswerIn,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 1) Load card + deck + check access + ensure main deck
    row = (
        db.query(models.Card, models.Deck)
        .join(models.Deck, models.Card.deck_id == models.Deck.id)
        .join(models.DeckAccess, models.DeckAccess.deck_id == models.Deck.id)
        .filter(models.Card.id == card_id, models.DeckAccess.user_id == current_user.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Card not found or no access")

    card, deck = row
    if deck.deck_type != "main":
        raise HTTPException(status_code=400, detail="You can only study from main deck")

    # 2) Determine review vs new BEFORE applying review
    rec = crud.get_user_card_progress(db, current_user.id, card_id)
    was_review = (rec is not None) and ((rec.times_seen or 0) > 0)

    # 3) Apply review (updates progress)
    result = _apply_review(db, current_user.id, card_id, payload.learned)

    # 4) Resolve learning pair from deck languages
    pair = (
        db.query(models.UserLearningPair)
        .filter(
            models.UserLearningPair.user_id == current_user.id,
            models.UserLearningPair.source_language_id == deck.source_language_id,
            models.UserLearningPair.target_language_id == deck.target_language_id,
        )
        .first()
    )
    if not pair:
        pair = models.UserLearningPair(
            user_id=current_user.id,
            source_language_id=deck.source_language_id,
            target_language_id=deck.target_language_id,
            is_default=False,
        )
        db.add(pair)
        db.flush()

    day = bishkek_today()
    dp = crud.get_or_create_daily_progress(
        db, user_id=current_user.id, learning_pair_id=pair.id, day=day
    )
    dp.cards_done += 1
    dp.reviews_done += 1 if was_review else 0
    dp.new_done += 0 if was_review else 1

    db.commit()
    return result


@router.get("/decks/{deck_id}/next", response_model=schemas.StudyBatchOut)
def next_study_for_deck(
    deck_id: int,
    limit: int = Query(20, ge=1, le=100),
    new_ratio: float = Query(0.3, ge=0.0, le=1.0),
    max_new_per_day: int = Query(10, ge=0, le=1000),
    max_reviews_per_day: int = Query(100, ge=0, le=5000),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    deck = crud.get_deck(db, deck_id, current_user.id)
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found or no access")

    if deck.deck_type != "main":
        raise HTTPException(status_code=400, detail="You can only study from main deck")

    return build_next_batch(
        db=db,
        user_id=current_user.id,
        deck_id=deck_id,
        limit=limit,
        new_ratio=new_ratio,
        max_new_per_day=max_new_per_day,
        max_reviews_per_day=max_reviews_per_day,
    )


@router.get("/decks/{deck_id}/status", response_model=schemas.StudyStatusOut)
def study_status_for_deck(
    deck_id: int,
    max_new_per_day: int = Query(10, ge=0, le=1000),
    max_reviews_per_day: int = Query(100, ge=0, le=5000),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):

    deck = crud.get_deck(db, deck_id, current_user.id)
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found or no access")
    if deck.deck_type != "main":
        raise HTTPException(status_code=400, detail="You can only study from main deck")
    return build_study_status(
        db=db,
        user_id=current_user.id,
        deck_id=deck_id,
        max_new_per_day=max_new_per_day,
        max_reviews_per_day=max_reviews_per_day,
    )
