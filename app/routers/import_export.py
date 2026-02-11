from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Body
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Literal
from sqlalchemy.orm import Session
from datetime import datetime
import csv, io

from ..database import get_db
from ..deps import get_current_user
from .. import schemas, crud

router = APIRouter(prefix="/words", tags=["words"])

ImportMode = Literal["skip", "update", "fail"]

def _normalize(s: str) -> str:
    return s.strip()

def _apply_import(db: Session, user_id: int, language_id: int, items: list[schemas.WordImportItem], mode: str):
    created = updated = skipped = 0

    for it in items:
        text = _normalize(it.text)
        translation = _normalize(it.translation)
        example_sentence = _normalize(it.example_sentence) if it.example_sentence else None

        if not text or not translation:
            # protects JSON import too
            raise HTTPException(status_code=400, detail="text and translation are required")

        existing = crud.find_word_by_term(db, user_id, language_id, text)

        if existing is None:
            crud.create_word_fields(db, user_id, language_id, text, translation, example_sentence)
            created += 1
        else:
            if mode == "skip":
                skipped += 1
            elif mode == "fail":
                raise HTTPException(status_code=409, detail=f"Duplicate text: '{text}'")
            elif mode == "update":
                existing.translation = translation
                existing.example_sentence = example_sentence
                updated += 1

    db.commit()
    return {
        "language_id": language_id,
        "received": len(items),
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "mode": mode,
    }

@router.post("/import/json")
def import_words_json(
    language_id: int,
    mode: str = Query(default="skip"),
    payload: schemas.WordImportRequest = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return _apply_import(db, current_user.id, language_id, payload.items, mode)

@router.post("/import/csv")
def import_words_csv(
    language_id: int,
    mode: str = Query(default="skip"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    content = file.file.read().decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(content))

    items: list[schemas.WordImportItem] = []
    for i, row in enumerate(reader, start=2):
        text = _normalize(row.get("text", ""))
        translation = _normalize(row.get("translation", ""))
        example_sentence = row.get("example_sentence")
        example_sentence = _normalize(example_sentence) if example_sentence else None

        if not text or not translation:
            raise HTTPException(status_code=400, detail=f"CSV invalid at row {i}: text/translation required")

        items.append(
            schemas.WordImportItem(
                text=text,
                translation=translation,
                example_sentence=example_sentence,
            )
        )

    return _apply_import(db, current_user.id, language_id, items, mode)

@router.get("/export")
def export_words(
    language_id: int,
    format: Literal["csv", "json"] = Query(default="csv"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    words = crud.get_words_by_language(db, language_id, current_user.id)

    if format == "json":
        data = [
            {"text": w.text, "translation": w.translation, "example_sentence": getattr(w, "example_sentence", None)}
            for w in words
        ]
        return JSONResponse(content={"language_id": language_id, "count": len(data), "items": data})

    # CSV streaming
    def gen():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["text", "translation", "example_sentence"])
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        for w in words:
            writer.writerow([w.text, w.translation, getattr(w, "example_sentence", "") or ""])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    filename = f"words_language_{language_id}_{datetime.utcnow().date().isoformat()}.csv"
    return StreamingResponse(
        gen(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )