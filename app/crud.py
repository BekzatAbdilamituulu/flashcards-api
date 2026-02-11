from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import datetime

from . import models, schemas



# ---------- Languages ----------
def language_has_words(db: Session, language_id: int, user_id: int) -> bool:
    return (
        db.query(models.Word)
        .filter(
            models.Word.language_id == language_id,
            models.Word.owner_id == user_id,
        )
        .first()
        is not None
    )


def create_language(db: Session, language: schemas.LanguageCreate, user_id: int) -> models.Language:
    obj = models.Language(**language.dict(), owner_id=user_id)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_languages(db: Session, user_id: int) -> list[models.Language]:
    return (
    db.query(models.Language)
    .filter(models.Language.owner_id == user_id)
    .all()
)

def get_language(db: Session, language_id: int, user_id: int) -> models.Language | None:
    return (
        db.query(models.Language)
        .filter(models.Language.id == language_id, models.Language.owner_id == user_id)
        .first()
    )

def update_language(db: Session, language_id: int, payload: schemas.LanguageUpdate, user_id: int):
    obj = (
        db.query(models.Language)
        .filter(models.Language.id == language_id, models.Language.owner_id == user_id)
        .first()
    )
    if not obj:
        return None

    # only update provided fields
    data = payload.dict(exclude_unset=True)
    for k, v in data.items():
        setattr(obj, k, v)

    db.commit()
    db.refresh(obj)
    return obj


def delete_language(db: Session, language_id: int, user_id: int) -> bool:
    obj = (
        db.query(models.Language)
        .filter(
            models.Language.id == language_id,
            models.Language.owner_id == user_id,
        )
        .first()
    )
    if not obj:
        return False

    #  prevent delete if words exist
    if language_has_words(db, language_id, user_id):
        raise ValueError("Language contains words")

    db.delete(obj)
    db.commit()
    return True



# ---------- Words ----------
def create_word(db: Session, word: schemas.WordCreate, user_id: int) -> models.Word:
    obj = models.Word(**word.dict(), owner_id=user_id)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_words_by_language(db: Session, language_id: int, user_id: int) -> list[models.Word]:
    return (db.query(models.Word).filter(
    models.Word.language_id == language_id,
    models.Word.owner_id == user_id)
    .all()
)


def get_word(db: Session, word_id: int, user_id: int) -> models.Word | None:
    return (
        db.query(models.Word)
        .filter(models.Word.id == word_id, models.Word.owner_id == user_id)
        .first()
)

def update_word(db: Session, word_id: int, word: schemas.WordCreate, user_id: int):
    db_word = (db.query(models.Word)
        .filter(models.Word.id == word_id, models.Word.owner_id == user_id)
        .first()
    )
    if not db_word:
        return None

    db_word.text = word.text
    db_word.translation = word.translation
    db_word.example_sentence = word.example_sentence
    db_word.language_id = word.language_id

    db.commit()
    db.refresh(db_word)
    return db_word


def delete_word(db: Session, word_id: int, user_id: int) -> bool:
    db_word = (db.query(models.Word)
        .filter(models.Word.id == word_id, models.Word.owner_id == user_id)
        .first()
    )
    if not db_word:
        return False

    db.delete(db_word)
    db.commit()
    return True

def find_word_by_term(db: Session, user_id: int, language_id: int, text: str):
    return (
        db.query(models.Word)
        .filter(
            models.Word.owner_id == user_id,
            models.Word.language_id == language_id,
            models.Word.text == text,
        )
        .first()
    )

def create_word_fields(db: Session, user_id: int, language_id: int, text: str, translation: str, example_sentence: str | None = None):
    w = models.Word(
        owner_id=user_id,
        language_id=language_id,
        text=text.strip(),
        translation=translation.strip(),
        example_sentence=example_sentence.strip() if example_sentence else None,
    )
    db.add(w)
    return w



# ---------- Users ----------
def create_user(db: Session, username: str, hashed_password: str) -> models.User:
    obj = models.User(username=username, hashed_password=hashed_password)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_user(db: Session, user_id: int) -> models.User | None:
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_username(db: Session, username: str) -> models.User | None:
    return db.query(models.User).filter(models.User.username == username).first()


# ---------- Study progress ----------
def get_user_word_record(db: Session, user_id: int, word_id: int) -> models.UserWord | None:
    return db.query(models.UserWord).filter(
        and_(models.UserWord.user_id == user_id, models.UserWord.word_id == word_id)
    ).first()


