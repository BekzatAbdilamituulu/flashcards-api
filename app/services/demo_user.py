from sqlalchemy.orm import Session
from .. import crud
from .security import hash_password

def get_or_create_demo_user(db: Session, user_id: int):
    user = crud.get_user(db, user_id)
    if user:
        return user
    return crud.create_user(
        db=db,
        username=f"demo_user_{user_id}",
        hashed_password=hash_password("demo"),
    )
