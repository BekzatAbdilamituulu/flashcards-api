from .. import crud, schemas
from ..services.deck import compute_status


def build_progress_list(db, user_id: int, language_id: int):
    rows = crud.get_user_progress(db, user_id, language_id)

    return [
        schemas.WordProgressOut(
            word=word,
            times_seen=uw.times_seen or 0,
            times_correct=uw.times_correct or 0,
            status=compute_status(uw.times_seen or 0, uw.times_correct or 0),
            last_review=uw.last_review,
        )
        for (word, uw) in rows
    ]
