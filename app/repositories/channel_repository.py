from uuid import UUID

from sqlalchemy import func, or_, select

from app.extensions.database import db
from app.models.channel import Channel
from app.models.channel_membership import ChannelMembership


def get_channel(channel_id: UUID) -> Channel | None:
    return db.session.get(Channel, channel_id)


def get_membership(channel_id: UUID, user_id: UUID) -> ChannelMembership | None:
    return db.session.scalar(
        select(ChannelMembership).where(
            ChannelMembership.channel_id == channel_id,
            ChannelMembership.user_id == user_id,
        )
    )


def list_channels(user_id: UUID, page: int, per_page: int):
    visibility = or_(Channel.is_private.is_(False), ChannelMembership.user_id == user_id)
    base = (
        select(Channel)
        .outerjoin(ChannelMembership, ChannelMembership.channel_id == Channel.id)
        .where(visibility)
        .distinct()
        .order_by(Channel.created_at.desc())
    )
    total = db.session.scalar(
        select(func.count()).select_from(
            select(Channel.id)
            .outerjoin(ChannelMembership, ChannelMembership.channel_id == Channel.id)
            .where(visibility)
            .distinct()
            .subquery()
        )
    ) or 0
    items = db.session.scalars(base.offset((page - 1) * per_page).limit(per_page)).all()
    return items, total


def list_members(channel_id: UUID, page: int, per_page: int):
    base = (
        select(ChannelMembership)
        .where(ChannelMembership.channel_id == channel_id)
        .order_by(ChannelMembership.joined_at.asc())
    )
    total = db.session.scalar(
        select(func.count()).select_from(ChannelMembership).where(ChannelMembership.channel_id == channel_id)
    ) or 0
    items = db.session.scalars(base.offset((page - 1) * per_page).limit(per_page)).all()
    return items, total
