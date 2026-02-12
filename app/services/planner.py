from dataclasses import dataclass
from typing import List, Optional

from .. import crud, models


@dataclass
class PlanResult:
    planned_reviews: int
    planned_new: int
    review_word_ids: List[int]
    new_word_ids: List[int]
    message: Optional[str]
    backlog_due_count: int
    backlog_protection_active: bool


def build_today_plan(
    db,
    user: models.User,
    language_id: int,
    backlog_threshold: int = 150,
) -> PlanResult:
    """
    Card-based planner.
    """

    capacity = user.daily_card_target
    due_count = crud.count_due_reviews(db, user.id, language_id)

    backlog_protection_active = due_count >= backlog_threshold
    message = None

    if backlog_protection_active:
        # survival mode
        planned_reviews = capacity
        planned_new = 0
        message = (
            f"You have {due_count} reviews waiting. "
            "New cards paused until backlog is reduced."
        )
    else:
        # normal distribution
        reviews_cap = int(capacity * 0.7)
        new_cap = capacity - reviews_cap

        planned_reviews = reviews_cap
        planned_new = min(user.daily_new_target, new_cap)

    # pull reviews
    due_items = crud.get_due_reviews_prioritized(
        db, user.id, language_id, limit=planned_reviews
    )
    review_word_ids = [uw.word_id for uw in due_items]

    # if not enough reviews, shift capacity to new
    if len(review_word_ids) < planned_reviews:
        free = planned_reviews - len(review_word_ids)
        planned_new += free

    # pull new
    new_words = crud.get_new_words(
        db, user.id, language_id, exclude_word_ids=review_word_ids, limit=planned_new
    )
    new_word_ids = [w.id for w in new_words]

    # don't lie
    planned_reviews = len(review_word_ids)
    planned_new = len(new_word_ids)

    return PlanResult(
        planned_reviews=planned_reviews,
        planned_new=planned_new,
        review_word_ids=review_word_ids,
        new_word_ids=new_word_ids,
        message=message,
        backlog_due_count=due_count,
        backlog_protection_active=backlog_protection_active,
    )
