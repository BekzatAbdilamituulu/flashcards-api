from __future__ import annotations

from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from .. import crud, schemas
from ..utils.dates import month_bounds
from ..utils.time import bishkek_today

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("/daily", response_model=schemas.DailyProgressRangeOut)
def daily_progress_range(
    from_date: date,
    to_date: date,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if from_date > to_date:
        raise ValueError("from_date must be <= to_date")

    items = crud.get_daily_progress_filled(db, current_user.id, from_date, to_date)

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
    limit: int = Query(default=50, ge=1, le=200),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    d = bishkek_today()
    count = crud.count_cards_created_on_day(db, current_user.id, d, deck_id=deck_id)
    return {
        "date": d,
        "count": count,
    }

@router.get("/streak", response_model=schemas.StreakOut)
def streak(
    threshold: int = Query(default=10, ge=1, le=1000),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = crud.get_streak(db, current_user.id, threshold=threshold)
    return data

@router.get("/month", response_model=schemas.DailyProgressRangeOut)
def monthly_progress(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        from_date, to_date = month_bounds(year, month)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    items = crud.get_daily_progress_filled(db, current_user.id, from_date, to_date)

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
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    d = bishkek_today()

    # today progress row
    dp = crud.get_daily_progress_for_day(db, current_user.id, d)

    # today created cards
    today_added = crud.count_cards_created_on_day(db, current_user.id, d, deck_id=deck_id)

    # streak
    st = crud.get_streak(db, current_user.id, threshold=streak_threshold)

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