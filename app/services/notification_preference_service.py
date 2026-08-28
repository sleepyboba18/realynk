from app.notifications.types import DEFAULT_PREFERENCES, NotificationType
from app.repositories import notification_preference_repository
from app.extensions.database import db


class NotificationPreferenceError(ValueError):
    pass


def _type_value(notification_type: str) -> str:
    try:
        return NotificationType(notification_type).value
    except ValueError as exc:
        raise NotificationPreferenceError("Unknown notification type") from exc


def get_preferences(user) -> dict[str, bool]:
    effective = dict(DEFAULT_PREFERENCES)
    for preference in notification_preference_repository.get_user_preferences(user.id):
        effective[preference.notification_type] = preference.enabled
    return effective


def is_enabled(user_id, notification_type: str) -> bool:
    value = _type_value(notification_type)
    preference = notification_preference_repository.get_preference(user_id, value)
    return preference.enabled if preference else DEFAULT_PREFERENCES[value]


def set_preference(user, notification_type: str, enabled: bool):
    value = _type_value(notification_type)
    if not isinstance(enabled, bool):
        raise NotificationPreferenceError("enabled must be a boolean")
    preference = notification_preference_repository.upsert_preference(user.id, value, enabled)
    db.session.commit()
    return preference


def set_preferences(user, preferences: dict[str, bool]):
    unknown = set(preferences) - set(DEFAULT_PREFERENCES)
    if unknown or any(not isinstance(value, bool) for value in preferences.values()):
        raise NotificationPreferenceError("Invalid notification preferences")
    rows = [
        notification_preference_repository.upsert_preference(user.id, key, value)
        for key, value in preferences.items()
    ]
    db.session.commit()
    return rows
