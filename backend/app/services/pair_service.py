from __future__ import annotations
from sqlalchemy.orm import Session

from app import crud, models


def resolve_user_pair(
    db: Session,
    user_id: int,
    pair_id: int | None = None,
):
    pair = crud.get_user_learning_pair(db, user_id, pair_id)
    if not pair:
        raise ValueError("Learning pair not found")
    return pair


def resolve_user_pair_by_payload(
    db: Session,
    user_id: int,
    *,
    pair_id: int | None = None,
    source_language_id: int | None = None,
    target_language_id: int | None = None,
) -> models.UserLearningPair:
    if pair_id is not None:
        return crud.get_user_learning_pair(db, user_id, pair_id)

    if source_language_id is not None or target_language_id is not None:
        if source_language_id is None or target_language_id is None:
            raise ValueError("Provide both source_language_id and target_language_id, or neither")

        if source_language_id == target_language_id:
            raise ValueError("Source and target must differ")

        pair = crud.get_user_learning_pair_by_langs(
            db,
            user_id,
            source_language_id,
            target_language_id,
        )
        if not pair:
            raise ValueError("Learning pair not found")
        return pair

    return crud.get_user_learning_pair(db, user_id, None)


def get_user_pair_by_id(
    db: Session,
    *,
    user_id: int,
    pair_id: int,
) -> models.UserLearningPair | None:
    return (
        db.query(models.UserLearningPair)
        .filter(
            models.UserLearningPair.id == pair_id,
            models.UserLearningPair.user_id == user_id,
        )
        .first()
    )

def get_default_pair(
    db: Session,
    *,
    user_id: int,
) -> models.UserLearningPair | None:
    return (
        db.query(models.UserLearningPair)
        .filter(
            models.UserLearningPair.user_id == user_id,
            models.UserLearningPair.is_default.is_(True),
        )
        .first()
    )

def get_pair_by_languages(
    db: Session,
    *,
    user_id: int,
    source_language_id: int,
    target_language_id: int,
) -> models.UserLearningPair | None:
    return (
        db.query(models.UserLearningPair)
        .filter(
            models.UserLearningPair.user_id == user_id,
            models.UserLearningPair.source_language_id == source_language_id,
            models.UserLearningPair.target_language_id == target_language_id,
        )
        .first()
    )

def get_or_create_pair_from_languages(
    db: Session,
    *,
    user_id: int,
    source_language_id: int,
    target_language_id: int,
    make_default: bool = False,
) -> models.UserLearningPair:
    pair = (
        db.query(models.UserLearningPair)
        .filter(
            models.UserLearningPair.user_id == user_id,
            models.UserLearningPair.source_language_id == source_language_id,
            models.UserLearningPair.target_language_id == target_language_id,
        )
        .first()
    )
    if pair:
        return pair

    pair = models.UserLearningPair(
        user_id=user_id,
        source_language_id=source_language_id,
        target_language_id=target_language_id,
        is_default=make_default,
    )
    db.add(pair)
    db.flush()
    return pair

def get_or_create_pair_from_deck(
    db: Session,
    *,
    user_id: int,
    deck: models.Deck,
    make_default: bool = False,
) -> models.UserLearningPair:
    return get_or_create_pair_from_languages(
        db,
        user_id=user_id,
        source_language_id=deck.source_language_id,
        target_language_id=deck.target_language_id,
        make_default=make_default,
    )

def validate_pair_inputs(
    *,
    pair_id: int | None = None,
    source_language_id: int | None = None,
    target_language_id: int | None = None,
) -> None:
    has_pair_id = pair_id is not None
    has_any_lang = source_language_id is not None or target_language_id is not None
    has_both_langs = source_language_id is not None and target_language_id is not None

    if has_pair_id and has_any_lang:
        raise ValueError("Use either pair_id or source/target language ids, not both")

    if has_any_lang and not has_both_langs:
        raise ValueError("Both source_language_id and target_language_id are required")

def resolve_pair_for_user(
    db: Session,
    *,
    user_id: int,
    pair_id: int | None = None,
    source_language_id: int | None = None,
    target_language_id: int | None = None,
    auto_create_by_langs: bool = False,
    use_default_if_missing: bool = True,
) -> models.UserLearningPair:
    validate_pair_inputs(
        pair_id=pair_id,
        source_language_id=source_language_id,
        target_language_id=target_language_id,
    )

    if pair_id is not None:
        pair = get_user_pair_by_id(db, user_id=user_id, pair_id=pair_id)
        if not pair:
            raise ValueError("Learning pair not found")
        return pair

    if source_language_id is not None and target_language_id is not None:
        if auto_create_by_langs:
            return get_or_create_pair_from_languages(
                db,
                user_id=user_id,
                source_language_id=source_language_id,
                target_language_id=target_language_id,
            )

        pair = get_pair_by_languages(
            db,
            user_id=user_id,
            source_language_id=source_language_id,
            target_language_id=target_language_id,
        )
        if not pair:
            raise ValueError("Learning pair not found")
        return pair

    if use_default_if_missing:
        pair = get_default_pair(db, user_id=user_id)
        if not pair:
            raise ValueError("Default learning pair not set")
        return pair

    raise ValueError("Learning pair is required")