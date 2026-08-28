from datetime import datetime, timezone

from app.auth.jwt import create_access_token
from app.extensions.database import db
from app.models.user import User
from app.repositories import user_repository


class InvalidCredentialsError(ValueError):
    """Raised without revealing which login credential failed."""


def authenticate(identifier: str, password: str) -> User:
    normalized_identifier = identifier.strip().lower()
    user = user_repository.get_by_identifier(normalized_identifier)
    if user is None or not user.is_active or user.status != "active" or not user.check_password(password):
        raise InvalidCredentialsError("Invalid credentials")
    user.last_login_at = datetime.now(timezone.utc)
    db.session.commit()
    return user


def issue_access_token(user: User) -> str:
    return create_access_token(user.id)


def change_password(user: User, current_password: str, new_password: str) -> None:
    if not user.check_password(current_password):
        raise InvalidCredentialsError("Current password is incorrect")
    user.set_password(new_password)
    db.session.commit()
