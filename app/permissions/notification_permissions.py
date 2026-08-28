def can_view_notification(user, notification) -> bool:
    return bool(user and notification and notification.recipient_id == user.id)


def can_mark_notification_read(user, notification) -> bool:
    return can_view_notification(user, notification)


def can_delete_notification(user, notification) -> bool:
    return can_view_notification(user, notification)
