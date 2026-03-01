from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db
from ..deps import get_current_user

router = APIRouter(prefix="/languages", tags=["languages"])


@router.get("", response_model=list[schemas.LanguageOut])
def list_languages(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    """Read-only for normal users (languages are global/admin-managed)."""
    return crud.list_languages(db)
