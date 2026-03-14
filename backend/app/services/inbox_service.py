from __future__ import annotations

import re
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.services import deck_service
from app.services.pair_service import resolve_pair_for_user
from app.services.reading_source_service import resolve_or_create_reading_source

# Matches: em dash, en dash, minus sign, hyphen variants, colon, semicolon, equals, tab, pipe
SPLIT_RE = re.compile(r"\s*(?:—|–|−|-|‐|:|;|=|\t|\|)\s*", re.UNICODE)


def _split_line(line: str, fixed_delim: Optional[str]) -> Optional[Tuple[str, str]]:
    raw = (line or "").strip()
    if not raw or raw.startswith("#"):
        return None

    if fixed_delim:
        if fixed_delim not in raw:
            return None
        left, right = raw.split(fixed_delim, 1)
        front = left.strip()
        back = right.strip()
        if not front:
            return None
        return front, back

    parts = SPLIT_RE.split(raw, maxsplit=1)
    if len(parts) == 2:
        front, back = parts[0].strip(), parts[1].strip()
        if not front:
            return None
        return front, back

    return raw, ""


def resolve_inbox_deck(
    db: Session,
    *,
    user_id: int,
    source_language_id: int | None,
    target_language_id: int | None,
) -> models.Deck:
    pair = resolve_pair_for_user(
        db,
        user_id=user_id,
        source_language_id=source_language_id,
        target_language_id=target_language_id,
        auto_create_by_langs=True,
        use_default_if_missing=True,
    )

    return deck_service.resolve_main_deck_from_pair(
        db,
        user_id=user_id,
        pair=pair,
    )


def quick_add_word(
    db: Session,
    *,
    user_id: int,
    payload: schemas.InboxWordIn,
) -> dict:
    try:
        deck = resolve_inbox_deck(
            db,
            user_id=user_id,
            source_language_id=payload.source_language_id,
            target_language_id=payload.target_language_id,
        )
        pair = resolve_pair_for_user(
            db,
            user_id=user_id,
            source_language_id=deck.source_language_id,
            target_language_id=deck.target_language_id,
            auto_create_by_langs=False,
            use_default_if_missing=False,
        )
        reading_source = resolve_or_create_reading_source(
            db,
            user_id=user_id,
            pair_id=pair.id,
            reading_source_id=payload.reading_source_id,
            source_title=payload.source_title,
            source_author=payload.source_author,
            source_kind=payload.source_kind,
            source_reference=payload.source_reference,
            create_if_missing=True,
        )

        back = (payload.back or "").strip()
        example = payload.example_sentence.strip() if payload.example_sentence else None

        card = crud.create_card(
            db,
            deck_id=deck.id,
            user_id=user_id,
            front=payload.front.strip(),
            back=back,
            example_sentence=example,
            reading_source_id=reading_source.id if reading_source else None,
            source_title=payload.source_title,
            source_author=payload.source_author,
            source_kind=payload.source_kind,
            source_reference=payload.source_reference,
            source_sentence=payload.source_sentence,
            source_page=payload.source_page,
            context_note=payload.context_note,
            auto_fill=True,
        )
        db.commit()
        return {"deck_id": deck.id, "card": card}
    except Exception:
        db.rollback()
        raise


def bulk_import(
    db: Session,
    *,
    user_id: int,
    payload: schemas.InboxBulkIn,
) -> dict:
    deck = resolve_inbox_deck(
        db,
        user_id=user_id,
        source_language_id=payload.source_language_id,
        target_language_id=payload.target_language_id,
    )

    lines = payload.text.splitlines()
    results: list[schemas.BulkItemResult] = []
    created_count = 0
    preview_count = 0
    duplicate_count = 0
    invalid_count = 0
    failed_count = 0
    seen_norms: set[str] = set()

    for idx, line in enumerate(lines):
        parsed = _split_line(line, payload.delimiter)
        if not parsed:
            invalid_count += 1
            results.append(
                schemas.BulkItemResult(
                    index=idx,
                    line=line,
                    status="invalid",
                    reason="empty/invalid",
                )
            )
            continue

        front, back = parsed
        front = front.strip()
        back = (back or "").strip()

        if not front:
            invalid_count += 1
            results.append(
                schemas.BulkItemResult(
                    index=idx,
                    line=line,
                    front=front,
                    status="invalid",
                    reason="empty front",
                )
            )
            continue

        front_norm = crud.normalize_front(front)
        if front_norm in seen_norms:
            duplicate_count += 1
            results.append(
                schemas.BulkItemResult(
                    index=idx,
                    line=line,
                    front=front,
                    status="duplicate",
                    reason="duplicate in paste",
                )
            )
            continue
        seen_norms.add(front_norm)

        if crud.card_exists_in_deck(db, deck.id, front):
            duplicate_count += 1
            results.append(
                schemas.BulkItemResult(
                    index=idx,
                    line=line,
                    front=front,
                    status="duplicate",
                    reason="duplicate",
                )
            )
            continue

        if payload.dry_run:
            preview_count += 1
            results.append(
                schemas.BulkItemResult(
                    index=idx,
                    line=line,
                    front=front,
                    status="preview",
                    reason="dry_run",
                )
            )
            continue

        try:
            with db.begin_nested():
                card = crud.create_card(
                    db,
                    deck_id=deck.id,
                    user_id=user_id,
                    front=front,
                    back=back,
                    example_sentence=None,
                    auto_fill=False,
                )
            created_count += 1
            results.append(
                schemas.BulkItemResult(
                    index=idx,
                    line=line,
                    front=front,
                    status="created",
                    card_id=card.id,
                )
            )
        except ValueError as e:
            msg = str(e)
            if "Duplicate word in this deck" in msg:
                duplicate_count += 1
                status = "duplicate"
            else:
                invalid_count += 1
                status = "invalid"
            results.append(
                schemas.BulkItemResult(
                    index=idx,
                    line=line,
                    front=front,
                    status=status,
                    reason=msg,
                )
            )
        except Exception as e:
            failed_count += 1
            results.append(
                schemas.BulkItemResult(
                    index=idx,
                    line=line,
                    front=front,
                    status="failed",
                    reason=str(e),
                )
            )

    if payload.dry_run:
        # Ensure preview mode never persists writes (e.g., auto-created pair/deck).
        db.rollback()
    else:
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

    return {
        "deck_id": deck.id,
        "created_count": created_count,
        "preview_count": preview_count,
        "duplicate_count": duplicate_count,
        "invalid_count": invalid_count,
        "failed_count": failed_count,
        # Legacy compatibility fields
        "created": created_count,
        "skipped": duplicate_count + invalid_count,
        "failed": failed_count,
        "results": results,
    }
