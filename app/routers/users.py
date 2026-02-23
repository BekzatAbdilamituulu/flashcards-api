from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..deps import get_current_user
from .. import crud, models, schemas
from datetime import date

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=schemas.UserOut)
def me(current_user=Depends(get_current_user)):
    return current_user


@router.get("/me/progress", response_model=list[schemas.UserCardProgressOut])
def get_my_progress(
    deck_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Verify access (viewer is enough)
    try:
        crud.require_deck_access(db, current_user.id, deck_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Deck not found or no access")

    progress = (
        db.query(models.UserCardProgress)
        .join(models.Card, models.Card.id == models.UserCardProgress.card_id)
        .filter(models.UserCardProgress.user_id == current_user.id)
        .filter(models.Card.deck_id == deck_id)
        .order_by(models.UserCardProgress.due_at.asc().nulls_last(), models.UserCardProgress.id.asc())
        .all()
    )
    return progress


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


@router.get("/me/progress/stats")
def my_progress_stats(
    deck_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        crud.require_deck_access(db, current_user.id, deck_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Deck not found or no access")

    return {
        "deck_id": deck_id,
        "due_count": crud.count_due_reviews(db, current_user.id, deck_id),
        "new_available_count": crud.count_new_available(db, current_user.id, deck_id),
        "reviewed_today": crud.count_reviewed_today(db, current_user.id, deck_id),
        "new_introduced_today": crud.count_new_introduced_today(db, current_user.id, deck_id),
        "next_due_at": crud.get_next_due_at(db, current_user.id, deck_id),
    }

@router.put("/me/languages", response_model=schemas.UserOut)
def set_my_default_languages(
    payload: schemas.UserLanguageDefaultsIn,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Validate language ids exist
    src = db.query(models.Language).filter(models.Language.id == payload.default_source_language_id).first()
    tgt = db.query(models.Language).filter(models.Language.id == payload.default_target_language_id).first()
    if not src or not tgt:
        raise HTTPException(status_code=422, detail="Invalid language id(s)")
    if payload.default_source_language_id == payload.default_target_language_id:
        raise HTTPException(status_code=422, detail="source and target languages must be different")

    current_user.default_source_language_id = payload.default_source_language_id
    current_user.default_target_language_id = payload.default_target_language_id
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user

@router.get("/me/daily-progress", response_model=schemas.DailyProgressRangeOut)
def daily_progress(
    from_date: date,
    to_date: date,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        rows = crud.get_daily_progress(
            db,
            user_id=current_user.id,
            from_date=from_date,
            to_date=to_date,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    items = [
        schemas.DailyProgressOut(
            date=r.date,
            cards_done=r.cards_done,
            reviews_done=r.reviews_done,
            new_done=r.new_done,
        )
        for r in rows
    ]

    return {
        "from_date": from_date,
        "to_date": to_date,
        "items": items,
    }