from __future__ import annotations

from datetime import date
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from .. import crud, schemas, models
from ..utils.dates import month_bounds
from ..utils.time import bishkek_today

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("/daily", response_model=schemas.DailyProgressRangeOut)
def daily_progress_range(
    from_date: date,
    to_date: date,
    pair_id: int | None = Query(default=None),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if pair_id is None:
        pair = crud.get_default_learning_pair(db, current_user.id)
        if not pair:
            raise HTTPException(status_code=400, detail="No default learning pair set")
        pair_id = pair.id

    if from_date > to_date:
        raise HTTPException(status_code=400, detail="from_date must be <= to_date")

    items = crud.get_daily_progress_filled(
        db, current_user.id, pair_id, from_date, to_date
    )

    return {
        "from_date": from_date,
        "to_date": to_date,
        "items": [
            {
                "date": r.date,
                "cards_done": r.cards_done,
                "reviews_done": r.reviews_done,
                "new_done": r.new_done,
            }
            for r in items
        ],
    }

@router.get("/today-added", response_model=schemas.TodayAddedOut)
def today_added(
    deck_id: int | None = Query(default=None),
    pair_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    d = bishkek_today()

    # If deck_id is provided, validate access + enforce main deck
    if deck_id is not None:
        deck = crud.get_deck(db, deck_id, current_user.id)
        if not deck:
            raise HTTPException(status_code=404, detail="Deck not found or no access")
        if deck.deck_type != "main":
            raise HTTPException(status_code=400, detail="Only main deck is allowed for progress")

    # If deck_id is not provided, resolve it from pair
    if deck_id is None:
        if pair_id is None:
            pair = crud.get_default_learning_pair(db, current_user.id)
            if not pair:
                raise HTTPException(status_code=400, detail="No default learning pair set")
            pair_id = pair.id
        else:
            pair = (
                db.query(models.UserLearningPair)
                .filter(
                    models.UserLearningPair.user_id == current_user.id,
                    models.UserLearningPair.id == pair_id,
                )
                .first()
            )
            if not pair:
                raise HTTPException(status_code=404, detail="Learning pair not found")

        deck = crud.get_or_create_main_deck_for_pair(
            db,
            current_user,
            source_language_id=pair.source_language_id,
            target_language_id=pair.target_language_id,
        )
        deck_id = deck.id

    count = crud.count_cards_created_on_day(db, current_user.id, d, deck_id=deck_id)
    return {"date": d, "count": count}

@router.get("/streak", response_model=schemas.StreakOut)
def streak(
    threshold: int = Query(default=10, ge=1, le=1000),
    pair_id: int | None = Query(default=None),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if pair_id is None:
        pair = crud.get_default_learning_pair(db, current_user.id)
        if not pair:
            raise HTTPException(status_code=400, detail="No default learning pair set")
        pair_id = pair.id

    data = crud.get_streak(db, current_user.id, pair_id, threshold=threshold)
    return data

@router.get("/month", response_model=schemas.DailyProgressRangeOut)
def monthly_progress(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    pair_id: int | None = Query(default=None),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if pair_id is None:
        pair = crud.get_default_learning_pair(db, current_user.id)
        if not pair:
            raise HTTPException(status_code=400, detail="No default learning pair set")
        pair_id = pair.id

    try:
        from_date, to_date = month_bounds(year, month)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    items = crud.get_daily_progress_filled(
        db, current_user.id, pair_id, from_date, to_date
    )

    return {
        "from_date": from_date,
        "to_date": to_date,
        "items": [
            {
                "date": r.date,
                "cards_done": r.cards_done,
                "reviews_done": r.reviews_done,
                "new_done": r.new_done,
            }
            for r in items
        ],
    }

@router.get("/summary", response_model=schemas.ProgressSummaryOut)
def progress_summary(
    deck_id: int | None = Query(default=None),
    streak_threshold: int = Query(default=10, ge=1, le=1000),
    pair_id: int | None = Query(default=None),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    d = bishkek_today()

    # today progress row
    dp = crud.get_daily_progress_for_day(db, current_user.id, pair_id, d)

    # today created cards
    today_added = crud.count_cards_created_on_day(db, current_user.id, d, deck_id=deck_id)

    # streak
    st = crud.get_streak(db, current_user.id, pair_id, threshold=streak_threshold)

    # study queue info (filtered by deck if provided)
    # If deck_id is None, you can either:
    #  - return zeros, or
    #  - implement global due counts across all decks.
    # For now, do deck-only if deck_id provided:
    if deck_id is not None:
        due_count = crud.count_due_reviews(db, current_user.id, deck_id)
        new_available = crud.count_new_available(db, current_user.id, deck_id)
        next_due = crud.get_next_due_at(db, current_user.id, deck_id)
    else:
        due_count = 0
        new_available = 0
        next_due = None

    # totals
    total_cards = crud.count_total_cards(db, current_user.id, deck_id=deck_id)
    status_counts = crud.count_progress_statuses(db, current_user.id, deck_id=deck_id)

    return {
        "date": d,
        "today_cards_done": dp.cards_done,
        "today_reviews_done": dp.reviews_done,
        "today_new_done": dp.new_done,
        "today_added_cards": today_added,
        "current_streak": st["current_streak"],
        "best_streak": st["best_streak"],
        "streak_threshold": st["threshold"],
        "due_count": due_count,
        "new_available_count": new_available,
        "next_due_at": next_due,
        "total_cards": total_cards,
        "total_mastered": status_counts["mastered"],
        "total_learning": status_counts["learning"],
        "total_new": status_counts["new"],
    }

@router.delete("/me/progress")
def reset_my_progress(
    deck_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Verify access (viewer is enough to reset own progress)
    try:
        crud.require_deck_access(db, current_user.id, deck_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Deck not found or no access")

    card_ids_subq = db.query(models.Card.id).filter(models.Card.deck_id == deck_id).subquery()

    deleted = (
        db.query(models.UserCardProgress)
        .filter(
            models.UserCardProgress.user_id == current_user.id,
            models.UserCardProgress.card_id.in_(card_ids_subq),
        )
        .delete(synchronize_session=False)
    )
    db.commit()

    return {"deck_id": deck_id, "deleted": deleted}