from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import get_db
from app.deps import get_current_user
from app.services.auto_content import get_preview_no_save_async
from app.services.pair_service import resolve_pair_for_user

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

    pair = resolve_pair_for_user(
        db,
        user_id=current_user.id,
        source_language_id=payload.source_language_id,
        target_language_id=payload.target_language_id,
        auto_create_by_langs=True,
        use_default_if_missing=True,
    )

    front = (payload.front or "").strip()
    if not front:
        raise HTTPException(status_code=422, detail="front is required")

    # load Language objects
    src_lang = (
        db.query(models.Language)
        .filter(models.Language.id == pair.source_language_id)
        .first()
    )
    tgt_lang = (
        db.query(models.Language)
        .filter(models.Language.id == pair.target_language_id)
        .first()
    )
    if not src_lang or not tgt_lang:
        raise HTTPException(status_code=422, detail="Invalid language ids")

    tr, ex, tr_cached, ex_cached = await get_preview_no_save_async(
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
            "translation": tr_cached,
            "example": ex_cached,
        },
    }
