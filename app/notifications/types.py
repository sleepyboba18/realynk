from enum import StrEnum


class NotificationType(StrEnum):
    NEW_MESSAGE = "new_message"
    MENTION = "mention"
    DIRECT_MESSAGE = "direct_message"
    REACTION = "reaction"
    CHANNEL_INVITATION = "channel_invitation"
    SYSTEM = "system"


DEFAULT_PREFERENCES = {notification_type.value: True for notification_type in NotificationType}
