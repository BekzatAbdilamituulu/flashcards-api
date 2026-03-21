from __future__ import annotations

import re
import secrets
from datetime import date, datetime, timedelta
from typing import List, Optional

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload

from app.utils.time import bishkek_day_bounds, bishkek_today
from .deps import is_admin_username

from . import models, schemas

# ----------------- Permissions -----------------

# ----------------- Users (Auth) -----------------

def require_deck_access(db: Session, user_id: int, deck_id: int) -> models.DeckAccess:
    row = (
        db.query(models.DeckAccess)
        .filter(models.DeckAccess.user_id == user_id, models.DeckAccess.deck_id == deck_id)
        .first()
    )
    if not row:
        raise PermissionError("No access to deck")
    return row

def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_google_sub(db: Session, google_sub: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.google_sub == google_sub).first()


def create_user(
    db: Session,
    username: str,
    hashed_password: str,
    *,
    email: str | None = None,
    google_sub: str | None = None,
    email_verified: bool = False,
) -> models.User:
    user = models.User(
        username=username,
        hashed_password=hashed_password,
        email=email,
        google_sub=google_sub,
        email_verified=email_verified,
    )
    db.add(user)
    db.flush()
    db.refresh(user)
    return user


def _normalize_username_candidate(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9_]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "user"


def generate_unique_username(db: Session, email: str) -> str:
    local_part = email.split("@", 1)[0]
    base = _normalize_username_candidate(local_part)

    for suffix in range(0, 1000):
        candidate = base if suffix == 0 else f"{base}_{suffix}"
        if not get_user_by_username(db, candidate):
            return candidate

    while True:
        candidate = f"{base}_{secrets.token_hex(3)}"
        if not get_user_by_username(db, candidate):
            return candidate

def get_user_learning_pair(
    db: Session,
    user_id: int,
    pair_id: int | None = None,
) -> models.UserLearningPair:
    if pair_id is not None:
        pair = (
            db.query(models.UserLearningPair)
            .filter(
                models.UserLearningPair.id == pair_id,
                models.UserLearningPair.user_id == user_id,
            )
            .first()
        )
        if not pair:
            raise ValueError("Learning pair not found")
        return pair

    pair = (
        db.query(models.UserLearningPair)
        .filter(
            models.UserLearningPair.user_id == user_id,
            models.UserLearningPair.is_default == True,
        )
        .first()
    )
    if not pair:
        raise ValueError("Default learning pair not found")
    return pair

def get_user_learning_pair_by_langs(
    db: Session,
    user_id: int,
    source_language_id: int,
    target_language_id: int,
):
    return (
        db.query(models.UserLearningPair)
        .filter(
            models.UserLearningPair.user_id == user_id,
            models.UserLearningPair.source_language_id == source_language_id,
            models.UserLearningPair.target_language_id == target_language_id,
        )
        .first()
    )


def normalize_content_kind(
    content_kind: str | models.ContentKind | schemas.ContentKind | None,
) -> models.ContentKind:
    if content_kind is None:
        return models.ContentKind.WORD
    if isinstance(content_kind, models.ContentKind):
        return content_kind
    if isinstance(content_kind, schemas.ContentKind):
        return models.ContentKind(content_kind.value)

    value = str(content_kind).strip().lower() or models.ContentKind.WORD.value
    return models.ContentKind(value)

# ---------default users language pair


