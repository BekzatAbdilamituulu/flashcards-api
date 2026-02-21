
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from .. import crud, schemas
from ..services.srs import sm2_update, Sm2State
from ..deps import get_current_user

router = APIRouter(prefix="/study", tags=["study"])


def _apply_review(db: Session, user_id: int, card_id: int, quality: int) -> schemas.UserCardProgressOut:
    card = crud.get_card(db, card_id, user_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found or no access")

    rec = crud.get_user_card_progress(db, user_id, card_id)
    if not rec:
        rec = crud.create_user_card_progress(db, user_id, card_id)

    rec.times_seen = (rec.times_seen or 0) + 1
    if quality >= 3:
        rec.times_correct = (rec.times_correct or 0) + 1

    state = Sm2State(
        ease_factor=rec.ease_factor or 2.5,
        interval_days=rec.interval_days or 0,
        repetitions=rec.repetitions or 0,
    )

    new_state = sm2_update(state, quality)

    rec.ease_factor = new_state.ease_factor
    rec.interval_days = new_state.interval_days
    rec.repetitions = new_state.repetitions

    now = datetime.utcnow()
    rec.last_review = now
    rec.next_review = now + timedelta(days=rec.interval_days)

    db.commit()
    db.refresh(rec)
    return rec


@router.post("/{card_id}", response_model=schemas.UserCardProgressOut)
def study_card_me(
    card_id: int,
    payload: Optional[schemas.StudyAnswerIn] = None,
    correct: Optional[bool] = Query(default=None),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # prefer body
    if payload is not None:
        if payload.quality is not None:
            quality = payload.quality
        elif payload.correct is not None:
            quality = 4 if payload.correct else 1
        else:
            raise HTTPException(status_code=422, detail="Provide 'quality' or 'correct'")
    # fallback query param
    elif correct is not None:
        quality = 4 if correct else 1
    else:
        raise HTTPException(
            status_code=422,
            detail="Provide JSON body {'quality':0..5} or {'correct':true/false} or ?correct=true/false",
        )

    rec = crud.get_user_card_progress(db, current_user.id, card_id)
    was_review = (rec is not None) and ((rec.times_seen or 0) > 0)

    result = _apply_review(db, current_user.id, card_id, quality)
    dp = crud.get_or_create_daily_progress(db, user_id=current_user.id)
    dp.cards_done += 1
    if was_review:
        dp.reviews_done += 1
    else:
        dp.new_done += 1

    db.commit()

    return result


@router.get("/next", response_model=schemas.StudyBatchOut)
def next_study(
    deck_id: int,
    limit: int = 20,
    new_ratio: float = 0.3,
    max_new_per_day: int = 10,
    max_reviews_per_day: int = 100,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    limit = max(1, min(limit, 20))
    new_ratio = max(0.0, min(new_ratio, 1.0))

    # quotas (per deck)
    reviewed_today = crud.count_reviewed_today(db, current_user.id, deck_id)
    new_today = crud.count_new_introduced_today(db, current_user.id, deck_id)

    remaining_review_quota = max(0, max_reviews_per_day - reviewed_today)
    remaining_new_quota = max(0, max_new_per_day - new_today)

    target_new = int(round(limit * new_ratio))
    target_reviews = limit - target_new

    target_reviews = min(target_reviews, remaining_review_quota)
    target_new = min(limit - target_reviews, remaining_new_quota)

    review_cards, review_total = crud.get_due_reviews(
        db,
        deck_id,
        current_user.id,
        limit=target_reviews,
        offset=0,
    )
    remaining = min(limit - len(review_cards), remaining_new_quota)

    new_cards, new_total = crud.get_new_cards(
        db,
        deck_id,
        current_user.id,
        [c.id for c in review_cards],
        limit=remaining,
        offset=0,
    )

    cards = review_cards + new_cards
    return {"deck_id": deck_id, "count": len(cards), "cards": cards}


@router.get("/status", response_model=schemas.StudyStatusOut)
def study_status(
    deck_id: int,
    max_new_per_day: int = 10,
    max_reviews_per_day: int = 100,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reviewed_today = crud.count_reviewed_today(db, current_user.id, deck_id)
    new_today = crud.count_new_introduced_today(db, current_user.id, deck_id)

    due_count = crud.count_due_reviews(db, current_user.id, deck_id)
    new_available_count = crud.count_new_available(db, current_user.id, deck_id)
    next_due_at = crud.get_next_due_at(db, current_user.id, deck_id)

    remaining_review_quota = max(0, max_reviews_per_day - reviewed_today)
    remaining_new_quota = max(0, max_new_per_day - new_today)

    return {
        "deck_id": deck_id,
        "due_count": due_count,
        "new_available_count": new_available_count,
        "reviewed_today": reviewed_today,
        "new_introduced_today": new_today,
        "remaining_review_quota": remaining_review_quota,
        "remaining_new_quota": remaining_new_quota,
        "next_due_at": next_due_at,
    }