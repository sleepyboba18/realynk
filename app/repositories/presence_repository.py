from uuid import UUID

from sqlalchemy import exists, or_, select
from sqlalchemy.orm import aliased

from app.extensions.database import db
from app.models.channel_membership import ChannelMembership
from app.models.conversation_participant import ConversationParticipant
from app.models.user import User


def get_user(user_id: UUID) -> User | None:
    return db.session.get(User, user_id)


def get_users(user_ids: list[UUID]) -> list[User]:
    if not user_ids:
        return []
    return db.session.scalars(select(User).where(User.id.in_(user_ids))).all()


def can_view_presence(viewer_id: UUID, target_id: UUID) -> bool:
    if viewer_id == target_id:
        return True
    viewer_membership = aliased(ChannelMembership)
    target_membership = aliased(ChannelMembership)
    shared_channel = exists(
        select(1)
        .select_from(viewer_membership)
        .join(target_membership, target_membership.channel_id == viewer_membership.channel_id)
        .where(
            viewer_membership.user_id == viewer_id,
            target_membership.user_id == target_id,
        )
    )
    shared_conversation = exists(
        select(ConversationParticipant.id).where(
            ConversationParticipant.conversation_id.in_(
                select(ConversationParticipant.conversation_id).where(
                    ConversationParticipant.user_id == viewer_id,
                    ConversationParticipant.left_at.is_(None),
                )
            ),
            ConversationParticipant.user_id == target_id,
            ConversationParticipant.left_at.is_(None),
        )
    )
    return bool(db.session.scalar(select(or_(shared_channel, shared_conversation))))


def visible_user_ids(viewer_id: UUID, target_ids: list[UUID]) -> set[UUID]:
    return {target_id for target_id in target_ids if can_view_presence(viewer_id, target_id)}


def shared_observer_ids(target_id: UUID) -> set[UUID]:
    target_membership = aliased(ChannelMembership)
    observer_membership = aliased(ChannelMembership)
    channel_users = db.session.scalars(
        select(observer_membership.user_id)
        .select_from(observer_membership)
        .join(target_membership, target_membership.channel_id == observer_membership.channel_id)
        .where(target_membership.user_id == target_id)
        .where(observer_membership.user_id.is_not(None))
    ).all()
    conversation_users = db.session.scalars(
        select(ConversationParticipant.user_id).where(
            ConversationParticipant.conversation_id.in_(
                select(ConversationParticipant.conversation_id).where(
                    ConversationParticipant.user_id == target_id,
                    ConversationParticipant.left_at.is_(None),
                )
            ),
            ConversationParticipant.left_at.is_(None),
        )
    ).all()
    return set(channel_users) | set(conversation_users)
