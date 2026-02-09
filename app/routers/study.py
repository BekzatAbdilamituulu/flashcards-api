from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
import random
from typing import Optional

from ..database import get_db
from .. import crud, schemas
from ..services.deck import compute_status
from ..services.review import score_word
from ..deps import get_current_user  # <-- JWT dependency

router = APIRouter(prefix="/study", tags=["study"])


# -------------------------
# 
# -------------------------
def _apply_review(db, user_id: int, word_id: int, is_correct: bool):
    word = crud.get_word(db, word_id, user_id)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")

    rec = crud.get_user_word_record(db, user_id, word_id)
    if not rec:
        rec = crud.create_user_word_record(db, user_id, word_id)

    rec.times_seen = (rec.times_seen or 0) + 1
    if is_correct:
        rec.times_correct = (rec.times_correct or 0) + 1

    rec.last_review = datetime.utcnow()
    rec.status = compute_status(rec.times_seen or 0, rec.times_correct or 0)

    db.commit()
    db.refresh(rec)
    return rec



@router.post("/{word_id}", response_model=schemas.UserWordOut)
def study_word_me(
    word_id: int,
    payload: Optional[schemas.StudyAnswerIn] = None,  # JSON body (optional)
    correct: Optional[bool] = Query(default=None),    # query param (optional)
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # choose correct value from body first, otherwise from query
    if payload is not None:
        is_correct = payload.correct
    elif correct is not None:
        is_correct = correct
    else:
        raise HTTPException(
            status_code=422,
            detail="Provide JSON body {'correct': true/false} or ?correct=true/false",
        )

    return _apply_review(db, current_user.id, word_id, is_correct)


@router.get("/next", response_model=list[schemas.NextReviewOut])
def next_word_me(
    language_id: int,
    limit: int = 5,
    random_top: int = 3,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    limit = max(1, min(limit, 50))

    rows = crud.get_review_candidates(db, current_user.id, language_id)
    if not rows:
        raise HTTPException(status_code=404, detail="No words for this language")

    scored: list[schemas.NextReviewOut] = []

    for word, uw in rows:
        times_seen = (uw.times_seen if uw else 0) or 0
        times_correct = (uw.times_correct if uw else 0) or 0
        last_review = uw.last_review if uw else None

        status_str = compute_status(times_seen, times_correct)
        s = score_word(times_seen, times_correct, last_review)

        if status_str == "new":
            reason = "new word"
        elif status_str == "learning":
            reason = "needs practice"
        else:
            reason = "review mastered"

        scored.append(
            schemas.NextReviewOut(
                word=word,
                score=float(round(s, 4)),
                reason=reason,
                last_review=last_review,
                times_seen=times_seen,
                times_correct=times_correct,
                status=status_str,
            )
        )

    scored.sort(key=lambda x: x.score, reverse=True)

    top = scored[:limit]
    random_top = min(len(top), max(1, random_top))
    choice = random.choice(top[:random_top])

    return [choice]


