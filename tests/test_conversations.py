from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.permissions.conversation_permissions import (
    can_access_conversation,
    can_leave_conversation,
    can_message_user,
    is_conversation_participant,
)
from app.schemas.conversation import validate_create_conversation
from app.services.conversation_service import ConversationError, _canonical_pair


def test_canonical_pair_is_independent_of_request_order():
    first, second = uuid4(), uuid4()
    assert _canonical_pair(first, second) == _canonical_pair(second, first)
    assert _canonical_pair(first, second)[0].hex < _canonical_pair(first, second)[1].hex


def test_conversation_schema_requires_only_valid_target_uuid():
    assert not validate_create_conversation({"user_id": str(uuid4())})
    assert "user_id" in validate_create_conversation({"user_id": "invalid"})
    assert "fields" in validate_create_conversation({"user_id": str(uuid4()), "extra": True})


def test_self_conversation_error_contract():
    error = ConversationError(
        "SELF_CONVERSATION_NOT_ALLOWED",
        "You cannot create a direct conversation with yourself",
        422,
    )
    assert error.code == "SELF_CONVERSATION_NOT_ALLOWED"
    assert error.status == 422


def test_only_active_participants_can_access_or_leave():
    user = SimpleNamespace(id=uuid4(), is_active=True)
    active = SimpleNamespace(user_id=user.id, left_at=None)
    left = SimpleNamespace(user_id=user.id, left_at=object())
    conversation = SimpleNamespace(participants=[active])
    assert is_conversation_participant(user, conversation, active)
    assert can_access_conversation(user, conversation, active)
    assert can_leave_conversation(user, conversation, active)
    assert not is_conversation_participant(user, conversation, left)


def test_blocking_hook_requires_active_users():
    assert can_message_user(SimpleNamespace(is_active=True), SimpleNamespace(is_active=True))
    assert not can_message_user(SimpleNamespace(is_active=False), SimpleNamespace(is_active=True))
