from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, select, update

from app.extensions.database import db
from app.models.notification import Notification


def create(notification: Notification) -> Notification:
    db.session.add(notification)
    return notification


def get_by_id(notification_id: UUID) -> Notification | None:
    return db.session.get(Notification, notification_id)


def find_duplicate(recipient_id: UUID, deduplication_key: str | None) -> Notification | None:
    if not deduplication_key:
        return None
    return db.session.scalar(
        select(Notification).where(
            Notification.recipient_id == recipient_id,
            Notification.deduplication_key == deduplication_key,
            Notification.deleted_at.is_(None),
        )
    )


def list_for_user(recipient_id: UUID, page: int, limit: int, unread_only: bool):
    conditions = [Notification.recipient_id == recipient_id, Notification.deleted_at.is_(None)]
    if unread_only:
        conditions.append(Notification.is_read.is_(False))
    statement = (
        select(Notification)
        .where(*conditions)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    total = db.session.scalar(select(func.count(Notification.id)).where(*conditions)) or 0
    return db.session.scalars(statement).all(), total


def count_unread(recipient_id: UUID) -> int:
    return db.session.scalar(
        select(func.count(Notification.id)).where(
            Notification.recipient_id == recipient_id,
            Notification.deleted_at.is_(None),
            Notification.is_read.is_(False),
        )
    ) or 0


def mark_all_read(recipient_id: UUID, read_at: datetime) -> int:
    result = db.session.execute(
        update(Notification)
        .where(
            Notification.recipient_id == recipient_id,
            Notification.deleted_at.is_(None),
            Notification.is_read.is_(False),
        )
        .values(is_read=True, read_at=read_at)
    )
    return result.rowcount
