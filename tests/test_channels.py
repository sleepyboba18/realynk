from types import SimpleNamespace
from uuid import uuid4

from app.permissions.channel_permissions import (
    can_delete_channel,
    can_manage_channel,
    can_manage_member,
    can_view_channel,
    has_channel_role,
)
from app.schemas.channel import (
    validate_create_channel,
    validate_role,
    validate_update_channel,
    validate_user_id,
)


def membership(role):
    return SimpleNamespace(role=role)


def test_channel_schema_accepts_public_text_channel():
    assert not validate_create_channel({"name": "backend", "is_private": False})


def test_channel_schema_rejects_invalid_name_and_type():
    errors = validate_create_channel({"name": "a\n", "channel_type": "voice"})
    assert "name" in errors
    assert "channel_type" in errors


def test_channel_update_schema_rejects_owner_fields():
    assert "fields" in validate_update_channel({"owner_id": str(uuid4())})


def test_member_schema_validates_uuid_and_role():
    assert not validate_user_id({"user_id": str(uuid4())})
    assert "user_id" in validate_user_id({"user_id": "bad"})
    assert not validate_role({"role": "admin"})
    assert "role" in validate_role({"role": "owner"})


def test_role_hierarchy_and_permissions():
    assert has_channel_role(membership("owner"), "admin")
    assert has_channel_role(membership("admin"), "member")
    assert not has_channel_role(membership("member"), "admin")
    assert can_manage_channel(membership("admin"))
    assert can_delete_channel(membership("owner"))
    assert can_manage_member(membership("owner"), membership("member"))
    assert not can_manage_member(membership("admin"), membership("owner"))


def test_private_visibility_requires_membership():
    private_channel = SimpleNamespace(is_private=True)
    public_channel = SimpleNamespace(is_private=False)
    assert can_view_channel(private_channel, membership("member"))
    assert not can_view_channel(private_channel, None)
    assert can_view_channel(public_channel, None)
