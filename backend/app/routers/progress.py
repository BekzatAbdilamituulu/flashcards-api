from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..deps import get_current_user
from app.services.errors import NotFoundError, ValidationError
from app.services.progress_service import (
    build_progress_summary,
    daily_progress_range as daily_progress_range_service,
    monthly_progress_range as monthly_progress_range_service,
    reset_my_progress_for_deck,
    streak_for_user,
    today_added_for_user,
)

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("/daily", response_model=schemas.DailyProgressRangeOut)
def daily_progress_range(
    from_date: date,
    to_date: date,
    pair_id: int | None = Query(default=None),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return daily_progress_range_service(
            db,
            user_id=current_user.id,
            from_date=from_date,
            to_date=to_date,
            pair_id=pair_id,
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/today-added", response_model=schemas.TodayAddedOut)
def today_added(
    deck_id: int | None = Query(default=None),
    pair_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return today_added_for_user(
            db,
            user_id=current_user.id,
            deck_id=deck_id,
            pair_id=pair_id,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/streak", response_model=schemas.StreakOut)
def streak(
    threshold: int = Query(default=10, ge=1, le=1000),
    pair_id: int | None = Query(default=None),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return streak_for_user(
            db,
            user_id=current_user.id,
            threshold=threshold,
            pair_id=pair_id,
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/month", response_model=schemas.DailyProgressRangeOut)
def monthly_progress(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    pair_id: int | None = Query(default=None),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return monthly_progress_range_service(
            db,
            user_id=current_user.id,
            year=year,
            month=month,
            pair_id=pair_id,
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

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
    try:
        return reset_my_progress_for_deck(
            db,
            user_id=current_user.id,
            deck_id=deck_id,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