def list_learning_pairs(db: Session, user_id: int):
    return (
        db.query(models.UserLearningPair)
        .options(
            joinedload(models.UserLearningPair.source_language),
            joinedload(models.UserLearningPair.target_language),
        )
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
    db.flush()
    return (
        db.query(models.UserLearningPair)
        .options(
            joinedload(models.UserLearningPair.source_language),
            joinedload(models.UserLearningPair.target_language),
        )
        .filter(models.UserLearningPair.id == pair.id)
        .first()
    )


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
            models.Deck.deck_type == models.DeckType.MAIN,
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
        deck_type=models.DeckType.MAIN,
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
        .options(
            joinedload(models.UserLearningPair.source_language),
            joinedload(models.UserLearningPair.target_language),
        )
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

    db.flush()
    return (
        db.query(models.UserLearningPair)
        .options(
            joinedload(models.UserLearningPair.source_language),
            joinedload(models.UserLearningPair.target_language),
        )
        .filter(models.UserLearningPair.id == pair.id)
        .first()
    )


# ----------------- Languages (global/admin) -----------------
def list_languages(db: Session) -> List[models.Language]:
    return db.query(models.Language).order_by(models.Language.name.asc()).all()


def create_language(db: Session, name: str, code: Optional[str] = None) -> models.Language:
    lang = models.Language(name=name, code=code)
    db.add(lang)
    db.flush()
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
    db.flush()
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
    db.flush()
    return True

def count_cards_in_deck(db: Session, deck_id: int) -> int:
    return db.query(models.Card).filter(models.Card.deck_id == deck_id).count()


# ----------------- Library (admin-created decks) -----------------


def list_library_decks(
    db: Session,
    user_id: int,
    limit: int,
    offset: int,
    pair_id: int | None = None,
):
    pair = get_user_learning_pair(db, user_id, pair_id)

    base_q = (
        db.query(models.Deck)
        .filter(
            models.Deck.deck_type == models.DeckType.LIBRARY,
            models.Deck.source_language_id == pair.source_language_id,
            models.Deck.target_language_id == pair.target_language_id,
        )
        .order_by(models.Deck.id.desc())
    )

    total = base_q.count()
    items = base_q.offset(offset).limit(limit).all()
    return items, total

def get_library_deck_for_import(db: Session, library_deck_id: int) -> models.Deck | None:
    return (
        db.query(models.Deck)
        .filter(
            models.Deck.id == library_deck_id,
            models.Deck.deck_type == models.DeckType.LIBRARY,
        )
        .first()
    )


def get_card_for_library_import(db: Session, library_card_id: int) -> models.Card | None:
    return (
        db.query(models.Card)
        .join(models.Deck, models.Deck.id == models.Card.deck_id)
        .filter(
            models.Card.id == library_card_id,
            models.Deck.deck_type == models.DeckType.LIBRARY,
        )
        .first()
    )

def list_library_deck_cards(
    db: Session,
    deck_id: int,
    limit: int,
    offset: int,
    *,
    reading_source_id: int | None = None,
    user_id: int | None = None,
):
    deck = (
        db.query(models.Deck)
        .filter(models.Deck.id == deck_id, models.Deck.deck_type == models.DeckType.LIBRARY)
        .first()
    )
    if not deck:
        return [], 0

    if reading_source_id is not None:
        if user_id is None:
            raise ValueError("user_id is required for reading_source filter")
        source = (
            db.query(models.ReadingSource)
            .filter(
                models.ReadingSource.id == reading_source_id,
                models.ReadingSource.user_id == user_id,
            )
            .first()
        )
        if not source:
            raise LookupError("Reading source not found")
        pair = (
            db.query(models.UserLearningPair)
            .filter(
                models.UserLearningPair.id == source.pair_id,
                models.UserLearningPair.user_id == user_id,
            )
            .first()
        )
        if not pair:
            raise LookupError("Reading source not found")
        if (
            pair.source_language_id != deck.source_language_id
            or pair.target_language_id != deck.target_language_id
        ):
            raise ValueError("Reading source pair does not match deck pair")

    base_q = (
        db.query(models.Card)
        .options(joinedload(models.Card.reading_source))
        .filter(models.Card.deck_id == deck_id)
        .order_by(models.Card.id.asc())
    )
    if reading_source_id is not None:
        base_q = base_q.filter(models.Card.reading_source_id == reading_source_id)

    total = base_q.count()
    items = base_q.offset(offset).limit(limit).all()
    return items, total


def import_library_card_to_user_deck(
    db: Session,
    user_id: int,
    library_card_id: int,
    target_deck_id: int,
):
    lib_card = (
        db.query(models.Card)
        .join(models.Deck, models.Deck.id == models.Card.deck_id)
        .filter(models.Card.id == library_card_id)
        .first()
    )
    if not lib_card:
        raise LookupError("Library card not found")

    if lib_card.deck.deck_type != models.DeckType.LIBRARY:
        raise ValueError("Card is not from a library deck")

    access = require_deck_access(db, user_id, target_deck_id)
    if access.role not in (models.DeckRole.OWNER, models.DeckRole.EDITOR):
        raise PermissionError("No permission to add cards to target deck")

    target_deck = access.deck
    if target_deck.deck_type not in (models.DeckType.USERS, models.DeckType.MAIN):
        raise ValueError("Cards can be imported only into user study decks")

    if (
        lib_card.deck.source_language_id != target_deck.source_language_id
        or lib_card.deck.target_language_id != target_deck.target_language_id
    ):
        raise ValueError("Library card language pair does not match target deck")

    existing = (
        db.query(models.Card)
        .filter(
            models.Card.deck_id == target_deck_id,
            models.Card.front_norm == lib_card.front_norm,
        )
        .first()
    )
    if existing:
        return {
            "imported": False,
            "skipped": True,
            "reason": "duplicate",
            "card": existing,
        }

    new_card = models.Card(
        deck_id=target_deck_id,
        front=lib_card.front,
        front_norm=lib_card.front_norm,
        back=lib_card.back,
        example_sentence=lib_card.example_sentence,
        content_kind=lib_card.content_kind,
        source_title=lib_card.source_title,
        source_author=lib_card.source_author,
        source_reference=lib_card.source_reference,
        source_sentence=lib_card.source_sentence,
        source_page=lib_card.source_page,
        context_note=lib_card.context_note,
    )
    db.add(new_card)
    db.flush()
    db.refresh(new_card)

    return {
        "imported": True,
        "skipped": False,
        "reason": None,
        "card": new_card,
    }

def import_selected_library_cards_to_user_deck(
    db: Session,
    user_id: int,
    library_deck_id: int,
    target_deck_id: int,
    card_ids: list[int],
):
    deck = db.query(models.Deck).filter(models.Deck.id == library_deck_id).first()
    if not deck:
        raise LookupError("Library deck not found")
    if deck.deck_type != models.DeckType.LIBRARY:
        raise ValueError("Deck is not a library deck")

    results = []
    imported_count = 0
    skipped_count = 0

    for card_id in card_ids:
        lib_card = (
            db.query(models.Card)
            .filter(
                models.Card.id == card_id,
                models.Card.deck_id == library_deck_id,
            )
            .first()
        )
        if not lib_card:
            results.append(
                {
                    "library_card_id": card_id,
                    "imported": False,
                    "skipped": True,
                    "reason": "card_not_in_library_deck",
                    "card": None,
                }
            )
            skipped_count += 1
            continue

        try:
            out = import_library_card_to_user_deck(
                db,
                user_id=user_id,
                library_card_id=card_id,
                target_deck_id=target_deck_id,
            )
            results.append(
                {
                    "library_card_id": card_id,
                    "imported": out["imported"],
                    "skipped": out["skipped"],
                    "reason": out.get("reason"),
                    "card": out.get("card"),
                }
            )
            if out["imported"]:
                imported_count += 1
            else:
                skipped_count += 1
        except (ValueError, PermissionError, LookupError) as e:
            results.append(
                {
                    "library_card_id": card_id,
                    "imported": False,
                    "skipped": True,
                    "reason": str(e),
                    "card": None,
                }
            )
            skipped_count += 1

    return {
        "results": results,
        "imported_count": imported_count,
        "skipped_count": skipped_count,
    }

# ----------------- Decks -----------------


def create_deck(
    db: Session,
    name: str,
    owner_id: int,
    source_language_id: int,
    target_language_id: int,
    *,
    deck_type: models.DeckType = models.DeckType.USERS,
    source_type: str | None = None,
    author_name: str | None = None,
) -> models.Deck:
    deck = models.Deck(
        name=name,
        owner_id=owner_id,
        source_language_id=source_language_id,
        target_language_id=target_language_id,
        deck_type=deck_type,
        source_type=source_type,
        author_name=author_name,
    )
    db.add(deck)
    db.flush()  # get deck.id

    access = models.DeckAccess(deck_id=deck.id, user_id=owner_id, role=models.DeckRole.OWNER)
    db.add(access)
    db.flush()
    db.refresh(deck)
    return deck


def update_deck(
    db: Session,
    *,
    deck_id: int,
    user_id: int,
    name: str | None = None,
    is_public: bool | None = None,
    source_type: str | None = None,
    author_name: str | None = None,
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
    if deck.deck_type != models.DeckType.USERS:
        raise PermissionError("Only 'users' decks can be updated")

    if name is not None:
        name = name.strip()
        if not name:
            raise ValueError("Name is required")
        deck.name = name

    if is_public is not None:
        deck.is_public = is_public
    if source_type is not None:
        deck.source_type = source_type
    if author_name is not None:
        deck.author_name = author_name

    db.flush()
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
    if deck.deck_type != models.DeckType.USERS:
        raise PermissionError("Only 'users' decks can be deleted")

    db.delete(deck)
    db.flush()
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
    pair_id: int | None = None,
):
    base_q = (
        db.query(models.Deck)
        .join(models.DeckAccess, models.DeckAccess.deck_id == models.Deck.id)
        .filter(models.DeckAccess.user_id == user_id)
    )

    if pair_id is not None:
        pair = get_user_learning_pair(db, user_id, pair_id)
        base_q = base_q.filter(
            models.Deck.source_language_id == pair.source_language_id,
            models.Deck.target_language_id == pair.target_language_id,
        )

    base_q = base_q.order_by(models.Deck.id.desc())

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


def _resolve_reading_source_for_deck(
    db: Session,
    *,
    user_id: int,
    deck: models.Deck,
    reading_source_id: int | None,
) -> models.ReadingSource | None:
    if reading_source_id is None:
        return None

    source = (
        db.query(models.ReadingSource)
        .filter(
            models.ReadingSource.id == reading_source_id,
            models.ReadingSource.user_id == user_id,
        )
        .first()
    )
    if not source:
        raise LookupError("Reading source not found")

    pair = (
        db.query(models.UserLearningPair)
        .filter(
            models.UserLearningPair.id == source.pair_id,
            models.UserLearningPair.user_id == user_id,
        )
        .first()
    )
    if not pair:
        raise LookupError("Reading source not found")

    if (
        pair.source_language_id != deck.source_language_id
        or pair.target_language_id != deck.target_language_id
    ):
        raise ValueError("Reading source pair does not match deck pair")

    return source


def create_card(
    db: Session,
    deck_id: int,
    user_id: int,
    front: str,
    back: str,
    example_sentence: Optional[str] = None,
    content_kind: str | models.ContentKind | schemas.ContentKind | None = None,
    reading_source_id: Optional[int] = None,
    source_title: Optional[str] = None,
    source_author: Optional[str] = None,
    source_kind: Optional[str] = None,
    source_reference: Optional[str] = None,
    source_sentence: Optional[str] = None,
    source_page: Optional[str] = None,
    context_note: Optional[str] = None,
    *,
    auto_fill: bool = True,
) -> models.Card:
    access = require_deck_access(db, user_id, deck_id)
    deck = access.deck
    if access.role not in (models.DeckRole.OWNER, models.DeckRole.EDITOR):
        raise PermissionError("No permission to edit deck")
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    is_admin = user is not None and is_admin_username(user.username)

    if deck.deck_type == models.DeckType.LIBRARY and not is_admin:
        raise PermissionError("Library decks are read only")
    reading_source = _resolve_reading_source_for_deck(
        db,
        user_id=user_id,
        deck=deck,
        reading_source_id=reading_source_id,
    )
    if reading_source is None and (source_title or "").strip():
        from app.services.reading_source_service import resolve_or_create_reading_source

        pair = get_user_learning_pair_by_langs(
            db,
            user_id=user_id,
            source_language_id=deck.source_language_id,
            target_language_id=deck.target_language_id,
        )
        if pair:
            reading_source = resolve_or_create_reading_source(
                db,
                user_id=user_id,
                pair_id=pair.id,
                source_title=source_title,
                source_author=source_author,
                source_kind=source_kind,
                source_reference=source_reference,
                create_if_missing=True,
            )

    front_clean = (front or "").strip()
    if not front_clean:
        raise ValueError("Front is required")

    front_norm = normalize_front(front_clean)
    existing = (
        db.query(models.Card.id)
        .filter(models.Card.deck_id == deck_id, models.Card.front_norm == front_norm)
        .first()
    )
    if existing:
        raise ValueError("Duplicate word in this deck")

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
    back_clean = auto_content.clean_text(back)
    example_clean = auto_content.clean_example(example_sentence)
    source_title_clean = auto_content.clean_text(source_title)
    source_author_clean = auto_content.clean_text(source_author)
    source_reference_clean = auto_content.clean_text(source_reference)
    source_sentence_clean = auto_content.clean_text(source_sentence)
    context_note_clean = auto_content.clean_text(context_note)
    content_kind_clean = normalize_content_kind(content_kind)
    source_page_clean = (source_page or "").strip() or None
    source_title_final = source_title_clean or (reading_source.title if reading_source else None)
    source_author_final = source_author_clean or (reading_source.author if reading_source else None)
    source_reference_final = source_reference_clean or (
        reading_source.reference if reading_source else None
    )
    if source_kind is not None and reading_source is not None:
        reading_source.kind = auto_content.clean_text(source_kind) or None
    card = models.Card(
        deck_id=deck_id,
        front=front_clean,
        front_norm=front_norm,
        back=back_clean,
        example_sentence=example_clean,
        content_kind=content_kind_clean,
        reading_source_id=reading_source.id if reading_source else None,
        source_title=source_title_final,
        source_author=source_author_final,
        source_reference=source_reference_final,
        source_sentence=source_sentence_clean or None,
        source_page=source_page_clean,
        context_note=context_note_clean or None,
    )

    db.add(card)
    db.flush()
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
    content_kind: str | models.ContentKind | schemas.ContentKind | None = None,
    reading_source_id: Optional[int] = None,
    source_title: Optional[str] = None,
    source_author: Optional[str] = None,
    source_kind: Optional[str] = None,
    source_reference: Optional[str] = None,
    source_sentence: Optional[str] = None,
    source_page: Optional[str] = None,
    context_note: Optional[str] = None,
) -> models.Card:
    access = require_deck_access(db, user_id, deck_id)
    deck = access.deck
    if access.role not in (models.DeckRole.OWNER, models.DeckRole.EDITOR):
        raise PermissionError("No permission to edit deck")
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    is_admin = user is not None and is_admin_username(user.username)

    if deck.deck_type == models.DeckType.LIBRARY and not is_admin:
        raise PermissionError('Library decks are read-only')
    reading_source = _resolve_reading_source_for_deck(
        db,
        user_id=user_id,
        deck=deck,
        reading_source_id=reading_source_id,
    )
    if (
        reading_source is None
        and reading_source_id is None
        and source_title is not None
        and source_title.strip()
    ):
        from app.services.reading_source_service import resolve_or_create_reading_source

        pair = get_user_learning_pair_by_langs(
            db,
            user_id=user_id,
            source_language_id=deck.source_language_id,
            target_language_id=deck.target_language_id,
        )
        if pair:
            reading_source = resolve_or_create_reading_source(
                db,
                user_id=user_id,
                pair_id=pair.id,
                source_title=source_title,
                source_author=source_author,
                source_kind=source_kind,
                source_reference=source_reference,
                create_if_missing=True,
            )

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
        front_norm = normalize_front(front_clean)
        duplicate = (
            db.query(models.Card.id)
            .filter(
                models.Card.deck_id == deck_id,
                models.Card.front_norm == front_norm,
                models.Card.id != card_id,
            )
            .first()
        )
        if duplicate:
            raise ValueError("Duplicate word in this deck")
        card.front = front_clean
        card.front_norm = front_norm

    if back is not None:
        card.back = (back or "").strip()

    if example_sentence is not None:
        # allow clearing with empty string
        val = (example_sentence or "").strip()
        card.example_sentence = val or None
    if content_kind is not None:
        card.content_kind = normalize_content_kind(content_kind)
    if reading_source_id is not None:
        card.reading_source_id = reading_source.id if reading_source else None
        if not source_title:
            card.source_title = reading_source.title if reading_source else None
        if not source_author:
            card.source_author = reading_source.author if reading_source else None
        if not source_reference:
            card.source_reference = reading_source.reference if reading_source else None
    elif reading_source is not None:
        card.reading_source_id = reading_source.id
    if source_title is not None:
        card.source_title = auto_content.clean_text(source_title) or None
    if source_author is not None:
        card.source_author = auto_content.clean_text(source_author) or None
    if source_kind is not None and reading_source is not None:
        reading_source.kind = auto_content.clean_text(source_kind) or None
    if source_reference is not None:
        card.source_reference = auto_content.clean_text(source_reference) or None
    if source_sentence is not None:
        card.source_sentence = auto_content.clean_text(source_sentence) or None
    if source_page is not None:
        card.source_page = (source_page or "").strip() or None
    if context_note is not None:
        card.context_note = auto_content.clean_text(context_note) or None

    db.flush()
    db.refresh(card)
    return card


