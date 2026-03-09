from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..deps import get_current_user
from ..services import inbox_service

router = APIRouter(prefix="/inbox", tags=["inbox"])


@router.post("/word", response_model=schemas.InboxWordOut, status_code=status.HTTP_201_CREATED)
def quick_add_word(
    payload: schemas.InboxWordIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        return inbox_service.quick_add_word(
            db,
            user_id=user.id,
            payload=payload,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/bulk", response_model=schemas.InboxBulkOut, status_code=status.HTTP_201_CREATED)
def bulk_import(
    payload: schemas.InboxBulkIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        return inbox_service.bulk_import(
            db,
            user_id=user.id,
            payload=payload,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))