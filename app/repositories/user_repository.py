from uuid import UUID

from sqlalchemy import or_, select

from app.extensions.database import db
from app.models.user import User


def get_by_id(user_id: UUID) -> User | None:
    return db.session.get(User, user_id)


def get_by_identifier(identifier: str) -> User | None:
    statement = select(User).where(or_(User.email == identifier, User.username == identifier))
    return db.session.scalar(statement)


def get_by_username(username: str) -> User | None:
    return db.session.scalar(select(User).where(User.username == username))


def get_by_email(email: str) -> User | None:
    return db.session.scalar(select(User).where(User.email == email))


def get_by_usernames(usernames: set[str]) -> list[User]:
    if not usernames:
        return []
    return db.session.scalars(select(User).where(User.username.in_(usernames))).all()
