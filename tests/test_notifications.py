from types import SimpleNamespace
from uuid import uuid4

from app.notifications.types import DEFAULT_PREFERENCES, NotificationType
from app.permissions.notification_permissions import (
    can_delete_notification,
    can_mark_notification_read,
    can_view_notification,
)
from app.schemas.notification import validate_bulk_preferences, validate_preference


def test_notification_types_and_defaults_are_centralized():
    assert NotificationType.REACTION.value == "reaction"
    assert all(DEFAULT_PREFERENCES.values())
    assert set(DEFAULT_PREFERENCES) == {item.value for item in NotificationType}


def test_preference_validation_rejects_unknown_values():
    assert not validate_preference({"notification_type": "reaction", "enabled": False})
    assert "notification_type" in validate_preference({"notification_type": "unknown", "enabled": True})
    assert not validate_bulk_preferences({"reaction": False})
    assert "preferences" in validate_bulk_preferences({"unknown": True})


def test_notification_permissions_are_recipient_scoped():
    owner = SimpleNamespace(id=uuid4())
    notification = SimpleNamespace(recipient_id=owner.id)
    other = SimpleNamespace(id=uuid4())
    assert can_view_notification(owner, notification)
    assert can_mark_notification_read(owner, notification)
    assert can_delete_notification(owner, notification)
    assert not can_view_notification(other, notification)


def test_notification_model_has_deduplication_constraint():
    from app.models.notification import Notification

    names = {constraint.name for constraint in Notification.__table__.constraints}
    assert "uq_notification_recipient_deduplication" in names
