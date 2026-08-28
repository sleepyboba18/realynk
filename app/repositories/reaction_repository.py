from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.extensions.database import db
from app.models.message_reaction import MessageReaction


def get(message_id: UUID, user_id: UUID, emoji: str) -> MessageReaction | None:
    return db.session.scalar(
        select(MessageReaction).where(
            MessageReaction.message_id == message_id,
            MessageReaction.user_id == user_id,
            MessageReaction.emoji == emoji,
        )
    )


def aggregate(message_id: UUID, user_id: UUID):
    rows = db.session.execute(
        select(
            MessageReaction.emoji,
            func.count(MessageReaction.id).label("count"),
            func.bool_or(MessageReaction.user_id == user_id).label("reacted_by_me"),
        )
        .where(MessageReaction.message_id == message_id)
        .group_by(MessageReaction.emoji)
        .order_by(func.count(MessageReaction.id).desc(), MessageReaction.emoji.asc())
    ).all()
    return [{"emoji": row.emoji, "count": row.count, "reacted_by_me": bool(row.reacted_by_me)} for row in rows]
