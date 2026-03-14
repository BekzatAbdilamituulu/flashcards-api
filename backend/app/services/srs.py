from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from .. import crud, models

# Explicit SRS rules (DeepLex MVP):
# - wrong answer in learning drops one stage (min stage 1)
# - stage progression on correct answer follows fixed intervals
# - stage 5 + correct => mastered
FIRST_REVIEW_DELAY_SECONDS = 45
WRONG_ANSWER_DELAY_SECONDS = 45
LEARNING_SUCCESS_INTERVALS = {
    1: timedelta(minutes=5),
    2: timedelta(hours=1),
    3: timedelta(hours=5),
    4: timedelta(hours=14),
}
MAX_LEARNING_STAGE = 5


def utcnow() -> datetime:
    return datetime.utcnow()


@dataclass(frozen=True)
class SrsResult:
    status: str  # new | learning | mastered
    stage: int | None  # 1..5 when learning
    due_at: datetime | None

@dataclass
class ApplyReviewResult:
    progress: models.UserCardProgress
    was_review: bool

def _normalize_status(status: models.ProgressStatus | str | None) -> models.ProgressStatus:
    if status is None:
        return models.ProgressStatus.NEW
    if isinstance(status, models.ProgressStatus):
        return status
    return models.ProgressStatus(status)


def _normalize_stage(stage: int | None) -> int:
    if stage is None:
        return 1
    return max(1, min(int(stage), MAX_LEARNING_STAGE))


def compute_next_review_state(
    *,
    status: models.ProgressStatus | str | None,
    stage: int | None,
    learned: bool,
    now: datetime,
) -> SrsResult:
    cur_status = _normalize_status(status)

    if cur_status == models.ProgressStatus.MASTERED:
        return SrsResult(status=models.ProgressStatus.MASTERED, stage=stage, due_at=None)

    if cur_status == models.ProgressStatus.NEW:
        if not learned:
            return SrsResult(
                status=models.ProgressStatus.NEW,
                stage=None,
                due_at=now + timedelta(seconds=WRONG_ANSWER_DELAY_SECONDS),
            )

        return SrsResult(
            status=models.ProgressStatus.LEARNING,
            stage=1,
            due_at=now + timedelta(seconds=FIRST_REVIEW_DELAY_SECONDS),
        )

    if cur_status == models.ProgressStatus.LEARNING:
        cur_stage = _normalize_stage(stage)

        if not learned:
            new_stage = max(1, cur_stage - 1)
            return SrsResult(
                status=models.ProgressStatus.LEARNING,
                stage=new_stage,
                due_at=now + timedelta(seconds=WRONG_ANSWER_DELAY_SECONDS),
            )

        if cur_stage in LEARNING_SUCCESS_INTERVALS:
            next_stage = cur_stage + 1
            return SrsResult(
                status=models.ProgressStatus.LEARNING,
                stage=next_stage,
                due_at=now + LEARNING_SUCCESS_INTERVALS[cur_stage],
            )

        return SrsResult(status=models.ProgressStatus.MASTERED, stage=5, due_at=None)

    return SrsResult(
        status=models.ProgressStatus.NEW,
        stage=None,
        due_at=now + timedelta(seconds=WRONG_ANSWER_DELAY_SECONDS),
    )


def apply_review_no_commit(
    db: Session,
    user_id: int,
    card_id: int,
    learned: bool,
) -> ApplyReviewResult:
    card = crud.get_card(db, card_id, user_id)
    if not card:
        raise LookupError("Card not found or no access")

    rec = crud.get_user_card_progress(db, user_id, card_id)

    was_review = (rec is not None) and ((rec.times_seen or 0) > 0)

    if not rec:
        rec = crud.create_user_card_progress(db, user_id, card_id)

    now = utcnow()

    rec.times_seen = (rec.times_seen or 0) + 1
    if learned:
        rec.times_correct = (rec.times_correct or 0) + 1

    rec.status = _normalize_status(rec.status)
    res = compute_next_review_state(
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
    reading_source_id: int | None = None,
):
    # clamp
    limit = max(1, min(int(limit), 20))
    # Keep new_ratio input for API compatibility; due reviews are prioritized in queue building.
    _ = max(0.0, min(float(new_ratio), 1.0))

    # quotas (per deck)
    reviewed_today = crud.count_reviewed_today(db, user_id, deck_id)
    new_today = crud.count_new_introduced_today(db, user_id, deck_id)

    remaining_review_quota = max(0, max_reviews_per_day - reviewed_today)
    remaining_new_quota = max(0, max_new_per_day - new_today)

    # Reviews are always prioritized before introducing new cards.
    review_cards, _review_total = crud.get_due_reviews(
        db,
        deck_id,
        user_id,
        limit=min(limit, remaining_review_quota),
        offset=0,
        reading_source_id=reading_source_id,
    )

    remaining = max(0, limit - len(review_cards))
    new_limit = min(remaining, remaining_new_quota)

    new_cards, _new_total = crud.get_new_cards(
        db,
        deck_id,
        user_id,
        [c.id for c in review_cards],
        limit=new_limit,
        offset=0,
        reading_source_id=reading_source_id,
    )

    cards = review_cards + new_cards

    items = [{"type": "review", "card": c} for c in review_cards] + [
        {"type": "new", "card": c} for c in new_cards
    ]

    meta = {
        "deck_id": deck_id,
        "reading_source_id": reading_source_id,
        "due_count": crud.count_due_reviews(db, user_id, deck_id, reading_source_id=reading_source_id),
        "new_available_count": crud.count_new_available(db, user_id, deck_id, reading_source_id=reading_source_id),
        "reviewed_today": reviewed_today,
        "new_introduced_today": new_today,
        "remaining_review_quota": remaining_review_quota,
        "remaining_new_quota": remaining_new_quota,
        "next_due_at": crud.get_next_due_at(db, user_id, deck_id, reading_source_id=reading_source_id),
    }

    return {
        "deck_id": deck_id,
        "reading_source_id": reading_source_id,
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
    reading_source_id: int | None = None,
):
    reviewed_today = crud.count_reviewed_today(db, user_id, deck_id)
    new_today = crud.count_new_introduced_today(db, user_id, deck_id)

    due_count = crud.count_due_reviews(db, user_id, deck_id, reading_source_id=reading_source_id)
    new_available_count = crud.count_new_available(db, user_id, deck_id, reading_source_id=reading_source_id)
    next_due_at = crud.get_next_due_at(db, user_id, deck_id, reading_source_id=reading_source_id)

    remaining_review_quota = max(0, max_reviews_per_day - reviewed_today)
    remaining_new_quota = max(0, max_new_per_day - new_today)

    return {
        "deck_id": deck_id,
        "reading_source_id": reading_source_id,
        "due_count": due_count,
        "new_available_count": new_available_count,
        "reviewed_today": reviewed_today,
        "new_introduced_today": new_today,
        "remaining_review_quota": remaining_review_quota,
        "remaining_new_quota": remaining_new_quota,
        "next_due_at": next_due_at,
    }
