from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from flask import current_app


class TokenError(ValueError):
    """Raised when an access token is missing or invalid."""


def create_access_token(user_id: UUID) -> str:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=current_app.config["JWT_ACCESS_TOKEN_EXPIRES_MINUTES"])
    payload = {"sub": str(user_id), "iat": now, "exp": expires_at}
    return jwt.encode(payload, current_app.config["JWT_SECRET_KEY"], algorithm="HS256")


def decode_access_token(token: str) -> UUID:
    try:
        payload = jwt.decode(
            token,
            current_app.config["JWT_SECRET_KEY"],
            algorithms=["HS256"],
            options={"require": ["sub", "iat", "exp"]},
        )
        return UUID(payload["sub"])
    except (jwt.InvalidTokenError, ValueError, KeyError, TypeError) as exc:
        raise TokenError("Invalid access token") from exc
