from __future__ import annotations
from sqlalchemy.orm import Session

from app import crud, models
from app.services.pair_service import resolve_pair_for_user


def _get_user_or_raise(db: Session, user_id: int) -> models.User:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise ValueError("User not found")
    return user


def require_readable_deck(
    db: Session,
    *,
    user_id: int,
    deck_id: int,
) -> models.Deck:
    deck = crud.get_deck(db, deck_id, user_id)
    if not deck:
        raise LookupError("Deck not found or no access")
    return deck


def get_user_readable_deck(db: Session, user_id: int, deck_id: int) -> models.Deck:
    # Backward-compatible alias; prefer require_readable_deck.
    return require_readable_deck(db, user_id=user_id, deck_id=deck_id)


def require_editable_deck(
    db: Session,
    *,
    user_id: int,
    deck_id: int,
) -> models.Deck:
    try:
        access = crud.require_deck_access(db, user_id, deck_id)
    except PermissionError:
        raise PermissionError("No permission to edit deck")
    if access.role not in (models.DeckRole.OWNER, models.DeckRole.EDITOR):
        raise PermissionError("No permission to edit deck")
    return access.deck


def require_users_deck(
    db: Session,
    *,
    user_id: int,
    deck_id: int,
) -> models.Deck:
    deck = require_readable_deck(
        db,
        user_id=user_id,
        deck_id=deck_id,
    )
    if deck.deck_type != models.DeckType.USERS:
        raise ValueError("Only user decks are allowed")
    return deck


def require_main_deck(
    db: Session,
    *,
    user_id: int,
    deck_id: int,
) -> models.Deck:
    deck = require_readable_deck(
        db,
        user_id=user_id,
        deck_id=deck_id,
    )
    if deck.deck_type != models.DeckType.MAIN:
        raise ValueError("You can only study from main deck")
    return deck


def require_study_card(
    db: Session,
    *,
    user_id: int,
    card_id: int,
) -> tuple[models.Card, models.Deck]:
    row = (
        db.query(models.Card, models.Deck)
        .join(models.Deck, models.Card.deck_id == models.Deck.id)
        .join(models.DeckAccess, models.DeckAccess.deck_id == models.Deck.id)
        .filter(
            models.Card.id == card_id,
            models.DeckAccess.user_id == user_id,
        )
        .first()
    )
    if not row:
        raise LookupError("Card not found or no access")

    card, deck = row

    if deck.deck_type != models.DeckType.MAIN:
        raise ValueError("Study is allowed only from main decks")

    return card, deck


def resolve_main_deck_for_user_pair(
    db: Session,
    *,
    user_id: int,
    pair_id: int | None = None,
    source_language_id: int | None = None,
    target_language_id: int | None = None,
) -> models.Deck:
    pair = resolve_pair_for_user(
        db,
        user_id=user_id,
        pair_id=pair_id,
        source_language_id=source_language_id,
        target_language_id=target_language_id,
        auto_create_by_langs=True,
        use_default_if_missing=True,
    )

    user = _get_user_or_raise(db, user_id)

    deck = crud.get_or_create_main_deck_for_pair(
        db,
        user=user,
        source_language_id=pair.source_language_id,
        target_language_id=pair.target_language_id,
    )
    db.flush()
    return deck


def resolve_main_deck_from_pair(
    db: Session,
    user=None,
    *,
    user_id: int | None = None,
    pair: models.UserLearningPair,
) -> models.Deck:
    if user_id is None:
        if user is None:
            raise ValueError("user_id is required")
        user_id = user.id

    user_obj = _get_user_or_raise(db, user_id)

    deck = crud.get_or_create_main_deck_for_pair(
        db,
        user=user_obj,
        source_language_id=pair.source_language_id,
        target_language_id=pair.target_language_id,
    )
    db.flush()
    return deck


def resolve_main_deck_by_pair_or_deck(
    db: Session,
    user=None,
    *,
    user_id: int | None = None,
    deck_id: int | None = None,
    pair_id: int | None = None,
) -> models.Deck:
    if user_id is None:
        if user is None:
            raise ValueError("user_id is required")
        user_id = user.id

    if deck_id is not None:
        return require_main_deck(
            db,
            user_id=user_id,
            deck_id=deck_id,
        )

    return resolve_main_deck_for_user_pair(
        db,
        user_id=user_id,
        pair_id=pair_id,
    )