def delete_card(db: Session, deck_id: int, card_id: int, user_id: int) -> bool:
    access = require_deck_access(db, user_id, deck_id)
    deck = access.deck
    if access.role not in (models.DeckRole.OWNER, models.DeckRole.EDITOR):
        raise PermissionError("No permission to edit deck")
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    is_admin = user is not None and is_admin_username(user.username)

    if deck.deck_type == models.DeckType.LIBRARY and not is_admin:
        raise PermissionError('Library decks are read-only')

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
    db.flush()
    return True


def list_deck_cards(
    db: Session,
    deck_id: int,
    user_id: int,
    limit: int,
    offset: int,
    reading_source_id: int | None = None,
):
    access = require_deck_access(db, user_id, deck_id)
    deck = access.deck

    if reading_source_id is not None:
        source = (
            db.query(models.ReadingSource)
            .filter(
                models.ReadingSource.id == reading_source_id,
                models.ReadingSource.user_id == user_id,
            )
            .first()
        )
        if not source:
            raise LookupError("Reading source not found")
        pair = (
            db.query(models.UserLearningPair)
            .filter(
                models.UserLearningPair.id == source.pair_id,
                models.UserLearningPair.user_id == user_id,
            )
            .first()
        )
        if not pair:
            raise LookupError("Reading source not found")
        if (
            pair.source_language_id != deck.source_language_id
            or pair.target_language_id != deck.target_language_id
        ):
            raise ValueError("Reading source pair does not match deck pair")

    base_q = (
        db.query(models.Card)
        .options(joinedload(models.Card.reading_source))
        .filter(models.Card.deck_id == deck_id)
        .order_by(models.Card.id.asc())
    )
    if reading_source_id is not None:
        base_q = base_q.filter(models.Card.reading_source_id == reading_source_id)

    total = base_q.count()
    cards = base_q.offset(offset).limit(limit).all()

    if not cards:
        return [], total

    card_ids = [c.id for c in cards]

    progress_rows = (
        db.query(models.UserCardProgress)
        .filter(
            models.UserCardProgress.user_id == user_id,
            models.UserCardProgress.card_id.in_(card_ids),
        )
        .all()
    )
    progress_by_card_id = {p.card_id: p for p in progress_rows}

    items = []
    for card in cards:
        progress = progress_by_card_id.get(card.id)
        status = progress.status if progress and progress.status else models.ProgressStatus.NEW

        item = schemas.CardOut.model_validate(card).model_dump()
        item["status"] = status
        items.append(item)

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
    db.flush()
    db.refresh(rec)
    return rec

