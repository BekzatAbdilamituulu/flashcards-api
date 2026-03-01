from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db
from ..deps import require_admin

router = APIRouter(prefix="/admin/languages", tags=["admin"])


@router.post("", response_model=schemas.LanguageOut, status_code=status.HTTP_201_CREATED)
def create_language(
    payload: schemas.LanguageCreate, db: Session = Depends(get_db), _admin=Depends(require_admin)
):
    try:
        return crud.create_language(db, name=payload.name, code=payload.code)
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Language with this code already exists")


@router.patch("/{language_id}", response_model=schemas.LanguageOut)
def update_language(
    language_id: int,
    payload: schemas.LanguageUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    try:
        updated = crud.update_language(db, language_id, name=payload.name, code=payload.code)
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Language with this code already exists")

    if not updated:
        raise HTTPException(status_code=404, detail="Language not found")
    return updated


@router.delete("/{language_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_language(language_id: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    try:
        ok = crud.delete_language(db, language_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if not ok:
        raise HTTPException(status_code=404, detail="Language not found")
    return
