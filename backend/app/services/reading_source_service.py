from __future__ import annotations

import re
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models
from app.utils.time import bishkek_day_bounds, bishkek_today


def _normalize_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).lower()


def get_reading_source(db: Session, *, user_id: int, source_id: int) -> models.ReadingSource:
    source = (
        db.query(models.ReadingSource)
        .filter(
            models.ReadingSource.id == source_id,
            models.ReadingSource.user_id == user_id,
        )
        .first()
    )
    if not source:
        raise LookupError("Reading source not found")
    return source


def list_reading_sources_for_pair(
    db: Session,
    *,
    user_id: int,
    pair_id: int | None = None,
    include_stats: bool = False,
) -> list[models.ReadingSource]:
    q = db.query(models.ReadingSource).filter(models.ReadingSource.user_id == user_id)
    if pair_id is not None:
        q = q.filter(models.ReadingSource.pair_id == pair_id)

    items = q.order_by(models.ReadingSource.created_at.desc(), models.ReadingSource.id.desc()).all()

    if not include_stats or not items:
        return items

    source_ids = [item.id for item in items]

    total_rows = (
        db.query(models.Card.reading_source_id, func.count(models.Card.id))
        .join(models.Deck, models.Deck.id == models.Card.deck_id)
        .filter(models.Card.reading_source_id.in_(source_ids))
        .filter(models.Deck.owner_id == user_id)
        .filter(models.Deck.deck_type == models.DeckType.MAIN)
        .group_by(models.Card.reading_source_id)
        .all()
    )
    total_map = {sid: count for sid, count in total_rows}

    due_rows = (
        db.query(models.Card.reading_source_id, func.count(models.UserCardProgress.id))
        .join(models.UserCardProgress, models.UserCardProgress.card_id == models.Card.id)
        .join(models.Deck, models.Deck.id == models.Card.deck_id)
        .filter(
            models.Card.reading_source_id.in_(source_ids),
            models.Deck.owner_id == user_id,
            models.Deck.deck_type == models.DeckType.MAIN,
            models.UserCardProgress.user_id == user_id,
            models.UserCardProgress.due_at.isnot(None),
            models.UserCardProgress.due_at <= datetime.utcnow(),
        )
        .group_by(models.Card.reading_source_id)
        .all()
    )
    due_map = {sid: count for sid, count in due_rows}

    today_start_tz, today_end_tz = bishkek_day_bounds(bishkek_today())
    # Card.created_at is stored as naive datetime in current schema.
    today_start = today_start_tz.replace(tzinfo=None)
    today_end = today_end_tz.replace(tzinfo=None)
    today_rows = (
        db.query(models.Card.reading_source_id, func.count(models.Card.id))
        .join(models.Deck, models.Deck.id == models.Card.deck_id)
        .filter(
            models.Card.reading_source_id.in_(source_ids),
            models.Deck.owner_id == user_id,
            models.Deck.deck_type == models.DeckType.MAIN,
            models.Card.created_at >= today_start,
            models.Card.created_at < today_end,
        )
        .group_by(models.Card.reading_source_id)
        .all()
    )
    today_map = {sid: count for sid, count in today_rows}

    last_added_rows = (
        db.query(models.Card.reading_source_id, func.max(models.Card.created_at))
        .join(models.Deck, models.Deck.id == models.Card.deck_id)
        .filter(
            models.Card.reading_source_id.in_(source_ids),
            models.Deck.owner_id == user_id,
            models.Deck.deck_type == models.DeckType.MAIN,
        )
        .group_by(models.Card.reading_source_id)
        .all()
    )
    last_added_map = {sid: created_at for sid, created_at in last_added_rows}

    for item in items:
        setattr(item, "total_cards", int(total_map.get(item.id, 0) or 0))
        setattr(item, "due_cards", int(due_map.get(item.id, 0) or 0))
        setattr(item, "added_today", int(today_map.get(item.id, 0) or 0))
        setattr(item, "last_added_at", last_added_map.get(item.id))

    return items


def create_reading_source(
    db: Session,
    *,
    user_id: int,
    pair_id: int,
    title: str,
    author: str | None = None,
    kind: str | None = None,
    reference: str | None = None,
) -> models.ReadingSource:
    title_clean = (title or "").strip()
    if not title_clean:
        raise ValueError("Source title is required")

    author_clean = (author or "").strip() or None
    kind_clean = (kind or "").strip() or None
    reference_clean = (reference or "").strip() or None

    source = models.ReadingSource(
        user_id=user_id,
        pair_id=pair_id,
        title=title_clean,
        title_norm=_normalize_text(title_clean),
        author=author_clean,
        author_norm=_normalize_text(author_clean),
        kind=kind_clean,
        reference=reference_clean,
    )
    db.add(source)
    db.flush()
    db.refresh(source)
    return source


def resolve_or_create_reading_source(
    db: Session,
    *,
    user_id: int,
    pair_id: int,
    reading_source_id: int | None = None,
    source_title: str | None = None,
    source_author: str | None = None,
    source_kind: str | None = None,
    source_reference: str | None = None,
    create_if_missing: bool = True,
) -> models.ReadingSource | None:
    if reading_source_id is not None:
        source = get_reading_source(db, user_id=user_id, source_id=reading_source_id)
        if source.pair_id != pair_id:
            raise ValueError("Reading source pair does not match card pair")
        return source

    title_clean = (source_title or "").strip()
    if not title_clean:
        return None

    title_norm = _normalize_text(title_clean)
    author_clean = (source_author or "").strip() or None
    author_norm = _normalize_text(author_clean)

    existing = (
        db.query(models.ReadingSource)
        .filter(
            models.ReadingSource.user_id == user_id,
            models.ReadingSource.pair_id == pair_id,
            models.ReadingSource.title_norm == title_norm,
            models.ReadingSource.author_norm == author_norm,
        )
        .first()
    )
    if existing:
        if source_kind is not None:
            existing.kind = (source_kind or "").strip() or None
        if source_reference is not None:
            existing.reference = (source_reference or "").strip() or None
        db.flush()
        return existing

    if not create_if_missing:
        return None

    return create_reading_source(
        db,
        user_id=user_id,
        pair_id=pair_id,
        title=title_clean,
        author=author_clean,
        kind=source_kind,
        reference=source_reference,
    )