def reset_card_progress(
    db: Session,
    deck_id: int,
    card_id: int,
    user_id: int,
):
    deck = (
        db.query(models.Deck)
        .join(models.DeckAccess, models.DeckAccess.deck_id == models.Deck.id)
        .filter(
            models.Deck.id == deck_id,
            models.DeckAccess.user_id == user_id,
        )
        .first()
    )
    if not deck:
        raise PermissionError("No permission to access deck")

    card = (
        db.query(models.Card)
        .filter(
            models.Card.id == card_id,
            models.Card.deck_id == deck_id,
        )
        .first()
    )
    if not card:
        raise LookupError("Card not found")

    progress = (
        db.query(models.UserCardProgress)
        .filter(
            models.UserCardProgress.user_id == user_id,
            models.UserCardProgress.card_id == card_id,
        )
        .first()
    )

    if progress:
        progress.status = models.ProgressStatus.NEW
        progress.due_at = None
        progress.last_reviewed_at = None

        if hasattr(progress, "interval_days"):
            progress.interval_days = 0
        if hasattr(progress, "ease_factor"):
            progress.ease_factor = 2.5
        if hasattr(progress, "lapses"):
            progress.lapses = 0
        if hasattr(progress, "reps"):
            progress.reps = 0

        db.add(progress)
        db.flush()
        db.refresh(progress)

    return card


