from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .. import crud, models, schemas

SMALL_DELAY_SECONDS = 45  # "after few cards" approximation




@dataclass(frozen=True)
class SrsResult:
    status: str  # new | learning | mastered
    stage: int | None  # 1..5 when learning
    due_at: datetime | None

@dataclass
class ApplyReviewResult:
    progress: models.UserCardProgress
    was_review: bool

def schedule_next(
    *,
    status: models.ProgressStatus,
    stage: int | None,
    learned: bool,
    now: datetime,
) -> SrsResult:
    if status == models.ProgressStatus.MASTERED:
        return SrsResult(status=models.ProgressStatus.MASTERED, stage=stage, due_at=None)

    if status == models.ProgressStatus.NEW:
        if not learned:
            return SrsResult(
                status=models.ProgressStatus.NEW,
                stage=None,
                due_at=now + timedelta(seconds=SMALL_DELAY_SECONDS),
            )

        return SrsResult(
            status=models.ProgressStatus.LEARNING,
            stage=1,
            due_at=now + timedelta(seconds=SMALL_DELAY_SECONDS),
        )

    if status == models.ProgressStatus.LEARNING:
        cur_stage = int(stage or 1)

        if not learned:
            new_stage = max(1, cur_stage - 1)
            return SrsResult(
                status=models.ProgressStatus.LEARNING,
                stage=new_stage,
                due_at=now + timedelta(seconds=SMALL_DELAY_SECONDS),
            )

        if cur_stage == 1:
            return SrsResult(status=models.ProgressStatus.LEARNING, stage=2, due_at=now + timedelta(minutes=5))
        if cur_stage == 2:
            return SrsResult(status=models.ProgressStatus.LEARNING, stage=3, due_at=now + timedelta(hours=1))
        if cur_stage == 3:
            return SrsResult(status=models.ProgressStatus.LEARNING, stage=4, due_at=now + timedelta(hours=12))
        if cur_stage == 4:
            return SrsResult(status=models.ProgressStatus.LEARNING, stage=5, due_at=now + timedelta(hours=72))

        return SrsResult(status=models.ProgressStatus.MASTERED, stage=5, due_at=None)

    return SrsResult(
        status=models.ProgressStatus.NEW,
        stage=None,
        due_at=now + timedelta(seconds=SMALL_DELAY_SECONDS),
    )


def apply_review_no_commit(
    db: Session,
    user_id: int,
    card_id: int,
    learned: bool,
) -> ApplyReviewResult:
    card = crud.get_card(db, card_id, user_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found or no access")

    rec = crud.get_user_card_progress(db, user_id, card_id)

    was_review = (rec is not None) and ((rec.times_seen or 0) > 0)

    if not rec:
        rec = crud.create_user_card_progress(db, user_id, card_id)

    now = datetime.utcnow()

    rec.times_seen = (rec.times_seen or 0) + 1
    if learned:
        rec.times_correct = (rec.times_correct or 0) + 1

    rec.status = rec.status or models.ProgressStatus.NEW

    res = schedule_next(
        status=rec.status,
        stage=rec.stage,
        learned=learned,
        now=now,
    )

    rec.status = (
        res.status
        if isinstance(res.status, models.ProgressStatus)
        else models.ProgressStatus(res.status)
    )
    rec.stage = res.stage
    rec.due_at = res.due_at
    rec.last_review = now

    db.flush()
    return ApplyReviewResult(
        progress=rec,
        was_review=was_review,
    )

def build_next_batch(
    *,
    db: Session,
    user_id: int,
    deck_id: int,
    limit: int = 20,
    new_ratio: float = 0.3,
    max_new_per_day: int = 10,
    max_reviews_per_day: int = 100,
):
    # clamp
    limit = max(1, min(int(limit), 20))
    new_ratio = max(0.0, min(float(new_ratio), 1.0))

    # quotas (per deck)
    reviewed_today = crud.count_reviewed_today(db, user_id, deck_id)
    new_today = crud.count_new_introduced_today(db, user_id, deck_id)

    remaining_review_quota = max(0, max_reviews_per_day - reviewed_today)
    remaining_new_quota = max(0, max_new_per_day - new_today)

    target_new = int(round(limit * new_ratio))
    target_reviews = limit - target_new

    target_reviews = min(target_reviews, remaining_review_quota)
    target_new = min(limit - target_reviews, remaining_new_quota)

    review_cards, _review_total = crud.get_due_reviews(
        db,
        deck_id,
        user_id,
        limit=target_reviews,
        offset=0,
    )

    remaining = min(limit - len(review_cards), remaining_new_quota)

    new_cards, _new_total = crud.get_new_cards(
        db,
        deck_id,
        user_id,
        [c.id for c in review_cards],
        limit=remaining,
        offset=0,
    )

    cards = review_cards + new_cards

    items = [{"type": "review", "card": c} for c in review_cards] + [
        {"type": models.ProgressStatus.NEW, "card": c} for c in new_cards
    ]

    meta = {
        "deck_id": deck_id,
        "due_count": crud.count_due_reviews(db, user_id, deck_id),
        "new_available_count": crud.count_new_available(db, user_id, deck_id),
        "reviewed_today": reviewed_today,
        "new_introduced_today": new_today,
        "remaining_review_quota": remaining_review_quota,
        "remaining_new_quota": remaining_new_quota,
        "next_due_at": crud.get_next_due_at(db, user_id, deck_id),
    }

    return {
        "deck_id": deck_id,
        "count": len(cards),
        "cards": cards,
        "items": items,
        "meta": meta,
    }


def build_study_status(
    *,
    db: Session,
    user_id: int,
    deck_id: int,
    max_new_per_day: int = 10,
    max_reviews_per_day: int = 100,
):
    reviewed_today = crud.count_reviewed_today(db, user_id, deck_id)
    new_today = crud.count_new_introduced_today(db, user_id, deck_id)

    due_count = crud.count_due_reviews(db, user_id, deck_id)
    new_available_count = crud.count_new_available(db, user_id, deck_id)
    next_due_at = crud.get_next_due_at(db, user_id, deck_id)

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
