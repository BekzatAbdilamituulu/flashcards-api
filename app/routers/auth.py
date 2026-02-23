from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt, JWTError
from datetime import datetime, timezone
from ..database import get_db
from ..config import settings
from .. import crud, schemas
from ..models import RefreshToken
from ..services.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=schemas.TokenOut, status_code=201)
def register(payload: schemas.RegisterIn, db: Session = Depends(get_db)):
    existing = crud.get_user_by_username(db, payload.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    user = crud.create_user(db, payload.username, hash_password(payload.password))

    access = create_access_token(subject=user.username)
    refresh, jti, exp = create_refresh_token(subject=user.username)

    db.add(
        RefreshToken(
            user_id=user.id,
            jti=jti,
            token_hash=hash_token(refresh),
            expires_at=exp,
        )
    )
    db.commit()

    return schemas.TokenOut(access_token=access, refresh_token=refresh)

@router.post("/login", response_model=schemas.TokenOut)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = crud.get_user_by_username(db, username=form_data.username)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    access = create_access_token(subject=user.username)
    refresh, jti, exp = create_refresh_token(subject=user.username)

    db.add(
        RefreshToken(
            user_id=user.id,
            jti=jti,
            token_hash=hash_token(refresh),
            expires_at=exp,
        )
    )
    db.commit()

    return schemas.TokenOut(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=schemas.TokenOut)
def refresh_tokens(payload: schemas.RefreshIn, db: Session = Depends(get_db)):
    token = payload.refresh_token

    try:
        data = jwt.decode(token, settings.refresh_secret_key, algorithms=[settings.algorithm])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    username = data.get("sub")
    jti = data.get("jti")
    if not username or not jti:
        raise HTTPException(status_code=401, detail="Invalid refresh token payload")

    user = crud.get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    db_token = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()
    if not db_token:
        raise HTTPException(status_code=401, detail="Refresh token not found")

    expires_at = db_token.expires_at

    # SQLite may return naive datetime even if timezone=True.
    # Use a "now" with the same awareness as expires_at.
    if expires_at.tzinfo is None:
        now = datetime.utcnow()
    else:
        now = datetime.now(timezone.utc)

    if expires_at <= now:
        raise HTTPException(status_code=401, detail="Refresh token expired")

    if db_token.revoked_at is not None:
        raise HTTPException(status_code=401, detail="Refresh token revoked")

    if db_token.expires_at <= now:
        raise HTTPException(status_code=401, detail="Refresh token expired")

    if db_token.token_hash != hash_token(token):
        raise HTTPException(status_code=401, detail="Refresh token mismatch")

    # ROTATE: revoke old refresh
    db_token.revoked_at = now

    # issue new pair
    access = create_access_token(subject=user.username)
    new_refresh, new_jti, new_exp = create_refresh_token(subject=user.username)

    db.add(RefreshToken(
        user_id=user.id,
        jti=new_jti,
        token_hash=hash_token(new_refresh),
        expires_at=new_exp,
    ))

    db.commit()

    return schemas.TokenOut(access_token=access, refresh_token=new_refresh)

@router.post("/logout")
def logout(payload: schemas.RefreshIn, db: Session = Depends(get_db)):
    token_hash = hash_token(payload.refresh_token)

    db_token = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash,
        RefreshToken.revoked_at.is_(None),
    ).first()

    if db_token:
        db_token.revoked_at = datetime.utcnow()
        db.commit()

    return {"detail": "Logged out"}