# ----------------- Study selection queries -----------------
def get_default_learning_pair(db: Session, user_id: int) -> models.UserLearningPair | None:
    return (
        db.query(models.UserLearningPair)
        .options(
            joinedload(models.UserLearningPair.source_language),
            joinedload(models.UserLearningPair.target_language),
        )
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
    reading_source_id: int | None = None,
):
    require_deck_access(db, user_id, deck_id)
    now = _utc_now()

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
            models.UserCardProgress.status == models.ProgressStatus.LEARNING,
            models.UserCardProgress.due_at.isnot(None),
            models.UserCardProgress.due_at <= now,
        )
    )

    if reading_source_id is not None:
        base_q = base_q.filter(models.Card.reading_source_id == reading_source_id)

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
    reading_source_id: int | None = None,
):
    require_deck_access(db, user_id, deck_id)

    now = _utc_now()

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
                    models.UserCardProgress.status == models.ProgressStatus.NEW,
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

    if reading_source_id is not None:
        base_q = base_q.filter(models.Card.reading_source_id == reading_source_id)

    base_q = base_q.order_by(models.Card.id.asc())

    total = base_q.count()
    items = base_q.offset(offset).limit(limit).all()

    return items, total


# ----------------- Daily counters for quotas -----------------


def _utc_day_start(now: datetime) -> datetime:
    return datetime(now.year, now.month, now.day)


