from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.extensions.database import db
from app.models.user import User
from app.repositories import user_repository


class DuplicateUserError(ValueError):
    """Raised when a username or email is already registered."""


class UserNotFoundError(LookupError):
    """Raised when a requested user does not exist."""


def create_user(username: str, email: str, password: str, display_name: str | None) -> User:
    normalized_username = username.strip().lower()
    normalized_email = email.strip().lower()
    if user_repository.get_by_username(normalized_username):
        raise DuplicateUserError("Username or email is already registered")
    if user_repository.get_by_email(normalized_email):
        raise DuplicateUserError("Username or email is already registered")

    user = User(
        username=normalized_username,
        email=normalized_email,
        display_name=display_name.strip() if display_name else None,
    )
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise DuplicateUserError("Username or email is already registered") from exc
    return user


def get_user(user_id: UUID) -> User:
    user = user_repository.get_by_id(user_id)
    if user is None:
        raise UserNotFoundError("User not found")
    return user


def update_profile(user: User, updates: dict[str, object]) -> User:
    for field in ("display_name", "avatar_url"):
        if field in updates:
            value = updates[field]
            setattr(user, field, value.strip() if isinstance(value, str) else value)
    db.session.commit()
    return user
