from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import List, Optional

from sqlalchemy import and_, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.utils.time import bishkek_day_bounds, bishkek_today

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


# ---------default users language pair


def list_learning_pairs(db: Session, user_id: int):
    return (
        db.query(models.UserLearningPair)
        .filter(models.UserLearningPair.user_id == user_id)
        .order_by(models.UserLearningPair.is_default.desc(), models.UserLearningPair.id.asc())
        .all()
    )


def create_learning_pair(
    db: Session, user_id: int, source_language_id: int, target_language_id: int
):
    pair = models.UserLearningPair(
        user_id=user_id,
        source_language_id=source_language_id,
        target_language_id=target_language_id,
        is_default=False,
    )
    db.add(pair)
    db.commit()
    db.refresh(pair)
    return pair


def get_or_create_main_deck_for_pair(
    db: Session,
    user,
    source_language_id: int,
    target_language_id: int,
) -> models.Deck:

    deck = (
        db.query(models.Deck)
        .filter(
            models.Deck.owner_id == user.id,
            models.Deck.deck_type == "main",
            models.Deck.source_language_id == source_language_id,
            models.Deck.target_language_id == target_language_id,
        )
        .first()
    )

    if deck:
        return deck

    deck = models.Deck(
        name="Main Deck",
        owner_id=user.id,
        deck_type="main",
        source_language_id=source_language_id,
        target_language_id=target_language_id,
    )
    db.add(deck)
    db.flush()

    access = models.DeckAccess(
        deck_id=deck.id,
        user_id=user.id,
        role=models.DeckRole.OWNER,
    )
    db.add(access)

    return deck


def set_default_learning_pair(db: Session, user_id: int, pair_id: int):
    pair = (
        db.query(models.UserLearningPair)
        .filter(
            models.UserLearningPair.user_id == user_id,
            models.UserLearningPair.id == pair_id,
        )
        .first()
    )
    if not pair:
        return None

    # unset others
    db.query(models.UserLearningPair).filter(
        models.UserLearningPair.user_id == user_id,
        models.UserLearningPair.id != pair_id,
    ).update({"is_default": False})

    pair.is_default = True
    db.add(pair)

    # load user once
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return None  # should not happen, but safe

    # sync old fields ONLY if they exist (compat mode)
    if hasattr(user, "default_source_language_id"):
        user.default_source_language_id = pair.source_language_id
    if hasattr(user, "default_target_language_id"):
        user.default_target_language_id = pair.target_language_id
    db.add(user)

    # ensure main deck exists for this default pair
    get_or_create_main_deck_for_pair(
        db,
        user,
        source_language_id=pair.source_language_id,
        target_language_id=pair.target_language_id,
    )

    db.commit()
    db.refresh(pair)
    return pair


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


def update_language(
    db: Session, language_id: int, name: Optional[str] = None, code: Optional[str] = None
) -> Optional[models.Language]:
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


def count_cards_in_deck(db: Session, deck_id: int) -> int:
    return db.query(models.Card).filter(models.Card.deck_id == deck_id).count()


# ----------------- Library (admin-created decks) -----------------


def list_library_decks(
    db: Session,
    *,
    source_language_id: int | None = None,
    target_language_id: int | None = None,
):
    q = (
        db.query(models.Deck)
        .filter(models.Deck.deck_type == "library")
        .order_by(models.Deck.id.desc())
    )
    if source_language_id is not None:
        q = q.filter(models.Deck.source_language_id == source_language_id)
    if target_language_id is not None:
        q = q.filter(models.Deck.target_language_id == target_language_id)
    return q.all()


def list_library_deck_cards(db: Session, deck_id: int, limit: int, offset: int):
    deck = (
        db.query(models.Deck)
        .filter(models.Deck.id == deck_id, models.Deck.deck_type == "library")
        .first()
    )
    if not deck:
        return [], 0

    base_q = (
        db.query(models.Card).filter(models.Card.deck_id == deck_id).order_by(models.Card.id.asc())
    )
    total = base_q.count()
    items = base_q.offset(offset).limit(limit).all()
    return items, total


