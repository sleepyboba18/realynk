from types import SimpleNamespace
from uuid import uuid4

from app.permissions.message_permissions import can_send_channel_message
from app.permissions.reaction_permissions import can_remove_reaction, can_react_to_message
from app.schemas.read import MAX_READ_BATCH, validate_message_ids
from app.schemas.reaction import EMOJI_MAX_LENGTH, validate_reaction


def test_reaction_validation_accepts_unicode_and_rejects_unknown_fields():
    assert not validate_reaction({"emoji": "👍"})
    assert "fields" in validate_reaction({"emoji": "👍", "user_id": str(uuid4())})
    assert "emoji" in validate_reaction({"emoji": ""})
    assert "emoji" in validate_reaction({"emoji": "x" * (EMOJI_MAX_LENGTH + 1)})


def test_read_batch_validation_is_bounded_and_uuid_only():
    message_ids, errors = validate_message_ids({"message_ids": [str(uuid4())]})
    assert len(message_ids) == 1
    assert not errors
    assert "message_ids" in validate_message_ids({"message_ids": ["bad"]})[1]
    assert "message_ids" in validate_message_ids({"message_ids": [str(uuid4())] * (MAX_READ_BATCH + 1)})[1]


def test_reaction_permissions_require_access_and_owner_removal():
    user = SimpleNamespace(id=uuid4(), is_active=True, status="active")
    channel = SimpleNamespace(is_private=False)
    membership = SimpleNamespace(user_id=user.id, role="member")
    message = SimpleNamespace(deleted_at=None)
    assert can_react_to_message(user, message, (channel, membership))
    assert not can_react_to_message(user, SimpleNamespace(deleted_at=object()), (channel, membership))
    assert can_remove_reaction(user, SimpleNamespace(user_id=user.id))
    assert not can_remove_reaction(user, SimpleNamespace(user_id=uuid4()))


def test_read_and_reaction_models_have_distinct_database_contracts():
    from app.models.message_read import MessageRead
    from app.models.message_reaction import MessageReaction

    reaction_constraints = {constraint.name for constraint in MessageReaction.__table__.constraints}
    read_constraints = {constraint.name for constraint in MessageRead.__table__.constraints}
    assert "uq_message_reaction_user_emoji" in reaction_constraints
    assert "uq_message_read_user" in read_constraints
