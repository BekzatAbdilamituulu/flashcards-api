from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from .. import schemas
from ..services.stats import get_language_stats

router = APIRouter(tags=["stats"])

@router.get("/stats", response_model=schemas.StatsOut)
def stats(
    language_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_language_stats(db, user.id, language_id)