def _utc_now() -> datetime:
    return datetime.utcnow()


def utc_day_bounds(now: datetime):
    start = datetime(now.year, now.month, now.day)
    end = start + timedelta(days=1)
    return start, end


def count_cards_created_on_day(
    db: Session,
    user_id: int,
    d: date,
    deck_id: int | None = None,
    pair_id: int | None = None,
) -> int:
    start, end = bishkek_day_bounds(d)

    q = (
        db.query(models.Card)
        .join(models.Deck, models.Deck.id == models.Card.deck_id)
        .join(models.DeckAccess, models.DeckAccess.deck_id == models.Card.deck_id)
        .filter(
            models.DeckAccess.user_id == user_id,
            models.Card.created_at >= start,
            models.Card.created_at < end,
        )
    )

    if deck_id is not None:
        require_deck_access(db, user_id, deck_id)
        q = q.filter(models.Card.deck_id == deck_id)
    elif pair_id is not None:
        pair = (
            db.query(models.UserLearningPair)
            .filter(
                models.UserLearningPair.user_id == user_id,
                models.UserLearningPair.id == pair_id,
            )
            .first()
        )
        if not pair:
            return 0

        q = q.filter(
            models.Deck.source_language_id == pair.source_language_id,
            models.Deck.target_language_id == pair.target_language_id,
        )

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
    now = _utc_now()
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
    now = _utc_now()
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


