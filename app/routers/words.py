from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from .. import schemas, crud
from ..models import Word
from ..schemas import WordCreate, WordOut

router = APIRouter(prefix="/words", tags=["words"])

@router.get("", response_model=list[schemas.WordOut])
def get_words(language_id: int, db: Session = Depends(get_db)):
    return crud.get_words_by_language(db, language_id)

@router.post("", response_model=schemas.WordOut)
def create_word(word: schemas.WordCreate, db: Session = Depends(get_db)):
    return crud.create_word(db, word)




@router.put("/{word_id}", response_model=WordOut)
def update_word(word_id: int, word: WordCreate, db: Session = Depends(get_db)):
    db_word = db.query(Word).filter(Word.id == word_id).first()
    if not db_word:
        raise HTTPException(status_code=404, detail="Word not found")

    db_word.text = word.text
    db_word.translation = word.translation
    db_word.example_sentence = word.example_sentence
    db_word.language_id = word.language_id

    db.commit()
    db.refresh(db_word)
    return db_word


@router.delete("/{word_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_word(word_id: int, db: Session = Depends(get_db)):
    db_word = db.query(Word).filter(Word.id == word_id).first()
    if not db_word:
        raise HTTPException(status_code=404, detail="Word not found")

    db.delete(db_word)
    db.commit()
    return