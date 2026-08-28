from uuid import UUID

from sqlalchemy import select

from app.extensions.database import db
from app.models.notification_preference import NotificationPreference


def get_user_preferences(user_id: UUID) -> list[NotificationPreference]:
    return db.session.scalars(
        select(NotificationPreference).where(NotificationPreference.user_id == user_id)
    ).all()


def get_preference(user_id: UUID, notification_type: str) -> NotificationPreference | None:
    return db.session.scalar(
        select(NotificationPreference).where(
            NotificationPreference.user_id == user_id,
            NotificationPreference.notification_type == notification_type,
        )
    )


def upsert_preference(user_id: UUID, notification_type: str, enabled: bool) -> NotificationPreference:
    preference = get_preference(user_id, notification_type)
    if preference is None:
        preference = NotificationPreference(
            user_id=user_id,
            notification_type=notification_type,
            enabled=enabled,
        )
        db.session.add(preference)
    else:
        preference.enabled = enabled
    return preference
