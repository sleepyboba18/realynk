from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import joinedload, selectinload

from app.extensions.database import db
from app.models.message import Message


def get_by_id(message_id: UUID) -> Message | None:
    return db.session.scalar(
        select(Message)
        .options(joinedload(Message.sender), selectinload(Message.attachments))
        .where(Message.id == message_id)
    )


def list_history(
    channel_id: UUID | None,
    conversation_id: UUID | None,
    limit: int,
    before: Message | None = None,
    offset: int = 0,
) -> tuple[list[Message], bool]:
    context_filter = (
        Message.channel_id == channel_id
        if channel_id is not None
        else Message.conversation_id == conversation_id
    )
    statement = select(Message).options(
        joinedload(Message.sender), selectinload(Message.attachments)
    ).where(context_filter)
    if before:
        statement = statement.where(
            or_(
                Message.created_at < before.created_at,
                and_(Message.created_at == before.created_at, Message.id < before.id),
            )
        )
    statement = (
        statement.order_by(Message.created_at.desc(), Message.id.desc())
        .offset(offset)
        .limit(limit + 1)
    )
    rows = db.session.scalars(statement).unique().all()
    has_more = len(rows) > limit
    return list(reversed(rows[:limit])), has_more