def import_library_card_to_user_deck(
    db: Session,
    *,
    user_id: int,
    library_card_id: int,
    target_deck_id: int,
):
    """Copy ONE card from a library deck into a user's deck.

    - Library card must belong to a deck with deck_type == "library"
    - User must have OWNER/EDITOR access to target_deck
    - Duplicates are skipped based on (deck_id, front_norm)
    """

    access = require_deck_access(db, user_id, target_deck_id)
    if access.role not in (models.DeckRole.OWNER, models.DeckRole.EDITOR):
        raise PermissionError("No permission to add cards to target deck")

    lib_card = (
        db.query(models.Card)
        .join(models.Deck, models.Deck.id == models.Card.deck_id)
        .filter(models.Card.id == library_card_id, models.Deck.deck_type == "library")
        .first()
    )
    if not lib_card:
        raise LookupError("Library card not found")

    exists = (
        db.query(models.Card.id)
        .filter(
            models.Card.deck_id == target_deck_id, models.Card.front_norm == lib_card.front_norm
        )
        .first()
    )
    if exists:
        return {"imported": False, "skipped": True, "reason": "duplicate", "card": None}

    new_card = models.Card(
        deck_id=target_deck_id,
        front=lib_card.front,
        front_norm=lib_card.front_norm,
        back=lib_card.back,
        example_sentence=lib_card.example_sentence,
    )
    db.add(new_card)
    db.commit()
    db.refresh(new_card)

    return {"imported": True, "skipped": False, "reason": None, "card": new_card}


# ----------------- Decks -----------------


def create_deck(
    db: Session,
    name: str,
    owner_id: int,
    source_language_id: int,
    target_language_id: int,
    *,
    deck_type: str = "users",
) -> models.Deck:
    deck = models.Deck(
        name=name,
        owner_id=owner_id,
        source_language_id=source_language_id,
        target_language_id=target_language_id,
        deck_type=deck_type,
    )
    db.add(deck)
    db.flush()  # get deck.id

    access = models.DeckAccess(deck_id=deck.id, user_id=owner_id, role=models.DeckRole.OWNER)
    db.add(access)

    db.commit()
    db.refresh(deck)
    return deck


def update_deck(
    db: Session,
    *,
    deck_id: int,
    user_id: int,
    name: str | None = None,
    is_public: bool | None = None,
) -> models.Deck:
    access = (
        db.query(models.DeckAccess)
        .filter(models.DeckAccess.deck_id == deck_id, models.DeckAccess.user_id == user_id)
        .first()
    )
    if not access or access.role != models.DeckRole.OWNER:
        raise PermissionError("Only owner can update deck")

    deck = db.query(models.Deck).filter(models.Deck.id == deck_id).first()
    if not deck:
        raise LookupError("Deck not found")

    # 🔒 restriction
    if deck.deck_type != "users":
        raise PermissionError("Only 'users' decks can be updated")

    if name is not None:
        name = name.strip()
        if not name:
            raise ValueError("Name is required")
        deck.name = name

    if is_public is not None:
        deck.is_public = is_public

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

    # Only users decks are deletable by the owner
    if deck.deck_type != "users":
        raise PermissionError("Only 'users' decks can be deleted")

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


def get_user_decks(
    db: Session,
    user_id: int,
    limit: int,
    offset: int,
):
    base_q = (
        db.query(models.Deck)
        .join(models.DeckAccess, models.DeckAccess.deck_id == models.Deck.id)
        .filter(models.DeckAccess.user_id == user_id)
        .order_by(models.Deck.id.desc())
    )

    total = base_q.count()
    items = base_q.offset(offset).limit(limit).all()

    return items, total


