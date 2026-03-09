from __future__ import annotations

from sqlalchemy.orm import Session

from app import crud, models
from app.services import deck_service
from app.services.pair_service import get_or_create_pair_from_languages


def import_library_card_to_main_deck(
    db: Session,
    *,
    user_id: int,
    library_card_id: int,
) -> dict:
    card = crud.get_card_for_library_import(db, library_card_id)
    if not card:
        raise LookupError("Library card not found")

    deck = card.deck
    if deck.deck_type != models.DeckType.LIBRARY:
        raise ValueError("Only library cards can be imported")

    pair = get_or_create_pair_from_languages(
        db,
        user_id=user_id,
        source_language_id=deck.source_language_id,
        target_language_id=deck.target_language_id,
        make_default=False,
    )

    target_deck = deck_service.resolve_main_deck_from_pair(
        db,
        user_id=user_id,
        pair=pair,
    )

    existing = (
        db.query(models.Card)
        .filter(
            models.Card.deck_id == target_deck.id,
            models.Card.front_norm == card.front_norm,
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

    new_card = crud.create_card(
        db,
        deck_id=target_deck.id,
        user_id=user_id,
        front=card.front,
        back=card.back or "",
        example_sentence=card.example_sentence,
        auto_fill=False,
    )

    return {
        "imported": True,
        "skipped": False,
        "reason": None,
        "card": new_card,
    }

def import_selected_library_cards_to_main_deck(
    db: Session,
    *,
    user_id: int,
    library_deck_id: int,
    card_ids: list[int],
) -> dict:
    library_deck = crud.get_library_deck_for_import(db, library_deck_id)
    if not library_deck:
        raise LookupError("Library deck not found")

    pair = get_or_create_pair_from_languages(
        db,
        user_id=user_id,
        source_language_id=library_deck.source_language_id,
        target_language_id=library_deck.target_language_id,
        make_default=False,
    )

    target_deck = deck_service.resolve_main_deck_from_pair(
        db,
        user_id=user_id,
        pair=pair,
    )

    results = []
    imported_count = 0
    skipped_count = 0

    for card_id in card_ids:
        card = crud.get_card_for_library_import(db, card_id)
        if not card or card.deck_id != library_deck_id:
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

        if crud.card_exists_in_deck(db, target_deck.id, card.front):
            results.append(
                {
                    "library_card_id": card_id,
                    "imported": False,
                    "skipped": True,
                    "reason": "duplicate",
                    "card": None,
                }
            )
            skipped_count += 1
            continue

        new_card = crud.create_card(
            db,
            deck_id=target_deck.id,
            user_id=user_id,
            front=card.front,
            back=card.back or "",
            example_sentence=card.example_sentence,
            auto_fill=False,
        )

        results.append(
            {
                "library_card_id": card_id,
                "imported": True,
                "skipped": False,
                "reason": None,
                "card": new_card,
            }
        )
        imported_count += 1

    return {
        "results": results,
        "imported_count": imported_count,
        "skipped_count": skipped_count,
    }