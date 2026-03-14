from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from .. import crud, models, schemas
from ..database import get_db
from ..deps import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=schemas.UserOut)
def me(current_user=Depends(get_current_user)):
    return current_user


@router.put("/me/languages", response_model=schemas.UserOut)
def set_default_languages(
    payload: schemas.UserSetLanguagesIn,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.default_source_language_id == payload.default_target_language_id:
        raise HTTPException(status_code=422, detail="Source and target must differ")

    pair = (
        db.query(models.UserLearningPair)
        .filter(
            models.UserLearningPair.user_id == current_user.id,
            models.UserLearningPair.source_language_id == payload.default_source_language_id,
            models.UserLearningPair.target_language_id == payload.default_target_language_id,
        )
        .first()
    )

    try:
        if not pair:
            pair = models.UserLearningPair(
                user_id=current_user.id,
                source_language_id=payload.default_source_language_id,
                target_language_id=payload.default_target_language_id,
                is_default=False,
            )
            db.add(pair)
            db.flush()

        # this updates user legacy fields (if exist) + ensures main deck exists
        pair = crud.set_default_learning_pair(db, current_user.id, pair.id)
        db.commit()
    except Exception:
        db.rollback()
        raise

    # return fresh user (so defaults are not None)
    user = db.query(models.User).filter(models.User.id == current_user.id).first()
    return user


@router.get("/me/learning-pairs", response_model=list[schemas.UserLearningPairOut])
def my_learning_pairs(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.list_learning_pairs(db, current_user.id)


@router.post("/me/learning-pairs", response_model=schemas.UserLearningPairOut)
def add_learning_pair(
    payload: schemas.UserLearningPairCreateIn,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.source_language_id == payload.target_language_id:
        raise HTTPException(status_code=422, detail="source and target languages must be different")

    # validate languages exist (optional; you can keep)
    src = db.get(models.Language, payload.source_language_id)
    tgt = db.get(models.Language, payload.target_language_id)
    if not src or not tgt:
        raise HTTPException(status_code=422, detail="Invalid language id(s)")

    existing = (
        db.query(models.UserLearningPair)
        .options(
            joinedload(models.UserLearningPair.source_language),
            joinedload(models.UserLearningPair.target_language),
        )
        .filter(
            models.UserLearningPair.user_id == current_user.id,
            models.UserLearningPair.source_language_id == payload.source_language_id,
            models.UserLearningPair.target_language_id == payload.target_language_id,
        )
        .first()
    )
    try:
        if existing:
            pair = existing
        else:
            pair = crud.create_learning_pair(
                db,
                current_user.id,
                payload.source_language_id,
                payload.target_language_id,
            )

        if payload.make_default:
            pair = crud.set_default_learning_pair(db, current_user.id, pair.id)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return pair


@router.put("/me/learning-pairs/{pair_id}/default", response_model=schemas.UserLearningPairOut)
def set_default_pair(
    pair_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        pair = crud.set_default_learning_pair(db, current_user.id, pair_id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    if not pair:
        raise HTTPException(status_code=404, detail="Pair not found")
    return pair

@router.put("/me/goals", response_model=schemas.UserOut)
def update_my_goals(
    payload: schemas.UserGoalIn,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = (
        db.query(models.User)
        .filter(models.User.id == current_user.id)
        .first()
    )
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.daily_card_target = payload.daily_card_target
    user.daily_new_target = payload.daily_new_target

    db.commit()
    db.refresh(user)  
    return user

@router.get("/me/default-learning-pair", response_model=schemas.UserLearningPairOut)
def get_default_pair(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pair = crud.get_default_learning_pair(db, current_user.id)
    if not pair:
        raise HTTPException(status_code=404, detail="Default learning pair not set")
    return pair