def card_exists_in_deck(db: Session, deck_id: int, front: str) -> bool:
    fn = normalize_front(front)
    return (
        db.query(models.Card.id)
        .filter(models.Card.deck_id == deck_id, models.Card.front_norm == fn)
        .first()
        is not None
    )


# ----------------- Cards -----------------


def normalize_front(text: str) -> str:
    # lower, trim, collapse spaces
    return re.sub(r"\s+", " ", (text or "").strip()).lower()


from app.services import auto_content


def create_card(
    db: Session,
    deck_id: int,
    user_id: int,
    front: str,
    back: str,
    example_sentence: Optional[str] = None,
    *,
    auto_fill: bool = True,
) -> models.Card:
    access = require_deck_access(db, user_id, deck_id)
    deck = access.deck
    if access.role not in (models.DeckRole.OWNER, models.DeckRole.EDITOR):
        raise ValueError("No permission to edit deck")
    if access.deck.deck_type == "library":
        raise PermissionError("Library decks are read-only")

    front_clean = (front or "").strip()
    if not front_clean:
        raise ValueError("Front is required")

    front_norm = normalize_front(front_clean)

    # Auto-fill ONLY if allowed
    if auto_fill:
        if not (back or "").strip():
            src_lang = deck.source_language
            tgt_lang = deck.target_language
            back = (
                auto_content.get_translation_with_cache(
                    db, src_lang=src_lang, tgt_lang=tgt_lang, text_raw=front_clean
                )
                or ""
            )

        if not (example_sentence or "").strip():
            src_lang = deck.source_language
            tgt_lang = deck.target_language
            example_sentence = auto_content.get_example_with_cache(
                db, src_lang=src_lang, tgt_lang=tgt_lang, text_raw=front_clean
            )

    card = models.Card(
        deck_id=deck_id,
        front=front_clean,
        front_norm=front_norm,
        back=(back or "").strip(),
        example_sentence=example_sentence,
    )

    db.add(card)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Duplicate word in this deck")

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


def update_card(
    db: Session,
    deck_id: int,
    card_id: int,
    user_id: int,
    *,
    front: Optional[str] = None,
    back: Optional[str] = None,
    example_sentence: Optional[str] = None,
) -> models.Card:
    access = require_deck_access(db, user_id, deck_id)
    if access.role not in (models.DeckRole.OWNER, models.DeckRole.EDITOR):
        raise PermissionError("No permission to edit deck")
    if access.deck.deck_type == "library":
        raise PermissionError("Library decks are read-only")
    card = (
        db.query(models.Card)
        .filter(models.Card.id == card_id, models.Card.deck_id == deck_id)
        .first()
    )
    if not card:
        raise LookupError("Card not found")

    if front is not None:
        front_clean = (front or "").strip()
        if not front_clean:
            raise ValueError("Front is required")
        card.front = front_clean
        card.front_norm = normalize_front(front_clean)

    if back is not None:
        card.back = (back or "").strip()

    if example_sentence is not None:
        # allow clearing with empty string
        val = (example_sentence or "").strip()
        card.example_sentence = val or None

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Duplicate word in this deck")

    db.refresh(card)
    return card


def delete_card(db: Session, deck_id: int, card_id: int, user_id: int) -> bool:
    access = require_deck_access(db, user_id, deck_id)
    if access.role not in (models.DeckRole.OWNER, models.DeckRole.EDITOR):
        raise PermissionError("No permission to edit deck")
    if access.deck.deck_type == "library":
        raise PermissionError("Library decks are read-only")

    card = (
        db.query(models.Card)
        .filter(models.Card.id == card_id, models.Card.deck_id == deck_id)
        .first()
    )
    if not card:
        return False

    # IMPORTANT: prevent FK issues (UserCardProgress references cards.id)
    db.query(models.UserCardProgress).filter(models.UserCardProgress.card_id == card_id).delete(
        synchronize_session=False
    )

    db.delete(card)
    db.commit()
    return True


