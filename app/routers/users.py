from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .. import schemas, crud
from ..database import get_db
from ..services.security import hash_password
from ..services.progress import build_progress_list
from ..deps import get_current_user  # <-- JWT dependency

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=schemas.UserOut)
def me(current_user=Depends(get_current_user)):
    return current_user


@router.get("/me/progress", response_model=list[schemas.WordProgressOut])
def get_my_progress(
    language_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return build_progress_list(db, current_user.id, language_id)


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



