from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.deck_service import require_main_deck, require_study_card
from app.services.pair_service import get_or_create_pair_from_deck
from app.services.progress_service import record_study_answer
from app.services.srs import apply_review_no_commit, build_next_batch, build_study_status

def study_card(
    db: Session,
    *,
    user_id: int,
    card_id: int,
    learned: bool,
):
    try:
        card, deck = require_study_card(
            db,
            user_id=user_id,
            card_id=card_id,
        )

        review_result = apply_review_no_commit(
            db,
            user_id=user_id,
            card_id=card.id,
            learned=learned,
        )

        result = review_result.progress

        pair = get_or_create_pair_from_deck(
            db,
            user_id=user_id,
            deck=deck,
        )

        # TODO: future hook point for emitting compact review history events.
        record_study_answer(
            db,
            user_id=user_id,
            pair_id=pair.id,
            was_review=review_result.was_review,
        )
        db.commit()
        db.refresh(result)
        return result
    except Exception:
        db.rollback()
        raise


def next_study_for_main_deck(
    db: Session,
    *,
    user_id: int,
    deck_id: int,
    limit: int,
    new_ratio: float,
    max_new_per_day: int,
    max_reviews_per_day: int,
    reading_source_id: int | None = None,
):
    require_main_deck(
        db,
        user_id=user_id,
        deck_id=deck_id,
    )
    return build_next_batch(
        db=db,
        user_id=user_id,
        deck_id=deck_id,
        limit=limit,
        new_ratio=new_ratio,
        max_new_per_day=max_new_per_day,
        max_reviews_per_day=max_reviews_per_day,
        reading_source_id=reading_source_id,
    )


def status_for_main_deck(
    db: Session,
    *,
    user_id: int,
    deck_id: int,
    max_new_per_day: int,
    max_reviews_per_day: int,
    reading_source_id: int | None = None,
):
    require_main_deck(
        db,
        user_id=user_id,
        deck_id=deck_id,
    )
    return build_study_status(
        db=db,
        user_id=user_id,
        deck_id=deck_id,
        max_new_per_day=max_new_per_day,
        max_reviews_per_day=max_reviews_per_day,
        reading_source_id=reading_source_id,
    )
