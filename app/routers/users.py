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
