from __future__ import annotations

from sqlalchemy.orm import Session

from app import models
from app.services.deck_service import require_study_card
from app.services.pair_service import get_or_create_pair_from_deck
from app.services.progress_service import record_study_answer
from app.utils.time import bishkek_today
from app.services.srs import apply_review_no_commit

def study_card(
    db: Session,
    *,
    user_id: int,
    card_id: int,
    learned: bool,
):
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

    record_study_answer(
        db,
        user_id=user_id,
        pair_id=pair.id,
        was_review=review_result.was_review,
    )
    db.commit()
    db.refresh(result)
    return result