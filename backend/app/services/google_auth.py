from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, status

from app.config import settings


@dataclass
class GoogleIdentity:
    sub: str
    email: str
    email_verified: bool
    name: str | None = None
    picture: str | None = None


def verify_google_id_token(token: str) -> GoogleIdentity:
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google sign-in is not configured",
        )

    try:
        from google.auth.transport import requests
        from google.oauth2 import id_token
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google sign-in support is unavailable on the server",
        ) from exc

    try:
        payload = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            settings.google_client_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token") from exc

    email = payload.get("email")
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google account email is required")

    if not payload.get("email_verified"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google account email is not verified")

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token payload")

    return GoogleIdentity(
        sub=sub,
        email=email,
        email_verified=True,
        name=payload.get("name"),
        picture=payload.get("picture"),
    )
