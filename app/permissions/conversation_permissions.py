def is_conversation_participant(user, conversation, participant=None) -> bool:
    if participant is not None:
        return participant.user_id == user.id and participant.left_at is None
    return any(item.user_id == user.id and item.left_at is None for item in conversation.participants)


def can_access_conversation(user, conversation, participant=None) -> bool:
    return is_conversation_participant(user, conversation, participant)


def can_leave_conversation(user, conversation, participant=None) -> bool:
    return is_conversation_participant(user, conversation, participant)


def can_message_user(sender, recipient) -> bool:
    return bool(sender and recipient and sender.is_active and recipient.is_active)
