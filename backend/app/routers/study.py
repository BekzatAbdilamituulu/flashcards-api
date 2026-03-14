from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..deps import get_current_user
from ..services.study_service import next_study_for_main_deck, status_for_main_deck, study_card

router = APIRouter(prefix="/study", tags=["study"])


@router.post("/{card_id}", response_model=schemas.UserCardProgressOut)
def study_card_me(
    card_id: int,
    payload: schemas.StudyAnswerIn,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return study_card(
            db,
            user_id=current_user.id,
            card_id=card_id,
            learned=payload.learned,
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/decks/{deck_id}/next", response_model=schemas.StudyBatchOut)
def next_study_for_deck(
    deck_id: int,
    limit: int = Query(20, ge=1, le=100),
    new_ratio: float = Query(0.3, ge=0.0, le=1.0),
    max_new_per_day: int = Query(10, ge=0, le=1000),
    max_reviews_per_day: int = Query(100, ge=0, le=5000),
    reading_source_id: int | None = Query(default=None, ge=1),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return next_study_for_main_deck(
            db,
            user_id=current_user.id,
            deck_id=deck_id,
            limit=limit,
            new_ratio=new_ratio,
            max_new_per_day=max_new_per_day,
            max_reviews_per_day=max_reviews_per_day,
            reading_source_id=reading_source_id,
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/decks/{deck_id}/status", response_model=schemas.StudyStatusOut)
def study_status_for_deck(
    deck_id: int,
    max_new_per_day: int = Query(10, ge=0, le=1000),
    max_reviews_per_day: int = Query(100, ge=0, le=5000),
    reading_source_id: int | None = Query(default=None, ge=1),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return status_for_main_deck(
            db,
            user_id=current_user.id,
            deck_id=deck_id,
            max_new_per_day=max_new_per_day,
            max_reviews_per_day=max_reviews_per_day,
            reading_source_id=reading_source_id,
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
