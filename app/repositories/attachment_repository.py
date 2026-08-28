from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.extensions.database import db
from app.models.attachment import Attachment


def get_by_id(attachment_id: UUID) -> Attachment | None:
    return db.session.scalar(
        select(Attachment)
        .options(selectinload(Attachment.message))
        .where(Attachment.id == attachment_id)
    )


def get_for_message(message_id: UUID):
    return db.session.scalars(
        select(Attachment).where(
            Attachment.message_id == message_id,
            Attachment.deleted_at.is_(None),
        ).order_by(Attachment.created_at.asc(), Attachment.id.asc())
    ).all()


def count_for_message(message_id: UUID) -> int:
    from sqlalchemy import func
    return db.session.scalar(
        select(func.count(Attachment.id)).where(
            Attachment.message_id == message_id,
            Attachment.deleted_at.is_(None),
        )
    ) or 0


def total_size_for_message(message_id: UUID) -> int:
    from sqlalchemy import func
    return db.session.scalar(
        select(func.coalesce(func.sum(Attachment.file_size), 0)).where(
            Attachment.message_id == message_id,
            Attachment.deleted_at.is_(None),
        )
    ) or 0
