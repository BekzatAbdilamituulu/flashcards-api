from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from .. import schemas, crud

router = APIRouter(prefix="/languages", tags=["languages"])

@router.post("", response_model=schemas.LanguageOut)
def create_language(language: schemas.LanguageCreate, db: Session = Depends(get_db)):
    return crud.create_language(db, language)

@router.get("", response_model=list[schemas.LanguageOut])
def get_languages(db: Session = Depends(get_db)):
    return crud.get_languages(db)
