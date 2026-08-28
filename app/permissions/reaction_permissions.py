from app.permissions.message_permissions import can_send_channel_message, can_send_conversation_message


def can_react_to_message(user, message, access_context) -> bool:
    context, membership = access_context
    if message.deleted_at is not None:
        return False
    if hasattr(context, "is_private"):
        return can_send_channel_message(user, context, membership)
    return can_send_conversation_message(user, context, membership)


def can_remove_reaction(user, reaction) -> bool:
    return bool(user and reaction.user_id == user.id)


def can_view_reactions(user, message, access_context) -> bool:
    context, membership = access_context
    if hasattr(context, "is_private"):
        return can_send_channel_message(user, context, membership)
    return can_send_conversation_message(user, context, membership)
