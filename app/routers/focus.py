from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from .. import schemas, crud
from ..services.stats import get_language_stats

router = APIRouter(tags=["focus"])

@router.get("/focus", response_model=list[schemas.WeakWordOut])
def focus_words(
    language_id: int,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rows = crud.get_weak_words(
        db,
        user_id=current_user.id,
        language_id=language_id,
        limit=limit,
    )

    result = []
    for r in rows:
        acc = 0.0
        if r.times_seen:
            acc = r.times_correct / r.times_seen

        result.append({
            "word_id": r.word_id,
            "accuracy": acc,
            "times_seen": r.times_seen,
            "times_correct": r.times_correct,
        })

    return result
