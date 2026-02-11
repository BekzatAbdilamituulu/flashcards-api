from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..services.deck import interval_for, MASTERED 


def get_language_stats(db: Session, user_id: int, language_id: int) -> schemas.StatsOut:
    lang = (
        db.query(models.Language)
        .filter(models.Language.id == language_id, models.Language.owner_id == user_id)
        .first()
    )
    if not lang:
        raise HTTPException(status_code=404, detail="Language not found")

    total_words = (
        db.query(models.Word)
        .filter(models.Word.language_id == language_id)
        .count()
    )

    learned_records = (
        db.query(models.UserWord)
        .join(models.Word, models.Word.id == models.UserWord.word_id)
        .filter(models.UserWord.user_id == user_id, models.Word.language_id == language_id)
        .all()
    )

    learned_words = len(learned_records)
    new_words = max(total_words - learned_words, 0)

    learning_words = sum(1 for uw in learned_records if (uw.times_correct or 0) < MASTERED)
    mastered_words = sum(1 for uw in learned_records if (uw.times_correct or 0) >= MASTERED)

    now = datetime.utcnow()  
    overdue_words = 0
    for uw in learned_records:
        if uw.last_review and now >= uw.last_review + interval_for(uw):
            overdue_words += 1

    return schemas.StatsOut(
        language_id=language_id,
        total_words=total_words,
        learned_words=learned_words,
        new_words=new_words,
        learning_words=learning_words,
        mastered_words=mastered_words,
        overdue_words=overdue_words,
    )
