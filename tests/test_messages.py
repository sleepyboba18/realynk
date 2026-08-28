from types import SimpleNamespace
from uuid import uuid4

from app.permissions.message_permissions import (
    can_delete_message,
    can_edit_message,
    can_send_channel_message,
    can_send_conversation_message,
)
from app.schemas.message import validate_create_message, validate_update_message


def test_message_create_requires_exactly_one_context():
    assert "context" in validate_create_message({"content": "hello"})
    assert "context" in validate_create_message(
        {"channel_id": str(uuid4()), "conversation_id": str(uuid4()), "content": "hello"}
    )


def test_message_schema_validates_content_and_unknown_fields():
    assert "content" in validate_create_message({"channel_id": str(uuid4()), "content": "  "})
    assert "fields" in validate_create_message(
        {"channel_id": str(uuid4()), "content": "hello", "sender_id": str(uuid4())}
    )
    assert "content" in validate_update_message({"content": ""})
    assert not validate_update_message({"content": "edited"})


def test_message_permissions_require_active_membership_or_participant():
    user = SimpleNamespace(id=uuid4(), is_active=True, status="active")
    channel = SimpleNamespace(is_private=True)
    membership = SimpleNamespace(user_id=user.id, role="member")
    conversation = SimpleNamespace()
    participant = SimpleNamespace(user_id=user.id, left_at=None)
    assert can_send_channel_message(user, channel, membership)
    assert can_send_conversation_message(user, conversation, participant)
    assert not can_send_channel_message(user, channel, None)
    assert not can_send_conversation_message(user, conversation, SimpleNamespace(user_id=user.id, left_at=object()))


def test_only_sender_can_edit_or_delete_non_deleted_message():
    user = SimpleNamespace(id=uuid4())
    message = SimpleNamespace(sender_id=user.id, deleted_at=None)
    other = SimpleNamespace(id=uuid4())
    assert can_edit_message(user, message)
    assert can_delete_message(user, message)
    assert not can_edit_message(other, message)
    assert not can_delete_message(other, message)
    message.deleted_at = object()
    assert not can_edit_message(user, message)
    assert not can_delete_message(user, message)
