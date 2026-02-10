import random
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_

from .. import models, schemas

MASTERED = 3

def interval_for(uw) -> timedelta:
    if (uw.times_correct or 0) >= 3:
        return timedelta(days=14)
    if (uw.times_correct or 0) == 2:
        return timedelta(days=3)
    if (uw.times_correct or 0) == 1:
        return timedelta(days=1)
    return timedelta(minutes=10)

def is_overdue(uw, now: datetime) -> bool:
    if not uw.last_review:
        return False
    return now >= uw.last_review + interval_for(uw)

def compute_status(times_seen: int, times_correct: int) -> str:
    if times_correct >= MASTERED:
        return "mastered"
    if times_seen <= 0:
        return "new"
    return "learning"

def build_deck_items(db: Session, user_id: int, language_id: int, limit: int = 20) -> list[schemas.DeckItemOut]:
    lang = (
        db.query(models.Language)
        .filter(models.Language.id == language_id, models.Language.owner_id == user_id)
        .first()
    )
    if not lang:
        raise HTTPException(status_code=404, detail="Language not found")

    learned = (
        db.query(models.Word, models.UserWord)
        .join(
            models.UserWord,
            and_(
                models.UserWord.word_id == models.Word.id,
                models.UserWord.user_id == user_id,
            ),
        )
        .filter(models.Word.language_id == language_id)
        .all()
    )

    now = datetime.utcnow()

    overdue_learning, overdue_mastered = [], []
    due_learning, due_mastered = [], []

    for w, uw in learned:
        mastered = (uw.times_correct or 0) >= MASTERED
        overdue = is_overdue(uw, now)
        if mastered and overdue:
            overdue_mastered.append((w, uw))
        elif mastered and not overdue:
            due_mastered.append((w, uw))
        elif (not mastered) and overdue:
            overdue_learning.append((w, uw))
        else:
            due_learning.append((w, uw))

    new_words = (
        db.query(models.Word)
        .filter(models.Word.language_id == language_id)
        .filter(
            ~models.Word.id.in_(
                db.query(models.UserWord.word_id).filter(models.UserWord.user_id == user_id)
            )
        )
        .all()
    )

    n_new_target = int(limit * 0.7)
    n_learning_target = int(limit * 0.2)
    n_mastered_target = max(limit - n_new_target - n_learning_target, 0)

    overdue_cap = int(limit * 0.6)

    random.shuffle(overdue_learning)
    random.shuffle(overdue_mastered)
    random.shuffle(new_words)
    random.shuffle(due_learning)
    random.shuffle(due_mastered)

    picked_pairs: list[tuple[models.Word, models.UserWord]] = []
    picked_new: list[models.Word] = []

    overdue_all = overdue_learning + overdue_mastered
    picked_overdue = overdue_all[:overdue_cap]
    picked_pairs.extend(picked_overdue)

    remaining_slots = limit - len(picked_pairs)
    if remaining_slots <= 0:
        return _to_items(picked_pairs, picked_new)

    n_new = min(n_new_target, remaining_slots)
    picked_new = new_words[:n_new]
    remaining_slots -= len(picked_new)

    if remaining_slots <= 0:
        return _to_items(picked_pairs, picked_new)

    n_learning = min(n_learning_target, remaining_slots)
    picked_pairs.extend(due_learning[:n_learning])
    remaining_slots -= n_learning

    if remaining_slots <= 0:
        return _to_items(picked_pairs, picked_new)

    n_mastered = min(n_mastered_target, remaining_slots)
    picked_pairs.extend(due_mastered[:n_mastered])
    remaining_slots -= n_mastered

    if remaining_slots > 0:
        remaining_learning = due_learning[n_learning:]
        remaining_mastered = due_mastered[n_mastered:]
        filler_pairs = remaining_learning + remaining_mastered
        random.shuffle(filler_pairs)
        picked_pairs.extend(filler_pairs[:remaining_slots])

    return _to_items(picked_pairs, picked_new)

def _to_items(pairs, new_words):
    items: list[schemas.DeckItemOut] = []

    for w in new_words:
        items.append(
            schemas.DeckItemOut(word=w, status="new", times_seen=0, times_correct=0, last_review=None)
        )

    for w, uw in pairs:
        items.append(
            schemas.DeckItemOut(
                word=w,
                status=uw.status or compute_status(uw.times_seen or 0, uw.times_correct or 0),
                times_seen=uw.times_seen or 0,
                times_correct=uw.times_correct or 0,
                last_review=uw.last_review,
            )
        )

    return items