def count_due_reviews(
    db: Session,
    user_id: int,
    deck_id: int | None = None,
    pair_id: int | None = None,
    reading_source_id: int | None = None,
) -> int:
    now = _utc_now()

    q = (
        db.query(models.UserCardProgress)
        .join(models.Card, models.Card.id == models.UserCardProgress.card_id)
        .join(models.Deck, models.Deck.id == models.Card.deck_id)
        .join(models.DeckAccess, models.DeckAccess.deck_id == models.Card.deck_id)
        .filter(
            models.DeckAccess.user_id == user_id,
            models.UserCardProgress.user_id == user_id,
            models.UserCardProgress.status == models.ProgressStatus.LEARNING,
            models.UserCardProgress.due_at.isnot(None),
            models.UserCardProgress.due_at <= now,
        )
    )

    if deck_id is not None:
        q = q.filter(models.Card.deck_id == deck_id)
    elif pair_id is not None:
        pair = (
            db.query(models.UserLearningPair)
            .filter(
                models.UserLearningPair.user_id == user_id,
                models.UserLearningPair.id == pair_id,
            )
            .first()
        )
        if not pair:
            return 0

        q = q.filter(
            models.Deck.source_language_id == pair.source_language_id,
            models.Deck.target_language_id == pair.target_language_id,
        )

    if reading_source_id is not None:
        q = q.filter(models.Card.reading_source_id == reading_source_id)

    return q.count()


def count_new_available(
    db: Session,
    user_id: int,
    deck_id: int | None = None,
    pair_id: int | None = None,
    reading_source_id: int | None = None,
) -> int:
    now = _utc_now()

    q = (
        db.query(models.Card)
        .join(models.Deck, models.Deck.id == models.Card.deck_id)
        .join(models.DeckAccess, models.DeckAccess.deck_id == models.Card.deck_id)
        .outerjoin(
            models.UserCardProgress,
            and_(
                models.UserCardProgress.card_id == models.Card.id,
                models.UserCardProgress.user_id == user_id,
            ),
        )
        .filter(
            models.DeckAccess.user_id == user_id,
            or_(
                models.UserCardProgress.id.is_(None),
                and_(
                    models.UserCardProgress.status == models.ProgressStatus.NEW,
                    or_(
                        models.UserCardProgress.due_at.is_(None),
                        models.UserCardProgress.due_at <= now,
                    ),
                ),
            ),
        )
    )

    if deck_id is not None:
        q = q.filter(models.Card.deck_id == deck_id)
    elif pair_id is not None:
        pair = (
            db.query(models.UserLearningPair)
            .filter(
                models.UserLearningPair.user_id == user_id,
                models.UserLearningPair.id == pair_id,
            )
            .first()
        )
        if not pair:
            return 0

        q = q.filter(
            models.Deck.source_language_id == pair.source_language_id,
            models.Deck.target_language_id == pair.target_language_id,
        )

    if reading_source_id is not None:
        q = q.filter(models.Card.reading_source_id == reading_source_id)

    return q.count()


