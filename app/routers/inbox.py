from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db
from ..deps import get_current_user
from ..services.inbox_service import _split_line, resolve_language_pair

router = APIRouter(prefix="/inbox", tags=["inbox"])


@router.post("/word", response_model=schemas.InboxWordOut, status_code=status.HTTP_201_CREATED)
def quick_add_word(
    payload: schemas.InboxWordIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        src_id, tgt_id = resolve_language_pair(
            db,
            user,
            source_language_id=payload.source_language_id,
            target_language_id=payload.target_language_id,
            require_pair_exists=False,
        )
        deck = crud.get_or_create_main_deck_for_pair(
            db,
            user,
            source_language_id=src_id,
            target_language_id=tgt_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    back = (payload.back or "").strip()
    example = payload.example_sentence.strip() if payload.example_sentence else None

    try:
        card = crud.create_card(
            db,
            deck_id=deck.id,
            user_id=user.id,
            front=payload.front.strip(),
            back=back,
            example_sentence=example,
            auto_fill=True,
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
        src_id, tgt_id = resolve_language_pair(
            db,
            user,
            source_language_id=payload.source_language_id,
            target_language_id=payload.target_language_id,
            require_pair_exists=False,
        )
        deck = crud.get_or_create_main_deck_for_pair(
            db,
            user,
            source_language_id=src_id,
            target_language_id=tgt_id,
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

        # normalize for "same request" duplicates
        front_norm = crud.normalize_front(front)  # create this helper (you already planned it)
        if front_norm in seen_norms:
            skipped += 1
            results.append(
                schemas.BulkItemResult(line=line, status="skipped", reason="duplicate in paste")
            )
            continue
        seen_norms.add(front_norm)

        # duplicate in DB
        if crud.card_exists_in_deck(db, deck.id, front):
            skipped += 1
            results.append(schemas.BulkItemResult(line=line, status="skipped", reason="duplicate"))
            continue

        # Dry run: do not insert
        if payload.dry_run:
            results.append(schemas.BulkItemResult(line=line, status="preview", reason="dry_run"))
            created += 1
            continue

        # Real insert
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
