
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from .. import crud, schemas
from ..services.srs import schedule_next
from ..deps import get_current_user

router = APIRouter(prefix="/study", tags=["study"])


def _apply_review(db: Session, user_id: int, card_id: int, learned: bool) -> schemas.UserCardProgressOut:
    card = crud.get_card(db, card_id, user_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found or no access")

    rec = crud.get_user_card_progress(db, user_id, card_id)
    if not rec:
        rec = crud.create_user_card_progress(db, user_id, card_id)

    now = datetime.utcnow()

    # stats
    rec.times_seen = (rec.times_seen or 0) + 1
    if learned:
        rec.times_correct = (rec.times_correct or 0) + 1

    # default status
    rec.status = rec.status or "new"

    # compute next scheduling
    res = schedule_next(
        status=rec.status,
        stage=rec.stage,
        learned=learned,
        now=now,
    )

    rec.status = res.status
    rec.stage = res.stage
    rec.due_at = res.due_at
    rec.last_review = now

    db.commit()
    db.refresh(rec)
    return rec


@router.post("/{card_id}", response_model=schemas.UserCardProgressOut)
def study_card_me(
    card_id: int,
    payload: schemas.StudyAnswerIn,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rec = crud.get_user_card_progress(db, current_user.id, card_id)
    was_review = (rec is not None) and ((rec.times_seen or 0) > 0)

    result = _apply_review(db, current_user.id, card_id, payload.learned)

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