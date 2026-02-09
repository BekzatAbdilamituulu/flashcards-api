from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from .. import schemas, crud
from ..models import Word
from ..schemas import WordCreate, WordOut
from ..deps import get_current_user

router = APIRouter(prefix="/words", tags=["words"])

@router.get("", response_model=list[schemas.WordOut])
def get_words(
    language_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    return crud.get_words_by_language(db, language_id, user.id)

@router.post("", response_model=schemas.WordOut)
def create_word(
    word: schemas.WordCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    return crud.create_word(db, word, user.id)




@router.put("/{word_id}", response_model=WordOut)
def update_word(
    word_id: int,
    word: WordCreate,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    updated = crud.update_word(db, word_id, word, user.id)
    if not updated:
        raise HTTPException(status_code=404, detail='Word not found')
    return updated



@router.delete("/{word_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_word(
    word_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    ok = crud.delete_word(db, word_id, user.id)
    if not ok:
        raise HTTPException(status_code=404, detail='Word not found')

    return
