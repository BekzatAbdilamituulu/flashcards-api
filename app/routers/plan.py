from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from .. import schemas
from ..services.planner import build_today_plan
from .. import crud


router = APIRouter(prefix="/plan", tags=["plan"])


@router.get("/today", response_model=schemas.TodayPlanOut)
def today_plan(
    language_id: int,
    backlog_threshold: int = 150,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    res = build_today_plan(
        db=db,
        user=current_user,
        language_id=language_id,
        backlog_threshold=backlog_threshold,
    )

    items = (
        [{"word_id": wid, "kind": "review"} for wid in res.review_word_ids] +
        [{"word_id": wid, "kind": "new"} for wid in res.new_word_ids]
    )

    return {
        "language_id": language_id,
        "planned_reviews": res.planned_reviews,
        "planned_new": res.planned_new,
        "items": items,
        "message": res.message,
        "backlog_due_count": res.backlog_due_count,
        "backlog_protection_active": res.backlog_protection_active,
    }

@router.get("/today_goal")
def today_goal(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    progress = crud.get_or_create_daily_progress(db, current_user.id)

    target = current_user.daily_card_target
    done = progress.cards_done
    remaining = max(0, target - done)

    return {
        "target": target,
        "done": done,
        "remaining": remaining,
        "completed": done >= target,
    }
