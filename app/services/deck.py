import random
from sqlalchemy.orm import Session
from sqlalchemy import and_

from .. import models

MASTERED = 3

def build_deck(db: Session, user_id: int, language_id: int, limit: int = 20) -> list[models.Word]:
    learned = (
        db.query(models.Word, models.UserWord)
        .join(models.UserWord, and_(models.UserWord.word_id == models.Word.id,
                                   models.UserWord.user_id == user_id))
        .filter(models.Word.language_id == language_id)
        .all()
    )

    learning_words = [w for (w, uw) in learned if (uw.times_correct or 0) < MASTERED]
    known_words = [w for (w, uw) in learned if (uw.times_correct or 0) >= MASTERED]

    new_words = (
        db.query(models.Word)
        .filter(models.Word.language_id == language_id)
        .filter(~models.Word.id.in_(
            db.query(models.UserWord.word_id).filter(models.UserWord.user_id == user_id)
        ))
        .all()
    )

    n_new = int(limit * 0.7)
    n_learning = int(limit * 0.2)
    n_known = max(limit - n_new - n_learning, 0)

    random.shuffle(new_words)
    random.shuffle(learning_words)
    random.shuffle(known_words)

    deck = new_words[:n_new] + learning_words[:n_learning] + known_words[:n_known]
    random.shuffle(deck)
    return deck

def compute_status(times_seen: int, times_correct: int) -> str:
    if times_correct >= MASTERED:
        return "mastered"
    if times_seen <= 0:
        return "new"
    return "learning"