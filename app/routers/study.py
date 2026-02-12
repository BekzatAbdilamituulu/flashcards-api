from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
import random
from typing import Optional

from ..database import get_db
from .. import crud, schemas
from ..services.deck import compute_status
from ..services.review import score_word
from ..services.srs import sm2_update, Sm2State
from ..deps import get_current_user  # <-- JWT dependency

router = APIRouter(prefix="/study", tags=["study"])


# -------------------------
# 
# -------------------------
def _apply_review(db, user_id: int, word_id: int, quality: int):
    word = crud.get_word(db, word_id, user_id)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")

    rec = crud.get_user_word_record(db, user_id, word_id)
    if not rec:
        rec = crud.create_user_word_record(db, user_id, word_id)

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



@router.post("/{word_id}", response_model=schemas.UserWordOut)
def study_word_me(
    word_id: int,
    payload: Optional[schemas.StudyAnswerIn] = None,
    correct: Optional[bool] = Query(default=None),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 1) prefer body
    if payload is not None:
        if payload.quality is not None:
            quality = payload.quality
        elif payload.correct is not None:
            quality = 4 if payload.correct else 1
        else:
            raise HTTPException(status_code=422, detail="Provide 'quality' or 'correct'")
    # 2) fallback query param
    elif correct is not None:
        quality = 4 if correct else 1
    else:
        raise HTTPException(
            status_code=422,
            detail="Provide JSON body {'quality':0..5} or {'correct':true/false} or ?correct=true/false",
        )

    return _apply_review(db, current_user.id, word_id, quality)



@router.get("/next", response_model=schemas.DeckOut)
def next_study(
    language_id: int,
    limit: int = 20,
    new_ratio: float = 0.3,
    max_new_per_day: int = 10,
    max_reviews_per_day: int = 100,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    limit = max(1, min(limit, 50))
    new_ratio = max(0.0, min(new_ratio, 1.0))

    reviewed_today = crud.count_reviewed_today(db, current_user.id, language_id)
    new_today = crud.count_new_introduced_today(db, current_user.id, language_id)

    remaining_review_quota = max(0, max_reviews_per_day - reviewed_today)
    remaining_new_quota = max(0, max_new_per_day - new_today)

    target_new = int(round(limit * new_ratio))
    target_reviews = limit - target_new

    target_reviews = min(target_reviews, remaining_review_quota)
    target_new = min(limit - target_reviews, remaining_new_quota)

    review_words = crud.get_due_reviews(db, language_id, current_user.id, target_reviews)

    remaining = min(limit - len(review_words), remaining_new_quota)
    new_words = crud.get_new_words(db, language_id, current_user.id, [w.id for w in review_words], remaining)

    words = review_words + new_words
    return {"language_id": language_id, "count": len(words), "words": words}


@router.get("/status", response_model=schemas.StudyStatusOut)
def study_status(
    language_id: int,
    max_new_per_day: int = 10,
    max_reviews_per_day: int = 100,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reviewed_today = crud.count_reviewed_today(db, current_user.id, language_id)
    new_today = crud.count_new_introduced_today(db, current_user.id, language_id)

    due_count = crud.count_due_reviews(db, current_user.id, language_id)
    new_available_count = crud.count_new_available(db, current_user.id, language_id)
    next_due_at = crud.get_next_due_at(db, current_user.id, language_id)

    remaining_review_quota = max(0, max_reviews_per_day - reviewed_today)
    remaining_new_quota = max(0, max_new_per_day - new_today)

    return {
        "language_id": language_id,
        "due_count": due_count,
        "new_available_count": new_available_count,
        "reviewed_today": reviewed_today,
        "new_introduced_today": new_today,
        "remaining_review_quota": remaining_review_quota,
        "remaining_new_quota": remaining_new_quota,
        "next_due_at": next_due_at,
    }