def create_user_word_record(db: Session, user_id: int, word_id: int) -> models.UserWord:
    rec = models.UserWord(
        user_id=user_id,
        word_id=word_id,
        times_seen=0,
        times_correct=0,
        last_review=None,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def get_user_words(db: Session, user_id: int) -> list[models.UserWord]:
    return db.query(models.UserWord).filter(models.UserWord.user_id == user_id).all()


# User progress

def get_user_progress(db: Session, user_id: int, language_id: int):
    # returns list of (Word, Userword)
    rows = (
        db.query(models.Word, models.UserWord)
        .join(
            models.UserWord,
            and_(
                models.UserWord.word_id == models.Word.id,
                models.UserWord.user_id == user_id
            )
        )
        .filter(models.Word.language_id == language_id)
        .all()
    )
    return rows


def get_progress_stats(db: Session, user_id: int, language_id: int):
    rows = (
        db.query(
            models.UserWord.status,
            func.coalesce(func.sum(models.UserWord.times_seen), 0),
            func.coalesce(func.sum(models.UserWord.times_correct), 0),
            func.count(models.UserWord.id),
        )
        .join(models.Word, models.Word.id == models.UserWord.word_id)
        .filter(models.UserWord.user_id == user_id)
        .filter(models.Word.language_id == language_id)
        .group_by(models.UserWord.status)
        .all()
    )

    # rows: [(status, sum_seen, sum_correctm count), ...]
    counts = {'new': 0, 'learning': 0, 'mastered': 0}
    total_seen = 0
    total_correct = 0
    total_tracked = 0

    for status, sum_seen, sum_correct, count in rows:
        status_key = (status or "new").lower()
        if status_key not in counts:
            status_key = 'learning'

        counts[status_key] += int(count)
        total_seen += int(sum_seen or 0)
        total_correct += int(sum_correct or 0)
        total_tracked += int(count)

    accuracy = (total_correct / total_seen) if total_seen > 0 else 0.0

    return{
        "language_id": language_id,
        "total_tracked": total_tracked,
        "new": counts["new"],
        "learning": counts["learning"],
        "mastered": counts["mastered"],
        "total_seen": total_seen,
        "total_correct": total_correct,
        "accuracy": accuracy,
    }

def reset_user_progress(db: Session, user_id: int, language_id: int) -> int:
    # subquery: all word IDs in this language
    word_ids_subq = (
        db.query(models.Word.id)
        .filter(models.Word.language_id == language_id)
        .subquery()
    )

    # query of UserWord rows to delete (NO JOIN)
    q = (
        db.query(models.UserWord)
        .filter(models.UserWord.user_id == user_id)
        .filter(models.UserWord.word_id.in_(word_ids_subq))
    )

    deleted = q.count()
    q.delete(synchronize_session=False)
    db.commit()
    return deleted

def get_review_candidates(db: Session, language_id: int, user_id: int):
    # returns list of (Word, UserWord|None) for the language

    rows = (
        db.query(models.Word, models.UserWord)
        .outerjoin(
            models.UserWord,
            and_(
                models.UserWord.word_id == models.Word.id,
                models.UserWord.user_id == user_id,
                )
            )
        .filter(models.Word.language_id == language_id)
        .filter(models.Word.owner_id == user_id)
        .all()
    )
    return rows


#srs
def get_due_reviews(db: Session, language_id: int, user_id: int, limit: int):
    now = datetime.utcnow()
    return (
        db.query(models.Word)
        .join(models.UserWord, models.UserWord.word_id == models.Word.id)
        .filter(
            models.Word.owner_id == user_id,
            models.Word.language_id == language_id,
            models.UserWord.user_id == user_id,
            models.UserWord.next_review.isnot(None),
            models.UserWord.next_review <= now,
        )
        .order_by(models.UserWord.next_review.asc())
        .limit(limit)
        .all()
    )

def get_new_words(db: Session, language_id: int, user_id: int, exclude_word_ids: list[int], limit: int):
    q = (
        db.query(models.Word)
        .outerjoin(
            models.UserWord,
            and_(
                models.UserWord.word_id == models.Word.id,
                models.UserWord.user_id == user_id,
            )
        )
        .filter(
            models.Word.owner_id == user_id,
            models.Word.language_id == language_id,
            models.UserWord.id.is_(None),  # no progress record => new
        )
    )

    if exclude_word_ids:
        q = q.filter(~models.Word.id.in_(exclude_word_ids))

    return q.order_by(models.Word.id.asc()).limit(limit).all()


def count_reviewed_today(db: Session, user_id: int, language_id: int) -> int:
    now = datetime.utcnow()
    start = datetime(now.year, now.month, now.day)  # UTC day start
    return (
        db.query(models.UserWord)
        .join(models.Word, models.Word.id == models.UserWord.word_id)
        .filter(
            models.UserWord.user_id == user_id,
            models.Word.language_id == language_id,
            models.UserWord.last_review.isnot(None),
            models.UserWord.last_review >= start,
        )
        .count()
    )

def count_new_introduced_today(db: Session, user_id: int, language_id: int) -> int:
    now = datetime.utcnow()
    start = datetime(now.year, now.month, now.day)
    return (
        db.query(models.UserWord)
        .join(models.Word, models.Word.id == models.UserWord.word_id)
        .filter(
            models.UserWord.user_id == user_id,
            models.Word.language_id == language_id,
            models.UserWord.times_seen == 1,
            models.UserWord.last_review.isnot(None),
            models.UserWord.last_review >= start,
        )
        .count()
    )