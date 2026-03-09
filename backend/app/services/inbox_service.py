from __future__ import annotations

import re
from typing import Optional, Tuple

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.services import deck_service
from app.services.pair_service import resolve_pair_for_user

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
    deck = resolve_inbox_deck(
        db,
        user_id=user_id,
        source_language_id=payload.source_language_id,
        target_language_id=payload.target_language_id,
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
        auto_fill=True,
    )

    return {"deck_id": deck.id, "card": card}


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
    created = 0
    skipped = 0
    failed = 0
    seen_norms: set[str] = set()

    for line in lines:
        parsed = _split_line(line, payload.delimiter)
        if not parsed:
            skipped += 1
            results.append(
                schemas.BulkItemResult(line=line, status="skipped", reason="empty/invalid")
            )
            continue

        front, back = parsed
        front = front.strip()
        back = (back or "").strip()

        if not front:
            skipped += 1
            results.append(
                schemas.BulkItemResult(line=line, status="skipped", reason="empty front")
            )
            continue

        front_norm = crud.normalize_front(front)
        if front_norm in seen_norms:
            skipped += 1
            results.append(
                schemas.BulkItemResult(line=line, status="skipped", reason="duplicate in paste")
            )
            continue
        seen_norms.add(front_norm)

        if crud.card_exists_in_deck(db, deck.id, front):
            skipped += 1
            results.append(
                schemas.BulkItemResult(line=line, status="skipped", reason="duplicate")
            )
            continue

        if payload.dry_run:
            created += 1
            results.append(
                schemas.BulkItemResult(line=line, status="preview", reason="dry_run")
            )
            continue

        try:
            card = crud.create_card(
                db,
                deck_id=deck.id,
                user_id=user_id,
                front=front,
                back=back,
                example_sentence=None,
                auto_fill=False,
            )
            created += 1
            results.append(
                schemas.BulkItemResult(line=line, status="created", card_id=card.id)
            )
        except ValueError as e:
            skipped += 1
            results.append(
                schemas.BulkItemResult(line=line, status="skipped", reason=str(e))
            )
        except IntegrityError:
            db.rollback()
            skipped += 1
            results.append(
                schemas.BulkItemResult(line=line, status="skipped", reason="duplicate")
            )
        except Exception as e:
            failed += 1
            results.append(
                schemas.BulkItemResult(line=line, status="failed", reason=str(e))
            )

    return {
        "deck_id": deck.id,
        "created": created,
        "skipped": skipped,
        "failed": failed,
        "results": results,
    }