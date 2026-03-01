from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import get_db
from app.deps import get_current_user
from app.services.auto_content import get_preview_with_cache_async
from app.services.inbox_service import resolve_language_pair

router = APIRouter(prefix="/auto", tags=["auto"])


@router.post("/preview", response_model=schemas.AutoPreviewOut)
async def preview_auto(
    payload: schemas.AutoPreviewIn,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.deck_id is not None:
        if not crud.user_has_access_to_deck(db, current_user.id, payload.deck_id):
            raise HTTPException(status_code=403, detail="No access to deck")

    src_id, tgt_id = resolve_language_pair(
        db,
        user=current_user,
        source_language_id=payload.source_language_id,
        target_language_id=payload.target_language_id,
    )

    front = (payload.front or "").strip()
    if not front:
        raise HTTPException(status_code=422, detail="front is required")

    # load Language objects
    src_lang = db.query(models.Language).filter(models.Language.id == src_id).first()
    tgt_lang = db.query(models.Language).filter(models.Language.id == tgt_id).first()
    if not src_lang or not tgt_lang:
        raise HTTPException(status_code=422, detail="Invalid language ids")

    tr, ex = await get_preview_with_cache_async(
        db, src_lang=src_lang, tgt_lang=tgt_lang, text_raw=front
    )

    return {
        "front": front,
        "suggested_back": tr,
        "suggested_example_sentence": ex,
        "provider": {
            "translation": "mymemory" if tr else None,
            "example": "tatoeba" if ex else None,
        },
        "cached": {
            "translation": False,
            "example": False,
        },
    }