def list_deck_cards(
    db: Session,
    deck_id: int,
    user_id: int,
    limit: int,
    offset: int,
):
    require_deck_access(db, user_id, deck_id)

    base_q = (
        db.query(models.Card).filter(models.Card.deck_id == deck_id).order_by(models.Card.id.asc())
    )

    total = base_q.count()
    items = base_q.offset(offset).limit(limit).all()

    return items, total


# ----------------- Study progress (SM-2) -----------------


def get_user_card_progress(
    db: Session, user_id: int, card_id: int
) -> Optional[models.UserCardProgress]:
    return (
        db.query(models.UserCardProgress)
        .filter(
            models.UserCardProgress.user_id == user_id, models.UserCardProgress.card_id == card_id
        )
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
def get_default_learning_pair(db: Session, user_id: int) -> models.UserLearningPair | None:
    return (
        db.query(models.UserLearningPair)
        .filter(
            models.UserLearningPair.user_id == user_id,
            models.UserLearningPair.is_default.is_(True),
        )
        .first()
    )


def get_due_reviews(
    db: Session,
    deck_id: int,
    user_id: int,
    limit: int,
    offset: int,
):
    require_deck_access(db, user_id, deck_id)
    now = datetime.utcnow()

    base_q = (
        db.query(models.Card)
        .join(
            models.UserCardProgress,
            and_(
                models.UserCardProgress.card_id == models.Card.id,
                models.UserCardProgress.user_id == user_id,
            ),
        )
        .filter(
            models.UserCardProgress.user_id == user_id,
            models.Card.deck_id == deck_id,
            models.UserCardProgress.status == "learning",
            models.UserCardProgress.due_at.isnot(None),
            models.UserCardProgress.due_at <= now,
        )
    )

    total = base_q.count()
    items = base_q.offset(offset).limit(limit).all()

    return items, total


def get_new_cards(
    db: Session,
    deck_id: int,
    user_id: int,
    exclude_card_ids: list[int] | None,
    limit: int,
    offset: int,
):
    require_deck_access(db, user_id, deck_id)

    now = datetime.utcnow()

    base_q = (
        db.query(models.Card)
        .outerjoin(
            models.UserCardProgress,
            and_(
                models.UserCardProgress.card_id == models.Card.id,
                models.UserCardProgress.user_id == user_id,
            ),
        )
        .filter(models.Card.deck_id == deck_id)
        .filter(
            or_(
                models.UserCardProgress.id.is_(None),
                and_(
                    models.UserCardProgress.status == "new",
                    or_(
                        models.UserCardProgress.due_at.is_(None),
                        models.UserCardProgress.due_at <= now,
                    ),
                ),
            )
        )
    )

    if exclude_card_ids:
        base_q = base_q.filter(models.Card.id.notin_(exclude_card_ids))

    base_q = base_q.order_by(models.Card.id.asc())

    total = base_q.count()
    items = base_q.offset(offset).limit(limit).all()

    return items, total


# ----------------- Daily counters for quotas -----------------


def _utc_day_start(now: datetime) -> datetime:
    return datetime(now.year, now.month, now.day)


def utc_day_bounds(now: datetime):
    start = datetime(now.year, now.month, now.day)
    end = start + timedelta(days=1)
    return start, end


def count_cards_created_on_day(
    db: Session, user_id: int, d: date, deck_id: int | None = None
) -> int:
    start, end = bishkek_day_bounds(d)

    q = (
        db.query(models.Card)
        .join(models.Deck, models.Deck.id == models.Card.deck_id)  # join Deck for deck_type
        .join(models.DeckAccess, models.DeckAccess.deck_id == models.Card.deck_id)
        .filter(
            models.DeckAccess.user_id == user_id,
            models.Card.created_at >= start,
            models.Card.created_at < end,
        )
    )

    if deck_id is not None:
        q = q.filter(models.Card.deck_id == deck_id, models.Deck.deck_type == "main")
    else:
        # optional: if you ever call without deck_id, you might still want only main
        # q = q.filter(models.Deck.deck_type == "main")
        pass

    return q.count()


def list_cards_created_on_day(
    db: Session,
    user_id: int,
    d: date,
    deck_id: int | None = None,
    limit: int = 50,
):
    start, end = bishkek_day_bounds(d)

    q = (
        db.query(models.Card)
        .join(models.DeckAccess, models.DeckAccess.deck_id == models.Card.deck_id)
        .filter(
            models.DeckAccess.user_id == user_id,
            models.Card.created_at >= start,
            models.Card.created_at < end,
        )
        .order_by(models.Card.created_at.desc())
        .limit(limit)
    )
    if deck_id is not None:
        q = q.filter(models.Card.deck_id == deck_id)
    return q.all()


def get_daily_progress_filled(
    db: Session,
    user_id: int,
    learning_pair_id: int,
    from_date: date,
    to_date: date,
):
    rows = get_daily_progress(db, user_id, learning_pair_id, from_date, to_date)
    by_date = {r.date: r for r in rows}

    cur = from_date
    out = []
    while cur <= to_date:
        r = by_date.get(cur)
        if r:
            out.append(r)
        else:
            out.append(
                models.DailyProgress(
                    user_id=user_id,
                    learning_pair_id=learning_pair_id,
                    date=cur,
                    cards_done=0,
                    reviews_done=0,
                    new_done=0,
                )
            )
        cur += timedelta(days=1)
    return out


def get_streak(
    db: Session, user_id: int, learning_pair_id: int, *, threshold: int = 10
) -> dict:  # use Bishkek day
    today = bishkek_today()
    from_date = today - timedelta(days=400)

    rows = (
        db.query(models.DailyProgress)
        .filter(
            models.DailyProgress.user_id == user_id,
            models.DailyProgress.learning_pair_id == learning_pair_id,
            models.DailyProgress.date >= from_date,
            models.DailyProgress.date <= today,
            models.DailyProgress.cards_done >= threshold,
        )
        .order_by(models.DailyProgress.date.asc())
        .all()
    )
    active = {r.date for r in rows}

    def best_streak(active_dates: set[date]) -> int:
        if not active_dates:
            return 0
        best = 0
        for d in sorted(active_dates):
            if (d - timedelta(days=1)) not in active_dates:
                run = 1
                nxt = d + timedelta(days=1)
                while nxt in active_dates:
                    run += 1
                    nxt += timedelta(days=1)
                best = max(best, run)
        return best

    # streak can end today if today is active, else end yesterday if active
    end = today if today in active else (today - timedelta(days=1))
    if end not in active:
        return {"current_streak": 0, "best_streak": best_streak(active), "threshold": threshold}

    cur = 0
    d = end
    while d in active:
        cur += 1
        d = d - timedelta(days=1)

    return {"current_streak": cur, "best_streak": best_streak(active), "threshold": threshold}


def _best_streak(active_dates: set[date]) -> int:
    if not active_dates:
        return 0
    best = 0
    for d in sorted(active_dates):
        # compute streak start at d
        if (d - timedelta(days=1)) not in active_dates:
            run = 1
            nxt = d + timedelta(days=1)
            while nxt in active_dates:
                run += 1
                nxt += timedelta(days=1)
            best = max(best, run)
    return best


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
            models.UserCardProgress.status == "learning",
            models.UserCardProgress.due_at.isnot(None),
            models.UserCardProgress.due_at <= now,
        )
        .count()
    )


