from __future__ import annotations

from sqlalchemy.orm import Session

from app import crud, models
from app.services import deck_service
from app.services.pair_service import get_or_create_pair_from_languages
from app.services.reading_source_service import resolve_or_create_reading_source


def list_library_decks_for_user(
    db: Session,
    *,
    user_id: int,
    limit: int,
    offset: int,
    pair_id: int | None = None,
) -> tuple[list[models.Deck], int]:
    return crud.list_library_decks(
        db,
        user_id,
        limit=limit,
        offset=offset,
        pair_id=pair_id,
    )


def list_library_cards_for_deck(
    db: Session,
    *,
    user_id: int,
    deck_id: int,
    limit: int,
    offset: int,
    reading_source_id: int | None = None,
):
    return crud.list_library_deck_cards(
        db,
        deck_id,
        limit=limit,
        offset=offset,
        reading_source_id=reading_source_id,
        user_id=user_id,
    )


def create_library_deck_for_admin(
    db: Session,
    *,
    owner_id: int,
    name: str,
    source_language_id: int,
    target_language_id: int,
    source_type: str | None = None,
    author_name: str | None = None,
) -> models.Deck:
    try:
        deck = crud.create_deck(
            db,
            name=name,
            owner_id=owner_id,
            source_language_id=source_language_id,
            target_language_id=target_language_id,
            deck_type=models.DeckType.LIBRARY,
            source_type=source_type,
            author_name=author_name,
        )
        deck.is_public = True
        db.commit()
        db.refresh(deck)
        return deck
    except Exception:
        db.rollback()
        raise


def import_library_card_to_main_deck(
    db: Session,
    *,
    user_id: int,
    library_card_id: int,
    dry_run: bool = False,
) -> dict:
    try:
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
                "status": "duplicate",
                "imported": False,
                "skipped": True,
                "reason": "duplicate",
                "card": existing,
            }

        if dry_run:
            db.rollback()
            return {
                "status": "preview",
                "imported": False,
                "skipped": False,
                "reason": "dry_run",
                "card": None,
            }

        source_title = card.source_title or (card.reading_source.title if card.reading_source else None)
        source_author = card.source_author or (
            card.reading_source.author if card.reading_source else None
        )
        source_kind = card.reading_source.kind if card.reading_source else None
        source_reference = card.source_reference or (
            card.reading_source.reference if card.reading_source else None
        )
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

        new_card = crud.create_card(
            db,
            deck_id=target_deck.id,
            user_id=user_id,
            front=card.front,
            back=card.back or "",
            example_sentence=card.example_sentence,
            content_kind=card.content_kind,
            reading_source_id=reading_source.id if reading_source else None,
            source_title=source_title,
            source_author=source_author,
            source_kind=source_kind,
            source_reference=source_reference,
            source_sentence=card.source_sentence,
            source_page=card.source_page,
            context_note=card.context_note,
            auto_fill=False,
        )
        db.commit()

        return {
            "status": "created",
            "imported": True,
            "skipped": False,
            "reason": None,
            "card": new_card,
        }
    except Exception:
        db.rollback()
        raise

def import_selected_library_cards_to_main_deck(
    db: Session,
    *,
    user_id: int,
    library_deck_id: int,
    card_ids: list[int],
    dry_run: bool = False,
) -> dict:
    try:
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
        created_count = 0
        preview_count = 0
        duplicate_count = 0
        invalid_count = 0
        failed_count = 0

        for card_id in card_ids:
            card = crud.get_card_for_library_import(db, card_id)
            if not card or card.deck_id != library_deck_id:
                results.append(
                    {
                        "library_card_id": card_id,
                        "status": "invalid",
                        "imported": False,
                        "skipped": True,
                        "reason": "card_not_in_library_deck",
                        "card": None,
                    }
                )
                invalid_count += 1
                continue

            if crud.card_exists_in_deck(db, target_deck.id, card.front):
                results.append(
                    {
                        "library_card_id": card_id,
                        "status": "duplicate",
                        "imported": False,
                        "skipped": True,
                        "reason": "duplicate",
                        "card": None,
                    }
                )
                duplicate_count += 1
                continue

            if dry_run:
                results.append(
                    {
                        "library_card_id": card_id,
                        "status": "preview",
                        "imported": False,
                        "skipped": False,
                        "reason": "dry_run",
                        "card": None,
                    }
                )
                preview_count += 1
                continue

            try:
                with db.begin_nested():
                    source_title = card.source_title or (
                        card.reading_source.title if card.reading_source else None
                    )
                    source_author = card.source_author or (
                        card.reading_source.author if card.reading_source else None
                    )
                    source_kind = card.reading_source.kind if card.reading_source else None
                    source_reference = card.source_reference or (
                        card.reading_source.reference if card.reading_source else None
                    )
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
                    new_card = crud.create_card(
                        db,
                        deck_id=target_deck.id,
                        user_id=user_id,
                        front=card.front,
                        back=card.back or "",
                        example_sentence=card.example_sentence,
                        content_kind=card.content_kind,
                        reading_source_id=reading_source.id if reading_source else None,
                        source_title=source_title,
                        source_author=source_author,
                        source_kind=source_kind,
                        source_reference=source_reference,
                        source_sentence=card.source_sentence,
                        source_page=card.source_page,
                        context_note=card.context_note,
                        auto_fill=False,
                    )
                results.append(
                    {
                        "library_card_id": card_id,
                        "status": "created",
                        "imported": True,
                        "skipped": False,
                        "reason": None,
                        "card": new_card,
                    }
                )
                created_count += 1
            except ValueError as e:
                msg = str(e)
                if "Duplicate word in this deck" in msg:
                    status = "duplicate"
                    duplicate_count += 1
                else:
                    status = "invalid"
                    invalid_count += 1
                results.append(
                    {
                        "library_card_id": card_id,
                        "status": status,
                        "imported": False,
                        "skipped": True,
                        "reason": msg,
                        "card": None,
                    }
                )
            except Exception as e:
                failed_count += 1
                results.append(
                    {
                        "library_card_id": card_id,
                        "status": "failed",
                        "imported": False,
                        "skipped": True,
                        "reason": str(e),
                        "card": None,
                    }
                )
        if dry_run:
            db.rollback()
        else:
            db.commit()

        return {
            "results": results,
            "created_count": created_count,
            "preview_count": preview_count,
            "duplicate_count": duplicate_count,
            "invalid_count": invalid_count,
            "failed_count": failed_count,
            "imported_count": created_count,
            "skipped_count": duplicate_count + invalid_count + failed_count,
        }
    except Exception:
        db.rollback()
        raise
