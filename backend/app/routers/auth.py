from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from ..core.rate_limit import limiter
from jose import JWTError, jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..config import settings
from ..database import get_db
from ..models import RefreshToken
from ..services.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _authenticate_user(db: Session, *, username: str, password: str):
    user = crud.get_user_by_username(db, username=username)
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    return user


def _persist_refresh_token(
    db: Session,
    *,
    user_id: int,
    refresh_token: str,
    jti: str,
    expires_at,
) -> None:
    db.add(
        RefreshToken(
            user_id=user_id,
            jti=jti,
            token_hash=hash_token(refresh_token),
            expires_at=expires_at,
        )
    )


def _commit_or_rollback(db: Session) -> None:
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def _issue_tokens_for_user(db: Session, *, user) -> schemas.TokenOut:
    access = create_access_token(subject=user.username)
    refresh, jti, exp = create_refresh_token(subject=user.username)
    _persist_refresh_token(
        db,
        user_id=user.id,
        refresh_token=refresh,
        jti=jti,
        expires_at=exp,
    )
    return schemas.TokenOut(access_token=access, refresh_token=refresh)


@router.post("/register", response_model=schemas.TokenOut, status_code=201)
@limiter.limit("1000/minute")
def register(
    request: Request,
    payload: schemas.RegisterIn,
    db: Session = Depends(get_db),
):
    existing = crud.get_user_by_username(db, payload.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    try:
        user = crud.create_user(db, payload.username, hash_password(payload.password))
        tokens = _issue_tokens_for_user(db, user=user)
        _commit_or_rollback(db)
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Username already exists")
    return tokens


@router.post("/login-json", response_model=schemas.TokenOut)
@limiter.limit("1000/minute")
def login_json(request: Request, payload: schemas.LoginIn, db: Session = Depends(get_db)):
    user = _authenticate_user(db, username=payload.username, password=payload.password)
    tokens = _issue_tokens_for_user(db, user=user)
    _commit_or_rollback(db)
    return tokens


@router.post("/login", response_model=schemas.TokenOut)
@limiter.limit("1000/minute")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = _authenticate_user(db, username=form_data.username, password=form_data.password)
    tokens = _issue_tokens_for_user(db, user=user)
    _commit_or_rollback(db)
    return tokens


@router.post("/refresh", response_model=schemas.TokenOut)
@limiter.limit("1000/minute")
def refresh_tokens(request: Request, payload: schemas.RefreshIn, db: Session = Depends(get_db)):
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

    _persist_refresh_token(
        db,
        user_id=user.id,
        refresh_token=new_refresh,
        jti=new_jti,
        expires_at=new_exp,
    )
    _commit_or_rollback(db)

    return schemas.TokenOut(access_token=access, refresh_token=new_refresh)


@router.post("/logout")
def logout(payload: schemas.RefreshIn, db: Session = Depends(get_db)):
    token_hash = hash_token(payload.refresh_token)

    db_token = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
        )
        .first()
    )

    if db_token:
        db_token.revoked_at = datetime.utcnow()
        _commit_or_rollback(db)

    return {"detail": "Logged out"}