def get_next_due_at(
    db: Session,
    user_id: int,
    deck_id: int | None = None,
    pair_id: int | None = None,
    reading_source_id: int | None = None,
):
    q = (
        db.query(func.min(models.UserCardProgress.due_at))
        .join(models.Card, models.Card.id == models.UserCardProgress.card_id)
        .join(models.Deck, models.Deck.id == models.Card.deck_id)
        .join(models.DeckAccess, models.DeckAccess.deck_id == models.Card.deck_id)
        .filter(
            models.DeckAccess.user_id == user_id,
            models.UserCardProgress.user_id == user_id,
            models.UserCardProgress.status == models.ProgressStatus.LEARNING,
            models.UserCardProgress.due_at.isnot(None),
        )
    )

    if deck_id is not None:
        q = q.filter(models.Card.deck_id == deck_id)
    elif pair_id is not None:
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

        q = q.filter(
            models.Deck.source_language_id == pair.source_language_id,
            models.Deck.target_language_id == pair.target_language_id,
        )

    if reading_source_id is not None:
        q = q.filter(models.Card.reading_source_id == reading_source_id)

    return q.scalar()


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


def count_total_cards(
    db: Session,
    user_id: int,
    deck_id: int | None = None,
    pair_id: int | None = None,
) -> int:
    q = (
        db.query(models.Card)
        .join(models.Deck, models.Deck.id == models.Card.deck_id)
        .join(models.DeckAccess, models.DeckAccess.deck_id == models.Card.deck_id)
        .filter(models.DeckAccess.user_id == user_id)
    )

    if deck_id is not None:
        q = q.filter(models.Card.deck_id == deck_id)
    elif pair_id is not None:
        pair = (
            db.query(models.UserLearningPair)
            .filter(
                models.UserLearningPair.user_id == user_id,
                models.UserLearningPair.id == pair_id,
            )
            .first()
        )
        if not pair:
            return 0

        q = q.filter(
            models.Deck.source_language_id == pair.source_language_id,
            models.Deck.target_language_id == pair.target_language_id,
        )

    return q.count()

def count_progress_statuses(
    db: Session,
    user_id: int,
    deck_id: int | None = None,
    pair_id: int | None = None,
) -> dict:
    pair = None
    if deck_id is None and pair_id is not None:
        pair = (
            db.query(models.UserLearningPair)
            .filter(
                models.UserLearningPair.user_id == user_id,
                models.UserLearningPair.id == pair_id,
            )
            .first()
        )
        if not pair:
            return {"mastered": 0, "learning": 0, "new": 0}

    # mastered + learning from progress rows
    q = (
        db.query(models.UserCardProgress.status, func.count(models.UserCardProgress.id))
        .join(models.Card, models.Card.id == models.UserCardProgress.card_id)
        .join(models.Deck, models.Deck.id == models.Card.deck_id)
        .filter(models.UserCardProgress.user_id == user_id)
    )

    if deck_id is not None:
        q = q.filter(models.Card.deck_id == deck_id)
    elif pair is not None:
        q = q.filter(
            models.Deck.source_language_id == pair.source_language_id,
            models.Deck.target_language_id == pair.target_language_id,
        )

    rows = q.group_by(models.UserCardProgress.status).all()

    counts = {"mastered": 0, "learning": 0, "new": 0}

    for status, c in rows:
        key = status.value if hasattr(status, "value") else str(status)
        if key in counts:
            counts[key] = int(c)

    # new cards = cards without any progress row
    q2 = (
        db.query(models.Card)
        .join(models.Deck, models.Deck.id == models.Card.deck_id)
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
    elif pair is not None:
        q2 = q2.filter(
            models.Deck.source_language_id == pair.source_language_id,
            models.Deck.target_language_id == pair.target_language_id,
        )

    counts["new"] += q2.count()
    return counts
