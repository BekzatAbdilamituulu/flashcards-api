
from __future__ import annotations

from datetime import datetime, date
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from sqlalchemy.exc import IntegrityError

from . import models


# ----------------- Permissions -----------------

# ----------------- Users (Auth) -----------------

def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.username == username).first()


def create_user(db: Session, username: str, hashed_password: str) -> models.User:
    user = models.User(username=username, hashed_password=hashed_password)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(user)
    return user


# ----------------- Languages (global/admin) -----------------

def list_languages(db: Session) -> List[models.Language]:
    return db.query(models.Language).order_by(models.Language.name.asc()).all()


def create_language(db: Session, name: str, code: Optional[str] = None) -> models.Language:
    lang = models.Language(name=name, code=code)
    db.add(lang)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(lang)
    return lang


def update_language(db: Session, language_id: int, name: Optional[str] = None, code: Optional[str] = None) -> Optional[models.Language]:
    lang = db.query(models.Language).filter(models.Language.id == language_id).first()
    if not lang:
        return None
    if name is not None:
        lang.name = name
    if code is not None:
        lang.code = code
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(lang)
    return lang


def delete_language(db: Session, language_id: int) -> bool:
    lang = db.query(models.Language).filter(models.Language.id == language_id).first()
    if not lang:
        return False

    used = (
        db.query(models.Deck)
        .filter(
            (models.Deck.source_language_id == language_id)
            | (models.Deck.target_language_id == language_id)
        )
        .first()
    )
    if used:
        raise ValueError("Language is used by a deck")

    db.delete(lang)
    db.commit()
    return True

def require_deck_access(db: Session, user_id: int, deck_id: int) -> models.DeckAccess:
    row = (
        db.query(models.DeckAccess)
        .filter(models.DeckAccess.user_id == user_id, models.DeckAccess.deck_id == deck_id)
        .first()
    )
    if not row:
        raise ValueError("No access to deck")
    return row


# ----------------- Decks -----------------

def create_deck(db: Session, name: str, owner_id: int, source_language_id: int, target_language_id: int) -> models.Deck:
    deck = models.Deck(
        name=name,
        owner_id=owner_id,
        source_language_id=source_language_id,
        target_language_id=target_language_id,
    )
    db.add(deck)
    db.flush()  # get deck.id

    # creator access
    access = models.DeckAccess(deck_id=deck.id, user_id=owner_id, role=models.DeckRole.OWNER)
    db.add(access)

    db.commit()
    db.refresh(deck)
    return deck


def delete_deck(db: Session, deck_id: int, user_id: int) -> bool:
    access = (
        db.query(models.DeckAccess)
        .filter(models.DeckAccess.user_id == user_id, models.DeckAccess.deck_id == deck_id)
        .first()
    )
    if not access or access.role != models.DeckRole.OWNER:
        return False

    deck = db.query(models.Deck).filter(models.Deck.id == deck_id).first()
    if not deck:
        return False

    db.delete(deck)
    db.commit()
    return True


def get_deck(db: Session, deck_id: int, user_id: int) -> Optional[models.Deck]:
    # any access is enough to read
    q = (
        db.query(models.Deck)
        .join(models.DeckAccess, models.DeckAccess.deck_id == models.Deck.id)
        .filter(models.Deck.id == deck_id, models.DeckAccess.user_id == user_id)
    )
    return q.first()


def get_user_decks(db: Session, user_id: int) -> List[models.Deck]:
    return (
        db.query(models.Deck)
        .join(models.DeckAccess, models.DeckAccess.deck_id == models.Deck.id)
        .filter(models.DeckAccess.user_id == user_id)
        .order_by(models.Deck.id.desc())
        .all()
    )


def set_deck_share_code(db: Session, deck_id: int, user_id: int, shared_code: str) -> Optional[models.Deck]:
    access = (
        db.query(models.DeckAccess)
        .filter(models.DeckAccess.user_id == user_id, models.DeckAccess.deck_id == deck_id)
        .first()
    )
    if not access or access.role != models.DeckRole.OWNER:
        return None

    deck = db.query(models.Deck).filter(models.Deck.id == deck_id).first()
    if not deck:
        return None

    deck.shared_code = shared_code
    deck.status = models.DeckStatus.PUBLISHED
    deck.is_public = True

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(deck)
    return deck


def join_deck_by_code(db: Session, user_id: int, shared_code: str) -> Optional[models.DeckAccess]:
    deck = db.query(models.Deck).filter(models.Deck.shared_code == shared_code).first()
    if not deck:
        return None

    existing = (
        db.query(models.DeckAccess)
        .filter(models.DeckAccess.user_id == user_id, models.DeckAccess.deck_id == deck.id)
        .first()
    )
    if existing:
        return existing

    access = models.DeckAccess(deck_id=deck.id, user_id=user_id, role=models.DeckRole.VIEWER)
    db.add(access)
    db.commit()
    db.refresh(access)
    return access


# ----------------- Cards -----------------

def create_card(db: Session, deck_id: int, user_id: int, front: str, back: str, example_sentence: Optional[str] = None) -> models.Card:
    access = require_deck_access(db, user_id, deck_id)
    if access.role not in (models.DeckRole.OWNER, models.DeckRole.EDITOR):
        raise ValueError("No permission to edit deck")

    card = models.Card(deck_id=deck_id, front=front, back=back, example_sentence=example_sentence)
    db.add(card)
    db.commit()
    db.refresh(card)
    return card


def get_card(db: Session, card_id: int, user_id: int) -> Optional[models.Card]:
    # ensure the card is in a deck the user can access
    q = (
        db.query(models.Card)
        .join(models.DeckAccess, models.DeckAccess.deck_id == models.Card.deck_id)
        .filter(models.Card.id == card_id, models.DeckAccess.user_id == user_id)
    )
    return q.first()


