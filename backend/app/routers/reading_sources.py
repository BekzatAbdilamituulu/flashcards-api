from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user
from app.services import pair_service
from app.services.srs import _normalize_status
from app.services.reading_source_service import (
    delete_reading_source,
    get_reading_source,
    list_reading_sources_for_pair,
    resolve_or_create_reading_source,
    update_reading_source,
)

router = APIRouter(prefix="/reading-sources", tags=["reading-sources"])


def _memory_strength_from_progress(status: str | None, stage: int | None) -> str:
    normalized = str(_normalize_status(status).value if status is not None else "new")
    if normalized == "mastered":
        return "Strong"
    if normalized == "learning":
        if stage is None:
            return "Medium"
        if int(stage) >= 4:
            return "Strong"
        if int(stage) >= 2:
            return "Medium"
        return "Weak"
    return "Weak"


@router.get("", response_model=schemas.Page[schemas.ReadingSourceOutWithStats])
def list_reading_sources(
    pair_id: int | None = None,
    include_stats: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if pair_id is not None and not pair_service.get_user_pair_by_id(
        db,
        user_id=user.id,
        pair_id=pair_id,
    ):
        raise HTTPException(status_code=404, detail="Learning pair not found")

    items = list_reading_sources_for_pair(
        db,
        user_id=user.id,
        pair_id=pair_id,
        include_stats=include_stats,
    )

    total = len(items)
    paged = items[offset : offset + limit]
    return {
        "items": paged,
        "meta": {
            "limit": limit,
            "offset": offset,
            "total": total,
            "has_more": offset + len(paged) < total,
        },
    }


@router.post("", response_model=schemas.ReadingSourceOut, status_code=status.HTTP_201_CREATED)
def create_source(
    payload: schemas.ReadingSourceCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    pair = pair_service.get_user_pair_by_id(db, user_id=user.id, pair_id=payload.pair_id)
    if not pair:
        raise HTTPException(status_code=404, detail="Learning pair not found")

    try:
        source = resolve_or_create_reading_source(
            db,
            user_id=user.id,
            pair_id=payload.pair_id,
            source_title=payload.title,
            source_author=payload.author,
            source_kind=payload.kind,
            source_reference=payload.reference,
            create_if_missing=True,
        )
        if source is None:
            raise ValueError("Source title is required")
        db.commit()
        return source
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        db.rollback()
        raise


@router.get("/{source_id}", response_model=schemas.ReadingSourceOut)
def get_source(
    source_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        return get_reading_source(db, user_id=user.id, source_id=source_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{source_id}", response_model=schemas.ReadingSourceOut)
def patch_source(
    source_id: int,
    payload: schemas.ReadingSourceUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        source = update_reading_source(
            db,
            user_id=user.id,
            source_id=source_id,
            title=payload.title,
            author=payload.author,
            kind=payload.kind,
            reference=payload.reference,
        )
        db.commit()
        return source
    except LookupError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Reading source with this title and author already exists for this pair",
        )
    except Exception:
        db.rollback()
        raise


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_source(
    source_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        delete_reading_source(db, user_id=user.id, source_id=source_id)
        db.commit()
        return
    except LookupError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))
    except Exception:
        db.rollback()
        raise


@router.get("/{source_id}/detail", response_model=schemas.SourceDetailOut)
def get_source_detail(
    source_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        source = get_reading_source(db, user_id=user.id, source_id=source_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))

    items_with_stats = list_reading_sources_for_pair(
        db,
        user_id=user.id,
        pair_id=source.pair_id,
        include_stats=True,
    )
    source_with_stats = next((item for item in items_with_stats if item.id == source.id), source)

    q = (
        db.query(models.Card)
        .options(joinedload(models.Card.reading_source))
        .filter(
            models.Card.reading_source_id == source.id,
            models.Card.deck.has(models.Deck.owner_id == user.id),
        )
        .order_by(models.Card.created_at.desc(), models.Card.id.desc())
    )
    total = q.count()
    items = q.offset(offset).limit(limit).all()

    card_ids = [item.id for item in items]
    progress_map = {}
    if card_ids:
        progress_rows = (
            db.query(models.UserCardProgress)
            .filter(
                models.UserCardProgress.user_id == user.id,
                models.UserCardProgress.card_id.in_(card_ids),
            )
            .all()
        )
        progress_map = {row.card_id: row for row in progress_rows}

    for item in items:
        progress = progress_map.get(item.id)
        setattr(
            item,
            "memory_strength",
            _memory_strength_from_progress(
                progress.status if progress else None,
                progress.stage if progress else None,
            ),
        )

    return {
        "source": source_with_stats,
        "cards": items,
        "meta": {
            "limit": limit,
            "offset": offset,
            "total": total,
            "has_more": offset + len(items) < total,
        },
    }


@router.get("/{source_id}/cards", response_model=schemas.Page[schemas.CardOut])
def get_source_cards(
    source_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    detail = get_source_detail(source_id, limit=limit, offset=offset, db=db, user=user)
    return {
        "items": detail["cards"],
        "meta": detail["meta"],
    }