def count_new_available(db: Session, user_id: int, deck_id: int) -> int:
    now = datetime.utcnow()

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
            or_(
                models.UserCardProgress.id.is_(None),
                and_(
                    models.UserCardProgress.status == "new",
                    or_(
                        models.UserCardProgress.due_at.is_(None),
                        models.UserCardProgress.due_at <= now,
                    ),
                ),
            ),
        )
        .count()
    )


def get_next_due_at(db: Session, user_id: int, deck_id: int):
    return (
        db.query(func.min(models.UserCardProgress.due_at))
        .join(models.Card, models.Card.id == models.UserCardProgress.card_id)
        .filter(
            models.UserCardProgress.user_id == user_id,
            models.Card.deck_id == deck_id,
            models.UserCardProgress.status == "learning",
            models.UserCardProgress.due_at.isnot(None),
        )
        .scalar()
    )


# ----------------- Daily progress row -----------------
def get_or_create_daily_progress(
    db: Session, *, user_id: int, learning_pair_id: int, day: date
) -> models.DailyProgress:
    row = (
        db.query(models.DailyProgress)
        .filter(
            models.DailyProgress.user_id == user_id,
            models.DailyProgress.learning_pair_id == learning_pair_id,
            models.DailyProgress.date == day,
        )
        .first()
    )
    if row:
        return row

    row = models.DailyProgress(user_id=user_id, learning_pair_id=learning_pair_id, date=day)
    db.add(row)
    db.flush()
    return row


