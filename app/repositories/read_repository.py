from uuid import UUID

from sqlalchemy import and_, exists, func, or_, select

from app.extensions.database import db
from app.models.message_read import MessageRead
from app.models.message import Message
from app.models.channel_membership import ChannelMembership
from app.models.conversation_participant import ConversationParticipant


def get(message_id: UUID, user_id: UUID) -> MessageRead | None:
    return db.session.scalar(
        select(MessageRead).where(
            MessageRead.message_id == message_id,
            MessageRead.user_id == user_id,
        )
    )


def count(message_id: UUID) -> int:
    return db.session.scalar(
        select(func.count(MessageRead.id)).where(MessageRead.message_id == message_id)
    ) or 0


def create(message_id: UUID, user_id: UUID, read_at):
    item = MessageRead(message_id=message_id, user_id=user_id, read_at=read_at)
    db.session.add(item)
    return item


def unread_count(user_id: UUID) -> int:
    channel_access = exists(
        select(ChannelMembership.id).where(
            ChannelMembership.channel_id == Message.channel_id,
            ChannelMembership.user_id == user_id,
        )
    )
    conversation_access = exists(
        select(ConversationParticipant.id).where(
            ConversationParticipant.conversation_id == Message.conversation_id,
            ConversationParticipant.user_id == user_id,
            ConversationParticipant.left_at.is_(None),
        )
    )
    already_read = exists(
        select(MessageRead.id).where(
            MessageRead.message_id == Message.id,
            MessageRead.user_id == user_id,
        )
    )
    return db.session.scalar(
        select(func.count(Message.id)).where(
            Message.sender_id != user_id,
            Message.deleted_at.is_(None),
            or_(
                and_(Message.channel_id.is_not(None), channel_access),
                and_(Message.conversation_id.is_not(None), conversation_access),
            ),
            ~already_read,
        )
    ) or 0
