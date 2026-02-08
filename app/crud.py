from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from . import models, schemas


# ---------- Languages ----------
def create_language(db: Session, language: schemas.LanguageCreate) -> models.Language:
    obj = models.Language(**language.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_languages(db: Session) -> list[models.Language]:
    return db.query(models.Language).all()


# ---------- Words ----------
def create_word(db: Session, word: schemas.WordCreate) -> models.Word:
    obj = models.Word(**word.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_words_by_language(db: Session, language_id: int) -> list[models.Word]:
    return db.query(models.Word).filter(models.Word.language_id == language_id).all()


def get_word(db: Session, word_id: int) -> models.Word | None:
    return db.query(models.Word).filter(models.Word.id == word_id).first()

def update_word(db: Session, word_id: int, word: schemas.WordCreate):
    db_word = db.query(models.Word).filter(models.Word.id == word_id).first()
    if not db_word:
        return None

    db_word.text = word.text
    db_word.translation = word.translation
    db_word.example_sentence = word.example_sentence
    db_word.language_id = word.language_id

    db.commit()
    db.refresh(db_word)
    return db_word


def delete_word(db: Session, word_id: int) -> bool:
    db_word = db.query(models.Word).filter(models.Word.id == word_id).first()
    if not db_word:
        return False

    db.delete(db_word)
    db.commit()
    return True





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

def get_review_candidates(db: Session, user_id: int, language_id: int):
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
        .all()
    )
    return rows