from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from .. import schemas, crud
from ..services.security import hash_password
from ..services.deck import compute_status
from ..deps import get_current_user  # <-- JWT dependency

router = APIRouter(prefix="/users", tags=["users"])

'''
@router.post("", response_model=schemas.UserOut)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # NOTE: your schema currently uses `hashed_password` as input field name.
    # It actually contains the *plain password* from the client. Consider renaming to `password`.
    return crud.create_user(db, user.username, hash_password(user.password))
'''

# -------------------------
# New "me" endpoints (recommended)
# -------------------------

@router.get("/me/progress", response_model=list[schemas.WordProgressOut])
def get_my_progress(
    language_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = crud.get_user_progress(db, current_user.id, language_id)

    return [
        schemas.WordProgressOut(
            word=word,
            times_seen=uw.times_seen or 0,
            times_correct=uw.times_correct or 0,
            status=compute_status(uw.times_seen or 0, uw.times_correct or 0),
            last_review=uw.last_review,
        )
        for (word, uw) in rows
    ]


@router.get("/me/progress/stats", response_model=schemas.ProgressStatsOut)
def my_progress_stats(
    language_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.get_progress_stats(db, current_user.id, language_id)


@router.delete("/me/progress", response_model=schemas.ProgressResetOut)
def reset_my_progress(
    language_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    deleted = crud.reset_user_progress(db, current_user.id, language_id)
    return schemas.ProgressResetOut(
        user_id=current_user.id,
        language_id=language_id,
        deleted=deleted,
    )