def get_daily_progress(
    db: Session,
    user_id: int,
    learning_pair_id: int,
    from_date: date,
    to_date: date,
):
    if from_date > to_date:
        raise ValueError("from_date must be <= to_date")

    return (
        db.query(models.DailyProgress)
        .filter(
            models.DailyProgress.user_id == user_id,
            models.DailyProgress.learning_pair_id == learning_pair_id,
            models.DailyProgress.date >= from_date,
            models.DailyProgress.date <= to_date,
        )
        .order_by(models.DailyProgress.date.asc())
        .all()
    )


def get_daily_progress_for_day(
    db: Session,
    user_id: int,
    learning_pair_id: int,
    day: date,
):
    row = (
        db.query(models.DailyProgress)
        .filter(
            models.DailyProgress.user_id == user_id,
            models.DailyProgress.learning_pair_id == learning_pair_id,
            models.DailyProgress.date == day,
        )
        .first()
    )
    if row:
        return row

    return models.DailyProgress(
        user_id=user_id,
        learning_pair_id=learning_pair_id,
        date=day,
        cards_done=0,
        reviews_done=0,
        new_done=0,
    )


def count_total_cards(db: Session, user_id: int, deck_id: int | None = None) -> int:
    q = (
        db.query(models.Card)
        .join(models.DeckAccess, models.DeckAccess.deck_id == models.Card.deck_id)
        .filter(models.DeckAccess.user_id == user_id)
    )
    if deck_id is not None:
        q = q.filter(models.Card.deck_id == deck_id)
    return q.count()


def count_progress_statuses(db: Session, user_id: int, deck_id: int | None = None) -> dict:
    # mastered + learning from progress rows
    q = (
        db.query(models.UserCardProgress.status, func.count(models.UserCardProgress.id))
        .join(models.Card, models.Card.id == models.UserCardProgress.card_id)
        .filter(models.UserCardProgress.user_id == user_id)
    )
    if deck_id is not None:
        q = q.filter(models.Card.deck_id == deck_id)

    rows = q.group_by(models.UserCardProgress.status).all()
    counts = {"mastered": 0, "learning": 0, "new": 0}
    for status, c in rows:
        if status in counts:
            counts[status] = int(c)

    # new cards also include cards without any progress row
    q2 = (
        db.query(models.Card)
        .outerjoin(
            models.UserCardProgress,
            and_(
                models.UserCardProgress.card_id == models.Card.id,
                models.UserCardProgress.user_id == user_id,
            ),
        )
        .join(models.DeckAccess, models.DeckAccess.deck_id == models.Card.deck_id)
        .filter(
            models.DeckAccess.user_id == user_id,
            models.UserCardProgress.id.is_(None),
        )
    )
    if deck_id is not None:
        q2 = q2.filter(models.Card.deck_id == deck_id)

    counts["new"] += q2.count()
    return counts
