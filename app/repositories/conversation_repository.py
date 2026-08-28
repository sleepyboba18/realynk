from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.extensions.database import db
from app.models.conversation import Conversation
from app.models.conversation_participant import ConversationParticipant


def get_by_id(conversation_id: UUID) -> Conversation | None:
    return db.session.scalar(
        select(Conversation)
        .options(selectinload(Conversation.participants).selectinload(ConversationParticipant.user))
        .where(Conversation.id == conversation_id)
    )


def get_direct_by_pair(participant_a_id: UUID, participant_b_id: UUID) -> Conversation | None:
    return db.session.scalar(
        select(Conversation)
        .options(selectinload(Conversation.participants).selectinload(ConversationParticipant.user))
        .where(
            Conversation.conversation_type == "direct",
            Conversation.participant_a_id == participant_a_id,
            Conversation.participant_b_id == participant_b_id,
        )
    )


def get_participant(conversation_id: UUID, user_id: UUID) -> ConversationParticipant | None:
    return db.session.scalar(
        select(ConversationParticipant).where(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.user_id == user_id,
        )
    )


def list_for_user(user_id: UUID, page: int, per_page: int):
    base = (
        select(Conversation)
        .join(ConversationParticipant)
        .options(selectinload(Conversation.participants).selectinload(ConversationParticipant.user))
        .where(
            ConversationParticipant.user_id == user_id,
            ConversationParticipant.left_at.is_(None),
        )
        .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
    )
    total = db.session.scalar(
        select(func.count(Conversation.id))
        .join(ConversationParticipant)
        .where(
            ConversationParticipant.user_id == user_id,
            ConversationParticipant.left_at.is_(None),
        )
    ) or 0
    items = db.session.scalars(base.offset((page - 1) * per_page).limit(per_page)).unique().all()
    return items, total


def list_participants(conversation_id: UUID):
    return db.session.scalars(
        select(ConversationParticipant)
        .options(selectinload(ConversationParticipant.user))
        .where(ConversationParticipant.conversation_id == conversation_id)
        .order_by(ConversationParticipant.joined_at.asc())
    ).all()
