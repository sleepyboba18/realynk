from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.extensions.database import db
from app.models.moderation_action import ModerationAction


def create_action(action: ModerationAction) -> ModerationAction:
    db.session.add(action)
    return action


def get_active_action(user_id: UUID, action: str):
    from datetime import datetime, timezone
    return db.session.scalar(
        select(ModerationAction).where(
            ModerationAction.target_user_id == user_id,
            ModerationAction.action == action,
            ModerationAction.revoked_at.is_(None),
            (ModerationAction.expires_at.is_(None) | (ModerationAction.expires_at > datetime.now(timezone.utc))),
        ).order_by(ModerationAction.created_at.desc())
    )


def get_user_actions(user_id: UUID):
    return db.session.scalars(
        select(ModerationAction).options(joinedload(ModerationAction.moderator), joinedload(ModerationAction.target_user)).where(ModerationAction.target_user_id == user_id).order_by(ModerationAction.created_at.desc(), ModerationAction.id.desc())
    ).all()


def list_actions(limit: int, offset: int):
    statement = select(ModerationAction).options(joinedload(ModerationAction.moderator), joinedload(ModerationAction.target_user)).order_by(ModerationAction.created_at.desc(), ModerationAction.id.desc()).offset(offset).limit(limit)
    return db.session.scalars(statement).unique().all()
