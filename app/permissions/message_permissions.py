from app.permissions.channel_permissions import has_channel_role
from app.permissions.conversation_permissions import can_access_conversation
from app.permissions.moderation_permissions import has_moderation_role, is_restricted


def _is_active_user(user) -> bool:
    return bool(getattr(user, "is_active", True) and getattr(user, "status", "active") == "active")


def can_send_channel_message(user, channel, membership) -> bool:
    return bool(
        user
        and _is_active_user(user)
        and not is_restricted(user)
        and membership
        and membership.user_id == user.id
        and has_channel_role(membership, "member")
        and (not getattr(channel, "locked_at", None) or has_moderation_role(user))
    )


def can_send_conversation_message(user, conversation, participant) -> bool:
    return bool(
        user
        and _is_active_user(user)
        and not is_restricted(user)
        and can_access_conversation(user, conversation, participant)
    )


def can_edit_message(user, message) -> bool:
    return bool(user and _is_active_user(user) and not is_restricted(user) and message.sender_id == user.id and message.deleted_at is None)


def can_delete_message(user, message) -> bool:
    return bool(user and _is_active_user(user) and message.sender_id == user.id and message.deleted_at is None)


def can_view_message_history(user, context, membership_or_participant) -> bool:
    if hasattr(context, "is_private"):
        return can_send_channel_message(user, context, membership_or_participant)
    return can_send_conversation_message(user, context, membership_or_participant)
