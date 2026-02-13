from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import datetime, date

from . import models, schemas
from .services import mymemory, examples
import os


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

#Deck
def create_deck(db: Session, payload: schemas.DecksCreate, user_id: int) -> models.Deck:
    # Ensure languages belong to the user
    src = get_language(db, payload.source_language_id, user_id)
    tgt = get_language(db, payload.target_language_id, user_id)
    if not src or not tgt:
        raise ValueError("Invalid source/target language for this user")

    obj = models.Deck(
        name=payload.name,
        owner_id=user_id,
        source_language_id=payload.source_language_id,
        target_language_id=payload.target_language_id,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def get_decks(db: Session, user_id: int) -> list[models.Deck]:
    return (
        db.query(models.Deck)
        .filter(models.Deck.owner_id == user_id)
        .order_by(models.Deck.id.desc())
        .all()
    )

def get_deck(db: Session, deck_id: int, user_id: int) -> models.Deck | None:
    return (
        db.query(models.Deck)
        .filter(models.Deck.id == deck_id, models.Deck.owner_id == user_id)
        .first()
    )
    
def delete_deck(db: Session, deck_id: int, user_id: int) -> bool:
    deck = (
        db.query(models.Deck)
        .filter(models.Deck.id == deck_id, models.Deck.owner_id == user_id)
        .first()
    )
    if not deck:
        return False

    db.delete(deck)
    db.commit()
    return True


# ---------- Words ----------
def create_word(db: Session, word: schemas.WordCreate, user_id: int) -> models.Word:
    data = word.dict()

    # If deck_id provided, infer language pair from deck 
    deck_id = data.get("deck_id")
    if deck_id is not None:
        deck = get_deck(db, deck_id, user_id)
        if not deck:
            raise ValueError("Deck not found")

        # Force word.language_id to deck source language unless explicitly provided
        if not data.get("language_id"):
            data["language_id"] = deck.source_language_id

        # Determine translation target language from deck
        src_code = deck.source_language.code or ""
        tgt_code = deck.target_language.code or ""

        if not src_code or not tgt_code:
            raise ValueError("Deck languages must have 'code' set (e.g., en, ru)")

        email = os.getenv("MYMEMORY_EMAIL")

        # Auto-translate if requested or translation missing
        if data.get("auto_translate") or not data.get("translation"):
            data["translation"] = mymemory.translate(
                data["text"],
                src_code,
                tgt_code,
                email=email,
            )

        # Auto example sentence (store bilingual in example_sentence)
        if data.get("auto_example") and not data.get("example_sentence"):
            src_sentence = examples.make_example_sentence(data["text"], src_code)
            if src_sentence:
                tgt_sentence = mymemory.translate(src_sentence, src_code, tgt_code, email=email)
                data["example_sentence"] = f"{src_sentence} — {tgt_sentence}"

    # Remove helper flags before SQLAlchemy model init
    auto_translate = data.pop("auto_translate", None)
    data.pop("auto_example", None)

    # Legacy mode: require translation + language_id if not using deck
    if deck_id is None:
        if not data.get("language_id"):
            raise ValueError("language_id is required unless deck_id is provided")
        if not data.get("translation"):
            raise ValueError("translation is required unless auto_translate is enabled with deck_id")

    obj = models.Word(**data, owner_id=user_id)
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

def get_or_create_daily_progress(db, user_id: int):
    today = date.today()

    row = (
        db.query(models.DailyProgress)
        .filter(
            models.DailyProgress.user_id == user_id,
            models.DailyProgress.date == today,
        )
        .first()
    )

    if not row:
        row = models.DailyProgress(
            user_id=user_id,
            date=today,
            cards_done=0,
            reviews_done=0,
            new_done=0,
        )
        db.add(row)
        db.commit()
        db.refresh(row)

    return row

def get_weak_words(
    db: Session,
    user_id: int,
    language_id: int,
    min_seen: int = 3,
    limit: int = 20,
):
    accuracy = (
        (models.UserWord.times_correct * 1.0) /
        func.nullif(models.UserWord.times_seen, 0)
    )

    q = (
        db.query(models.UserWord)
        .join(models.Word, models.Word.id == models.UserWord.word_id)
        .filter(
            models.UserWord.user_id == user_id,
            models.Word.language_id == language_id,
            models.UserWord.times_seen >= min_seen,
        )
        .order_by(
            accuracy.asc()  # lowest accuracy = worst
        )
        .limit(limit)
    )

    return q.all()


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

def get_due_reviews_prioritized(
    db: Session,
    language_id: int,
    user_id: int,
    limit: int,
    strategy: str = "overdue",
):
    """Return due review words with a deterministic priority order.

    strategy:
      - "overdue": most overdue first (next_review asc)
      - "weak": lowest accuracy first, then most overdue
    """
    now = datetime.utcnow()

    q = (
        db.query(models.Word)
        .join(models.UserWord, models.UserWord.word_id == models.Word.id)
        .filter(
            models.Word.owner_id == user_id,
            models.Word.language_id == language_id,
            models.UserWord.user_id == user_id,
            models.UserWord.next_review.isnot(None),
            models.UserWord.next_review <= now,
        )
    )

    if strategy == "weak":
        # accuracy = times_correct / times_seen (lower => weaker). Treat unseen as weakest.
        accuracy = (
            func.coalesce(models.UserWord.times_correct, 0)
            / func.nullif(func.coalesce(models.UserWord.times_seen, 0), 0)
        )
        q = q.order_by(accuracy.asc().nullsfirst(), models.UserWord.next_review.asc())
    else:
        q = q.order_by(models.UserWord.next_review.asc())

    return q.limit(limit).all()


def get_new_words(
    db: Session,
    language_id: int,
    user_id: int,
    exclude_word_ids: list[int] | None,
    limit: int,
):
    """
    Returns words that user has never studied yet.
    """

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
            models.UserWord.id.is_(None),
        )
    )

    if exclude_word_ids:
        q = q.filter(models.Word.id.notin_(exclude_word_ids))

    return (
        q.order_by(models.Word.id.asc())  # deterministic, good for tests
        .limit(limit)
        .all()
    )


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

def count_due_reviews(db: Session, user_id: int, language_id: int) -> int:
    now = datetime.utcnow()
    return (
        db.query(models.UserWord)
        .join(models.Word, models.Word.id == models.UserWord.word_id)
        .filter(
            models.UserWord.user_id == user_id,
            models.Word.language_id == language_id,
            models.UserWord.next_review.isnot(None),
            models.UserWord.next_review <= now,
        )
        .count()
    )


def count_new_available(db: Session, user_id: int, language_id: int) -> int:
    return (
        db.query(models.Word)
        .outerjoin(
            models.UserWord,
            and_(
                models.UserWord.word_id == models.Word.id,
                models.UserWord.user_id == user_id,
            ),
        )
        .filter(
            models.Word.owner_id == user_id,
            models.Word.language_id == language_id,
            models.UserWord.id.is_(None),
        )
        .count()
    )


def get_next_due_at(db: Session, user_id: int, language_id: int):
    return (
        db.query(func.min(models.UserWord.next_review))
        .join(models.Word, models.Word.id == models.UserWord.word_id)
        .filter(
            models.UserWord.user_id == user_id,
            models.Word.language_id == language_id,
            models.UserWord.next_review.isnot(None),
        )
        .scalar()
    )
