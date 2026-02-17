from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from .. import crud, models, schemas

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
        .order_by(models.UserCardProgress.next_review.asc().nulls_last(), models.UserCardProgress.id.asc())
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