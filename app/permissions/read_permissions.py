def can_mark_message_read(user, message) -> bool:
    return bool(user and message and message.deleted_at is None)
