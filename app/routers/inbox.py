from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, Tuple
import re

from ..database import get_db
from ..deps import get_current_user
from .. import crud, schemas

router = APIRouter(prefix="/inbox", tags=["inbox"])

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

    # no delimiter -> front only
    return raw, ""


@router.post("/word", response_model=schemas.InboxWordOut, status_code=status.HTTP_201_CREATED)
def quick_add_word(
    payload: schemas.InboxWordIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        deck = crud.get_or_create_inbox_deck(
            db,
            user,
            source_language_id=payload.source_language_id,
            target_language_id=payload.target_language_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # allow back to be empty now (user fills later)
    back = payload.back or ""

    try:
        card = crud.create_card(
            db,
            deck_id=deck.id,
            user_id=user.id,
            front=payload.front.strip(),
            back=back.strip(),
            example_sentence=(payload.example_sentence.strip() if payload.example_sentence else None),
        )
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

    return {"deck_id": deck.id, "card": card}



@router.post("/bulk", response_model=schemas.InboxBulkOut, status_code=status.HTTP_201_CREATED)
def bulk_import(
    payload: schemas.InboxBulkIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        deck = crud.get_or_create_inbox_deck(
            db,
            user,
            source_language_id=payload.source_language_id,
            target_language_id=payload.target_language_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    lines = payload.text.splitlines()
    results: list[schemas.BulkItemResult] = []
    created = skipped = failed = 0
    seen_norms: set[str] = set()

    for line in lines:
        parsed = _split_line(line, payload.delimiter)
        if not parsed:
            skipped += 1
            results.append(schemas.BulkItemResult(line=line, status="skipped", reason="empty/invalid"))
            continue

        front, back = parsed
        front = front.strip()
        back = (back or "").strip()

        if not front:
            skipped += 1
            results.append(schemas.BulkItemResult(line=line, status="skipped", reason="empty front"))
            continue

        # normalize for "same request" duplicates
        front_norm = crud.normalize_front(front)  # create this helper (you already planned it)
        if front_norm in seen_norms:
            skipped += 1
            results.append(schemas.BulkItemResult(line=line, status="skipped", reason="duplicate in paste"))
            continue
        seen_norms.add(front_norm)

        # duplicate in DB
        if crud.card_exists_in_deck(db, deck.id, front):
            skipped += 1
            results.append(schemas.BulkItemResult(line=line, status="skipped", reason="duplicate"))
            continue

        #Dry run: do not insert
        if payload.dry_run:
            results.append(schemas.BulkItemResult(line=line, status="preview", reason="dry_run"))
            created += 1
            continue

        #Real insert
        try:
            card = crud.create_card(
                db,
                deck_id=deck.id,
                user_id=user.id,
                front=front,
                back=back,
                example_sentence=None,
            )
            created += 1
            results.append(schemas.BulkItemResult(line=line, status="created", card_id=card.id))
        except ValueError as e:
            # e.g. permission or "Duplicate word in this deck" if you added unique constraint
            skipped += 1
            results.append(schemas.BulkItemResult(line=line, status="skipped", reason=str(e)))
        except IntegrityError:
            db.rollback()
            skipped += 1
            results.append(schemas.BulkItemResult(line=line, status="skipped", reason="duplicate"))
        except Exception as e:
            failed += 1
            results.append(schemas.BulkItemResult(line=line, status="failed", reason=str(e)))

    return {
        "deck_id": deck.id,
        "created": created,
        "skipped": skipped,
        "failed": failed,
        "results": results,
    }

