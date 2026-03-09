from __future__ import annotations
from sqlalchemy.orm import Session
from dataclasses import dataclass
from app import crud
from app.services.deck_service import resolve_main_deck_by_pair_or_deck
from app.services.pair_service import resolve_user_pair
from app.utils.time import bishkek_today
from app import models

@dataclass
class QueueSnapshot:
    due_count: int
    new_available_count: int
    next_due_at: datetime | None


@dataclass
class DailyQuotaSnapshot:
    reviewed_today: int
    new_introduced_today: int
    remaining_review_quota: int
    remaining_new_quota: int

def get_queue_snapshot(
    db: Session,
    *,
    user_id: int,
    deck_id: int | None = None,
    pair_id: int | None = None,
) -> QueueSnapshot:
    return QueueSnapshot(
        due_count=crud.count_due_reviews(
            db,
            user_id=user_id,
            deck_id=deck_id,
            pair_id=pair_id,
        ),
        new_available_count=crud.count_new_available(
            db,
            user_id=user_id,
            deck_id=deck_id,
            pair_id=pair_id,
        ),
        next_due_at=crud.get_next_due_at(
            db,
            user_id=user_id,
            deck_id=deck_id,
            pair_id=pair_id,
        ),
    )

def get_daily_quota_snapshot(
    db: Session,
    *,
    user_id: int,
    deck_id: int,
    max_reviews_per_day: int,
    max_new_per_day: int,
) -> DailyQuotaSnapshot:
    reviewed_today = crud.count_reviewed_today(
        db,
        user_id=user_id,
        deck_id=deck_id,
    )
    new_introduced_today = crud.count_new_introduced_today(
        db,
        user_id=user_id,
        deck_id=deck_id,
    )

    return DailyQuotaSnapshot(
        reviewed_today=reviewed_today,
        new_introduced_today=new_introduced_today,
        remaining_review_quota=max(0, max_reviews_per_day - reviewed_today),
        remaining_new_quota=max(0, max_new_per_day - new_introduced_today),
    )

def record_study_answer(
    db: Session,
    *,
    user_id: int,
    pair_id: int,
    was_review: bool,
):
    day = bishkek_today()

    dp = crud.get_or_create_daily_progress(
        db,
        user_id=user_id,
        learning_pair_id=pair_id,
        day=day,
    )

    dp.cards_done += 1
    if was_review:
        dp.reviews_done += 1
    else:
        dp.new_done += 1

    db.flush()
    return dp

def build_progress_summary(
    db: Session,
    current_user,
    *,
    deck_id: int | None = None,
    pair_id: int | None = None,
    streak_threshold: int = 10,
):
    d = bishkek_today()
    pair = resolve_user_pair(db, current_user.id, pair_id)

    dp = crud.get_daily_progress_for_day(db, current_user.id, pair.id, d)
    today_added = crud.count_cards_created_on_day(
        db, current_user.id, d, deck_id=deck_id, pair_id=pair.id
    )
    st = crud.get_streak(db, current_user.id, pair.id, threshold=streak_threshold)

    if deck_id is not None:
        deck = resolve_main_deck_by_pair_or_deck(
            db,
            user_id=current_user.id,
            deck_id=deck_id,
        )
        queue = get_queue_snapshot(
            db,
            user_id=current_user.id,
            deck_id=deck.id,
        )
    else:
        queue = get_queue_snapshot(
            db,
            user_id=current_user.id,
            pair_id=pair.id,
        )

    due_count = queue.due_count
    new_available = queue.new_available_count
    next_due = queue.next_due_at

    daily_card_target = int(getattr(current_user, "daily_card_target", 20) or 20)
    daily_new_target = int(getattr(current_user, "daily_new_target", 7) or 7)

    quota = get_daily_quota_snapshot(
        db,
        user_id=current_user.id,
        deck_id=deck_id,
        max_reviews_per_day=daily_card_target,
        max_new_per_day=daily_new_target,
    )

    cards_remaining = quota.remaining_review_quota
    new_remaining = quota.remaining_new_quota

    cards_goal_pct = (
        min(quota.reviewed_today / daily_card_target, 1.0)
        if daily_card_target > 0 else 1.0
    )
    new_goal_pct = (
        min(quota.new_introduced_today / daily_new_target, 1.0)
        if daily_new_target > 0 else 1.0
    )

    total_cards = crud.count_total_cards(db, current_user.id, deck_id=deck_id, pair_id=pair.id)
    status_counts = crud.count_progress_statuses(db, current_user.id, deck_id=deck_id, pair_id=pair.id)

    return {
        "date": d,
        "today_cards_done": dp.cards_done,
        "today_reviews_done": dp.reviews_done,
        "today_new_done": dp.new_done,
        "today_added_cards": today_added,
        "daily_card_target": daily_card_target,
        "daily_new_target": daily_new_target,
        "cards_remaining": cards_remaining,
        "new_remaining": new_remaining,
        "cards_goal_pct": cards_goal_pct,
        "new_goal_pct": new_goal_pct,
        "current_streak": st["current_streak"],
        "best_streak": st["best_streak"],
        "streak_threshold": st["threshold"],
        "due_count": due_count,
        "new_available_count": new_available,
        "next_due_at": next_due,
        "total_cards": total_cards,
        "total_mastered": int(
            status_counts.get("mastered", status_counts.get('mastered', 0))
        ),
        "total_learning": int(
            status_counts.get("learning", status_counts.get('learning', 0))
        ),
        "total_new": int(
        status_counts.get("new", status_counts.get('new', 0))
        ),
        }