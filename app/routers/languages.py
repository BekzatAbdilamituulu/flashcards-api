from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ..database import get_db
from .. import schemas, crud
from ..deps import get_current_user

router = APIRouter(prefix="/languages", tags=["languages"])

@router.post("", response_model=schemas.LanguageOut)
def create_language(language: schemas.LanguageCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return crud.create_language(db, language, user.id)

@router.get("", response_model=list[schemas.LanguageOut])
def get_languages(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return crud.get_languages(db, user.id)

@router.patch("/{language_id}", response_model=schemas.LanguageOut)
def update_language(
    language_id: int,
    payload: schemas.LanguageUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    updated = crud.update_language(db, language_id, payload, user.id)
    if not updated:
        raise HTTPException(status_code=404, detail="Language not found")
    return updated


@router.delete("/{language_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_language(
    language_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        ok = crud.delete_language(db, language_id, user.id)
    except ValueError:
        raise HTTPException(status_code=409, detail="Language contains words")

    if not ok:
        raise HTTPException(status_code=404, detail="Language not found")

    return
