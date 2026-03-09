from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..database import get_db
from ..deps import get_current_user
from ..utils.dates import month_bounds
from ..utils.time import bishkek_today
from app.services.deck_service import require_readable_deck, resolve_main_deck_by_pair_or_deck
from app.services.progress_service import build_progress_summary

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

    items = crud.get_daily_progress_filled(db, current_user.id, pair_id, from_date, to_date)

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
    deck = resolve_main_deck_by_pair_or_deck(
        db,
        user_id=current_user.id,
        deck_id=deck_id,
        pair_id=pair_id,
    )
    count = crud.count_cards_created_on_day(db, current_user.id, d, deck_id=deck.id)
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
    items = crud.get_daily_progress_filled(db, current_user.id, pair_id, from_date, to_date)

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

def get_user_pair_deck_ids(db, user_id: int, pair_id: int) -> list[int]:
    pair = (
        db.query(models.UserLearningPair)
        .filter(
            models.UserLearningPair.user_id == user_id,
            models.UserLearningPair.id == pair_id,
        )
        .first()
    )
    if not pair:
        return []

    rows = (
        db.query(models.Deck.id)
        .join(models.DeckAccess, models.DeckAccess.deck_id == models.Deck.id)
        .filter(
            models.DeckAccess.user_id == user_id,
            models.Deck.source_language_id == pair.source_language_id,
            models.Deck.target_language_id == pair.target_language_id,
        )
        .all()
    )
    return [r[0] for r in rows]

@router.get("/summary", response_model=schemas.ProgressSummaryOut)
def progress_summary(
    deck_id: int | None = Query(default=None),
    streak_threshold: int = Query(default=10, ge=1, le=1000),
    pair_id: int | None = Query(default=None),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return build_progress_summary(
        db,
        current_user,
        deck_id=deck_id,
        pair_id=pair_id,
        streak_threshold=streak_threshold,
    )
    
@router.delete("/me/progress")
def reset_my_progress(
    deck_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Verify access (viewer is enough to reset own progress)
    try:
        require_readable_deck(
            db,
            user_id=current_user.id,
            deck_id=deck_id,
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))

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