def list_deck_cards(db: Session, deck_id: int, user_id: int) -> List[models.Card]:
    require_deck_access(db, user_id, deck_id)
    return (
        db.query(models.Card)
        .filter(models.Card.deck_id == deck_id)
        .order_by(models.Card.id.asc())
        .all()
    )


# ----------------- Study progress (SM-2) -----------------

def get_user_card_progress(db: Session, user_id: int, card_id: int) -> Optional[models.UserCardProgress]:
    return (
        db.query(models.UserCardProgress)
        .filter(models.UserCardProgress.user_id == user_id, models.UserCardProgress.card_id == card_id)
        .first()
    )


def create_user_card_progress(db: Session, user_id: int, card_id: int) -> models.UserCardProgress:
    rec = models.UserCardProgress(
        user_id=user_id,
        card_id=card_id,
        times_seen=0,
        times_correct=0,
        last_review=None,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


# ----------------- Study selection queries -----------------

def get_due_reviews(db: Session, deck_id: int, user_id: int, limit: int):
    """
    Due cards in one deck for this user.
    """
    require_deck_access(db, user_id, deck_id)
    now = datetime.utcnow()

    return (
        db.query(models.Card)
        .join(
            models.UserCardProgress,
            and_(
                models.UserCardProgress.card_id == models.Card.id,
                models.UserCardProgress.user_id == user_id,
            ),
        )
        .filter(
            models.Card.deck_id == deck_id,
            models.UserCardProgress.next_review.isnot(None),
            models.UserCardProgress.next_review <= now,
        )
        .order_by(models.UserCardProgress.next_review.asc())
        .limit(limit)
        .all()
    )


def get_new_words(
    db: Session,
    deck_id: int,
    user_id: int,
    exclude_card_ids: list[int] | None,
    limit: int,
):
    """
    Cards in the deck that user has never studied yet (no progress row).
    """
    require_deck_access(db, user_id, deck_id)

    q = (
        db.query(models.Card)
        .outerjoin(
            models.UserCardProgress,
            and_(
                models.UserCardProgress.card_id == models.Card.id,
                models.UserCardProgress.user_id == user_id,
            ),
        )
        .filter(
            models.Card.deck_id == deck_id,
            models.UserCardProgress.id.is_(None),
        )
    )

    if exclude_card_ids:
        q = q.filter(models.Card.id.notin_(exclude_card_ids))

    return q.order_by(models.Card.id.asc()).limit(limit).all()


# ----------------- Daily counters for quotas -----------------

def _utc_day_start(now: datetime) -> datetime:
    return datetime(now.year, now.month, now.day)


def count_reviewed_today(db: Session, user_id: int, deck_id: int) -> int:
    now = datetime.utcnow()
    start = _utc_day_start(now)

    return (
        db.query(models.UserCardProgress)
        .join(models.Card, models.Card.id == models.UserCardProgress.card_id)
        .filter(
            models.UserCardProgress.user_id == user_id,
            models.Card.deck_id == deck_id,
            models.UserCardProgress.last_review.isnot(None),
            models.UserCardProgress.last_review >= start,
        )
        .count()
    )


def count_new_introduced_today(db: Session, user_id: int, deck_id: int) -> int:
    now = datetime.utcnow()
    start = _utc_day_start(now)

    return (
        db.query(models.UserCardProgress)
        .join(models.Card, models.Card.id == models.UserCardProgress.card_id)
        .filter(
            models.UserCardProgress.user_id == user_id,
            models.Card.deck_id == deck_id,
            models.UserCardProgress.times_seen == 1,
            models.UserCardProgress.last_review.isnot(None),
            models.UserCardProgress.last_review >= start,
        )
        .count()
    )


def count_due_reviews(db: Session, user_id: int, deck_id: int) -> int:
    now = datetime.utcnow()

    return (
        db.query(models.UserCardProgress)
        .join(models.Card, models.Card.id == models.UserCardProgress.card_id)
        .filter(
            models.UserCardProgress.user_id == user_id,
            models.Card.deck_id == deck_id,
            models.UserCardProgress.next_review.isnot(None),
            models.UserCardProgress.next_review <= now,
        )
        .count()
    )


def count_new_available(db: Session, user_id: int, deck_id: int) -> int:
    return (
        db.query(models.Card)
        .outerjoin(
            models.UserCardProgress,
            and_(
                models.UserCardProgress.card_id == models.Card.id,
                models.UserCardProgress.user_id == user_id,
            ),
        )
        .filter(
            models.Card.deck_id == deck_id,
            models.UserCardProgress.id.is_(None),
        )
        .count()
    )


def get_next_due_at(db: Session, user_id: int, deck_id: int):
    return (
        db.query(func.min(models.UserCardProgress.next_review))
        .join(models.Card, models.Card.id == models.UserCardProgress.card_id)
        .filter(
            models.UserCardProgress.user_id == user_id,
            models.Card.deck_id == deck_id,
            models.UserCardProgress.next_review.isnot(None),
        )
        .scalar()
    )


# ----------------- Daily progress row -----------------

def get_or_create_daily_progress(db: Session, user_id: int) -> models.DailyProgress:
    today = date.today()

    row = (
        db.query(models.DailyProgress)
        .filter(models.DailyProgress.user_id == user_id, models.DailyProgress.date == today)
        .first()
    )

    if not row:
        row = models.DailyProgress(user_id=user_id, date=today, cards_done=0, reviews_done=0, new_done=0)
        db.add(row)
        db.commit()
        db.refresh(row)

    return row