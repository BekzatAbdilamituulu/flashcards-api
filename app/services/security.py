import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
REFRESH_SECRET_KEY = settings.refresh_secret_key
REFRESH_TOKEN_EXPIRE_DAYS = settings.refresh_token_expire_days


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES):
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expires_minutes)

    payload = {
        "sub": subject,
        "type": "access",
        "iat": int(now.timestamp()),
        "jti": str(uuid.uuid4()),
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(subject: str, expires_days: int = REFRESH_TOKEN_EXPIRE_DAYS):
    expire = datetime.now(timezone.utc) + timedelta(days=expires_days)
    jti = str(uuid.uuid4())
    payload = {"sub": subject, "type": "refresh", "jti": jti, "exp": expire}
    token = jwt.encode(payload, REFRESH_SECRET_KEY, algorithm=ALGORITHM)
    return token, jti, expire


def decode_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload.get("sub")
    except JWTError:
        return None
